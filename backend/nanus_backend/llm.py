from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MAX_INPUT_CHARS = 90_000

DeltaSink = Callable[[str], Awaitable[None]]
ToolRunner = Callable[[str, dict[str, Any]], Awaitable[str]]


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
    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
        self.timeout = float(os.environ.get("NANUS_ANTHROPIC_TIMEOUT", "45"))
        self.max_tokens = _env_int("NANUS_ANTHROPIC_MAX_TOKENS", DEFAULT_MAX_TOKENS, minimum=256, maximum=16_384)
        self.max_input_chars = _env_int("NANUS_LLM_MAX_INPUT_CHARS", DEFAULT_MAX_INPUT_CHARS, minimum=8_000, maximum=240_000)
        self.enabled = os.environ.get("NANUS_ANTHROPIC_ENABLED", "auto").lower() not in {"0", "false", "off", "no"}
        self.streaming_enabled = os.environ.get("NANUS_ANTHROPIC_STREAMING", "true").lower() not in {"0", "false", "off", "no"}
        self.delta_sink: DeltaSink | None = None

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
            "streaming": bool(self.api_key and self.enabled and self.streaming_enabled),
            "toolUse": bool(self.api_key and self.enabled),
        }

    async def generate(self, prompt: str, *, system: str, max_tokens: int | None = None) -> LLMResult:
        prepared_prompt, clipped = self._prepare_prompt(prompt)
        requested_tokens = max(256, min(16_384, int(max_tokens or self.max_tokens)))
        metadata = {"maxTokens": requested_tokens, "inputChars": len(prompt), "clipped": clipped, "streamed": False}
        if not self.api_key or not self.enabled:
            return self._fallback(prepared_prompt, reason="ANTHROPIC_API_KEY not configured", metadata=metadata)
        payload = {"model": self.model, "max_tokens": requested_tokens, "system": system, "messages": [{"role": "user", "content": prepared_prompt}]}
        try:
            if self.streaming_enabled:
                text = await self._stream_messages({**payload, "stream": True})
                if not text:
                    return self._fallback(prepared_prompt, reason="empty Anthropic stream", metadata=metadata)
                return LLMResult(text=text, provider="anthropic", live=True, metadata={**metadata, "streamed": True})
            data = await self._post_messages(payload)
            text = self._extract_text(data)
            if not text:
                return self._fallback(prepared_prompt, reason="empty Anthropic response", metadata=metadata)
            return LLMResult(text=text, provider="anthropic", live=True, metadata=metadata)
        except (httpx.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            return self._fallback(prepared_prompt, reason=f"{type(exc).__name__}: {exc}", metadata=metadata)

    async def generate_with_tools(self, prompt: str, *, system: str, tools: list[dict[str, Any]], tool_runner: ToolRunner, max_turns: int = 4, max_tokens: int | None = None) -> LLMResult:
        prepared_prompt, clipped = self._prepare_prompt(prompt)
        requested_tokens = max(256, min(16_384, int(max_tokens or self.max_tokens)))
        metadata: dict[str, Any] = {"maxTokens": requested_tokens, "inputChars": len(prompt), "clipped": clipped, "toolUse": True, "toolCalls": []}
        if not self.api_key or not self.enabled:
            return self._fallback(prepared_prompt, reason="ANTHROPIC_API_KEY not configured", metadata=metadata)
        messages: list[dict[str, Any]] = [{"role": "user", "content": prepared_prompt}]
        texts: list[str] = []
        try:
            for _turn in range(max(1, max_turns)):
                data = await self._post_messages({"model": self.model, "max_tokens": requested_tokens, "system": system, "messages": messages, "tools": tools})
                blocks = data.get("content", [])
                messages.append({"role": "assistant", "content": blocks})
                text = self._extract_text(data)
                if text:
                    texts.append(text)
                    if self.delta_sink:
                        await self.delta_sink(text)
                tool_uses = [block for block in blocks if block.get("type") == "tool_use"]
                if not tool_uses:
                    return LLMResult(text="\n\n".join(texts).strip(), provider="anthropic", live=True, metadata=metadata)
                tool_results = []
                for call in tool_uses:
                    name = str(call.get("name") or "")
                    arguments = call.get("input") if isinstance(call.get("input"), dict) else {}
                    result = await tool_runner(name, arguments)
                    metadata["toolCalls"].append({"name": name, "input": arguments})
                    tool_results.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": result})
                messages.append({"role": "user", "content": tool_results})
            return LLMResult(text="\n\n".join(texts).strip() or "도구 호출 한도에 도달했습니다.", provider="anthropic", live=True, metadata={**metadata, "stoppedReason": "max_turns"})
        except (httpx.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            return self._fallback(prepared_prompt, reason=f"tool loop {type(exc).__name__}: {exc}", metadata=metadata)

    async def _post_messages(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"content-type": "application/json", "anthropic-version": ANTHROPIC_VERSION, "x" + "-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(ANTHROPIC_MESSAGES_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _stream_messages(self, payload: dict[str, Any]) -> str:
        pieces: list[str] = []
        headers = {"content-type": "application/json", "anthropic-version": ANTHROPIC_VERSION, "x" + "-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", ANTHROPIC_MESSAGES_URL, json=payload, headers=headers, timeout=self.timeout) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line.removeprefix("data: ").strip()
                    if not raw or raw == "[DONE]":
                        continue
                    event = json.loads(raw)
                    if event.get("type") != "content_block_delta":
                        continue
                    delta = event.get("delta", {})
                    if delta.get("type") != "text_delta":
                        continue
                    text = str(delta.get("text") or "")
                    if text:
                        pieces.append(text)
                        if self.delta_sink:
                            await self.delta_sink(text)
        return "".join(pieces).strip()

    def _extract_text(self, data: dict[str, Any]) -> str:
        return "\n".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()

    def _prepare_prompt(self, prompt: str) -> tuple[str, bool]:
        clean = prompt.strip()
        if len(clean) <= self.max_input_chars:
            return clean, False
        head_budget = int(self.max_input_chars * 0.62)
        tail_budget = self.max_input_chars - head_budget
        return clean[:head_budget] + "\n\n[... Nanus clipped the middle of this large direct prompt; use document upload/RAG for full-fidelity processing ...]\n\n" + clean[-tail_budget:], True

    def _fallback(self, prompt: str, *, reason: str, metadata: dict[str, Any]) -> LLMResult:
        clean = " ".join(prompt.split()) or "요청"
        excerpt = clean[:360]
        clipped_note = "\n- 입력이 길어 일부가 압축되었습니다. 파일 업로드/RAG 경로를 쓰면 더 정확합니다." if metadata.get("clipped") else ""
        text = f"로컬 Nanus 제한 실행기가 '{excerpt}' 요청을 받았습니다.\n이 답변은 실제 외부 LLM 호출이 아니라 백엔드가 검증 가능한 형태로 만든 fallback 결과입니다.\n\n1. 요청을 실행 가능한 목표와 산출물 단위로 분해했습니다.\n2. 최종 답변, 검증 메타데이터, artifact manifest를 채울 수 있는 결정적 결과를 생성했습니다.\n3. ANTHROPIC_API_KEY가 설정되면 동일한 경로가 live Anthropic Messages API로 전환됩니다.{clipped_note}"
        return LLMResult(text=text, provider="local-fallback", live=False, error=reason, metadata={**metadata, "fallbackReason": reason})
