import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity,
  AlertCircle,
  ArrowUp,
  AudioLines,
  Bell,
  BellRing,
  CalendarClock,
  Check,
  ChevronDown,
  CircleCheck,
  Command,
  Copy,
  CornerDownLeft,
  CreditCard,
  Database,
  Download,
  ExternalLink,
  FileInput,
  FolderOpen,
  FolderPlus,
  HardDrive,
  ListFilter,
  Mic,
  Monitor,
  Moon,
  MoreHorizontal,
  PanelLeft,
  Paperclip,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkle,
  Sparkles,
  Sun,
  Terminal,
  Upload,
  Workflow,
  X,
} from "lucide-react";
import {
  agents,
  libraryItems,
  mobileTabs,
  navItems,
  quickActions,
  recommendations,
  runLedger,
  scheduledRuns,
  skills,
  tasks,
} from "./data";
import type { ActiveRun, PanelId, QuickAction, Recommendation, RunKind, RunStep, SkillPackage, ViewId } from "./types";

type ThemeMode = "dark" | "light";
type WorkspaceMode = "local" | "private";
type SkillTab = "recommended" | "installed" | "review";

interface ToastMessage {
  id: number;
  title: string;
  detail: string;
  tone?: "default" | "success" | "warning";
}

interface ProjectItem {
  id: string;
  name: string;
}

const commandLabels: Record<RunKind, string> = {
  deck: "발표자료 제작",
  site: "웹사이트 구축",
  app: "앱 개발",
  design: "디자인 정리",
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
  schedule: "Scheduler",
  library: "Library Indexer",
  agent: "Planner",
  general: "Nanus Executor",
};

const miniCommandLabels: Record<string, string> = {
  "deck-from-brief": "/deck",
  "manus-research": "/manus",
  "codex-refactor": "/codex",
};

const viewCopy: Record<ViewId, { eyebrow: string; title: string; placeholder: string }> = {
  home: {
    eyebrow: "Nanus Control",
    title: "무엇을 실행할까요?",
    placeholder: "작업을 할당하거나 /를 입력하여 더 많은 옵션을 확인하세요",
  },
  agents: {
    eyebrow: "Agent Console",
    title: "어떤 에이전트를 구성할까요?",
    placeholder: "예: Planner와 Codex Lane으로 문서 자동화 파이프라인을 구성해줘",
  },
  skills: {
    eyebrow: "Skill Hub",
    title: "어떤 스킬을 사용할까요?",
    placeholder: "예: /deck-from-brief 보고서를 12장 발표자료로 바꿔줘",
  },
  schedule: {
    eyebrow: "Scheduled Runs",
    title: "무엇을 예약할까요?",
    placeholder: "예: 매주 월요일 교육지원 사업 리서치 브리프를 만들어줘",
  },
  library: {
    eyebrow: "Library",
    title: "어떤 산출물을 찾을까요?",
    placeholder: "예: 최근 문서 시각화 엔진 설계 초안을 열어줘",
  },
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
  if (haystack.includes("deck") || haystack.includes("ppt") || haystack.includes("발표") || haystack.includes("슬라이드")) return "deck";
  if (haystack.includes("site") || haystack.includes("web") || haystack.includes("웹사이트")) return "site";
  if (haystack.includes("app") || haystack.includes("desktop") || haystack.includes("앱")) return "app";
  if (haystack.includes("design") || haystack.includes("디자인")) return "design";
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
    schedule: [{ id: "schedule", title: `${title} 예약`, type: "schedule" }],
    library: [{ id: "library", title: `${title} 검색 결과`, type: "library" }],
    agent: [{ id: "graph", title: `${title} 에이전트 그래프`, type: "graph" }],
    general: [{ id: "result", title: `${title} 결과`, type: "note" }],
  };
  return artifactMap[kind];
}

function createRun(input: string): ActiveRun {
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

function IconButton({
  label,
  children,
  small = false,
  selected = false,
  disabled = false,
  onClick,
}: {
  label: string;
  children: ReactNode;
  small?: boolean;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      className={`icon-button${small ? " tiny" : ""}${selected ? " selected" : ""}`}
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Sidebar({
  activeView,
  projects,
  notificationStatus,
  collapsed,
  mobileOpen,
  onToggleSidebar,
  onOpenPalette,
  onOpenProject,
  onOpenPanel,
  onSelectView,
  onSelectSkill,
  onSelectTask,
  onNotificationChoice,
}: {
  activeView: ViewId;
  projects: ProjectItem[];
  notificationStatus: "unknown" | "on" | "off";
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleSidebar: () => void;
  onOpenPalette: () => void;
  onOpenProject: () => void;
  onOpenPanel: (panel: PanelId) => void;
  onSelectView: (view: ViewId) => void;
  onSelectSkill: (skill: SkillPackage) => void;
  onSelectTask: (taskTitle: string) => void;
  onNotificationChoice: (enabled: boolean) => void;
}) {
  return (
    <aside className={`sidebar${mobileOpen ? " open" : ""}${collapsed ? " collapsed" : ""}`} aria-label="Nanus workspace navigation">
      <header className="brand-row">
        <button className="brand-lockup" type="button" aria-label="홈으로 이동" onClick={() => onSelectView("home")}>
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <span className="brand-name">nanus</span>
        </button>
        <IconButton label="검색" onClick={onOpenPalette}>
          <Search />
        </IconButton>
        <IconButton label={collapsed ? "사이드바 펼치기" : "사이드바 접기"} onClick={onToggleSidebar}>
          <PanelLeft />
        </IconButton>
      </header>

      <nav className="nav-stack" aria-label="Primary">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item${activeView === item.id ? " active" : ""}`}
              type="button"
              title={collapsed ? item.label : undefined}
              onClick={() => onSelectView(item.id)}
            >
              <Icon />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <section className="sidebar-section">
        <div className="section-title">
          <span>프로젝트</span>
          <IconButton label="프로젝트 추가" small onClick={onOpenProject}>
            <Plus />
          </IconButton>
        </div>
        <button className="project-row" type="button" onClick={onOpenProject}>
          <FolderPlus />
          <span>새 프로젝트</span>
        </button>
        {projects.map((project) => (
          <button key={project.id} className="project-row subtle" type="button" onClick={() => onSelectTask(`${project.name} 프로젝트 작업 계획`)}>
            <FolderOpen />
            <span>{project.name}</span>
          </button>
        ))}
      </section>

      <section className="sidebar-section tasks-section">
        <div className="section-title">
          <span>작업</span>
          <IconButton label="작업 필터" small onClick={() => onOpenPanel("run")}>
            <ListFilter />
          </IconButton>
        </div>
        {tasks.map((task, index) => {
          const Icon = task.icon;
          return (
            <button key={task.id} className={`task-row${index === 0 ? " selected" : ""}`} type="button" onClick={() => onSelectTask(task.title)}>
              <Icon />
              <span>{task.title}</span>
            </button>
          );
        })}
      </section>

      <section className="skill-mini" aria-label="Skill shortcuts">
        <button className="mini-title" type="button" onClick={() => onOpenPanel("skills")}>
          <Sparkles />
          <span>스킬 허브</span>
        </button>
        <div className="mini-grid">
          {skills.map((skill) => (
            <button key={skill.id} type="button" onClick={() => onSelectSkill(skill)}>
              {miniCommandLabels[skill.id] ?? skill.command}
            </button>
          ))}
        </div>
      </section>

      {notificationStatus !== "on" ? (
        <div className="notify-card">
          <div>
            <BellRing />
            <span>{notificationStatus === "unknown" ? "작업 완료 시 브라우저 알림을 켜세요." : "브라우저 알림이 꺼져 있습니다."}</span>
          </div>
          <div className="notify-actions">
            <button type="button" onClick={() => onNotificationChoice(false)}>
              지금은 필요없습니다
            </button>
            <button type="button" className="light" onClick={() => onNotificationChoice(true)}>
              켜기
            </button>
          </div>
        </div>
      ) : null}

      <footer className="account-row">
        <button className="avatar" type="button" aria-label="계정 설정" onClick={() => onOpenPanel("settings")}>
          H
        </button>
        <strong>Hans Patel</strong>
        <IconButton label="작업공간 장치" onClick={() => onOpenPanel("connections")}>
          <Monitor />
        </IconButton>
        <IconButton label="알림" selected={notificationStatus === "on"} onClick={() => onOpenPanel("notifications")}>
          <Bell />
          {notificationStatus !== "off" ? <span className="dot" /> : null}
        </IconButton>
      </footer>
    </aside>
  );
}

function MainStage({
  activeView,
  composer,
  composerError,
  suggestions,
  suggestionsVisible,
  mode,
  theme,
  onComposerChange,
  onTemplate,
  onOpenPanel,
  onOpenPalette,
  onStartRun,
  onHideSuggestions,
  onRefreshSuggestions,
  onSetMode,
  onToggleTheme,
  onToggleSidebar,
}: {
  activeView: ViewId;
  composer: string;
  composerError: string;
  suggestions: Recommendation[];
  suggestionsVisible: boolean;
  mode: WorkspaceMode;
  theme: ThemeMode;
  onComposerChange: (value: string) => void;
  onTemplate: (value: string) => void;
  onOpenPanel: (panel: PanelId) => void;
  onOpenPalette: () => void;
  onStartRun: () => void;
  onHideSuggestions: () => void;
  onRefreshSuggestions: () => void;
  onSetMode: (mode: WorkspaceMode) => void;
  onToggleTheme: () => void;
  onToggleSidebar: () => void;
}) {
  const copy = viewCopy[activeView];

  return (
    <main className="main-stage">
      <header className="topbar">
        <div className="top-left">
          <IconButton label="사이드바 전환" onClick={onToggleSidebar}>
            <PanelLeft />
          </IconButton>
          <button className="workspace-switch" type="button" onClick={onOpenPalette}>
            <span>Nanus 0.1 Control</span>
            <ChevronDown />
          </button>
        </div>
        <div className="top-actions">
          <IconButton label={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"} onClick={onToggleTheme}>
            {theme === "dark" ? <Sun /> : <Moon />}
          </IconButton>
          <IconButton label="설정" onClick={() => onOpenPanel("settings")}>
            <Settings />
          </IconButton>
          <button className="credit-pill" type="button" onClick={() => onOpenPanel("billing")}>
            <Sparkle />
            <span>1,207</span>
          </button>
        </div>
      </header>

      <section className="hero-workspace" aria-label="Nanus start workspace">
        <span className="workspace-eyebrow">{copy.eyebrow}</span>
        <div className="plan-toggle" role="group" aria-label="Execution mode">
          <button type="button" className={mode === "local" ? "active" : undefined} onClick={() => onSetMode("local")}>
            로컬 실행
          </button>
          <button type="button" className={mode === "private" ? "active" : undefined} onClick={() => onSetMode("private")}>
            프라이빗 스택 시작
          </button>
        </div>

        <h1>{copy.title}</h1>

        <div className={`composer-stack${suggestionsVisible ? " has-suggestions" : ""}`}>
          <section className="composer" aria-label="작업 입력">
            <label className="sr-only" htmlFor="nanus-composer">
              작업 입력
            </label>
            <textarea
              id="nanus-composer"
              value={composer}
              rows={3}
              placeholder={copy.placeholder}
              aria-invalid={Boolean(composerError)}
              aria-describedby={composerError ? "composer-error" : undefined}
              onChange={(event) => onComposerChange(event.target.value)}
            />
            {composerError ? (
              <p id="composer-error" className="field-error" role="alert">
                <AlertCircle />
                {composerError}
              </p>
            ) : null}
            <div className="composer-actions">
              <div className="left-tools">
                <button className="round-tool" type="button" aria-label="파일 첨부" title="파일 첨부" onClick={() => onOpenPanel("library")}>
                  <Paperclip />
                </button>
                <button className="round-tool" type="button" aria-label="스킬 선택" title="스킬 선택" onClick={() => onOpenPanel("skills")}>
                  <Workflow />
                </button>
                <button className="round-tool" type="button" aria-label="화면 연결" title="화면 연결" onClick={() => onOpenPanel("connections")}>
                  <Monitor />
                </button>
              </div>
              <div className="right-tools">
                <button className="ghost-tool" type="button" aria-label="음성 입력 준비" title="음성 입력 준비" onClick={() => onOpenPanel("connections")}>
                  <AudioLines />
                </button>
                <button className="ghost-tool" type="button" aria-label="마이크 권한" title="마이크 권한" onClick={() => onOpenPanel("notifications")}>
                  <Mic />
                </button>
                <button className={`send-button${composer.trim() ? " ready" : ""}`} type="button" aria-label="실행" title="실행" onClick={onStartRun}>
                  <ArrowUp />
                </button>
              </div>
            </div>
          </section>

          {suggestionsVisible ? (
            <section className="suggestions" aria-label="추천 항목">
              <div className="suggestion-header">
                <strong>추천 항목</strong>
                <div>
                  <IconButton label="새로고침" small onClick={onRefreshSuggestions}>
                    <RefreshCw />
                  </IconButton>
                  <IconButton label="닫기" small onClick={onHideSuggestions}>
                    <X />
                  </IconButton>
                </div>
              </div>
              <div className="suggestion-grid">
                {suggestions.map((item) => (
                  <button key={item.id} className="suggestion-card" type="button" onClick={() => onTemplate(item.command)}>
                    <div className="integration-row">
                      {item.tags.map((tag) => (
                        <span key={`${item.id}-${tag.label}`} className={`integration ${tag.tone}`}>
                          {tag.label}
                        </span>
                      ))}
                    </div>
                    <span>{item.body}</span>
                    <CornerDownLeft />
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <button className="restore-suggestions" type="button" onClick={onRefreshSuggestions}>
              추천 항목 다시 보기
            </button>
          )}
        </div>

        <section className="quick-actions" aria-label="빠른 작업">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button key={action.id} type="button" onClick={() => onTemplate(action.command)}>
                <Icon />
                <span>{action.label}</span>
              </button>
            );
          })}
          <button type="button" onClick={() => onOpenPanel("skills")}>
            <MoreHorizontal />
            <span>더보기</span>
          </button>
        </section>

        <section className="workspace-summary" aria-label="Workspace status">
          <button type="button" onClick={() => onOpenPanel("skills")}>
            <ShieldCheck />
            <span>
              <strong>스킬 생성</strong>
              <small>반복 작업을 팀 라이브러리로 승격</small>
            </span>
          </button>
          <button type="button" onClick={() => onOpenPanel("run")}>
            <Activity />
            <span>
              <strong>실행 기록</strong>
              <small>권한, 로그, 산출물 추적</small>
            </span>
          </button>
          <button type="button" onClick={() => onOpenPanel("library")}>
            <Database />
            <span>
              <strong>산출물 보관함</strong>
              <small>PPT, HWPX, 웹 요약본 관리</small>
            </span>
          </button>
        </section>
      </section>
    </main>
  );
}

function SkillHub({
  open,
  selectedSkill,
  activeTab,
  onClose,
  onSelectTab,
  onSelectSkill,
  onStartRun,
  onImportSkill,
}: {
  open: boolean;
  selectedSkill: SkillPackage;
  activeTab: SkillTab;
  onClose: () => void;
  onSelectTab: (tab: SkillTab) => void;
  onSelectSkill: (skill: SkillPackage) => void;
  onStartRun: () => void;
  onImportSkill: () => void;
}) {
  const filteredSkills = useMemo(() => {
    if (activeTab === "installed") return skills.filter((skill) => skill.enabled);
    if (activeTab === "review") return skills.filter((skill) => !skill.enabled);
    return skills;
  }, [activeTab]);

  return (
    <aside className={`detail-panel${open ? " open" : ""}`} aria-label="Nanus detail panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">Skill Hub</span>
          <h2>설치 가능한 스킬</h2>
        </div>
        <IconButton label="패널 닫기" onClick={onClose}>
          <X />
        </IconButton>
      </div>
      <div className="segmented" role="tablist" aria-label="Skill filter">
        <button className={activeTab === "recommended" ? "active" : undefined} type="button" onClick={() => onSelectTab("recommended")}>
          추천
        </button>
        <button className={activeTab === "installed" ? "active" : undefined} type="button" onClick={() => onSelectTab("installed")}>
          설치됨
        </button>
        <button className={activeTab === "review" ? "active" : undefined} type="button" onClick={() => onSelectTab("review")}>
          검토
        </button>
      </div>
      <div className="skill-list">
        {filteredSkills.map((skill) => {
          const Icon = skill.icon;
          return (
            <button
              key={skill.id}
              className={`skill-card${selectedSkill.id === skill.id ? " selected" : ""}`}
              type="button"
              onClick={() => onSelectSkill(skill)}
            >
              <div className={`skill-icon ${skill.tone}`}>
                <Icon />
              </div>
              <div>
                <strong>{skill.name}</strong>
                <span>{skill.description}</span>
                <small>{skill.source}</small>
              </div>
              {skill.enabled ? <Check className="skill-check" aria-hidden="true" /> : null}
            </button>
          );
        })}
      </div>
      <section className="permission-box">
        <div>
          <strong>실행 전 권한 리뷰</strong>
          <span>{selectedSkill.permissionSummary}</span>
        </div>
        <div className="permission-actions">
          <button type="button" className="secondary" onClick={onImportSkill}>
            <Upload />
            스킬 가져오기
          </button>
          <button type="button" onClick={onStartRun} disabled={!selectedSkill.enabled}>
            {selectedSkill.enabled ? "승인 후 실행" : "패키지 연결 필요"}
          </button>
        </div>
      </section>
    </aside>
  );
}

function RunInspector({
  open,
  run,
  paused,
  onClose,
  onTogglePause,
  onCopyLog,
  onExport,
}: {
  open: boolean;
  run: ActiveRun | null;
  paused: boolean;
  onClose: () => void;
  onTogglePause: () => void;
  onCopyLog: () => void;
  onExport: () => void;
}) {
  const status = paused ? "paused" : run?.status ?? "queued";
  const activeRun = run ?? createRun("/run 새 작업을 입력하면 여기에서 실행 상태를 확인할 수 있습니다");

  return (
    <aside className={`run-panel${open ? " open" : ""}`} aria-label="Current run inspector">
      <div className="panel-header">
        <div>
          <span className="eyebrow">Run Inspector</span>
          <h2>{activeRun.title}</h2>
        </div>
        <IconButton label="런 패널 닫기" onClick={onClose}>
          <X />
        </IconButton>
      </div>
      <div className="run-actions">
        <button type="button" onClick={onTogglePause}>
          {paused ? <Play /> : <Pause />}
          {paused ? "재개" : "일시정지"}
        </button>
        <button type="button" onClick={onCopyLog}>
          <Copy />
          로그 복사
        </button>
        <button type="button" onClick={onExport}>
          <Download />
          내보내기
        </button>
      </div>
      <div className="run-status">
        <span className={`status-dot ${status}`} />
        <strong>{paused ? "일시정지됨" : activeRun.status === "complete" ? "완료됨" : "실행 중"}</strong>
        <span>{activeRun.worker}</span>
      </div>
      <div className="run-progress" aria-label="실행 진행률">
        <span style={{ width: `${paused ? activeRun.progress : Math.max(activeRun.progress, 48)}%` }} />
      </div>
      <div className="run-meta">
        <span>{activeRun.command}</span>
        <span>{activeRun.startedAt}</span>
      </div>
      <ol className="timeline">
        {activeRun.steps.map((step) => (
          <li key={step.id} className={step.state === "pending" ? undefined : step.state}>
            <span />
            <div>
              <strong>{step.title}</strong>
              <small>{step.detail}</small>
            </div>
          </li>
        ))}
      </ol>
      <div className="artifact-preview">
        <div className={`slide-thumb ${activeRun.kind}`}>
          <span>{activeRun.artifacts[0]?.type ?? "result"}</span>
          <strong>{activeRun.artifacts[0]?.title ?? activeRun.title}</strong>
          <small>{commandLabels[activeRun.kind]}</small>
        </div>
        <div className="preview-lines">
          {activeRun.log.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </div>
      </div>
    </aside>
  );
}

function ContextPanel({
  panel,
  open,
  onClose,
  onTemplate,
  onNotify,
}: {
  panel: PanelId;
  open: boolean;
  onClose: () => void;
  onTemplate: (value: string) => void;
  onNotify: (title: string, detail: string, tone?: ToastMessage["tone"]) => void;
}) {
  const content = {
    agents: {
      eyebrow: "Agents",
      title: "에이전트 구성",
      body: agents,
    },
    schedule: {
      eyebrow: "Schedule",
      title: "예약된 실행",
      body: scheduledRuns,
    },
    library: {
      eyebrow: "Library",
      title: "산출물 라이브러리",
      body: libraryItems,
    },
  };

  if (panel === "connections") {
    const connectionItems = [
      { id: "codex", name: "Codex Workspace", detail: "현재 로컬 파일 시스템과 테스트 러너가 연결됨", icon: Terminal },
      { id: "claude", name: "Claude Code Bridge", detail: "외부 코드 에이전트 연결 슬롯 준비", icon: Command },
      { id: "browser", name: "Browser Session", detail: "Playwright 기반 화면 검증 가능", icon: Monitor },
    ];

    return (
      <aside className={`detail-panel${open ? " open" : ""}`} aria-label="Connection panel">
        <PanelTitle eyebrow="Connections" title="연결된 작업 환경" onClose={onClose} />
        <div className="context-list">
          {connectionItems.map((item) => {
            const Icon = item.icon;
            return (
            <button key={item.id} type="button" onClick={() => onNotify(item.name, item.detail, "success")}>
              <Icon />
              <span>
                <strong>{item.name}</strong>
                <small>{item.detail}</small>
              </span>
              <ExternalLink />
            </button>
          );
          })}
        </div>
      </aside>
    );
  }

  if (panel === "billing") {
    return (
      <aside className={`detail-panel${open ? " open" : ""}`} aria-label="Credit panel">
        <PanelTitle eyebrow="Credits" title="사용량과 비용" onClose={onClose} />
        <div className="metric-grid">
          <div>
            <strong>1,207</strong>
            <span>남은 실행 크레딧</span>
          </div>
          <div>
            <strong>72%</strong>
            <span>로컬 처리 비율</span>
          </div>
        </div>
        <button className="panel-primary" type="button" onClick={() => onNotify("비용 모드 적용", "고비용 클라우드 작업은 실행 전 승인을 요구합니다.", "success")}>
          비용 제한 모드 켜기
        </button>
      </aside>
    );
  }

  if (panel === "notifications") {
    return (
      <aside className={`detail-panel${open ? " open" : ""}`} aria-label="Notification panel">
        <PanelTitle eyebrow="Notifications" title="알림과 권한" onClose={onClose} />
        <div className="settings-list compact">
          <button type="button" onClick={() => onNotify("브라우저 알림 켜짐", "작업 완료와 승인 요청을 알려드립니다.", "success")}>
            <BellRing />
            <span>
              <strong>작업 완료 알림</strong>
              <small>긴 실행이 끝나면 알려줍니다.</small>
            </span>
            <span className="switch on" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => onNotify("마이크 권한 확인", "음성 입력은 연결 패널에서 다시 설정할 수 있습니다.", "default")}>
            <Mic />
            <span>
              <strong>음성 입력</strong>
              <small>명령 입력 보조 기능</small>
            </span>
            <span className="switch" aria-hidden="true" />
          </button>
        </div>
      </aside>
    );
  }

  if (!["agents", "schedule", "library"].includes(panel)) return null;

  const selected = content[panel as keyof typeof content];

  return (
    <aside className={`detail-panel${open ? " open" : ""}`} aria-label={`${selected.title} panel`}>
      <PanelTitle eyebrow={selected.eyebrow} title={selected.title} onClose={onClose} />
      <div className="context-list">
        {selected.body.map((item) => {
          const title = "description" in item ? item.name : item.title;
          const detail = "description" in item ? item.description : "cadence" in item ? `${item.cadence} · ${item.target}` : item.meta;
          const command = "description" in item ? `/agent ${item.name} ${item.description}` : "cadence" in item ? `/schedule ${item.title} ${item.cadence}` : `/library ${item.title}`;

          return (
            <button key={item.id} type="button" onClick={() => onTemplate(command)}>
              {"description" in item ? <Workflow /> : "cadence" in item ? <CalendarClock /> : <FileInput />}
              <span>
                <strong>{title}</strong>
                <small>{detail}</small>
              </span>
              <CornerDownLeft />
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function PanelTitle({ eyebrow, title, onClose }: { eyebrow: string; title: string; onClose: () => void }) {
  return (
    <div className="panel-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      <IconButton label="패널 닫기" onClick={onClose}>
        <X />
      </IconButton>
    </div>
  );
}

function SettingsPanel({
  open,
  theme,
  mode,
  density,
  onClose,
  onSetTheme,
  onSetMode,
  onSetDensity,
  onNotify,
}: {
  open: boolean;
  theme: ThemeMode;
  mode: WorkspaceMode;
  density: "comfortable" | "compact";
  onClose: () => void;
  onSetTheme: (theme: ThemeMode) => void;
  onSetMode: (mode: WorkspaceMode) => void;
  onSetDensity: (density: "comfortable" | "compact") => void;
  onNotify: (title: string, detail: string, tone?: ToastMessage["tone"]) => void;
}) {
  return (
    <aside className={`detail-panel settings-panel${open ? " open" : ""}`} aria-label="Settings panel">
      <PanelTitle eyebrow="Settings" title="작업공간 설정" onClose={onClose} />
      <div className="settings-list">
        <section>
          <h3>테마</h3>
          <div className="segmented two">
            <button className={theme === "dark" ? "active" : undefined} type="button" onClick={() => onSetTheme("dark")}>
              <Moon />
              다크
            </button>
            <button className={theme === "light" ? "active" : undefined} type="button" onClick={() => onSetTheme("light")}>
              <Sun />
              라이트
            </button>
          </div>
        </section>
        <section>
          <h3>실행 모드</h3>
          <div className="segmented two">
            <button className={mode === "local" ? "active" : undefined} type="button" onClick={() => onSetMode("local")}>
              <HardDrive />
              로컬
            </button>
            <button className={mode === "private" ? "active" : undefined} type="button" onClick={() => onSetMode("private")}>
              <ShieldCheck />
              프라이빗
            </button>
          </div>
        </section>
        <section>
          <h3>밀도</h3>
          <div className="segmented two">
            <button className={density === "comfortable" ? "active" : undefined} type="button" onClick={() => onSetDensity("comfortable")}>
              보통
            </button>
            <button className={density === "compact" ? "active" : undefined} type="button" onClick={() => onSetDensity("compact")}>
              컴팩트
            </button>
          </div>
        </section>
        <button className="panel-primary" type="button" onClick={() => onNotify("설정 저장됨", "테마, 실행 모드, 화면 밀도를 현재 브라우저에 저장했습니다.", "success")}>
          <CircleCheck />
          설정 저장
        </button>
      </div>
    </aside>
  );
}

function ProjectDialog({
  open,
  value,
  error,
  onChange,
  onClose,
  onSubmit,
}: {
  open: boolean;
  value: string;
  error: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  if (!open) return null;

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form className="modal-card" aria-label="새 프로젝트 만들기" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
        <div className="panel-header">
          <div>
            <span className="eyebrow">Project</span>
            <h2>새 프로젝트 만들기</h2>
          </div>
          <IconButton label="닫기" onClick={onClose}>
            <X />
          </IconButton>
        </div>
        <label className="field-label" htmlFor="project-name">
          프로젝트 이름
        </label>
        <input
          id="project-name"
          value={value}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "project-error" : undefined}
          placeholder="예: 교육지원 사업 분석"
          onChange={(event) => onChange(event.target.value)}
        />
        {error ? (
          <p id="project-error" className="field-error" role="alert">
            <AlertCircle />
            {error}
          </p>
        ) : null}
        <div className="modal-actions">
          <button type="button" onClick={onClose}>
            취소
          </button>
          <button type="submit" className="primary">
            생성
          </button>
        </div>
      </form>
    </div>
  );
}

function CommandPalette({
  open,
  query,
  onQueryChange,
  onClose,
  onRunCommand,
}: {
  open: boolean;
  query: string;
  onQueryChange: (value: string) => void;
  onClose: () => void;
  onRunCommand: (value: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const commands = useMemo(
    () => [
      ...skills.map((skill) => ({ id: skill.id, label: skill.name, detail: skill.enabled ? skill.worker : "패키지 연결 필요", value: `${skill.command} ` })),
      ...quickActions.map((action: QuickAction) => ({ id: action.id, label: action.label, detail: "빠른 작업", value: action.command })),
      { id: "settings", label: "설정 열기", detail: "테마, 실행 모드, 밀도", value: "/settings " },
    ],
    [],
  );
  const visibleCommands = commands.filter((item) => `${item.label} ${item.detail} ${item.value}`.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  return (
    <div className={`command-palette${open ? " open" : ""}`} role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={onClose}>
      <div className="palette-card" onMouseDown={(event) => event.stopPropagation()}>
        <div className="palette-input">
          <Search />
          <input ref={inputRef} type="text" value={query} aria-label="명령 입력" placeholder="명령, 스킬, 작업 검색" onChange={(event) => onQueryChange(event.target.value)} />
        </div>
        {visibleCommands.length ? (
          visibleCommands.map((command) => (
            <button key={command.id} type="button" onClick={() => onRunCommand(command.value)}>
              <span>{command.label}</span>
              <small>{command.detail}</small>
            </button>
          ))
        ) : (
          <div className="empty-state">
            <Search />
            <strong>검색 결과가 없습니다</strong>
            <span>다른 명령어나 스킬 이름을 입력하세요.</span>
          </div>
        )}
      </div>
    </div>
  );
}

function MobileTabs({
  activeView,
  onSelectView,
  onOpenRun,
}: {
  activeView: ViewId;
  onSelectView: (view: ViewId) => void;
  onOpenRun: () => void;
}) {
  return (
    <nav className="mobile-tabs" aria-label="Mobile">
      {mobileTabs.map((tab) => {
        const Icon = tab.icon;
        const active =
          (tab.id === "home" && activeView === "home") ||
          (tab.id === "skills" && activeView === "skills") ||
          (tab.id === "files" && activeView === "library");
        return (
          <button
            key={tab.id}
            className={active ? "active" : undefined}
            type="button"
            onClick={() => {
              if (tab.id === "run") onOpenRun();
              else if (tab.id === "skills") onSelectView("skills");
              else if (tab.id === "files") onSelectView("library");
              else onSelectView("home");
            }}
          >
            <Icon />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function ToastViewport({ toast, onDismiss }: { toast: ToastMessage | null; onDismiss: () => void }) {
  return (
    <div className="toast-viewport" aria-live="polite" aria-atomic="true">
      {toast ? (
        <div className={`toast ${toast.tone ?? "default"}`}>
          {toast.tone === "success" ? <CircleCheck /> : toast.tone === "warning" ? <AlertCircle /> : <Sparkles />}
          <span>
            <strong>{toast.title}</strong>
            <small>{toast.detail}</small>
          </span>
          <IconButton label="알림 닫기" small onClick={onDismiss}>
            <X />
          </IconButton>
        </div>
      ) : null}
    </div>
  );
}

export function App() {
  const [activeView, setActiveView] = useState<ViewId>("home");
  const [panel, setPanel] = useState<PanelId>("none");
  const [composer, setComposer] = useState("");
  const [composerError, setComposerError] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<SkillPackage>(skills[0]);
  const [skillTab, setSkillTab] = useState<SkillTab>("recommended");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [suggestionsVisible, setSuggestionsVisible] = useState(true);
  const [suggestionOffset, setSuggestionOffset] = useState(0);
  const [theme, setTheme] = useState<ThemeMode>(() => (localStorage.getItem("nanus-theme") === "light" ? "light" : "dark"));
  const [mode, setMode] = useState<WorkspaceMode>(() => (localStorage.getItem("nanus-mode") === "private" ? "private" : "local"));
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const [notificationStatus, setNotificationStatus] = useState<"unknown" | "on" | "off">("unknown");
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [projectDraft, setProjectDraft] = useState("");
  const [projectError, setProjectError] = useState("");
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [runPaused, setRunPaused] = useState(false);

  const visibleSuggestions = useMemo(() => {
    return recommendations.map((_, index) => recommendations[(index + suggestionOffset) % recommendations.length]);
  }, [suggestionOffset]);

  useEffect(() => {
    localStorage.setItem("nanus-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("nanus-mode", mode);
  }, [mode]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
        if (panel !== "none") setPanel("none");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [panel]);

  function notify(title: string, detail: string, tone: ToastMessage["tone"] = "default") {
    setToast({ id: Date.now(), title, detail, tone });
  }

  function openPanel(nextPanel: PanelId) {
    setPanel(nextPanel);
    setMobileSidebarOpen(false);
  }

  function selectView(view: ViewId) {
    setActiveView(view);
    setMobileSidebarOpen(false);
    if (view === "home") setPanel("none");
    else if (view === "skills") setPanel("skills");
    else setPanel(view);
  }

  function selectSkill(skill: SkillPackage) {
    setSelectedSkill(skill);
    setComposer(`${skill.command} `);
    setComposerError("");
    setPanel("skills");
    setPaletteOpen(false);
    setPaletteQuery("");
  }

  function applyTemplate(value: string) {
    setComposer(value);
    setComposerError("");
    setSuggestionsVisible(true);
    setPaletteOpen(false);
    setPaletteQuery("");
  }

  function updateComposer(value: string) {
    setComposer(value);
    setComposerError("");
    if (value.endsWith("/")) {
      setPaletteQuery("/");
      setPaletteOpen(true);
    }
  }

  function startRun() {
    const trimmed = composer.trim();
    if (!trimmed) {
      setComposerError("실행할 작업을 입력하거나 추천 항목을 선택하세요.");
      notify("작업 설명 필요", "추천 항목이나 빠른 작업을 누르면 바로 실행 초안을 만들 수 있습니다.", "warning");
      return;
    }
    const nextRun = createRun(trimmed);
    setActiveRun(nextRun);
    setRunPaused(false);
    setPanel("run");
    setMobileSidebarOpen(false);
    notify("실행 시작", `${mode === "local" ? "로컬" : "프라이빗"} 모드로 '${nextRun.title}' 작업을 시작했습니다.`, "success");
  }

  function selectTask(taskTitle: string) {
    const template = `/deck-from-brief ${taskTitle}`;
    applyTemplate(template);
    setActiveRun(createRun(template));
    setPanel("run");
  }

  function createProject() {
    const name = projectDraft.trim();
    if (!name) {
      setProjectError("프로젝트 이름을 입력하세요.");
      return;
    }
    setProjects((current) => [...current, { id: `${Date.now()}`, name }]);
    setProjectDraft("");
    setProjectError("");
    setPanel("none");
    notify("프로젝트 생성됨", `${name} 프로젝트가 사이드바에 추가됐습니다.`, "success");
  }

  function handleNotificationChoice(enabled: boolean) {
    setNotificationStatus(enabled ? "on" : "off");
    notify(enabled ? "알림 켜짐" : "알림 꺼짐", enabled ? "작업 완료와 승인 요청을 알려드립니다." : "나중에 알림 패널에서 다시 켤 수 있습니다.", enabled ? "success" : "default");
  }

  function runCommand(value: string) {
    if (value.startsWith("/settings")) {
      setPanel("settings");
      setPaletteOpen(false);
      setPaletteQuery("");
      return;
    }
    applyTemplate(value);
  }

  const projectDialogOpen = panel === "project";
  const contextPanelOpen = ["agents", "schedule", "library", "connections", "billing", "notifications"].includes(panel);

  return (
    <div className={`app-shell${sidebarCollapsed ? " sidebar-collapsed" : ""}`} data-theme={theme} data-density={density}>
      <Sidebar
        activeView={activeView}
        projects={projects}
        notificationStatus={notificationStatus}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileSidebarOpen}
        onToggleSidebar={() => {
          if (window.matchMedia("(max-width: 980px)").matches) setMobileSidebarOpen((open) => !open);
          else setSidebarCollapsed((collapsed) => !collapsed);
        }}
        onOpenPalette={() => setPaletteOpen(true)}
        onOpenProject={() => setPanel("project")}
        onOpenPanel={openPanel}
        onSelectView={selectView}
        onSelectSkill={selectSkill}
        onSelectTask={selectTask}
        onNotificationChoice={handleNotificationChoice}
      />
      <MainStage
        activeView={activeView}
        composer={composer}
        composerError={composerError}
        suggestions={visibleSuggestions}
        suggestionsVisible={suggestionsVisible}
        mode={mode}
        theme={theme}
        onComposerChange={updateComposer}
        onTemplate={applyTemplate}
        onOpenPanel={openPanel}
        onOpenPalette={() => setPaletteOpen(true)}
        onStartRun={startRun}
        onHideSuggestions={() => setSuggestionsVisible(false)}
        onRefreshSuggestions={() => {
          setSuggestionOffset((offset) => (offset + 1) % recommendations.length);
          setSuggestionsVisible(true);
        }}
        onSetMode={(nextMode) => {
          setMode(nextMode);
          notify("실행 모드 변경", nextMode === "local" ? "로컬 샌드박스를 우선 사용합니다." : "프라이빗 클라우드 실행을 우선 사용합니다.", "success");
        }}
        onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
        onToggleSidebar={() => {
          if (window.matchMedia("(max-width: 980px)").matches) setMobileSidebarOpen((open) => !open);
          else setSidebarCollapsed((collapsed) => !collapsed);
        }}
      />
      <SkillHub
        open={panel === "skills"}
        selectedSkill={selectedSkill}
        activeTab={skillTab}
        onClose={() => setPanel("none")}
        onSelectTab={setSkillTab}
        onSelectSkill={selectSkill}
        onStartRun={startRun}
        onImportSkill={() => notify("스킬 가져오기 준비", "Manus SKILL.md 패키지나 GitHub URL을 받는 연결 지점입니다.", "default")}
      />
      <RunInspector
        open={panel === "run"}
        run={activeRun}
        paused={runPaused}
        onClose={() => setPanel("none")}
        onTogglePause={() => {
          setRunPaused((paused) => !paused);
          notify(runPaused ? "실행 재개" : "실행 일시정지", runPaused ? "런 타임라인이 다시 진행됩니다." : "현재 단계에서 대기합니다.", "success");
        }}
        onCopyLog={() => notify("로그 복사됨", activeRun ? `${activeRun.title} 로그 ${activeRun.log.length}줄을 준비했습니다.` : "실행 후 로그를 복사할 수 있습니다.", "success")}
        onExport={() => notify("산출물 내보내기", activeRun ? `${activeRun.artifacts.map((artifact) => artifact.type).join(", ")} 산출물을 준비했습니다.` : "실행 후 산출물을 내보낼 수 있습니다.", "success")}
      />
      <ContextPanel panel={panel} open={contextPanelOpen} onClose={() => setPanel("none")} onTemplate={applyTemplate} onNotify={notify} />
      <SettingsPanel
        open={panel === "settings"}
        theme={theme}
        mode={mode}
        density={density}
        onClose={() => setPanel("none")}
        onSetTheme={(nextTheme) => {
          setTheme(nextTheme);
          notify("테마 변경", nextTheme === "dark" ? "다크 모드가 적용됐습니다." : "라이트 모드가 적용됐습니다.", "success");
        }}
        onSetMode={setMode}
        onSetDensity={setDensity}
        onNotify={notify}
      />
      <ProjectDialog
        open={projectDialogOpen}
        value={projectDraft}
        error={projectError}
        onChange={(value) => {
          setProjectDraft(value);
          setProjectError("");
        }}
        onClose={() => setPanel("none")}
        onSubmit={createProject}
      />
      <CommandPalette open={paletteOpen} query={paletteQuery} onQueryChange={setPaletteQuery} onClose={() => setPaletteOpen(false)} onRunCommand={runCommand} />
      <MobileTabs activeView={activeView} onSelectView={selectView} onOpenRun={() => setPanel("run")} />
      <ToastViewport toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
