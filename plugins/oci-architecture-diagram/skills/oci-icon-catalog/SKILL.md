---
name: oci-icon-catalog
description: Maintain the OCI icon catalog for the diagram plugin by extracting Visio .vssx stencils, importing Oracle SVG icon folders, sanitizing SVG artwork, mapping aliases, and fixing generic or broken service icons.
---

# OCI Icon Catalog

Use this skill when icons are missing, generic, too small, visually broken, or
when the user provides an OCI icon folder.

## Sources

The plugin supports two local icon paths:

- Visio stencils from the repo `oci/` folder.
- Oracle SVG icon library folders such as `D:\Desktop\Oracle\4.tools\_OCI icons`.

No network is required.

## Extract Visio Stencils

```powershell
python scripts/extract_oci_icons.py --source ../../oci --out assets/oci-icons
```

This creates best-effort SVGs and `assets/oci-icons/catalog.json`.

## Import Clean SVG Library

```powershell
python scripts/import_oci_svg_icons.py --source "D:\Desktop\Oracle\4.tools\_OCI icons" --out assets/oci-icons
```

The importer maps SVG filenames to catalog services, sanitizes metadata, prefixes
classes and ids, inlines style rules, updates `catalog.json`, and marks imported
services with `iconSource: local-svg`.

## Quality Checks

- Inspect `catalog.json` for `localSvgImportedCount`.
- Confirm key services use `iconSource: local-svg`: DNS, WAF, Load Balancer,
  Container Engine for Kubernetes, Autonomous Database, Object Storage, Bastion,
  Vault, Logging, Monitoring, Service Gateway, Streaming, OCI Queue.
- Regenerate affected diagrams after icon import.
- Use `oci-diagram-visual-qa` when a browser screenshot is available.
