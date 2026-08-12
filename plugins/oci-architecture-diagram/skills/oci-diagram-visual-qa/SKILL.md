---
name: oci-diagram-visual-qa
description: Visually verify generated OCI diagram HTML in the Browser, checking icon rendering, text overlap, edge label placement, arrow readability, group spacing, zoom controls, and gallery navigation.
---

# OCI Diagram Visual QA

Use this skill after renderer or CSS changes, after icon imports, or when the
user reports visual issues in the in-app Browser.

## Browser Checks

Serve the plugin root first:

```powershell
python scripts/serve_architecture_site.py --port 8765 --diagram <diagram-id>
```

Open the printed `http://127.0.0.1:8765/src/index.html?diagram=<diagram-id>`
URL with the Browser plugin, then verify:

- Official icons render inside node cards and are not generic blocks.
- Each node card shows only the icon and the OCI service name: icon first,
  service name below it. Functional component names stay out of the visible card.
- Icons must not have an extra colored tile, rounded square, or other backdrop
  behind the official SVG.
- Edge labels sit on or near their paths and do not overlap node cards. Their
  rectangles use a light fill and their text uses a contrasting semantic color;
  no label may inherit SVG's black default fill.
- Edge colors differ by semantic flow.
- Group labels have enough top padding and do not touch node cards.
- Public, app, data, operations, and platform groups are aligned, readable, and
  have enough horizontal space between them for edge labels.
- The bottom of the page must not show a chip-only legend. If service context is
  shown, use a compact service inventory with each component/service and its
  role in the architecture.
- Toolbar controls show compact standalone `-` and `+` buttons plus a matching
  zoom percentage button. Clicking the percentage must fit the diagram. The
  controls sit vertically in the bottom-right of the diagram shell, raised
  above the horizontal scrollbar, with no visible toolbar frame. The controls
  must stay pinned while the diagram zooms or pans, and clicking them must not
  start panning.
- Service inventory uses the English heading `Architecture Services` and a
  table with visible column headers. Rows must flow naturally without vertical
  pagination or an internal height-limited scroll area.
- In case decks, each service card shows only the service name and its concise
  architectural role. Hover and keyboard focus must highlight the corresponding
  SVG node and clear the highlight on exit or blur.
- The upper-right capture icon is visible on every tab, copies the active slide
  as a 1920×1080 PNG, omits itself from the image, and reports clipboard status
  accessibly.
- The gallery root shows links to generated diagrams without debug counters.
- The project menu remains available for diagrams and decks, loads from
  `projects.json`, supports double-click metadata editing and creates a new
  version when duplicating. ZIP export must contain only checked projects and a
  matching portable project database.

Use the Browser plugin as the visual QA surface. Do not import standalone
Playwright packages or drive a separate browser process for this plugin flow;
the Browser skill already exposes the browser inspection API needed for local
pages.

## Browser Delivery

After QA, keep the verified Codex Browser tab on the localhost gallery URL and
return that same URL as the primary final link. Only list `file://` or raw HTML
paths as supporting artifacts.

## Iteration Rule

If a screenshot shows overlap, broken icons, floating labels, or poor spacing,
patch the renderer/spec, regenerate HTML, refresh Browser, and capture again.
Do not stop at a code-only fix for visual bugs.

## Useful DOM Targets

- Diagram: `svg.diagram`
- Nodes: `g.node`
- Icon: `svg.node-icon`
- Edge labels: `.edge-label`
- Service inventory: `.service-inventory`
- Toolbar: `.diagram-toolbar`
- Stage: `.diagram-stage`
- Example DNS node: `#node-dns` or `#node-dns-main`
