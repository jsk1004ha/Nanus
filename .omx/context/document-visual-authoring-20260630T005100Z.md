# Context Snapshot: Document and Visualization Authoring Extension

Created: 2026-06-30T00:51:00Z
Workspace: `C:\Users\js100\Desktop\coding\Nanus`

## Task Statement

Extend Nanus with a powerful document, presentation, spreadsheet, and visualization authoring capability. The user wants the system to use strong open-source projects for PPT generation, document writing/editing, visualization, Korean HWP/HWPX handling, Excel generation, and AI-assisted writing workflows.

## Desired Outcome

Design the best architecture for artifact production and integrate it into the existing Nanus SuperAgent plan:

- PPT/PPTX generation and editing.
- DOCX/HTML/PDF/HWPX/HWP document authoring and conversion.
- Spreadsheet/XLSX generation and analysis.
- Data visualization, diagrams, dashboards, charts, graph/network views, maps, database diagrams, and animations.
- AI writing, editing, documentation templates, and collaborative editing integration.
- Strong verification loop: render, inspect, lint, validate, export.

## Current Nanus Baseline

The existing ralplan-approved architecture is:

- TypeScript-first control plane.
- Worker Adapter Gateway.
- Codex and Claude Code as controlled workers.
- Canonical persisted/streamed events in `snake_case`.
- `RunPolicy`, redaction, isolated workspaces, and file-backed dev ledger in MVP.
- LangGraph constrained to control-flow; run ledger is audit truth.

The document/visualization feature should plug into the Worker Adapter Gateway as a new capability family, not become a separate control plane.

## Repository Evidence

Metadata was collected from official GitHub/PyPI sources on 2026-06-30.

### Presentation

- `hugohe3/ppt-master`: MIT, Python, AI-generated editable PowerPoint with native shapes/animations and template following.
- `presenton/presenton`: Apache-2.0, TypeScript, open-source AI presentation generator and API.

### Documentation and Document Processing

- `matheusfelipeog/beautiful-docs`: MIT, documentation examples/curation.
- `race2infinity/The-Documentation-Compendium`: templates and documentation writing guidance; no GitHub license metadata detected.
- `langgenius/dify`: production-ready platform for agentic workflow development; license metadata returned `NOASSERTION`, so treat as integration/reference rather than embedded code until license review.
- `theJayTea/WritingTools`: GPL-3.0, system-wide grammar assistant; use as UX inspiration or separate optional connector, not embedded core.
- `ONLYOFFICE/documentserver`: AGPL-3.0, collaborative online office suite; use as separate service adapter, not embedded library.
- `docling-project/docling`: MIT, document parsing/preparation for GenAI.
- `airmang/python-hwpx`: Apache-2.0, pure Python HWPX automation.
- `neolord0/hwplib`: Apache-2.0, Java HWP library.
- `iyulab/unhwp`: MIT, Rust HWP/HWPX conversion to Markdown, plain text, JSON with bindings.

### Visualization

- `microsoft/data-formulator`: MIT, interactive AI-powered data analysis and visualization.
- `microsoft/lida`: MIT, automatic generation of visualizations and infographics using LLMs.
- `Kanaries/pygwalker`: Apache-2.0, dataframe-to-interactive visual analysis UI.
- `apache/echarts`: Apache-2.0, browser charting/visualization library.
- `plotly/plotly.js`: MIT, JavaScript charting library.
- `metabase/metabase`: license metadata returned `NOASSERTION`; use as external BI connector/service after license review.
- `mermaid-js/mermaid`: MIT, text-to-diagram rendering.
- `xyflow/xyflow`: MIT, React/Svelte node-based UI.
- `cytoscape/cytoscape.js`: MIT, graph/network visualization and analysis.
- `chartdb/chartdb`: AGPL-3.0, database diagram editor; use as service inspiration/connector, not embedded library without AGPL decision.
- `keplergl/kepler.gl`: MIT, geospatial analysis tool.
- `ManimCommunity/manim`: MIT, mathematical animations.

### Excel and Tabular Artifacts

- `jmcnamara/XlsxWriter`: BSD-2-Clause, Python XLSX writer.
- `openpyxl`: PyPI package for reading/writing Excel `.xlsx`/`.xlsm` files.
- `pyexcel/pyexcel`: BSD-3-Clause, unified API for CSV/ODS/XLS/XLSX/XLSM.
- `exceljs/exceljs`: MIT, JavaScript Excel workbook manager.

## Constraints

- AGPL/GPL projects must not be embedded into Nanus core without an explicit licensing decision.
- Document generation must be deterministic enough to test visually.
- All artifact workers must use the existing `RunPolicy`, event envelope, redaction, ledger, and sandbox model.
- Generated artifacts need provenance, source notes, and render verification evidence.
- Korean HWP/HWPX support matters enough to be a first-class import/export path, but HWP binary editing can be staged after HWPX/Markdown/JSON conversion.

## Likely Codebase Touchpoints

- `packages/artifact-core`: Artifact IR, style system, render target contracts, provenance, QA result schema.
- `packages/artifact-workers-presentation`: Presenton/ppt-master adapters and PPTX export.
- `packages/artifact-workers-document`: DOCX/HWPX/HWP/PDF/Markdown/HTML adapters.
- `packages/artifact-workers-visualization`: ECharts/Plotly/Mermaid/XYFlow/Cytoscape/Kepler/Manim adapters.
- `packages/artifact-workers-spreadsheet`: XLSX/CSV adapters.
- `apps/api`: artifact authoring endpoints and event streams.
- `apps/web`: Artifact Studio UI.
- `docs/architecture`: architecture diagrams, ADRs, format support matrix, licensing notes.
