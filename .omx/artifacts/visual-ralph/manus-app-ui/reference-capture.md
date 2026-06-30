# Visual Ralph Reference Capture - Manus App UI

## Source

- Source URL: https://manus.im/app
- User intent: use Manus as the visual reference for a Nanus/SuperAgent UI direction.
- Scope note: this is a product UI reference for layout, density, interaction model, and visual language. It excludes copying private assets, authenticated personal data, backend behavior, branding, or proprietary implementation details.

## Capture Status

- Static HTML snapshot: `.omx/artifacts/visual-ralph/manus-app-ui/manus-app.html`
- Rendered public URL screenshot: `.omx/artifacts/visual-ralph/manus-app-ui/source-desktop-1440x900.png` and `.omx/artifacts/visual-ralph/manus-app-ui/source-mobile-390x844.png`
- Rendered public URL screenshot after wait: `.omx/artifacts/visual-ralph/manus-app-ui/source-desktop-1440x900-wait.png` and `.omx/artifacts/visual-ralph/manus-app-ui/source-mobile-390x844-wait.png`
- User-provided authenticated/dark workspace screenshot: `.omx/artifacts/visual-ralph/manus-app-ui/source-user-manus-dark-2048x1152.png`
- Implementation screenshot: `.omx/artifacts/visual-ralph/manus-app-ui/nanus-desktop-1440x900-v2.png` and `.omx/artifacts/visual-ralph/manus-app-ui/nanus-mobile-390x844-v2.png`

The public URL capture shows a loading/challenge state, so the user-provided dark workspace screenshot is the approved visual direction for the implemented Nanus surface.

## Evidence From Static HTML

- App route: `/app`
- Document language/direction: `en`, `ltr`
- App shell background class: `bg-[var(--background-menu-white)]`
- Theme color: `#f8f8f7`
- Progress/accent token exposed by the app shell: `#0081f2`
- Product metadata:
  - Title: `Manus`
  - Description: `Manus is the action engine that goes beyond answers to execute tasks, automate workflows, and extend your human reach.`
- Runtime shape: Next.js client app with websocket/API environment variables and CDN-hosted static assets.

## Approved Visual Direction From User Screenshot

- Dark workspace shell with a nearly black main canvas and a slightly lighter left sidebar.
- Large empty central working area with the primary prompt/composer centered horizontally.
- Sidebar navigation: new task, agents, skills/plugins, scheduled work, library, projects, recent tasks, account controls.
- Central prompt: large headline, wide rounded composer, compact icon controls, and a suggestion tray attached under the composer.
- Secondary chips for common work types such as slides, website, desktop app, design, and more.
- Lower carousel card for reusable skills.
- Compact credit/status badge in the top-right corner.
- Product-specific translation for Nanus: Skill Hub, Codex/Claude workers, official Manus-compatible skill entries, and Artifact Studio.

## Required Baseline Captures

Capture these states before implementation starts:

- Desktop: `1440x900`, `https://manus.im/app`, logged-out/default app state unless the user provides an authenticated state.
- Mobile: `390x844`, same route/state.
- Optional focused captures after desktop/mobile:
  - left navigation and project/task history
  - task composer
  - active run or empty state
  - artifact/document preview area, if visible in the source state

Capture command used for public URL:

```powershell
npx playwright screenshot --viewport-size=1440,900 https://manus.im/app .omx/artifacts/visual-ralph/manus-app-ui/source-desktop-1440x900.png
npx playwright screenshot --viewport-size=390,844 https://manus.im/app .omx/artifacts/visual-ralph/manus-app-ui/source-mobile-390x844.png
```

## Interaction Parity Notes

Visible controls in the approved source state should map to Nanus equivalents:

- navigation rail or sidebar -> workspace, runs, agents, artifacts, settings
- primary composer -> task prompt with attachments, mode, model, approval policy
- active run surface -> plan, tool timeline, checkpoints, logs, artifacts
- artifact preview -> document, deck, spreadsheet, chart, and diagram previews
- account/login/paywall surfaces -> excluded unless explicitly requested

## Known Exclusions

- no authenticated user data
- no exact backend/API behavior
- no Manus brand replication
- no multi-page crawling
- no third-party widget parity
- no asset approximation by placeholder shapes or handcrafted inline SVG

## Approval Gate

The user-provided dark workspace screenshot is approved as the visual source of truth for this pass. Public URL screenshots are retained as capture evidence but not used as the primary visual target because they do not expose the authenticated workspace state.
