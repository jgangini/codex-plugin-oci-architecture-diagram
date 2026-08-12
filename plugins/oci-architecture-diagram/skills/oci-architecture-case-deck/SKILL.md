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
Lay out the Use Case body in two equal columns: a portable, accessible visual
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
architecture. Hovering or focusing a card must highlight the matching diagram
node and visually de-emphasize the other nodes. Order the cards by the final
diagram coordinates: left to right, then top to bottom within each column, so
keyboard and pointer reading order match the architecture.

In the BoM tab, show the annual estimate (monthly total multiplied by 12) directly
to the left of the monthly total; this is a presentation total, not a discounted
price. Place a `Descargar JSON` button to the right of those totals. The portable deck must embed and download the exact bytes of the supplied
Oracle Cost Estimator JSON. Alongside the button, explain that the user should
open Oracle Cloud Cost Estimator, choose the three-dot menu, select `Import`, and
upload the JSON; include the official Cost Estimator link.

Every tab must expose a camera-icon button in the upper-right header. It copies
the active 16:9 page to the clipboard as a 1920×1080 PNG so it can be pasted into
PowerPoint. Exclude the capture control itself from the copied image and announce
success or failure through an accessible live region.

## Portable project portfolio

Register generated cases and diagrams in `src/projects.json`; this JSON file is
the portable project database. Keep the project menu available for diagrams and
case decks. The menu must support search, multi-selection for sharing, inline
name and description editing on double click, and duplication with an explicit
version number. Persist edits atomically through the localhost server; retain a
browser-local fallback when a shared package is opened without that server.

Export selected projects as a dependency-free ZIP containing their portable
HTML files, `projects.json`, the gallery shell and its OCI icon. A recipient must
be able to open `src/index.html` from the extracted package and navigate only
the projects selected by the sender.

## Delivery

Always deliver the unchanged architecture JSON, the unchanged Oracle Cost Estimator JSON, the case-deck JSON, the deck HTML and the validation state. Do not call the BoM browser-validated until the exact final JSON has been imported successfully in a clean Oracle Cost Estimator session.
