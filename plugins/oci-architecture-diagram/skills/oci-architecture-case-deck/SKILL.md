---
name: oci-architecture-case-deck
description: Coordinate OCI discovery, architecture, sizing, validated Cost Estimator JSON and a 16:9 case deck with Case, Architecture and BoM tabs.
---

# OCI Architecture Case Deck

Use this skill for an end-to-end OCI case that must produce an architecture JSON, an Oracle Cost Estimator JSON and a presentation-ready web deck.

## Start gate

1. Require a non-empty .source/README.md in the case workspace.
2. Initialize local case memory with node scripts/case-memory.mjs init <workspace> <case-slug>.
3. Keep customer evidence and generated deliverables outside the plugin installation.

## Workflow

1. Invoke oci-architecture-commercial-discovery to record facts, questions and assumptions.
2. Invoke oci-architecture-solution to approve the service map and create the normalized architecture JSON.
3. Invoke oci-architecture-sizing to select low/base/high, produce the exact Oracle Cost Estimator JSON and the case-deck JSON.
4. Validate the architecture and render the deck with python scripts/generate_oci_diagram.py --spec <architecture.json> --deck <case-deck.json> --bom <oracle-cost-estimator.json> --out <case-deck.html>.
5. Invoke oci-architecture-curation after final delivery.

The architecture nodes, service inventory and BoM table must be a one-to-one
view of components with a positive monthly estimate in the supplied Oracle Cost
Estimator JSON. Do not add unpriced convenience, security, network or
observability nodes to a cost-aligned case deck.

Use `Use Case` as the case-tab heading. Its one-line header description must be
generic and explain what the page contains; do not use the case-specific
objective as that subtitle. Present the objective once in the tab body without
adding scope, assumptions or open-decision panels unless the user requests them.
Lay out the Use Case body in two equal columns. The visual column must be a
replaceable image area that fills its container with `object-fit: cover`. Center
the upload-image icon and show the exact rendered width and height of that area,
not a fixed 16:9 size. Generate a GPT image prompt using the same calculated
aspect ratio and dimensions so the generated asset fills the area without crop
or bars. In the editable prompt dialog, place a copy icon inside the textarea's
lower-right corner and show a toast after copying; do not use a separate text
copy button. When served from the local portfolio, persist an uploaded image
in the project's `assets/project-images/<project-id>/` folder and store its
relative URL in `projects.json`; browser storage is only the offline fallback.
Persist its editable prompt and direct text edits locally in the portable deck;
clicking the uploaded image must open download and delete actions, while the
prompt text icon remains in the image corner. Accept PNG, JPEG and WebP
uploads up to 3 MB; show a visible error toast when the selected file is
rejected or cannot be read.
Make the page subtitle, case description and architecture service labels editable
on click through an explicit Save action. Use a portable, accessible visual
illustration on the left and the case-specific objective on the right. Embed the
visual in the HTML so the deck does not depend on an external image file.
Generate a concise `case.description` paragraph from discovery evidence and
render it without a colored border or background. Use a case-specific generated
image when available; otherwise preserve the generated visual as a replaceable
image area.

In the Architecture tab, use a generic one-line header description that tells
the reader the page contains OCI services, their relationships and the solution
flow; do not enumerate customer-specific services in that subtitle. Each service
card shows only the OCI service name and a brief explanation of its role in that
architecture. Hovering or focusing a card or diagram component must highlight the
matching source node, its immediate destination nodes, and its outgoing lines and
labels; visually de-emphasize unrelated nodes and connections. Order the cards by the final
diagram coordinates: left to right, then top to bottom within each column, so
keyboard and pointer reading order match the architecture.

In the BoM tab, show the annual estimate (monthly total multiplied by 12) directly
to the left of the monthly total; this is a presentation total, not a discounted
price. Show an SKU column from the exact priced lines in the supplied Cost
Estimator JSON. Place a `Descargar JSON` button to the right of those totals.
The portable deck must embed and download the exact bytes of the supplied Oracle
Cost Estimator JSON; do not generate a custom spreadsheet and present it as a
Cost Estimator export. Include an `XLS` action beside the JSON, styled as the
same download control, that
opens Oracle Cloud Cost Estimator, where the user chooses the three-dot menu,
selects `Import`, uploads the JSON, and uses Cost Estimator's own `Export`
action to obtain the official Excel file.

## Browser validation and official Excel

Use the Browser plugin to perform this official UI workflow for each final BoM:

1. Open a clean Cost Estimator tab and select **Main actions > Import**.
2. Upload the exact `--bom` JSON delivered with the deck and select **Import**.
3. Validate success only if the import dialog closes, the expected
   configurations render, and the official **Export** action is enabled.
4. Set `bom.validation` to `browser_validated` only after that visible success
   condition. Keep `locally_validated` if Browser cannot reach or accept the
   JSON, and report the visible failure.
   If Oracle recalculates a different monthly total, retain the accepted import
   result but leave price freshness as `unverified` and regenerate the BoM only
   from the official export.
5. If the user requests the official Excel, select **Export** in that validated
   Cost Estimator tab and preserve the downloaded file alongside the exact
   JSON. Do not substitute a plugin-produced XLSX, CSV, or HTML table.

Invoke `oci-cost-estimator-browser-export` for the official JSON/XLS pair. The
static deck cannot upload files to or automate a third-party website; the
Browser plugin performs that work during a Codex run. Embed the exact validated
JSON and XLS so their deck actions are real downloads, not handoff links.

The portable project menu must expose the same two actions for every
BoM-enabled, browser-validated deck: `JSON` and `XLS` download the exact
official artifacts exported from the same Cost Estimator session. Disable both
actions for an unvalidated or diagram-only project rather than exposing an
invented BoM export.

The portfolio header must expose a download icon for a PowerPoint file. It must
render the Use Case, Architecture and BoM tabs as full 1920×1080 PNGs and package
them as three 16:9 slides in an Office-compatible `.pptx`; do not depend on
clipboard permissions or rebuild the diagram with PowerPoint shapes. Rasterize
the complete deck surface, preserving the Oracle brand as the final floating
layer. Do not rewrite SVG marker definitions or marker presentation attributes
during rasterization. The generated package must include the slide master,
layout, theme and relationships PowerPoint requires. Exclude the download
control itself from the rendered slides and announce success or failure through
an accessible toast.

Use a compact, minimal scrollbar treatment consistently for scrollable deck
controls. Keep success and error toasts compact in the upper-right corner of
the active deck, with green success and OCI-red error states.

The portfolio viewer must keep the 16:9 deck fully visible within the available
viewport, with no page-level vertical scrollbar. Scale the iframe from both the
available width and the height below the portfolio header.

## Portable project portfolio

Register generated cases and diagrams in `src/projects.json`; this JSON file is
the portable project database. Keep the project menu available for diagrams and
case decks. The menu must support search, multi-selection for sharing, inline
name and description editing on double click, and duplication with an explicit
version number. Every new project identifier must use the timestamp format
`yyyy-mm-dd-hh-mm-ss-ms`; use that identifier in the `diagram` URL query
parameter. Persist edits atomically through the localhost server; retain a
browser-local fallback when a shared package is opened without that server.
When a project is served locally, persist an uploaded Use Case image as a
validated PNG, JPEG or WebP file under `assets/project-images/<project-id>/`
and store its relative URL in that project's `caseImageUrl` field in
`projects.json`. Include the file in a selected-project ZIP export; browser
storage is only an offline fallback.

Export selected projects as a dependency-free ZIP containing their portable
HTML files, `projects.json`, the gallery shell and its OCI icon. A recipient must
be able to open `src/index.html` from the extracted package and navigate only
the projects selected by the sender.

## Delivery

Always deliver the unchanged architecture JSON, the unchanged Oracle Cost Estimator JSON, the case-deck JSON, the deck HTML and the validation state. Do not call the BoM browser-validated until the exact final JSON has been imported successfully in a clean Oracle Cost Estimator session.
