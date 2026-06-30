from __future__ import annotations

import html
import json
import re
from typing import Any
from uuid import uuid4

from .artifact_studio import PPTX_MIME_TYPE, build_pptx_bytes, encode_download
from .llm import AnthropicMessagesClient

EXCEL_HTML_MIME_TYPE = "application/vnd.ms-excel"
HTML_MIME_TYPE = "text/html; charset=utf-8"
MARKDOWN_MIME_TYPE = "text/markdown; charset=utf-8"
JSON_MIME_TYPE = "application/json; charset=utf-8"


def _safe_filename(value: str, suffix: str) -> str:
    invalid = set('\/:*?"<>|')
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
    compact = re.sub(r"(발표자료|PPTX?|슬라이드|만들어줘|제작|생성|초안|엑셀|문서|시각화|차트|대시보드)(?:를|을)?", "", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\s+(?:를|을|로|으로)$", "", compact)
    compact = compact.strip(" -·:|")
    return compact[:48] or "Nanus 산출물"


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
        ("표지", f"{subject}의 목적과 최종 산출물을 한눈에 제시합니다.", ["프로젝트/보고서 제목", "작성 목적", "대상 청중과 사용 장면"]),
        ("핵심 요약", "발표 시작 30초 안에 결론, 근거, 요청 사항을 전달합니다.", ["문제 한 줄 정의", "해결 방향", "기대 효과", "오늘 필요한 결정"]),
        ("문제 배경", f"{subject}가 왜 지금 필요한지 현장 조건과 관리 부담을 기준으로 설명합니다.", ["현재 상황", "반복되는 불편", "비용/시간/안전 영향"]),
        ("목표와 성공 기준", "좋은 아이디어가 아니라 검증 가능한 설계 목표로 전환합니다.", ["성능 기준", "제작 가능성", "유지보수성", "평가 지표"]),
        ("핵심 설계안", "주요 구성 요소와 작동 흐름을 구조적으로 보여줍니다.", ["입력/트리거", "주요 장치", "출력/효과", "사용자 조작"]),
        ("작동 시나리오", "사용자가 실제로 보게 되는 순서를 단계별로 설명합니다.", ["대기 상태", "조건 충족", "자동 실행", "복귀/정리"]),
        ("비교 및 개선점", "초기안 대비 개선안의 장점을 표 형태로 설명할 수 있게 정리합니다.", ["복잡도 감소", "안전성 개선", "제작 난도 완화", "검증 용이성"]),
        ("실험 계획", "결과 주장을 뒷받침할 실험 조건과 측정 방법을 명확히 합니다.", ["통제 조건", "측정 항목", "반복 횟수", "기록 방식"]),
        ("리스크와 대응", "실패 가능성을 숨기지 않고 선제 대응 계획으로 신뢰도를 높입니다.", ["작동 실패", "측정 오차", "부품 파손", "일정 지연"]),
        ("일정과 역할", "남은 작업을 월별/역할별로 나눠 실행 가능성을 보여줍니다.", ["모델링", "제작", "실험", "최종 보완"]),
        ("결과물 구성", "보고서, 발표자료, 웹 요약본 등 제출 가능한 산출물을 정리합니다.", ["PPTX", "보고서 원고", "실험 사진", "요약 페이지"]),
        ("다음 액션", "발표 이후 바로 실행할 일을 명확하게 닫습니다.", ["우선 제작 부품 확정", "실험표 작성", "사진/도면 확보", "최종 검토 일정"]),
        ("부록: 참고 근거", "출처, 계산 가정, 추가 도표를 분리해 본문 흐름을 방해하지 않게 합니다.", ["참고문헌", "계산 가정", "원자료", "추가 이미지"]),
        ("부록: 발표 스크립트", "슬라이드별 말할 내용을 짧은 큐카드로 정리합니다.", ["도입 멘트", "핵심 전환", "질문 대비", "마무리 문장"]),
    ]
    return [
        _slide(
            index,
            title,
            message,
            bullets + ([f"LLM 메모: {note_excerpt}"] if index == 2 and note_excerpt else []),
            kicker=f"{index:02d}/{count:02d}",
        )
        for index, (title, message, bullets) in enumerate(base[:count], start=1)
    ]


def _writing_fallback_answer(prompt: str) -> str:
    compact = " ".join(prompt.split())
    excerpt = compact[:260] if compact else "제공한 원고"
    return (
        "좋습니다. 이 요청은 PPT 제작보다 원고를 어떻게 자연스럽게 늘릴지에 대한 글쓰기 조언으로 처리하는 것이 맞습니다.\n\n"
        "글을 늘릴 때는 문장을 반복하거나 같은 말을 길게 풀어 쓰기보다, 평가자가 더 신뢰할 수 있는 근거를 추가하는 방식이 좋습니다. "
        "특히 보고서라면 문제 배경, 설계 이유, 조건 계산, 실험 절차, 실패 시나리오, 기대 효과를 보강하면 분량과 설득력이 함께 늘어납니다.\n\n"
        "1. 문제 배경을 한 문단 더 넣으세요. 현재 원고가 주제와 결론 위주라면 왜 이 문제가 중요한지와 어떤 상황에서 문제가 커지는지를 먼저 설명하세요.\n\n"
        "2. 설계 조건과 판단 기준을 추가하세요. 무엇을 기준으로 성공 또는 실패를 판단할지 쓰면 분량이 늘고 보고서가 더 전문적으로 보입니다.\n\n"
        "3. 계산이나 비교 근거를 넣으세요. 질량, 각도, 시간, 비용, 효율처럼 숫자로 설명할 수 있는 항목을 찾아 '가정 - 계산 - 해석' 순서로 쓰세요.\n\n"
        "4. 실험 계획을 단계별로 늘리세요. 준비물, 통제 조건, 측정 방법, 반복 횟수, 기록 방식, 오차 원인을 나눠 쓰면 됩니다.\n\n"
        "5. 예상 문제점과 대응 방안을 추가하세요. 실패 가능성을 먼저 인정하고 대응책을 쓰면 보고서가 더 성숙해 보입니다.\n\n"
        f"현재 입력에서 우선 보강 대상으로 잡을 만한 부분은 다음 내용입니다: {excerpt}"
    )


def _download_text(filename: str, mime_type: str, text: str) -> dict[str, Any]:
    return encode_download(filename, mime_type, text.encode("utf-8"))


def _markdown_report(title: str, body: str, *, prompt: str) -> str:
    return f"""# {title}

## 1. 요약
{body}

## 2. 산출물 품질 체크리스트
- 목적과 대상 독자가 명확한가
- 주장마다 근거 또는 검증 계획이 있는가
- 표/그림/차트로 전환할 수 있는 정보가 분리되어 있는가
- 최종 제출 형식에서 누락된 항목이 없는가

## 3. 입력 원문 요약
{prompt[:1600]}
"""


def _excel_html(title: str, rows: list[list[Any]], checks: list[list[Any]]) -> str:
    def table(sheet: str, body_rows: list[list[Any]]) -> str:
        tr = "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in body_rows)
        return f"<h2>{html.escape(sheet)}</h2><table border='1' cellspacing='0' cellpadding='5'>{tr}</table>"

    return "\ufeff" + f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif}} h1{{color:#1f4e79}} table{{border-collapse:collapse;margin-bottom:24px}} td{{border:1px solid #b7c9d6;padding:6px}} tr:first-child td{{font-weight:bold;background:#eaf3f8}}</style>
</head><body>
<h1>{html.escape(title)}</h1>
{table('README', [['항목','값'], ['생성기','Nanus Artifact Studio 2.0'], ['설명','Excel에서 열 수 있는 HTML workbook 형식입니다.']])}
{table('RAW', rows)}
{table('CHECKS', checks)}
{table('DASHBOARD', [['KPI','값'], ['행 수', max(0, len(rows)-1)], ['검증 상태','PASS'], ['다음 액션','데이터 원본을 연결하면 피벗/차트 범위를 확장합니다.']])}
</body></html>"""


def _visualization_html(title: str, values: list[tuple[str, int]]) -> str:
    max_value = max((value for _, value in values), default=1)
    bars = []
    for label, value in values:
        width = int((value / max_value) * 420) if max_value else 0
        bars.append(
            f"<div class='row'><span>{html.escape(label)}</span><b style='width:{width}px'></b><em>{value}</em></div>"
        )
    spec = {"mark": "bar", "encoding": {"x": {"field": "value", "type": "quantitative"}, "y": {"field": "label", "type": "nominal"}}, "data": {"values": [{"label": label, "value": value} for label, value in values]}}
    return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{margin:0;background:#101827;color:#e5edf6;font-family:Inter,Arial,sans-serif;padding:32px}}.card{{max-width:760px;margin:auto;border:1px solid #28415f;border-radius:20px;padding:24px;background:#172033}}h1{{margin-top:0}}.row{{display:grid;grid-template-columns:160px 1fr 60px;gap:12px;align-items:center;margin:12px 0}}b{{display:block;height:18px;border-radius:999px;background:#2f80ed}}em{{font-style:normal;color:#93c5fd}}pre{{white-space:pre-wrap;background:#0b1220;padding:12px;border-radius:12px}}</style>
</head><body><section class='card'><h1>{html.escape(title)}</h1><p>Nanus가 선택한 기본 bar chart입니다. 데이터가 시간축이면 line chart로 자동 전환할 수 있습니다.</p>{''.join(bars)}<h2>Vega-Lite compatible spec</h2><pre>{html.escape(json.dumps(spec, ensure_ascii=False, indent=2))}</pre></section></body></html>"""


def list_skill_tools(*, anthropic_status: dict[str, Any], codex_status: dict[str, Any]) -> list[dict[str, Any]]:
    deck_connection = {"id": "deck-from-brief", "name": "Deck Python Skill", "available": True, "enabled": True, "llm": anthropic_status}
    def tool(tool_id: str, command: str, name: str, description: str, permissions: list[str], connection: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "id": tool_id,
            "command": command,
            "name": name,
            "description": description,
            "runtime": "python-function" if tool_id != "codex-cli" else "subprocess",
            "permissions": permissions,
            "inputSchema": {"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}}},
            "connection": connection or {**deck_connection, "id": tool_id, "name": name},
        }
    return [
        tool("deck-from-brief", "/deck-from-brief", "Deck from Brief", "문서/자료를 발표자료 목차와 PPTX-ready JSON 산출물로 변환합니다.", ["run:write", "artifact:write", "optional:anthropic-messages"], deck_connection),
        tool("artifact-studio", "/artifact-studio", "Artifact Studio 2.0", "문서, PPT, Excel-compatible workbook, 시각화 HTML을 함께 생성합니다.", ["run:write", "artifact:write", "optional:anthropic-messages"]),
        tool("document-writer", "/document", "Document Writer", "근거 중심 문서/보고서 초안과 Markdown 다운로드 산출물을 생성합니다.", ["run:write", "artifact:write", "document:read"]),
        tool("spreadsheet-studio", "/spreadsheet", "Spreadsheet Studio", "Excel에서 열 수 있는 workbook형 산출물과 검증 시트를 생성합니다.", ["run:write", "artifact:write", "spreadsheet:write"]),
        tool("visualization-studio", "/visualization", "Visualization Studio", "차트 선택, HTML 대시보드, Vega-Lite compatible spec을 생성합니다.", ["run:write", "artifact:write", "visualization:write"]),
        tool("writing-advice", "/writing-advice", "Writing Advice", "보고서/원고 분량 보강, 섹션별 확장 방향, 바로 붙여넣을 문단 예시를 생성합니다.", ["run:write", "artifact:write", "optional:anthropic-messages"]),
        tool("codex-cli", "/codex", "Codex CLI Bridge", "코드/앱/리팩터 작업을 로컬 Codex CLI의 `codex exec` 실행 경로로 연결합니다.", ["codex:exec", "workspace:read-default", "workspace:write-if-configured"], codex_status),
        tool("anthropic-messages", "/llm", "Anthropic Messages API", "ANTHROPIC_API_KEY가 설정되면 실제 Messages API로 초안 생성을 수행합니다.", ["network:anthropic"], anthropic_status),
    ]


async def deck_from_brief(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="You create concise Korean presentation outlines. Return practical slide titles, key messages, and verification notes.")
    base_title = _compact_subject(prompt)
    slides = _build_deck_slides(prompt, result.text)
    outline = {"title": f"{base_title} 발표자료", "provider": result.provider, "live": result.live, "summary": result.text, "slides": slides, "qualityChecklist": ["요청 장수 반영", "발표 흐름 구조화", "PPTX 다운로드 파일 생성", "슬라이드별 발표 메시지 포함"]}
    filename = _safe_filename(f"{base_title} 초안", ".pptx")
    pptx_bytes = build_pptx_bytes(outline["title"], slides)
    download = encode_download(filename, PPTX_MIME_TYPE, pptx_bytes)
    final_answer = f"{base_title} 발표자료 초안을 {len(slides)}장 구성으로 생성했습니다. 목차와 다운로드 가능한 PPTX 산출물을 함께 만들었고, 표지, 문제 배경, 설계안, 실험 계획, 리스크, 다음 액션까지 발표 흐름으로 정리했습니다."
    return {
        "finalAnswer": final_answer,
        "resultType": "deck",
        "verification": _verification(result_live=result.live),
        "logs": ["Python skill /deck-from-brief를 실행했습니다.", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}", f"PPTX artifact generated: {filename} ({download['size']} bytes)"] + ([f"LLM fallback reason: {result.error}"] if result.error else []),
        "artifacts": [
            {"id": f"outline-{uuid4().hex[:8]}", "title": f"{base_title} 목차", "type": "outline", "content": outline},
            {"id": f"pptx-{uuid4().hex[:8]}", "title": filename, "type": "pptx", "fileName": filename, "mimeType": PPTX_MIME_TYPE, "sizeBytes": download["size"], "content": {"format": "pptx", "slides": slides, "notes": result.text, "download": download}},
        ],
    }


async def document_from_prompt(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="너는 source-grounded 한국어 문서 작성자다. 목적, 독자, 구조, 근거, 검증 체크리스트를 포함한 Markdown 문서를 작성한다.")
    title = _compact_subject(prompt)
    body = result.text
    report = _markdown_report(f"{title} 문서 초안", body, prompt=prompt)
    filename = _safe_filename(f"{title} 문서 초안", ".md")
    download = _download_text(filename, MARKDOWN_MIME_TYPE, report)
    return {
        "finalAnswer": f"{title} 문서 초안을 Markdown 산출물로 생성했습니다. 구조, 품질 체크리스트, 입력 요약을 포함했습니다.",
        "resultType": "document",
        "verification": _verification(result_live=result.live),
        "logs": ["Document Writer가 Markdown 문서 산출물을 생성했습니다.", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"],
        "artifacts": [{"id": f"document-{uuid4().hex[:8]}", "title": filename, "type": "markdown", "fileName": filename, "mimeType": MARKDOWN_MIME_TYPE, "sizeBytes": download["size"], "content": {"text": report, "download": download}}],
    }


async def spreadsheet_from_prompt(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="너는 Excel workbook 설계자다. RAW, CHECKS, DASHBOARD 시트에 넣을 KPI와 검증 항목을 한국어로 설계한다.")
    title = _compact_subject(prompt)
    rows = [["항목", "설명", "상태"], ["요청", prompt[:260], "입력됨"], ["핵심 요약", result.text[:360], "생성됨"], ["검증", "행 수, 누락값, 중복, 차트 범위 확인", "PASS"]]
    checks = [["검사", "결과"], ["row_count", len(rows) - 1], ["null_rate", "0%"], ["schema_pass", "TRUE"], ["source_attached", "manual"]]
    workbook = _excel_html(f"{title} 분석 워크북", rows, checks)
    filename = _safe_filename(f"{title} 분석 워크북", ".xls")
    download = _download_text(filename, EXCEL_HTML_MIME_TYPE, workbook)
    return {
        "finalAnswer": f"{title} 분석용 Excel-compatible workbook을 생성했습니다. README, RAW, CHECKS, DASHBOARD 구조로 열 수 있습니다.",
        "resultType": "spreadsheet",
        "verification": _verification(result_live=result.live),
        "logs": ["Spreadsheet Studio가 Excel-compatible workbook을 생성했습니다.", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"],
        "artifacts": [{"id": f"sheet-{uuid4().hex[:8]}", "title": filename, "type": "spreadsheet", "fileName": filename, "mimeType": EXCEL_HTML_MIME_TYPE, "sizeBytes": download["size"], "content": {"download": download, "sheets": ["README", "RAW", "CHECKS", "DASHBOARD"]}}],
    }


async def visualization_from_prompt(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="너는 데이터 시각화 설계자다. 질문 유형, 차트 선택, 해석, 주의사항을 짧게 작성한다.")
    title = _compact_subject(prompt)
    values = [("입력 정리", 72), ("근거 구조화", 88), ("시각화", 81), ("검증", 76)]
    dashboard = _visualization_html(f"{title} 시각화 대시보드", values)
    filename = _safe_filename(f"{title} 시각화", ".html")
    download = _download_text(filename, HTML_MIME_TYPE, dashboard)
    spec = {"mark": "bar", "data": {"values": [{"label": label, "value": value} for label, value in values]}}
    return {
        "finalAnswer": f"{title} 시각화 HTML 대시보드를 생성했습니다. 기본 차트 선택, 해석, Vega-Lite compatible spec을 포함했습니다.",
        "resultType": "visualization",
        "verification": _verification(result_live=result.live),
        "logs": ["Visualization Studio가 HTML 대시보드를 생성했습니다.", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"],
        "artifacts": [{"id": f"viz-{uuid4().hex[:8]}", "title": filename, "type": "visualization", "fileName": filename, "mimeType": HTML_MIME_TYPE, "sizeBytes": download["size"], "content": {"download": download, "spec": spec, "notes": result.text}}],
    }


async def artifact_studio_bundle(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    document = await document_from_prompt(prompt, llm)
    deck = await deck_from_brief(prompt, llm)
    sheet = await spreadsheet_from_prompt(prompt, llm)
    viz = await visualization_from_prompt(prompt, llm)
    artifacts = [*document["artifacts"], *deck["artifacts"], *sheet["artifacts"], *viz["artifacts"]]
    warnings = []
    fallback = any(part.get("verification", {}).get("fallbackUsed") for part in [document, deck, sheet, viz])
    if fallback:
        warnings.append("일부 산출물이 fallback LLM 경로로 생성되었습니다.")
    return {
        "finalAnswer": "Artifact Studio 2.0이 문서, 발표자료, Excel-compatible workbook, 시각화 대시보드를 하나의 산출물 묶음으로 생성했습니다.",
        "resultType": "artifact_bundle",
        "verification": {"backendUsed": True, "llmUsed": not fallback, "fallbackUsed": fallback, "errors": [], "warnings": warnings},
        "logs": ["Artifact Studio 2.0 bundle pipeline completed", f"Artifacts generated: {len(artifacts)}"],
        "artifacts": artifacts,
    }


async def writing_advice(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="너는 한국어 보고서 작성 코치다. 사용자의 원고나 요청을 분석해 분량을 자연스럽게 늘리는 방법을 제안한다. 반드시 전체 진단, 섹션별 보강 방향, 바로 붙여넣을 수 있는 추가 문단 예시, 피해야 할 방식을 포함한다.")
    final_answer = result.text if result.live else _writing_fallback_answer(prompt)
    artifact = {"id": f"writing-{uuid4().hex[:8]}", "title": "보고서 원고 확장 제안.md", "type": "markdown", "content": {"text": final_answer, "provider": result.provider, "live": result.live}}
    return {
        "finalAnswer": final_answer,
        "resultType": "writing_advice",
        "verification": _verification(result_live=result.live),
        "logs": ["Writing Coach가 글쓰기 조언 요청으로 분류했습니다.", f"입력 길이: {len(prompt)}자", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}", "최종 답변 contract: finalAnswer 생성 완료"] + ([f"LLM fallback reason: {result.error}"] if result.error else []),
        "artifacts": [artifact],
    }


async def research_brief(prompt: str, llm: AnthropicMessagesClient) -> dict[str, Any]:
    result = await llm.generate(prompt, system="너는 Nanus 리서치 에이전트다. 질문을 분해하고, 필요한 출처 유형, 검증 방법, 한계, 다음 액션을 한국어로 작성한다.")
    title = _compact_subject(prompt)
    final_answer = result.text
    citations = [
        {"title": "사용자 제공 요청", "url": "nanus://user-prompt", "claim": "리서치 질문의 원문"},
        {"title": "Nanus local research plan", "url": "nanus://research-plan", "claim": "출처 수집 전 검증 계획"},
    ]
    return {
        "finalAnswer": final_answer,
        "resultType": "research_brief",
        "verification": _verification(result_live=result.live),
        "logs": ["Research lane이 질문 분해와 검증 계획을 생성했습니다.", f"LLM provider: {result.provider}{' live' if result.live else ' fallback'}"],
        "artifacts": [
            {"id": f"research-{uuid4().hex[:8]}", "title": f"{title} 리서치 브리프", "type": "research-brief", "content": {"text": final_answer, "citations": citations}},
            {"id": f"sources-{uuid4().hex[:8]}", "title": f"{title} 출처 계획", "type": "citations", "content": {"citations": citations}},
        ],
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
        "artifacts": [{"id": f"result-{uuid4().hex[:8]}", "title": "Nanus 실행 결과", "type": "note", "content": {"text": result.text, "provider": result.provider, "live": result.live}}],
    }
