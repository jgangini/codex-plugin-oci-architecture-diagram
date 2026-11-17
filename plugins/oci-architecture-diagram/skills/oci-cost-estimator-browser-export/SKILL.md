---
name: oci-cost-estimator-browser-export
description: Build, export, and round-trip validate official Oracle Cloud Cost Estimator JSON and XLS artifacts through the Browser UI when a BoM is created, refreshed, rejected on import, or requested in Oracle's official format.
---

# OCI Cost Estimator Browser Export

Use this skill after sizing is approved and before a case deck exposes JSON or
XLS downloads. Use the official Oracle Cloud Cost Estimator UI through the
Browser plugin; do not call an API and do not synthesize Oracle metadata,
catalog hashes, prices, JSON, or spreadsheets locally.

## Hard contract

- A local validator is only a preflight. It cannot mark an artifact official.
- `meta.dataBuildID` and `meta.hash` belong to Cost Estimator. Never copy,
  calculate, patch, or reuse them from another estimate.
- Treat JSON and XLS as one artifact pair exported from the same in-memory
  estimate.
- Do not mutate the JSON after export.
- Set `bom.validation` to `browser_validated` only after the exported JSON
  passes the clean-session round trip below.
- Until that succeeds, set `bom.validation` to `locally_validated` or `blocked`,
  keep `bom.priceFreshness` as `unverified`, and disable official JSON/XLS
  downloads in the deck and project menu.

## Workflow

1. Open a clean `https://www.oracle.com/cloud/costestimator.html` tab with the
   Browser plugin and record the visible data build number and build date.
2. If an earlier JSON exists, try **Main actions > Import** once. Import
   succeeds only when the dialog closes, the expected configurations appear,
   the expected total is nonzero or otherwise explicitly justified, and
   **Export** is enabled. A closed dialog alone is not success.
3. If import fails, rebuild the approved configurations in Cost Estimator with
   visible service controls. Do not repair the JSON outside the page. Match the
   architecture, configuration names, SKUs, quantities, utilization, region,
   currency, and sizing assumptions one-to-one.
4. Select **Main actions > Export**, choose **JavaScript Object Notation
   (JSON)**, give the file a stable project name, and download it.
5. Without changing the estimate, export **Excel Spreadsheet (XLS)** with the
   same base name. Preserve both files beside the architecture and case-deck
   manifests.
6. Open another clean Cost Estimator tab. Import the exact downloaded JSON and
   select **Import** only after the button is enabled.
7. Verify all expected configurations, SKUs, quantities, and the displayed
   monthly total. Verify **Export** is enabled. Record the validation timestamp,
   build number, build date, currency, and the paths of the official JSON/XLS
   pair in the delivery notes.
8. Mark the deck `browser_validated`, set price freshness to `current` only when
   the selected catalog/region/currency are current, rerender, and register the
   project with `bomValidation: "browser_validated"`.

## Failure handling

If the official JSON exported moments earlier does not round-trip, keep the
artifacts as diagnostics but do not publish them. Capture the visible state and
browser logs without inventing a checksum fix. Report the Cost Estimator build
and leave the deck downloads disabled.

If an older JSON imports to an empty estimate or USD 0.00, treat it as rejected
even if the dialog closes. Rebuild it in the current catalog and repeat the
complete export and round-trip validation.

## Delivery

Deliver the unchanged Oracle JSON, Oracle XLS, architecture JSON, case-deck
JSON, HTML, and the validation record. The static HTML may download the
embedded official pair, but it must never automate Cost Estimator itself or
label a locally generated workbook as official.
