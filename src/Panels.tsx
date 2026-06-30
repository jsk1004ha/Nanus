import { useEffect, useMemo, useRef, type FormEvent, type ReactNode } from "react";
import {
  AlertCircle,
  BellRing,
  CalendarClock,
  Check,
  CircleCheck,
  Command,
  Copy,
  Download,
  ExternalLink,
  FileInput,
  Gauge,
  HardDrive,
  Mic,
  Monitor,
  Moon,
  Pause,
  Play,
  Search,
  ShieldCheck,
  Sun,
  Terminal,
  Upload,
  Workflow,
  X,
} from "lucide-react";
import { agents, libraryItems, quickActions, scheduledRuns, skills } from "./data";
import { createProductivityPlan } from "./productivityModel";
import { commandLabels, createRun } from "./runModel";
import type { ActiveRun, DensityMode, PanelId, QuickAction, SkillPackage, SkillTab, ThemeMode, WorkspaceMode } from "./types";

type NotifyTone = "default" | "success" | "warning";

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
  onNotify: (title: string, detail: string, tone?: NotifyTone) => void;
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
            </button>
          );
        })}
      </div>
    </aside>
  );
}

const workbenchModes = [
  {
    id: "coding",
    title: "코딩",
    command: "/codex-build 코드베이스를 분석하고 필요한 수정, 테스트, 검증까지 진행해줘",
    icon: Terminal,
    detail: "파일 수정, 터미널 실행, 테스트, 회귀 확인을 한 런으로 묶습니다.",
    lanes: ["코드베이스 읽기", "패치 작성", "타입/빌드/테스트", "리뷰 노트"],
    outputs: ["패치", "테스트 결과", "변경 요약"],
    guardrail: "workspace 변경 전 실행 범위와 검증 명령을 먼저 고정",
  },
  {
    id: "design",
    title: "디자인",
    command: "/design-qa 현재 화면을 분석하고 UX, 반응형, 접근성 개선을 실행 가능한 작업으로 정리해줘",
    icon: Monitor,
    detail: "스크린샷 기반 QA, UX 구조, 컴포넌트 상태, 반응형 문제를 함께 봅니다.",
    lanes: ["화면 캡처", "시각 QA", "UX 문구", "반응형 검증"],
    outputs: ["개선 목록", "디자인 토큰", "스크린샷 증거"],
    guardrail: "작은 화면과 실제 버튼 상태까지 확인",
  },
  {
    id: "research",
    title: "리서치",
    command: "/research-brief 핵심 질문을 조사하고 출처, 상충 근거, 결론, 다음 액션을 정리해줘",
    icon: Search,
    detail: "웹/문서 조사, 출처 검증, 요약 합성, 인용 가능한 브리프를 만듭니다.",
    lanes: ["질문 분해", "출처 수집", "근거 검증", "요약 합성"],
    outputs: ["리서치 브리프", "출처 목록", "한계와 후속 질문"],
    guardrail: "최신 정보와 직접 인용은 출처 확인 후 사용",
  },
] as const;

function WorkbenchPanel({
  open,
  onClose,
  onTemplate,
  onRunTemplate,
  onNotify,
}: {
  open: boolean;
  onClose: () => void;
  onTemplate: (value: string) => void;
  onRunTemplate: (value: string) => void;
  onNotify: (title: string, detail: string, tone?: NotifyTone) => void;
}) {
  return (
    <aside className={`detail-panel workbench-panel${open ? " open" : ""}`} aria-label="Workbench panel">
      <PanelTitle eyebrow="Manus-style Workbench" title="코딩 · 디자인 · 리서치" onClose={onClose} />
      <div className="workbench-list">
        {workbenchModes.map((mode) => {
          const Icon = mode.icon;
          return (
            <article key={mode.id} className="workbench-card">
              <div className="workbench-card-header">
                <span>
                  <Icon />
                </span>
                <div>
                  <strong>{mode.title}</strong>
                  <small>{mode.detail}</small>
                </div>
              </div>
              <div className="workbench-chip-row" aria-label={`${mode.title} 실행 레인`}>
                {mode.lanes.map((lane) => (
                  <span key={lane}>{lane}</span>
                ))}
              </div>
              <div className="workbench-output">
                <strong>산출물</strong>
                <small>{mode.outputs.join(" · ")}</small>
              </div>
              <div className="workbench-guardrail">
                <ShieldCheck />
                <span>{mode.guardrail}</span>
              </div>
              <div className="workbench-actions">
                <button type="button" onClick={() => onTemplate(mode.command)}>
                  입력창에 넣기
                </button>
                <button type="button" className="secondary" onClick={() => onRunTemplate(mode.command)}>
                  바로 실행
                </button>
                <IconButton label={`${mode.title} 권한 보기`} small onClick={() => onNotify(`${mode.title} 권한`, mode.guardrail, "default")}>
                  <ShieldCheck />
                </IconButton>
              </div>
            </article>
          );
        })}
      </div>
    </aside>
  );
}

function ProductivityPanel({
  open,
  run,
  draft,
  mode,
  paused,
  onClose,
  onTemplate,
  onNotify,
}: {
  open: boolean;
  run: ActiveRun | null;
  draft: string;
  mode: WorkspaceMode;
  paused: boolean;
  onClose: () => void;
  onTemplate: (value: string) => void;
  onNotify: (title: string, detail: string, tone?: NotifyTone) => void;
}) {
  const plan = createProductivityPlan(run, draft, { skills, agents, scheduledRuns, libraryItems, mode, paused });
  const reduction = Math.round((plan.savedHours / plan.manualHours) * 100);

  function savePlanToLedger() {
    try {
      const current = JSON.parse(localStorage.getItem("nanus-productivity-ledger") ?? "[]");
      const ledger = Array.isArray(current) ? current : [];
      const entry = {
        id: `${Date.now()}`,
        savedAt: new Date().toISOString(),
        title: plan.title,
        savedHours: plan.savedHours,
        automationScore: plan.automationScore,
        laneCount: plan.lanes.length,
        nextActions: plan.nextActions,
      };
      localStorage.setItem("nanus-productivity-ledger", JSON.stringify([entry, ...ledger].slice(0, 30)));
      onNotify("생산성 계획 저장", `${plan.nextActions.length}개 다음 액션을 로컬 ledger에 고정했습니다.`, "success");
    } catch {
      onNotify("ledger 저장 실패", "브라우저 로컬 저장소 권한을 확인하세요.", "warning");
    }
  }

  return (
    <aside className={`detail-panel productivity-panel${open ? " open" : ""}`} aria-label="Productivity panel">
      <PanelTitle eyebrow="Productivity Engine" title="Manus 대비 생산성 계획" onClose={onClose} />
      <section className="productivity-score" aria-label="생산성 점수">
        <div>
          <span>예상 절감</span>
          <strong>{plan.savedHours}h</strong>
          <small>
            수작업 {plan.manualHours}h → Nanus {plan.nanusHours}h
          </small>
        </div>
        <div>
          <span>자동화</span>
          <strong>{plan.automationScore}</strong>
          <small>반복 단계 자동화 점수</small>
        </div>
        <div>
          <span>레버리지</span>
          <strong>{reduction}%</strong>
          <small>병렬화와 스킬 재사용 효과</small>
        </div>
      </section>

      <div className="productivity-actions">
        <button type="button" onClick={() => onTemplate(`/productivity-plan ${plan.title}`)}>
          계획을 입력창에 적용
        </button>
        <button type="button" className="secondary" onClick={savePlanToLedger}>
          ledger 저장
        </button>
      </div>

      <section className="productivity-section">
        <h3>다음 실행 액션</h3>
        <ol className="next-action-list">
          {plan.nextActions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ol>
      </section>

      <section className="productivity-section">
        <h3>병렬 실행 레인</h3>
        <div className="lane-list">
          {plan.lanes.map((lane) => (
            <article key={lane.id}>
              <Gauge />
              <span>
                <strong>{lane.title}</strong>
                <small>{lane.owner} · {lane.minutes}분 · {lane.detail}</small>
              </span>
            </article>
          ))}
        </div>
      </section>

      <section className="productivity-section">
        <h3>스킬화 후보</h3>
        <div className="skill-candidate-list">
          {plan.reusableSkills.map((skill) => (
            <button key={skill.id} type="button" onClick={() => onTemplate(`${skill.command} ${plan.title}`)}>
              <strong>{skill.name}</strong>
              <small>{skill.payoff}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="productivity-section">
        <h3>위험 게이트</h3>
        <div className="risk-gate-list">
          {plan.riskGates.map((gate) => (
            <article key={gate.id} className={gate.status}>
              <span>{gate.status === "ready" ? "Ready" : gate.status === "review" ? "Review" : "Blocked"}</span>
              <strong>{gate.label}</strong>
              <small>{gate.detail}</small>
            </article>
          ))}
        </div>
      </section>
    </aside>
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
  density: DensityMode;
  onClose: () => void;
  onSetTheme: (theme: ThemeMode) => void;
  onSetMode: (mode: WorkspaceMode) => void;
  onSetDensity: (density: DensityMode) => void;
  onNotify: (title: string, detail: string, tone?: NotifyTone) => void;
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

export interface PanelsProps {
  panel: PanelId;
  selectedSkill: SkillPackage;
  skillTab: SkillTab;
  activeRun: ActiveRun | null;
  draft: string;
  runPaused: boolean;
  theme: ThemeMode;
  mode: WorkspaceMode;
  density: DensityMode;
  projectDraft: string;
  projectError: string;
  paletteOpen: boolean;
  paletteQuery: string;
  onClosePanel: () => void;
  onSelectSkill: (skill: SkillPackage) => void;
  onSelectTab: (tab: SkillTab) => void;
  onStartRun: () => void;
  onImportSkill: () => void;
  onTogglePause: () => void;
  onCopyLog: () => void;
  onExport: () => void;
  onTemplate: (value: string) => void;
  onRunTemplate: (value: string) => void;
  onNotify: (title: string, detail: string, tone?: NotifyTone) => void;
  onSetTheme: (theme: ThemeMode) => void;
  onSetMode: (mode: WorkspaceMode) => void;
  onSetDensity: (density: DensityMode) => void;
  onProjectDraftChange: (value: string) => void;
  onProjectSubmit: () => void;
  onPaletteQueryChange: (value: string) => void;
  onClosePalette: () => void;
  onRunCommand: (value: string) => void;
}

export default function Panels({
  panel,
  selectedSkill,
  skillTab,
  activeRun,
  draft,
  runPaused,
  theme,
  mode,
  density,
  projectDraft,
  projectError,
  paletteOpen,
  paletteQuery,
  onClosePanel,
  onSelectSkill,
  onSelectTab,
  onStartRun,
  onImportSkill,
  onTogglePause,
  onCopyLog,
  onExport,
  onTemplate,
  onRunTemplate,
  onNotify,
  onSetTheme,
  onSetMode,
  onSetDensity,
  onProjectDraftChange,
  onProjectSubmit,
  onPaletteQueryChange,
  onClosePalette,
  onRunCommand,
}: PanelsProps) {
  const contextPanelOpen = ["agents", "schedule", "library", "connections", "billing", "notifications"].includes(panel);

  return (
    <>
      <SkillHub
        open={panel === "skills"}
        selectedSkill={selectedSkill}
        activeTab={skillTab}
        onClose={onClosePanel}
        onSelectTab={onSelectTab}
        onSelectSkill={onSelectSkill}
        onStartRun={onStartRun}
        onImportSkill={onImportSkill}
      />
      <RunInspector
        open={panel === "run"}
        run={activeRun}
        paused={runPaused}
        onClose={onClosePanel}
        onTogglePause={onTogglePause}
        onCopyLog={onCopyLog}
        onExport={onExport}
      />
      <ContextPanel panel={panel} open={contextPanelOpen} onClose={onClosePanel} onTemplate={onTemplate} onNotify={onNotify} />
      <WorkbenchPanel open={panel === "workbench"} onClose={onClosePanel} onTemplate={onTemplate} onRunTemplate={onRunTemplate} onNotify={onNotify} />
      <ProductivityPanel
        open={panel === "productivity"}
        run={activeRun}
        draft={draft}
        mode={mode}
        paused={runPaused}
        onClose={onClosePanel}
        onTemplate={onTemplate}
        onNotify={onNotify}
      />
      <SettingsPanel
        open={panel === "settings"}
        theme={theme}
        mode={mode}
        density={density}
        onClose={onClosePanel}
        onSetTheme={onSetTheme}
        onSetMode={onSetMode}
        onSetDensity={onSetDensity}
        onNotify={onNotify}
      />
      <ProjectDialog open={panel === "project"} value={projectDraft} error={projectError} onChange={onProjectDraftChange} onClose={onClosePanel} onSubmit={onProjectSubmit} />
      <CommandPalette open={paletteOpen} query={paletteQuery} onQueryChange={onPaletteQueryChange} onClose={onClosePalette} onRunCommand={onRunCommand} />
    </>
  );
}
