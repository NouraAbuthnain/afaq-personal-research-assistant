"""Reusable test for report generation and workspace saving."""

from pprint import pprint

from agents.executive import executive_node
from agents.report_generator import report_generation_node
from agents.research import research_node
from agents.workspace import workspace_node
from state import create_initial_state


# Change only this request.
REQUEST = (
    "Research and compare Linux, Microsoft Windows, and macOS "
    "in terms of target users, software ecosystem, security, "
    "customization, strengths, and limitations, then prepare "
    "a Markdown report for reports/operating-systems-comparison.md."
)


def run_test(request: str) -> None:
    """Run the complete research-and-save workflow manually."""

    state = create_initial_state(request)

    executive_update = executive_node(state)
    state.update(executive_update)

    print("\nExecutive result:")
    pprint(executive_update, sort_dicts=False)

    if executive_update.get("intent") == "clarification":
        return

    research_update = research_node(state)
    state.update(research_update)

    print("\nResearch result:")
    pprint(research_update, sort_dicts=False)

    if research_update.get("errors"):
        return

    report_update = report_generation_node(state)
    state.update(report_update)

    print("\nReport result:")
    pprint(report_update, sort_dicts=False)

    if not state.get("draft_report"):
        return

    workspace_update = workspace_node(state)
    state.update(workspace_update)

    print("\nWorkspace result:")
    pprint(workspace_update, sort_dicts=False)

    if state.get("requires_confirmation"):
        print(
            "\nThe file already exists. "
            "Simulating user approval..."
        )

        state["confirmation_status"] = "approved"
        state["requires_confirmation"] = False

        workspace_update = workspace_node(state)
        state.update(workspace_update)

        print("\nWorkspace result after approval:")
        pprint(workspace_update, sort_dicts=False)

    if state.get("saved_path"):
        print(
            f"\nSuccess: report saved to "
            f"workspace/{state['saved_path']}"
        )


if __name__ == "__main__":
    run_test(REQUEST)