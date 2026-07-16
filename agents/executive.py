"""Executive Agent for request classification and routing."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import OPENAI_MODEL, validate_config
from prompts.system_prompts import EXECUTIVE_AGENT_PROMPT
from state import ResearchAssistantState


class RoutingDecision(BaseModel):
    """Structured routing decision produced by the Executive Agent."""

    intent: Literal[
        "general",
        "knowledge",
        "research",
        "workspace",
        "knowledge_and_research",
        "research_and_save",
        "clarification",
    ]

    selected_routes: list[
        Literal["general", "knowledge", "research", "workspace"]
    ] = Field(default_factory=list)

    plan: list[str] = Field(default_factory=list)

    knowledge_query: str = ""
    research_query: str = ""

    file_operation: Literal[
        "none",
        "list",
        "read",
        "create",
        "update",
    ] = "none"

    file_path: str = ""
    report_requested: bool = False
    requested_format: str = "markdown"
    clarification_question: str = ""


validate_config()

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
)

router_llm = llm.with_structured_output(RoutingDecision)


def extract_explicit_file_path(user_request: str) -> str:
    """Extract a file path explicitly written by the user."""

    patterns = [
        r"`([^`]+\.(?:md|txt|json))`",
        r"\b([\w\-./\\]+\.(?:md|txt|json))\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_request, flags=re.IGNORECASE)

        if match:
            return match.group(1).replace("\\", "/").strip()

    return ""


def infer_format(file_path: str) -> str:
    """Infer the requested report format from the file extension."""

    extension = PurePosixPath(file_path).suffix.lower()

    formats = {
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
    }

    return formats.get(extension, "markdown")


def clarification_result(
    *,
    question: str,
    step_count: int,
    research_query: str = "",
) -> dict:
    """Return a standardized clarification state update."""

    return {
        "intent": "clarification",
        "selected_routes": [],
        "plan": [],
        "research_query": research_query,
        "file_operation": "none",
        "file_path": "",
        "report_requested": False,
        "clarification_question": question,
        "workflow_status": "waiting_for_user",
        "step_count": step_count,
    }


def executive_node(state: ResearchAssistantState) -> dict:
    """Classify the request and create a validated execution plan."""

    user_request = state.get("user_request", "").strip()
    step_count = state.get("step_count", 0) + 1

    if not user_request:
        return clarification_result(
            question="What would you like me to do?",
            step_count=step_count,
        )

    decision = router_llm.invoke(
        [
            {
                "role": "system",
                "content": EXECUTIVE_AGENT_PROMPT,
            },
            {
                "role": "user",
                "content": user_request,
            },
        ]
    )

    explicit_file_path = extract_explicit_file_path(user_request)

    # Normalize model outputs.
    decision.knowledge_query = decision.knowledge_query.strip()
    decision.research_query = decision.research_query.strip()
    decision.clarification_question = (
        decision.clarification_question.strip()
    )

    # Never trust an LLM-generated file path.
    decision.file_path = explicit_file_path

    # Deterministic routing.
    if decision.intent == "general":
        selected_routes = ["general"]

    elif decision.intent == "knowledge":
        selected_routes = ["knowledge"]

    elif decision.intent == "research":
        selected_routes = ["research"]

    elif decision.intent == "workspace":
        selected_routes = ["workspace"]

    elif decision.intent == "knowledge_and_research":
        selected_routes = ["knowledge", "research"]

    elif decision.intent == "research_and_save":
        selected_routes = ["research", "workspace"]
        decision.report_requested = True
        decision.file_operation = "create"

    else:
        selected_routes = []

    # Validate knowledge requests.
    if decision.intent == "knowledge" and not decision.knowledge_query:
        return clarification_result(
            question="What topic should I search for in your notes?",
            step_count=step_count,
        )

    # Validate research requests.
    if (
        decision.intent
        in {
            "research",
            "knowledge_and_research",
            "research_and_save",
        }
        and not decision.research_query
    ):
        return clarification_result(
            question="What topic would you like me to research?",
            step_count=step_count,
        )

    # Validate direct workspace requests.
    if decision.intent == "workspace":
        operation_requires_path = decision.file_operation in {
            "read",
            "create",
            "update",
        }

        if operation_requires_path and not explicit_file_path:
            return clarification_result(
                question="Which workspace file path should I use?",
                step_count=step_count,
            )

    # Validate research-and-save requests.
    if decision.intent == "research_and_save":
        if not explicit_file_path:
            return clarification_result(
                question=(
                    "Where should I save the report? "
                    "For example: reports/langgraph.md"
                ),
                step_count=step_count,
                research_query=decision.research_query,
            )

        decision.requested_format = infer_format(explicit_file_path)

    # Handle model-requested clarification.
    if decision.intent == "clarification":
        return clarification_result(
            question=(
                decision.clarification_question
                or "Could you provide more details about your request?"
            ),
            step_count=step_count,
        )

    return {
        "intent": decision.intent,
        "selected_routes": selected_routes,
        "plan": decision.plan,
        "knowledge_query": decision.knowledge_query,
        "research_query": decision.research_query,
        "file_operation": decision.file_operation,
        "file_path": decision.file_path,
        "report_requested": decision.report_requested,
        "requested_format": decision.requested_format,
        "clarification_question": "",
        "workflow_status": "running",
        "step_count": step_count,
    }