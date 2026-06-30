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
                """
            )

    def save_run(self, run: dict[str, Any]) -> dict[str, Any]:
        now = time()
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
                    _json_dumps(run.get("runtime", {})),
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
            if not row or row["status"] in {"complete", "failed", "cancelled"}:
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
        return {
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
            "runtime": _json_loads(row["runtime_json"], {}),
        }

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
