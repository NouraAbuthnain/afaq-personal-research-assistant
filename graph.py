"""LangGraph orchestration for the Personal Research Assistant."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from agents.executive import executive_node
from agents.general import final_response_node, general_node
from agents.knowledge import knowledge_node
from agents.report_generator import report_generation_node
from agents.research import research_node
from agents.workspace import workspace_node
from config import validate_config
from state import ResearchAssistantState


validate_config()


# ---------------------------------------------------------------------------
# Stop-condition helpers
# ---------------------------------------------------------------------------

def stop_reason(state: ResearchAssistantState) -> str:
    """Return the reason execution should stop, or an empty string."""

    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 10)

    error_count = state.get("error_count", 0)
    max_errors = state.get("max_errors", 3)

    if step_count >= max_steps:
        return (
            f"The workflow reached the maximum of "
            f"{max_steps} execution steps."
        )

    if error_count >= max_errors:
        return (
            f"The workflow exceeded its error budget of "
            f"{max_errors} errors."
        )

    if state.get("workflow_status") == "failed":
        return "The workflow encountered an unrecoverable error."

    return ""


def stop_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Stop safely when a workflow limit has been reached."""

    reason = stop_reason(state) or "The workflow was stopped safely."
    step_count = state.get("step_count", 0) + 1

    answer = f"I could not complete the request. {reason}"

    return {
        "messages": [AIMessage(content=answer)],
        "final_response": answer,
        "workflow_status": "failed",
        "task_complete": False,
        "step_count": step_count,
    }


# ---------------------------------------------------------------------------
# Clarification
# ---------------------------------------------------------------------------

def clarification_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Return the clarification question created by the Executive Agent."""

    question = (
        state.get("clarification_question")
        or "Could you provide more details about your request?"
    ).strip()

    step_count = state.get("step_count", 0) + 1

    return {
        "messages": [AIMessage(content=question)],
        "final_response": question,
        "workflow_status": "waiting_for_user",
        "task_complete": False,
        "step_count": step_count,
    }


# ---------------------------------------------------------------------------
# Human-in-the-loop overwrite approval
# ---------------------------------------------------------------------------

def approval_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Pause the graph and request approval for an overwrite."""

    pending_action = state.get("pending_action", {})
    file_path = str(
        pending_action.get("file_path")
        or state.get("file_path", "")
    ).strip()

    user_decision = interrupt(
        {
            "type": "overwrite_confirmation",
            "message": (
                f"The file `{file_path}` already exists. "
                "Do you approve overwriting it?"
            ),
            "file_path": file_path,
            "operation": pending_action.get(
                "operation",
                state.get("file_operation", "create"),
            ),
        }
    )

    if isinstance(user_decision, bool):
        approved = user_decision
    else:
        approved = str(user_decision).strip().lower() in {
            "approve",
            "approved",
            "yes",
            "y",
            "true",
        }

    if approved:
        return {
            "requires_confirmation": False,
            "confirmation_status": "approved",
            "workflow_status": "running",
            "step_count": state.get("step_count", 0) + 1,
        }

    return {
        "requires_confirmation": False,
        "confirmation_status": "rejected",
        "pending_action": {},
        "file_result": "The overwrite operation was rejected by the user.",
        "workflow_status": "running",
        "step_count": state.get("step_count", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_executive(
    state: ResearchAssistantState,
) -> (
    str
    | list[Send]
):
    """Route the request to the required capability or capabilities."""

    if stop_reason(state):
        return "stop"

    intent = state.get("intent", "general")

    if intent == "general":
        return "general"

    if intent == "knowledge":
        return "knowledge"

    if intent == "research":
        return "research"

    if intent == "workspace":
        return "workspace"

    if intent == "research_and_save":
        return "research"

    if intent == "knowledge_and_research":
        # These independent retrieval tasks run in parallel.
        return [
            Send("knowledge", state),
            Send("research", state),
        ]

    if intent == "clarification":
        return "clarification"

    return "clarification"


def route_after_knowledge(
    state: ResearchAssistantState,
) -> str:
    """Route after personal-knowledge retrieval."""

    if stop_reason(state):
        return "stop"

    return "final_response"


def route_after_research(
    state: ResearchAssistantState,
) -> str:
    """Continue to report generation only when saving was requested."""

    if stop_reason(state):
        return "stop"

    if state.get("intent") == "research_and_save":
        return "report_generation"

    return "final_response"


def route_after_report(
    state: ResearchAssistantState,
) -> str:
    """Continue from report generation to file writing."""

    if stop_reason(state):
        return "stop"

    if not state.get("draft_report"):
        return "final_response"

    return "workspace"


def route_after_workspace(
    state: ResearchAssistantState,
) -> str:
    """Request approval when needed, otherwise produce the final response."""

    if stop_reason(state):
        return "stop"

    if state.get("requires_confirmation"):
        return "approval"

    return "final_response"


def route_after_approval(
    state: ResearchAssistantState,
) -> str:
    """Retry the file operation after approval or finish after rejection."""

    if stop_reason(state):
        return "stop"

    if state.get("confirmation_status") == "approved":
        return "workspace"

    return "final_response"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph():
    """Build and compile the Personal Research Assistant workflow."""

    workflow = StateGraph(ResearchAssistantState)

    workflow.add_node("executive", executive_node)
    workflow.add_node("general", general_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("research", research_node)
    workflow.add_node(
        "report_generation",
        report_generation_node,
    )
    workflow.add_node("workspace", workspace_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("final_response", final_response_node)
    workflow.add_node("stop", stop_node)

    workflow.add_edge(START, "executive")

    workflow.add_conditional_edges(
        "executive",
        route_after_executive,
        {
            "general": "general",
            "knowledge": "knowledge",
            "research": "research",
            "workspace": "workspace",
            "clarification": "clarification",
            "stop": "stop",
        },
    )

    workflow.add_conditional_edges(
        "knowledge",
        route_after_knowledge,
        {
            "final_response": "final_response",
            "stop": "stop",
        },
    )

    workflow.add_conditional_edges(
        "research",
        route_after_research,
        {
            "report_generation": "report_generation",
            "final_response": "final_response",
            "stop": "stop",
        },
    )

    workflow.add_conditional_edges(
        "report_generation",
        route_after_report,
        {
            "workspace": "workspace",
            "final_response": "final_response",
            "stop": "stop",
        },
    )

    workflow.add_conditional_edges(
        "workspace",
        route_after_workspace,
        {
            "approval": "approval",
            "final_response": "final_response",
            "stop": "stop",
        },
    )

    workflow.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "workspace": "workspace",
            "final_response": "final_response",
            "stop": "stop",
        },
    )

    workflow.add_edge("general", END)
    workflow.add_edge("clarification", END)
    workflow.add_edge("final_response", END)
    workflow.add_edge("stop", END)

    # In-memory checkpointing is sufficient for the first working version.
    # Each conversation is isolated using a different thread_id.
    checkpointer = MemorySaver()

    return workflow.compile(
        checkpointer=checkpointer,
    )


graph = build_graph()