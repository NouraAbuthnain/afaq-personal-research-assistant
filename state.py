"""Shared state and message schemas for the Personal Research Assistant."""

from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Typed communication between agents
# ---------------------------------------------------------------------------
AgentName = Literal[
    "executive",
    "knowledge",
    "research",
    "workspace",
    "report_generation",
]

MessageType = Literal["request", "response", "handoff", "error"]


class AgentMessage(BaseModel):
    """Typed envelope used for communication between system components."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: AgentName
    recipient: AgentName
    type: MessageType
    payload: dict[str, Any]
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# LangGraph shared state
# ---------------------------------------------------------------------------
Intent = Literal[
    "general",
    "knowledge",
    "research",
    "workspace",
    "knowledge_and_research",
    "research_and_save",
    "clarification",
]

RouteName = Literal[
    "general",
    "knowledge",
    "research",
    "workspace",
    "report_generation",
    "final_response",
]

FileOperation = Literal[
    "none",
    "list",
    "read",
    "create",
    "update",
]

ConfirmationStatus = Literal[
    "not_required",
    "pending",
    "approved",
    "rejected",
]

WorkflowStatus = Literal[
    "running",
    "waiting_for_user",
    "completed",
    "failed",
]


class ResearchAssistantState(TypedDict, total=False):
    """Shared data read and updated by LangGraph nodes."""

    # User conversation
    messages: Annotated[list[BaseMessage], add_messages]
    user_request: str

    # Typed agent-to-agent communication
    agent_messages: Annotated[list[AgentMessage], operator.add]

    # Executive Agent: classification, planning, and routing
    intent: Intent
    plan: list[str]
    selected_routes: list[RouteName]
    next_step: RouteName
    clarification_question: str

    # Knowledge Agent outputs
    knowledge_query: str
    knowledge_findings: Annotated[list[dict[str, Any]], operator.add]

    # Research Agent outputs
    research_query: str
    research_findings: Annotated[list[dict[str, Any]], operator.add]

    # Sources from both retrieval agents
    citations: Annotated[list[dict[str, str]], operator.add]

    # Report Generation capability
    report_requested: bool
    requested_format: str
    draft_report: str

    # Workspace Agent and sandboxed file operations
    file_operation: FileOperation
    file_path: str
    file_content: str
    file_exists: bool
    path_is_safe: bool
    file_result: str
    saved_path: str

    # Human-in-the-loop
    requires_confirmation: bool
    confirmation_status: ConfirmationStatus
    pending_action: dict[str, Any]

    # Execution control and stop conditions
    workflow_status: WorkflowStatus
    step_count: int
    max_steps: int
    error_count: int
    max_errors: int
    errors: Annotated[list[str], operator.add]
    task_complete: bool

    # Final user-facing answer
    final_response: str


def create_initial_state(user_request: str) -> ResearchAssistantState:
    """Create a clean state for one user request."""

    return {
        "messages": [HumanMessage(content=user_request)],
        "user_request": user_request,
        "agent_messages": [],

        "intent": "general",
        "plan": [],
        "selected_routes": [],
        "next_step": "general",
        "clarification_question": "",

        "knowledge_query": "",
        "knowledge_findings": [],

        "research_query": "",
        "research_findings": [],

        "citations": [],

        "report_requested": False,
        "requested_format": "markdown",
        "draft_report": "",

        "file_operation": "none",
        "file_path": "",
        "file_content": "",
        "file_exists": False,
        "path_is_safe": False,
        "file_result": "",
        "saved_path": "",

        "requires_confirmation": False,
        "confirmation_status": "not_required",
        "pending_action": {},

        "workflow_status": "running",
        "step_count": 0,
        "max_steps": 10,
        "error_count": 0,
        "max_errors": 3,
        "errors": [],
        "task_complete": False,

        "final_response": "",
    }