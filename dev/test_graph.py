"""Reusable end-to-end test for the complete LangGraph workflow."""

from pprint import pprint
from uuid import uuid4

from langgraph.types import Command

from graph import graph
from state import create_initial_state


# Change only this request.
# REQUEST = (
#     "Look up the Model Context Protocol and summarize it for me."
# )

# REQUEST = "What is in my note about last week's meeting?"

REQUEST = (
    "Research and compare Linux, Microsoft Windows, and macOS "
    "in terms of target users, software ecosystem, security, "
    "customization, strengths, and limitations, then prepare "
    "a Markdown report for reports/os-graph-test.md."
)


def run_graph_test(request: str) -> None:
    """Run one complete graph request."""

    thread_id = f"test-{uuid4()}"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = create_initial_state(request)

    result = graph.invoke(
        initial_state,
        config=config,
    )

    print("\nGraph result:")
    pprint(result, sort_dicts=False)

    print("\nFinal response:\n")
    print(result.get("final_response", ""))

    # Detect a LangGraph interrupt.
    snapshot = graph.get_state(config)

    if snapshot.next:
        print("\nThe graph is paused.")
        print("Next node(s):", snapshot.next)

        user_answer = input(
            "Approve the pending overwrite? (yes/no): "
        ).strip()

        resumed_result = graph.invoke(
            Command(resume=user_answer),
            config=config,
        )

        print("\nResumed result:")
        pprint(resumed_result, sort_dicts=False)

        print("\nFinal response after resume:\n")
        print(
            resumed_result.get(
                "final_response",
                "",
            )
        )


if __name__ == "__main__":
    run_graph_test(REQUEST)