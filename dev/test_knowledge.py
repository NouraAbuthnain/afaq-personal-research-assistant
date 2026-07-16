"""Manual test for the Knowledge Agent."""

from pprint import pprint

from agents.knowledge import knowledge_node
from state import create_initial_state

# ------------------------------------------------------------------
# Change only this line when testing
# ------------------------------------------------------------------
REQUEST = "What is in my note about last week's meeting?"
# ------------------------------------------------------------------


def run_test(request: str) -> None:
    """Run one Knowledge Agent test."""

    state = create_initial_state(request)

    # The Executive Agent normally fills this.
    # Since we're testing the Knowledge Agent directly,
    # we simulate what the Executive Agent would produce.
    state["knowledge_query"] = request

    result = knowledge_node(state)

    pprint(result, sort_dicts=False)


if __name__ == "__main__":
    run_test(REQUEST)