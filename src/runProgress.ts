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

function localFinalAnswer(run: ActiveRun) {
  if (run.finalAnswer) return run.finalAnswer;
  if (run.kind === "writing") {
    return (
      "글을 늘릴 때는 같은 말을 반복하기보다 문제 배경, 판단 기준, 계산 근거, 실험 절차, 예상 문제와 대응 방안을 추가하는 방식이 좋습니다.\n\n" +
      "먼저 원고의 각 섹션마다 '왜 필요한가', '어떻게 확인할 것인가', '실패하면 어떻게 대응할 것인가' 중 하나를 덧붙이세요. " +
      "그 다음 바로 붙여넣을 수 있는 문단 예시를 섹션별로 추가하면 분량과 설득력이 함께 늘어납니다."
    );
  }
  return `${run.title} 요청을 로컬 미리보기로 처리했습니다. 실제 백엔드가 연결되면 이 영역에는 assistant 최종 답변과 검증 정보가 표시됩니다.`;
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
    finalAnswer: status === "complete" ? localFinalAnswer(run) : run.finalAnswer,
    resultType: status === "complete" ? run.resultType ?? (run.kind === "writing" ? "writing_advice" : "answer") : run.resultType,
    verification:
      status === "complete"
        ? run.verification ?? {
            backendUsed: false,
            llmUsed: false,
            fallbackUsed: true,
            errors: [],
            warnings: ["브라우저 로컬 미리보기 결과입니다."],
          }
        : run.verification,
  };
}
