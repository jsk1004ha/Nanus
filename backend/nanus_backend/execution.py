from __future__ import annotations

import asyncio
from typing import Any

from .codex_bridge import CodexBridge
from .llm import AnthropicMessagesClient
from .tooling import (
    artifact_studio_bundle,
    deck_from_brief,
    document_from_prompt,
    generic_llm_result,
    research_brief,
    spreadsheet_from_prompt,
    visualization_from_prompt,
    writing_advice,
)
from .storage import RunStore


def _append_log(run: dict[str, Any], line: str) -> None:
    if line not in run["log"]:
        run["log"].append(line)


def _set_step(run: dict[str, Any], active_index: int) -> None:
    steps = run.get("steps", [])
    if not steps:
        return
    safe = max(0, min(len(steps) - 1, active_index))
    for index, step in enumerate(steps):
        step["state"] = "done" if index < safe else "active" if index == safe else "pending"
    run["progress"] = max(int(run.get("progress", 0)), min(92, round(((safe + 0.5) / max(1, len(steps))) * 88)))


def _finish_steps(run: dict[str, Any]) -> None:
    for step in run.get("steps", []):
        step["state"] = "done"
    run["progress"] = 100


def _answer(result: dict[str, Any]) -> str:
    text = str(result.get("finalAnswer") or "").strip()
    if len(text) < 20:
        raise RuntimeError("Assistant final answer is missing")
    return text


def _download_ok(artifact: dict[str, Any]) -> bool:
    content = artifact.get("content")
    if not isinstance(content, dict):
        return True
    download = content.get("download")
    if not isinstance(download, dict):
        return True
    return bool(download.get("filename")) and bool(download.get("mimeType")) and int(download.get("size") or 0) > 0


def _verify(result: dict[str, Any], final_answer: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    raw = result.get("verification") if isinstance(result.get("verification"), dict) else {}
    errors = [str(item) for item in raw.get("errors", []) if str(item).strip()]
    warnings = [str(item) for item in raw.get("warnings", []) if str(item).strip()]
    fallback = bool(raw.get("fallbackUsed"))
    artifacts_ok = all(_download_ok(artifact) for artifact in artifacts)
    if not final_answer:
        errors.append("finalAnswer is missing")
    if not artifacts_ok:
        errors.append("artifact integrity check failed")
    if fallback and not warnings:
        warnings.append("fallback runtime used")
    return {
        "backendUsed": bool(raw.get("backendUsed", True)),
        "llmUsed": bool(raw.get("llmUsed", False)),
        "fallbackUsed": fallback,
        "status": "failed" if errors else "degraded" if fallback else "verified",
        "finalAnswerPresent": bool(final_answer),
        "artifactIntegrityOk": artifacts_ok,
        "traceClosed": True,
        "streaming": True,
        "errors": errors,
        "warnings": warnings,
    }


def _assistant_message_id(run: dict[str, Any]) -> str | None:
    runtime = run.get("runtime") if isinstance(run.get("runtime"), dict) else {}
    conversation = runtime.get("conversation") if isinstance(runtime.get("conversation"), dict) else {}
    message_id = conversation.get("assistantMessageId")
    return str(message_id) if message_id else None


def _chunks(text: str) -> list[str]:
    parts: list[str] = []
    buf = ""
    for token in text.split(" "):
        next_buf = f"{buf} {token}" if buf else token
        if len(next_buf) > 180:
            parts.append(next_buf)
            buf = ""
        else:
            buf = next_buf
    if buf:
        parts.append(buf)
    return parts or [text]


def _subtasks(kind: str) -> list[dict[str, Any]]:
    names = {
        "research": ["scope", "sources", "synthesis"],
        "deck": ["story", "render", "slide-qa"],
        "document": ["outline", "draft", "doc-qa"],
        "spreadsheet": ["schema", "workbook", "checks"],
        "visualization": ["question", "chart", "caption"],
        "app": ["scope", "code", "test"],
    }.get(kind, ["plan", "execute", "verify"])
    return [{"id": name, "owner": name.title(), "status": "pending"} for name in names]


class ExecutionEngine:
    def __init__(self, store: RunStore, *, llm: AnthropicMessagesClient | None = None, codex: CodexBridge | None = None) -> None:
        self.store = store
        self.llm = llm or AnthropicMessagesClient()
        self.codex = codex or CodexBridge()

    async def execute_job(self, job_id: str) -> None:
        job = self.store.claim_job(job_id)
        if not job:
            return
        run_id = str(job["runId"])
        run = self.store.get_run(run_id)
        if not run:
            self.store.update_job(job_id, "failed", error=f"run {run_id} not found")
            return
        try:
            run["status"] = "running"
            runtime = run.setdefault("runtime", {})
            runtime["agentLoop"] = []
            runtime["subtasks"] = _subtasks(str(run.get("kind") or "general"))
            _append_log(run, "Agent runtime started.")
            self._update_message(run, status="running")
            self._persist_and_emit(run, "run.started")
            self._event(run_id, "subtasks.created", {"runId": run_id, "subtasks": runtime["subtasks"]})

            run = await self._phase(run_id, job_id, "plan", "Planner", "작업을 하위 실행 단위로 나눕니다.", 0)
            if not run:
                return
            self._mark_subtasks(run, "planned")
            self._persist_and_emit(run, "subtasks.updated")

            run = await self._phase(run_id, job_id, "execute", "Tool Executor", "선택한 도구와 산출물 생성기를 실행합니다.", min(1, len(run.get("steps", [])) - 1))
            if not run:
                return
            result = await self._execute_adapter(run)
            final = _answer(result)
            artifacts = [artifact for artifact in result.get("artifacts", []) if isinstance(artifact, dict)]

            run = self.store.get_run(run_id) or run
            run["resultType"] = str(result.get("resultType") or run.get("kind") or "answer")
            run["verification"] = _verify(result, final, artifacts)
            if run["verification"]["status"] == "failed":
                raise RuntimeError("; ".join(run["verification"]["errors"]))
            await self._stream_answer(run, final)
            run = self.store.get_run(run_id) or run
            run["finalAnswer"] = final
            self._update_message(run, content=final, status="degraded" if run["verification"]["status"] == "degraded" else "complete")
            for line in result.get("logs", []):
                _append_log(run, line)

            stored_artifacts: list[dict[str, Any]] = []
            for artifact in artifacts:
                stored = self.store.add_artifact(run_id, artifact)
                stored_artifacts.append(stored)
                self._event(run_id, "artifact.created", {"runId": run_id, "artifact": stored})
            if stored_artifacts:
                ids = {artifact.get("id") for artifact in stored_artifacts}
                types = {artifact.get("type") for artifact in stored_artifacts}
                run["artifacts"] = [artifact for artifact in run.get("artifacts", []) if artifact.get("id") not in ids and artifact.get("type") not in types] + stored_artifacts
            self._event(run_id, "assistant.message.completed", {"runId": run_id, "assistantMessageId": _assistant_message_id(run), "finalAnswer": final, "resultType": run.get("resultType"), "verification": run.get("verification")})
            self._mark_subtasks(run, "completed")
            self._persist_and_emit(run)

            run = await self._phase(run_id, job_id, "verify", "Verifier", "답변과 산출물 무결성을 확인합니다.", max(0, len(run.get("steps", [])) - 1))
            if not run:
                return
            _finish_steps(run)
            run["status"] = "degraded" if run.get("verification", {}).get("status") == "degraded" else "complete"
            _append_log(run, "제한 실행으로 종료되었습니다." if run["status"] == "degraded" else "실행이 완료되었습니다.")
            self._record_phase(run, phase_id="deliver", title="Artifact Handoff", detail="답변과 산출물을 전달했습니다.")
            self._persist_and_emit(run)
            self.store.update_job(job_id, run["status"])
            self._event(run_id, "run.done" if run["status"] == "complete" else "run.degraded", {"run": run})
        except Exception as exc:
            failed = self.store.get_run(run_id)
            if failed:
                failed["status"] = "failed"
                _append_log(failed, f"실행 실패: {exc}")
                self._update_message(failed, status="failed", content=f"실행 실패: {exc}")
                self._persist_and_emit(failed, "run.failed")
            self.store.update_job(job_id, "failed", error=str(exc))

    async def _execute_adapter(self, run: dict[str, Any]) -> dict[str, Any]:
        prompt = run.get("prompt") or run.get("command") or run.get("title") or ""
        command = run.get("command", "/run")
        kind = run.get("kind", "general")
        if self.codex.should_handle(command, prompt, kind):
            return await self._codex_result(run, prompt, kind)
        if command in {"/artifact-studio", "/artifact"}:
            return await artifact_studio_bundle(prompt, self.llm)
        if kind == "writing":
            return await writing_advice(prompt, self.llm)
        if kind == "document":
            return await document_from_prompt(prompt, self.llm)
        if kind == "spreadsheet":
            return await spreadsheet_from_prompt(prompt, self.llm)
        if kind == "visualization":
            return await visualization_from_prompt(prompt, self.llm)
        if kind == "research":
            return await research_brief(prompt, self.llm)
        if kind == "deck":
            return await deck_from_brief(prompt, self.llm)
        return await generic_llm_result(prompt, self.llm)

    async def _codex_result(self, run: dict[str, Any], prompt: str, kind: str) -> dict[str, Any]:
        result = await self.codex.run(prompt or run.get("title") or "Nanus task")
        return {
            "finalAnswer": result.text,
            "resultType": "code_patch" if result.live and kind in {"app", "site"} else "codex_answer",
            "verification": {"backendUsed": True, "llmUsed": result.live, "fallbackUsed": not result.live, "errors": [], "warnings": [] if result.live else ["Codex fallback used"]},
            "logs": [f"Codex Bridge: {'live codex exec' if result.live else 'deterministic fallback'}"],
            "artifacts": [{"id": f"codex-{run['id'][:8]}", "title": f"{run['title']} Codex 결과", "type": "codex-summary", "content": {"text": result.text, "live": result.live, "command": result.command}}],
        }

    async def _stream_answer(self, run: dict[str, Any], final_answer: str) -> None:
        run_id = str(run["id"])
        message_id = _assistant_message_id(run)
        partial = ""
        for index, chunk in enumerate(_chunks(final_answer), start=1):
            current = self.store.get_run(run_id) or run
            if current.get("status") == "cancelled":
                return
            partial = f"{partial} {chunk}".strip() if partial else chunk
            current["finalAnswer"] = partial
            self.store.save_run(current)
            if message_id:
                self.store.update_message(message_id, content=partial, status="streaming")
            self._event(run_id, "assistant.message.delta", {"run": current, "delta": chunk, "content": partial, "index": index})
            await asyncio.sleep(0.01)

    def _mark_subtasks(self, run: dict[str, Any], status: str) -> None:
        runtime = run.setdefault("runtime", {})
        subtasks = runtime.get("subtasks") if isinstance(runtime.get("subtasks"), list) else []
        runtime["subtasks"] = [{**dict(item), "status": status} for item in subtasks if isinstance(item, dict)]

    def _update_message(self, run: dict[str, Any], *, status: str | None = None, content: str | None = None) -> None:
        message_id = _assistant_message_id(run)
        if message_id:
            self.store.update_message(message_id, status=status, content=content)

    def _persist_and_emit(self, run: dict[str, Any], event_type: str = "run.updated") -> dict[str, Any]:
        self.store.save_run(run)
        return self._event(run["id"], event_type, {"run": run})

    def _event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.store.add_event(run_id, event_type, payload)

    def _record_phase(self, run: dict[str, Any], *, phase_id: str, title: str, detail: str) -> dict[str, Any]:
        runtime = run.setdefault("runtime", {})
        loop = runtime.get("agentLoop") if isinstance(runtime.get("agentLoop"), list) else []
        phase = {"id": phase_id, "title": title, "detail": detail, "progress": int(run.get("progress", 0)), "index": len(loop) + 1}
        loop.append(phase)
        runtime["agentLoop"] = loop
        _append_log(run, f"Agent phase: {title} — {detail}")
        return phase

    async def _phase(self, run_id: str, job_id: str, phase_id: str, title: str, detail: str, step_index: int) -> dict[str, Any] | None:
        await self._checkpoint(run_id, job_id)
        run = self.store.get_run(run_id)
        if not run or run.get("status") == "cancelled":
            self.store.update_job(job_id, "cancelled")
            return None
        _set_step(run, step_index)
        phase = self._record_phase(run, phase_id=phase_id, title=title, detail=detail)
        self.store.save_run(run)
        self._event(run_id, "agent.phase", {"run": run, "phase": phase})
        return run

    async def _checkpoint(self, run_id: str, job_id: str) -> None:
        while True:
            await asyncio.sleep(0.02)
            run = self.store.get_run(run_id)
            if not run or run["status"] != "paused":
                return
            self.store.update_job(job_id, "paused")
