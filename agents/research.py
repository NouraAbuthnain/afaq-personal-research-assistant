"""Research Agent for grounded external Wikipedia research."""

from __future__ import annotations

from typing import Any, Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import OPENAI_MODEL, validate_config
from prompts.system_prompts import RESEARCH_AGENT_PROMPT
from state import ResearchAssistantState
from tools.research_tools import (
    research_multiple_wikipedia_topics,
    research_wikipedia,
)


class ResearchPlan(BaseModel):
    """Structured plan describing how the request should be researched."""

    mode: Literal["single_topic", "comparison"]
    topics: list[str] = Field(default_factory=list)
    comparison_criteria: list[str] = Field(default_factory=list)


class ResearchFinding(BaseModel):
    """One externally sourced research finding."""

    fact: str
    source_title: str
    source_url: str


class ResearchResponse(BaseModel):
    """Structured output produced by the Research Agent."""

    status: Literal["answered", "not_found"]
    summary: str
    findings: list[ResearchFinding] = Field(default_factory=list)


validate_config()

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
)

research_planner_llm = llm.with_structured_output(ResearchPlan)

research_llm = llm.with_structured_output(ResearchResponse)


def create_research_plan(query: str) -> ResearchPlan:
    """Create a reusable research plan from the user's request."""

    return research_planner_llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Create a research plan for the user's request.\n"
                    "\n"
                    "Rules:\n"
                    "- Use mode='single_topic' when the request concerns "
                    "one main subject.\n"
                    "- Use mode='comparison' when the user explicitly names "
                    "two or more subjects to compare.\n"
                    "- For comparison mode, copy only the subjects explicitly "
                    "named by the user.\n"
                    "- Extract comparison criteria when the user states them.\n"
                    "- Do not invent products, organizations, technologies, "
                    "or ranking candidates.\n"
                    "- When the user asks for top or best options without "
                    "naming candidates, keep mode='single_topic' and use the "
                    "full request as the research topic.\n"
                    "- Keep topic names short and suitable for Wikipedia "
                    "search."
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ]
    )


def build_research_instructions(
    query: str,
    plan: ResearchPlan,
) -> str:
    """Create synthesis instructions from the research plan."""

    if plan.mode == "comparison":
        topics_text = ", ".join(plan.topics)
        criteria_text = (
            ", ".join(plan.comparison_criteria)
            if plan.comparison_criteria
            else "the information supported by the supplied sources"
        )

        return (
            f"Original request: {query}\n"
            f"Comparison subjects: {topics_text}\n"
            f"Comparison criteria: {criteria_text}\n\n"
            "Compare the subjects consistently. Do not claim that one is "
            "universally best unless the evidence explicitly supports it."
        )

    topic = plan.topics[0] if plan.topics else query

    return (
        f"Original request: {query}\n"
        f"Main research topic: {topic}\n\n"
        "Provide a concise summary of the most relevant supported facts."
    )


def research_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Research Wikipedia and return grounded, sourced findings."""

    query = (
        state.get("research_query")
        or state.get("user_request", "")
    ).strip()

    step_count = state.get("step_count", 0) + 1

    if not query:
        return {
            "errors": [
                "The Research Agent received an empty query."
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    try:
        plan = create_research_plan(query)
    except Exception as error:
        return {
            "errors": [
                f"Research planning failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    cleaned_topics = list(
        dict.fromkeys(
            topic.strip()
            for topic in plan.topics
            if topic.strip()
        )
    )

    try:
        if plan.mode == "comparison" and len(cleaned_topics) >= 2:
            retrieved_articles = research_multiple_wikipedia_topics(
                cleaned_topics
            )
        else:
            search_query = (
                cleaned_topics[0]
                if cleaned_topics
                else query
            )

            retrieved_articles = research_wikipedia(
                query=search_query,
                article_limit=3,
            )

    except Exception as error:
        return {
            "errors": [
                f"External research failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    if not retrieved_articles:
        return {
            "research_findings": [
                {
                    "summary": (
                        "I could not find relevant Wikipedia "
                        "articles for this request."
                    ),
                    "facts": [],
                    "sources": [],
                    "research_mode": plan.mode,
                    "topics": cleaned_topics,
                }
            ],
            "citations": [],
            "step_count": step_count,
        }

    evidence_parts: list[str] = []

    for article in retrieved_articles:
        title = str(article.get("title", "")).strip()
        url = str(article.get("url", "")).strip()
        content = str(article.get("content", "")).strip()

        if not title or not url or not content:
            continue

        evidence_parts.append(
            (
                f"[SOURCE TITLE: {title}]\n"
                f"[SOURCE URL: {url}]\n"
                f"{content}"
            )
        )

    if not evidence_parts:
        return {
            "research_findings": [
                {
                    "summary": (
                        "Wikipedia results were found, but they did not "
                        "contain readable article evidence."
                    ),
                    "facts": [],
                    "sources": [],
                    "research_mode": plan.mode,
                    "topics": cleaned_topics,
                }
            ],
            "citations": [],
            "step_count": step_count,
        }

    evidence = "\n\n---\n\n".join(evidence_parts)

    research_instructions = build_research_instructions(
        query=query,
        plan=plan,
    )

    try:
        response = research_llm.invoke(
            [
                {
                    "role": "system",
                    "content": RESEARCH_AGENT_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"{research_instructions}\n\n"
                        "Use only the external evidence below.\n"
                        "Copy source titles and URLs exactly as supplied.\n"
                        "Every factual finding must be supported by one of "
                        "the supplied sources.\n\n"
                        f"{evidence}"
                    ),
                },
            ]
        )

    except Exception as error:
        return {
            "errors": [
                f"Research Agent failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    valid_sources = {
        article["url"]: article
        for article in retrieved_articles
        if article.get("url")
    }

    grounded_facts: list[dict[str, str]] = []
    citations_by_url: dict[str, dict[str, str]] = {}

    for finding in response.findings:
        source_url = finding.source_url.strip()
        source_article = valid_sources.get(source_url)

        if source_article is None:
            continue

        fact = finding.fact.strip()

        if not fact:
            continue

        source_title = str(
            source_article.get("title", "")
        ).strip()

        grounded_facts.append(
            {
                "fact": fact,
                "source_title": source_title,
                "source_url": source_url,
            }
        )

        citations_by_url[source_url] = {
            "title": source_title,
            "reference": source_url,
            "url": source_url,
        }

    summary = response.summary.strip()

    if not summary:
        summary = (
            "Relevant external information was found, "
            "but no summary was generated."
        )

    if not grounded_facts:
        top_article = retrieved_articles[0]
        top_url = str(top_article.get("url", "")).strip()
        top_title = str(top_article.get("title", "")).strip()

        if top_url:
            citations_by_url[top_url] = {
                "title": top_title,
                "reference": top_url,
                "url": top_url,
            }

    return {
        "research_findings": [
            {
                "summary": summary,
                "facts": grounded_facts,
                "sources": list(citations_by_url.values()),
                "research_mode": plan.mode,
                "topics": cleaned_topics,
                "comparison_criteria": plan.comparison_criteria,
            }
        ],
        "citations": list(citations_by_url.values()),
        "step_count": step_count,
    }