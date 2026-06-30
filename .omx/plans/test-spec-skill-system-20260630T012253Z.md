# Test Spec - Nanus Skill Hub and Manus-Compatible Official Skills

## Objective

Verify that Nanus can install, review, invoke, and audit skills while preserving sandbox, permission, and source-trust boundaries.

## Unit Tests

- Parse a minimal `SKILL.md` package.
- Parse a package with optional `manifest.json`, examples, tests, scripts, and assets.
- Reject packages missing `SKILL.md`.
- Compute and persist package checksum.
- Normalize source refs for upload, local path, GitHub, generated, and official catalog entries.
- Resolve slash commands to an enabled package version.
- Reject slash commands for disabled or reference-only skills.
- Map skill-declared permissions into a concrete `RunPolicy`.
- Serialize skill events using the canonical `snake_case` worker event envelope.

## Integration Tests

- Install a local skill from a folder, review it, enable it, invoke it, and disable it.
- Generate a draft skill from a prior run; verify it remains disabled until review passes.
- Import a GitHub skill fixture by repo/path/branch and store source ref plus checksum.
- Upload a zip fixture and verify package contents are extracted only inside the intended skill store.
- Promote a user skill to project scope with review metadata.
- Promote a project skill to team scope with owner metadata.
- Invoke a skill that dispatches to Codex and verify the run ledger includes skill package metadata.
- Invoke a skill that dispatches to Artifact Studio and verify generated artifacts keep source provenance.

## Official Manus Compatibility Tests

- Catalog entry with public package URL can be imported only after review.
- Catalog entry without package source is displayed as `reference_only`.
- Reference-only official entry cannot be enabled or invoked.
- `/manus:<name>` resolves only when the official-compatible skill is installed and enabled.
- Official, community, local, generated, project, and team skills have distinct trust labels.
- The UI must not imply that Nanus bundles proprietary Manus official skills unless the package is actually present and licensed.

## Security Tests

- Imported skill cannot request broader filesystem access than its reviewed policy.
- Skill with network `open` requires explicit approval.
- Skill with terminal access runs in a disposable or scoped workspace according to policy.
- Skill logs are redacted before persistence and streaming.
- Skill package extraction blocks path traversal.
- Skill review flags suspicious scripts, binary payloads, and undeclared tools.

## UI Tests

- Skill Hub browse view shows installed, local, project, team, generated, GitHub, and official reference entries.
- Skill review panel shows `SKILL.md`, source, checksum, permissions, worker compatibility, tests, and examples.
- Composer shows slash command suggestions and inserts selected skill.
- Pre-run permission review appears before privileged skill invocation.
- Run timeline shows skill resolution, review, dispatch, verification, and completion.
- Right inspector shows skill package metadata and artifacts.
- Mobile view exposes Skill Hub via bottom navigation or full-screen sheet without text overlap.

## Acceptance Criteria

- At least one local fixture skill completes successfully.
- Generated, GitHub, upload, and official catalog paths are represented in UI and registry state.
- Reference-only official Manus entries cannot execute.
- Every skill run appears in the run ledger with source, version, checksum, permissions, worker mapping, artifacts, and verification result.
- All tests that cover package parsing, path traversal, permission mapping, slash resolution, and ledger serialization pass.
