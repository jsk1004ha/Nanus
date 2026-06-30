# Test Spec: Nanus SuperAgent Claude/Codex MVP

Created: 2026-06-30T00:32:58Z
Status: Ralplan consensus approved
RALPLAN-DR mode: Deliberate.

## Success Definition

Nanus is ready for the first implementation milestone when it can accept a task, dispatch it to a controlled Codex or Claude worker adapter, stream normalized events, persist artifacts, enforce sandbox/tool policy, and verify or explain the run outcome.

## Test Layers

### Unit Tests

1. Worker adapter contract
   - `capabilities()` returns stable worker metadata.
   - `health()` returns `ok`, `missing_binary`, `auth_missing`, or `unsupported_version`.
   - `startRun()` emits ordered events for success, failure, timeout, and cancellation.
   - `startRun()` requires an immutable `RunPolicy` snapshot.
   - Every emitted event has `run_id`, `worker_id`, `sequence`, `timestamp`, `event_type`, and `redaction_status`.
   - Persisted JSONL fixtures, API responses, and WebSocket/SSE streams use canonical `snake_case`.
   - Any TypeScript camelCase helper is verified through an explicit mapper test and never becomes the persisted schema.
   - `collectArtifacts()` returns final response and patch/log artifacts.
   - Artifact metadata includes worker ID, run ID, source event ID, checksum, and redaction status.

2. Codex parser
   - Parses `thread.started`, `turn.started`, `item.started`, `item.completed`, `turn.completed`, `turn.failed`, and `error` from JSONL.
   - Converts command execution, file change, MCP call, reasoning, and final message items into normalized `WorkerEvent`.
   - Ignores unknown event types without crashing and records an `adapter.warning`.

3. Claude parser
   - Parses `stream-json` output fixtures.
   - Converts assistant messages, tool events, partial messages, hook events, and final output into normalized `WorkerEvent`.
   - Handles missing `claude` binary as `worker.failed` with reason `missing_binary`, not an unhandled exception.

4. Redaction
   - Redacts `OPENAI_API_KEY`, `CODEX_API_KEY`, `ANTHROPIC_API_KEY`, bearer tokens, GitHub tokens, and common `.env` patterns from events and artifacts.
   - Redaction runs before persistence and before UI streaming.

5. Policy engine
   - Read-only sandbox denies write-capable task requests.
   - Workspace-write sandbox allows writes only inside the selected worktree/workspace.
   - Full access is rejected unless run profile is explicitly marked disposable.
   - Network mode is explicit and defaults to `deny`.
   - `RunPolicy` cannot be modified after dispatch.
   - Required MCP server failure aborts the run.

6. State authority
   - Run ledger reconstructs operator-visible state after restart.
   - LangGraph checkpoint is used only to select the next legal orchestration transition.
   - If ledger and checkpoint disagree, the run moves to `manual_recovery_required`.
   - Memory is disabled or advisory-only and cannot change worker selection or sandbox policy in MVP.

### Integration Tests

1. Codex local smoke
   - Precondition: `codex` exists and auth is configured.
   - Run: `codex exec --json --sandbox read-only "summarize this repository in 3 bullets"`.
   - Expected: normalized events include worker start, final message, usage/turn completion if available, and no file changes.

2. Codex workspace-write fixture
   - Precondition: fixture git repository.
   - Run a bounded task that edits a known fixture file.
   - Expected: patch artifact exists, modified paths stay inside fixture workspace, and verification command runs.

3. Claude health
   - If `claude` is absent, health endpoint returns `missing_binary` and setup instructions.
   - If `claude` is present, run a read-only print-mode task with JSON or stream-json output and normalize events.

4. API run lifecycle
   - `POST /tasks` creates a task.
   - `GET /tasks/:id` returns current state.
   - `GET /runs/:id/events` streams or returns event history.
   - Cancellation endpoint stops an active worker and persists `worker.cancelled`.

5. Persistence
   - Start a task, stop API process, restart API, and verify task/run/event state is recoverable.
   - Verify event ordering is stable by `run_id`, sequence number, and timestamp.
   - Corrupt or stale orchestration checkpoint while preserving run ledger.
   - Expected: API still shows ledger truth and blocks automatic continuation until manual recovery.
   - In Phase 1, replay `.nanus/runs/<runId>/events.jsonl` and reconstruct terminal run state without Postgres.

6. MCP config
   - Run a worker with a strict MCP config containing one allowed test server.
   - Simulate required server startup failure.
   - Expected: run fails early with a clear policy event.

### E2E Tests

1. Operational task E2E
   - Submit: "Inspect this repo and list the files that define the agent adapter contract."
   - Expected: task completes with final artifact, event stream visible, no unexpected file changes, and verification result recorded.

2. Controlled edit E2E
   - Submit a task against a fixture repo to update a README line.
   - Expected: patch artifact, diff preview, human approval gate before applying to main workspace, verification command result.

3. Manual recovery E2E
   - Create a run with a valid ledger and intentionally stale orchestration checkpoint.
   - Expected: run enters `manual_recovery_required`, worker dispatch is frozen, and operator actions are limited to mark failed, resume from selected ledger event, retry in a new run, or archive with notes.

4. Missing dependency E2E
   - Disable or remove `claude` from `PATH`.
   - Submit a Claude-targeted task.
   - Expected: no crash; UI/API reports `missing_binary` and suggests install/configuration path.

5. Secret safety E2E
   - Inject fake secrets into a per-run environment.
   - Worker echoes environment intentionally in a fixture.
   - Expected: persisted and streamed logs contain redacted values only.

## Observability Requirements

- Each run has a trace ID.
- Each worker event has `run_id`, `worker_id`, `sequence`, `timestamp`, `event_type`, and redaction status.
- Tool calls, command executions, file changes, policy decisions, and verification steps are visible in the run ledger.
- Failed runs include exit code, reason, bounded stderr excerpt, and next recommended action.

## Acceptance Criteria Matrix

| Requirement | Test Evidence |
| --- | --- |
| Codex worker connection | Codex local smoke and parser fixtures pass. |
| Claude worker connection | Health check passes or returns `missing_binary`; parser fixtures pass. |
| Controlled filesystem writes | Workspace-write fixture and sandbox policy tests pass. |
| Event normalization | Adapter contract and parser unit tests pass. |
| Run persistence | Dev ledger replay and persistence integration tests pass. |
| State authority | Ledger/checkpoint conflict and manual recovery tests pass. |
| Tool policy | MCP config integration test passes. |
| Secret safety | Redaction unit and secret safety E2E pass. |
| Product usability | Operational task E2E shows event stream, artifacts, and cancellation. |

## Manual Verification Checklist

- Confirm `codex --version` and record compatibility.
- Confirm whether `claude --version` is available.
- Start local API and Web UI.
- Submit read-only Codex task.
- Submit Claude task and inspect health behavior.
- Inspect run ledger for event order, artifacts, policy decisions, and redaction.
- Confirm no untracked source changes occur outside the expected fixture/worktree.

## Non-goals for MVP Testing

- Full OpenHands integration.
- Full OWL wide-research swarm.
- Production multi-tenant isolation.
- Public A2A marketplace.
- Long-term personalization memory using mem0/Zep.
