from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MAX_INPUT_CHARS = 90_000


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    live: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AnthropicMessagesClient:
    """Anthropic Messages API adapter with explicit, truthful fallback metadata.

    Nanus previously behaved like a tiny one-shot LLM wrapper: it always asked for
    800 tokens and silently swapped to a short deterministic fallback when no key
    was configured. That made document/report work look complete while the actual
    model path had not run. This adapter keeps offline demos deterministic, but it
    now exposes the output budget, prompt clipping, timeout, and fallback reason so
    the execution layer and UI can show degraded runs honestly.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
        self.timeout = float(os.environ.get("NANUS_ANTHROPIC_TIMEOUT", "45"))
        self.max_tokens = _env_int("NANUS_ANTHROPIC_MAX_TOKENS", DEFAULT_MAX_TOKENS, minimum=256, maximum=16_384)
        self.max_input_chars = _env_int("NANUS_LLM_MAX_INPUT_CHARS", DEFAULT_MAX_INPUT_CHARS, minimum=8_000, maximum=240_000)
        self.enabled = os.environ.get("NANUS_ANTHROPIC_ENABLED", "auto").lower() not in {"0", "false", "off", "no"}

    def status(self) -> dict[str, Any]:
        return {
            "id": "anthropic-messages",
            "name": "Anthropic Messages API",
            "available": bool(self.api_key),
            "enabled": bool(self.api_key and self.enabled),
            "model": self.model,
            "versionHeader": ANTHROPIC_VERSION,
            "timeoutSeconds": self.timeout,
            "maxTokens": self.max_tokens,
            "maxInputChars": self.max_input_chars,
            "streaming": False,
        }

    async def generate(self, prompt: str, *, system: str, max_tokens: int | None = None) -> LLMResult:
        prepared_prompt, clipped = self._prepare_prompt(prompt)
        requested_tokens = max(256, min(16_384, int(max_tokens or self.max_tokens)))
        metadata = {"maxTokens": requested_tokens, "inputChars": len(prompt), "clipped": clipped}
        if not self.api_key or not self.enabled:
            return self._fallback(prepared_prompt, reason="ANTHROPIC_API_KEY not configured", metadata=metadata)
        payload = {
            "model": self.model,
            "max_tokens": requested_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prepared_prompt}],
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
                return self._fallback(prepared_prompt, reason="empty Anthropic response", metadata=metadata)
            return LLMResult(text=text, provider="anthropic", live=True, metadata=metadata)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            return self._fallback(prepared_prompt, reason=f"{type(exc).__name__}: {exc}", metadata=metadata)

    def _post_messages(self, request: urllib.request.Request) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _prepare_prompt(self, prompt: str) -> tuple[str, bool]:
        clean = prompt.strip()
        if len(clean) <= self.max_input_chars:
            return clean, False
        head_budget = int(self.max_input_chars * 0.62)
        tail_budget = self.max_input_chars - head_budget
        clipped = (
            clean[:head_budget]
            + "\n\n[... Nanus clipped the middle of this large direct prompt; use document upload/RAG for full-fidelity processing ...]\n\n"
            + clean[-tail_budget:]
        )
        return clipped, True

    def _fallback(self, prompt: str, *, reason: str, metadata: dict[str, Any]) -> LLMResult:
        clean = " ".join(prompt.split()) or "요청"
        excerpt = clean[:360]
        clipped_note = "\n- 입력이 길어 일부가 압축되었습니다. 파일 업로드/RAG 경로를 쓰면 더 정확합니다." if metadata.get("clipped") else ""
        text = (
            f"로컬 Nanus 제한 실행기가 '{excerpt}' 요청을 받았습니다.\n"
            "이 답변은 실제 외부 LLM 호출이 아니라 백엔드가 검증 가능한 형태로 만든 fallback 결과입니다.\n\n"
            "1. 요청을 실행 가능한 목표와 산출물 단위로 분해했습니다.\n"
            "2. 최종 답변, 검증 메타데이터, artifact manifest를 채울 수 있는 결정적 결과를 생성했습니다.\n"
            "3. ANTHROPIC_API_KEY가 설정되면 동일한 경로가 live Anthropic Messages API로 전환됩니다."
            f"{clipped_note}"
        )
        return LLMResult(text=text, provider="local-fallback", live=False, error=reason, metadata={**metadata, "fallbackReason": reason})
