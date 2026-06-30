import type { ActiveRun, RunStep } from "./types";

const progressIncrement = 22;

function progressSteps(steps: RunStep[], progress: number): RunStep[] {
  if (progress >= 100) {
    return steps.map((step) => ({ ...step, state: "done" }));
  }

  const activeIndex = Math.min(steps.length - 1, Math.max(0, Math.floor((progress / 100) * steps.length)));
  return steps.map((step, index) => ({
    ...step,
    state: index < activeIndex ? "done" : index === activeIndex ? "active" : "pending",
  }));
}

function appendRunLog(log: string[], line: string) {
  return log.includes(line) ? log : [...log, line];
}

export function advanceRun(run: ActiveRun): ActiveRun {
  if (run.status !== "running") return run;

  const progress = Math.min(100, run.progress + progressIncrement);
  const steps = progressSteps(run.steps, progress);
  const status: ActiveRun["status"] = progress >= 100 ? "complete" : "running";
  const previousDoneIds = new Set(run.steps.filter((step) => step.state === "done").map((step) => step.id));
  let log = run.log;

  for (const step of steps) {
    if (step.state === "done" && !previousDoneIds.has(step.id)) {
      log = appendRunLog(log, `완료: ${step.title}`);
    }
  }

  const activeStep = steps.find((step) => step.state === "active");
  if (activeStep) {
    log = appendRunLog(log, `현재 단계: ${activeStep.title}`);
  }

  if (status === "complete") {
    log = appendRunLog(log, "실행이 완료되었습니다.");
  }

  return {
    ...run,
    progress,
    status,
    steps,
    log,
  };
}
