#!/usr/bin/env python3
"""Extract OCI service icons from Visio .vssx stencils into SVG files.

The official OCI Visio stencils store the service artwork as Visio vector
geometry, not as simple image files. This extractor reads the package, maps
masters to their vector definitions, and emits best-effort SVG icons plus a
catalog used by the HTML renderer.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"v": VISIO_NS, "r": REL_NS, "pr": PKG_REL_NS}
RID = f"{{{REL_NS}}}id"

PLUGIN_ROOT = Path(__file__).resolve().parents[1]

GENERIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect x="10" y="14" width="80" height="68" rx="12" fill="#fff7f4" stroke="#c74634" stroke-width="6"/>
  <path d="M26 36h48M26 51h48M26 66h30" fill="none" stroke="#312d2a" stroke-width="7" stroke-linecap="round"/>
  <circle cx="72" cy="66" r="7" fill="#2c5967"/>
</svg>
"""

CURATED_ALIASES = {
    "adb": "oracle-autonomous-database",
    "autonomous-database": "oracle-autonomous-database",
    "autonomous-db": "oracle-autonomous-database",
    "bucket": "buckets",
    "buckets": "buckets",
    "compute": "virtual-machine",
    "compute-instance": "virtual-machine",
    "database": "oracle-database",
    "db": "oracle-database",
    "function": "functions",
    "functions": "functions",
    "igw": "internet-gateway",
    "instance": "virtual-machine",
    "internet-gateway": "internet-gateway",
    "k8s": "container-engine-for-kubernetes",
    "kubernetes": "container-engine-for-kubernetes",
    "lb": "load-balancer-primary",
    "load-balancer": "load-balancer-primary",
    "nat": "nat-gateway",
    "object-storage": "object-storage",
    "oke": "container-engine-for-kubernetes",
    "storage": "object-storage",
    "subnet": "route-table-and-security-list-subnets",
    "vcn": "virtual-cloud-network",
    "vm": "virtual-machine",
}


@dataclass
class SvgShape:
    markup: str
    warnings: list[str] = field(default_factory=list)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return re.sub(r"-+", "-", slug) or "unknown"


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def cell_map(elem: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for cell in elem.findall("v:Cell", NS):
        name = cell.attrib.get("N")
        if name:
            result[name] = cell.attrib.get("V", "")
    return result


def row_cell(row: ET.Element, name: str) -> str | None:
    cell = row.find(f"v:Cell[@N='{name}']", NS)
    if cell is None:
        return None
    return cell.attrib.get("V")


def parse_color(value: str | None, default: str = "#312d2a") -> str:
    if not value:
        return default
    value = value.strip()
    if value.startswith("#") and len(value) in (4, 7):
        return value
    if value == "0":
        return "#000000"
    if value == "1":
        return "#ffffff"
    return default


def parse_polyline(value: str | None) -> list[tuple[float, float]]:
    if not value:
        return []
    match = re.search(r"POLYLINE\((.*?)\)", value, re.IGNORECASE)
    if not match:
        return []
    nums = [parse_float(part) for part in re.split(r"[,\s]+", match.group(1).strip()) if part]
    return list(zip(nums[0::2], nums[1::2]))


def point_from_row(row: ET.Element, width: float, height: float, relative: bool) -> tuple[float, float]:
    x = parse_float(row_cell(row, "X"))
    y = parse_float(row_cell(row, "Y"))
    if relative:
        x *= width
        y *= height
    return x, y


def style_for_shape(cells: dict[str, str], section: ET.Element) -> tuple[str, str, str]:
    section_cells = cell_map(section)
    no_fill = section_cells.get("NoFill") == "1" or cells.get("FillPattern") == "0"
    no_line = (
        section_cells.get("NoLine") == "1"
        or cells.get("LinePattern") == "0"
        or cells.get("LineWeight") == "0"
    )
    fill = "none" if no_fill else parse_color(cells.get("FillForegnd"), "#2c5967")
    stroke = "none" if no_line else parse_color(cells.get("LineColor"), "#312d2a")
    raw_weight = parse_float(cells.get("LineWeight"), 0.004)
    stroke_width = "0" if no_line else fmt(min(max(raw_weight, 0.0025), 0.012))
    return fill, stroke, stroke_width


def convert_points(
    points: Iterable[tuple[float, float]],
    offset_x: float,
    offset_y: float,
    root_height: float,
) -> list[tuple[float, float]]:
    return [(offset_x + x, root_height - (offset_y + y)) for x, y in points]


def path_from_section(
    section: ET.Element,
    cells: dict[str, str],
    offset_x: float,
    offset_y: float,
    root_height: float,
) -> list[str]:
    width = max(parse_float(cells.get("Width"), 1.0), 0.001)
    height = max(parse_float(cells.get("Height"), 1.0), 0.001)
    fill, stroke, stroke_width = style_for_shape(cells, section)
    pieces: list[str] = []
    commands: list[str] = []

    def append_path() -> None:
        nonlocal commands
        if len(commands) > 1:
            pieces.append(
                f'<path d="{" ".join(commands)} Z" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}" stroke-linejoin="round"/>'
            )
        commands = []

    for row in section.findall("v:Row", NS):
        row_type = row.attrib.get("T", "")
        relative = row_type.startswith("Rel")

        if row_type in {"MoveTo", "RelMoveTo"}:
            append_path()
            x, y = point_from_row(row, width, height, relative)
            sx, sy = convert_points([(x, y)], offset_x, offset_y, root_height)[0]
            commands.append(f"M {fmt(sx)} {fmt(sy)}")
        elif row_type in {"LineTo", "RelLineTo", "ArcTo", "EllipticalArcTo", "RelEllipticalArcTo", "NURBSTo"}:
            if not commands:
                sx, sy = convert_points([(0, 0)], offset_x, offset_y, root_height)[0]
                commands.append(f"M {fmt(sx)} {fmt(sy)}")
            x, y = point_from_row(row, width, height, relative)
            sx, sy = convert_points([(x, y)], offset_x, offset_y, root_height)[0]
            commands.append(f"L {fmt(sx)} {fmt(sy)}")
        elif row_type in {"PolylineTo", "RelPolylineTo"}:
            points = parse_polyline(row_cell(row, "A"))
            if points:
                max_coord = max(max(abs(x), abs(y)) for x, y in points)
                if relative or max_coord <= 1.5:
                    points = [(x * width, y * height) for x, y in points]
                svg_points = convert_points(points, offset_x, offset_y, root_height)
                data = [f"M {fmt(svg_points[0][0])} {fmt(svg_points[0][1])}"]
                data.extend(f"L {fmt(x)} {fmt(y)}" for x, y in svg_points[1:])
                pieces.append(
                    f'<path d="{" ".join(data)} Z" fill="{fill}" stroke="{stroke}" '
                    f'stroke-width="{stroke_width}" stroke-linejoin="round"/>'
                )
        elif row_type == "Ellipse":
            cx, cy = convert_points([(width / 2, height / 2)], offset_x, offset_y, root_height)[0]
            pieces.append(
                f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(width / 2)}" ry="{fmt(height / 2)}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )
        elif row_type in {"RelCubBezTo", "RelQuadBezTo"}:
            if not commands:
                sx, sy = convert_points([(0, 0)], offset_x, offset_y, root_height)[0]
                commands.append(f"M {fmt(sx)} {fmt(sy)}")
            x, y = point_from_row(row, width, height, True)
            sx, sy = convert_points([(x, y)], offset_x, offset_y, root_height)[0]
            commands.append(f"L {fmt(sx)} {fmt(sy)}")

    append_path()
    return pieces


def render_shape(shape: ET.Element, parent_x: float, parent_y: float, root_height: float) -> SvgShape:
    cells = cell_map(shape)
    width = max(parse_float(cells.get("Width"), 1.0), 0.001)
    height = max(parse_float(cells.get("Height"), 1.0), 0.001)
    pin_x = parse_float(cells.get("PinX"), width / 2)
    pin_y = parse_float(cells.get("PinY"), height / 2)
    loc_x = parse_float(cells.get("LocPinX"), width / 2)
    loc_y = parse_float(cells.get("LocPinY"), height / 2)
    offset_x = parent_x + pin_x - loc_x
    offset_y = parent_y + pin_y - loc_y

    parts: list[str] = []
    warnings: list[str] = []

    if shape.find("v:Text", NS) is None:
        for section in shape.findall("v:Section[@N='Geometry']", NS):
            section_parts = path_from_section(section, cells, offset_x, offset_y, root_height)
            parts.extend(section_parts)

    child_parent = shape.find("v:Shapes", NS)
    if child_parent is not None:
        for child in child_parent.findall("v:Shape", NS):
            child_svg = render_shape(child, offset_x, offset_y, root_height)
            parts.append(child_svg.markup)
            warnings.extend(child_svg.warnings)

    return SvgShape("\n".join(part for part in parts if part), warnings)


def render_master_svg(master_xml: bytes, service_name: str) -> SvgShape:
    root = ET.fromstring(master_xml)
    top_shapes = root.findall("./v:Shapes/v:Shape", NS)
    if not top_shapes:
        return SvgShape(GENERIC_SVG, [f"{service_name}: no top-level Visio shapes found"])

    root_shape = top_shapes[0]
    root_cells = cell_map(root_shape)
    root_width = max(parse_float(root_cells.get("Width"), 1.0), 0.001)
    root_height = max(parse_float(root_cells.get("Height"), 1.0), 0.001)

    shape_parent = root_shape.find("v:Shapes", NS)
    shapes = shape_parent.findall("v:Shape", NS) if shape_parent is not None else top_shapes
    parts: list[str] = []
    warnings: list[str] = []
    for shape in shapes:
        rendered = render_shape(shape, 0, 0, root_height)
        if rendered.markup:
            parts.append(rendered.markup)
        warnings.extend(rendered.warnings)

    if not parts:
        return SvgShape(GENERIC_SVG, [f"{service_name}: no convertible vector geometry found"])

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(root_width)} {fmt(root_height)}">\n'
        f'  <title>{html.escape(service_name)}</title>\n'
        f'  <g>\n{"".join(parts)}\n  </g>\n'
        f"</svg>\n"
    )
    return SvgShape(svg, warnings)


def read_xml_from_zip(zf: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(zf.read(name))


def relationships_by_id(zf: zipfile.ZipFile) -> dict[str, str]:
    rels = read_xml_from_zip(zf, "visio/masters/_rels/masters.xml.rels")
    result: dict[str, str] = {}
    for rel in rels.findall("pr:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            result[rid] = target
    return result


def master_rel_id(master: ET.Element) -> str | None:
    rel = master.find("v:Rel", NS)
    if rel is None:
        return None
    return rel.attrib.get(RID)


def keywords_for_master(master: ET.Element) -> list[str]:
    keywords: list[str] = []
    for cell in master.findall("./v:PageSheet/v:Cell", NS):
        if cell.attrib.get("N") == "ShapeKeywords":
            value = cell.attrib.get("V", "")
            keywords.extend(part.strip() for part in value.split(",") if part.strip())
    return keywords


def category_from_file(path: Path) -> str:
    name = path.stem
    if name.startswith("OCI_"):
        name = name[4:]
    return name.replace("_", " ")


def resolve_source(raw: str) -> Path:
    path = Path(raw)
    candidates = [
        path,
        Path.cwd() / path,
        PLUGIN_ROOT / path,
        PLUGIN_ROOT.parent.parent / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Source path not found: {raw}")


def resolve_output(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    normalized = raw.replace("\\", "/")
    if normalized.startswith("../assets/"):
        return (PLUGIN_ROOT / normalized.removeprefix("../")).resolve()
    return (Path.cwd() / path).resolve()


def extract_icons(source: Path, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "generic.svg").write_text(GENERIC_SVG, encoding="utf-8")

    services: dict[str, dict[str, object]] = {}
    aliases: dict[str, str] = {"generic": "generic"}
    warnings: list[str] = []

    for stencil in sorted(source.glob("*.vssx")):
        category = category_from_file(stencil)
        with zipfile.ZipFile(stencil) as zf:
            rels = relationships_by_id(zf)
            masters = read_xml_from_zip(zf, "visio/masters/masters.xml")
            for master in masters.findall("v:Master", NS):
                if master.attrib.get("IconSize") != "4":
                    continue
                service_name = master.attrib.get("Name") or master.attrib.get("NameU") or "Unknown OCI Service"
                slug = slugify(service_name)
                rel_id = master_rel_id(master)
                target = rels.get(rel_id or "")
                if not target:
                    warnings.append(f"{stencil.name}: {service_name} has no master relationship")
                    continue
                try:
                    rendered = render_master_svg(zf.read(f"visio/masters/{target}"), service_name)
                except Exception as exc:  # noqa: BLE001 - catalog should survive partial Visio issues
                    rendered = SvgShape(GENERIC_SVG, [f"{service_name}: {exc}"])
                icon_file = f"{slug}.svg"
                (out_dir / icon_file).write_text(rendered.markup, encoding="utf-8")

                keywords = keywords_for_master(master)
                services[slug] = {
                    "name": service_name,
                    "category": category,
                    "file": icon_file,
                    "sourceFile": stencil.name,
                    "masterId": master.attrib.get("ID"),
                    "keywords": keywords,
                    "warnings": rendered.warnings,
                }
                aliases[slug] = slug
                aliases[slugify(service_name)] = slug
                for keyword in keywords:
                    aliases.setdefault(slugify(keyword), slug)
                warnings.extend(rendered.warnings)

    for alias, target in CURATED_ALIASES.items():
        if target in services:
            aliases[alias] = target

    catalog = {
        "generatedBy": "extract_oci_icons.py",
        "source": str(source),
        "serviceCount": len(services),
        "services": services,
        "aliases": dict(sorted(aliases.items())),
        "warnings": warnings,
    }
    (out_dir / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract OCI Visio stencil icons to SVG.")
    parser.add_argument("--source", default=str(PLUGIN_ROOT.parent.parent / "oci"), help="Directory containing OCI .vssx files.")
    parser.add_argument("--out", default=str(PLUGIN_ROOT / "assets" / "oci-icons"), help="Output directory for SVG icons and catalog.json.")
    args = parser.parse_args(argv)

    try:
        source = resolve_source(args.source)
        out_dir = resolve_output(args.out)
        catalog = extract_icons(source, out_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Extracted {catalog['serviceCount']} OCI service icons to {out_dir}")
    if catalog.get("warnings"):
        print(f"Warnings: {len(catalog['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
