import { useEffect, type Dispatch, type SetStateAction } from "react";
import { Activity } from "lucide-react";
import { commandLabels } from "./runModel";
import { advanceRun } from "./runProgress";
import type { ActiveRun, PanelId } from "./types";
import "./run-workspace.css";

export default function RunWorkspace({
  run,
  paused,
  onOpenPanel,
  onTogglePause,
  onRunChange,
}: {
  run: ActiveRun;
  paused: boolean;
  onOpenPanel: (panel: PanelId) => void;
  onTogglePause: () => void;
  onRunChange: Dispatch<SetStateAction<ActiveRun | null>>;
}) {
  useEffect(() => {
    if (paused || run.status !== "running" || run.source === "backend") return undefined;

    const interval = window.setInterval(() => {
      onRunChange((currentRun) => {
        if (!currentRun || currentRun.status !== "running") return currentRun;
        return advanceRun(currentRun);
      });
    }, 650);

    return () => window.clearInterval(interval);
  }, [onRunChange, paused, run.id, run.source, run.status]);

  const activeStep = run.steps.find((step) => step.state === "active");
  const terminal = run.status === "complete" || run.status === "failed" || run.status === "cancelled" || run.status === "degraded";
  const effectivelyPaused = paused || run.status === "paused";
  const statusLabel = effectivelyPaused
    ? "일시정지됨"
    : run.status === "complete"
      ? "완료됨"
      : run.status === "queued"
        ? "대기 중"
        : run.status === "waiting"
          ? "승인 대기"
          : run.status === "failed"
            ? "실패"
            : run.status === "degraded"
              ? "제한 실행"
            : run.status === "cancelled"
              ? "취소됨"
              : "실행 중";
  const statusClass = paused ? "paused" : run.status;
  const visibleLogs = run.log.slice(-6);
  const runtimeState = effectivelyPaused ? "PAUSED" : run.status === "complete" ? "FINISHED" : run.status.toUpperCase();
  const answerParagraphs = run.finalAnswer?.split(/\n{2,}/).map((part) => part.trim()).filter(Boolean) ?? [];
  const runtimeStack = [
    { label: "State loop", value: runtimeState, detail: `${run.steps.filter((step) => step.state === "done").length}/${run.steps.length} steps` },
    { label: "Memory", value: `${run.log.length} records`, detail: "user · agent · observe" },
    { label: "Tool collection", value: run.source === "backend" ? "FastAPI · Codex · MCP" : "Browser · Editor · Ask", detail: run.source === "backend" ? "SQLite + WebSocket stream" : "local tools + MCP-ready" },
    { label: "Planning flow", value: activeStep?.title ?? "완료", detail: `${run.worker} handoff` },
  ];

  return (
    <section className="active-run-workspace" aria-label="Active run workspace">
      <div className="user-run-bubble" aria-label="User prompt">
        <span>요청</span>
        <p>{run.prompt || run.command}</p>
      </div>

      <article className="agent-run-card">
        <header className="agent-run-header">
          <span className="agent-avatar" aria-hidden="true">
            <img src="/nanus-icon.png" alt="" />
          </span>
          <div>
            <strong>nanus</strong>
            <small>{run.worker}</small>
          </div>
          <span className={`run-badge ${statusClass}`} data-testid="run-status">
            {statusLabel}
          </span>
        </header>

        <div className="agent-run-copy">
          <h2>{run.title}</h2>
          <p>
            {run.finalAnswer
              ? "Nanus가 최종 답변을 생성했습니다. 실행 로그와 산출물은 아래에서 확인할 수 있습니다."
              : run.status === "complete"
                ? `${commandLabels[run.kind]} 결과를 만들고 검증 대기 산출물을 정리했습니다.`
              : run.status === "failed"
                ? "실행 중 오류가 발생했습니다. 실행 기록에서 로그를 확인하세요."
                : run.status === "degraded"
                  ? "일부 도구가 실패해 제한된 결과만 표시합니다."
                : run.status === "cancelled"
                  ? "사용자 요청으로 실행을 취소했습니다."
                  : effectivelyPaused
                ? `${activeStep?.title ?? "현재 단계"}에서 실행을 멈춰 두었습니다.`
                : `${activeStep?.title ?? "작업 준비"} 단계가 진행 중입니다.`}
          </p>
        </div>

        {answerParagraphs.length ? (
          <section className={`assistant-answer${run.status === "failed" ? " error" : ""}`} aria-label="Assistant message">
            <span>{run.status === "failed" ? "실패 원인" : "답변"}</span>
            {answerParagraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </section>
        ) : null}

        <div className="agent-run-metrics" aria-label="Run summary">
          <span>
            <strong>{run.command}</strong>
            <small>명령</small>
          </span>
          <span>
            <strong>{run.progress}%</strong>
            <small>진행률</small>
          </span>
          <span>
            <strong>{run.verification?.fallbackUsed ? "fallback" : run.verification?.llmUsed ? "live" : run.source ?? "local"}</strong>
            <small>실행 출처</small>
          </span>
        </div>

        <div className="agent-runtime-grid" aria-label="OpenManus-inspired runtime">
          {runtimeStack.map((item) => (
            <span key={item.label}>
              <small>{item.label}</small>
              <strong>{item.value}</strong>
              <em>{item.detail}</em>
            </span>
          ))}
        </div>

        <span className="sr-only" data-testid="run-progress-value">
          {run.progress}
        </span>
        <div
          className="run-progress active-run-progress"
          role="progressbar"
          aria-label="실행 진행률"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={run.progress}
        >
          <span style={{ width: `${run.progress}%` }} />
        </div>

        <ol className="timeline active-run-timeline">
          {run.steps.map((step) => (
            <li key={step.id} className={step.state === "pending" ? undefined : step.state}>
              <span />
              <div>
                <strong>{step.title}</strong>
                <small>{step.detail}</small>
              </div>
            </li>
          ))}
        </ol>

        <div className="active-run-log" aria-label="Run log">
          {visibleLogs.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </div>

        <div className="active-run-artifacts" aria-label="Run artifacts">
          {run.artifacts.map((artifact) => (
            <button key={artifact.id} type="button" onClick={() => onOpenPanel("library")}>
              <span>{artifact.type}</span>
              <strong>{artifact.title}</strong>
            </button>
          ))}
        </div>

        <div className="active-run-actions">
          <button type="button" onClick={onTogglePause} disabled={terminal}>
            <Activity />
            {effectivelyPaused ? "재개" : "일시정지"}
          </button>
          <button type="button" className="secondary" onClick={() => onOpenPanel("run")}>
            실행 기록
          </button>
          <button type="button" className="secondary" onClick={() => onOpenPanel("productivity")}>
            생산성 엔진
          </button>
        </div>
      </article>
    </section>
  );
}
