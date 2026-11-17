# Local Codex Policy for codex-plugin-oci-architecture

This file supplements the global `~/.codex/AGENTS.md`.

Keep this file repo-specific. Do not duplicate universal rules that already live in the global policy.

## Project Identity

- Repo root: `D:\dev\codex-plugin-oci-architecture`
- Purpose: Build and publish the portable `oci-architecture-diagram` Codex plugin.
- Technical audience: OCI solution architects and plugin maintainers.
- Primary surfaces: plugin skills, JSON/SVG renderer, local project portfolio, Cost Estimator export workflow, icon catalog, and release package.

## Repo Operating Defaults

- Preferred validation commands: bundled-Python `unittest discover` for `plugins/oci-architecture-diagram/tests` and `node --test --test-isolation=none plugins/oci-architecture-diagram/scripts/case-memory.test.mjs`.
- Preferred search and inspection tools: `rg`, exact JSON/XML parsing, and DOM/browser state; do not use screenshots as verification.
- Default runtime or environment assumptions: Windows PowerShell and the Codex bundled Python runtime.

## Local Validation Policy

- Required checks beyond global Graphify and Sentrux: strict XML parsing for imported SVGs, full plugin unit tests, Node case-memory test, and `git diff --check`.
- Safe shortcuts for docs-only work: run `git diff --check`; skip runtime tests only when no executable contract or skill behavior changes.
- Release, deploy, or approval gates: version the plugin manifest, use the tag alone as the GitHub release title, and publish only after tests pass.

## Repo-Specific Friction

- Sensitive paths or fragile areas: `src/projects.json`, portable project images, browser-validated Cost Estimator JSON/XLS pairs, SVG namespace sanitization, and generated HTML/PPTX rasterization.
- Credentials, external systems, or approval boundaries: Oracle Cost Estimator browser validation and GitHub pushes/releases require authenticated external access.
- Noisy, slow, or expensive commands to avoid by default: regenerating large static suites; the active portfolio source of truth is `src/projects.json`.

## Continuous Improvement Triggers

- Promote a repeated friction to this local file after 2 recurrences in the same repo.
- Promote a repeated manual sequence to a script or skill after 3 recurrences or when it is safety-critical.
- Promote a rule to the global policy only when it is cross-repo or clearly universal.
- Review `.codex/improvement-log.md` before large tasks and record only meaningful signal after non-trivial work.

## Future Delegation Hooks

- Candidate explorer roles:
- Candidate reviewer roles:
- Candidate repo-specific skills or MCPs:
