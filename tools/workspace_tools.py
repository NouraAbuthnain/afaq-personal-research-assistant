"""Client tools for calling the Filesystem MCP server."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def parse_tool_result(result: Any) -> dict[str, Any]:
    """Extract JSON data from an MCP tool result."""

    if getattr(result, "isError", False):
        raise RuntimeError(
            "The Filesystem MCP tool reported an error."
        )

    text_parts: list[str] = []

    for content_item in getattr(result, "content", []):
        text = getattr(content_item, "text", None)

        if text:
            text_parts.append(text)

    if not text_parts:
        raise RuntimeError(
            "The Filesystem MCP tool returned no readable content."
        )

    try:
        data = json.loads("\n".join(text_parts))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The Filesystem MCP tool returned invalid JSON."
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "The Filesystem MCP tool returned an unexpected format."
        )

    return data


async def call_filesystem_tool_async(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call one tool from the Filesystem MCP server."""

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "mcp_servers.filesystem_server",
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

            result = await session.call_tool(
                tool_name,
                arguments,
            )

            return parse_tool_result(result)


def call_filesystem_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call a filesystem MCP tool from synchronous code."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            call_filesystem_tool_async(
                tool_name=tool_name,
                arguments=arguments,
            )
        )

    raise RuntimeError(
        "call_filesystem_tool() cannot run inside an active "
        "async event loop."
    )


def list_workspace_files(
    directory: str = ".",
    recursive: bool = True,
) -> dict[str, Any]:
    """List workspace contents."""

    return call_filesystem_tool(
        "list_files",
        {
            "directory": directory,
            "recursive": recursive,
        },
    )


def read_workspace_file(
    file_path: str,
) -> dict[str, Any]:
    """Read one workspace file."""

    return call_filesystem_tool(
        "read_file",
        {
            "file_path": file_path,
        },
    )


def create_workspace_file(
    file_path: str,
    content: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a workspace file."""

    return call_filesystem_tool(
        "create_file",
        {
            "file_path": file_path,
            "content": content,
            "overwrite": overwrite,
        },
    )


def update_workspace_file(
    file_path: str,
    content: str,
    approved: bool = False,
) -> dict[str, Any]:
    """Update a workspace file."""

    return call_filesystem_tool(
        "update_file",
        {
            "file_path": file_path,
            "content": content,
            "approved": approved,
        },
    )