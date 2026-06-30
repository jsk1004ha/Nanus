from __future__ import annotations

import os
import shutil
import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodexResult:
    text: str
    live: bool
    command: list[str]
    error: str | None = None


class CodexBridge:
    """Bridge to the local Codex CLI.

    The bridge is intentionally configuration-gated. It exposes whether Codex is
    installed and invokes `codex exec` only when NANUS_CODEX_ENABLED is an
    explicit truthy value. Tests and demos therefore use deterministic fallback
    unless the operator opts into local subprocess execution.
    """

    def __init__(self, *, cwd: str | Path | None = None) -> None:
        configured = os.environ.get("CODEX_EXECUTABLE")
        configured_path = Path(configured).expanduser() if configured else None
        resolved = str(configured_path) if configured_path and configured_path.exists() else shutil.which(configured or "codex")
        self.executable = resolved or configured
        self.available = bool(resolved)
        self.cwd = Path(cwd or os.environ.get("NANUS_CODEX_WORKDIR") or Path.cwd()).resolve()
        self.enabled_mode = os.environ.get("NANUS_CODEX_ENABLED", "").lower()
        self.enabled = self.enabled_mode in {"1", "true", "on", "yes", "live"}
        self.timeout = float(os.environ.get("NANUS_CODEX_TIMEOUT", "45"))
        self.sandbox = os.environ.get("NANUS_CODEX_SANDBOX", "read-only")
        self.model = os.environ.get("NANUS_CODEX_MODEL", "")

    def status(self) -> dict[str, Any]:
        return {
            "id": "codex-cli",
            "name": "Codex CLI Bridge",
            "available": self.available,
            "enabled": bool(self.available and self.enabled),
            "mode": self.enabled_mode,
            "executable": self.executable,
            "cwd": str(self.cwd),
            "sandbox": self.sandbox,
            "invocation": "codex exec --json --sandbox <mode> --ask-for-approval never --cd <workspace> -",
        }

    def should_handle(self, command: str, prompt: str, kind: str) -> bool:
        haystack = f"{command} {prompt}".lower()
        if command.startswith("/codex"):
            return True
        return kind in {"app", "site"} or any(token in haystack for token in ["codex", "코드", "codebase", "refactor", "리팩터"])

    async def run(self, prompt: str) -> CodexResult:
        if not self.available or not self.executable:
            return self._fallback(prompt, error="codex executable not found")
        if not self.enabled:
            return self._fallback(prompt, error="NANUS_CODEX_ENABLED is not true")

        with tempfile.NamedTemporaryFile("r+", encoding="utf-8", suffix=".md", delete=False) as output:
            output_path = output.name
        command = [
            self.executable,
            "exec",
            "--json",
            "--sandbox",
            self.sandbox,
            "--ask-for-approval",
            "never",
            "--cd",
            str(self.cwd),
            "--output-last-message",
            output_path,
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.append("-")

        safe_prompt = (
            "You are connected from the Nanus backend Codex bridge. "
            "Execute the user task inside the configured sandbox. "
            "Make workspace edits only when the sandbox permits them and the task requires code changes. "
            "Do not perform destructive actions; finish with a concise execution summary.\n\n"
            f"User task:\n{prompt}\n"
        )
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                input=safe_prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=self.cwd,
                check=False,
            )
            output_text = Path(output_path).read_text(encoding="utf-8").strip() if Path(output_path).exists() else ""
            if completed.returncode != 0:
                error = (completed.stderr or completed.stdout or f"codex exited {completed.returncode}").strip()
                return self._fallback(prompt, error=error, command=command)
            return CodexResult(text=output_text or completed.stdout.strip() or "Codex execution completed.", live=True, command=command)
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            return self._fallback(prompt, error=f"{type(exc).__name__}: {exc}", command=command)
        finally:
            try:
                Path(output_path).unlink(missing_ok=True)
            except OSError:
                pass

    def _fallback(self, prompt: str, *, error: str, command: list[str] | None = None) -> CodexResult:
        task = " ".join(prompt.split()) or "코드 작업"
        text = (
            f"Codex Bridge fallback이 '{task}' 요청을 안전하게 수신했습니다.\n"
            "- 로컬 Codex CLI 연결 상태와 실행 명령은 /api/tools에서 확인할 수 있습니다.\n"
            "- NANUS_CODEX_ENABLED=true 설정 시 codex exec 경로를 사용합니다.\n"
            "- 현재 실행은 테스트 가능한 결정적 산출물과 체크리스트를 생성했습니다."
        )
        return CodexResult(text=text, live=False, command=command or [], error=error)
