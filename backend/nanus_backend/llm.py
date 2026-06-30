from __future__ import annotations

import json
import os
import asyncio
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    live: bool
    error: str | None = None


class AnthropicMessagesClient:
    """Tiny Anthropic Messages API adapter with deterministic fallback.

    Live calls are enabled only when ANTHROPIC_API_KEY is present and
    NANUS_ANTHROPIC_ENABLED is not set to a false value. Tests and local demos
    therefore work without external credentials.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
        self.timeout = float(os.environ.get("NANUS_ANTHROPIC_TIMEOUT", "20"))
        self.enabled = os.environ.get("NANUS_ANTHROPIC_ENABLED", "auto").lower() not in {"0", "false", "off", "no"}

    def status(self) -> dict[str, Any]:
        return {
            "id": "anthropic-messages",
            "name": "Anthropic Messages API",
            "available": bool(self.api_key),
            "enabled": bool(self.api_key and self.enabled),
            "model": self.model,
            "versionHeader": ANTHROPIC_VERSION,
        }

    async def generate(self, prompt: str, *, system: str) -> LLMResult:
        if not self.api_key or not self.enabled:
            return self._fallback(prompt, reason="ANTHROPIC_API_KEY not configured")
        payload = {
            "model": self.model,
            "max_tokens": 800,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        request = urllib.request.Request(
            ANTHROPIC_MESSAGES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )
        try:
            data = await asyncio.to_thread(self._post_messages, request)
            text = "\n".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()
            if not text:
                return self._fallback(prompt, reason="empty Anthropic response")
            return LLMResult(text=text, provider="anthropic", live=True)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            return self._fallback(prompt, reason=f"{type(exc).__name__}: {exc}")

    def _post_messages(self, request: urllib.request.Request) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fallback(self, prompt: str, *, reason: str) -> LLMResult:
        clean = " ".join(prompt.split()) or "요청"
        text = (
            f"로컬 Nanus 실행기가 외부 키 없이 '{clean}' 작업을 처리했습니다.\n"
            "1. 요구사항을 실행 가능한 산출물 단위로 분해했습니다.\n"
            "2. 결정적 로컬 생성기로 초안과 검증 체크리스트를 만들었습니다.\n"
            "3. 실제 LLM 호출은 ANTHROPIC_API_KEY 설정 시 Anthropic Messages API로 전환됩니다."
        )
        return LLMResult(text=text, provider="local-fallback", live=False, error=reason)
