---
name: oci-architecture-diagram
description: Orchestrate the full OCI Architecture Diagram plugin workflow by combining the local skills for prompt normalization, architecture validation, icon catalog maintenance, HTML rendering, and visual QA.
---

# OCI Architecture Diagram

Use this as the entrypoint when the user asks to draw, generate, repair, or
review an Oracle Cloud Infrastructure architecture diagram. The renderer still
produces a static, self-contained HTML file with embedded SVG, but the final
user-facing delivery must be the local HTTP gallery opened in the Codex Browser.

## Route to Specialist Skills

- Use `oci-spec-normalizer` to convert Spanish/English natural language into
  the normalized JSON schema.
- Use `oci-architecture-validator` before rendering when the prompt is complex,
  ambiguous, production-oriented, or security-sensitive.
- Use `oci-icon-catalog` when icons are missing, ugly, generic, or when the user
  provides an OCI icon folder.
- Use `oci-diagram-renderer` to run the CLI renderer or regenerate examples.
- Use `oci-diagram-visual-qa` after frontend/layout changes or when the user
  reports overlaps, bad arrows, bad spacing, unreadable text, or broken icons.
- Use oci-architecture-case-deck when the case also needs a 16:9 Case,
  Architecture and BoM deck with the exact Oracle Cost Estimator JSON.

## Default Workflow

1. Normalize the prompt to JSON with stable ids, groups, nodes, and edges.
2. Validate architecture coherence and schema correctness.
3. Ensure the icon catalog has usable SVGs for all important services.
4. Render the HTML with `scripts/generate_oci_diagram.py`.
5. Add or update the diagram entry in `src/architectures.js` when the user
   should navigate to it from the local gallery.
6. Serve the plugin root with `scripts/serve_architecture_site.py` and open the
   gallery through the Browser plugin at a local HTTP URL such as
   `http://127.0.0.1:8765/src/index.html?project=<project-id>`.
7. Iterate until icons, labels, arrows, groups, and navigation look solid.
8. Return the generated HTML path, local gallery URL, warnings, and verification
   performed.

For a case deck, retain the normalized architecture JSON and the delivered
Oracle Cost Estimator JSON as separate artifacts. Render the companion deck
manifest only with --deck and --bom; do not synthesize or overwrite either
source JSON.

Use the Browser plugin for local visual QA. Do not import the standalone
Playwright package or open `file://` pages unless the user explicitly requests
that fallback.

## Cost Estimator Browser Validation

When the case includes an Oracle Cost Estimator BoM, invoke
`oci-cost-estimator-browser-export`; do not replace it with an API call or a
locally generated JSON/spreadsheet.

1. Open a clean `https://www.oracle.com/cloud/costestimator.html` tab.
2. Select **Main actions > Import** and upload the exact delivered JSON through
   the Browser file chooser.
3. Select **Import** only after Cost Estimator enables it.
4. Treat the BoM as `browser_validated` only when the import dialog closes,
   the expected configurations are rendered, and **Main actions > Export** is
   enabled. Record the validation timestamp and Cost Estimator build shown by
   the page when available.
   If Cost Estimator recalculates a different monthly total, retain the
   `browser_validated` import result but keep price freshness as `unverified`;
   report the difference and regenerate the delivered BoM only from an official
   Cost Estimator export.
5. When the user requests the official spreadsheet, select **Export** in the
   same validated session and retain the downloaded Oracle-generated file next
   to the unchanged JSON. Never call a plugin-generated `.xlsx` the official
   Cost Estimator export.

Browser automation is a Codex plugin workflow, not a capability of the static
portable HTML deck. The deck may link to Cost Estimator, but it must not claim
that its link independently imports, validates, or exports a file.

## Final Delivery Contract

- Always serve the plugin root over localhost before final delivery. Prefer
  `127.0.0.1:8765`; choose another free port only when that port is occupied by
  an unrelated process.
- Always open the navigable gallery URL with the Codex Browser plugin before
  final response: `http://127.0.0.1:8765/src/index.html?project=<project-id>`.
- The final response must lead with the Browser-opened localhost URL. Include
  the HTML/JSON file paths and renderer warnings after that link.
- If Browser cannot be used, state that explicitly and still provide the local
  HTTP URL that should be opened once Browser is available. Do not present a
  `file://` URL as the primary delivery.

## Commands

```powershell
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --out examples/web-architecture.html
python scripts/serve_architecture_site.py --port 8765 --project web-architecture
```
