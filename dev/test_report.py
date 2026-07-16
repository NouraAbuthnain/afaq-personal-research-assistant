from pprint import pprint

from agents.executive import executive_node
from agents.research import research_node
from agents.report_generator import report_generation_node
from state import create_initial_state


# Change only this line.
REQUEST = (
    "Research and compare PostgreSQL, MySQL, and MongoDB "
    "in terms of database model, scalability, typical use cases, "
    "advantages, and limitations, then prepare a Markdown report "
    "for reports/database-comparison.md."
)


def run_test(request: str) -> None:
    state = create_initial_state(request)

    # Executive Agent
    state.update(executive_node(state))

    print("\nExecutive result:")
    pprint(state, sort_dicts=False)

    # Research Agent
    state.update(research_node(state))

    print("\nResearch result:")
    pprint(state["research_findings"], sort_dicts=False)

    # Report Generator
    state.update(report_generation_node(state))

    print("\nGenerated report:\n")
    print(state.get("draft_report", ""))


if __name__ == "__main__":
    run_test(REQUEST)