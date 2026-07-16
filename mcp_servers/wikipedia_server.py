"""MCP server exposing Wikipedia research tools."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_PAGE_URL = "https://en.wikipedia.org/wiki/"

USER_AGENT = (
    "NouraAbuthnainPersonalResearchAssistant/1.0 "
    "(educational project)"
)

REQUEST_TIMEOUT = 15
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 10
MAX_ARTICLE_CHARACTERS = 12_000


mcp = FastMCP("Wikipedia Research Server")


def request_wikipedia(
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Send one request to the Wikipedia API."""

    query_string = urlencode(parameters)
    request_url = f"{WIKIPEDIA_API_URL}?{query_string}"

    request = Request(
        request_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response_text = response.read().decode("utf-8")

    except HTTPError as error:
        raise RuntimeError(
            f"Wikipedia returned HTTP {error.code}."
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to Wikipedia: {error.reason}"
        ) from error

    except TimeoutError as error:
        raise RuntimeError(
            "The Wikipedia request timed out."
        ) from error

    try:
        return json.loads(response_text)

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Wikipedia returned an invalid JSON response."
        ) from error


@mcp.tool()
def search_wikipedia(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> str:
    """Search Wikipedia and return matching article titles."""

    normalized_query = query.strip()

    if not normalized_query:
        return json.dumps(
            {
                "status": "error",
                "message": "The search query cannot be empty.",
                "results": [],
            }
        )

    safe_limit = max(
        1,
        min(limit, MAX_SEARCH_LIMIT),
    )

    data = request_wikipedia(
        {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": normalized_query,
            "srlimit": safe_limit,
            "utf8": 1,
        }
    )

    search_results = data.get(
        "query",
        {},
    ).get(
        "search",
        [],
    )

    results = [
        {
            "title": item.get("title", ""),
            "page_id": item.get("pageid"),
            "word_count": item.get("wordcount", 0),
            "url": (
                WIKIPEDIA_PAGE_URL
                + quote(
                    item.get("title", "").replace(" ", "_")
                )
            ),
        }
        for item in search_results
        if item.get("title")
    ]

    return json.dumps(
        {
            "status": "success",
            "query": normalized_query,
            "results": results,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def fetch_wikipedia_article(title: str) -> str:
    """Read the plain-text extract of one Wikipedia article."""

    normalized_title = title.strip()

    if not normalized_title:
        return json.dumps(
            {
                "status": "error",
                "message": "The article title cannot be empty.",
            }
        )

    data = request_wikipedia(
        {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "explaintext": 1,
            "exsectionformat": "plain",
            "redirects": 1,
            "titles": normalized_title,
        }
    )

    pages = data.get(
        "query",
        {},
    ).get(
        "pages",
        {},
    )

    if not pages:
        return json.dumps(
            {
                "status": "not_found",
                "title": normalized_title,
                "message": "No Wikipedia article was found.",
            }
        )

    page = next(iter(pages.values()))

    if "missing" in page:
        return json.dumps(
            {
                "status": "not_found",
                "title": normalized_title,
                "message": "No Wikipedia article was found.",
            }
        )

    resolved_title = page.get(
        "title",
        normalized_title,
    )

    extract = page.get("extract", "").strip()

    if not extract:
        return json.dumps(
            {
                "status": "not_found",
                "title": resolved_title,
                "message": (
                    "The article did not contain readable text."
                ),
            }
        )

    return json.dumps(
        {
            "status": "success",
            "title": resolved_title,
            "url": (
                WIKIPEDIA_PAGE_URL
                + quote(resolved_title.replace(" ", "_"))
            ),
            "extract": extract[:MAX_ARTICLE_CHARACTERS],
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")