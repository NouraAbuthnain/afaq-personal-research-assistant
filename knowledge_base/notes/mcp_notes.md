# Model Context Protocol (MCP) — Notes

## What it is
MCP is an open standard, originally introduced by Anthropic in November 2024, for connecting AI systems (LLMs, agents) to external tools, data sources, and services through a single standardized interface. It's commonly described as "USB-C for AI applications" — one protocol that any AI app can use to plug into any compliant data source or tool, instead of every app writing a bespoke integration for every tool (the "N×M integration problem").

In December 2025, Anthropic donated MCP to the Agentic AI Foundation (AAIF), a directed fund under the Linux Foundation co-founded by Anthropic, Block, and OpenAI — making it a vendor-neutral, community-governed standard. It's since been adopted across the ecosystem, including by OpenAI and Google DeepMind.

## Architecture
Three participants:
- **Host** — the AI application the user actually interacts with (e.g., Claude Desktop, Claude Code, an IDE like Cursor or VS Code).
- **Client** — lives inside the host; each client keeps a dedicated, stateful connection to one MCP server. A single host can run multiple clients simultaneously, giving the model a unified tool surface across many servers.
- **Server** — exposes a given system's capabilities (a database, an API, a SaaS product) through the protocol.

Communication runs over JSON-RPC 2.0, over one of two transports:
- **stdio** — local subprocess communication; typical for desktop apps and local dev.
- **Streamable HTTP** — for remote, scalable server deployments.

## The three primitives a server can expose
- **Tools** — actions the model can invoke (send a message, run a query, create a record, trigger a deployment).
- **Resources** — data the model can read (files, database rows, docs).
- **Prompts** — reusable, parameterized prompt templates the server provides to the client.

A newer extension, **MCP Apps** (added under the November 2025 extensions system), lets tools return rich HTML UI that renders in a sandboxed iframe inside the chat — e.g., an interactive dashboard or a form — rather than just returning text. This was co-developed with OpenAI.

## Relationship to A2A
MCP and Google's Agent-to-Agent protocol (A2A, released April 2025) are complementary, not competitors: MCP governs how a single agent talks to its tools and data; A2A governs how separate agents delegate tasks to and communicate with each other. A typical production system uses both — e.g., an agent pulls context via MCP, then hands a sub-task to another agent via A2A.

## Adoption (as of early-mid 2026, per third-party trackers)
- Hundreds of public MCP servers exist for common tools (GitHub, Slack, Google Drive, Postgres, Notion, Jira, Stripe, Figma, and more).
- SDKs are available for Python, TypeScript, C#, Java, and Swift.
- Reported monthly SDK download figures are in the tens of millions, though exact numbers vary by source and should be treated as directional, not precise.

## Security considerations (worth taking seriously, not boilerplate)
- **Prompt injection / tool poisoning** — a compromised or malicious server can return content designed to manipulate the model into taking unintended actions or exfiltrating data through another connected tool. This has been flagged by independent security researchers as an open class of risk, not a solved problem.
- **Scoping & permissions** — the protocol itself doesn't mandate a tenant/permission model; multi-tenant SaaS providers building MCP servers need to design isolation and per-role scoping themselves.
- **Rate limiting / cost attribution** — also not defined at the protocol level; something to handle at the gateway or application layer.
- **Auditability** — log every tool call (what was invoked, with what parameters, by which agent/user) since agents can act autonomously once given tool access.

## Practical framing
Treat "expose X as an MCP server" as roughly equivalent to "write a well-scoped API wrapper around X, once, in a standard shape" — the payoff is that every MCP-compatible host/agent can use it without a bespoke integration, at the cost of needing to think through auth, scoping, and audit logging up front rather than per-integration.

## Sources
- Anthropic: "Introducing the Model Context Protocol"
- modelcontextprotocol.io official docs
- Wikipedia: Model Context Protocol (cross-checked for the AAIF donation timeline and adoption facts)
- WorkOS and DEV Community 2026 guides (cross-checked for architecture/primitives detail)
