import type { ActiveRun } from "./types";

export interface RunHistoryItem {
  id: string;
  title: string;
  prompt: string;
  command: string;
  status: ActiveRun["status"];
  progress: number;
  startedAt: string;
  source: "local" | "backend";
  snapshot: ActiveRun;
}

const RUN_HISTORY_KEY = "nanus-run-history";
const MAX_RUN_HISTORY = 8;

function stripLargeDownloads(run: ActiveRun): ActiveRun {
  return {
    ...run,
    artifacts: run.artifacts.map((artifact) => {
      const download = artifact.content?.download;
      if (!download?.base64) return artifact;
      return {
        ...artifact,
        content: {
          ...artifact.content,
          download: {
            ...download,
            base64: undefined,
          },
        },
      };
    }),
  };
}

export function toRunHistoryItem(run: ActiveRun): RunHistoryItem {
  const snapshot = stripLargeDownloads({ ...run, source: run.source ?? "local" });
  return {
    id: run.id,
    title: run.title,
    prompt: run.prompt,
    command: run.command,
    status: run.status,
    progress: run.progress,
    startedAt: run.startedAt,
    source: run.source ?? "local",
    snapshot,
  };
}

export function readRunHistory(): RunHistoryItem[] {
  try {
    const raw = localStorage.getItem(RUN_HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is RunHistoryItem => Boolean(item?.id && item?.title && item?.snapshot));
  } catch {
    return [];
  }
}

export function writeRunHistory(history: RunHistoryItem[]) {
  try {
    localStorage.setItem(RUN_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_RUN_HISTORY)));
  } catch {
    // History is a convenience layer; backend SQLite remains the source of truth when available.
  }
}

export function mergeRunHistory(current: RunHistoryItem[], items: RunHistoryItem[]) {
  const seen = new Set<string>();
  return [...items, ...current].filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  }).slice(0, MAX_RUN_HISTORY);
}

export function upsertRunHistory(current: RunHistoryItem[], run: ActiveRun) {
  const next = mergeRunHistory(current, [toRunHistoryItem(run)]);
  writeRunHistory(next);
  return next;
}
