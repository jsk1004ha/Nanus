# PRD - Nanus Manus-Inspired UI

## Objective

Create a production-grade Nanus app UI that translates the Manus-style autonomous agent workspace into a controllable local/hybrid SuperAgent product connected to Codex, Claude Code, Skill Hub, and Artifact Studio.

## Users

- builders running complex autonomous coding and research tasks
- operators who need auditability, approvals, and cost control
- document-heavy teams creating decks, docs, spreadsheets, and visualizations from sources
- power users and teams who want reusable skills they can install, inspect, customize, and share

## Product Promise

Nanus lets the user see and steer what the agent is doing: plan, execute, inspect, approve, verify, and export outputs without switching between chat, terminal, browser, document editor, and dashboard tools.

## Non-Goals

- clone Manus branding or private assets
- implement Manus backend behavior
- create a marketing landing page
- build multi-page settings or billing flows in the first UI pass
- support authenticated source-state parity until the user provides that state

## Core Experience

1. User opens Nanus and lands in the active workspace.
2. User enters a task in a compact composer.
3. User can invoke a skill through slash command, picker, or recommendation.
4. Nanus resolves the skill package, permissions, worker mapping, and run policy.
5. Nanus creates a plan and assigns workers such as Codex, Claude Code, browser, research, Skill Hub, or Artifact Studio.
6. User watches the plan, timeline, and run inspector update live.
7. Privileged actions pause for approval.
8. Generated artifacts open in the right panel or Artifact Studio.
9. Verification and export status are shown before the run is marked complete.

## First-Screen Layout

- Persistent header with workspace, run status, model, cost/time, and global actions.
- Left workspace sidebar with navigation, recent runs, pinned skills, and project scopes.
- Center task thread plus planner timeline.
- Right inspector with files, browser, terminal, tools, artifacts, trace, and QA tabs.
- Sticky composer anchored to the center panel.

## Skill Hub Requirements

Nanus must support skill installation, inspection, invocation, and governance as a first-class product surface.

Required user flows:

- Browse installed, local, project, team, and official-style catalog skills.
- Create a skill from natural language, a prior run, a local folder, or a GitHub repository.
- Upload a skill package as `SKILL.md`, folder, or archive.
- Import a skill from GitHub by repo, path, branch, tag, or release asset.
- Review skill contents, examples, required tools, permissions, and tests before enabling.
- Invoke skills from the composer with `/skill-name`, from the command palette, or from recommended actions.
- Pin frequently used skills to the left sidebar.
- Promote a user skill to project or team scope after review.
- Disable, rollback, fork, export, or delete installed skills.

## Manus Official Skills Compatibility

Nanus should model Manus's official Skills feature without assuming proprietary access.

Officially supported Manus concepts to mirror:

- file-system skill package centered on `SKILL.md`
- adding skills by building with the agent, uploading a package, browsing an official library, importing from GitHub, and invoking with slash commands
- Project/Team Skill Library style scope controls

Nanus product rules:

- `Official Manus` is a source label, not a bundled asset claim.
- Nanus can browse or install official Manus skills only when there is a public package URL, compatible export, or user-provided package.
- If no public package source exists, the UI shows the official capability as `reference only` and offers a Nanus-native equivalent template.
- Official, community, local, and generated skills must be visually distinct and carry trust labels.
- Skill execution must use the same run ledger, redaction, approval, and sandbox policy as all other worker activity.

## Artifact Studio Requirements

Artifact Studio must feel as important as code execution.

- document preview and outline
- deck preview and slide sorter
- spreadsheet preview and chart bindings
- visualization preview for charts, diagrams, flows, maps, and animations
- export status for PDF, DOCX, PPTX, XLSX, HTML, Markdown, and HWPX when supported
- source grounding and citation panel
- QA panel with overflow, formatting, chart binding, and export validation warnings

## Visual Requirements

- Match the approved Manus source screenshot for density, spacing rhythm, and app-shell restraint.
- Use an off-white product shell, white working surfaces, thin borders, compact typography, and restrained blue accent.
- Avoid decorative gradients, marketing hero sections, large rounded cards, or one-note palettes.
- Use real icon libraries for controls.
- All controls visible on the first screen must be functional in the prototype.
- Skill Hub surfaces should use compact list/detail patterns, not marketplace-style promotional cards.

## Responsive Requirements

- Desktop: `1440x900`
- Mobile: `390x844`
- No overlapping text, clipped labels, or shifting fixed-format controls.
- Mobile uses full-screen sheets for inspector/artifact detail.

## Accessibility Requirements

- keyboard reachable primary controls
- visible focus states
- sufficient contrast for text and semantic states
- clear waiting, blocked, failed, and approval-required states
- no critical state conveyed by color alone
- skill trust, risk, and disabled states are conveyed by text and icon, not color alone

## Acceptance Criteria

- Approved source screenshot/state exists under `.omx/artifacts/visual-ralph/manus-app-ui/`.
- Source viewport, route, and state are documented.
- Implementation screenshot exists for desktop and mobile.
- Product Design QA has source and implementation side by side.
- Visual Ralph verdict score is `>= 90`.
- Build/lint/test or equivalent verification passes.
- UI encodes reusable tokens for color, typography, spacing, radii, and component states.
- First-screen controls are interactive with realistic mock data.
- Skill Hub supports at least one local skill, one generated skill stub, one GitHub import stub, and one official-catalog reference entry in the first prototype.
- Composer supports slash-command skill invocation with a visible pre-run permission review.
- Skill execution appears in the same timeline and inspector as ordinary worker runs.

## Current Blocker

Rendered Manus baseline screenshots are not captured yet. Product Design and Visual Ralph rules require source capture approval before implementation.
