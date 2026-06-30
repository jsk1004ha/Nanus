import type { ActiveRun, ProductivityPlan, SkillPackage, WorkspaceMode } from "./types";

export interface ProductivityWorkspaceContext {
  mode: WorkspaceMode;
  paused: boolean;
  skills: Array<Pick<SkillPackage, "command" | "name" | "enabled" | "worker">>;
  agents: Array<{ id: string; name: string; status: string; description: string }>;
  scheduledRuns: Array<{ id: string; title: string; cadence: string; target: string }>;
  libraryItems: Array<{ id: string; title: string; meta: string }>;
}

const base = { manualHours: 5.5, nanusHours: 1.4, automationScore: 81, leverageScore: 80 };
const profiles: Record<string, typeof base> = {
  deck: { manualHours: 9.5, nanusHours: 1.8, automationScore: 88, leverageScore: 91 },
  writing: { manualHours: 4.5, nanusHours: 0.7, automationScore: 84, leverageScore: 82 },
  document: { manualHours: 7.5, nanusHours: 1.2, automationScore: 86, leverageScore: 86 },
  spreadsheet: { manualHours: 8.5, nanusHours: 1.5, automationScore: 85, leverageScore: 84 },
  visualization: { manualHours: 7.5, nanusHours: 1.3, automationScore: 87, leverageScore: 87 },
  research: { manualHours: 10.5, nanusHours: 2.1, automationScore: 85, leverageScore: 89 },
  app: { manualHours: 18, nanusHours: 4.4, automationScore: 79, leverageScore: 84 },
  site: { manualHours: 14, nanusHours: 3.2, automationScore: 82, leverageScore: 86 },
  design: { manualHours: 7, nanusHours: 1.6, automationScore: 86, leverageScore: 88 },
  general: base,
};

function defaultLanes(kind: string, ratio: number): ProductivityPlan["lanes"] {
  const names = kind === "document" ? ["outline", "draft", "review"] : kind === "spreadsheet" ? ["schema", "workbook", "checks"] : kind === "visualization" ? ["question", "chart", "caption"] : ["understand", "execute", "verify"];
  return names.map((name, index) => ({
    id: name,
    title: name,
    owner: index === 0 ? "Planner" : index === 1 ? "Executor" : "Verifier",
    detail: `${name} lane · ${Math.round(ratio * 100)}% progress reflected`,
    minutes: Math.max(5, Math.round([12, 20, 10][index] * Math.max(0.52, 1 - ratio * 0.38))),
  }));
}

export function createProductivityPlan(run: ActiveRun | null, draft: string, context: ProductivityWorkspaceContext): ProductivityPlan {
  const kind = run?.kind ?? "general";
  const profile = profiles[kind] ?? base;
  const title = run?.title || draft.trim() || "New productivity plan";
  const done = run?.steps.filter((step) => step.state === "done").length ?? 0;
  const total = run?.steps.length ?? 3;
  const pending = Math.max(0, total - done);
  const ratio = run ? Math.max(run.progress / 100, done / Math.max(total, 1)) : draft.trim() ? 0.12 : 0;
  const enabled = context.skills.filter((skill) => skill.enabled);
  const review = context.skills.filter((skill) => !skill.enabled)[0];
  const manualHours = Number((profile.manualHours * Math.min(1.18, 1 + (context.agents.length + enabled.length) * 0.015)).toFixed(1));
  const nanusHours = Number(Math.max(0.4, profile.nanusHours * Math.max(0.52, 1 - ratio * 0.38) + pending * 0.08).toFixed(1));
  const lanes = defaultLanes(kind, ratio);
  const skill = enabled[0];
  return {
    title,
    manualHours,
    nanusHours,
    savedHours: Number((manualHours - nanusHours).toFixed(1)),
    automationScore: Math.min(99, Math.round(profile.automationScore + enabled.length * 2 + done * 2)),
    leverageScore: Math.min(99, Math.round(profile.leverageScore + context.agents.length * 2 + context.libraryItems.length - (context.paused ? 4 : 0))),
    lanes,
    reusableSkills: [
      { id: "brief", name: `${title.slice(0, 18)} reusable skill`, command: skill?.command ?? `/skill-create ${kind}`, payoff: "Reuse repeatable structure" },
      { id: "qa", name: "Verification gate", command: "/qa-gate", payoff: "Validate artifact and output" },
      { id: "handoff", name: "Agent handoff", command: "/agent-handoff", payoff: `Synthesize ${context.agents.length} agent states` },
    ],
    riskGates: [
      { id: "data", label: "Data", status: context.mode === "local" ? "ready" : "review", detail: context.mode },
      { id: "cost", label: "Cost", status: review ? "review" : "ready", detail: review ? review.name : "enabled only" },
      { id: "quality", label: "Quality", status: run?.status === "complete" ? "ready" : "review", detail: `${pending} pending steps` },
    ],
    nextActions: ["Save state", `Promote ${skill?.name ?? "new skill"}`, `Run ${lanes.length} lanes`, context.libraryItems[0]?.title ?? "Attach library"],
  };
}
