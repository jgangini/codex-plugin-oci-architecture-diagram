# OCI Architecture Diagram for Codex

Codex marketplace repository for installing the `oci-architecture-diagram`
plugin. The plugin helps Codex normalize Oracle Cloud Infrastructure
architecture prompts, validate the diagram model, render portable HTML/SVG
diagrams, and open the local gallery in the Codex Browser.

## Install From GitHub

Users can add the marketplace with any of these forms:

```powershell
codex plugin marketplace add jgangini/codex-plugin-oci-architecture-diagram
codex plugin marketplace add jgangini/codex-plugin-oci-architecture-diagram@v0.1.0
codex plugin marketplace add https://github.com/jgangini/codex-plugin-oci-architecture-diagram.git
```

For local testing before publishing:

```powershell
git clone https://github.com/jgangini/codex-plugin-oci-architecture-diagram.git
cd codex-plugin-oci-architecture-diagram
codex plugin marketplace add .
```

Then open Codex, find **OCI Architecture Diagram** in the plugin list, install
it if needed, and start a new thread so the plugin skills are loaded.

## Upgrade

```powershell
codex plugin marketplace upgrade oci-architecture
```

Pinned installs can be upgraded by changing the Git ref, for example from a
tag to `main` or from `v0.1.0` to a newer release tag.

## Marketplace Layout

The marketplace entry lives at:

```text
.agents/plugins/marketplace.json
```

It exposes one plugin:

```text
plugins/oci-architecture-diagram
```

The marketplace source path is intentionally relative:

```json
"path": "./plugins/oci-architecture-diagram"
```

That keeps installation flexible across GitHub shorthand, HTTPS Git URLs, SSH
Git URLs, pinned refs, and local clone workflows.

## Development

From `plugins/oci-architecture-diagram`:

```powershell
python scripts/generate_oci_diagram.py --spec examples/web-architecture.json --out examples/web-architecture.html
python scripts/serve_architecture_site.py --port 8765 --diagram web-architecture
```

Then open:

```text
http://127.0.0.1:8765/src/index.html?diagram=web-architecture
```

Run tests from the repository root:

```powershell
python -m unittest discover -s plugins/oci-architecture-diagram/tests -v
```

Some icon extraction tests expect Oracle OCI stencil sources under a sibling
`oci/` directory. Renderer and packaging tests do not require those external
source files.
