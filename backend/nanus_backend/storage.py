from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from time import time
from typing import Any

DEFAULT_DB_PATH = Path(os.environ.get("NANUS_DB_PATH", ".nanus/nanus.sqlite3"))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


class RunStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("pragma foreign_keys = on")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._connection() as conn:
            conn.executescript(
                """
                create table if not exists runs (
                    id text primary key,
                    title text not null,
                    prompt text not null,
                    command text not null,
                    kind text not null,
                    status text not null,
                    worker text not null,
                    progress integer not null,
                    started_at text not null,
                    steps_json text not null,
                    artifacts_json text not null,
                    log_json text not null,
                    runtime_json text not null,
                    created_at real not null,
                    updated_at real not null
                );
                create table if not exists artifacts (
                    id text primary key,
                    run_id text not null references runs(id) on delete cascade,
                    title text not null,
                    type text not null,
                    content_json text not null,
                    created_at real not null
                );
                create table if not exists events (
                    id integer primary key autoincrement,
                    run_id text not null references runs(id) on delete cascade,
                    event_type text not null,
                    payload_json text not null,
                    created_at real not null
                );
                create table if not exists jobs (
                    id text primary key,
                    run_id text not null references runs(id) on delete cascade,
                    status text not null,
                    attempts integer not null,
                    error text,
                    created_at real not null,
                    updated_at real not null,
                    claimed_at real
                );
                create table if not exists conversations (
                    id text primary key,
                    title text not null,
                    project_id text,
                    instructions text,
                    created_at real not null,
                    updated_at real not null
                );
                create table if not exists messages (
                    id text primary key,
                    conversation_id text not null references conversations(id) on delete cascade,
                    run_id text references runs(id) on delete set null,
                    role text not null,
                    content text not null,
                    status text not null,
                    created_at real not null,
                    updated_at real not null
                );
                create index if not exists idx_messages_conversation_created
                    on messages(conversation_id, created_at);
                create index if not exists idx_messages_run
                    on messages(run_id);
                """
            )

    def save_run(self, run: dict[str, Any]) -> dict[str, Any]:
        now = time()
        runtime = dict(run.get("runtime", {}))
        result = dict(runtime.get("result", {})) if isinstance(runtime.get("result"), dict) else {}
        for key in ("finalAnswer", "resultType", "verification"):
            if key in run:
                result[key] = run[key]
        if result:
            runtime["result"] = result
        with self._lock, self._connection() as conn:
            previous = conn.execute("select created_at from runs where id = ?", (run["id"],)).fetchone()
            conn.execute(
                """
                insert into runs (
                    id, title, prompt, command, kind, status, worker, progress, started_at,
                    steps_json, artifacts_json, log_json, runtime_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    title=excluded.title,
                    prompt=excluded.prompt,
                    command=excluded.command,
                    kind=excluded.kind,
                    status=excluded.status,
                    worker=excluded.worker,
                    progress=excluded.progress,
                    started_at=excluded.started_at,
                    steps_json=excluded.steps_json,
                    artifacts_json=excluded.artifacts_json,
                    log_json=excluded.log_json,
                    runtime_json=excluded.runtime_json,
                    updated_at=excluded.updated_at
                """,
                (
                    run["id"],
                    run["title"],
                    run["prompt"],
                    run["command"],
                    run["kind"],
                    run["status"],
                    run["worker"],
                    int(run["progress"]),
                    run["startedAt"],
                    _json_dumps(run.get("steps", [])),
                    _json_dumps(run.get("artifacts", [])),
                    _json_dumps(run.get("log", [])),
                    _json_dumps(runtime),
                    previous["created_at"] if previous else now,
                    now,
                ),
            )
        return run

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            row = conn.execute("select * from runs where id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute("select * from runs order by created_at desc").fetchall()
        return [self._row_to_run(row) for row in rows]

    def save_conversation(
        self,
        conversation_id: str,
        *,
        title: str,
        project_id: str | None = None,
        instructions: str | None = None,
    ) -> dict[str, Any]:
        now = time()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                insert into conversations (id, title, project_id, instructions, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    project_id=coalesce(excluded.project_id, conversations.project_id),
                    instructions=coalesce(excluded.instructions, conversations.instructions),
                    updated_at=excluded.updated_at
                """,
                (conversation_id, title, project_id, instructions, now, now),
            )
            row = self._conversation_row(conn, conversation_id)
        if row is None:
            raise RuntimeError(f"Conversation {conversation_id} was not persisted")
        return self._row_to_conversation(row)

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            row = self._conversation_row(conn, conversation_id)
        return self._row_to_conversation(row) if row else None

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                """
                select
                    c.*,
                    count(m.id) as message_count,
                    max(m.updated_at) as last_message_at
                from conversations c
                left join messages m on m.conversation_id = c.id
                group by c.id
                order by c.updated_at desc
                """
            ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        *,
        role: str,
        content: str,
        status: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        now = time()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                insert into messages (id, conversation_id, run_id, role, content, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    run_id=excluded.run_id,
                    content=excluded.content,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (message_id, conversation_id, run_id, role, content, status, now, now),
            )
            conn.execute("update conversations set updated_at = ? where id = ?", (now, conversation_id))
            row = conn.execute("select * from messages where id = ?", (message_id,)).fetchone()
        if row is None:
            raise RuntimeError(f"Message {message_id} was not persisted")
        return self._row_to_message(row)

    def update_message(
        self,
        message_id: str,
        *,
        content: str | None = None,
        status: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any] | None:
        now = time()
        assignments = ["updated_at = ?"]
        values: list[Any] = [now]
        if content is not None:
            assignments.append("content = ?")
            values.append(content)
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if run_id is not None:
            assignments.append("run_id = ?")
            values.append(run_id)
        values.append(message_id)
        with self._lock, self._connection() as conn:
            conn.execute(f"update messages set {', '.join(assignments)} where id = ?", values)
            row = conn.execute("select * from messages where id = ?", (message_id,)).fetchone()
            if row:
                conn.execute("update conversations set updated_at = ? where id = ?", (now, row["conversation_id"]))
        return self._row_to_message(row) if row else None

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                "select * from messages where conversation_id = ? order by created_at, id",
                (conversation_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def enqueue_job(self, run_id: str, job_id: str) -> dict[str, Any]:
        now = time()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                insert into jobs (id, run_id, status, attempts, error, created_at, updated_at, claimed_at)
                values (?, ?, 'queued', 0, null, ?, ?, null)
                on conflict(id) do nothing
                """,
                (job_id, run_id, now, now),
            )
        job = self.get_job(job_id)
        if not job:
            raise RuntimeError(f"Job {job_id} was not persisted")
        return job

    def claim_job(self, job_id: str) -> dict[str, Any] | None:
        now = time()
        with self._lock, self._connection() as conn:
            row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
            if not row or row["status"] in {"complete", "failed", "cancelled", "degraded"}:
                return self._row_to_job(row) if row else None
            conn.execute(
                """
                update jobs
                set status = 'running',
                    attempts = attempts + 1,
                    updated_at = ?,
                    claimed_at = ?
                where id = ?
                """,
                (now, now, job_id),
            )
            row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def update_job(self, job_id: str, status: str, *, error: str | None = None) -> dict[str, Any] | None:
        now = time()
        with self._lock, self._connection() as conn:
            conn.execute(
                "update jobs set status = ?, error = ?, updated_at = ? where id = ?",
                (status, error, now, job_id),
            )
            row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_job_for_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            row = conn.execute("select * from jobs where run_id = ? order by created_at desc limit 1", (run_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_recoverable_jobs(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute("select * from jobs where status in ('queued', 'running') order by created_at").fetchall()
        return [self._row_to_job(row) for row in rows]

    def add_artifact(self, run_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
        artifact_id = artifact.get("id") or f"{run_id}-{artifact.get('type', 'artifact')}"
        stored = {**artifact, "id": artifact_id}
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                insert into artifacts (id, run_id, title, type, content_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    title=excluded.title,
                    type=excluded.type,
                    content_json=excluded.content_json
                """,
                (
                    artifact_id,
                    run_id,
                    stored.get("title", artifact_id),
                    stored.get("type", "artifact"),
                    _json_dumps(stored.get("content", {})),
                    time(),
                ),
            )
        return stored

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute("select * from artifacts where run_id = ? order by created_at", (run_id,)).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    def get_artifact(self, run_id: str, artifact_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "select * from artifacts where run_id = ? and id = ?",
                (run_id, artifact_id),
            ).fetchone()
        return self._row_to_artifact(row) if row else None

    def add_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        created_at = time()
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                "insert into events (run_id, event_type, payload_json, created_at) values (?, ?, ?, ?)",
                (run_id, event_type, _json_dumps(payload), created_at),
            )
            event_id = int(cursor.lastrowid)
        return {"id": event_id, "runId": run_id, "type": event_type, "payload": payload, "createdAt": created_at}

    def list_events(self, run_id: str, *, after: int = 0) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                "select * from events where run_id = ? and id > ? order by id",
                (run_id, after),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "runId": row["run_id"],
                "type": row["event_type"],
                "payload": _json_loads(row["payload_json"], {}),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def _row_to_run(self, row: sqlite3.Row) -> dict[str, Any]:
        runtime = _json_loads(row["runtime_json"], {})
        run = {
            "id": row["id"],
            "title": row["title"],
            "prompt": row["prompt"],
            "command": row["command"],
            "kind": row["kind"],
            "status": row["status"],
            "worker": row["worker"],
            "progress": row["progress"],
            "startedAt": row["started_at"],
            "steps": _json_loads(row["steps_json"], []),
            "artifacts": _json_loads(row["artifacts_json"], []),
            "log": _json_loads(row["log_json"], []),
            "runtime": runtime,
        }
        result = runtime.get("result") if isinstance(runtime, dict) else None
        if isinstance(result, dict):
            if isinstance(result.get("finalAnswer"), str):
                run["finalAnswer"] = result["finalAnswer"]
            if isinstance(result.get("resultType"), str):
                run["resultType"] = result["resultType"]
            if isinstance(result.get("verification"), dict):
                run["verification"] = result["verification"]
        return run

    def _row_to_job(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "runId": row["run_id"],
            "status": row["status"],
            "attempts": row["attempts"],
            "error": row["error"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "claimedAt": row["claimed_at"],
        }

    def _row_to_artifact(self, row: sqlite3.Row) -> dict[str, Any]:
        content = _json_loads(row["content_json"], {})
        artifact: dict[str, Any] = {
            "id": row["id"],
            "runId": row["run_id"],
            "title": row["title"],
            "type": row["type"],
            "content": content,
            "createdAt": row["created_at"],
            "downloadUrl": f"/api/runs/{row['run_id']}/artifacts/{row['id']}/download",
        }
        download = content.get("download") if isinstance(content, dict) else None
        if isinstance(download, dict):
            if download.get("filename"):
                artifact["fileName"] = download["filename"]
            if download.get("mimeType"):
                artifact["mimeType"] = download["mimeType"]
            if isinstance(download.get("size"), int):
                artifact["sizeBytes"] = download["size"]
        return artifact

    def _conversation_row(self, conn: sqlite3.Connection, conversation_id: str) -> sqlite3.Row | None:
        return conn.execute(
            """
            select
                c.*,
                count(m.id) as message_count,
                max(m.updated_at) as last_message_at
            from conversations c
            left join messages m on m.conversation_id = c.id
            where c.id = ?
            group by c.id
            """,
            (conversation_id,),
        ).fetchone()

    def _row_to_conversation(self, row: sqlite3.Row) -> dict[str, Any]:
        keys = set(row.keys())
        conversation: dict[str, Any] = {
            "id": row["id"],
            "title": row["title"],
            "projectId": row["project_id"],
            "instructions": row["instructions"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if "message_count" in keys:
            conversation["messageCount"] = int(row["message_count"] or 0)
        if "last_message_at" in keys:
            conversation["lastMessageAt"] = row["last_message_at"]
        return conversation

    def _row_to_message(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversationId": row["conversation_id"],
            "runId": row["run_id"],
            "role": row["role"],
            "content": row["content"],
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
