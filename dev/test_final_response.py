"""Manual tests for the Final Response node."""

from pprint import pprint

from agents.general import final_response_node
from state import create_initial_state


# Change only this line.
TEST_MODE = "knowledge"
# TEST_MODE = "research"
# TEST_MODE = "saved_report"
# TEST_MODE = "confirmation"

def build_state(test_mode: str):
    """Create a completed workflow state."""

    state = create_initial_state("Test request")

    if test_mode == "knowledge":
        state.update(
            {
                "intent": "knowledge",
                "knowledge_findings": [
                    {
                        "answer": (
                            "The meeting covered LangGraph orchestration, "
                            "MCP integration, blockers, and next steps."
                        ),
                        "source": "notes/last_week_meeting.md",
                        "excerpt": "Meeting excerpt...",
                    }
                ],
                "citations": [
                    {
                        "title": "notes/last_week_meeting.md",
                        "reference": "notes/last_week_meeting.md",
                    }
                ],
            }
        )

    elif test_mode == "research":
        state.update(
            {
                "intent": "research",
                "research_findings": [
                    {
                        "summary": (
                            "The Model Context Protocol standardizes "
                            "communication between AI applications "
                            "and external tools."
                        ),
                        "facts": [],
                        "sources": [],
                    }
                ],
                "citations": [
                    {
                        "title": "Model Context Protocol",
                        "reference": (
                            "https://en.wikipedia.org/wiki/"
                            "Model_Context_Protocol"
                        ),
                        "url": (
                            "https://en.wikipedia.org/wiki/"
                            "Model_Context_Protocol"
                        ),
                    }
                ],
            }
        )

    elif test_mode == "saved_report":
        state.update(
            {
                "intent": "research_and_save",
                "saved_path": "reports/sample-report.md",
            }
        )

    elif test_mode == "confirmation":
        state.update(
            {
                "requires_confirmation": True,
                "pending_action": {
                    "file_path": "reports/sample-report.md",
                },
            }
        )

    return state


def run_test(test_mode: str):
    """Run one final-response scenario."""

    state = build_state(test_mode)

    result = final_response_node(state)

    print(f"\nScenario: {test_mode}\n")

    pprint(result, sort_dicts=False)

    print("\nDisplayed response:\n")

    print(result["final_response"])


if __name__ == "__main__":
    run_test(TEST_MODE)