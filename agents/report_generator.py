"""Report-generation capability for structured research reports."""

from __future__ import annotations

from typing import Any, Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import OPENAI_MODEL, validate_config
from prompts.system_prompts import REPORT_GENERATION_PROMPT
from state import ResearchAssistantState


class ReportSection(BaseModel):
    """One structured section in a generated report."""

    heading: str
    content: str


class GeneratedReport(BaseModel):
    """Structured output produced by the report generator."""

    status: Literal["completed", "insufficient_evidence"]
    title: str
    introduction: str
    sections: list[ReportSection] = Field(default_factory=list)
    conclusion: str
    source_references: list[str] = Field(default_factory=list)


validate_config()

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
)

report_llm = llm.with_structured_output(GeneratedReport)


def format_report_as_markdown(report: GeneratedReport) -> str:
    """Convert a structured report into Markdown."""

    parts: list[str] = [
        f"# {report.title.strip()}",
        "",
        report.introduction.strip(),
    ]

    for section in report.sections:
        heading = section.heading.strip()
        content = section.content.strip()

        if not heading or not content:
            continue

        parts.extend(
            [
                "",
                f"## {heading}",
                "",
                content,
            ]
        )

    if report.conclusion.strip():
        parts.extend(
            [
                "",
                "## Conclusion",
                "",
                report.conclusion.strip(),
            ]
        )

    valid_references = [
        reference.strip()
        for reference in report.source_references
        if reference.strip()
    ]

    if valid_references:
        parts.extend(
            [
                "",
                "## Sources",
                "",
            ]
        )

        for index, reference in enumerate(
            valid_references,
            start=1,
        ):
            parts.append(f"{index}. {reference}")

    return "\n".join(parts).strip() + "\n"


def format_report_as_text(report: GeneratedReport) -> str:
    """Convert a structured report into plain text."""

    parts: list[str] = [
        report.title.strip(),
        "=" * len(report.title.strip()),
        "",
        report.introduction.strip(),
    ]

    for section in report.sections:
        heading = section.heading.strip()
        content = section.content.strip()

        if not heading or not content:
            continue

        parts.extend(
            [
                "",
                heading,
                "-" * len(heading),
                content,
            ]
        )

    if report.conclusion.strip():
        parts.extend(
            [
                "",
                "Conclusion",
                "----------",
                report.conclusion.strip(),
            ]
        )

    valid_references = [
        reference.strip()
        for reference in report.source_references
        if reference.strip()
    ]

    if valid_references:
        parts.extend(
            [
                "",
                "Sources",
                "-------",
            ]
        )

        for index, reference in enumerate(
            valid_references,
            start=1,
        ):
            parts.append(f"{index}. {reference}")

    return "\n".join(parts).strip() + "\n"


def collect_research_evidence(
    state: ResearchAssistantState,
) -> tuple[str, list[str]]:
    """Collect grounded research findings and verified source references."""

    research_findings = state.get("research_findings", [])
    citations = state.get("citations", [])

    evidence_parts: list[str] = []

    for finding_group in research_findings:
        if not isinstance(finding_group, dict):
            continue

        summary = str(
            finding_group.get("summary", "")
        ).strip()

        if summary:
            evidence_parts.append(
                f"Research summary:\n{summary}"
            )

        facts = finding_group.get("facts", [])

        if isinstance(facts, list):
            for fact_item in facts:
                if not isinstance(fact_item, dict):
                    continue

                fact = str(
                    fact_item.get("fact", "")
                ).strip()

                source_title = str(
                    fact_item.get("source_title", "")
                ).strip()

                source_url = str(
                    fact_item.get("source_url", "")
                ).strip()

                if not fact:
                    continue

                evidence_parts.append(
                    (
                        f"Fact: {fact}\n"
                        f"Source title: {source_title}\n"
                        f"Source URL: {source_url}"
                    )
                )

    verified_references: list[str] = []
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

        if not reference:
            continue

        formatted_reference = (
            f"{title} — {reference}"
            if title
            else reference
        )

        if formatted_reference in seen_references:
            continue

        seen_references.add(formatted_reference)
        verified_references.append(formatted_reference)

    return "\n\n".join(evidence_parts), verified_references


def report_generation_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Generate a clean report from grounded research findings."""

    step_count = state.get("step_count", 0) + 1
    requested_format = (
        state.get("requested_format", "markdown")
        .strip()
        .lower()
    )

    evidence, verified_references = collect_research_evidence(
        state
    )

    if not evidence:
        return {
            "errors": [
                "Report Generation received no research findings."
            ],
            "error_count": state.get("error_count", 0) + 1,
            "draft_report": "",
            "step_count": step_count,
        }

    user_request = state.get("user_request", "").strip()
    research_query = state.get("research_query", "").strip()

    try:
        generated_report = report_llm.invoke(
            [
                {
                    "role": "system",
                    "content": REPORT_GENERATION_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Original user request:\n{user_request}\n\n"
                        f"Research topic:\n{research_query}\n\n"
                        f"Requested format:\n{requested_format}\n\n"
                        "Verified source references:\n"
                        + "\n".join(verified_references)
                        + "\n\n"
                        "Grounded research evidence:\n"
                        + evidence
                    ),
                },
            ]
        )

    except Exception as error:
        return {
            "errors": [
                f"Report Generation failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "draft_report": "",
            "step_count": step_count,
        }

    # Never trust model-generated references.
    generated_report.source_references = verified_references

    if generated_report.status == "insufficient_evidence":
        return {
            "errors": [
                "The available research was insufficient "
                "to generate the requested report."
            ],
            "error_count": state.get("error_count", 0) + 1,
            "draft_report": "",
            "step_count": step_count,
        }

    if requested_format in {"txt", "text", "plain_text"}:
        draft_report = format_report_as_text(
            generated_report
        )
        normalized_format = "text"

    else:
        draft_report = format_report_as_markdown(
            generated_report
        )
        normalized_format = "markdown"

    return {
        "draft_report": draft_report,
        "requested_format": normalized_format,
        "step_count": step_count,
    }