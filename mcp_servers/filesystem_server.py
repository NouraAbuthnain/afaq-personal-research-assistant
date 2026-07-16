"""Filesystem MCP server for sandboxed workspace operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from config import WORKSPACE_DIR


mcp = FastMCP("Workspace Filesystem Server")

SUPPORTED_TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".py",
    ".yaml",
    ".yml",
}

MAX_FILE_SIZE_BYTES = 1_000_000


def json_response(data: dict[str, Any]) -> str:
    """Serialize an MCP result as JSON."""

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


def resolve_workspace_path(relative_path: str) -> Path:
    """Resolve a path and ensure it remains inside the workspace."""

    normalized_path = relative_path.strip()

    if not normalized_path:
        raise ValueError("The file path cannot be empty.")

    supplied_path = Path(normalized_path)

    if supplied_path.is_absolute():
        raise ValueError(
            "Absolute paths are not allowed. "
            "Use a path relative to the workspace."
        )

    workspace_root = WORKSPACE_DIR.resolve()
    requested_path = (workspace_root / supplied_path).resolve()

    try:
        requested_path.relative_to(workspace_root)
    except ValueError as error:
        raise ValueError(
            "The requested path is outside the workspace sandbox."
        ) from error

    return requested_path


def relative_workspace_path(file_path: Path) -> str:
    """Return a normalized path relative to the workspace."""

    return file_path.relative_to(
        WORKSPACE_DIR.resolve()
    ).as_posix()


def validate_supported_file(file_path: Path) -> None:
    """Reject unsupported file types."""

    if file_path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix or 'no extension'}."
        )


@mcp.tool()
def list_files(
    directory: str = ".",
    recursive: bool = True,
) -> str:
    """List files and folders inside the workspace sandbox."""

    try:
        directory_path = resolve_workspace_path(directory)
    except ValueError as error:
        return json_response(
            {
                "status": "error",
                "operation": "list",
                "message": str(error),
                "items": [],
            }
        )

    if not directory_path.exists():
        return json_response(
            {
                "status": "not_found",
                "operation": "list",
                "path": directory,
                "message": "The requested directory does not exist.",
                "items": [],
            }
        )

    if not directory_path.is_dir():
        return json_response(
            {
                "status": "error",
                "operation": "list",
                "path": directory,
                "message": "The requested path is not a directory.",
                "items": [],
            }
        )

    iterator = (
        directory_path.rglob("*")
        if recursive
        else directory_path.iterdir()
    )

    items: list[dict[str, Any]] = []

    for item_path in sorted(iterator):
        items.append(
            {
                "path": relative_workspace_path(item_path),
                "type": (
                    "directory"
                    if item_path.is_dir()
                    else "file"
                ),
                "size_bytes": (
                    item_path.stat().st_size
                    if item_path.is_file()
                    else None
                ),
            }
        )

    return json_response(
        {
            "status": "success",
            "operation": "list",
            "path": relative_workspace_path(directory_path),
            "items": items,
        }
    )


@mcp.tool()
def read_file(file_path: str) -> str:
    """Read a supported text file from the workspace."""

    try:
        requested_path = resolve_workspace_path(file_path)
        validate_supported_file(requested_path)
    except ValueError as error:
        return json_response(
            {
                "status": "error",
                "operation": "read",
                "path": file_path,
                "message": str(error),
            }
        )

    if not requested_path.exists():
        return json_response(
            {
                "status": "not_found",
                "operation": "read",
                "path": file_path,
                "message": "The requested file does not exist.",
            }
        )

    if not requested_path.is_file():
        return json_response(
            {
                "status": "error",
                "operation": "read",
                "path": file_path,
                "message": "The requested path is not a file.",
            }
        )

    file_size = requested_path.stat().st_size

    if file_size > MAX_FILE_SIZE_BYTES:
        return json_response(
            {
                "status": "error",
                "operation": "read",
                "path": file_path,
                "message": (
                    "The file exceeds the maximum readable size."
                ),
            }
        )

    try:
        content = requested_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return json_response(
            {
                "status": "error",
                "operation": "read",
                "path": file_path,
                "message": f"Could not read the file: {error}",
            }
        )

    return json_response(
        {
            "status": "success",
            "operation": "read",
            "path": relative_workspace_path(requested_path),
            "content": content,
            "size_bytes": file_size,
        }
    )


@mcp.tool()
def create_file(
    file_path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """Create a file, refusing existing files unless overwrite is approved."""

    try:
        requested_path = resolve_workspace_path(file_path)
        validate_supported_file(requested_path)
    except ValueError as error:
        return json_response(
            {
                "status": "error",
                "operation": "create",
                "path": file_path,
                "message": str(error),
            }
        )

    if requested_path.exists() and not overwrite:
        return json_response(
            {
                "status": "confirmation_required",
                "operation": "create",
                "path": relative_workspace_path(requested_path),
                "message": (
                    "The file already exists. "
                    "User approval is required before overwriting it."
                ),
            }
        )

    try:
        requested_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        requested_path.write_text(
            content,
            encoding="utf-8",
        )
    except OSError as error:
        return json_response(
            {
                "status": "error",
                "operation": "create",
                "path": file_path,
                "message": f"Could not create the file: {error}",
            }
        )

    return json_response(
        {
            "status": "success",
            "operation": "create",
            "path": relative_workspace_path(requested_path),
            "message": "The file was created successfully.",
        }
    )


@mcp.tool()
def update_file(
    file_path: str,
    content: str,
    approved: bool = False,
) -> str:
    """Replace an existing file only after explicit approval."""

    try:
        requested_path = resolve_workspace_path(file_path)
        validate_supported_file(requested_path)
    except ValueError as error:
        return json_response(
            {
                "status": "error",
                "operation": "update",
                "path": file_path,
                "message": str(error),
            }
        )

    if not requested_path.exists():
        return json_response(
            {
                "status": "not_found",
                "operation": "update",
                "path": file_path,
                "message": "The requested file does not exist.",
            }
        )

    if not requested_path.is_file():
        return json_response(
            {
                "status": "error",
                "operation": "update",
                "path": file_path,
                "message": "The requested path is not a file.",
            }
        )

    if not approved:
        return json_response(
            {
                "status": "confirmation_required",
                "operation": "update",
                "path": relative_workspace_path(requested_path),
                "message": (
                    "User approval is required before updating "
                    "the existing file."
                ),
            }
        )

    try:
        requested_path.write_text(
            content,
            encoding="utf-8",
        )
    except OSError as error:
        return json_response(
            {
                "status": "error",
                "operation": "update",
                "path": file_path,
                "message": f"Could not update the file: {error}",
            }
        )

    return json_response(
        {
            "status": "success",
            "operation": "update",
            "path": relative_workspace_path(requested_path),
            "message": "The file was updated successfully.",
        }
    )


if __name__ == "__main__":
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    mcp.run(transport="stdio")