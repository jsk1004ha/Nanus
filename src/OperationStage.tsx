import { type Dispatch, type SetStateAction } from "react";
import { Activity, AlertCircle, ArrowUp, Monitor, Paperclip, Workflow } from "lucide-react";
import RunWorkspace from "./RunWorkspace";
import type { ActiveRun, PanelId } from "./types";
import "./operation-stage.css";

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
  const terminal = activeRun.status === "complete" || activeRun.status === "failed" || activeRun.status === "cancelled";

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
