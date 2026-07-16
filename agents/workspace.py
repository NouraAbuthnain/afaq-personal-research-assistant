"""Workspace Agent for safe sandboxed file operations."""

from __future__ import annotations

from typing import Any

from state import ResearchAssistantState
from tools.workspace_tools import (
    create_workspace_file,
    list_workspace_files,
    read_workspace_file,
    update_workspace_file,
)


def workspace_node(
    state: ResearchAssistantState,
) -> dict[str, Any]:
    """Perform one authorized workspace operation through MCP."""

    operation = state.get("file_operation", "none")
    file_path = state.get("file_path", "").strip()
    step_count = state.get("step_count", 0) + 1

    confirmation_status = state.get(
        "confirmation_status",
        "not_required",
    )

    content = (
        state.get("draft_report")
        or state.get("file_content", "")
    )

    try:
        if operation == "list":
            result = list_workspace_files(
                directory=file_path or ".",
                recursive=True,
            )

        elif operation == "read":
            if not file_path:
                return {
                    "errors": [
                        "A file path is required for the read operation."
                    ],
                    "error_count": state.get("error_count", 0) + 1,
                    "step_count": step_count,
                }

            result = read_workspace_file(file_path)

        elif operation == "create":
            if not file_path:
                return {
                    "errors": [
                        "A file path is required for the create operation."
                    ],
                    "error_count": state.get("error_count", 0) + 1,
                    "step_count": step_count,
                }

            if not content:
                return {
                    "errors": [
                        "No content was supplied for file creation."
                    ],
                    "error_count": state.get("error_count", 0) + 1,
                    "step_count": step_count,
                }

            overwrite_approved = (
                confirmation_status == "approved"
            )

            result = create_workspace_file(
                file_path=file_path,
                content=content,
                overwrite=overwrite_approved,
            )

        elif operation == "update":
            if not file_path:
                return {
                    "errors": [
                        "A file path is required for the update operation."
                    ],
                    "error_count": state.get("error_count", 0) + 1,
                    "step_count": step_count,
                }

            if not content:
                return {
                    "errors": [
                        "No content was supplied for the update operation."
                    ],
                    "error_count": state.get("error_count", 0) + 1,
                    "step_count": step_count,
                }

            update_approved = (
                confirmation_status == "approved"
            )

            result = update_workspace_file(
                file_path=file_path,
                content=content,
                approved=update_approved,
            )

        else:
            return {
                "errors": [
                    f"Unsupported workspace operation: {operation}"
                ],
                "error_count": state.get("error_count", 0) + 1,
                "step_count": step_count,
            }

    except Exception as error:
        return {
            "errors": [
                f"Workspace operation failed: {error}"
            ],
            "error_count": state.get("error_count", 0) + 1,
            "step_count": step_count,
        }

    status = result.get("status", "error")
    result_path = str(
        result.get("path", file_path)
    ).strip()

    if status == "confirmation_required":
        return {
            "file_exists": True,
            "path_is_safe": True,
            "requires_confirmation": True,
            "confirmation_status": "pending",
            "pending_action": {
                "operation": operation,
                "file_path": result_path,
                "content": content,
            },
            "file_result": result.get(
                "message",
                "User approval is required.",
            ),
            "workflow_status": "waiting_for_user",
            "step_count": step_count,
        }

    if status == "success":
        update: dict[str, Any] = {
            "file_result": result.get(
                "message",
                "Workspace operation completed successfully.",
            ),
            "path_is_safe": True,
            "requires_confirmation": False,
            "confirmation_status": "not_required",
            "pending_action": {},
            "step_count": step_count,
        }

        if operation in {"create", "update"}:
            update["saved_path"] = result_path
            update["file_exists"] = True

        elif operation == "read":
            update["file_content"] = result.get(
                "content",
                "",
            )
            update["file_exists"] = True

        elif operation == "list":
            update["file_result"] = result.get(
                "items",
                [],
            )

        return update

    error_message = result.get(
        "message",
        "The workspace operation failed.",
    )

    return {
        "errors": [error_message],
        "error_count": state.get("error_count", 0) + 1,
        "file_result": error_message,
        "file_exists": status != "not_found",
        "step_count": step_count,
    }