# Context Snapshot: SuperAgent with Claude Code and Codex Workers

Created: 2026-06-30T00:32:58Z
Workspace: `C:\Users\js100\Desktop\coding\Nanus`

## Task Statement

Design a Manus-like autonomous agent system assembled from open-source and local/cloud components, with explicit support for connecting Claude Code and OpenAI Codex as execution workers.

The user supplied two architecture images:

- SuperAgent layered architecture: UI, orchestration, execution, memory, MCP tools, observability/eval, model layer.
- Manus feature mapping to open-source components: LangGraph/CrewAI, browser-use/Playwright, OpenHands/E2B, OWL/Firecrawl, mem0/Zep, MCP/A2A, model-agnostic foundation layer.

## Desired Outcome

Produce a durable implementation plan that can become the first build target for Nanus:

1. A realistic architecture diagram and component breakdown.
2. A first MVP scope that connects Codex and Claude Code without overbuilding the full platform.
3. A Worker Adapter contract for Claude Code, Codex, future OpenHands/browser/research agents, and external A2A agents.
4. Security and sandboxing rules that keep user data, credentials, and filesystem access controlled.
5. Testable acceptance criteria and verification path.

## Known Local Facts

- Repository is effectively empty except `LICENSE` and `.omx/` runtime files.
- `codex` is installed locally: `codex-cli 0.117.0`.
- Local `codex exec --help` confirms support for `--json`, `--sandbox read-only|workspace-write|danger-full-access`, `--output-schema`, `--output-last-message`, `resume`, `--ephemeral`, `--cd`, and `--skip-git-repo-check`.
- Local `codex app-server --help` confirms experimental app-server support over `stdio://` or `ws://IP:PORT`, plus WebSocket auth modes for non-loopback listeners.
- `claude` command is not currently installed or not on `PATH`.
- Docker is installed: Docker 29.5.3.
- Node.js is installed: v22.16.0.
- Python is installed: 3.13.12.

## External Evidence Used

- Claude Code CLI supports non-interactive `-p`, JSON/stream JSON output, `--max-turns`, `--mcp-config`, permission mode, custom system prompt, background sessions, worktrees, and MCP configuration.
  Source: https://code.claude.com/docs/en/cli-reference
- Claude Agent SDK provides Python and TypeScript programmatic access to Claude Code-like agent loops and built-in tools for reading files, running commands, and editing code.
  Source: https://code.claude.com/docs/en/agent-sdk/overview
- Codex non-interactive mode supports `codex exec`, JSONL event streaming, output schema, sandbox settings, resume, and safer automation guidance.
  Source: https://developers.openai.com/codex/noninteractive
- Codex SDK provides TypeScript and Python libraries to control local Codex agents and threads; Python uses the app-server over JSON-RPC.
  Source: https://developers.openai.com/codex/sdk
- Codex app-server supports JSON-RPC over stdio, WebSocket, and Unix socket; WebSocket is experimental and should not be remotely exposed without auth.
  Source: https://developers.openai.com/codex/app-server
- LangGraph persistence supports thread-scoped checkpoints and cross-thread stores, which is suitable for long-running/resumable agent workflows.
  Source: https://docs.langchain.com/oss/python/langgraph/persistence
- CrewAI crews model collaborative groups of agents, tasks, sequential/hierarchical processes, memory, callbacks, planning, and MCP integration.
  Source: https://docs.crewai.com/en/concepts/crews
- A2A defines Agent Cards for discovery, JSON-RPC task/message communication, and transport-level auth rather than embedding identity in payloads.
  Source: https://a2a-protocol.org/latest/specification/
- MCP is the standard tool integration layer for exposing external tools and context to agents.
  Source: https://modelcontextprotocol.io/docs/getting-started/intro
- E2B provides isolated sandboxes and has documented paths for Claude Code and Codex in sandboxed agent execution.
  Source: https://e2b.dev/docs

## Constraints

- Planning mode only: no application source code should be generated in this ralplan session.
- Start local-first and model-agnostic.
- Do not put API keys into persistent process environments or logs.
- Treat Claude Code/Codex as execution workers behind an adapter, not as unbounded controllers of the whole platform.
- MVP must remain small enough to implement and test before adding browser automation, OWL, OpenHands, mem0/Zep, or full A2A marketplace behavior.
- First implementation stack is TypeScript-first for the control plane and shared schemas, with Python sidecars allowed later only where an SDK or runtime is materially better in Python.
- State authority must be explicit: LangGraph checkpoints own control-flow recovery, the run ledger owns append-only operator/audit truth, and memory is advisory-only during MVP.
- No real write-capable worker run is allowed before the system creates an isolated workspace/worktree, freezes a per-run policy snapshot, and redacts events before persistence/streaming.

## Unknowns / Open Questions

- Whether Claude Code should be installed via CLI or only accessed via Claude Agent SDK. The plan supports both.
- Whether cloud sandboxes such as E2B should be mandatory in MVP or optional after local Docker/worktree execution works.

## Likely Codebase Touchpoints

The repository has no app code yet. The first execution lane should scaffold:

- `apps/api`: orchestration API and run/event endpoints.
- `apps/web`: operational web UI.
- `packages/agent-core`: task/run model, adapter contract, event schema.
- `packages/workers-codex`: Codex adapter.
- `packages/workers-claude`: Claude adapter.
- `packages/sandbox`: local worktree/Docker/E2B sandbox providers.
- `packages/mcp-gateway`: MCP registry and policy bridge.
- `docs/architecture`: diagrams, ADRs, threat model.
