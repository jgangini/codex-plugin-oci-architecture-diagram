---
name: oci-architecture-sizing
description: Turn an approved OCI architecture into traceable low/base/high quantities, a safe Oracle Cost Estimator JSON and a case-deck JSON with exact pricing references.
---

# OCI Architecture Sizing

Use measurable workload drivers, not named users alone. Select and label low, base or high; record formulas, assumptions and the bridge to the Cost Estimator configuration.

Use scripts/oracle-bom.mjs validate and summary as local preflight. Preserve unknown estimator fields and never overwrite a seed JSON. The case-deck JSON must map every positive monthly price line by exact configuration and service label. Architecture nodes, deck components and BoM rows must match one-to-one; omit unpriced components from a cost-aligned deck. Set validation to locally_validated until clean browser import succeeds.
