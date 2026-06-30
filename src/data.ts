import {
  Activity,
  BadgeCheck,
  Blocks,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Clock3,
  CodeXml,
  FileText,
  FolderOpen,
  Library,
  Laptop,
  MessageSquare,
  Presentation,
  ScanFace,
  SquarePen,
  SquareTerminal,
  WandSparkles,
} from "lucide-react";
import type { NavItem, QuickAction, Recommendation, RunLedger, SkillPackage, TaskItem } from "./types";

export const navItems: NavItem[] = [
  { id: "home", label: "새 작업", icon: SquarePen },
  { id: "agents", label: "에이전트", icon: ScanFace },
  { id: "workbench", label: "워크벤치", icon: Activity },
  { id: "skills", label: "스킬", icon: Blocks },
  { id: "schedule", label: "예약됨", icon: Clock3 },
  { id: "library", label: "라이브러리", icon: Library },
];

export const mobileTabs = [
  { id: "home", label: "Chat", icon: MessageSquare },
  { id: "run", label: "Runs", icon: Activity },
  { id: "workbench", label: "Work", icon: Activity },
  { id: "skills", label: "Skills", icon: Blocks },
  { id: "productivity", label: "Engine", icon: Activity },
  { id: "files", label: "Files", icon: FolderOpen },
] as const;

export const tasks: TaskItem[] = [
  { id: "deck", title: "12장짜리 PPT 제작", icon: Presentation },
  { id: "plan", title: "학습지원 분석 계획서 생성", icon: FileText },
  { id: "report", title: "시각지대 분석 보고서", icon: ChartNoAxesCombined },
];

export const skills: SkillPackage[] = [
  {
    id: "deck-from-brief",
    command: "/deck-from-brief",
    name: "Deck from Brief",
    description: "문서/자료를 발표자료로 변환",
    source: "Nanus official · Artifact Studio · 검증됨",
    trust: "nanus_official",
    worker: "Artifact Studio",
    permissionSummary: "파일 읽기, Artifact Studio, 네트워크 allowlist",
    icon: Presentation,
    tone: "violet",
    enabled: true,
  },
  {
    id: "manus-research",
    command: "/manus:research",
    name: "Manus Research Skill",
    description: "공식 Manus 호환 항목",
    source: "reference only · 패키지 필요",
    trust: "official_manus_reference",
    worker: "Research adapter",
    permissionSummary: "공개 패키지 또는 사용자 제공 export 필요",
    icon: BadgeCheck,
    tone: "blue",
    enabled: false,
  },
  {
    id: "codex-refactor",
    command: "/codex-refactor",
    name: "Codex Refactor Lane",
    description: "작업공간 쓰기 전 승인 필요",
    source: "local · Codex · sandboxed",
    trust: "local",
    worker: "Codex",
    permissionSummary: "workspace-write 전 승인, isolated worktree",
    icon: SquareTerminal,
    tone: "green",
    enabled: true,
  },
];

export const recommendations: Recommendation[] = [
  {
    id: "education-deck",
    command: "/deck-from-brief 교육지원 사업 데이터를 분석해 12장짜리 발표자료를 만들어줘",
    body: "교육지원 사업 데이터를 분석하고 12장짜리 발표자료를 제작하세요.",
    tags: [
      { label: "PPT", tone: "purple" },
      { label: "RAG", tone: "green" },
      { label: "QA", tone: "amber" },
    ],
  },
  {
    id: "official-skills",
    command: "/research-brief Manus 공식 Skills 기능을 조사하고 Nanus 스킬 설계와 비교해줘",
    body: "공식 스킬 기능을 조사하고 실행 가능한 설계로 정리하세요.",
    tags: [
      { label: "Web", tone: "blue" },
      { label: "Cite", tone: "green" },
      { label: "Risk", tone: "red" },
    ],
  },
  {
    id: "hwpx-export",
    command: "/artifact-studio HWPX 계획서를 PPT와 웹 요약본으로 변환해줘",
    body: "HWPX 계획서를 발표자료와 웹 요약본으로 변환하세요.",
    tags: [
      { label: "HWPX", tone: "pink" },
      { label: "Deck", tone: "purple" },
      { label: "Web", tone: "blue" },
    ],
  },
];

export const quickActions: QuickAction[] = [
  { id: "slides", label: "슬라이드 제작", command: "/deck-from-brief 새 프로젝트 계획서로 슬라이드 제작", icon: BriefcaseBusiness },
  { id: "site", label: "웹사이트 구축", command: "/site-builder 보고서 기반 웹사이트 구축", icon: CodeXml },
  { id: "desktop", label: "데스크톱 앱 개발", command: "/codex-build 데스크톱 앱 개발", icon: Laptop },
  { id: "design", label: "디자인", command: "/design-system 디자인 시스템 정리", icon: WandSparkles },
  { id: "research", label: "조사", command: "/research-brief 근거", icon: ChartNoAxesCombined },
];

export const runLedger: RunLedger = {
  title: "12장짜리 PPT 제작",
  status: "계획 수립 중",
  worker: "Codex + Artifact Studio",
  steps: [
    { id: "resolve", title: "스킬 해석", detail: "/deck-from-brief · v0.3.2", state: "done" },
    { id: "structure", title: "자료 구조화", detail: "Docling · citation QA", state: "active" },
    { id: "render", title: "슬라이드 렌더링", detail: "Presenton · PPTX export", state: "pending" },
  ],
};

export const agents = [
  {
    id: "planner",
    name: "Planner",
    status: "대기",
    description: "작업을 단계와 권한 경계로 분해합니다.",
  },
  {
    id: "artifact",
    name: "Artifact Studio",
    status: "준비됨",
    description: "문서, PPT, 웹 요약본을 생성합니다.",
  },
  {
    id: "codex",
    name: "Codex Lane",
    status: "격리됨",
    description: "워크스페이스 파일 수정과 테스트를 실행합니다.",
  },
];

export const scheduledRuns = [
  {
    id: "weekly-report",
    title: "주간 리서치 브리프",
    cadence: "매주 월요일 09:00",
    target: "Library / Reports",
  },
  {
    id: "deck-check",
    title: "PPT 품질 검사",
    cadence: "문서 업로드 후",
    target: "Artifact Studio",
  },
];

export const libraryItems = [
  {
    id: "official-skill-note",
    title: "Manus 공식 Skills 조사 노트",
    meta: "Web citations · Skill Hub",
  },
  {
    id: "doc-visual-stack",
    title: "문서 시각화 엔진 설계",
    meta: "PPT · HWPX · ECharts · Mermaid",
  },
  {
    id: "ppt-template",
    title: "12장 발표자료 템플릿",
    meta: "Presenton · ppt-master",
  },
];
