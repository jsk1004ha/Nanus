from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from .browser_tools import BrowserSafetyError, browser_snapshot
from .llm import AnthropicMessagesClient


def _source_artifact(title: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": f"sources-{uuid4().hex[:8]}", "title": f"{title} 출처", "type": "citations", "content": {"citations": sources}}


def _research_artifact(title: str, text: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": f"research-{uuid4().hex[:8]}", "title": f"{title} 리서치 브리프", "type": "research-brief", "content": {"text": text, "citations": sources}}


def _compact_title(prompt: str) -> str:
    return " ".join(prompt.split())[:48] or "Nanus 리서치"


async def research_brief(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    title = _compact_title(prompt)
    sources: list[dict[str, Any]] = []

    async def run_tool(name: str, arguments: dict[str, Any]) -> str:
        if name != "browser_fetch":
            return json.dumps({"error": f"unknown tool {name}"}, ensure_ascii=False)
        url = str(arguments.get("url") or "").strip()
        if not url:
            return json.dumps({"error": "missing url"}, ensure_ascii=False)
        try:
            snapshot = await browser_snapshot(url)
            item = {"title": snapshot.title, "url": snapshot.final_url, "claim": "browser_fetch evidence", "engine": snapshot.engine, "text": snapshot.text[:1200]}
            sources.append(item)
            return json.dumps(item, ensure_ascii=False)
        except (BrowserSafetyError, Exception) as exc:
            return json.dumps({"error": str(exc), "url": url}, ensure_ascii=False)

    tools = [
        {
            "name": "browser_fetch",
            "description": "Fetch a public http(s) page in read-only mode and return title, final URL, and readable body text. Use it for concrete public sources only.",
            "input_schema": {"type": "object", "required": ["url"], "properties": {"url": {"type": "string", "description": "Public http(s) URL"}}},
        }
    ]
    system = (
        "너는 Nanus 리서치 에이전트다. 질문을 분해하고, 필요한 경우 browser_fetch 도구로 공개 URL을 확인한다. "
        "확인하지 않은 정보는 확정 사실처럼 쓰지 말고 '검증 필요'로 표시한다. "
        "최종 답변은 핵심 결론, 확인한 근거, 상충 가능성, 다음 조사 액션으로 구성한다."
    )
    result = await llm.generate_with_tools(prompt, system=system, tools=tools, tool_runner=run_tool, max_turns=4)
    if not sources:
        sources = [
            {"title": "사용자 제공 요청", "url": "nanus://user-prompt", "claim": "리서치 질문의 원문"},
            {"title": "Nanus local research plan", "url": "nanus://research-plan", "claim": "출처 수집 전 검증 계획"},
        ]
    warnings = [] if result.live else ["실제 웹 도구 루프 대신 로컬 fallback 연구 계획을 생성했습니다."]
    if result.live and not result.metadata.get("toolCalls"):
        warnings.append("모델이 browser_fetch 도구를 호출하지 않았습니다. 공개 URL이 필요한 주장에는 추가 검증이 필요합니다.")
    return {
        "finalAnswer": result.text,
        "resultType": "research_brief",
        "verification": {"backendUsed": True, "llmUsed": result.live, "fallbackUsed": not result.live, "errors": [], "warnings": warnings},
        "logs": [f"Research lane provider: {result.provider}{' live' if result.live else ' fallback'}", f"Tool calls: {len(result.metadata.get('toolCalls', []))}"],
        "artifacts": [_research_artifact(title, result.text, sources), _source_artifact(title, sources)],
    }
