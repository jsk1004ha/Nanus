import type { ActiveRun, WorkspaceMode } from "./types";
import { backendApiUrl, backendEnabled, backendWebSocketUrl } from "./backendConfig";

interface BackendRunEvent {
  type: string;
  payload?: { run?: ActiveRun; message?: string };
  run?: ActiveRun;
  message?: string | null;
}

function asBackendRun(run: ActiveRun): ActiveRun {
  return { ...run, source: "backend" };
}

function isTerminalRun(run: ActiveRun) {
  return run.status === "complete" || run.status === "failed" || run.status === "cancelled" || run.status === "degraded";
}

async function createBackendRun(input: string, mode: WorkspaceMode): Promise<ActiveRun> {
  const response = await fetch(backendApiUrl("/api/chat"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: input, mode }),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = (await response.json()) as { run?: ActiveRun };
  if (!payload.run) throw new Error("Backend returned no run");
  return asBackendRun(payload.run);
}

function subscribeToRun(runId: string, onRun: (run: ActiveRun) => void, onFallback: (reason: string) => void) {
  let closed = false;
  let finished = false;
  const socket = new WebSocket(backendWebSocketUrl(`/ws/run/${encodeURIComponent(runId)}`));
  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data as string) as BackendRunEvent;
      const run = payload.payload?.run ?? payload.run;
      if (run) onRun(asBackendRun(run));
      if (payload.type === "run.done" || (run && isTerminalRun(run))) finished = true;
      if (payload.type === "error") onFallback(payload.payload?.message ?? payload.message ?? "stream error");
    } catch {
      onFallback("invalid WebSocket event");
    }
  });
  socket.addEventListener("error", () => {
    if (!closed) onFallback("WebSocket failed");
  });
  socket.addEventListener("close", () => {
    if (!closed && !finished) onFallback("WebSocket closed before completion");
  });
  return () => {
    closed = true;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) socket.close();
  };
}

export async function loadBackendRuns(): Promise<ActiveRun[]> {
  if (!backendEnabled) throw new Error("backend disabled");
  const response = await fetch(backendApiUrl("/api/runs"));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = (await response.json()) as { runs?: ActiveRun[] };
  return (payload.runs ?? []).map(asBackendRun);
}

export async function restoreLatestBackendRun(onRun: (run: ActiveRun) => void) {
  const runs = await loadBackendRuns();
  const latest = runs[0];
  if (!latest) return null;
  onRun(latest);
  if (!isTerminalRun(latest)) {
    return subscribeToRun(latest.id, onRun, (reason) => onRun({ ...latest, log: [...latest.log, `백엔드 재연결 실패: ${reason}`] }));
  }
  return null;
}

export async function setBackendRunPaused(runId: string, paused: boolean): Promise<ActiveRun> {
  if (!backendEnabled) throw new Error("backend disabled");
  const response = await fetch(backendApiUrl(`/api/runs/${encodeURIComponent(runId)}/${paused ? "pause" : "resume"}`), {
    method: "POST",
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = (await response.json()) as { run: ActiveRun };
  return asBackendRun(payload.run);
}

export async function cancelBackendRun(runId: string): Promise<ActiveRun> {
  if (!backendEnabled) throw new Error("backend disabled");
  const response = await fetch(backendApiUrl(`/api/runs/${encodeURIComponent(runId)}/cancel`), {
    method: "POST",
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = (await response.json()) as { run: ActiveRun };
  return asBackendRun(payload.run);
}

export async function connectBackendRun(input: string, mode: WorkspaceMode, localRun: ActiveRun, onRun: (run: ActiveRun) => void) {
  if (!backendEnabled) return null;
  const failRun = (reason: string) =>
    onRun({
      ...localRun,
      status: "failed",
      progress: 0,
      steps: localRun.steps.map((step) => ({ ...step, state: "pending" })),
      artifacts: [],
      finalAnswer: `실제 백엔드 실행이 실패했습니다.\n\n원인: ${reason}\n\n이 화면은 성공 결과가 아니며, 로컬 미리보기로 완료 처리하지 않았습니다. 입력이 매우 길다면 파일/문서 업로드 경로가 필요합니다.`,
      resultType: "backend_error",
      verification: {
        backendUsed: false,
        llmUsed: false,
        fallbackUsed: false,
        errors: [reason],
        warnings: ["백엔드 실패를 로컬 완료로 대체하지 않았습니다."],
      },
      log: [...localRun.log, `백엔드 실행 실패: ${reason}`, "실제 실행 결과가 아니므로 완료 처리하지 않았습니다."],
    });
  try {
    const backendRun = await createBackendRun(input, mode);
    onRun(backendRun);
    return subscribeToRun(backendRun.id, onRun, failRun);
  } catch (error) {
    failRun(error instanceof Error ? error.message : "unknown");
    return null;
  }
}
