#!/usr/bin/env python3
"""Render every architecture prompt case to HTML and build a small gallery."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from architecture_prompt_cases import architecture_prompt_cases
import generate_oci_diagram as renderer


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PLUGIN_ROOT / "examples" / "generated-suite"
DEFAULT_CATALOG = PLUGIN_ROOT / "assets" / "oci-icons" / "catalog.json"


def gallery_html(title: str, subtitle: str, links: list[str], quick_prefix: str = "", suite_href: str = "generated-suite/index.html") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --ink: #312d2a;
      --muted: #5c6f82;
      --line: #d7dde4;
      --oci: #c74634;
      --panel: #ffffff;
      --page: #f6f7f8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--page);
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px;
    }}
    header {{
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
    }}
    .quick-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 20px;
    }}
    .quick-links a {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: #2c5967;
      padding: 9px 12px;
      font-weight: 700;
      text-decoration: none;
    }}
    ol {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 12px;
      list-style-position: inside;
      padding: 0;
      margin: 0;
    }}
    li {{
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 12px;
      min-height: 116px;
    }}
    li a {{
      display: block;
      color: var(--oci);
      font-weight: 700;
      text-decoration: none;
      margin-bottom: 6px;
    }}
    li span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(subtitle)}</p>
      </div>
    </header>
    <nav class="quick-links" aria-label="Quick links">
      <a href="{html.escape(quick_prefix)}live-query-ecommerce.html">Consulta viva e-commerce</a>
      <a href="{html.escape(suite_href)}">Galeria generated-suite</a>
      <a href="{html.escape(quick_prefix)}web-architecture.html">Ejemplo web minimo</a>
    </nav>
    <ol>
      {"".join(links)}
    </ol>
  </main>
</body>
</html>
"""


def render_suite(out_dir: Path, catalog_path: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog = renderer.load_catalog(catalog_path)
    links: list[str] = []
    root_links: list[str] = []
    for case in architecture_prompt_cases():
        output = out_dir / f"{case['id']}.html"
        output.write_text(renderer.render_html(case["spec"], catalog, catalog_path), encoding="utf-8")
        links.append(
            f'<li><a href="{html.escape(output.name)}">{html.escape(case["id"])}</a>'
            f'<span>{html.escape(case["prompt"])}</span></li>'
        )
        root_links.append(
            f'<li><a href="{html.escape(out_dir.name)}/{html.escape(output.name)}">{html.escape(case["id"])}</a>'
            f'<span>{html.escape(case["prompt"])}</span></li>'
        )

    (out_dir / "index.html").write_text(
        gallery_html(
            "OCI Architecture Prompt Suite",
            "Arquitecturas OCI renderizadas como diagramas HTML/SVG estaticos.",
            links,
            quick_prefix="../",
            suite_href="index.html",
        ),
        encoding="utf-8",
    )
    (out_dir.parent / "index.html").write_text(
        gallery_html(
            "OCI Architecture Diagram Gallery",
            "Portada local con la consulta viva y la galeria generada.",
            root_links,
        ),
        encoding="utf-8",
    )
    return len(links)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the 100-case OCI architecture prompt suite.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    catalog_path = Path(args.catalog)
    diagram_count = render_suite(out_dir, catalog_path)
    print(f"Rendered {diagram_count} diagrams to {out_dir}")
    print(f"Gallery: {out_dir / 'index.html'}")
    print(f"Root index: {out_dir.parent / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
