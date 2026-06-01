---
name: oci-architecture-validator
description: Validate OCI diagram JSON specs for schema correctness, coherent cloud architecture, service placement, missing connections, duplicated ids, unknown services, and render-risk before generating HTML.
---

# OCI Architecture Validator

Use this skill before rendering non-trivial diagrams, after editing a spec, or
when a user says the generated architecture is incoherent.

## Deterministic Validation

Run the renderer in validation mode from the plugin root:

```powershell
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --validate-only
```

The renderer rejects duplicated node ids, missing edge endpoints, malformed
arrays, and invalid JSON. Unknown services are allowed but should be reviewed
because they render with a generic fallback.

## Architecture Checks

- Public entry should usually be DNS, WAF, Internet Gateway, API Gateway, or
  public Load Balancer before private workloads.
- Databases, queues, vaults, and private application nodes should not be placed
  in a public subnet unless the user explicitly requests it.
- Object Storage should normally be reached through service APIs or Service
  Gateway from private workloads.
- OKE/Compute application tiers should have a clear ingress path and clear data
  path.
- Add observability edges (`logs`, `metrics`) to Logging/Monitoring when the
  prompt mentions operations, production, audit, or troubleshooting.
- Add Vault and `secrets` edges when the prompt mentions encryption, secrets,
  compliance, regulated workloads, or secure credentials.
- Do not overpack one subnet; split public, application, data, and operations
  groups when the diagram has more than six nodes.

## Render-Risk Checks

- Keep node labels short enough for a 184px card; put detail in service names or
  edge labels, not in the node label.
- Prefer 6-14 nodes per diagram for a single static page. Split bigger systems
  into multiple diagrams.
- Avoid many fan-out edges from one node to the same column; use intermediary
  services when the architecture supports it.
- Use labels from the renderer color taxonomy: traffic, data, events, admin,
  security, observability, service.

If validation changes the spec, rerun deterministic validation and then hand off
to `oci-diagram-renderer`.
