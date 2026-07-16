"""Local tools for searching and reading the user's knowledge base."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from config import KNOWLEDGE_BASE_DIR


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

DEFAULT_MAX_RESULTS = 3
MAX_EXCERPT_LENGTH = 1200
MAX_PDF_PAGES = 100

STOP_WORDS = {
    "a",
    "an",
    "and",
    "about",
    "are",
    "article",
    "document",
    "for",
    "from",
    "in",
    "is",
    "it",
    "me",
    "my",
    "note",
    "notes",
    "of",
    "on",
    "say",
    "says",
    "the",
    "to",
    "what",
    "with",
}


def tokenize(text: str) -> set[str]:
    """Normalize text into searchable terms."""

    normalized_text = text.lower()

    normalized_text = normalized_text.replace("_", " ")
    normalized_text = normalized_text.replace("-", " ")
    normalized_text = normalized_text.replace("\\", " ")
    normalized_text = normalized_text.replace("/", " ")

    # Convert "week's" to "week".
    normalized_text = re.sub(r"'s\b", "", normalized_text)

    tokens = re.findall(r"[a-zA-Z0-9]+", normalized_text)

    return {
        token
        for token in tokens
        if len(token) > 2 and token not in STOP_WORDS
    }


def read_pdf_text(file_path: Path) -> str:
    """Extract searchable text from a digital PDF."""

    try:
        reader = PdfReader(str(file_path))
    except Exception as error:
        raise ValueError(
            f"Could not open PDF: {file_path.name}"
        ) from error

    page_texts: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        if page_number > MAX_PDF_PAGES:
            break

        try:
            text = page.extract_text() or ""
        except Exception:
            # One unreadable page should not reject the entire PDF.
            continue

        cleaned_text = text.strip()

        if cleaned_text:
            page_texts.append(
                f"[Page {page_number}]\n{cleaned_text}"
            )

    if not page_texts:
        raise ValueError(
            f"No extractable text was found in {file_path.name}. "
            "The PDF may be scanned or image-based."
        )

    return "\n\n".join(page_texts)


def read_document_text(file_path: Path) -> str:
    """Read a supported knowledge-base document."""

    extension = file_path.suffix.lower()

    if extension in {".md", ".txt"}:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"Could not decode document: {file_path.name}"
            ) from error

    if extension == ".pdf":
        return read_pdf_text(file_path)

    raise ValueError(
        f"Unsupported knowledge file type: {extension}"
    )


def calculate_relevance(
    query: str,
    content: str,
    filename: str,
) -> int:
    """Score a document using filename and content matches."""

    query_terms = tokenize(query)

    if not query_terms:
        return 0

    content_terms = tokenize(content)
    filename_terms = tokenize(filename)

    content_matches = query_terms.intersection(content_terms)
    filename_matches = query_terms.intersection(filename_terms)

    score = len(content_matches)
    score += len(filename_matches) * 4

    combined_terms = content_terms.union(filename_terms)

    if query_terms.issubset(combined_terms):
        score += 5

    return score


def split_into_chunks(
    content: str,
    max_chunk_length: int = 1800,
) -> list[str]:
    """Split a document into searchable text chunks."""

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", content)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)

        if current_parts and (
            current_length + paragraph_length > max_chunk_length
        ):
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_length = 0

        # Handle one unusually large paragraph.
        if paragraph_length > max_chunk_length:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_length = 0

            for start in range(
                0,
                paragraph_length,
                max_chunk_length,
            ):
                chunks.append(
                    paragraph[start : start + max_chunk_length]
                )

            continue

        current_parts.append(paragraph)
        current_length += paragraph_length + 2

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def create_excerpt(
    content: str,
    query: str,
) -> str:
    """Return the most relevant excerpt from one document."""

    cleaned_content = content.strip()

    if not cleaned_content:
        return ""

    chunks = split_into_chunks(cleaned_content)
    query_terms = tokenize(query)

    ranked_chunks = sorted(
        chunks,
        key=lambda chunk: len(
            query_terms.intersection(tokenize(chunk))
        ),
        reverse=True,
    )

    if not ranked_chunks:
        return cleaned_content[:MAX_EXCERPT_LENGTH]

    excerpt = ranked_chunks[0]

    if len(excerpt) > MAX_EXCERPT_LENGTH:
        excerpt = (
            excerpt[:MAX_EXCERPT_LENGTH].rstrip()
            + "..."
        )

    return excerpt


def search_knowledge(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """Search notes, text documents, and PDFs."""

    normalized_query = query.strip()

    if not normalized_query:
        return []

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    results: list[dict[str, Any]] = []

    for file_path in KNOWLEDGE_BASE_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            content = read_document_text(file_path)
        except (OSError, ValueError):
            continue

        if not content.strip():
            continue

        relative_path = file_path.relative_to(
            KNOWLEDGE_BASE_DIR
        )

        source = relative_path.as_posix()

        relevance_score = calculate_relevance(
            query=normalized_query,
            content=content,
            filename=source,
        )

        if relevance_score <= 0:
            continue

        results.append(
            {
                "source": source,
                "score": relevance_score,
                "excerpt": create_excerpt(
                    content=content,
                    query=normalized_query,
                ),
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:max_results]


def read_knowledge_item(
    relative_path: str,
) -> dict[str, str]:
    """Safely read one document from the knowledge base."""

    knowledge_root = KNOWLEDGE_BASE_DIR.resolve()
    requested_path = (
        knowledge_root / relative_path
    ).resolve()

    try:
        requested_path.relative_to(knowledge_root)
    except ValueError as error:
        raise ValueError(
            "Knowledge paths must remain inside knowledge_base."
        ) from error

    if not requested_path.exists():
        raise FileNotFoundError(
            f"Knowledge item not found: {relative_path}"
        )

    if not requested_path.is_file():
        raise ValueError(
            f"Knowledge item is not a file: {relative_path}"
        )

    if requested_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported knowledge file type: "
            f"{requested_path.suffix}"
        )

    content = read_document_text(requested_path)

    return {
        "source": requested_path.relative_to(
            knowledge_root
        ).as_posix(),
        "content": content,
    }