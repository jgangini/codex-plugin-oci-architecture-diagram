---
name: oci-spec-normalizer
description: Convert Spanish or English natural-language Oracle Cloud architecture requests into the plugin's normalized v1 JSON diagram specification with stable groups, nodes, services, and edges.
---

# OCI Spec Normalizer

Use this skill when the user describes an OCI architecture in natural language
and needs a renderable JSON spec.

## Schema v1

```json
{
  "title": "OCI Web Architecture",
  "layout": "left-to-right",
  "groups": [
    { "id": "region", "label": "OCI Region", "type": "region" },
    { "id": "vcn", "label": "Production VCN", "type": "vcn", "parent": "region" },
    { "id": "private-subnet", "label": "Private Subnet", "type": "subnet", "parent": "vcn" }
  ],
  "nodes": [
    { "id": "lb", "label": "Public Load Balancer", "service": "Load Balancer", "group": "public-subnet" },
    { "id": "oke", "label": "Application Pods", "service": "OKE", "group": "private-subnet" }
  ],
  "edges": [
    { "from": "lb", "to": "oke", "label": "HTTP" }
  ]
}
```

Required node fields: `id`, `label`, `service`, `group`.
Required edge fields: `from`, `to`; `label` is optional.
Supported group fields: `id`, `label`, `type`, `parent`.

## Normalization Rules

- Use only the architecture name in `title`; do not add internal prefixes such
  as `OCI Live Query`, `demo`, `generated`, or `static diagram`.
- Treat region, VCN, public subnet, private subnet, data subnet, and operations
  subnet as groups unless the user explicitly asks to show them as service
  nodes.
- Prefer left-to-right flow: public entry, edge/network security, application
  tier, data/storage tier, platform services.
- Use lowercase kebab-case ids: `public-lb`, `app-pods`, `transaction-db`.
- Keep labels human-readable and service names catalog-friendly.
- Add edge labels only when the flow has a protocol or purpose: `DNS`, `HTTPS`,
  `HTTP`, `SQL`, `object API`, `events`, `async orders`, `logs`, `metrics`,
  `secrets`, `admin`.
- Do not invent unsupported OCI services when a close catalog service exists.

## Common Service Synonyms

- `OKE`, `kubernetes`, `k8s` -> `Container Engine for Kubernetes`
- `ADB`, `autonomous database`, `base autonoma` -> `Oracle Autonomous Database`
- `VM`, `compute`, `instancia` -> `Virtual Machine`
- `LB`, `balanceador`, `load balancer` -> `Load Balancer - Primary`
- `WAF`, `firewall web` -> `WAF`
- `bucket`, `object store`, `almacenamiento de objetos` -> `Object Storage`
- `VCN` -> `Virtual Cloud Network`
- `IGW`, `internet gateway` -> `Internet Gateway`
- `queue`, `cola`, `mensajeria` -> `OCI Queue`

## Output Discipline

Produce only valid JSON when the user asks for a spec. If they ask for a
diagram, save the spec and hand off to `oci-architecture-validator` and
`oci-diagram-renderer`.
