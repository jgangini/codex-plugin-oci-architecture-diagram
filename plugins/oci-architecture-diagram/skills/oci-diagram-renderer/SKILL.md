---
name: oci-diagram-renderer
description: Render validated OCI architecture JSON specs into portable static HTML/SVG diagrams, register them in the project catalog, and report renderer warnings and output paths.
---

# OCI Diagram Renderer

Use this skill when a normalized JSON spec is ready and the user wants the HTML
diagram generated or regenerated.

## Render One Diagram

```powershell
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --out examples/web-architecture.html
```

Use absolute paths when running outside the plugin root.
If the diagram should appear in the navigable local gallery, add or update its
entry in `src/architectures.js`.

## Validate Only

```powershell
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --out examples/web-architecture.html --validate-only
```

## Serve Local Gallery

```powershell
python scripts/serve_architecture_site.py --port 8765 --project web-architecture
```

Open the printed URL with the Browser plugin. For a specific diagram, the URL
must include `?project=<project-id>`, for example:

```text
http://127.0.0.1:8765/src/index.html?project=web-architecture
```

Prefer the HTTP gallery over `file://` links so navigation, iframe loading, and
refreshes match a normal local app flow.

## Output Expectations

- The HTML must be self-contained: inline CSS, embedded SVG icons, no external
  network dependency.
- The page should include the diagram toolbar for zoom, fit, and 1:1 navigation.
- Warnings about unknown services must be reported to the user and reviewed.
- After rendering UI/layout changes, use `oci-diagram-visual-qa` with Browser
  against the local HTTP gallery. Do not import standalone Playwright for this
  plugin workflow.
- Final delivery must include the localhost gallery URL after it has been opened
  in the Codex Browser.
