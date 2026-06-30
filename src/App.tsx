import { lazy, Suspense, useEffect, useMemo, useRef, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import {
  Activity,
  AlertCircle,
  ArrowUp,
  Bell,
  BellRing,
  ChevronDown,
  CircleCheck,
  CornerDownLeft,
  FolderOpen,
  FolderPlus,
  ListFilter,
  Mic,
  Monitor,
  Moon,
  MoreHorizontal,
  PanelLeft,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Sun,
  Workflow,
  X,
} from "lucide-react";
import {
  mobileTabs,
  navItems,
  quickActions,
  recommendations,
  skills,
  tasks,
} from "./data";
import { createRun } from "./runModel";
import type { ActiveRun, DensityMode, PanelId, Recommendation, SkillPackage, SkillTab, ThemeMode, ViewId, WorkspaceMode } from "./types";

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

const Panels = lazy(() => import("./Panels"));
const RunWorkspace = lazy(() => import("./RunWorkspace"));

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
  workbench: {
    eyebrow: "Workbench",
    title: "작업 선택",
    placeholder: "코드/디자인/문서",
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
            <img src="/nanus-icon.png" alt="" />
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
            <span>{notificationStatus === "unknown" ? "브라우저 알림을 켜세요." : "알림이 꺼져 있습니다."}</span>
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
  activeRun,
  runPaused,
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
  onTogglePause,
  onRunChange,
}: {
  activeView: ViewId;
  composer: string;
  composerError: string;
  suggestions: Recommendation[];
  suggestionsVisible: boolean;
  activeRun: ActiveRun | null;
  runPaused: boolean;
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
  onTogglePause: () => void;
  onRunChange: Dispatch<SetStateAction<ActiveRun | null>>;
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
            <span>Nanus Control</span>
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
            <Sparkles />
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
            프라이빗
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
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  onStartRun();
                }
              }}
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
                  <Mic />
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

        {activeRun ? (
          <Suspense fallback={null}>
            <RunWorkspace run={activeRun} paused={runPaused} onOpenPanel={onOpenPanel} onTogglePause={onTogglePause} onRunChange={onRunChange} />
          </Suspense>
        ) : null}

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
            <FolderOpen />
            <span>
              <strong>산출물 보관함</strong>
              <small>PPT, HWPX, 웹 요약본 관리</small>
            </span>
          </button>
          <button type="button" onClick={() => onOpenPanel("productivity")}>
            <Activity />
            <span>
              <strong>생산성 엔진</strong>
              <small>Manus 대비 절감 시간과 병렬 레인 측정</small>
            </span>
          </button>
        </section>
      </section>
    </main>
  );
}

function MobileTabs({
  activeView,
  onSelectView,
  onOpenRun,
  onOpenProductivity,
}: {
  activeView: ViewId;
  onSelectView: (view: ViewId) => void;
  onOpenRun: () => void;
  onOpenProductivity: () => void;
}) {
  return (
    <nav className="mobile-tabs" aria-label="Mobile">
      {mobileTabs.map((tab) => {
        const Icon = tab.icon;
        const active =
          (tab.id === "home" && activeView === "home") ||
          (tab.id === "workbench" && activeView === "workbench") ||
          (tab.id === "skills" && activeView === "skills") ||
          (tab.id === "files" && activeView === "library");
        return (
          <button
            key={tab.id}
            className={active ? "active" : undefined}
            type="button"
            onClick={() => {
              if (tab.id === "run") onOpenRun();
              else if (tab.id === "productivity") onOpenProductivity();
              else if (tab.id === "workbench") onSelectView("workbench");
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
  const [density, setDensity] = useState<DensityMode>("comfortable");
  const [notificationStatus, setNotificationStatus] = useState<"unknown" | "on" | "off">("unknown");
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [projectDraft, setProjectDraft] = useState("");
  const [projectError, setProjectError] = useState("");
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [runPaused, setRunPaused] = useState(false);
  const runStreamCleanup = useRef<(() => void) | null>(null);
  const runLaunchCount = useRef(0);

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
    return () => {
      runStreamCleanup.current?.();
    };
  }, []);

  useEffect(() => {
    const shouldRestoreBackend =
      import.meta.env.VITE_NANUS_RESTORE_BACKEND === "true" || Boolean(import.meta.env.VITE_NANUS_API_BASE);
    if (!shouldRestoreBackend) return undefined;

    let cancelled = false;
    const restoreToken = runLaunchCount.current;
    void import("./runApi")
      .then(({ restoreLatestBackendRun }) =>
        restoreLatestBackendRun((run) => {
          if (!cancelled && runLaunchCount.current === restoreToken) setActiveRun(run);
        }),
      )
      .then((cleanup) => {
        if (cancelled || runLaunchCount.current !== restoreToken) cleanup?.();
        else if (cleanup) runStreamCleanup.current = cleanup;
      })
      .catch(() => {
        // Backend is optional during static preview; local fallback remains active.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

  async function beginRun(input: string) {
    runLaunchCount.current += 1;
    const launchToken = runLaunchCount.current;
    const launchMode = mode;
    runStreamCleanup.current?.();
    runStreamCleanup.current = null;

    const localRun: ActiveRun = { ...createRun(input), source: "local" };
    setActiveRun(localRun);
    setRunPaused(false);
    setPanel("none");
    setMobileSidebarOpen(false);
    notify("실행 시작", `${launchMode === "local" ? "로컬" : "프라이빗"} · ${localRun.title}`, "success");

    void import("./runApi").then(({ connectBackendRun }) =>
      connectBackendRun(input, launchMode, localRun, (run) => {
        if (runLaunchCount.current === launchToken) setActiveRun(run);
      }).then((cleanup) => {
        if (runLaunchCount.current !== launchToken) cleanup?.();
        else runStreamCleanup.current = cleanup;
      }),
    ).catch((error: unknown) => {
      if (runLaunchCount.current === launchToken) {
        const detail = error instanceof Error ? error.message : "unknown";
        setActiveRun({ ...localRun, log: [...localRun.log, `백엔드 모듈 로드 실패: ${detail}`] });
      }
    });
  }

  function startRun() {
    const trimmed = composer.trim();
    if (!trimmed) {
      setComposerError("실행할 작업을 입력하세요.");
      notify("작업 설명 필요", "추천 항목을 선택할 수 있습니다.", "warning");
      return;
    }
    void beginRun(trimmed);
  }

  function runTemplate(value: string) {
    setComposer(value);
    setComposerError("");
    setSuggestionsVisible(true);
    setPaletteOpen(false);
    setPaletteQuery("");
    void beginRun(value);
  }

  function selectTask(taskTitle: string) {
    const template = `/deck-from-brief ${taskTitle}`;
    applyTemplate(template);
    void beginRun(template);
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
      notify("프로젝트 생성됨", `${name} 추가됨`, "success");
  }

  function handleNotificationChoice(enabled: boolean) {
    setNotificationStatus(enabled ? "on" : "off");
    notify(enabled ? "알림 켜짐" : "알림 꺼짐", enabled ? "완료/승인 요청 알림" : "나중에 다시 켤 수 있습니다.", enabled ? "success" : "default");
  }

  function toggleRunPause() {
    if (!activeRun || activeRun.status !== "running") {
      notify("일시정지 불가", activeRun?.status === "complete" ? "완료된 런입니다." : "실행 중인 작업이 없습니다.", "warning");
      return;
    }
    const nextPaused = !runPaused;
    setRunPaused(nextPaused);
    notify(nextPaused ? "실행 일시정지" : "실행 재개", nextPaused ? "현재 단계 대기" : "타임라인 재개", "success");
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
        activeRun={activeRun}
        runPaused={runPaused}
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
          notify("실행 모드 변경", nextMode === "local" ? "로컬 우선" : "프라이빗 우선", "success");
        }}
        onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
        onTogglePause={toggleRunPause}
        onRunChange={setActiveRun}
        onToggleSidebar={() => {
          if (window.matchMedia("(max-width: 980px)").matches) setMobileSidebarOpen((open) => !open);
          else setSidebarCollapsed((collapsed) => !collapsed);
        }}
      />
      {panel !== "none" || paletteOpen ? (
        <Suspense fallback={null}>
          <Panels
            panel={panel}
            selectedSkill={selectedSkill}
            skillTab={skillTab}
            activeRun={activeRun}
            draft={composer}
            runPaused={runPaused}
            theme={theme}
            mode={mode}
            density={density}
            projectDraft={projectDraft}
            projectError={projectError}
            paletteOpen={paletteOpen}
            paletteQuery={paletteQuery}
            onClosePanel={() => setPanel("none")}
            onSelectSkill={selectSkill}
            onSelectTab={setSkillTab}
            onStartRun={startRun}
            onImportSkill={() => notify("스킬 가져오기 준비", "SKILL.md/GitHub URL 연결", "default")}
            onTogglePause={toggleRunPause}
            onCopyLog={() => notify("로그 복사됨", activeRun ? `${activeRun.title} 로그 ${activeRun.log.length}줄` : "실행 후 복사 가능", "success")}
            onRestoreRun={(run) => {
              runStreamCleanup.current?.();
              runStreamCleanup.current = null;
              setRunPaused(false);
              setActiveRun(run);
              notify("저장된 실행 열림", `${run.title} 기록을 SQLite 백엔드에서 불러왔습니다.`, "success");
            }}
            onTemplate={applyTemplate}
            onRunTemplate={runTemplate}
            onNotify={notify}
            onSetTheme={(nextTheme) => {
              setTheme(nextTheme);
              notify("테마 변경", nextTheme === "dark" ? "다크 모드가 적용됐습니다." : "라이트 모드가 적용됐습니다.", "success");
            }}
            onSetMode={setMode}
            onSetDensity={setDensity}
            onProjectDraftChange={(value) => {
              setProjectDraft(value);
              setProjectError("");
            }}
            onProjectSubmit={createProject}
            onPaletteQueryChange={setPaletteQuery}
            onClosePalette={() => setPaletteOpen(false)}
            onRunCommand={runCommand}
          />
        </Suspense>
      ) : null}
      <MobileTabs activeView={activeView} onSelectView={selectView} onOpenRun={() => setPanel("run")} onOpenProductivity={() => setPanel("productivity")} />
      <ToastViewport toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
