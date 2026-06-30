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

- `POST /api/runs` persists a run to SQLite.
- `GET /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/artifacts`, and `GET /api/runs/{id}/events` read persisted data.
- `WS /ws/run/{id}` streams run snapshots, artifact events, and `run.done`.
- `/api/tools`, `/api/mcp/tools`, and `/mcp` expose Python skill/tool/Codex connections.
- `/deck-from-brief` runs a Python skill and emits `outline` + `pptx` artifacts.
- If `ANTHROPIC_API_KEY` is set, Anthropic Messages API is used; without it, deterministic fallback output keeps local tests offline and repeatable.
- Codex bridge is deterministic fallback by default; set `NANUS_CODEX_ENABLED=true` to opt into local `codex exec`.
- `NANUS_CODEX_SANDBOX=read-only` is the default live sandbox; use `workspace-write` only when you explicitly want Codex to edit the workspace.
- Optional Codex knobs: `CODEX_EXECUTABLE`, `NANUS_CODEX_WORKDIR`, `NANUS_CODEX_TIMEOUT`, `NANUS_CODEX_MODEL`.

## Test

```bash
npm run backend:test
npm run backend:test:pytest
```

Both commands run the same `tests/backend` pytest suite; the second name is kept as an explicit alias.
