# Test Spec: Nanus Artifact Studio

Created: 2026-06-30T00:51:00Z
Status: Extension test plan ready for execution handoff

## Success Definition

Artifact Studio is successful when Nanus can accept a document/deck/spreadsheet/visualization task, create a validated ArtifactPlan, route it to the correct engine adapter, emit canonical worker events, produce an ArtifactManifest, and block publishing until QA requirements pass or an explicit operator override is recorded.

## Unit Tests

### Artifact IR

- `ArtifactPlan` validates for document, presentation, spreadsheet, dashboard, diagram, map, animation, and mixed requests.
- Invalid render target format is rejected.
- Blocks with source references must point to known `SourceRef` IDs.
- Persisted JSON uses `snake_case`.
- TypeScript helpers cannot leak camelCase into persisted fixtures.

### Engine Registry

- MIT/Apache/BSD engines can be marked `core_candidate`.
- AGPL/GPL/NOASSERTION engines default to `service_adapter`, `optional_connector`, or `license_review_required`.
- Engine health can return `available`, `missing_binary`, `missing_service`, `license_blocked`, `unsupported_platform`, or `not_configured`.
- Routing fails closed when required engine is license-blocked.

### Document Workers

- Docling ingestion adapter creates structured source blocks from fixture metadata.
- Markdown/HTML draft worker produces manifest entries and QA requests.
- HWPX route reports health for python-hwpx.
- HWP legacy route reports conversion health for unhwp/hwplib sidecars.

### Presentation Workers

- Template-following deck routes to ppt-master.
- API-first deck generation routes to Presenton.
- PPTX output requires render QA before publish.
- Speaker notes/narration requests are represented in the deck plan, even when not implemented in MVP.

### Visualization Workers

- Mermaid worker rejects invalid diagram syntax and reports QA issue.
- ECharts worker requires a valid option object and a data binding.
- Plotly worker requires data/layout separation.
- Cytoscape worker requires node/edge elements.
- Kepler worker requires geospatial fields or a declared geo transform.
- Manim worker requires a scene source and video render target.

### Spreadsheet Workers

- XLSX route chooses exceljs for TypeScript-first generation.
- openpyxl route is selected for Python sidecar formula-preserving edits.
- XlsxWriter route is selected for deterministic generated reports.
- pyexcel route is selected for multi-format tabular conversion.

## Integration Tests

- Create a mixed artifact bundle with a Markdown report, Mermaid architecture diagram, ECharts chart, and XLSX workbook manifest.
- Ingest a document fixture through Docling and produce normalized blocks.
- Generate a Mermaid SVG/PNG/HTML preview target.
- Generate an ECharts HTML preview target from tabular data.
- Generate an XLSX fixture and inspect workbook metadata.
- Simulate Presenton unavailable and verify fallback/capability reporting.
- Simulate ppt-master sidecar unavailable and verify health status.
- Validate license policy blocks AGPL/GPL embedding by default.

## E2E Tests

1. Executive report bundle
   - Input: topic brief + CSV.
   - Output: Markdown/HTML report, ECharts chart, XLSX workbook manifest.
   - Expected: all artifacts have source refs, QA reports, and license notes.

2. Architecture deck request
   - Input: architecture outline and visual style.
   - Output: deck plan routed to Presenton or ppt-master.
   - Expected: deck publish is blocked until PPTX render QA completes.

3. Korean document workflow
   - Input: HWPX/HWP fixture.
   - Output: Markdown/JSON normalized extraction and HWPX capability result.
   - Expected: unsupported binary HWP edit path is reported clearly rather than silently failing.

4. Dashboard visualization
   - Input: tabular dataset and user question.
   - Output: ECharts/Plotly spec plus preview target.
   - Expected: chart data binding is auditable and chart is not blank.

5. License boundary
   - Input: request requiring ChartDB or ONLYOFFICE.
   - Output: service adapter requirement or license review block.
   - Expected: no AGPL component is embedded into core by default.

## QA Requirements

- Documents: structural checks, style checks, render preview when available, source/provenance checks, redaction checks.
- Presentations: slide render inspection, no overlap/clipping, template compliance, source/provenance checks.
- Spreadsheets: formula scan, typed values, chart/render preview, no broken refs.
- Visualizations: nonblank render, valid schema, data binding, label legibility.
- Animations: render success, duration, frame/video artifact, no missing assets.
- HWP/HWPX: validate conversion/extraction path and report unsupported edit modes explicitly.

## Acceptance Criteria Matrix

| Requirement | Evidence |
| --- | --- |
| IR-first artifact lifecycle | ArtifactPlan and ArtifactManifest schema tests pass. |
| Engine routing | Engine registry and routing tests pass. |
| License safety | AGPL/GPL/NOASSERTION block/service tests pass. |
| Document route | Docling/HWPX/Markdown health and fixture tests pass. |
| Presentation route | Presenton/ppt-master routing tests pass. |
| Visualization route | Mermaid/ECharts/Plotly/Cytoscape/Kepler/Manim spec tests pass. |
| Spreadsheet route | exceljs/openpyxl/XlsxWriter/pyexcel routing tests pass. |
| QA gate | Publish is blocked without QA pass or explicit override event. |
| Ledger integration | Artifact events use canonical `snake_case` envelope and manifest provenance. |

## Manual Verification Checklist

- Confirm selected engines and licenses in registry.
- Generate one mixed artifact bundle.
- Open preview artifacts and confirm they are nonblank and legible.
- Inspect event ledger for artifact plan/render/QA/export events.
- Confirm redaction and provenance are present in manifests.
- Confirm publish action is blocked before QA completion.

## Non-goals for First Artifact Studio MVP

- Full collaborative ONLYOFFICE editing.
- Full Metabase embedding.
- Full ChartDB embedding.
- Full HWP binary editing.
- Full video rendering pipeline for Manim.
- One-click production deployment of every listed external repo.
