from __future__ import annotations

import asyncio
from typing import Any

from .codex_bridge import CodexBridge
from .llm import AnthropicMessagesClient
from .tooling import deck_from_brief, generic_llm_result, writing_advice
from .storage import RunStore


def _append_log(run: dict[str, Any], line: str) -> None:
    if line not in run["log"]:
        run["log"].append(line)


def _set_progress(run: dict[str, Any], progress: int) -> None:
    run["progress"] = max(0, min(100, progress))
    steps = run.get("steps", [])
    if not steps:
        return
    if progress >= 100:
        for step in steps:
            step["state"] = "done"
        return
    active_index = min(len(steps) - 1, max(0, int((progress / 100) * len(steps))))
    for index, step in enumerate(steps):
        step["state"] = "done" if index < active_index else "active" if index == active_index else "pending"


def _newly_done_titles(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[str]:
    previous_done = {step["id"] for step in previous if step.get("state") == "done"}
    return [step["title"] for step in current if step.get("state") == "done" and step.get("id") not in previous_done]


def _final_answer(adapter_result: dict[str, Any]) -> str:
    final_answer = str(adapter_result.get("finalAnswer") or "").strip()
    if len(final_answer) < 20:
        raise RuntimeError("Assistant final answer is missing")
    return final_answer


def _download_integrity_ok(artifact: dict[str, Any]) -> bool:
    content = artifact.get("content")
    if not isinstance(content, dict):
        return True
    download = content.get("download")
    if not isinstance(download, dict):
        return True
    return bool(download.get("filename")) and bool(download.get("mimeType")) and isinstance(download.get("size"), int) and download["size"] > 0


def _artifact_integrity_ok(artifacts: list[dict[str, Any]]) -> bool:
    return all(
        bool(artifact.get("id"))
        and bool(artifact.get("title"))
        and bool(artifact.get("type"))
        and _download_integrity_ok(artifact)
        for artifact in artifacts
    )


def _normalize_verification(adapter_result: dict[str, Any], *, final_answer: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    raw = adapter_result.get("verification") if isinstance(adapter_result.get("verification"), dict) else {}
    errors = [str(item) for item in raw.get("errors", []) if str(item).strip()]
    warnings = [str(item) for item in raw.get("warnings", []) if str(item).strip()]
    fallback_used = bool(raw.get("fallbackUsed"))
    final_answer_present = bool(final_answer.strip())
    artifact_integrity_ok = _artifact_integrity_ok(artifacts)
    if not final_answer_present:
        errors.append("finalAnswer is missing")
    if not artifact_integrity_ok:
        errors.append("artifact integrity check failed")
    if fallback_used and not any("fallback" in warning.lower() or "제한" in warning for warning in warnings):
        warnings.append("실제 LLM/도구 대신 제한 실행 fallback을 사용했습니다.")
    status = "failed" if errors else "degraded" if fallback_used else "verified"
    return {
        "backendUsed": bool(raw.get("backendUsed", True)),
        "llmUsed": bool(raw.get("llmUsed", False)),
        "fallbackUsed": fallback_used,
        "status": status,
        "finalAnswerPresent": final_answer_present,
        "artifactIntegrityOk": artifact_integrity_ok,
        "traceClosed": True,
        "errors": errors,
        "warnings": warnings,
    }


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
        if run["status"] == "cancelled":
            self.store.update_job(job_id, "cancelled")
            return

        try:
            run["status"] = "running"
            _append_log(run, "백그라운드 작업자가 실행을 시작했습니다.")
            self._persist_and_emit(run, "run.started")

            await self._checkpoint(run_id, job_id)
            run = self.store.get_run(run_id)
            if not run or run["status"] == "cancelled":
                self.store.update_job(job_id, "cancelled")
                return

            previous_steps = [dict(step) for step in run["steps"]]
            _set_progress(run, 34)
            for title in _newly_done_titles(previous_steps, run["steps"]):
                _append_log(run, f"완료: {title}")
            active = next((step for step in run["steps"] if step.get("state") == "active"), None)
            if active:
                _append_log(run, f"현재 단계: {active['title']}")
            self._persist_and_emit(run)

            await self._checkpoint(run_id, job_id)
            run = self.store.get_run(run_id)
            if not run or run["status"] == "cancelled":
                self.store.update_job(job_id, "cancelled")
                return

            previous_steps = [dict(step) for step in run["steps"]]
            _set_progress(run, 56)
            for title in _newly_done_titles(previous_steps, run["steps"]):
                _append_log(run, f"완료: {title}")
            active = next((step for step in run["steps"] if step.get("state") == "active"), None)
            if active:
                _append_log(run, f"현재 단계: {active['title']}")
            self._persist_and_emit(run)

            adapter_result = await self._execute_adapter(run)
            final_answer = _final_answer(adapter_result)
            run = self.store.get_run(run_id)
            if not run or run["status"] == "cancelled":
                self.store.update_job(job_id, "cancelled")
                return
            run["finalAnswer"] = final_answer
            run["resultType"] = str(adapter_result.get("resultType") or run.get("kind") or "answer")
            run["verification"] = _normalize_verification(
                adapter_result,
                final_answer=final_answer,
                artifacts=[artifact for artifact in adapter_result.get("artifacts", []) if isinstance(artifact, dict)],
            )
            if run["verification"]["status"] == "failed":
                raise RuntimeError("; ".join(run["verification"]["errors"]) or "Result contract validation failed")
            for line in adapter_result.get("logs", []):
                _append_log(run, line)
            _append_log(run, "최종 답변 contract: finalAnswer 검증 완료")

            persisted_artifacts: list[dict[str, Any]] = []
            for artifact in adapter_result.get("artifacts", []):
                stored = self.store.add_artifact(run_id, artifact)
                persisted_artifacts.append(stored)
                self._event(run_id, "artifact.created", {"runId": run_id, "artifact": stored})

            if persisted_artifacts:
                persisted_ids = {artifact.get("id") for artifact in persisted_artifacts}
                persisted_types = {artifact.get("type") for artifact in persisted_artifacts}
                run["artifacts"] = [
                    artifact
                    for artifact in run.get("artifacts", [])
                    if artifact.get("id") not in persisted_ids and artifact.get("type") not in persisted_types
                ] + persisted_artifacts
            self._event(
                run_id,
                "assistant.message.completed",
                {
                    "runId": run_id,
                    "finalAnswer": final_answer,
                    "resultType": run.get("resultType"),
                    "verification": run.get("verification"),
                },
            )
            self._persist_and_emit(run)

            await self._checkpoint(run_id, job_id)
            run = self.store.get_run(run_id)
            if not run or run["status"] == "cancelled":
                self.store.update_job(job_id, "cancelled")
                return

            previous_steps = [dict(step) for step in run["steps"]]
            _set_progress(run, 82)
            for title in _newly_done_titles(previous_steps, run["steps"]):
                _append_log(run, f"완료: {title}")
            active = next((step for step in run["steps"] if step.get("state") == "active"), None)
            if active:
                _append_log(run, f"현재 단계: {active['title']}")
            self._persist_and_emit(run)

            await self._checkpoint(run_id, job_id)
            run = self.store.get_run(run_id)
            if not run or run["status"] == "cancelled":
                self.store.update_job(job_id, "cancelled")
                return

            previous_steps = [dict(step) for step in run["steps"]]
            _set_progress(run, 100)
            for title in _newly_done_titles(previous_steps, run["steps"]):
                _append_log(run, f"완료: {title}")
            verification_status = str(run.get("verification", {}).get("status") or "verified")
            run["status"] = "degraded" if verification_status == "degraded" else "complete"
            if run["status"] == "degraded":
                _append_log(run, "제한 실행으로 종료되었습니다. 답변은 제공되었지만 fallback 또는 일부 제한이 있습니다.")
            else:
                _append_log(run, "실행이 완료되었습니다.")
            self._persist_and_emit(run)
            self.store.update_job(job_id, run["status"])
            self._event(run_id, "run.done" if run["status"] == "complete" else "run.degraded", {"run": run})
        except Exception as exc:
            failed_run = self.store.get_run(run_id)
            if failed_run:
                failed_run["status"] = "failed"
                _append_log(failed_run, f"실행 실패: {exc}")
                self._persist_and_emit(failed_run, "run.failed")
            self.store.update_job(job_id, "failed", error=str(exc))

    async def _execute_adapter(self, run: dict[str, Any]) -> dict[str, Any]:
        prompt = run.get("prompt") or run.get("command") or run.get("title") or ""
        command = run.get("command", "/run")
        kind = run.get("kind", "general")
        if self.codex.should_handle(command, prompt, kind) or (self.codex.enabled and kind != "deck"):
            return await self._codex_adapter_result(run, prompt, kind)
        if kind == "writing":
            return await writing_advice(prompt, self.llm)
        if command in {"/deck-from-brief", "/artifact-studio"} or kind == "deck":
            return await deck_from_brief(prompt, self.llm)
        return await generic_llm_result(prompt, self.llm)

    async def _codex_adapter_result(self, run: dict[str, Any], prompt: str, kind: str) -> dict[str, Any]:
        task_prompt = prompt or run.get("title") or run.get("command") or "Nanus task"
        if kind == "writing":
            task_prompt = (
                "한국어 보고서 작성 코치로 답변하세요. 전체 진단, 섹션별 보강 방향, 바로 붙여넣을 수 있는 추가 문단 예시, "
                "피해야 할 방식을 포함하세요.\n\n"
                f"사용자 요청:\n{task_prompt}"
            )
        elif kind not in {"app", "site"}:
            task_prompt = (
                "Nanus assistant로서 사용자의 요청에 바로 도움이 되는 한국어 최종 답변을 작성하세요. "
                "필요하면 작업 계획과 다음 행동을 짧게 포함하되, 실제 파일 변경이 필요 없는 경우 변경하지 마세요.\n\n"
                f"사용자 요청:\n{task_prompt}"
            )
        codex_result = await self.codex.run(task_prompt)
        result_type = "code_patch" if codex_result.live and kind in {"app", "site"} else "codex_answer"
        artifact_type = "codex-summary" if kind in {"app", "site"} else "assistant-answer"
        return {
            "finalAnswer": codex_result.text,
            "resultType": result_type,
            "verification": {
                "backendUsed": True,
                "llmUsed": codex_result.live,
                "fallbackUsed": not codex_result.live,
                "errors": [],
                "warnings": [] if codex_result.live else ["Codex live 실행 대신 deterministic fallback을 사용했습니다."],
            },
            "logs": [
                f"Codex Bridge: {'live codex exec' if codex_result.live else 'deterministic fallback'}",
                *( [f"Codex Bridge note: {codex_result.error}"] if codex_result.error else [] ),
            ],
            "artifacts": [
                {
                    "id": f"codex-{run['id'][:8]}",
                    "title": f"{run['title']} Codex 결과",
                    "type": artifact_type,
                    "content": {"text": codex_result.text, "live": codex_result.live, "command": codex_result.command},
                }
            ],
        }

    def _persist_run(self, run: dict[str, Any]) -> None:
        self.store.save_run(run)

    def _persist_and_emit(self, run: dict[str, Any], event_type: str = "run.updated") -> dict[str, Any]:
        self._persist_run(run)
        return self._event(run["id"], event_type, {"run": run})

    def _event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.store.add_event(run_id, event_type, payload)

    async def _checkpoint(self, run_id: str, job_id: str) -> None:
        while True:
            await asyncio.sleep(0.02)
            run = self.store.get_run(run_id)
            if not run or run["status"] != "paused":
                return
            self.store.update_job(job_id, "paused")
