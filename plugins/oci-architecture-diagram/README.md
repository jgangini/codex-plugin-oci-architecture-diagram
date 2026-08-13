# OCI Architecture Diagram Plugin

Repo-local Codex plugin for generating static Oracle Cloud Infrastructure
architecture diagrams as portable HTML/SVG.

## Quick Start

From `plugins/oci-architecture-diagram`:

```powershell
python scripts/extract_oci_icons.py --source ../../oci --out assets/oci-icons
python scripts/import_oci_svg_icons.py --source "D:\Desktop\Oracle\4.tools\_OCI icons" --out assets/oci-icons
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --out examples/web-architecture.html
python scripts/serve_architecture_site.py --port 8765 --diagram web-architecture
```

If `python` is not on PATH, use the Python executable bundled with your Codex
workspace runtime.

Then open the local gallery with the Codex in-app Browser:

```text
http://127.0.0.1:8765/src/index.html?diagram=web-architecture
```

## Skills

The plugin is split into focused local skills instead of one large prompt:

- `oci-architecture-diagram`: orchestrates the full workflow.
- `oci-spec-normalizer`: converts natural language to JSON v1.
- `oci-architecture-validator`: checks schema, service placement, and coherence.
- `oci-icon-catalog`: extracts/imports/sanitizes OCI icons.
- `oci-diagram-renderer`: runs the HTML renderer and gallery generator.
- `oci-diagram-visual-qa`: uses Browser checks for icons, labels, spacing, and navigation.

## What It Produces

- `assets/oci-icons/*.svg`: best-effort SVG icons converted from OCI `.vssx`
  stencils, optionally replaced by cleaner SVG artwork from Oracle's OCI icon
  library through `scripts/import_oci_svg_icons.py`.
- `assets/oci-icons/catalog.json`: service names, aliases, categories, and
  conversion warnings.
- A single HTML file with inline CSS and embedded SVG, suitable for sharing or
  opening directly in a browser.
- `src/index.html`: a local HTTP gallery for navigating generated diagrams.
- `src/projects.json`: a portable database for names, descriptions, versions
  and HTML paths. The project menu edits this file through the localhost server,
  duplicates cases as explicit versions and exports checked projects as ZIP.

## Spec

The renderer accepts a small JSON model:

- `title`: diagram title.
- `layout`: currently `left-to-right`.
- `groups[]`: visual containers such as region, VCN, and subnet.
- `nodes[]`: OCI resources with `id`, `label`, `service`, and `group`.
- `edges[]`: connections with `from`, `to`, and optional `label`.

## Case Deck and BoM

The existing architecture JSON remains the source of the OCI diagram. A
companion case-deck JSON supplies the executive summary, service roles, sizing
explanations and exact configuration/service references to the BoM. Render it
without altering either JSON artifact:

~~~powershell
python scripts/generate_oci_diagram.py --spec deliverables/case-architecture.json --deck deliverables/case-deck.json --bom deliverables/case-oracle-cost-estimator.json --out deliverables/case-deck.html
~~~

The renderer calls scripts/oracle-bom.mjs detail first; an invalid hash or
invalid Cost Estimator structure stops rendering. For a cost-aligned deck, the
architecture nodes, component inventory and BoM rows must match the positive
monthly estimates in the supplied JSON one-to-one; unpriced components are not
rendered. Use
$oci-architecture-case-deck for the integrated discovery, architecture,
sizing, validation and case-memory workflow.

## Local Browser Flow

Use this flow when testing the plugin inside Codex:

1. Render or regenerate diagram HTML under `examples/`.
2. Register the diagram or case deck in `src/projects.json` when it should
   appear in the gallery. This portable JSON catalog stores project names,
   descriptions and explicit versions.
3. Serve the plugin root:

```powershell
python scripts/serve_architecture_site.py --port 8765 --diagram arquitectura-web-oke-adb
```

4. Use `@Browser` to open a local HTTP URL such as:

```text
http://127.0.0.1:8765/src/index.html?diagram=arquitectura-web-oke-adb
```

Open the project menu to search, select, duplicate, delete or export projects.
Double click the title or description in the viewer header to edit it, then
confirm whether to save. The server writes valid updates atomically to
`src/projects.json`; an extracted ZIP keeps a local browser fallback and
includes only the projects selected for sharing.

When the gallery is served locally, Use Case image uploads are validated and
written under `assets/project-images/<project-id>/`; the corresponding
project-relative `caseImageUrl` is stored atomically in `src/projects.json`.
The image remains available after a refresh, duplication, or selected-project
ZIP export.

Avoid standalone Playwright package imports for visual QA. The Browser plugin
is the intended surface for loading, inspecting, and refreshing local pages in
Codex.

Final responses for generated diagrams should lead with the localhost gallery
URL that was opened in the Codex Browser, followed by any HTML/JSON artifact
paths and renderer warnings.
