# Team Sync — Project Atlas
**Date:** Tuesday, July 8, 2026
**Attendees:** Sara (lead), Omar (backend), Priya (ML), Yusuf (infra)
**Absent:** Lina (PTO)

## Agenda
1. Retrieval pipeline status
2. Agent orchestration approach
3. MCP integration for internal tools
4. Blockers & next steps

## Notes

### 1. Retrieval pipeline status
- Priya reported the chunking + embedding pipeline is passing eval on the internal doc set (~92% top-5 recall on the test queries).
- Current embedding model: staying with the existing provider for now; revisit only if recall drops on the next eval batch.
- Open question: should we move from the current Postgres/pgvector setup to a dedicated vector DB once we cross ~5M chunks? Priya to benchmark query latency at current scale before deciding.

### 2. Agent orchestration approach
- Omar walked through a prototype using LangGraph for the multi-step research agent (search → summarize → validate → retry-if-invalid).
- Team agreed LangGraph's explicit state graph model fits better than a simple chain, mainly because we need human-approval checkpoints before the agent writes back to any external system.
- Decision (tentative, to confirm in writing): use LangGraph as the orchestration layer for v1. See `project_decisions.md`.

### 3. MCP integration for internal tools
- Yusuf proposed exposing our internal ticketing system and the docs search API as MCP servers instead of writing bespoke tool-calling code for each.
- Discussed security concerns: need to scope tool permissions per agent role, and log every tool call for audit purposes.
- Action: Yusuf to spike a minimal MCP server for the ticketing system by next sync.

### 4. Blockers & next steps
- Priya blocked on getting read access to the new eval dataset (Sara to follow up with data team).
- Omar needs a decision on checkpoint storage (in-memory vs. Postgres) before finishing the LangGraph prototype — leaning Postgres for durability.
- Next sync: **Tuesday, July 15, 2026**, focus on reviewing the MCP server spike and finalizing the checkpoint storage decision.

## Action Items
| Owner | Item | Due |
|---|---|---|
| Sara | Follow up on eval dataset access | Jul 10 |
| Priya | Benchmark pgvector latency at current scale | Jul 14 |
| Omar | Finish LangGraph prototype w/ Postgres checkpointing | Jul 15 |
| Yusuf | Spike MCP server for ticketing system | Jul 15 |
