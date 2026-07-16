"""General Assistant and final-response nodes."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from config import OPENAI_MODEL, validate_config
from prompts.system_prompts import FINAL_RESPONSE_PROMPT
from state import ResearchAssistantState


validate_config()

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
)


def general_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Answer general questions and simple conversational requests."""

    user_request = state.get("user_request", "").strip()
    step_count = state.get("step_count", 0) + 1

    if not user_request:
        return {
            "final_response": "What would you like help with?",
            "task_complete": True,
            "workflow_status": "completed",
            "step_count": step_count,
        }

    try:
        response = llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You are the friendly user-facing assistant "
                        "of a Personal Research Assistant system. "
                        "Answer general questions and conversational "
                        "requests clearly and concisely. Do not claim "
                        "to have searched notes, the web, or files "
                        "unless those tools were actually used."
                    ),
                },
                {
                    "role": "user",
                    "content": user_request,
                },
            ]
        )

        answer = str(response.content).strip()

    except Exception as error:
        return {
            "errors": [
                f"General Assistant failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "workflow_status": "failed",
            "step_count": step_count,
        }

    return {
        "messages": [AIMessage(content=answer)],
        "final_response": answer,
        "task_complete": True,
        "workflow_status": "completed",
        "step_count": step_count,
    }


def build_citation_text(
    citations: list[dict[str, str]],
) -> str:
    """Format deduplicated citations for the final response."""

    formatted_sources: list[str] = []
    seen_references: set[str] = set()

    for citation in citations:
        if not isinstance(citation, dict):
            continue

        title = str(
            citation.get("title", "")
        ).strip()

        reference = str(
            citation.get("url")
            or citation.get("reference")
            or ""
        ).strip()

        if not reference or reference in seen_references:
            continue

        seen_references.add(reference)

        if title:
            formatted_sources.append(
                f"- {title}: {reference}"
            )
        else:
            formatted_sources.append(
                f"- {reference}"
            )

    if not formatted_sources:
        return ""

    return "Sources:\n" + "\n".join(formatted_sources)


def final_response_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Create the final response from completed workflow results."""

    step_count = state.get("step_count", 0) + 1

    if state.get("requires_confirmation"):
        pending_action = state.get("pending_action", {})
        pending_path = str(
            pending_action.get("file_path")
            or state.get("file_path", "")
        ).strip()

        answer = (
            f"The file `{pending_path}` already exists. "
            "Do you approve overwriting it?"
        )

        return {
            "messages": [AIMessage(content=answer)],
            "final_response": answer,
            "workflow_status": "waiting_for_user",
            "task_complete": False,
            "step_count": step_count,
        }

    if state.get("errors"):
        error_text = "\n".join(
            f"- {error}"
            for error in state["errors"]
        )

        answer = (
            "I could not complete the request:\n"
            f"{error_text}"
        )

        return {
            "messages": [AIMessage(content=answer)],
            "final_response": answer,
            "workflow_status": "failed",
            "task_complete": False,
            "step_count": step_count,
        }

    intent = state.get("intent", "general")
    response_parts: list[str] = []

    if intent in {"knowledge", "knowledge_and_research"}:
        knowledge_findings = state.get(
            "knowledge_findings",
            [],
        )

        knowledge_answers = [
            str(item.get("answer", "")).strip()
            for item in knowledge_findings
            if isinstance(item, dict)
            and str(item.get("answer", "")).strip()
        ]

        if knowledge_answers:
            response_parts.append(
                "\n\n".join(
                    dict.fromkeys(knowledge_answers)
                )
            )

    if intent in {
        "research",
        "knowledge_and_research",
        "research_and_save",
    }:
        research_findings = state.get(
            "research_findings",
            [],
        )

        research_summaries = [
            str(item.get("summary", "")).strip()
            for item in research_findings
            if isinstance(item, dict)
            and str(item.get("summary", "")).strip()
        ]

        if (
            research_summaries
            and intent != "research_and_save"
        ):
            response_parts.append(
                "\n\n".join(
                    dict.fromkeys(research_summaries)
                )
            )

    saved_path = state.get("saved_path", "").strip()

    if saved_path:
        response_parts.append(
            f"The report was saved successfully to "
            f"`workspace/{saved_path}`."
        )

    file_operation = state.get(
        "file_operation",
        "none",
    )

    if file_operation == "read":
        file_content = state.get(
            "file_content",
            "",
        ).strip()

        if file_content:
            response_parts.append(
                f"File contents:\n\n{file_content}"
            )

    if file_operation == "list":
        file_result = state.get("file_result", [])

        if isinstance(file_result, list):
            if file_result:
                listed_paths = [
                    f"- {item.get('path', '')}"
                    for item in file_result
                    if isinstance(item, dict)
                    and item.get("path")
                ]

                response_parts.append(
                    "Workspace items:\n"
                    + "\n".join(listed_paths)
                )
            else:
                response_parts.append(
                    "The requested workspace folder is empty."
                )

    citation_text = build_citation_text(
        state.get("citations", [])
    )

    if citation_text:
        response_parts.append(citation_text)

    if not response_parts:
        response_parts.append(
            "The request was completed successfully."
        )

    grounded_content = "\n\n".join(response_parts)

    try:
        response = llm.invoke(
            [
                {
                    "role": "system",
                    "content": FINAL_RESPONSE_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        "Original user request:\n"
                        f"{state.get('user_request', '')}\n\n"
                        "Verified completed results:\n"
                        f"{grounded_content}\n\n"
                        "Rewrite these results into one concise "
                        "final response. Preserve citations and "
                        "the exact saved path."
                    ),
                },
            ]
        )

        answer = str(response.content).strip()

    except Exception:
        # Safe fallback: return verified content directly.
        answer = grounded_content

    return {
        "messages": [AIMessage(content=answer)],
        "final_response": answer,
        "task_complete": True,
        "workflow_status": "completed",
        "step_count": step_count,
    }