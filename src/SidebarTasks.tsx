import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { tasks } from "./data";
import { loadBackendRuns } from "./runApi";
import { mergeRunHistory, readRunHistory, toRunHistoryItem, upsertRunHistory, writeRunHistory, type RunHistoryItem } from "./runHistory";
import type { ActiveRun } from "./types";

export default function SidebarTasks({
  activeRun,
  onRestoreRun,
  onSelectTask,
}: {
  activeRun: ActiveRun | null;
  onRestoreRun: (item: RunHistoryItem) => void;
  onSelectTask: (taskTitle: string) => void;
}) {
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>(() => readRunHistory());
  const activeRunId = activeRun?.id;

  useEffect(() => {
    if (activeRun) setRunHistory((current) => upsertRunHistory(current, activeRun));
  }, [activeRun]);

  useEffect(() => {
    let cancelled = false;
    void loadBackendRuns()
      .then((runs) => {
        if (cancelled) return;
        setRunHistory((current) => {
          const next = mergeRunHistory(current, runs.map(toRunHistoryItem));
          writeRunHistory(next);
          return next;
        });
      })
      .catch(() => {
        // Static preview still uses local history; backend sync is opportunistic.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      {runHistory.length ? (
        runHistory.map((item) => (
          <button
            key={item.id}
            className={`task-row history${item.id === activeRunId ? " selected" : ""}`}
            type="button"
            onClick={() => onRestoreRun(item)}
          >
            <Activity />
            <span>
              <strong>{item.title}</strong>
              <small>{item.status} · {item.progress}%</small>
            </span>
          </button>
        ))
      ) : (
        <span className="task-empty">실행 후 여기에 저장됩니다</span>
      )}
      <span className="task-template-label">빠른 시작</span>
      {tasks.map((task) => {
        const Icon = task.icon;
        return (
          <button key={task.id} className="task-row template" type="button" onClick={() => onSelectTask(task.title)}>
            <Icon />
            <span>{task.title}</span>
          </button>
        );
      })}
    </>
  );
}
