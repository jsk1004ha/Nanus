import type { ActiveRun, RunKind, RunStep } from "./types";

export const commandLabels: Record<RunKind, string> = {
  deck: "발표자료 제작",
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
  return {
    command: hasCommand ? firstToken : "/run",
    prompt: hasCommand ? rest.join(" ").trim() : trimmed,
  };
}

function detectRunKind(command: string, prompt: string): RunKind {
  const haystack = `${command} ${prompt}`.toLowerCase();
  if (
    haystack.includes("artifact-studio") ||
    haystack.includes("deck") ||
    haystack.includes("ppt") ||
    haystack.includes("pdf") ||
    haystack.includes("hwpx") ||
    haystack.includes("발표") ||
    haystack.includes("슬라이드") ||
    haystack.includes("문서")
  )
    return "deck";
  if (haystack.includes("site") || haystack.includes("web") || haystack.includes("웹사이트")) return "site";
  if (haystack.includes("app") || haystack.includes("desktop") || haystack.includes("앱")) return "app";
  if (haystack.includes("design") || haystack.includes("디자인")) return "design";
  if (haystack.includes("research") || haystack.includes("리서치") || haystack.includes("조사") || haystack.includes("출처") || haystack.includes("근거")) return "research";
  if (haystack.includes("schedule") || haystack.includes("예약")) return "schedule";
  if (haystack.includes("library") || haystack.includes("라이브러리")) return "library";
  if (haystack.includes("agent") || haystack.includes("에이전트")) return "agent";
  return "general";
}

function summarizeRunTitle(prompt: string, command: string, kind: RunKind) {
  const source = prompt.trim() || commandLabels[kind] || command;
  return source.length > 44 ? `${source.slice(0, 43)}...` : source;
}

function buildRunSteps(kind: RunKind, prompt: string, command: string): RunStep[] {
  const baseDetail = prompt || command;
  const stepMap: Record<RunKind, RunStep[]> = {
    deck: [
      { id: "brief", title: "요구사항 해석", detail: baseDetail, state: "done" },
      { id: "outline", title: "슬라이드 구조 생성", detail: "목차, 메시지, 근거를 구성합니다.", state: "active" },
      { id: "render", title: "PPTX 렌더링", detail: "Presenton/export 슬롯을 준비합니다.", state: "pending" },
    ],
    site: [
      { id: "brief", title: "사이트 요구사항 해석", detail: baseDetail, state: "done" },
      { id: "layout", title: "페이지 구조 작성", detail: "섹션, 라우트, 콘텐츠 블록을 설계합니다.", state: "active" },
      { id: "build", title: "프론트엔드 생성", detail: "React/CSS 산출물을 빌드합니다.", state: "pending" },
    ],
    app: [
      { id: "scope", title: "앱 범위 정의", detail: baseDetail, state: "done" },
      { id: "tasks", title: "구현 태스크 분해", detail: "Codex Lane 실행 단위를 만듭니다.", state: "active" },
      { id: "verify", title: "테스트 계획", detail: "빌드와 브라우저 검증을 준비합니다.", state: "pending" },
    ],
    design: [
      { id: "audit", title: "디자인 요구사항 정리", detail: baseDetail, state: "done" },
      { id: "tokens", title: "토큰/컴포넌트 정리", detail: "색상, 간격, 상태를 정리합니다.", state: "active" },
      { id: "qa", title: "시각 QA", detail: "스크린샷 비교와 수정 목록을 생성합니다.", state: "pending" },
    ],
    research: [
      { id: "scope", title: "조사 질문 고정", detail: baseDetail, state: "done" },
      { id: "sources", title: "출처 수집/검증", detail: "검색과 인용 후보를 확인합니다.", state: "active" },
      { id: "synthesis", title: "근거 합성", detail: "요약, 결론, 한계를 작성합니다.", state: "pending" },
    ],
    schedule: [
      { id: "parse", title: "예약 조건 해석", detail: baseDetail, state: "done" },
      { id: "calendar", title: "실행 시간 계산", detail: "반복 주기와 대상 산출물을 확인합니다.", state: "active" },
      { id: "save", title: "예약 저장", detail: "승인 후 스케줄러에 등록합니다.", state: "pending" },
    ],
    library: [
      { id: "lookup", title: "라이브러리 검색", detail: baseDetail, state: "done" },
      { id: "index", title: "관련 산출물 매칭", detail: "문서, PPT, 웹 요약본을 연결합니다.", state: "active" },
      { id: "open", title: "작업으로 가져오기", detail: "선택한 산출물을 입력 컨텍스트로 붙입니다.", state: "pending" },
    ],
    agent: [
      { id: "roles", title: "에이전트 역할 구성", detail: baseDetail, state: "done" },
      { id: "permissions", title: "권한 경계 설정", detail: "파일, 브라우저, 실행 권한을 분리합니다.", state: "active" },
      { id: "handoff", title: "실행 핸드오프", detail: "작업 그래프에 연결합니다.", state: "pending" },
    ],
    general: [
      { id: "read", title: "요청 해석", detail: baseDetail, state: "done" },
      { id: "plan", title: "실행 계획 생성", detail: "필요한 도구와 산출물을 결정합니다.", state: "active" },
      { id: "result", title: "결과 작성", detail: "완료 가능한 출력으로 정리합니다.", state: "pending" },
    ],
  };

  return stepMap[kind];
}

function buildArtifacts(kind: RunKind, title: string): ActiveRun["artifacts"] {
  const artifactMap: Record<RunKind, ActiveRun["artifacts"]> = {
    deck: [
      { id: "outline", title: `${title} 목차`, type: "outline" },
      { id: "pptx", title: `${title} 초안.pptx`, type: "pptx" },
    ],
    site: [
      { id: "wireframe", title: `${title} 페이지 구조`, type: "wireframe" },
      { id: "preview", title: `${title} 미리보기`, type: "web" },
    ],
    app: [
      { id: "tasks", title: `${title} 구현 태스크`, type: "task-list" },
      { id: "checks", title: `${title} 검증 체크`, type: "test-plan" },
    ],
    design: [
      { id: "tokens", title: `${title} 토큰`, type: "design-tokens" },
      { id: "qa", title: `${title} QA`, type: "design-qa" },
    ],
    research: [
      { id: "brief", title: `${title} 리서치 브리프`, type: "research-brief" },
      { id: "sources", title: `${title} 출처 목록`, type: "citations" },
    ],
    schedule: [{ id: "schedule", title: `${title} 예약`, type: "schedule" }],
    library: [{ id: "library", title: `${title} 검색 결과`, type: "library" }],
    agent: [{ id: "graph", title: `${title} 에이전트 그래프`, type: "graph" }],
    general: [{ id: "result", title: `${title} 결과`, type: "note" }],
  };
  return artifactMap[kind];
}

export function createRun(input: string): ActiveRun {
  const { command, prompt } = splitCommand(input);
  const kind = detectRunKind(command, prompt);
  const title = summarizeRunTitle(prompt, command, kind);
  const steps = buildRunSteps(kind, prompt, command);

  return {
    id: `${Date.now()}`,
    title,
    prompt,
    command,
    kind,
    status: "running",
    worker: runWorkers[kind],
    progress: 34,
    startedAt: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }),
    steps,
    artifacts: buildArtifacts(kind, title),
    log: [
      `${command} 명령을 수신했습니다.`,
      `${commandLabels[kind]} 실행 그래프를 구성했습니다.`,
      `현재 단계: ${steps.find((step) => step.state === "active")?.title ?? steps[0].title}`,
    ],
  };
}
