"""Research tools that call the Wikipedia MCP server."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


DEFAULT_ARTICLE_LIMIT = 3
MAX_ARTICLE_LIMIT = 5

STOP_WORDS = {
    "a",
    "an",
    "and",
    "about",
    "for",
    "from",
    "in",
    "it",
    "look",
    "me",
    "of",
    "on",
    "please",
    "summarize",
    "summary",
    "the",
    "to",
    "up",
    "what",
}


def parse_tool_result(result: Any) -> dict[str, Any]:
    """Extract and validate JSON data from an MCP tool result."""

    if getattr(result, "isError", False):
        raise RuntimeError("The MCP tool reported an error.")

    text_parts: list[str] = []

    for content_item in getattr(result, "content", []):
        text = getattr(content_item, "text", None)

        if text:
            text_parts.append(text)

    if not text_parts:
        raise RuntimeError(
            "The MCP tool returned no readable content."
        )

    combined_text = "\n".join(text_parts)

    try:
        data = json.loads(combined_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The MCP tool returned invalid JSON."
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "The MCP tool returned an unexpected data format."
        )

    return data


def tokenize(text: str) -> set[str]:
    """Normalize text into terms used for relevance ranking."""

    tokens = re.findall(
        r"[a-zA-Z0-9]+",
        text.lower(),
    )

    return {
        token
        for token in tokens
        if len(token) > 2 and token not in STOP_WORDS
    }


def build_search_query(query: str) -> str:
    """Convert a natural-language request into a concise wiki query."""

    query_terms = tokenize(query)

    if not query_terms:
        return query.strip()

    return " ".join(sorted(query_terms))


def rank_search_results(
    search_items: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Rank Wikipedia results by similarity between query and title."""

    query_terms = tokenize(query)
    normalized_query = " ".join(query.lower().split())

    def calculate_title_score(
        item: dict[str, Any],
    ) -> tuple[int, int]:
        title = str(item.get("title", "")).strip()
        normalized_title = " ".join(title.lower().split())
        title_terms = tokenize(title)

        overlap = len(
            query_terms.intersection(title_terms)
        )

        exact_phrase_bonus = (
            10
            if normalized_title
            and normalized_title in normalized_query
            else 0
        )

        return exact_phrase_bonus + overlap, -len(title)

    return sorted(
        search_items,
        key=calculate_title_score,
        reverse=True,
    )


async def research_wikipedia_async(
    query: str,
    article_limit: int = DEFAULT_ARTICLE_LIMIT,
) -> list[dict[str, str]]:
    """Search and read relevant Wikipedia articles through MCP."""

    normalized_query = query.strip()

    if not normalized_query:
        return []

    safe_limit = max(
        1,
        min(article_limit, MAX_ARTICLE_LIMIT),
    )

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "mcp_servers.wikipedia_server",
        ],
    )

    async with stdio_client(
        server_parameters
    ) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            search_result = await session.call_tool(
                "search_wikipedia",
                {
                    "query": build_search_query(
                        normalized_query
                    ),
                    # Request additional candidates, then rank them.
                    "limit": MAX_ARTICLE_LIMIT,
                },
            )

            search_data = parse_tool_result(
                search_result
            )

            if search_data.get("status") != "success":
                return []

            raw_search_items = search_data.get(
                "results",
                [],
            )

            if not isinstance(raw_search_items, list):
                return []

            ranked_items = rank_search_results(
                search_items=raw_search_items,
                query=normalized_query,
            )

            articles: list[dict[str, str]] = []

            for search_item in ranked_items:
                if len(articles) >= safe_limit:
                    break

                if not isinstance(search_item, dict):
                    continue

                title = str(
                    search_item.get("title", "")
                ).strip()

                if not title:
                    continue

                article_result = await session.call_tool(
                    "fetch_wikipedia_article",
                    {
                        "title": title,
                    },
                )

                article_data = parse_tool_result(
                    article_result
                )

                if article_data.get("status") != "success":
                    continue

                resolved_title = str(
                    article_data.get("title", "")
                ).strip()

                url = str(
                    article_data.get("url", "")
                ).strip()

                content = str(
                    article_data.get("extract", "")
                ).strip()

                if not resolved_title or not url or not content:
                    continue

                articles.append(
                    {
                        "title": resolved_title,
                        "url": url,
                        "content": content,
                    }
                )

            return articles


async def research_multiple_wikipedia_topics_async(
    topics: list[str],
) -> list[dict[str, str]]:
    """Research several named topics through the Wikipedia MCP server."""

    cleaned_topics = [
        topic.strip()
        for topic in topics
        if topic.strip()
    ]

    if not cleaned_topics:
        return []

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "mcp_servers.wikipedia_server",
        ],
    )

    articles: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    async with stdio_client(
        server_parameters
    ) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            for topic in cleaned_topics:
                search_result = await session.call_tool(
                    "search_wikipedia",
                    {
                        "query": topic,
                        "limit": MAX_ARTICLE_LIMIT,
                    },
                )

                search_data = parse_tool_result(search_result)

                if search_data.get("status") != "success":
                    continue

                raw_items = search_data.get("results", [])

                if not isinstance(raw_items, list):
                    continue

                ranked_items = rank_search_results(
                    search_items=raw_items,
                    query=topic,
                )

                selected_article: dict[str, str] | None = None

                for item in ranked_items:
                    if not isinstance(item, dict):
                        continue

                    title = str(
                        item.get("title", "")
                    ).strip()

                    if not title:
                        continue

                    article_result = await session.call_tool(
                        "fetch_wikipedia_article",
                        {
                            "title": title,
                        },
                    )

                    article_data = parse_tool_result(
                        article_result
                    )

                    if article_data.get("status") != "success":
                        continue

                    resolved_title = str(
                        article_data.get("title", "")
                    ).strip()

                    url = str(
                        article_data.get("url", "")
                    ).strip()

                    content = str(
                        article_data.get("extract", "")
                    ).strip()

                    if not resolved_title or not url or not content:
                        continue

                    if url in seen_urls:
                        continue

                    selected_article = {
                        "title": resolved_title,
                        "url": url,
                        "content": content,
                    }
                    break

                if selected_article:
                    seen_urls.add(selected_article["url"])
                    articles.append(selected_article)

    return articles


def research_wikipedia(
    query: str,
    article_limit: int = DEFAULT_ARTICLE_LIMIT,
) -> list[dict[str, str]]:
    """Run Wikipedia research from synchronous application code."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            research_wikipedia_async(
                query=query,
                article_limit=article_limit,
            )
        )

    raise RuntimeError(
        "research_wikipedia() cannot run inside an active async event loop. "
        "Use 'await research_wikipedia_async(...)' instead."
    )

def research_multiple_wikipedia_topics(
    topics: list[str],
) -> list[dict[str, str]]:
    """Run multi-topic Wikipedia research synchronously."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            research_multiple_wikipedia_topics_async(
                topics
            )
        )

    raise RuntimeError(
        "research_multiple_wikipedia_topics() cannot run "
        "inside an active async event loop."
    )