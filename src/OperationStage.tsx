import { type Dispatch, type SetStateAction } from "react";
import { Activity, AlertCircle, ArrowUp, CheckCircle2, Clock3, Database, Monitor, Paperclip, ShieldCheck, Terminal, Workflow } from "lucide-react";
import RunWorkspace from "./RunWorkspace";
import type { ActiveRun, PanelId } from "./types";
import "./operation-stage.css";

function stageTone(run: ActiveRun) {
  if (run.status === "failed" || run.status === "cancelled") return "failed";
  if (run.status === "degraded" || run.verification?.fallbackUsed) return "degraded";
  if (run.status === "complete") return "verified";
  if (run.status === "waiting" || run.status === "paused") return "waiting";
  return "running";
}

function stageLabel(run: ActiveRun, paused: boolean) {
  if (paused || run.status === "paused") return "일시정지됨";
  if (run.status === "failed") return "실패";
  if (run.status === "cancelled") return "취소됨";
  if (run.status === "degraded") return "제한 실행";
  if (run.status === "complete") return "검증 완료";
  if (run.status === "waiting") return "승인 대기";
  if (run.status === "queued") return "대기열 등록";
  return "실행 중";
}

function latestAgentPhase(run: ActiveRun) {
  const raw = run.runtime?.agentLoop;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const record = raw[raw.length - 1] as Record<string, unknown>;
  return {
    title: String(record.title ?? "Agent loop"),
    detail: String(record.detail ?? "실행 중"),
  };
}

export default function OperationStage({
  activeRun,
  runPaused,
  composer,
  composerError,
  onComposerChange,
  onOpenPanel,
  onStartRun,
  onTogglePause,
  onRunChange,
}: {
  activeRun: ActiveRun;
  runPaused: boolean;
  composer: string;
  composerError: string;
  onComposerChange: (value: string) => void;
  onOpenPanel: (panel: PanelId) => void;
  onStartRun: () => void;
  onTogglePause: () => void;
  onRunChange: Dispatch<SetStateAction<ActiveRun | null>>;
}) {
  const effectivelyPaused = runPaused || activeRun.status === "paused";
  const terminal =
    activeRun.status === "complete" || activeRun.status === "failed" || activeRun.status === "cancelled" || activeRun.status === "degraded";
  const phase = latestAgentPhase(activeRun);
  const tone = stageTone(activeRun);
  const lanes = [
    {
      id: "planner",
      label: "Planner",
      value: phase?.title ?? "대기",
      detail: phase?.detail ?? "요구사항을 실행 그래프로 변환",
      icon: Workflow,
    },
    {
      id: "tools",
      label: "Tools",
      value: activeRun.source === "backend" ? "Backend" : "Local preview",
      detail: activeRun.source === "backend" ? "FastAPI · Codex · MCP" : "백엔드 연결 전 미리보기",
      icon: Terminal,
    },
    {
      id: "memory",
      label: "Memory",
      value: `${activeRun.log.length} events`,
      detail: activeRun.runtime?.conversation ? "conversation-linked" : "run-local",
      icon: Database,
    },
    {
      id: "trust",
      label: "Trust",
      value: activeRun.verification?.status ?? stageLabel(activeRun, effectivelyPaused),
      detail: activeRun.verification?.fallbackUsed ? "fallback 표시됨" : "상태와 결과 동기화",
      icon: ShieldCheck,
    },
  ];

  return (
    <section className="operation-stage" aria-label="Nanus operation workspace">
      <div className="operation-bar">
        <div>
          <span>{activeRun.command}</span>
          <strong>{activeRun.title}</strong>
        </div>
        <div className="operation-bar-actions">
          <button type="button" onClick={() => onOpenPanel("run")}>
            실행 기록
          </button>
          <button type="button" onClick={() => onOpenPanel("productivity")}>
            생산성
          </button>
        </div>
      </div>

      <section className={`operation-cockpit ${tone}`} aria-label="Agent cockpit">
        <div className="operation-cockpit-main">
          <span>Nanus Agent Workspace</span>
          <strong>{stageLabel(activeRun, effectivelyPaused)}</strong>
          <p>{phase?.detail ?? "대화, 도구 실행, 산출물 검증을 하나의 작업 흐름으로 추적합니다."}</p>
        </div>
        <div className="operation-cockpit-status">
          {terminal ? <CheckCircle2 /> : activeRun.status === "queued" ? <Clock3 /> : <Activity />}
          <span>{activeRun.progress}%</span>
        </div>
        <div className="operation-lane-grid">
          {lanes.map((lane) => {
            const Icon = lane.icon;
            return (
              <button key={lane.id} type="button" onClick={() => (lane.id === "tools" ? onOpenPanel("connections") : onOpenPanel("run"))}>
                <Icon />
                <span>
                  <small>{lane.label}</small>
                  <strong>{lane.value}</strong>
                  <em>{lane.detail}</em>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="operation-thread">
        <RunWorkspace run={activeRun} paused={runPaused} onOpenPanel={onOpenPanel} onTogglePause={onTogglePause} onRunChange={onRunChange} />
      </div>

      <section className="operation-composer composer" aria-label="작업 입력">
        <label className="sr-only" htmlFor="nanus-operation-composer">
          작업 입력
        </label>
        <textarea
          id="nanus-operation-composer"
          value={composer}
          rows={2}
          placeholder="Nanus에게 메시지 보내기"
          aria-invalid={Boolean(composerError)}
          aria-describedby={composerError ? "operation-composer-error" : undefined}
          onChange={(event) => onComposerChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              onStartRun();
            }
          }}
        />
        {composerError ? (
          <p id="operation-composer-error" className="field-error" role="alert">
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
            <button
              className="ghost-tool"
              type="button"
              aria-label={effectivelyPaused ? "실행 재개" : "실행 일시정지"}
              title={effectivelyPaused ? "실행 재개" : "실행 일시정지"}
              onClick={onTogglePause}
              disabled={terminal}
            >
              <Activity />
            </button>
            <button className={`send-button${composer.trim() ? " ready" : ""}`} type="button" aria-label="실행" title="실행" onClick={onStartRun}>
              <ArrowUp />
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}
