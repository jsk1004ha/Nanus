import type { LucideIcon } from "lucide-react";

export type ViewId = "home" | "agents" | "skills" | "schedule" | "library";

export type SkillTrustLabel =
  | "nanus_official"
  | "official_manus_reference"
  | "local"
  | "generated"
  | "github";

export type PanelId =
  | "none"
  | "skills"
  | "run"
  | "settings"
  | "project"
  | "agents"
  | "schedule"
  | "library"
  | "connections"
  | "billing"
  | "notifications";

export interface NavItem {
  id: ViewId;
  label: string;
  icon: LucideIcon;
}

export interface TaskItem {
  id: string;
  title: string;
  icon: LucideIcon;
}

export interface SkillPackage {
  id: string;
  command: string;
  name: string;
  description: string;
  source: string;
  trust: SkillTrustLabel;
  worker: string;
  permissionSummary: string;
  icon: LucideIcon;
  tone: "violet" | "blue" | "green";
  enabled: boolean;
}

export interface Recommendation {
  id: string;
  command: string;
  body: string;
  tags: Array<{
    label: string;
    tone: "purple" | "green" | "amber" | "blue" | "red" | "pink";
  }>;
}

export interface QuickAction {
  id: string;
  label: string;
  command: string;
  icon: LucideIcon;
}

export interface RunStep {
  id: string;
  title: string;
  detail: string;
  state: "done" | "active" | "pending";
}

export interface RunLedger {
  title: string;
  status: string;
  worker: string;
  steps: RunStep[];
}

export type RunKind = "deck" | "site" | "app" | "design" | "schedule" | "library" | "agent" | "general";

export interface ActiveRun {
  id: string;
  title: string;
  prompt: string;
  command: string;
  kind: RunKind;
  status: "queued" | "running" | "paused" | "complete";
  worker: string;
  progress: number;
  startedAt: string;
  steps: RunStep[];
  artifacts: Array<{
    id: string;
    title: string;
    type: string;
  }>;
  log: string[];
}
