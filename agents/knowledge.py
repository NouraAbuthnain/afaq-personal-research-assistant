"""Knowledge Agent for grounded personal-document retrieval."""

from __future__ import annotations

from typing import Any, Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import OPENAI_MODEL, validate_config
from prompts.system_prompts import KNOWLEDGE_AGENT_PROMPT
from state import ResearchAssistantState
from tools.knowledge_tools import search_knowledge


class KnowledgeResponse(BaseModel):
    """Structured output produced by the Knowledge Agent."""

    status: Literal["answered", "not_found"]
    answer: str
    sources: list[str] = Field(default_factory=list)


validate_config()

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
)

knowledge_llm = llm.with_structured_output(KnowledgeResponse)


def knowledge_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Retrieve personal knowledge and return cited findings."""

    query = (
        state.get("knowledge_query")
        or state.get("user_request", "")
    ).strip()

    step_count = state.get("step_count", 0) + 1

    if not query:
        return {
            "errors": [
                "The Knowledge Agent received an empty query."
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    retrieved_items = search_knowledge(query)

    if not retrieved_items:
        return {
            "knowledge_findings": [
                {
                    "answer": (
                        "I could not find relevant information "
                        "in the personal knowledge base."
                    ),
                    "source": "",
                    "excerpt": "",
                }
            ],
            "citations": [],
            "step_count": step_count,
        }

    evidence = "\n\n".join(
        (
            f"[SOURCE: {item['source']}]\n"
            f"{item['excerpt']}"
        )
        for item in retrieved_items
    )

    try:
        response = knowledge_llm.invoke(
            [
                {
                    "role": "system",
                    "content": KNOWLEDGE_AGENT_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{query}\n\n"
                        "Answer using only the evidence below.\n"
                        "In the sources field, copy each source path "
                        "exactly as written inside [SOURCE: ...].\n\n"
                        f"{evidence}"
                    ),
                },
            ]
        )
    except Exception as error:
        return {
            "errors": [
                f"Knowledge Agent failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    valid_sources = {
        item["source"]: item
        for item in retrieved_items
    }

    selected_sources = [
        source.strip()
        for source in response.sources
        if source.strip() in valid_sources
    ]

    if not selected_sources:
        selected_sources = [retrieved_items[0]["source"]]

    answer = response.answer.strip()

    if not answer:
        answer = (
            "I found relevant information in the personal "
            "knowledge base, but could not generate a summary."
        )

    knowledge_findings = [
        {
            "answer": answer,
            "source": source,
            "excerpt": valid_sources[source]["excerpt"],
        }
        for source in selected_sources
    ]

    citations = [
        {
            "title": source,
            "reference": source,
            "excerpt": valid_sources[source]["excerpt"],
        }
        for source in selected_sources
    ]

    return {
        "knowledge_findings": knowledge_findings,
        "citations": citations,
        "step_count": step_count,
    }