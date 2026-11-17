#!/usr/bin/env python3
"""Import Oracle's published OCI SVG icon library into the local catalog.

The Visio extractor keeps the plugin self-contained, but the Illustrator SVG
library has cleaner artwork. This importer maps those SVG files onto the
existing catalog entries, sanitizes noisy metadata, prefixes CSS classes/ids,
and replaces the canonical catalog SVG files in assets/oci-icons.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = PLUGIN_ROOT / "assets" / "oci-icons" / "catalog.json"
DEFAULT_OUT = PLUGIN_ROOT / "assets" / "oci-icons"

SERVICE_ICON_OVERRIDES: dict[str, tuple[str, ...]] = {
    "dns": ("domain-name-system-dns",),
    "waf": ("web-application-firewall-waf", "firewall"),
    "load-balancer-primary": ("load-balancer-lb", "flexible-load-balancer"),
    "oracle-autonomous-database": ("autonomous-database",),
    "oracle-autonomous-data-warehouse": ("autonomous-data-warehouse",),
    "oracle-autonomous-transaction-processing-atp": ("autonomous-transaction-processing-atp",),
    "oci-queue": ("queuing",),
    "virtual-cloud-network": ("virtual-cloud-network-vcn-red", "virtual-cloud-network-vcn"),
    "vault": ("vault", "key-vault"),
}

TRAILING_ACRONYMS = (
    "adb",
    "adw",
    "atp",
    "cdn",
    "cpe",
    "dcat",
    "dns",
    "drg",
    "lb",
    "mds",
    "nsg",
    "oda",
    "vcn",
    "vm",
    "waf",
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return re.sub(r"-+", "-", slug) or "unknown"


def add_candidate(candidates: list[str], value: str) -> None:
    slug = slugify(value)
    if slug and slug not in candidates:
        candidates.append(slug)


def discover_svg_icons(source: Path) -> dict[str, Path]:
    icons: dict[str, Path] = {}
    for path in source.rglob("*.svg"):
        if path.name.startswith("._"):
            continue
        slug = slugify(path.stem)
        current = icons.get(slug)
        if current is None or icon_rank(path, source) < icon_rank(current, source):
            icons[slug] = path
    return icons


def icon_rank(path: Path, source: Path) -> tuple[int, int, str]:
    rel = path.relative_to(source)
    return (len(rel.parts), len(path.name), str(rel).lower())


def service_candidates(slug: str, service: dict[str, Any], aliases: dict[str, str]) -> list[str]:
    candidates: list[str] = []
    for override in SERVICE_ICON_OVERRIDES.get(slug, ()):
        add_candidate(candidates, override)

    add_candidate(candidates, slug)
    name = str(service.get("name", ""))
    add_candidate(candidates, name)

    for base in list(candidates):
        if base.startswith("oracle-"):
            add_candidate(candidates, base.removeprefix("oracle-"))
        if base.startswith("oci-"):
            add_candidate(candidates, base.removeprefix("oci-"))
        for acronym in TRAILING_ACRONYMS:
            suffix = f"-{acronym}"
            if base.endswith(suffix):
                add_candidate(candidates, base[: -len(suffix)])
        if base.endswith("-red"):
            add_candidate(candidates, base.removesuffix("-red"))

    for alias, target in aliases.items():
        if target == slug and len(alias) > 2:
            add_candidate(candidates, alias)

    return candidates


def prefix_style_classes(style: str, class_prefix: str) -> str:
    return re.sub(r"\.([A-Za-z_][\w-]*)", rf".{class_prefix}\1", style)


def prefix_class_attributes(markup: str, class_prefix: str) -> str:
    def replace_double(match: re.Match[str]) -> str:
        classes = " ".join(f"{class_prefix}{part}" for part in match.group(1).split())
        return f'class="{classes}"'

    def replace_single(match: re.Match[str]) -> str:
        classes = " ".join(f"{class_prefix}{part}" for part in match.group(1).split())
        return f"class='{classes}'"

    markup = re.sub(r'\bclass="([^"]+)"', replace_double, markup)
    return re.sub(r"\bclass='([^']+)'", replace_single, markup)


def prefix_ids(markup: str, id_prefix: str) -> str:
    ids = sorted(set(re.findall(r'\bid=["\']([^"\']+)["\']', markup)), key=len, reverse=True)
    for identifier in ids:
        replacement = f"{id_prefix}{identifier}"
        markup = re.sub(rf'\bid=(["\']){re.escape(identifier)}\1', f'id="{replacement}"', markup)
        markup = markup.replace(f"url(#{identifier})", f"url(#{replacement})")
        markup = markup.replace(f'"#{identifier}"', f'"#{replacement}"')
        markup = markup.replace(f"'#{identifier}'", f"'#{replacement}'")
    return markup


def inline_style_rules(markup: str) -> str:
    rules: dict[str, str] = {}

    def collect_rules(match: re.Match[str]) -> str:
        for selector, declarations in re.findall(r"\.([A-Za-z_][\w-]*)\s*\{([^}]+)\}", match.group(1)):
            clean = declarations.strip()
            if clean and not clean.endswith(";"):
                clean += ";"
            rules[selector] = clean
        return ""

    markup = re.sub(r"<style\b[^>]*>(.*?)</style>", collect_rules, markup, flags=re.IGNORECASE | re.DOTALL)
    if not rules:
        return markup

    def apply_rules(match: re.Match[str]) -> str:
        tag = match.group(0)
        class_match = re.search(r'\bclass=["\']([^"\']+)["\']', tag)
        if not class_match:
            return tag
        declarations = " ".join(rules[class_name] for class_name in class_match.group(1).split() if class_name in rules)
        if not declarations:
            return tag
        style_match = re.search(r'\bstyle=(["\'])(.*?)\1', tag)
        if style_match:
            quote = style_match.group(1)
            current = style_match.group(2).strip()
            separator = "; " if current and not current.endswith(";") else " "
            updated = f"style={quote}{current}{separator}{declarations}{quote}"
            return tag[: style_match.start()] + updated + tag[style_match.end() :]
        insertion = f' style="{declarations}"'
        if tag.endswith("/>"):
            return tag[:-2] + insertion + "/>"
        return tag[:-1] + insertion + ">"

    return re.sub(r"<(?!/|style\b|svg\b)[^>]+>", apply_rules, markup, flags=re.IGNORECASE)


def sanitize_svg(raw_svg: str, slug: str) -> str:
    raw_svg = raw_svg.lstrip("\ufeff")
    raw_svg = re.sub(r"<\?xml[^>]*\?>", "", raw_svg, flags=re.IGNORECASE)
    raw_svg = re.sub(r"<!DOCTYPE.*?>", "", raw_svg, flags=re.IGNORECASE | re.DOTALL)
    raw_svg = re.sub(r"<!--.*?-->", "", raw_svg, flags=re.DOTALL)
    match = re.search(r"<svg\b([^>]*)>(.*)</svg>", raw_svg, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("not a valid SVG document")

    attrs = match.group(1)
    body = match.group(2)
    viewbox_match = re.search(r"viewBox=['\"]([^'\"]+)['\"]", attrs)
    viewbox = viewbox_match.group(1) if viewbox_match else "0 0 100 100"

    body = re.sub(r"<metadata\b[^>]*>.*?</metadata>", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<title\b[^>]*>.*?</title>", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<desc\b[^>]*>.*?</desc>", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<v:[^>]+/>\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"<v:([\w-]+)\b[^>]*>.*?</v:\1>\s*", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"\s+v:[\w-]+=(['\"]).*?\1", "", body, flags=re.IGNORECASE | re.DOTALL)

    prefix = f"oci-{slug}-"

    def replace_style(match: re.Match[str]) -> str:
        return f"<style>{prefix_style_classes(match.group(1), prefix)}</style>"

    body = re.sub(r"<style\b[^>]*>(.*?)</style>", replace_style, body, flags=re.IGNORECASE | re.DOTALL)
    body = prefix_class_attributes(body, prefix)
    body = inline_style_rules(body)
    body = prefix_ids(body, prefix)
    body = "\n".join(line.rstrip() for line in body.strip().splitlines())
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">\n{body}\n</svg>\n'


def import_icons(source: Path, out_dir: Path, catalog_path: Path) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(f"Source icon directory not found: {source}")
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")

    source = source.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    services: dict[str, dict[str, Any]] = catalog.get("services", {})
    aliases: dict[str, str] = catalog.get("aliases", {})
    source_icons = discover_svg_icons(source)

    imported: list[dict[str, str]] = []
    unmatched: list[str] = []

    for slug, service in services.items():
        matched_slug = ""
        source_icon: Path | None = None
        for candidate in service_candidates(slug, service, aliases):
            if candidate in source_icons:
                matched_slug = candidate
                source_icon = source_icons[candidate]
                break
        if source_icon is None:
            unmatched.append(slug)
            continue

        icon_file = out_dir / str(service.get("file", f"{slug}.svg"))
        sanitized = sanitize_svg(source_icon.read_text(encoding="utf-8-sig"), slug)
        icon_file.write_text(sanitized, encoding="utf-8")

        service["iconSource"] = "local-svg"
        service["localIconFile"] = source_icon.relative_to(source).as_posix()
        service["matchedLocalIconSlug"] = matched_slug
        service["warnings"] = []
        aliases.setdefault(matched_slug, slug)
        imported.append(
            {
                "service": slug,
                "source": source_icon.relative_to(source).as_posix(),
                "matchedSlug": matched_slug,
            }
        )

    catalog["aliases"] = dict(sorted(aliases.items()))
    catalog["localSvgIconSource"] = str(source)
    catalog["localSvgAvailableCount"] = len(source_icons)
    catalog["localSvgImportedCount"] = len(imported)
    catalog["localSvgUnmatchedCatalogCount"] = len(unmatched)
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "available": len(source_icons),
        "imported": len(imported),
        "unmatched": unmatched,
        "sample": imported[:12],
    }


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import clean OCI SVG icons into the local icon catalog.")
    parser.add_argument("--source", required=True, help="Directory containing Oracle OCI SVG icon files.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Directory containing catalog SVG files.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="catalog.json to update.")
    args = parser.parse_args(argv)

    try:
        report = import_icons(resolve_path(args.source), resolve_path(args.out), resolve_path(args.catalog))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Imported {report['imported']} catalog icons from {report['available']} local OCI SVG files.")
    if report["sample"]:
        print("Sample mappings:")
        for item in report["sample"]:
            print(f"  {item['service']} <- {item['source']}")
    if report["unmatched"]:
        print(f"Unmatched catalog services: {len(report['unmatched'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
