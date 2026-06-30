from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from .codex_bridge import CodexBridge
from .llm import AnthropicMessagesClient
from .tooling import deck_from_brief, generic_llm_result
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


class ExecutionEngine:
    def __init__(self, store: RunStore, *, llm: AnthropicMessagesClient | None = None, codex: CodexBridge | None = None) -> None:
        self.store = store
        self.llm = llm or AnthropicMessagesClient()
        self.codex = codex or CodexBridge()

    async def stream_run(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        run = self.store.get_run(run_id)
        if not run:
            yield {"type": "error", "payload": {"message": f"run {run_id} not found"}}
            return

        yield self._event(run_id, "run.snapshot", {"run": run})
        if run["status"] == "complete":
            yield self._event(run_id, "run.done", {"run": run})
            return

        await asyncio.sleep(0.02)
        _append_log(run, "FastAPI WebSocket 실행 스트림에 연결했습니다.")
        self._persist_run(run)
        yield self._event(run_id, "run.updated", {"run": run})

        await asyncio.sleep(0.02)
        previous_steps = [dict(step) for step in run["steps"]]
        _set_progress(run, 56)
        for title in _newly_done_titles(previous_steps, run["steps"]):
            _append_log(run, f"완료: {title}")
        active = next((step for step in run["steps"] if step.get("state") == "active"), None)
        if active:
            _append_log(run, f"현재 단계: {active['title']}")
        self._persist_run(run)
        yield self._event(run_id, "run.updated", {"run": run})

        adapter_result = await self._execute_adapter(run)
        for line in adapter_result.get("logs", []):
            _append_log(run, line)

        persisted_artifacts: list[dict[str, Any]] = []
        for artifact in adapter_result.get("artifacts", []):
            stored = self.store.add_artifact(run_id, artifact)
            persisted_artifacts.append(stored)
            yield self._event(run_id, "artifact.created", {"runId": run_id, "artifact": stored})

        if persisted_artifacts:
            persisted_ids = {artifact.get("id") for artifact in persisted_artifacts}
            persisted_types = {artifact.get("type") for artifact in persisted_artifacts}
            run["artifacts"] = [
                artifact
                for artifact in run.get("artifacts", [])
                if artifact.get("id") not in persisted_ids and artifact.get("type") not in persisted_types
            ] + persisted_artifacts

        await asyncio.sleep(0.02)
        previous_steps = [dict(step) for step in run["steps"]]
        _set_progress(run, 82)
        for title in _newly_done_titles(previous_steps, run["steps"]):
            _append_log(run, f"완료: {title}")
        active = next((step for step in run["steps"] if step.get("state") == "active"), None)
        if active:
            _append_log(run, f"현재 단계: {active['title']}")
        self._persist_run(run)
        yield self._event(run_id, "run.updated", {"run": run})

        await asyncio.sleep(0.02)
        previous_steps = [dict(step) for step in run["steps"]]
        _set_progress(run, 100)
        for title in _newly_done_titles(previous_steps, run["steps"]):
            _append_log(run, f"완료: {title}")
        _append_log(run, "실행이 완료되었습니다.")
        run["status"] = "complete"
        self._persist_run(run)
        yield self._event(run_id, "run.updated", {"run": run})
        yield self._event(run_id, "run.done", {"run": run})

    async def _execute_adapter(self, run: dict[str, Any]) -> dict[str, Any]:
        prompt = run.get("prompt") or run.get("command") or run.get("title") or ""
        command = run.get("command", "/run")
        kind = run.get("kind", "general")
        if self.codex.should_handle(command, prompt, kind):
            codex_result = await self.codex.run(prompt)
            return {
                "logs": [
                    f"Codex Bridge: {'live codex exec' if codex_result.live else 'deterministic fallback'}",
                    *( [f"Codex Bridge note: {codex_result.error}"] if codex_result.error else [] ),
                ],
                "artifacts": [
                    {
                        "id": f"codex-{run['id'][:8]}",
                        "title": f"{run['title']} Codex 결과",
                        "type": "codex-summary",
                        "content": {"text": codex_result.text, "live": codex_result.live, "command": codex_result.command},
                    }
                ],
            }
        if command in {"/deck-from-brief", "/artifact-studio"} or kind == "deck":
            return await deck_from_brief(prompt, self.llm)
        return await generic_llm_result(prompt, self.llm)

    def _persist_run(self, run: dict[str, Any]) -> None:
        self.store.save_run(run)

    def _event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.store.add_event(run_id, event_type, payload)
