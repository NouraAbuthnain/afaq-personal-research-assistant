"""Manual tests for the General Assistant and final-response nodes."""

from pprint import pprint

from agents.general import general_node, final_response_node
from state import create_initial_state


# Change only this line.
REQUEST = "Hello! What can you help me with?"


def test_general_response(request: str) -> None:
    """Test a general conversational request."""

    state = create_initial_state(request)
    state["intent"] = "general"

    result = general_node(state)

    print("\nGeneral Assistant result:")
    pprint(result, sort_dicts=False)

    print("\nDisplayed response:\n")
    print(result.get("final_response", ""))


if __name__ == "__main__":
    test_general_response(REQUEST)