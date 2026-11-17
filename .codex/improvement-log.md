# Improvement Log - codex-plugin-oci-architecture

Use this file for evidence-backed harness improvements in this repo.

Keep entries short. Record real friction, recurring overhead, or meaningful improvements only.

## Promotion Thresholds

- 2 recurrences in this repo -> local `.codex/AGENTS.md` candidate
- 3 recurrences or safety-critical repetition -> script or skill candidate
- Cross-repo or clearly universal pattern -> global `~/.codex/AGENTS.md` candidate

## Entry Template

| Date | Task or Incident | Friction Observed | Evidence | Action Taken or Proposed | Promotion Target | Status |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD |  |  |  |  | local AGENTS / script / skill / global AGENTS / none | captured |
| 2026-08-14 | OCI icon catalog import | Oracle SVGs exported by Visio retained `v:*` elements and attributes after namespace declarations were removed, producing invalid portable assets. | All three supplied icons contained Visio extensions and failed strict XML parsing after the old sanitizer ran. | Strip Visio elements and attributes in the shared SVG sanitizer and cover the behavior with a strict XML test. | icon import script | addressed |
| 2026-08-14 | Portfolio workflow cleanup | The historical 100-case generated suite duplicated the current JSON project portfolio and kept obsolete scripts, tests, and documentation alive. | Runtime discovery showed the active gallery reads `src/projects.json`; the generated suite was referenced only by its own build chain and legacy checks. | Remove the generated suite and its builders; keep reference examples for renderer tests and use `project` as the canonical URL parameter. | plugin skills and tests | addressed |
| 2026-08-13 | Use Case image uploads | Browser-local image storage can fail or be cleared, so a loaded image disappeared after changing tabs or refreshing. | The page displayed the image but showed a local-save failure. | Store accepted PNG/JPEG/WebP files under `assets/project-images/<project-id>/`, save a project-relative URL atomically in `projects.json`, include it in duplicate/export flows, and migrate an existing local image when possible. | plugin server and renderer | addressed |
| 2026-08-12 | Portfolio project URLs | Slug-based project IDs caused mutable, non-standard `diagram` URLs and made renamed cases hard to identify consistently. | User requested a `yyyy-mm-dd-hh-mm-ss-ms` URL for every case. | Generate collision-safe timestamp IDs for new duplications and document the contract in the case-deck skill. | plugin UI and skill | addressed |
| 2026-08-12 | Project duplication | Materializing a new version from the highest project in a family could copy a sibling instead of the selected project. | A renamed duplicated case was overwritten when a later case used the same identifier/family. | Persist `sourceProjectId` on duplication and have the local server materialize that exact source; fail on an unknown source. | plugin server | addressed |
| 2026-08-12 | v0.4.0 release preparation | Generated HTML retained trailing whitespace from embedded OCI SVG markup. | `git diff --cached --check` failed on the portable case-deck example. | Normalize every generated HTML line before writing the output. | script | addressed |
| 2026-08-12 | PPTX export | Browser image clipboard writes were denied from the embedded deck and one SVG decode interrupted the fallback export. | Reproduced in a separate browser; the PPTX flow initially reported `EncodingError` for an SVG asset. | Replace clipboard capture with a three-slide PPTX download and ignore only SVG assets the canvas cannot decode. | plugin skill | addressed |
| 2026-08-12 | PPTX architecture slide | Computed SVG styles detached marker definitions from their canvas context and the floating Oracle badge was painted before the slide. | Exported architecture showed black connection bands and the badge behind the diagram. | Preserve native SVG styles in the serialized asset and draw the badge as the final canvas layer. | plugin renderer | addressed |
| 2026-08-12 | PPTX architecture slide | Applying computed `marker-end` styling while rasterizing the in-page SVG produced oversized black arrowheads in the exported PNG. | The downloaded PowerPoint showed black curves; PNG pixel validation after removing that override found 122 black pixels across 2,073,600 pixels. | Preserve the SVG's own marker attributes and rasterize the complete 1920×1080 deck to PNG before packaging it into the PPTX. | plugin renderer | addressed |
