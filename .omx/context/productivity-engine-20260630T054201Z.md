# Productivity Engine Context Snapshot

task statement: Think through how Nanus can become more powerful and more productive than Manus, then execute a concrete improvement using Ralph and Ultragoal.

desired outcome: Add a usable UI capability that turns a Nanus task/run into measurable productivity advantages: saved time, parallel lanes, reusable skill candidates, risk gates, and next actions. Preserve the current Manus-inspired commercial UI, existing smoke flows, and the frontend performance budget.

known facts/evidence:
- Current app is a Vite/React/TypeScript workspace UI.
- Existing UI already has prompt-derived run state, Skill Hub, settings, project creation, command palette, and mobile layout fixes.
- Previous performance work split panel code into a lazy chunk and added `npm run perf:budget`.
- Baseline bundle evidence from performance goal: initial JS reduced from `203750` to `188462` bytes, CSS `27459` bytes.
- The repo currently has uncommitted performance optimization changes.
- `omx ultragoal` and `omx performance-goal` are not available in this installed OMX CLI, so durable workflow state must be file-backed.

constraints:
- No new dependencies.
- Do not revert existing uncommitted performance work.
- Keep edits scoped and compatible with current tests.
- Maintain initial JS budget <= `190000` bytes and CSS <= `35000` bytes.
- Ralph requires fresh verification and architect-style sign-off before final completion.

unknowns/open questions:
- Real backend execution adapters for Claude/Codex/Manus are not implemented yet.
- Exact Manus proprietary skill semantics are not available; UI should avoid claiming actual official execution.

likely codebase touchpoints:
- `src/types.ts`
- `src/App.tsx`
- `src/Panels.tsx`
- a new productivity model module imported by the lazy panel chunk
- `.omx/artifacts/visual-ralph/manus-app-ui/react-smoke.spec.ts`
- `.omx/ultragoal/*`
- `.omx/state/productivity-engine/*`
