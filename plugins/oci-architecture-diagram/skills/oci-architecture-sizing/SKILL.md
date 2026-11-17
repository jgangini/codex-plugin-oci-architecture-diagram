---
name: oci-architecture-sizing
description: Turn an approved OCI architecture into traceable low/base/high quantities, a safe Oracle Cost Estimator JSON and a case-deck JSON with exact pricing references.
---

# OCI Architecture Sizing

Use measurable workload drivers, not named users alone. Select and label low, base or high; record formulas, assumptions and the bridge to the Cost Estimator configuration.

Use scripts/oracle-bom.mjs validate and summary as local preflight. Preserve unknown estimator fields and never overwrite a seed JSON. The case-deck JSON must map every positive monthly price line by exact configuration and service label. Architecture nodes, deck components and BoM rows must match one-to-one; omit unpriced components from a cost-aligned deck. Set validation to locally_validated until clean browser import succeeds.

For final artifacts, invoke `oci-cost-estimator-browser-export`. Use its Browser
round trip instead of an API: build or import the estimate, export the official
JSON and XLS from the same session, then re-import the exact exported JSON in a
clean session. Only then set `bom.validation` to `browser_validated`. A locally
rendered table, CSV, `.json`, or `.xlsx` is not an Oracle Cost Estimator export.

If Cost Estimator accepts the upload but produces no expected configurations or
USD 0.00, treat the import as rejected. Rebuild the estimate in the current
catalog rather than editing `meta.dataBuildID` or `meta.hash` locally.
