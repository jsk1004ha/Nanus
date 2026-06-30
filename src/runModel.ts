import type { ActiveRun, RunKind, RunStep } from "./types";

export const commandLabels: Record<RunKind, string> = {
  deck: "발표자료 제작",
  writing: "글쓰기 조언",
  document: "문서 작성",
  spreadsheet: "엑셀 제작",
  visualization: "시각화 제작",
  site: "웹사이트 구축",
  app: "앱 개발",
  design: "디자인 정리",
  research: "조사",
  schedule: "예약 실행",
  library: "라이브러리 작업",
  agent: "에이전트 구성",
  general: "일반 실행",
};

const runWorkers: Record<RunKind, string> = {
  deck: "Artifact Studio + Presenton",
  writing: "Writing Coach",
  document: "Document Writer",
  spreadsheet: "Spreadsheet Studio",
  visualization: "Visualization Studio",
  site: "Web Builder + Codex",
  app: "Codex Lane",
  design: "Design System Agent",
  research: "Research",
  schedule: "Scheduler",
  library: "Library Indexer",
  agent: "Planner",
  general: "Nanus Executor",
};

function splitCommand(input: string) {
  const trimmed = input.trim();
  const [firstToken, ...rest] = trimmed.split(/\s+/);
  const hasCommand = firstToken?.startsWith("/");
  return { command: hasCommand ? firstToken : "/run", prompt: hasCommand ? rest.join(" ").trim() : trimmed };
}

function detectRunKind(command: string, prompt: string): RunKind {
  const haystack = `${command} ${prompt}`.toLowerCase();
  if (command === "/deck-from-brief") return "deck";
  if (/(글\s*늘릴|늘릴\s*방법|늘릴방법|분량|보강|확장|문단 추가|문장 추가|첨삭|설득력 있게)/.test(haystack)) return "writing";
  if (command === "/spreadsheet" || command === "/excel" || command === "/xlsx" || /(엑셀|excel|xlsx|스프레드시트|워크북)/.test(haystack)) return "spreadsheet";
  if (command === "/visualization" || command === "/viz" || command === "/chart" || command === "/dashboard" || /(시각화|차트|그래프|dashboard|대시보드)/.test(haystack)) return "visualization";
  if (command === "/document" || command === "/doc" || command === "/report" || /(보고서|문서|docx|markdown|원고)/.test(haystack)) return "document";
  if (/(artifact-studio|deck|ppt|pdf|hwpx|발표|슬라이드)/.test(haystack)) return "deck";
  if (/(site|web|웹사이트)/.test(haystack)) return "site";
  if (/(app|desktop|앱)/.test(haystack)) return "app";
  if (/(design|디자인)/.test(haystack)) return "design";
  if (/(research|리서치|조사|출처|근거)/.test(haystack)) return "research";
  if (/(schedule|예약)/.test(haystack)) return "schedule";
  if (/(library|라이브러리)/.test(haystack)) return "library";
  if (/(agent|에이전트)/.test(haystack)) return "agent";
  return "general";
}

function summarizeRunTitle(prompt: string, command: string, kind: RunKind) {
  const source = prompt.trim() || commandLabels[kind] || command;
  return source.length > 44 ? `${source.slice(0, 43)}...` : source;
}

function makeSteps(kind: RunKind, prompt: string, command: string): RunStep[] {
  const detail = prompt || command;
  const map: Record<RunKind, Array<[string, string]>> = {
    deck: [["brief", "요구사항 해석"], ["outline", "슬라이드 구조 생성"], ["render", "PPTX 렌더링"]],
    writing: [["diagnose", "원고 진단"], ["strategy", "보강 방향 설계"], ["answer", "답변 작성"]],
    document: [["outline", "문서 구조 설계"], ["draft", "본문 작성"], ["export", "문서 내보내기"]],
    spreadsheet: [["schema", "시트 구조 설계"], ["workbook", "워크북 생성"], ["verify", "범위 검증"]],
    visualization: [["question", "질문 유형 분석"], ["chart", "차트 선택"], ["render", "대시보드 렌더링"]],
    site: [["brief", "사이트 요구사항 해석"], ["layout", "페이지 구조 작성"], ["build", "프론트엔드 생성"]],
    app: [["scope", "앱 범위 정의"], ["tasks", "구현 태스크 분해"], ["verify", "테스트 계획"]],
    design: [["audit", "디자인 요구사항 정리"], ["tokens", "토큰/컴포넌트 정리"], ["qa", "시각 QA"]],
    research: [["scope", "조사 질문 고정"], ["sources", "출처 수집/검증"], ["synthesis", "근거 합성"]],
    schedule: [["parse", "예약 조건 해석"], ["calendar", "실행 시간 계산"], ["save", "예약 저장"]],
    library: [["lookup", "라이브러리 검색"], ["index", "관련 산출물 매칭"], ["open", "작업으로 가져오기"]],
    agent: [["roles", "에이전트 역할 구성"], ["permissions", "권한 경계 설정"], ["handoff", "실행 핸드오프"]],
    general: [["read", "요청 해석"], ["plan", "실행 계획 생성"], ["result", "결과 작성"]],
  };
  return map[kind].map(([id, title], index) => ({ id, title, detail: index === 0 ? detail : `${commandLabels[kind]} 단계`, state: index === 0 ? "done" : index === 1 ? "active" : "pending" }));
}

function buildArtifacts(kind: RunKind, title: string): ActiveRun["artifacts"] {
  const map: Record<RunKind, ActiveRun["artifacts"]> = {
    deck: [{ id: "outline", title: `${title} 목차`, type: "outline" }, { id: "pptx", title: `${title} 초안.pptx`, type: "pptx" }],
    writing: [{ id: "writing-advice", title: "보고서 원고 확장 제안.md", type: "markdown" }],
    document: [{ id: "document", title: `${title} 문서 초안.md`, type: "markdown" }],
    spreadsheet: [{ id: "workbook", title: `${title} 분석 워크북.xlsx`, type: "spreadsheet" }],
    visualization: [{ id: "dashboard", title: `${title} 시각화.html`, type: "visualization" }],
    site: [{ id: "wireframe", title: `${title} 페이지 구조`, type: "wireframe" }, { id: "preview", title: `${title} 미리보기`, type: "web" }],
    app: [{ id: "tasks", title: `${title} 구현 태스크`, type: "task-list" }, { id: "checks", title: `${title} 검증 체크`, type: "test-plan" }],
    design: [{ id: "tokens", title: `${title} 토큰`, type: "design-tokens" }, { id: "qa", title: `${title} QA`, type: "design-qa" }],
    research: [{ id: "brief", title: `${title} 리서치 브리프`, type: "research-brief" }, { id: "sources", title: `${title} 출처 목록`, type: "citations" }],
    schedule: [{ id: "schedule", title: `${title} 예약`, type: "schedule" }],
    library: [{ id: "library", title: `${title} 검색 결과`, type: "library" }],
    agent: [{ id: "graph", title: `${title} 에이전트 그래프`, type: "graph" }],
    general: [{ id: "result", title: `${title} 결과`, type: "note" }],
  };
  return map[kind];
}

export function createRun(input: string): ActiveRun {
  const { command, prompt } = splitCommand(input);
  const kind = detectRunKind(command, prompt);
  const title = summarizeRunTitle(prompt, command, kind);
  const steps = makeSteps(kind, prompt, command);
  return { id: `${Date.now()}`, title, prompt, command, kind, status: "running", worker: runWorkers[kind], progress: 34, startedAt: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }), steps, artifacts: buildArtifacts(kind, title), log: [`${command} 명령을 수신했습니다.`, `${commandLabels[kind]} 실행 그래프를 구성했습니다.`, `현재 단계: ${steps.find((step) => step.state === "active")?.title ?? steps[0].title}`] };
}
