# Nanus UI Design Brief - Manus-Inspired Agent Workspace

## Brief Playback

Design Nanus as a serious agent workbench: a Manus-inspired app shell for planning, executing, inspecting, and approving autonomous multi-step tasks. It should connect naturally to Claude Code and Codex workers, expose a first-class skill installation and invocation system, and give document, deck, spreadsheet, and visualization creation first-class space inside the product.

The target feel is quiet, fast, dense, and operational. This is not a landing page and not a decorative dashboard.

## Primary Screen

Nanus opens directly into the active workspace.

- Left: workspace navigation, recent tasks, agent groups, pinned artifacts, and project scopes.
- Center: task thread, planner, step-by-step execution state, and the main composer.
- Right: live run inspector with tools, files, browser state, terminal output, citations, and generated artifacts.
- Bottom or collapsible strip: verification, approvals, policy warnings, and run cost/time summaries.

Desktop target at `1440x900`:

- app header: 52px
- left sidebar: 276px, resizable to 220-360px
- center work area: fluid, minimum 520px
- right inspector: 420px, collapsible to icon rail
- gutters: 12px
- panel padding: 12-16px

Mobile target at `390x844`:

- bottom navigation for Chat, Runs, Artifacts, Agents
- center thread as the default view
- inspector and artifact preview open as full-screen sheets
- composer remains sticky at the bottom

## Information Architecture

Top-level sections:

- Home: active task and recent runs
- Agents: Codex, Claude Code, browser, research, document, visualization, and custom workers
- Skills: local skills, project skills, team skills, official catalog imports, GitHub imports, and skill builder
- Artifacts: documents, decks, sheets, charts, diagrams, files, exports
- Runs: run ledger, checkpoints, retries, approvals, traces
- Knowledge: memory, sources, project docs, user rules
- Settings: models, credentials, tools, policies, MCP/A2A connections

## Main Components

### Task Composer

A compact command surface, not a chat toy.

- multiline prompt
- attachments and source picker
- mode selector: `Plan`, `Execute`, `Research`, `Build`, `Artifact`
- model selector with local/cloud labels
- approval policy indicator
- run button with icon and keyboard affordance

### Run Header

Shows the user what is happening without forcing them into logs.

- title and goal
- status: planning, executing, waiting for approval, verifying, complete, failed
- active worker: Codex, Claude Code, browser, research, artifact engine
- elapsed time, token/API cost, workspace branch
- pause, resume, stop, fork, export

### Skill Hub

Skills are reusable task capabilities, not prompt snippets. The UI should make them feel installable, inspectable, and governable.

Primary views:

- Browse: official-style curated skills, local skills, team skills, and recommended skills for the active workspace
- Installed: enabled skills, scope, version, owner, last run, and health
- Builder: create a skill from a prompt, previous run, folder, repo, or uploaded package
- Review: inspect `SKILL.md`, dependencies, tools, permissions, files, examples, and tests before enabling
- Runs: skill invocation history, outputs, failures, and promotion to project/team scope

Supported skill sources:

- Build with Nanus: generate a skill package from a description and verify it before install
- Upload: `.zip`, folder, or single `SKILL.md` package
- GitHub import: repo, folder, branch, or release archive
- Local path import: workspace or user skill directory
- Official catalog adapter: browse/install official or officially mirrored skills only when a public package source or user-provided export exists

Skill cards should show:

- name, category, source, version, trust level
- trigger phrase and slash command
- required tools, MCP servers, browser/filesystem/network needs
- supported workers: Nanus native, Codex, Claude Code, browser, Artifact Studio
- risk level and approval policy
- last verification result

### Slash Command And Skill Invocation

The composer supports `/skill-name` and a skill picker.

- `/deck-from-brief` routes to Artifact Studio presentation generation
- `/research-brief` routes to research plus citation QA
- `/codex-refactor` routes to Codex with workspace policy
- `/claude-review` routes to Claude Code when available
- `/manus:<official-skill>` is shown only for official catalog entries that have a resolvable package source

Invoking a skill expands into a visible execution plan before privileged actions run.

### Planner And Timeline

The center panel shows a compact plan graph and a readable step timeline.

- each step has state, owner, inputs, outputs, and risk flags
- each skill invocation shows its source package, version, permissions, and active worker mapping
- failed steps expose retry and alternate path actions
- approvals appear inline before privileged file, credential, browser, or external send actions

### Right Inspector

Tabs:

- Files
- Browser
- Terminal
- Tools
- Artifacts
- Trace
- QA

The inspector should feel like a professional IDE side panel: dense, stable, and scrollable, with no nested decorative cards.

### Artifact Studio

Document and visualization creation is not hidden behind chat output. It has a dedicated workbench.

Tabs:

- Brief
- Sources
- Outline
- Draft
- Deck
- Sheet
- Visual
- Export
- QA

Expected artifact surfaces:

- document editor and preview
- PPT/deck outline, slide sorter, speaker notes, export status
- spreadsheet grid, formulas, validation, chart bindings
- diagram and chart previews for Mermaid, ECharts, Plotly, Cytoscape, XYFlow, Kepler, and Manim outputs
- source grounding and citation inspector
- before/after diff for rewritten docs
- export matrix for PDF, DOCX, PPTX, XLSX, HTML, Markdown, HWPX where supported

## Visual Language

The visible source hints support an off-white app shell with a restrained blue progress/accent. Nanus should use that restraint, but avoid becoming a one-hue blue-gray interface.

Tokens:

- background: `#F8F8F7`
- surface: `#FFFFFF`
- surface-muted: `#F3F2EF`
- border: `#E4E1DA`
- border-strong: `#C9C4BA`
- text: `#1D1C1A`
- text-muted: `#756F67`
- accent: `#0081F2`
- success: `#16875D`
- warning: `#B76A00`
- danger: `#C23934`
- artifact-purple: `#6E56CF`
- research-green: `#087F5B`

Typography:

- family: Inter, SF Pro, Segoe UI, system sans-serif
- body: 13px / 20px
- compact metadata: 12px / 16px
- section title: 14px / 20px, 600
- page title: 18px / 24px, 650
- avoid negative letter spacing

Shape and elevation:

- default radius: 6px
- prominent surface radius: 8px maximum
- icon buttons: 32-36px square
- subtle 1px borders over heavy shadows
- shadows only for menus, sheets, and popovers

## Interaction Model

Required first-screen interactions:

- switch between Chat, Run Inspector, and Artifact Studio views
- open Skill Hub, install a sample skill, inspect permissions, and invoke it from the composer
- open a run step to inspect inputs, outputs, tool calls, and logs
- approve or reject a privileged action
- preview a generated document/deck/chart without leaving the run
- compare artifact versions
- command palette for tools, agents, and files
- resizable side panels
- loading, empty, error, blocked, waiting-for-user, and completed states

## Skill Quality And Governance

Skills must be safe enough to run inside an autonomous agent platform.

- every installed skill has a manifest, source, checksum, version, and owner
- every skill declares required tools, filesystem/network needs, and worker compatibility
- project/team skills require review before promotion
- official skills are labeled separately from community/local skills
- official Manus skills are not bundled unless their package is publicly available or supplied by the user
- risky skills run with a stricter approval policy by default
- skill tests can run in a disposable workspace before enabling
- skill output becomes normal run artifacts with provenance and redaction status

## Document And Visualization Quality Gates

Artifact Studio should surface quality as part of the UI:

- source coverage and missing-source warnings
- citation grounding
- layout overflow checks
- chart data binding checks
- export validation
- format-specific warnings, such as PPT text overflow or spreadsheet formula errors
- visual QA score against approved reference when a source design exists

## Implementation Direction After Approval

If the repository remains empty, start with a small React/TypeScript app shell and repo-native design tokens rather than introducing a broad design system. Keep the UI useful as the first screen, with realistic mock data for runs, workers, artifacts, and document generation states.

Implementation remains blocked until a rendered Manus source screenshot is captured and approved.
