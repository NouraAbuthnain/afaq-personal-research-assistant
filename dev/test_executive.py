from pprint import pprint

import agents.executive
from agents.executive import executive_node, extract_explicit_file_path
from state import create_initial_state


request = (
    "Research the top three vector databases and save a "
    "comparison report to reports/vector-dbs.md."
)

print("Loaded from:", agents.executive.__file__)
print("Extracted path:", repr(extract_explicit_file_path(request)))

state = create_initial_state(request)
result = executive_node(state)

pprint(result, sort_dicts=False)