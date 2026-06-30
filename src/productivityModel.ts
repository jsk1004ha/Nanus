import type { ActiveRun, ProductivityPlan, RunKind, SkillPackage, WorkspaceMode } from "./types";

export interface ProductivityWorkspaceContext {
  mode: WorkspaceMode;
  paused: boolean;
  skills: Array<Pick<SkillPackage, "command" | "name" | "enabled" | "worker">>;
  agents: Array<{ id: string; name: string; status: string; description: string }>;
  scheduledRuns: Array<{ id: string; title: string; cadence: string; target: string }>;
  libraryItems: Array<{ id: string; title: string; meta: string }>;
}

const productivityProfiles: Record<RunKind, Pick<ProductivityPlan, "manualHours" | "nanusHours" | "automationScore" | "leverageScore">> = {
  deck: { manualHours: 9.5, nanusHours: 1.8, automationScore: 88, leverageScore: 91 },
  site: { manualHours: 14, nanusHours: 3.2, automationScore: 82, leverageScore: 86 },
  app: { manualHours: 18, nanusHours: 4.4, automationScore: 79, leverageScore: 84 },
  design: { manualHours: 7, nanusHours: 1.6, automationScore: 86, leverageScore: 88 },
  research: { manualHours: 10.5, nanusHours: 2.1, automationScore: 85, leverageScore: 89 },
  schedule: { manualHours: 3.5, nanusHours: 0.6, automationScore: 91, leverageScore: 82 },
  library: { manualHours: 4.5, nanusHours: 0.9, automationScore: 84, leverageScore: 83 },
  agent: { manualHours: 8, nanusHours: 1.9, automationScore: 87, leverageScore: 90 },
  general: { manualHours: 5.5, nanusHours: 1.4, automationScore: 81, leverageScore: 80 },
};

const laneLibrary: Record<RunKind, ProductivityPlan["lanes"]> = {
  deck: [
    { id: "research", title: "자료 수집/검증", owner: "Research Lane", detail: "근거와 인용 후보를 병렬로 수집", minutes: 22 },
    { id: "structure", title: "스토리라인", owner: "Planner", detail: "12장 구조와 메시지를 먼저 고정", minutes: 14 },
    { id: "render", title: "PPT 렌더", owner: "Artifact Studio", detail: "템플릿, 차트, 요약본을 동시 생성", minutes: 28 },
  ],
  site: [
    { id: "ia", title: "정보 구조", owner: "Designer", detail: "섹션과 콘텐츠 우선순위 작성", minutes: 18 },
    { id: "build", title: "프론트엔드", owner: "Codex Lane", detail: "React/CSS 구현과 responsive QA", minutes: 42 },
    { id: "qa", title: "브라우저 검증", owner: "Verifier", detail: "Playwright smoke와 스크린샷 체크", minutes: 16 },
  ],
  app: [
    { id: "scope", title: "작업 분해", owner: "Planner", detail: "구현/테스트/리뷰 단위를 분리", minutes: 20 },
    { id: "code", title: "코드 실행", owner: "Codex Lane", detail: "파일 수정, 타입 체크, 빌드", minutes: 58 },
    { id: "review", title: "검증 리뷰", owner: "Architect", detail: "회귀와 설계 위험을 독립 점검", minutes: 24 },
  ],
  design: [
    { id: "audit", title: "시각 QA", owner: "Visual Ralph", detail: "참조 대비 레이아웃 차이를 수치화", minutes: 18 },
    { id: "tokens", title: "토큰 정리", owner: "Design System", detail: "색상/간격/상태를 재사용 가능하게 정리", minutes: 22 },
    { id: "copy", title: "UX 문구", owner: "Writer", detail: "행동 중심 문구와 상태 메시지 작성", minutes: 12 },
  ],
  research: [
    { id: "source", title: "출처 수집", owner: "Research Lane", detail: "검색, 문서, 웹 출처 후보를 병렬 수집", minutes: 24 },
    { id: "verify", title: "근거 검증", owner: "Citation QA", detail: "출처 신뢰도와 상충 근거를 점검", minutes: 18 },
    { id: "synthesis", title: "브리프 합성", owner: "Writer", detail: "핵심 결론, 한계, 다음 질문을 정리", minutes: 20 },
  ],
  schedule: [
    { id: "parse", title: "반복 조건", owner: "Scheduler", detail: "시간, 주기, 산출물 대상 파싱", minutes: 8 },
    { id: "guard", title: "승인 게이트", owner: "Policy Lane", detail: "외부 전송/비용 작업을 분리", minutes: 6 },
    { id: "notify", title: "완료 알림", owner: "Notification", detail: "작업 종료와 승인 요청 알림", minutes: 4 },
  ],
  library: [
    { id: "index", title: "산출물 색인", owner: "Library Indexer", detail: "PPT/HWPX/웹 요약본을 통합 검색", minutes: 10 },
    { id: "reuse", title: "재사용 후보", owner: "Skill Hub", detail: "반복 가능한 작업 패턴 감지", minutes: 8 },
    { id: "attach", title: "컨텍스트 부착", owner: "Planner", detail: "다음 실행에 필요한 파일과 메모리 연결", minutes: 6 },
  ],
  agent: [
    { id: "roles", title: "역할 구성", owner: "Planner", detail: "전문 레인과 handoff 계약 정의", minutes: 18 },
    { id: "tools", title: "도구 권한", owner: "MCP Gateway", detail: "파일/브라우저/외부 API 권한 분리", minutes: 14 },
    { id: "handoff", title: "팀 실행", owner: "A2A Router", detail: "병렬 레인 결과를 하나의 ledger로 합성", minutes: 20 },
  ],
  general: [
    { id: "understand", title: "요청 해석", owner: "Planner", detail: "목표, 산출물, 성공 기준을 명시", minutes: 12 },
    { id: "execute", title: "도구 실행", owner: "Nanus Executor", detail: "필요한 레인을 선택해 병렬 실행", minutes: 20 },
    { id: "verify", title: "완료 검증", owner: "Verifier", detail: "테스트, 산출물, 회귀 위험을 확인", minutes: 10 },
  ],
};

export function createProductivityPlan(run: ActiveRun | null, draft: string, context: ProductivityWorkspaceContext): ProductivityPlan {
  const kind = run?.kind ?? "general";
  const profile = productivityProfiles[kind];
  const title = run?.title || draft.trim() || "새 작업 생산성 계획";
  const completedSteps = run?.steps.filter((step) => step.state === "done").length ?? 0;
  const pendingSteps = run?.steps.filter((step) => step.state !== "done").length ?? (draft.trim() ? 3 : 1);
  const totalSteps = run?.steps.length ?? Math.max(3, pendingSteps);
  const progressRatio = run ? Math.max(run.progress / 100, completedSteps / Math.max(totalSteps, 1)) : draft.trim() ? 0.12 : 0;
  const enabledSkills = context.skills.filter((skill) => skill.enabled);
  const reviewSkills = context.skills.filter((skill) => !skill.enabled);
  const workspaceSignals = context.agents.length + context.scheduledRuns.length + context.libraryItems.length + enabledSkills.length;
  const workspaceMultiplier = Math.min(1.18, 1 + workspaceSignals * 0.015);
  const remainingMultiplier = Math.max(0.52, 1 - progressRatio * 0.38);
  const manualHours = Number((profile.manualHours * workspaceMultiplier).toFixed(1));
  const nanusHours = Number(Math.max(0.4, profile.nanusHours * remainingMultiplier + pendingSteps * 0.08).toFixed(1));
  const savedHours = Number((manualHours - nanusHours).toFixed(1));
  const automationScore = Math.min(99, Math.round(profile.automationScore + enabledSkills.length * 2 + completedSteps * 2 - reviewSkills.length));
  const leverageScore = Math.min(99, Math.round(profile.leverageScore + context.agents.length * 2 + context.libraryItems.length - (context.paused ? 4 : 0)));
  const runState = run ? `${completedSteps}/${totalSteps} 단계, 진행률 ${Math.round(progressRatio * 100)}% 반영` : "입력 초안과 워크스페이스 상태 반영";
  const artifactHint = run?.artifacts.length ? `${run.artifacts.length}개 산출물 연결` : `${context.libraryItems.length}개 라이브러리 항목 재사용`;
  const selectedLanes = laneLibrary[kind].map((lane) => ({
    ...lane,
    detail: `${lane.detail} · ${runState}`,
    minutes: Math.max(5, Math.round(lane.minutes * remainingMultiplier)),
  }));
  const primarySkill = enabledSkills[0];
  const codexSkill = enabledSkills.find((skill) => skill.worker.toLowerCase().includes("codex")) ?? primarySkill;
  const reviewSkill = reviewSkills[0];

  return {
    title,
    manualHours,
    nanusHours,
    savedHours,
    automationScore,
    leverageScore,
    lanes: selectedLanes,
    reusableSkills: [
      {
        id: "brief",
        name: `${title.slice(0, 18)} 반복 스킬`,
        command: primarySkill?.command ?? `/skill-create ${kind}`,
        payoff: primarySkill ? `${primarySkill.name} 권한 모델로 반복 입력을 재사용` : "동일한 입력 구조를 다음 실행부터 원클릭으로 재사용",
      },
      {
        id: "qa",
        name: "검증 게이트 스킬",
        command: "/qa-gate",
        payoff: `${artifactHint}, 완료 전 타입/빌드/브라우저 검증 요구`,
      },
      {
        id: "handoff",
        name: "Codex/Claude 핸드오프",
        command: codexSkill?.command ?? "/agent-handoff",
        payoff: `${context.agents.length}개 에이전트 상태를 기준으로 병렬 레인을 합성`,
      },
    ],
    riskGates: [
      {
        id: "data",
        label: "데이터 주권",
        status: context.mode === "local" ? "ready" : "review",
        detail: context.mode === "local" ? "현재 로컬 실행 우선, 외부 전송은 승인 후 진행" : "프라이빗 실행 전 전송 범위와 비밀값을 재확인",
      },
      {
        id: "cost",
        label: "비용 상한",
        status: reviewSkill ? "review" : "ready",
        detail: reviewSkill ? `${reviewSkill.name} 패키지 권한 검토 필요` : "활성 스킬만 사용하므로 추가 패키지 비용 없음",
      },
      {
        id: "quality",
        label: "완료 검증",
        status: run?.status === "complete" ? "ready" : "review",
        detail: run ? `${pendingSteps}개 남은 단계와 ${run.artifacts.length}개 산출물 검증 필요` : "실행 전 성공 기준과 산출물 검증을 고정",
      },
    ],
    nextActions: [
      run ? `${title} 실행 상태를 ledger에 고정하고 ${pendingSteps}개 남은 단계를 우선순위화` : "입력 초안을 실행 가능한 런으로 전환",
      `반복 가능 단계는 ${primarySkill?.name ?? "새 스킬"} 후보로 승격`,
      `위험 게이트를 통과한 ${selectedLanes.length}개 레인만 병렬 실행`,
      `${context.libraryItems[0]?.title ?? "산출물 라이브러리"}를 다음 컨텍스트로 연결`,
    ],
  };
}
