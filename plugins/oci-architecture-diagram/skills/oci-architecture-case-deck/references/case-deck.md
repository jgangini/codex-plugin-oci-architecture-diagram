# Case deck JSON v1

The deck is a companion artifact. It never replaces the normalized architecture JSON or the exact Oracle Cost Estimator JSON.

Required fields:

- version: 1
- case.summary and case.objective: non-empty strings
- case.description and case.imagePrompt: optional non-empty strings; imagePrompt
  overrides the generated prompt, whose size and aspect ratio match the rendered
  Use Case image area
- case.scope, case.assumptions and case.openDecisions: optional string arrays
- bom.scenario: low, base or high
- bom.validation: browser_validated, locally_validated or blocked
- bom.priceFreshness: current or unverified
- components: one to fourteen entries with id, optional nodeId, service, component, role, sizing and optional pricingRefs

Each pricing reference contains an exact configuration and service label from the Oracle Cost Estimator JSON. An optional sku narrows the reference to one item. The renderer calculates the amount itself only after canonical BoM validation succeeds.
