# Project Atlas — Decisions Log

Format: one entry per decision, most recent first. Each entry records the decision, the reasoning, and who owns follow-through.

---

## D-004: Use LangGraph for agent orchestration
**Date:** 2026-07-08
**Status:** Confirmed
**Owner:** Omar

**Decision:** Build the v1 research agent on LangGraph rather than a simpler chain-based approach or a role-based framework like CrewAI.

**Reasoning:**
- We need explicit human-in-the-loop approval gates before the agent writes to external systems — this is a first-class feature in LangGraph rather than something bolted on.
- The workflow has genuine loops (search → summarize → validate → retry), which fits a graph/state-machine model better than a linear chain.
- We need durable state (checkpointing) so a long-running agent run can survive a restart and be resumed or replayed.

**Alternatives considered:** CrewAI (rejected — too opinionated about role-based flows for our approval-gate requirement), plain function-calling loop (rejected — no persistence, no built-in interrupt mechanism).

---

## D-003: Expose internal tools via MCP servers
**Date:** 2026-07-08
**Status:** Confirmed, implementation in progress
**Owner:** Yusuf

**Decision:** Wrap the internal ticketing system and docs search API as MCP servers rather than writing custom tool-calling integrations per agent.

**Reasoning:**
- Avoids duplicating integration code across every agent/host that needs the same tools (the N×M integration problem MCP was designed to solve).
- Standard interface means we can swap which LLM/host is driving the agent without rewriting tool code.
- Tenant/permission scoping and audit logging need to be handled at the server level regardless of approach, so there's no real cost to standardizing now.

**Follow-up needed:** Define our internal policy for per-role tool scoping before any MCP server is exposed outside the dev environment.

---

## D-002: Stay on pgvector for retrieval, revisit at scale
**Date:** 2026-07-08
**Status:** Confirmed, revisit trigger set
**Owner:** Priya

**Decision:** Keep the retrieval layer on Postgres + pgvector rather than migrating to a dedicated vector database (e.g., Qdrant, Milvus) for now.

**Reasoning:**
- Current corpus size doesn't yet justify the operational overhead of a separate vector DB.
- Keeping vectors alongside relational data simplifies joins with user/document metadata and keeps us on infrastructure we already operate.
- Revisit trigger: if the corpus crosses ~5M chunks, or query latency at current scale is already poor (pending Priya's benchmark), re-evaluate a dedicated vector DB with HNSW indexing.

---

## D-001: Checkpoint storage for LangGraph — Postgres over in-memory
**Date:** 2026-07-08
**Status:** Confirmed
**Owner:** Omar

**Decision:** Use Postgres-backed checkpointing for the LangGraph agent instead of in-memory checkpointing, even for the v1 prototype.

**Reasoning:** In-memory checkpointing doesn't survive a process restart, and we already expect to need resumable runs for the human-approval workflow. Starting with Postgres avoids a migration later and lets us test the real persistence path early.
