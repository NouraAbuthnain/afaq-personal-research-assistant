# LangGraph — Notes

## What it is
LangGraph is an open-source Python/TypeScript library from LangChain Inc. for building stateful, multi-step AI agents as graphs, rather than as linear chains. It's positioned as the lower-level orchestration engine in the LangChain ecosystem — as of 2026, LangChain's own agent abstractions run on top of the LangGraph runtime. It's independent of LangChain proper, but interoperates with LangChain's model and tool abstractions. Both the Python and JS packages are MIT-licensed.

## Core primitives

- **State** — a shared object (typically defined as a TypedDict) that flows through the whole graph. Every node reads it and returns updates that get merged back in. This is effectively the agent's memory for a given run.
- **Nodes** — plain functions that do the actual work: call an LLM, run a tool, transform data. A node takes the current state and returns an update.
- **Edges** — define what runs next. Two kinds:
  - *Normal edges*: always go from node A to node B.
  - *Conditional edges*: a routing function inspects the state and picks the next node dynamically — this is what enables branching and retry loops.
- **StateGraph** — the builder class. You construct it with a state schema, add nodes and edges, set an entry point (`START`) and exit (`END`), then call `.compile()` to get a runnable graph.
- **Checkpointers** — persistence adapters (in-memory, SQLite, Postgres) that save state after each node runs. This is what makes a graph resumable across restarts and lets you implement "time travel" debugging.
- **Interrupts** — a built-in mechanism to pause execution before/after a given node so a human can approve, edit, or reject before the graph continues. This is the primary building block for human-in-the-loop workflows.

## Execution model
Under the hood, LangGraph uses a message-passing model inspired by Google's Pregel system. Execution proceeds in discrete "super-steps" — nodes that fire in parallel belong to the same super-step, sequential nodes belong to separate super-steps. A node is inactive until it receives a new state update on an incoming edge, at which point it "activates," runs, and passes its output onward.

Because the graph can cycle (a node can route back to an earlier node), LangGraph handles patterns that plain chains can't: retry-until-valid loops, iterative self-correction, multi-turn tool use, etc.

## Nodes returning `Command`
Instead of only returning a state update, a node/tool can return a `Command` object that bundles a state update *and* a routing instruction (`goto`) in one step. Useful when the next-node decision depends on data only known inside the tool call itself. Note: a node should use either static conditional edges or `Command`-based dynamic routing — not both.

## When to reach for it (vs. alternatives)
- **LangGraph** — best when you need arbitrary graph topology, durable state, human-in-the-loop gates, or fine-grained control over transitions.
- **CrewAI** — more opinionated, role/task-based; faster to prototype, harder to customize deeply.
- **AutoGen** — strongest for conversational multi-agent setups where agents talk to each other in natural language rather than through explicit graph edges.
- Plain function-calling loop — fine for simple, single-agent tool use with no need for persistence or approval gates.

## Production notes
- Package split: `langgraph` (core runtime), `langgraph-checkpoint` (persistence adapters), `langgraph-sdk` (client for the hosted LangGraph Platform).
- Common production pitfalls: graphs that never reach `END` (usually a routing/tool-condition bug), infinite loops (mitigate with a step counter in state + a max-steps conditional edge), and checkpoint schema drift when the state shape changes mid-project (use a fresh `thread_id` or a migration script).
- Design nodes to be idempotent where they have side effects (DB writes, API calls) — a resumed run may re-execute a node, so duplicate writes need to be guarded against (upserts, idempotency keys, read-before-write).
- LangChain Inc. also offers a paid hosted product (LangSmith Deployment, formerly "LangGraph Platform") for managed deployment and observability on top of the open-source library.

## Sources
- LangChain official docs — Graph API overview
- IBM: "What is LangGraph?"
- Multiple third-party 2026 guides/reviews (Atlan, ToolBrain, Latenode, FutureAGI) cross-checked for consistency on architecture and adoption claims
