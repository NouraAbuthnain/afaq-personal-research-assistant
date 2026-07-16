"""Manual test for the Research Agent."""

from pprint import pprint

from agents.research import research_node
from state import create_initial_state


# Change only this line.
REQUEST = (
    "Look up the Model Context Protocol "
    "and summarize it for me."
)


def run_test(request: str) -> None:
    """Run one reusable Research Agent test."""

    state = create_initial_state(request)

    # The Executive Agent normally creates this field.
    # We set it directly while testing the Research Agent.
    state["research_query"] = request

    result = research_node(state)

    pprint(result, sort_dicts=False)


if __name__ == "__main__":
    run_test(REQUEST)