from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

RunKind = str

COMMAND_LABELS: dict[RunKind, str] = {
    "deck": "발표자료 제작",
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
    "site": "Web Builder + Codex",
    "app": "Codex Lane",
    "design": "Design System Agent",
    "research": "Research",
    "schedule": "Scheduler",
    "library": "Library Indexer",
    "agent": "Planner",
    "general": "Nanus Executor",
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


def detect_run_kind(command: str, prompt: str) -> RunKind:
    haystack = f"{command} {prompt}".lower()
    if any(token in haystack for token in ["artifact-studio", "deck", "ppt", "pdf", "hwpx", "발표", "슬라이드", "문서"]):
        return "deck"
    if any(token in haystack for token in ["site", "web", "웹사이트"]):
        return "site"
    if any(token in haystack for token in ["app", "desktop", "앱"]):
        return "app"
    if any(token in haystack for token in ["design", "디자인"]):
        return "design"
    if any(token in haystack for token in ["research", "리서치", "조사", "출처", "근거"]):
        return "research"
    if any(token in haystack for token in ["schedule", "예약"]):
        return "schedule"
    if any(token in haystack for token in ["library", "라이브러리"]):
        return "library"
    if any(token in haystack for token in ["agent", "에이전트"]):
        return "agent"
    return "general"


def summarize_run_title(prompt: str, command: str, kind: RunKind) -> str:
    source = prompt.strip() or COMMAND_LABELS.get(kind) or command
    return f"{source[:43]}..." if len(source) > 44 else source


def build_run_steps(kind: RunKind, prompt: str, command: str) -> list[dict[str, Any]]:
    base_detail = prompt or command
    step_map: dict[RunKind, list[dict[str, Any]]] = {
        "deck": [
            {"id": "brief", "title": "요구사항 해석", "detail": base_detail, "state": "done"},
            {"id": "outline", "title": "슬라이드 구조 생성", "detail": "목차, 메시지, 근거를 구성합니다.", "state": "active"},
            {"id": "render", "title": "PPTX 렌더링", "detail": "Presenton/export 슬롯을 준비합니다.", "state": "pending"},
        ],
        "site": [
            {"id": "brief", "title": "사이트 요구사항 해석", "detail": base_detail, "state": "done"},
            {"id": "layout", "title": "페이지 구조 작성", "detail": "섹션, 라우트, 콘텐츠 블록을 설계합니다.", "state": "active"},
            {"id": "build", "title": "프론트엔드 생성", "detail": "React/CSS 산출물을 빌드합니다.", "state": "pending"},
        ],
        "app": [
            {"id": "scope", "title": "앱 범위 정의", "detail": base_detail, "state": "done"},
            {"id": "tasks", "title": "구현 태스크 분해", "detail": "Codex Lane 실행 단위를 만듭니다.", "state": "active"},
            {"id": "verify", "title": "테스트 계획", "detail": "빌드와 브라우저 검증을 준비합니다.", "state": "pending"},
        ],
        "design": [
            {"id": "audit", "title": "디자인 요구사항 정리", "detail": base_detail, "state": "done"},
            {"id": "tokens", "title": "토큰/컴포넌트 정리", "detail": "색상, 간격, 상태를 정리합니다.", "state": "active"},
            {"id": "qa", "title": "시각 QA", "detail": "스크린샷 비교와 수정 목록을 생성합니다.", "state": "pending"},
        ],
        "research": [
            {"id": "scope", "title": "조사 질문 고정", "detail": base_detail, "state": "done"},
            {"id": "sources", "title": "출처 수집/검증", "detail": "검색과 인용 후보를 확인합니다.", "state": "active"},
            {"id": "synthesis", "title": "근거 합성", "detail": "요약, 결론, 한계를 작성합니다.", "state": "pending"},
        ],
        "schedule": [
            {"id": "parse", "title": "예약 조건 해석", "detail": base_detail, "state": "done"},
            {"id": "calendar", "title": "실행 시간 계산", "detail": "반복 주기와 대상 산출물을 확인합니다.", "state": "active"},
            {"id": "save", "title": "예약 저장", "detail": "승인 후 스케줄러에 등록합니다.", "state": "pending"},
        ],
        "library": [
            {"id": "lookup", "title": "라이브러리 검색", "detail": base_detail, "state": "done"},
            {"id": "index", "title": "관련 산출물 매칭", "detail": "문서, PPT, 웹 요약본을 연결합니다.", "state": "active"},
            {"id": "open", "title": "작업으로 가져오기", "detail": "선택한 산출물을 입력 컨텍스트로 붙입니다.", "state": "pending"},
        ],
        "agent": [
            {"id": "roles", "title": "에이전트 역할 구성", "detail": base_detail, "state": "done"},
            {"id": "permissions", "title": "권한 경계 설정", "detail": "파일, 브라우저, 실행 권한을 분리합니다.", "state": "active"},
            {"id": "handoff", "title": "실행 핸드오프", "detail": "작업 그래프에 연결합니다.", "state": "pending"},
        ],
        "general": [
            {"id": "read", "title": "요청 해석", "detail": base_detail, "state": "done"},
            {"id": "plan", "title": "실행 계획 생성", "detail": "필요한 도구와 산출물을 결정합니다.", "state": "active"},
            {"id": "result", "title": "결과 작성", "detail": "완료 가능한 출력으로 정리합니다.", "state": "pending"},
        ],
    }
    return [dict(step) for step in step_map[kind]]


def build_artifacts(kind: RunKind, title: str) -> list[dict[str, Any]]:
    artifact_map: dict[RunKind, list[dict[str, str]]] = {
        "deck": [
            {"id": "outline", "title": f"{title} 목차", "type": "outline"},
            {"id": "pptx", "title": f"{title} 초안.pptx", "type": "pptx"},
        ],
        "site": [
            {"id": "wireframe", "title": f"{title} 페이지 구조", "type": "wireframe"},
            {"id": "preview", "title": f"{title} 미리보기", "type": "web"},
        ],
        "app": [
            {"id": "tasks", "title": f"{title} 구현 태스크", "type": "task-list"},
            {"id": "checks", "title": f"{title} 검증 체크", "type": "test-plan"},
        ],
        "design": [
            {"id": "tokens", "title": f"{title} 토큰", "type": "design-tokens"},
            {"id": "qa", "title": f"{title} QA", "type": "design-qa"},
        ],
        "research": [
            {"id": "brief", "title": f"{title} 리서치 브리프", "type": "research-brief"},
            {"id": "sources", "title": f"{title} 출처 목록", "type": "citations"},
        ],
        "schedule": [{"id": "schedule", "title": f"{title} 예약", "type": "schedule"}],
        "library": [{"id": "library", "title": f"{title} 검색 결과", "type": "library"}],
        "agent": [{"id": "graph", "title": f"{title} 에이전트 그래프", "type": "graph"}],
        "general": [{"id": "result", "title": f"{title} 결과", "type": "note"}],
    }
    return [dict(artifact) for artifact in artifact_map[kind]]


def create_run(input_text: str, *, mode: str = "local") -> dict[str, Any]:
    command, prompt = split_command(input_text)
    kind = detect_run_kind(command, prompt)
    title = summarize_run_title(prompt, command, kind)
    steps = build_run_steps(kind, prompt, command)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    return {
        "id": uuid4().hex,
        "title": title,
        "prompt": prompt,
        "command": command,
        "kind": kind,
        "status": "running",
        "worker": RUN_WORKERS[kind],
        "progress": 34,
        "startedAt": datetime.now().strftime("%H:%M"),
        "steps": steps,
        "artifacts": build_artifacts(kind, title),
        "log": [
            f"{command} 명령을 수신했습니다.",
            f"{COMMAND_LABELS[kind]} 실행 그래프를 구성했습니다.",
            f"현재 단계: {next((step['title'] for step in steps if step['state'] == 'active'), steps[0]['title'])}",
        ],
        "runtime": {"source": "backend", "mode": mode, "createdAt": now},
    }
