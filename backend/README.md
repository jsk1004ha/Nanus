# Nanus backend

Real execution layer for the Nanus UI prototype.

## Run locally

```bash
npm run backend:setup
npm run dev:full
```

`dev:full` starts FastAPI on `127.0.0.1:8765` and Vite with backend mode enabled. Vite dev proxies `/api`, `/ws`, and `/mcp` to the backend. For a separately hosted frontend, set `VITE_NANUS_API_BASE` to the backend origin and set `NANUS_CORS_ORIGINS` on the backend to the frontend origin(s).
Runtime knobs are documented in `.env.example`.

## Runtime behavior

- `POST /api/runs` persists a queued run, enqueues a durable background job, and returns immediately.
- `POST /api/chat` creates a conversation-backed user message, assistant message placeholder, and linked run.
- `GET /api/conversations` and `GET /api/conversations/{id}/messages` expose durable chat history independently of run events.
- `GET /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/artifacts`, and `GET /api/runs/{id}/events` read persisted data.
- `GET /api/runs/{id}/events?after=<seq>` returns append-only events after a known event id.
- `WS /ws/run/{id}` subscribes to persisted events only; it does not trigger execution.
- Execution now emits an explicit agent phase loop: `Planner -> Tool Executor -> Verifier -> Artifact Handoff`. Progress is derived from run steps instead of the previous fixed `34 -> 56 -> 82 -> 100` sequence.
- `POST /api/runs/{id}/pause`, `/resume`, and `/cancel` update run/job state and append audit events.
- `/api/tools`, `/api/mcp/tools`, and `/mcp` expose Python skill/tool/Codex connections.
- `/deck-from-brief` runs a Python skill and emits `outline` + `pptx` artifacts.
- `/writing-advice` handles report/writing expansion requests without forcing them into the deck pipeline.
- If `ANTHROPIC_API_KEY` is set, Anthropic Messages API is used; without it, deterministic fallback output keeps local tests offline and repeatable, and the run is marked degraded rather than silently successful.
- LLM output budget is controlled by `NANUS_ANTHROPIC_MAX_TOKENS` and defaults to 4096 rather than the old 800-token ceiling.
- Codex bridge is deterministic fallback by default; set `NANUS_CODEX_ENABLED=true` to opt into local `codex exec`.
- `NANUS_CODEX_SANDBOX=read-only` is the default live sandbox; use `workspace-write` only when you explicitly want Codex to edit the workspace.
- Optional Codex knobs: `CODEX_EXECUTABLE`, `NANUS_CODEX_WORKDIR`, `NANUS_CODEX_TIMEOUT`, `NANUS_CODEX_MODEL`.

## Test

```bash
npm run backend:test
npm run backend:test:pytest
```

Both commands run the same `tests/backend` pytest suite; the second name is kept as an explicit alias.
