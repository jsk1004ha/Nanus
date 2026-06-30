from __future__ import annotations

from typing import Any
from uuid import uuid4

from .artifact_studio import PPTX_MIME_TYPE, build_pptx_bytes, encode_download
from .llm import AnthropicMessagesClient


def _safe_filename(value: str, suffix: str) -> str:
    invalid = set('\\/:*?"<>|')
    cleaned = "".join("_" if char in invalid else char for char in value).strip(" .")
    return f"{(cleaned or 'nanus-artifact')[:80]}{suffix}"


def list_skill_tools(*, anthropic_status: dict[str, Any], codex_status: dict[str, Any]) -> list[dict[str, Any]]:
    deck_connection = {
        "id": "deck-from-brief",
        "name": "Deck Python Skill",
        "available": True,
        "enabled": True,
        "llm": anthropic_status,
    }
    return [
        {
            "id": "deck-from-brief",
            "command": "/deck-from-brief",
            "name": "Deck from Brief",
            "description": "문서/자료를 발표자료 목차와 PPTX-ready JSON 산출물로 변환합니다.",
            "runtime": "python-function",
            "permissions": ["run:write", "artifact:write", "optional:anthropic-messages"],
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": deck_connection,
        },
        {
            "id": "artifact-studio",
            "command": "/artifact-studio",
            "name": "Artifact Studio",
            "description": "HWPX/PDF/브리프 입력을 구조화하고 실제 다운로드 가능한 PPTX 산출물로 렌더링합니다.",
            "runtime": "python-function",
            "permissions": ["run:write", "artifact:write", "optional:anthropic-messages"],
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": {**deck_connection, "id": "artifact-studio", "name": "Artifact Studio"},
        },
        {
            "id": "codex-cli",
            "command": "/codex",
            "name": "Codex CLI Bridge",
            "description": "코드/앱/리팩터 작업을 로컬 Codex CLI의 `codex exec` 실행 경로로 연결합니다.",
            "runtime": "subprocess",
            "permissions": ["codex:exec", "workspace:read-default", "workspace:write-if-configured"],
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": codex_status,
        },
        {
            "id": "anthropic-messages",
            "command": "/llm",
            "name": "Anthropic Messages API",
            "description": "ANTHROPIC_API_KEY가 설정되면 실제 Messages API로 초안 생성을 수행합니다.",
            "runtime": "https",
            "permissions": ["network:anthropic"],
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": anthropic_status,
        },
    ]


async def deck_from_brief(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(
        prompt,
        system=(
            "You create concise Korean presentation outlines. Return practical slide titles, "
            "key messages, and verification notes."
        ),
    )
    compact = " ".join(prompt.split()) or "새 발표자료"
    base_title = compact[:36]
    slides = [
        {"number": 1, "title": "문제 정의", "message": f"{base_title}의 목적과 성공 기준을 정리합니다."},
        {"number": 2, "title": "핵심 데이터", "message": "입력 자료에서 의사결정에 필요한 근거를 추출합니다."},
        {"number": 3, "title": "실행 제안", "message": "다음 액션, 담당, 검증 지표를 제안합니다."},
    ]
    outline = {
        "title": f"{base_title} 발표자료",
        "provider": result.provider,
        "live": result.live,
        "summary": result.text,
        "slides": slides,
        "qualityChecklist": ["메시지-근거 연결", "12장 확장 가능 구조", "PPTX 다운로드 파일 생성"],
    }
    filename = _safe_filename(f"{base_title} 초안", ".pptx")
    pptx_bytes = build_pptx_bytes(outline["title"], slides)
    download = encode_download(filename, PPTX_MIME_TYPE, pptx_bytes)
    return {
        "logs": [
            "Python skill /deck-from-brief를 실행했습니다.",
            f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}",
            f"PPTX artifact generated: {filename} ({download['size']} bytes)",
        ] + ([f"LLM fallback reason: {result.error}"] if result.error else []),
        "artifacts": [
            {"id": f"outline-{uuid4().hex[:8]}", "title": f"{base_title} 목차", "type": "outline", "content": outline},
            {
                "id": f"pptx-{uuid4().hex[:8]}",
                "title": filename,
                "type": "pptx",
                "fileName": filename,
                "mimeType": PPTX_MIME_TYPE,
                "sizeBytes": download["size"],
                "content": {"format": "pptx", "slides": slides, "notes": result.text, "download": download},
            },
        ],
    }


async def generic_llm_result(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="You are the Nanus execution backend. Produce concise Korean task output.")
    logs = [f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"]
    if result.error:
        logs.append(f"LLM fallback reason: {result.error}")
    return {
        "logs": logs,
        "artifacts": [
            {
                "id": f"result-{uuid4().hex[:8]}",
                "title": "Nanus 실행 결과",
                "type": "note",
                "content": {"text": result.text, "provider": result.provider, "live": result.live},
            }
        ],
    }
