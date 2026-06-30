from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

RunKind = str

COMMAND_LABELS: dict[RunKind, str] = {
    "deck": "발표자료 제작",
    "writing": "글쓰기 조언",
    "document": "문서 작성",
    "spreadsheet": "엑셀 제작",
    "visualization": "시각화 제작",
    "site": "웹사이트 구축",
    "app": "앱 개발",
    "design": "디자인 정리",
    "research": "조사",
    "schedule": "예약 실행",
    "library": "라이브러리 작업",
    "agent": "에이전트 구성",
    "general": "일반 실행",
}

RUN_WORKERS: dict[RunKind, str] = {
    "deck": "Artifact Studio + Presenton",
    "writing": "Writing Coach",
    "document": "Document Writer",
    "spreadsheet": "Spreadsheet Studio",
    "visualization": "Visualization Studio",
    "site": "Web Builder + Codex",
    "app": "Codex Lane",
    "design": "Design System Agent",
    "research": "Research",
    "schedule": "Scheduler",
    "library": "Library Indexer",
    "agent": "Planner",
    "general": "Nanus Executor",
}

ARTIFACTS: dict[RunKind, list[tuple[str, str, str]]] = {
    "deck": [("outline", "목차", "outline"), ("pptx", "초안.pptx", "pptx")],
    "writing": [("writing-advice", "보고서 원고 확장 제안.md", "markdown")],
    "document": [("document", "문서 초안.md", "markdown")],
    "spreadsheet": [("workbook", "분석 워크북.xls", "spreadsheet")],
    "visualization": [("dashboard", "시각화.html", "visualization")],
    "research": [("brief", "리서치 브리프", "research-brief"), ("sources", "출처 목록", "citations")],
    "site": [("wireframe", "페이지 구조", "wireframe"), ("preview", "미리보기", "web")],
    "app": [("tasks", "구현 태스크", "task-list"), ("checks", "검증 체크", "test-plan")],
    "design": [("tokens", "토큰", "design-tokens"), ("qa", "QA", "design-qa")],
    "schedule": [("schedule", "예약", "schedule")],
    "library": [("library", "검색 결과", "library")],
    "agent": [("graph", "에이전트 그래프", "graph")],
    "general": [("result", "결과", "note")],
}


def split_command(input_text: str) -> tuple[str, str]:
    trimmed = input_text.strip()
    if not trimmed:
        return "/run", ""
    parts = trimmed.split()
    first = parts[0]
    if first.startswith("/"):
        return first, " ".join(parts[1:]).strip()
    return "/run", trimmed


def _has(haystack: str, tokens: list[str]) -> bool:
    return any(token in haystack for token in tokens)


def detect_run_kind(command: str, prompt: str) -> RunKind:
    haystack = f"{command} {prompt}".lower()
    if command == "/deck-from-brief":
        return "deck"
    if command in {"/document", "/doc", "/report"} or _has(haystack, ["보고서", "문서", "docx", "markdown", "원고"]):
        return "document"
    if command in {"/spreadsheet", "/excel", "/xlsx"} or _has(haystack, ["엑셀", "excel", "xlsx", "스프레드시트", "워크북"]):
        return "spreadsheet"
    if command in {"/visualization", "/viz", "/chart", "/dashboard"} or _has(haystack, ["시각화", "차트", "그래프", "dashboard", "대시보드"]):
        return "visualization"
    if _has(haystack, ["글 늘릴", "글늘릴", "늘릴방법", "늘릴 방법", "분량", "보강", "확장", "문단 추가", "문장 추가", "첨삭"]):
        return "writing"
    if _has(haystack, ["artifact-studio", "deck", "ppt", "pdf", "hwpx", "발표", "슬라이드"]):
        return "deck"
    if _has(haystack, ["site", "web", "웹사이트"]):
        return "site"
    if _has(haystack, ["app", "desktop", "앱"]):
        return "app"
    if _has(haystack, ["design", "디자인"]):
        return "design"
    if _has(haystack, ["research", "리서치", "조사", "출처", "근거"]):
        return "research"
    if _has(haystack, ["schedule", "예약"]):
        return "schedule"
    if _has(haystack, ["library", "라이브러리"]):
        return "library"
    if _has(haystack, ["agent", "에이전트"]):
        return "agent"
    return "general"


def summarize_run_title(prompt: str, command: str, kind: RunKind) -> str:
    source = prompt.strip() or COMMAND_LABELS.get(kind) or command
    return f"{source[:43]}..." if len(source) > 44 else source


def build_run_steps(kind: RunKind, prompt: str, command: str) -> list[dict[str, Any]]:
    detail = prompt or command
    special = {
        "document": [("outline", "문서 구조 설계"), ("draft", "본문 작성"), ("export", "문서 내보내기")],
        "spreadsheet": [("schema", "시트 구조 설계"), ("workbook", "워크북 생성"), ("verify", "범위 검증")],
        "visualization": [("question", "질문 유형 분석"), ("chart", "차트 선택"), ("render", "대시보드 렌더링")],
    }
    default = [("read", "요청 해석"), ("plan", "실행 계획 생성"), ("result", "결과 작성")]
    deck = [("brief", "요구사항 해석"), ("outline", "슬라이드 구조 생성"), ("render", "PPTX 렌더링")]
    writing = [("diagnose", "원고 진단"), ("strategy", "보강 방향 설계"), ("answer", "답변 작성")]
    rows = deck if kind == "deck" else writing if kind == "writing" else special.get(kind, default)
    return [{"id": step_id, "title": title, "detail": detail if index == 0 else f"{COMMAND_LABELS[kind]} 단계", "state": "done" if index == 0 else "active" if index == 1 else "pending"} for index, (step_id, title) in enumerate(rows)]


def build_artifacts(kind: RunKind, title: str) -> list[dict[str, Any]]:
    return [{"id": item_id, "title": label if item_id in {"writing-advice"} else f"{title} {label}", "type": item_type} for item_id, label, item_type in ARTIFACTS[kind]]


def create_run(input_text: str, *, mode: str = "local") -> dict[str, Any]:
    command, prompt = split_command(input_text)
    kind = detect_run_kind(command, prompt)
    title = summarize_run_title(prompt, command, kind)
    steps = [{**step, "state": "pending"} for step in build_run_steps(kind, prompt, command)]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "id": uuid4().hex,
        "title": title,
        "prompt": prompt,
        "command": command,
        "kind": kind,
        "status": "queued",
        "worker": RUN_WORKERS[kind],
        "progress": 0,
        "startedAt": datetime.now().strftime("%H:%M"),
        "steps": steps,
        "artifacts": build_artifacts(kind, title),
        "log": [f"{command} 명령을 수신했습니다.", f"{COMMAND_LABELS[kind]} 실행 그래프를 대기열에 등록했습니다."],
        "runtime": {"source": "backend", "mode": mode, "createdAt": now},
    }
