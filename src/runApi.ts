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

async function createBackendRun(input: string, mode: WorkspaceMode): Promise<ActiveRun> {
  const response = await fetch(backendApiUrl("/api/runs"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input, mode }),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return asBackendRun((await response.json()) as ActiveRun);
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
      if (payload.type === "run.done" || run?.status === "complete") finished = true;
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
  if (latest.status === "running" || latest.status === "queued") {
    return subscribeToRun(latest.id, onRun, (reason) => onRun({ ...latest, log: [...latest.log, `백엔드 재연결 실패: ${reason}`] }));
  }
  return null;
}

export async function connectBackendRun(input: string, mode: WorkspaceMode, localRun: ActiveRun, onRun: (run: ActiveRun) => void) {
  if (!backendEnabled) return null;
  const fallback = (reason: string) => onRun({ ...localRun, log: [...localRun.log, `백엔드 대체: ${reason}`] });
  try {
    const backendRun = await createBackendRun(input, mode);
    onRun(backendRun);
    return subscribeToRun(backendRun.id, onRun, fallback);
  } catch (error) {
    fallback(error instanceof Error ? error.message : "unknown");
    return null;
  }
}
