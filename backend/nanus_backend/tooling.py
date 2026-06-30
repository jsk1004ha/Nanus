from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from .artifact_studio import PPTX_MIME_TYPE, build_pptx_bytes, encode_download
from .llm import AnthropicMessagesClient


def _safe_filename(value: str, suffix: str) -> str:
    invalid = set('\\/:*?"<>|')
    cleaned = "".join("_" if char in invalid else char for char in value).strip(" .")
    return f"{(cleaned or 'nanus-artifact')[:80]}{suffix}"


def _verification(*, result_live: bool, errors: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "backendUsed": True,
        "llmUsed": result_live,
        "fallbackUsed": not result_live,
        "errors": errors or [],
        "warnings": warnings or ([] if result_live else ["LLM 키가 없어 로컬 fallback 답변을 생성했습니다."]),
    }


def _target_slide_count(prompt: str) -> int:
    match = re.search(r"(\d{1,2})\s*(?:장|slides?|페이지)", prompt, re.IGNORECASE)
    if not match:
        return 8
    return max(5, min(14, int(match.group(1))))


def _compact_subject(prompt: str) -> str:
    compact = " ".join(prompt.split())
    compact = re.sub(r"^/\S+\s*", "", compact)
    compact = re.sub(r"\d{1,2}\s*(?:장|slides?|페이지)(?:짜리)?", "", compact, flags=re.IGNORECASE)
    compact = re.sub(r"(발표자료|PPTX?|슬라이드|만들어줘|제작|생성|초안)(?:를|을)?", "", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\s+(?:를|을|로|으로)$", "", compact)
    compact = compact.strip(" -·:|")
    return compact[:48] or "Nanus 발표자료"


def _slide(number: int, title: str, message: str, bullets: list[str], *, kicker: str = "") -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "message": message,
        "bullets": bullets[:4],
        "kicker": kicker or f"{number:02d}",
    }


def _build_deck_slides(prompt: str, llm_notes: str) -> list[dict[str, Any]]:
    count = _target_slide_count(prompt)
    subject = _compact_subject(prompt)
    note_excerpt = " ".join(llm_notes.split())[:120] if llm_notes else ""
    base = [
        (
            "표지",
            f"{subject}의 목적과 최종 산출물을 한눈에 제시합니다.",
            ["프로젝트/보고서 제목", "작성 목적", "대상 청중과 사용 장면"],
        ),
        (
            "핵심 요약",
            "발표 시작 30초 안에 결론, 근거, 요청 사항을 전달합니다.",
            ["문제 한 줄 정의", "해결 방향", "기대 효과", "오늘 필요한 결정"],
        ),
        (
            "문제 배경",
            f"{subject}가 왜 지금 필요한지 현장 조건과 관리 부담을 기준으로 설명합니다.",
            ["현재 상황", "반복되는 불편", "비용/시간/안전 영향"],
        ),
        (
            "목표와 성공 기준",
            "좋은 아이디어가 아니라 검증 가능한 설계 목표로 전환합니다.",
            ["성능 기준", "제작 가능성", "유지보수성", "평가 지표"],
        ),
        (
            "핵심 설계안",
            "주요 구성 요소와 작동 흐름을 구조적으로 보여줍니다.",
            ["입력/트리거", "주요 장치", "출력/효과", "사용자 조작"],
        ),
        (
            "작동 시나리오",
            "사용자가 실제로 보게 되는 순서를 단계별로 설명합니다.",
            ["대기 상태", "조건 충족", "자동 실행", "복귀/정리"],
        ),
        (
            "비교 및 개선점",
            "초기안 대비 개선안의 장점을 표 형태로 설명할 수 있게 정리합니다.",
            ["복잡도 감소", "안전성 개선", "제작 난도 완화", "검증 용이성"],
        ),
        (
            "실험 계획",
            "결과 주장을 뒷받침할 실험 조건과 측정 방법을 명확히 합니다.",
            ["통제 조건", "측정 항목", "반복 횟수", "기록 방식"],
        ),
        (
            "리스크와 대응",
            "실패 가능성을 숨기지 않고 선제 대응 계획으로 신뢰도를 높입니다.",
            ["작동 실패", "측정 오차", "부품 파손", "일정 지연"],
        ),
        (
            "일정과 역할",
            "남은 작업을 월별/역할별로 나눠 실행 가능성을 보여줍니다.",
            ["모델링", "제작", "실험", "최종 보완"],
        ),
        (
            "결과물 구성",
            "보고서, 발표자료, 웹 요약본 등 제출 가능한 산출물을 정리합니다.",
            ["PPTX", "보고서 원고", "실험 사진", "요약 페이지"],
        ),
        (
            "다음 액션",
            "발표 이후 바로 실행할 일을 명확하게 닫습니다.",
            ["우선 제작 부품 확정", "실험표 작성", "사진/도면 확보", "최종 검토 일정"],
        ),
        (
            "부록: 참고 근거",
            "출처, 계산 가정, 추가 도표를 분리해 본문 흐름을 방해하지 않게 합니다.",
            ["참고문헌", "계산 가정", "원자료", "추가 이미지"],
        ),
        (
            "부록: 발표 스크립트",
            "슬라이드별 말할 내용을 짧은 큐카드로 정리합니다.",
            ["도입 멘트", "핵심 전환", "질문 대비", "마무리 문장"],
        ),
    ]
    slides = [
        _slide(
            index,
            title,
            message,
            bullets + ([f"LLM 메모: {note_excerpt}"] if index == 2 and note_excerpt else []),
            kicker=f"{index:02d}/{count:02d}",
        )
        for index, (title, message, bullets) in enumerate(base[:count], start=1)
    ]
    return slides


def _writing_fallback_answer(prompt: str) -> str:
    compact = " ".join(prompt.split())
    excerpt = compact[:260] if compact else "제공한 원고"
    return (
        "좋습니다. 이 요청은 PPT 제작보다 원고를 어떻게 자연스럽게 늘릴지에 대한 글쓰기 조언으로 처리하는 것이 맞습니다.\n\n"
        "글을 늘릴 때는 문장을 반복하거나 같은 말을 길게 풀어 쓰기보다, 평가자가 더 신뢰할 수 있는 근거를 추가하는 방식이 좋습니다. "
        "특히 보고서라면 문제 배경, 설계 이유, 조건 계산, 실험 절차, 실패 시나리오, 기대 효과를 보강하면 분량과 설득력이 함께 늘어납니다.\n\n"
        "1. 문제 배경을 한 문단 더 넣으세요.\n"
        "현재 원고가 주제와 결론 위주라면, 왜 이 문제가 중요한지와 어떤 상황에서 문제가 커지는지를 먼저 설명하세요. "
        "예를 들어 학교, 공공시설, 실험 환경처럼 관리자가 매일 확인하기 어려운 조건을 붙이면 글이 자연스럽게 확장됩니다.\n\n"
        "추가 문단 예시:\n"
        "이 주제는 단순히 장치를 만드는 활동에 그치지 않고, 실제 사용 환경에서 반복적으로 발생하는 관리 문제를 줄이기 위한 해결 방안을 찾는 과정이다. "
        "특히 사람이 직접 확인하기 어렵거나 관리 주기가 긴 환경에서는 작은 오염, 마찰, 오차가 누적되어 성능 저하로 이어질 수 있다. "
        "따라서 본 설계는 기능 구현뿐 아니라 유지관리 가능성과 반복 사용성을 함께 고려해야 한다.\n\n"
        "2. 설계 조건과 판단 기준을 추가하세요.\n"
        "무엇을 기준으로 성공 또는 실패를 판단할지 쓰면 분량이 늘고 보고서가 더 전문적으로 보입니다. "
        "예를 들어 작동 시간, 안정성, 비용, 제작 난이도, 재료 선택 이유를 각각 짧은 문단으로 분리할 수 있습니다.\n\n"
        "3. 계산이나 비교 근거를 넣으세요.\n"
        "정확한 실험값이 없더라도 가정값을 두고 간단한 계산 과정을 보여주면 좋습니다. "
        "질량, 각도, 시간, 비용, 효율처럼 숫자로 설명할 수 있는 항목을 찾아 '가정 - 계산 - 해석' 순서로 쓰세요.\n\n"
        "4. 실험 계획을 단계별로 늘리세요.\n"
        "실험은 '한다'고만 쓰지 말고 준비물, 통제 조건, 측정 방법, 반복 횟수, 기록 방식, 오차 원인을 나눠 쓰면 됩니다. "
        "이 부분은 분량을 늘리면서도 내용이 빈약해 보이지 않는 가장 안전한 구간입니다.\n\n"
        "5. 예상 문제점과 대응 방안을 추가하세요.\n"
        "실패 가능성을 먼저 인정하고 대응책을 쓰면 보고서가 더 성숙해 보입니다. "
        "예상 문제는 재료 파손, 측정 오차, 환경 변화, 작동 불안정, 제작 시간 부족 등으로 나눌 수 있습니다.\n\n"
        "피해야 할 방식도 있습니다. 같은 문장을 반복하거나, 형용사만 많이 붙이거나, 결론을 여러 번 말하는 방식은 분량은 늘어도 품질이 떨어집니다. "
        "대신 각 문단에 '왜 필요한가', '어떻게 확인할 것인가', '실패하면 어떻게 할 것인가' 중 하나를 추가하세요.\n\n"
        f"현재 입력에서 우선 보강 대상으로 잡을 만한 부분은 다음 내용입니다: {excerpt}"
    )


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
            "id": "writing-advice",
            "command": "/writing-advice",
            "name": "Writing Advice",
            "description": "보고서/원고 분량 보강, 섹션별 확장 방향, 바로 붙여넣을 문단 예시를 생성합니다.",
            "runtime": "python-function",
            "permissions": ["run:write", "artifact:write", "optional:anthropic-messages"],
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": {**deck_connection, "id": "writing-advice", "name": "Writing Advice"},
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
    base_title = _compact_subject(prompt)
    slides = _build_deck_slides(prompt, result.text)
    outline = {
        "title": f"{base_title} 발표자료",
        "provider": result.provider,
        "live": result.live,
        "summary": result.text,
        "slides": slides,
        "qualityChecklist": ["요청 장수 반영", "발표 흐름 구조화", "PPTX 다운로드 파일 생성", "슬라이드별 발표 메시지 포함"],
    }
    filename = _safe_filename(f"{base_title} 초안", ".pptx")
    pptx_bytes = build_pptx_bytes(outline["title"], slides)
    download = encode_download(filename, PPTX_MIME_TYPE, pptx_bytes)
    final_answer = (
        f"{base_title} 발표자료 초안을 {len(slides)}장 구성으로 생성했습니다. 목차와 다운로드 가능한 PPTX 산출물을 함께 만들었고, "
        "표지, 문제 배경, 설계안, 실험 계획, 리스크, 다음 액션까지 발표 흐름으로 정리했습니다."
    )
    return {
        "finalAnswer": final_answer,
        "resultType": "deck",
        "verification": _verification(result_live=result.live),
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


async def writing_advice(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(
        prompt,
        system=(
            "너는 한국어 보고서 작성 코치다. 사용자의 원고나 요청을 분석해 분량을 자연스럽게 늘리는 방법을 제안한다. "
            "반드시 전체 진단, 섹션별 보강 방향, 바로 붙여넣을 수 있는 추가 문단 예시, 피해야 할 방식을 포함한다."
        ),
    )
    final_answer = result.text if result.live else _writing_fallback_answer(prompt)
    artifact = {
        "id": f"writing-{uuid4().hex[:8]}",
        "title": "보고서 원고 확장 제안.md",
        "type": "markdown",
        "content": {"text": final_answer, "provider": result.provider, "live": result.live},
    }
    return {
        "finalAnswer": final_answer,
        "resultType": "writing_advice",
        "verification": _verification(result_live=result.live),
        "logs": [
            "Writing Coach가 글쓰기 조언 요청으로 분류했습니다.",
            f"입력 길이: {len(prompt)}자",
            f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}",
            "최종 답변 contract: finalAnswer 생성 완료",
        ] + ([f"LLM fallback reason: {result.error}"] if result.error else []),
        "artifacts": [artifact],
    }


async def generic_llm_result(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="You are the Nanus execution backend. Produce concise Korean task output.")
    logs = [f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"]
    if result.error:
        logs.append(f"LLM fallback reason: {result.error}")
    return {
        "finalAnswer": result.text,
        "resultType": "answer",
        "verification": _verification(result_live=result.live),
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
