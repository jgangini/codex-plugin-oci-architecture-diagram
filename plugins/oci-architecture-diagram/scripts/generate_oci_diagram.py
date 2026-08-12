#!/usr/bin/env python3
"""Render a normalized OCI architecture spec as a portable HTML/SVG diagram."""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import re
import subprocess
import sys
import textwrap
import unicodedata
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = PLUGIN_ROOT / "assets" / "oci-icons" / "catalog.json"
DEFAULT_BOM_TOOL = PLUGIN_ROOT / "scripts" / "oracle-bom.mjs"
DECK_BRAND_FILE = PLUGIN_ROOT / "assets" / "ora.svg"

NODE_W = 184
NODE_H = 112
ICON_SIZE = 52
MARGIN_X = 54
MARGIN_Y = 84
RANK_GAP = 320
ROW_GAP = 154
GROUP_GAP = 18

EDGE_COLORS = {
    "traffic": "#2c5967",
    "data": "#5f7f3f",
    "events": "#9a6634",
    "admin": "#6f5aa7",
    "security": "#a24b42",
    "observability": "#4f7d90",
    "service": "#4f6678",
}

GENERIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect x="10" y="14" width="80" height="68" rx="12" fill="#fff7f4" stroke="#c74634" stroke-width="6"/>
  <path d="M26 36h48M26 51h48M26 66h30" fill="none" stroke="#312d2a" stroke-width="7" stroke-linecap="round"/>
  <circle cx="72" cy="66" r="7" fill="#2c5967"/>
</svg>
"""

CLEAN_ICON_SVGS: dict[str, tuple[str, str]] = {
    "dns": (
        "0 0 100 100",
        '<path d="M50 13 82 31v38L50 87 18 69V31z"/>'
        '<line x1="50" y1="21" x2="50" y2="79" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="26" y1="36" x2="74" y2="64" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="74" y1="36" x2="26" y2="64" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>',
    ),
    "waf": (
        "0 0 100 100",
        '<path d="M50 10 82 23v22c0 22-12 36-32 45-20-9-32-23-32-45V23z"/>'
        '<line x1="34" y1="42" x2="66" y2="42" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>'
        '<line x1="34" y1="58" x2="60" y2="58" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>',
    ),
    "load-balancer-primary": (
        "0 0 100 100",
        '<path d="M18 50h28"/>'
        '<path d="M46 28v44l36-22z"/>'
        '<line x1="55" y1="30" x2="79" y2="18" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>'
        '<line x1="55" y1="70" x2="79" y2="82" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>',
    ),
    "container-engine-for-kubernetes": (
        "0 0 100 100",
        '<path d="M50 12 82 30v40L50 88 18 70V30z"/>'
        '<rect x="34" y="30" width="14" height="14" rx="2"/>'
        '<rect x="53" y="30" width="14" height="14" rx="2"/>'
        '<rect x="34" y="55" width="14" height="14" rx="2"/>'
        '<rect x="53" y="55" width="14" height="14" rx="2"/>',
    ),
    "oracle-autonomous-database": (
        "0 0 100 100",
        '<path d="M22 30c0-10 56-10 56 0v40c0 10-56 10-56 0z"/>'
        '<path d="M22 30c0 10 56 10 56 0" fill="none" stroke="#16343d" stroke-width="7"/>'
        '<path d="M22 51c0 10 56 10 56 0" fill="none" stroke="#16343d" stroke-width="7"/>',
    ),
    "object-storage": (
        "0 0 100 100",
        '<path d="M20 32 50 17l30 15v36L50 83 20 68z"/>'
        '<line x1="20" y1="32" x2="50" y2="47" stroke="#16343d" stroke-width="7"/>'
        '<line x1="80" y1="32" x2="50" y2="47" stroke="#16343d" stroke-width="7"/>'
        '<line x1="50" y1="47" x2="50" y2="83" stroke="#16343d" stroke-width="7"/>',
    ),
    "bastion": (
        "0 0 100 100",
        '<path d="M30 20h40v18h-8v42H38V38h-8z"/>'
        '<line x1="38" y1="38" x2="62" y2="38" stroke="#16343d" stroke-width="7"/>'
        '<line x1="43" y1="55" x2="57" y2="55" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>',
    ),
    "vault": (
        "0 0 100 100",
        '<rect x="20" y="38" width="60" height="42" rx="8"/>'
        '<path d="M34 38V27c0-19 32-19 32 0v11" fill="none" stroke="#16343d" stroke-width="9" stroke-linecap="round"/>'
        '<circle cx="50" cy="58" r="7" fill="#16343d"/>',
    ),
    "logging": (
        "0 0 100 100",
        '<path d="M25 14h42l12 12v60H25z"/>'
        '<line x1="36" y1="42" x2="64" y2="42" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="36" y1="58" x2="64" y2="58" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="36" y1="74" x2="55" y2="74" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>',
    ),
    "monitoring": (
        "0 0 100 100",
        '<rect x="18" y="22" width="64" height="50" rx="6"/>'
        '<path d="M28 58h12l8-18 10 28 8-18h8" fill="none" stroke="#16343d" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="38" y1="83" x2="62" y2="83" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>',
    ),
    "functions": (
        "0 0 100 100",
        '<rect x="18" y="22" width="64" height="56" rx="8"/>'
        '<path d="M42 34 30 50l12 16" fill="none" stroke="#16343d" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M58 34 70 50 58 66" fill="none" stroke="#16343d" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>',
    ),
    "streaming": (
        "0 0 100 100",
        '<rect x="20" y="18" width="60" height="64" rx="8"/>'
        '<circle cx="40" cy="36" r="6" fill="#16343d"/>'
        '<circle cx="40" cy="50" r="6" fill="#16343d"/>'
        '<circle cx="40" cy="64" r="6" fill="#16343d"/>'
        '<line x1="53" y1="36" x2="65" y2="36" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="53" y1="50" x2="65" y2="50" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="53" y1="64" x2="65" y2="64" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>',
    ),
    "oci-queue": (
        "0 0 100 100",
        '<rect x="18" y="24" width="64" height="52" rx="8"/>'
        '<line x1="31" y1="39" x2="69" y2="39" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="31" y1="52" x2="62" y2="52" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>'
        '<line x1="31" y1="65" x2="55" y2="65" stroke="#16343d" stroke-width="7" stroke-linecap="round"/>',
    ),
    "service-gateway": (
        "0 0 100 100",
        '<path d="M18 50 38 30h24l20 20-20 20H38z"/>'
        '<line x1="32" y1="50" x2="68" y2="50" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>'
        '<line x1="56" y1="38" x2="68" y2="50" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>'
        '<line x1="56" y1="62" x2="68" y2="50" stroke="#16343d" stroke-width="8" stroke-linecap="round"/>',
    ),
}

FALLBACK_ALIASES = {
    "adb": "oracle-autonomous-database",
    "autonomous-database": "oracle-autonomous-database",
    "compute": "virtual-machine",
    "compute-instance": "virtual-machine",
    "database": "oracle-database",
    "db": "oracle-database",
    "igw": "internet-gateway",
    "instance": "virtual-machine",
    "k8s": "container-engine-for-kubernetes",
    "kubernetes": "container-engine-for-kubernetes",
    "lb": "load-balancer-primary",
    "load-balancer": "load-balancer-primary",
    "object-storage": "object-storage",
    "oke": "container-engine-for-kubernetes",
    "storage": "object-storage",
    "vcn": "virtual-cloud-network",
    "vm": "virtual-machine",
}

SERVICE_ROLE_DESCRIPTIONS = {
    "api-gateway": "Publica endpoints controlados para que los clientes consuman la aplicacion.",
    "bastion": "Permite acceso administrativo temporal y auditado a recursos privados.",
    "container-engine-for-kubernetes": "Ejecuta los microservicios o pods de aplicacion en la subred privada.",
    "dns": "Resuelve el nombre publico y envia las solicitudes hacia el punto de entrada.",
    "email-delivery": "Envia correos transaccionales desde la aplicacion sin exponer la red privada.",
    "functions": "Ejecuta logica puntual y asincrona sin administrar servidores.",
    "internet-gateway": "Permite entrada o salida publica controlada para recursos en subred publica.",
    "load-balancer-primary": "Distribuye trafico entre la capa de aplicacion y mantiene un punto de entrada estable.",
    "logging": "Centraliza logs para auditoria, diagnostico y trazabilidad operativa.",
    "monitoring": "Recolecta metricas y senales de salud para alertas y observabilidad.",
    "nat-gateway": "Permite salida a internet desde subredes privadas sin recibir trafico entrante.",
    "object-storage": "Almacena objetos, archivos estaticos, documentos o respaldos usados por la solucion.",
    "oci-queue": "Desacopla trabajos asincronos para absorber picos y reintentos.",
    "open-search": "Indexa y consulta contenido para busqueda o recuperacion de informacion.",
    "oracle-autonomous-database": "Guarda datos transaccionales o vectoriales administrados por la plataforma.",
    "oracle-database": "Persiste datos criticos de negocio para la aplicacion.",
    "oracle-cloud-infrastructure-registry": "Almacena imagenes de contenedor usadas por la plataforma de ejecucion.",
    "oracle-cloud-infrastructure-vault": "Protege secretos, claves y material criptografico.",
    "service-gateway": "Conecta recursos privados con servicios OCI sin usar internet publico.",
    "streaming": "Transporta eventos en tiempo real entre productores y consumidores.",
    "vault": "Protege secretos, claves y material criptografico.",
    "virtual-cloud-network": "Aisla la red de la arquitectura y contiene subredes, rutas y controles.",
    "virtual-machine": "Ejecuta cargas de trabajo o componentes de aplicacion sobre compute.",
    "waf": "Filtra trafico HTTP/S malicioso antes de llegar al balanceador.",
}


class DiagramError(ValueError):
    """Raised when the diagram spec cannot be rendered."""


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return re.sub(r"-+", "-", slug) or "unknown"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiagramError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DiagramError("Diagram spec must be a JSON object.")
    return data


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"services": {}, "aliases": {}, "warnings": [f"Catalog not found: {path}"]}
    data = read_json(path)
    data.setdefault("services", {})
    data.setdefault("aliases", {})
    return data


def normalize_service(service: str, catalog: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    key = slugify(service)
    services = catalog.get("services", {})
    aliases = {**FALLBACK_ALIASES, **catalog.get("aliases", {})}
    target = aliases.get(key, key)
    if target in services:
        return target, services[target]
    for slug, item in services.items():
        names = {slug, slugify(str(item.get("name", "")))}
        if key in names:
            return slug, item
    return "generic", None


def validate_spec(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    nodes = spec.get("nodes")
    edges = spec.get("edges", [])
    groups = spec.get("groups", [])
    warnings: list[str] = []

    if not isinstance(nodes, list) or not nodes:
        raise DiagramError("Spec must include a non-empty nodes[] array.")
    if not isinstance(edges, list):
        raise DiagramError("edges must be an array.")
    if not isinstance(groups, list):
        raise DiagramError("groups must be an array.")

    node_ids: set[str] = set()
    normalized_nodes: list[dict[str, Any]] = []
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise DiagramError(f"nodes[{idx}] must be an object.")
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            raise DiagramError(f"nodes[{idx}] is missing id.")
        if node_id in node_ids:
            raise DiagramError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)
        label = str(node.get("label", node_id)).strip() or node_id
        service = str(node.get("service", label)).strip() or label
        group = str(node.get("group", "")).strip()
        normalized_nodes.append({**node, "id": node_id, "label": label, "service": service, "group": group})

    normalized_edges: list[dict[str, Any]] = []
    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise DiagramError(f"edges[{idx}] must be an object.")
        source = str(edge.get("from", "")).strip()
        target = str(edge.get("to", "")).strip()
        if source not in node_ids:
            raise DiagramError(f"edges[{idx}] references missing source node: {source}")
        if target not in node_ids:
            raise DiagramError(f"edges[{idx}] references missing target node: {target}")
        normalized_edges.append({**edge, "from": source, "to": target, "label": str(edge.get("label", "")).strip()})

    group_ids: set[str] = set()
    normalized_groups: list[dict[str, Any]] = []
    for idx, group in enumerate(groups):
        if not isinstance(group, dict):
            raise DiagramError(f"groups[{idx}] must be an object.")
        group_id = str(group.get("id", "")).strip()
        if not group_id:
            raise DiagramError(f"groups[{idx}] is missing id.")
        if group_id in group_ids:
            raise DiagramError(f"Duplicate group id: {group_id}")
        group_ids.add(group_id)
        normalized_groups.append(
            {
                **group,
                "id": group_id,
                "label": str(group.get("label", group_id)).strip() or group_id,
                "type": str(group.get("type", "group")).strip() or "group",
                "parent": str(group.get("parent", "")).strip(),
            }
        )

    for node in normalized_nodes:
        group_id = node.get("group", "")
        if group_id and group_id not in group_ids:
            warnings.append(f"Node {node['id']} references group {group_id}; creating an implicit group.")
            group_ids.add(group_id)
            normalized_groups.append({"id": group_id, "label": group_id, "type": "group", "parent": ""})

    return normalized_nodes, normalized_edges, normalized_groups, warnings


def compute_ranks(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    ranks = {node["id"]: 0 for node in nodes}
    for _ in range(max(len(nodes), 1)):
        changed = False
        for edge in edges:
            source = edge["from"]
            target = edge["to"]
            proposed = ranks[source] + 1
            if proposed > ranks[target]:
                ranks[target] = proposed
                changed = True
        if not changed:
            break
    max_rank = max(ranks.values() or [0])
    return {node_id: min(rank, max_rank) for node_id, rank in ranks.items()}


def layout_nodes(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    ranks = compute_ranks(nodes, edges)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for node in nodes:
        grouped.setdefault(ranks[node["id"]], []).append(node)

    positions: dict[str, tuple[float, float]] = {}
    for rank in sorted(grouped):
        rank_nodes = sorted(grouped[rank], key=lambda item: (str(item.get("group", "")), item["label"], item["id"]))
        for index, node in enumerate(rank_nodes):
            positions[node["id"]] = (MARGIN_X + rank * RANK_GAP, MARGIN_Y + index * ROW_GAP)
    return positions


def resolve_group_overlaps(
    groups: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    positions: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    if not groups:
        return positions

    adjusted = dict(positions)
    children: dict[str, list[str]] = {"": []}
    for group in groups:
        parent = str(group.get("parent", ""))
        children.setdefault(parent, []).append(group["id"])
        children.setdefault(group["id"], [])
    order = {group["id"]: index for index, group in enumerate(groups)}

    descendant_cache: dict[str, set[str]] = {}

    def descendants(group_id: str) -> set[str]:
        if group_id in descendant_cache:
            return descendant_cache[group_id]
        found = {group_id}
        for child_id in children.get(group_id, []):
            found.update(descendants(child_id))
        descendant_cache[group_id] = found
        return found

    node_groups = {node["id"]: node.get("group", "") for node in nodes}

    def shift_group(group_id: str, dy: float) -> None:
        affected = descendants(group_id)
        for node_id, group_id_for_node in node_groups.items():
            if group_id_for_node in affected:
                x, y = adjusted[node_id]
                adjusted[node_id] = (x, y + dy)

    def sibling_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return (
            first[0] < second[2] + GROUP_GAP
            and first[2] > second[0] - GROUP_GAP
            and first[1] < second[3] + GROUP_GAP
            and first[3] > second[1] - GROUP_GAP
        )

    for _ in range(max(1, len(groups) * 3)):
        moved = False
        bounds = group_bounds(groups, nodes, adjusted)
        for sibling_ids in children.values():
            present = [group_id for group_id in sibling_ids if group_id in bounds]
            present.sort(key=lambda group_id: (bounds[group_id][1], order.get(group_id, 0)))
            placed: list[str] = []
            for group_id in present:
                current = bounds[group_id]
                dy = 0.0
                for placed_id in placed:
                    previous = bounds[placed_id]
                    shifted = (current[0], current[1] + dy, current[2], current[3] + dy)
                    if sibling_overlap(shifted, previous):
                        dy = max(dy, previous[3] + GROUP_GAP - current[1])
                if dy > 0.5:
                    shift_group(group_id, dy)
                    current = (current[0], current[1] + dy, current[2], current[3] + dy)
                    bounds[group_id] = current
                    moved = True
                placed.append(group_id)
        if not moved:
            break
    return adjusted


def normalize_canvas_origin(
    groups: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    positions: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    boxes = [(x, y, x + NODE_W, y + NODE_H) for x, y in positions.values()]
    boxes.extend(group_bounds(groups, nodes, positions).values())
    if not boxes:
        return positions
    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    dx = max(0.0, 24.0 - min_x)
    dy = max(0.0, 34.0 - min_y)
    if dx == 0 and dy == 0:
        return positions
    return {node_id: (x + dx, y + dy) for node_id, (x, y) in positions.items()}


def port_offsets(edges: list[dict[str, Any]], positions: dict[str, tuple[float, float]]) -> dict[int, tuple[float, float]]:
    outgoing: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    incoming: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, edge in enumerate(edges):
        outgoing.setdefault(edge["from"], []).append((index, edge))
        incoming.setdefault(edge["to"], []).append((index, edge))

    def offset_for(index: int, count: int) -> float:
        if count <= 1:
            return 0.0
        span = min(NODE_H * 0.58, 16 * (count - 1))
        return -span / 2 + (span / (count - 1)) * index

    offsets: dict[int, list[float]] = {index: [0.0, 0.0] for index in range(len(edges))}
    for source, source_edges in outgoing.items():
        source_edges.sort(key=lambda item: (positions[item[1]["to"]][1], positions[item[1]["to"]][0], item[1]["to"]))
        for order, (index, _) in enumerate(source_edges):
            offsets[index][0] = offset_for(order, len(source_edges))

    for target, target_edges in incoming.items():
        target_edges.sort(key=lambda item: (positions[item[1]["from"]][1], positions[item[1]["from"]][0], item[1]["from"]))
        for order, (index, _) in enumerate(target_edges):
            offsets[index][1] = offset_for(order, len(target_edges))

    return {index: (values[0], values[1]) for index, values in offsets.items()}


def group_depth(group_id: str, groups_by_id: dict[str, dict[str, Any]]) -> int:
    depth = 0
    seen: set[str] = set()
    current = groups_by_id.get(group_id, {}).get("parent", "")
    while current and current in groups_by_id and current not in seen:
        seen.add(current)
        depth += 1
        current = groups_by_id[current].get("parent", "")
    return depth


def group_bounds(
    groups: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    positions: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    groups_by_id = {group["id"]: group for group in groups}
    children: dict[str, list[str]] = {}
    for group in groups:
        parent = group.get("parent", "")
        if parent:
            children.setdefault(parent, []).append(group["id"])

    direct_nodes: dict[str, list[str]] = {}
    for node in nodes:
        if node.get("group"):
            direct_nodes.setdefault(node["group"], []).append(node["id"])

    cache: dict[str, tuple[float, float, float, float]] = {}

    def bounds_for(group_id: str) -> tuple[float, float, float, float] | None:
        if group_id in cache:
            return cache[group_id]
        boxes: list[tuple[float, float, float, float]] = []
        for node_id in direct_nodes.get(group_id, []):
            x, y = positions[node_id]
            boxes.append((x, y, x + NODE_W, y + NODE_H))
        for child_id in children.get(group_id, []):
            child = bounds_for(child_id)
            if child:
                boxes.append(child)
        if not boxes:
            return None
        depth = group_depth(group_id, groups_by_id)
        pad_x = 26 + max(0, 2 - depth) * 10
        pad_y = 48 + max(0, 2 - depth) * 8
        min_x = min(box[0] for box in boxes) - pad_x
        min_y = min(box[1] for box in boxes) - pad_y
        max_x = max(box[2] for box in boxes) + pad_x
        max_y = max(box[3] for box in boxes) + pad_y
        cache[group_id] = (min_x, min_y, max_x, max_y)
        return cache[group_id]

    for group in groups:
        bounds_for(group["id"])
    return cache


def extract_svg_inner(svg: str) -> tuple[str, str]:
    viewbox_match = re.search(r"viewBox=['\"]([^'\"]+)['\"]", svg)
    body_match = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.IGNORECASE | re.DOTALL)
    viewbox = viewbox_match.group(1) if viewbox_match else "0 0 100 100"
    body = body_match.group(1).strip() if body_match else GENERIC_SVG
    body = "\n".join(line.rstrip() for line in body.splitlines())
    return viewbox, body


def icon_for_service(slug: str, service: dict[str, Any] | None, catalog_path: Path) -> tuple[str, str]:
    if service:
        icon_file = catalog_path.parent / str(service.get("file", ""))
        if icon_file.exists():
            if service.get("iconSource") != "local-svg" and slug in CLEAN_ICON_SVGS:
                return CLEAN_ICON_SVGS[slug]
            return extract_svg_inner(icon_file.read_text(encoding="utf-8"))
    if slug in CLEAN_ICON_SVGS:
        return CLEAN_ICON_SVGS[slug]
    return extract_svg_inner(GENERIC_SVG)


def wrap_label(text: str, width: int = 20, max_lines: int = 3) -> list[str]:
    lines = textwrap.wrap(text, width=width, break_long_words=False) or [text]
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [lines[max_lines - 1][: width - 1].rstrip() + "..."]
    return lines


def render_node(
    node: dict[str, Any],
    x: float,
    y: float,
    catalog: dict[str, Any],
    catalog_path: Path,
    warnings: list[str],
    used_services: dict[str, str],
) -> str:
    slug, service = normalize_service(node["service"], catalog)
    if service is None:
        warnings.append(f"Unknown OCI service '{node['service']}' on node {node['id']}; using generic icon.")
        service_name = node["service"]
    else:
        service_name = str(service.get("name", node["service"]))
    used_services[slug] = service_name
    viewbox, body = icon_for_service(slug, service, catalog_path)
    service_lines = wrap_label(service_name, width=24, max_lines=2)
    service_markup = []
    for idx, line in enumerate(service_lines):
        service_markup.append(
            f'<tspan x="{fmt(NODE_W / 2)}" dy="{0 if idx == 0 else 12}">{html.escape(line)}</tspan>'
        )

    return f"""
    <g class="node" id="node-{html.escape(node['id'])}" transform="translate({fmt(x)} {fmt(y)})">
      <rect class="node-card" width="{NODE_W}" height="{NODE_H}" rx="8"/>
      <svg class="node-icon" x="{fmt((NODE_W - ICON_SIZE) / 2)}" y="21" width="{ICON_SIZE}" height="{ICON_SIZE}" viewBox="{html.escape(viewbox)}" preserveAspectRatio="xMidYMid meet">
        {body}
      </svg>
      <text class="node-service-name" text-anchor="middle" x="{fmt(NODE_W / 2)}" y="89">{"".join(service_markup)}</text>
    </g>
"""


def fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def cubic_point(
    t: float,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[float, float]:
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return x, y


def edge_path(
    source: tuple[float, float],
    target: tuple[float, float],
    source_offset: float = 0.0,
    target_offset: float = 0.0,
) -> tuple[str, float, float]:
    sx, sy = source[0] + NODE_W, source[1] + NODE_H / 2 + source_offset
    tx, ty = target[0], target[1] + NODE_H / 2 + target_offset
    dx = tx - sx
    if tx >= sx:
        bend = min(92, max(46, dx * 0.36))
        p0 = (sx, sy)
        p1 = (sx + bend, sy)
        p2 = (tx - bend, ty)
        p3 = (tx, ty)
    else:
        bend = max(48, abs(dx) * 0.42)
        p0 = (sx, sy)
        p1 = (sx + bend, sy)
        p2 = (tx + bend, ty)
        p3 = (tx, ty)
    path = (
        f"M {fmt(p0[0])} {fmt(p0[1])} "
        f"C {fmt(p1[0])} {fmt(p1[1])}, {fmt(p2[0])} {fmt(p2[1])}, {fmt(p3[0])} {fmt(p3[1])}"
    )
    lx, ly = cubic_point(0.5, p0, p1, p2, p3)
    return path, lx, ly


def edge_label_width(label: str) -> float:
    return max(30, min(98, len(label) * 4.9 + 12))


def edge_kind(label: str) -> str:
    key = slugify(label)
    if key in {"dns", "https", "invoke"}:
        return "traffic"
    if key in {"sql", "object-api", "private-oci-apis"}:
        return "data"
    if "event" in key or "async" in key or "order" in key:
        return "events"
    if key == "admin":
        return "admin"
    if key == "secrets":
        return "security"
    if key in {"logs", "metrics"}:
        return "observability"
    return "service"


def group_label_width(label: str) -> float:
    return max(72, min(190, len(label) * 7.0 + 22))


def edge_label_box(label: str, x: float, y: float) -> tuple[float, float, float, float]:
    width = edge_label_width(label)
    return (x - width / 2, y - 11, x + width / 2, y + 6)


def intersects(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    pad: float = 0,
) -> bool:
    return (
        first[0] < second[2] + pad
        and first[2] > second[0] - pad
        and first[1] < second[3] + pad
        and first[3] > second[1] - pad
    )


def adjust_edge_label_position(
    label: str,
    x: float,
    y: float,
    node_boxes: list[tuple[float, float, float, float]],
    label_boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, tuple[float, float, float, float]]:
    offsets = [0, -20, 20, -40, 40, -64, 64, -88, 88, -116, 116, -144, 144]
    x_offsets = [0, -36, 36, -72, 72, -112, 112, -148, 148]
    for dx in x_offsets:
        for dy in offsets:
            candidate_x = x + dx
            candidate_y = max(42, y + dy)
            candidate = edge_label_box(label, candidate_x, candidate_y)
            if any(intersects(candidate, node, pad=8) for node in node_boxes):
                continue
            if any(intersects(candidate, other, pad=6) for other in label_boxes):
                continue
            return candidate_x, candidate_y, candidate
    for dx in range(-240, 241, 40):
        for dy in range(-176, 177, 22):
            candidate_x = x + dx
            candidate_y = max(42, y + dy)
            candidate = edge_label_box(label, candidate_x, candidate_y)
            if any(intersects(candidate, node, pad=8) for node in node_boxes):
                continue
            return candidate_x, candidate_y, candidate
    fallback_y = max(42, y - 196)
    return x, fallback_y, edge_label_box(label, x, fallback_y)


def render_edge_label(label: str, x: float, y: float, kind: str) -> str:
    safe_label = html.escape(label)
    width = edge_label_width(label)
    return (
        f'<g class="edge-label edge-label-{html.escape(kind)}" transform="translate({fmt(x)} {fmt(y)})">'
        f'<rect x="{fmt(-width / 2)}" y="-11" width="{fmt(width)}" height="17" rx="4"/>'
        f'<text text-anchor="middle" y="1">{safe_label}</text>'
        f"</g>"
    )


def render_svg(spec: dict[str, Any], catalog: dict[str, Any], catalog_path: Path) -> tuple[str, list[str], dict[str, str]]:
    nodes, edges, groups, warnings = validate_spec(spec)
    positions = layout_nodes(nodes, edges)
    positions = resolve_group_overlaps(groups, nodes, positions)
    positions = normalize_canvas_origin(groups, nodes, positions)
    bounds = group_bounds(groups, nodes, positions)
    groups_by_id = {group["id"]: group for group in groups}

    max_x = max((x + NODE_W for x, _ in positions.values()), default=500)
    max_y = max((y + NODE_H for _, y in positions.values()), default=350)
    if bounds:
        max_x = max(max_x, max(box[2] for box in bounds.values()))
        max_y = max(max_y, max(box[3] for box in bounds.values()))
    width = max(860, math.ceil(max_x + MARGIN_X))
    height = max(520, math.ceil(max_y + MARGIN_Y))

    group_markup: list[str] = []
    group_label_markup: list[str] = []
    palette = {
        "region": ("#f4f5f6", "#aeb7c1"),
        "vcn": ("#eef1f3", "#55727e"),
        "subnet": ("#e4e8eb", "#657484"),
        "availability-domain": ("#ece9e3", "#8a6f3d"),
        "group": ("#e4e8eb", "#657484"),
    }
    for group_id, box in sorted(bounds.items(), key=lambda item: group_depth(item[0], groups_by_id)):
        group = groups_by_id[group_id]
        fill, stroke = palette.get(str(group.get("type", "group")), palette["group"])
        x1, y1, x2, y2 = box
        label = str(group["label"])
        label_width = min(group_label_width(label), max(72, x2 - x1 - 24))
        group_type = str(group.get("type", "group")).lower()
        if group_type != "vcn":
            group_markup.append(
                f'<g class="diagram-group depth-{group_depth(group_id, groups_by_id)}" data-group-id="{html.escape(group_id)}">'
                f'<rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" '
                f'rx="8" fill="{fill}" stroke="{stroke}"/>'
                f"</g>"
            )
            group_label_markup.append(
                f'<g class="diagram-group-label depth-{group_depth(group_id, groups_by_id)}" data-group-id="{html.escape(group_id)}">'
                f'<rect x="{fmt(x1 + 12)}" y="{fmt(y1 + 9)}" width="{fmt(label_width)}" height="22" rx="5"/>'
                f'<text x="{fmt(x1 + 23)}" y="{fmt(y1 + 24)}">{html.escape(label)}</text>'
                f"</g>"
            )

    edge_markup: list[str] = []
    edge_offsets = port_offsets(edges, positions)
    node_boxes = [(x, y, x + NODE_W, y + NODE_H) for x, y in positions.values()]
    label_boxes: list[tuple[float, float, float, float]] = []
    for index, edge in enumerate(edges):
        source_offset, target_offset = edge_offsets[index]
        path, lx, ly = edge_path(positions[edge["from"]], positions[edge["to"]], source_offset, target_offset)
        label = edge.get("label", "")
        kind = edge_kind(label)
        edge_markup.append(f'<path class="edge edge-{html.escape(kind)}" d="{path}" marker-end="url(#arrow-{html.escape(kind)})"/>')
        if label:
            lx, ly, label_box = adjust_edge_label_position(label, lx, ly, node_boxes, label_boxes)
            label_boxes.append(label_box)
            edge_markup.append(render_edge_label(label, lx, ly, kind))

    used_services: dict[str, str] = {}
    node_markup = [
        render_node(node, *positions[node["id"]], catalog, catalog_path, warnings, used_services) for node in nodes
    ]

    title = html.escape(str(spec.get("title", "OCI Architecture Diagram")))
    marker_markup = "\n".join(
        f"""    <marker id="arrow-{kind}" viewBox="0 0 10 10" refX="8.4" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 1.5 1.5 L 8.5 5 L 1.5 8.5 z" fill="{color}"/>
    </marker>"""
        for kind, color in EDGE_COLORS.items()
    )
    svg = f"""
<svg class="diagram" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="diagram-title">
  <title id="diagram-title">{title}</title>
  <defs>
{marker_markup}
  </defs>
  <rect class="canvas" x="0" y="0" width="{width}" height="{height}"/>
  <g class="groups">
    {"".join(group_markup)}
  </g>
  <g class="edges">
    {"".join(edge_markup)}
  </g>
  <g class="group-labels">
    {"".join(group_label_markup)}
  </g>
  <g class="nodes">
    {"".join(node_markup)}
  </g>
</svg>
"""
    return svg, warnings, used_services


def service_role_description(slug: str, label: str, service_name: str) -> str:
    description = SERVICE_ROLE_DESCRIPTIONS.get(slug)
    if description:
        return description
    if label and label != service_name:
        return f"Soporta el componente {label} dentro del flujo definido para esta arquitectura."
    return "Cumple una funcion de apoyo dentro del flujo definido para esta arquitectura."


def render_service_inventory(spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    nodes, _edges, groups, _warnings = validate_spec(spec)
    groups_by_id = {group["id"]: group for group in groups}
    rows: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for node in nodes:
        slug, service = normalize_service(node["service"], catalog)
        service_name = str(service.get("name", node["service"])) if service else str(node["service"])
        label = str(node.get("label", service_name))
        group_label = str(groups_by_id.get(str(node.get("group", "")), {}).get("label", ""))
        key = (slug, service_name, label)
        if key in seen:
            continue
        seen.add(key)
        context = label if label == service_name else f"{label} - {group_label}" if group_label else label
        rows.append(
            f"""
        <tr>
          <td><span class="service-name">{html.escape(service_name)}</span></td>
          <td><span class="service-context">{html.escape(context)}</span></td>
          <td><p class="service-role">{html.escape(service_role_description(slug, label, service_name))}</p></td>
        </tr>"""
        )

    if not rows:
        return ""
    return f"""
    <section class="service-inventory" aria-label="Architecture services">
      <h2>Architecture Services</h2>
      <div class="service-table-wrap">
        <table class="service-table">
          <thead>
            <tr>
              <th scope="col">Service</th>
              <th scope="col">Component</th>
              <th scope="col">Role</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def render_html(spec: dict[str, Any], catalog: dict[str, Any], catalog_path: Path) -> str:
    svg, warnings, _used_services = render_svg(spec, catalog, catalog_path)
    title = str(spec.get("title", "OCI Architecture Diagram"))
    service_inventory = render_service_inventory(spec, catalog)
    warning_markup = ""
    if warnings:
        warning_markup = "<aside class=\"warnings\"><strong>Warnings</strong><ul>" + "".join(
            f"<li>{html.escape(warning)}</li>" for warning in warnings
        ) + "</ul></aside>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #312d2a;
      --muted: #5c6f82;
      --line: #d7dde4;
      --oci: #c74634;
      --teal: #2c5967;
      --page: #f6f7f8;
      --card: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--page);
      scrollbar-color: #8ea0aa #eef2f5;
      scrollbar-width: thin;
    }}
    body::-webkit-scrollbar,
    .diagram-wrap::-webkit-scrollbar,
    .service-table-wrap::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    body::-webkit-scrollbar-track,
    .diagram-wrap::-webkit-scrollbar-track,
    .service-table-wrap::-webkit-scrollbar-track {{
      background: #eef2f5;
    }}
    body::-webkit-scrollbar-thumb,
    .diagram-wrap::-webkit-scrollbar-thumb,
    .service-table-wrap::-webkit-scrollbar-thumb {{
      border: 1px solid #eef2f5;
      border-radius: 999px;
      background: #8ea0aa;
    }}
    body::-webkit-scrollbar-thumb:hover,
    .diagram-wrap::-webkit-scrollbar-thumb:hover,
    .service-table-wrap::-webkit-scrollbar-thumb:hover {{
      background: #6f7f8b;
    }}
    main {{
      min-width: 920px;
      padding: 28px;
    }}
    header {{
      margin: 0 0 18px;
    }}
    body.embedded main {{
      padding: 18px 28px 28px;
    }}
    body.embedded main > header {{
      display: none;
    }}
    h1 {{
      margin: 0;
      font-size: 26px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .diagram-shell {{
      position: relative;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .diagram-toolbar {{
      position: absolute;
      right: 12px;
      bottom: 32px;
      z-index: 8;
      display: inline-flex;
      flex-direction: column;
      gap: 3px;
      align-items: center;
      width: max-content;
      padding: 0;
      border: 0;
      background: transparent;
      box-shadow: none;
    }}
    .diagram-toolbar button,
    .zoom-percent {{
      width: 34px;
      height: 26px;
      border: 1px solid #c9d1d9;
      border-radius: 3px;
      background: rgba(255, 255, 255, 0.94);
      color: var(--ink);
      font: 700 11px/1 Arial, Helvetica, sans-serif;
      box-shadow: 0 2px 5px rgba(49, 45, 42, 0.10);
    }}
    .diagram-toolbar button {{
      cursor: pointer;
    }}
    .zoom-percent {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #405366;
      font-size: 10px;
      letter-spacing: 0;
    }}
    .diagram-toolbar button:hover {{
      border-color: var(--teal);
      color: var(--teal);
    }}
    .diagram-wrap {{
      position: relative;
      overflow: auto;
      background: #fff;
      cursor: grab;
      max-height: calc(100vh - 150px);
      padding-bottom: 16px;
      scrollbar-color: #8ea0aa transparent;
      scrollbar-width: thin;
    }}
    .diagram-wrap::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .diagram-wrap::-webkit-scrollbar-thumb {{
      border-color: transparent;
    }}
    .diagram-wrap.is-panning {{
      cursor: grabbing;
      user-select: none;
    }}
    .diagram-stage {{
      transform-origin: 0 0;
      width: max-content;
      height: max-content;
    }}
    .diagram {{
      display: block;
      width: auto;
      max-width: none;
      min-width: 0;
      height: auto;
      transform-origin: 0 0;
    }}
    .canvas {{
      fill: #ffffff;
    }}
    .diagram-group rect {{
      stroke-width: 1.5;
      stroke-dasharray: 0;
    }}
    .diagram-group.depth-1 rect,
    .diagram-group.depth-2 rect {{
      fill-opacity: 1;
    }}
    .diagram-group-label rect {{
      fill: rgba(255, 255, 255, 0.94);
      stroke: #d7dde4;
      stroke-width: 1;
    }}
    .diagram-group-label text {{
      font-size: 12px;
      font-weight: 700;
      fill: var(--ink);
    }}
    .edge {{
      fill: none;
      stroke: var(--muted);
      stroke-width: 1.65;
      stroke-linecap: round;
      opacity: 0.9;
    }}
    .edge-traffic {{ stroke: #2c5967; }}
    .edge-data {{ stroke: #5f7f3f; }}
    .edge-events {{ stroke: #9a6634; }}
    .edge-admin {{ stroke: #6f5aa7; }}
    .edge-security {{ stroke: #a24b42; }}
    .edge-observability {{ stroke: #4f7d90; }}
    .edge-service {{ stroke: #4f6678; }}
    .edge-label {{
      pointer-events: none;
    }}
    .edge-label rect {{
      fill: rgba(255, 255, 255, 0.95);
      stroke: #c7d0da;
      stroke-width: 1;
    }}
    .edge-label text {{
      fill: var(--muted);
      font-size: 8.8px;
      font-weight: 700;
    }}
    .edge-label-traffic rect {{ stroke: #93b6bd; fill: #f1f9fa; }}
    .edge-label-data rect {{ stroke: #b3c99d; fill: #f6fbf1; }}
    .edge-label-events rect {{ stroke: #d2b18e; fill: #fff8f0; }}
    .edge-label-admin rect {{ stroke: #c0b7df; fill: #f7f5ff; }}
    .edge-label-security rect {{ stroke: #d6aaa5; fill: #fff5f3; }}
    .edge-label-observability rect {{ stroke: #a6c6d1; fill: #f2f9fb; }}
    .edge-label-traffic text {{ fill: #2c5967; }}
    .edge-label-data text {{ fill: #557537; }}
    .edge-label-events text {{ fill: #865825; }}
    .edge-label-admin text {{ fill: #5f4f98; }}
    .edge-label-security text {{ fill: #8f3f37; }}
    .edge-label-observability text {{ fill: #426f82; }}
    .node-card {{
      fill: var(--card);
      stroke: #c9d1d9;
      stroke-width: 1.2;
      filter: drop-shadow(0 2px 5px rgba(49, 45, 42, 0.10));
    }}
    .node-icon {{
      overflow: visible;
    }}
    .node-icon path,
    .node-icon polygon,
    .node-icon rect,
    .node-icon circle,
    .node-icon line,
    .node-icon polyline {{
      vector-effect: non-scaling-stroke;
    }}
    .node-service-name {{
      fill: var(--ink);
      font-size: 11.4px;
      font-weight: 700;
    }}
    .service-inventory {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .service-inventory h2 {{
      margin: 0 0 8px;
      font-size: 15px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .service-table-wrap {{
      overflow-x: auto;
      border: 1px solid #d7dde4;
      background: #fff;
    }}
    .service-table {{
      width: 100%;
      min-width: 760px;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    .service-table th {{
      padding: 9px 12px;
      border-bottom: 1px solid #c9d1d9;
      background: #eef2f5;
      color: #405366;
      font-size: 11px;
      font-weight: 700;
      line-height: 1.25;
      text-align: left;
      text-transform: uppercase;
    }}
    .service-table td {{
      padding: 11px 12px;
      border-bottom: 1px solid #e5e9ee;
      vertical-align: top;
    }}
    .service-table tbody tr:nth-child(even) {{
      background: #f8fafb;
    }}
    .service-table tbody tr:last-child td {{
      border-bottom: 0;
    }}
    .service-table th:nth-child(1),
    .service-table td:nth-child(1) {{
      width: 24%;
    }}
    .service-table th:nth-child(2),
    .service-table td:nth-child(2) {{
      width: 26%;
    }}
    .service-name {{
      display: block;
      color: var(--ink);
      font-size: 12.8px;
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .service-context {{
      display: block;
      color: var(--muted);
      font-size: 11.4px;
      line-height: 1.3;
      overflow-wrap: anywhere;
    }}
    .service-role {{
      margin: 0;
      color: #405366;
      font-size: 12.2px;
      line-height: 1.4;
    }}
    .warnings {{
      margin-top: 14px;
      border-left: 4px solid var(--oci);
      background: #fff7f4;
      padding: 10px 14px;
      font-size: 13px;
    }}
    .warnings ul {{
      margin: 6px 0 0;
      padding-left: 18px;
    }}
    @media (max-width: 980px) {{
      main {{
        min-width: 0;
        padding: 18px;
      }}
      .diagram-wrap {{
        max-height: 62vh;
      }}
      .service-table {{
        min-width: 680px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(title)}</h1>
    </header>
    <section class="diagram-shell">
      <div class="diagram-wrap" tabindex="0">
        <div class="diagram-stage">
          {svg}
        </div>
      </div>
      <div class="diagram-toolbar" aria-label="Diagram navigation">
        <button type="button" data-diagram-action="zoom-out" title="Zoom out">-</button>
        <button type="button" data-diagram-action="zoom-in" title="Zoom in">+</button>
        <button type="button" class="zoom-percent" data-diagram-action="fit" title="Fit diagram" aria-live="polite">100%</button>
      </div>
    </section>
    {service_inventory}
    {warning_markup}
    <script type="application/json" id="diagram-spec">{html.escape(json.dumps(spec, ensure_ascii=False))}</script>
    <script>
      (() => {{
        if (new URLSearchParams(window.location.search).get("embed") === "1") {{
          document.body.classList.add("embedded");
        }}
        const wrap = document.querySelector(".diagram-wrap");
        const stage = document.querySelector(".diagram-stage");
        const svg = document.querySelector("svg.diagram");
        const zoomPercent = document.querySelector(".zoom-percent");
        if (!wrap || !stage || !svg) return;

        const naturalWidth = Number(svg.getAttribute("width")) || 1200;
        const naturalHeight = Number(svg.getAttribute("height")) || 800;
        let scale = 1;

        function applyScale(nextScale, anchor) {{
          const previous = scale;
          scale = Math.max(0.35, Math.min(2.5, nextScale));
          const anchorX = anchor ? anchor.x : wrap.clientWidth / 2;
          const anchorY = anchor ? anchor.y : wrap.clientHeight / 2;
          const ratioX = (wrap.scrollLeft + anchorX) / (naturalWidth * previous);
          const ratioY = (wrap.scrollTop + anchorY) / (naturalHeight * previous);
          stage.style.width = `${{naturalWidth * scale}}px`;
          stage.style.height = `${{naturalHeight * scale}}px`;
          svg.style.transform = `scale(${{scale}})`;
          if (zoomPercent) zoomPercent.textContent = `${{Math.round(scale * 100)}}%`;
          wrap.scrollLeft = ratioX * naturalWidth * scale - anchorX;
          wrap.scrollTop = ratioY * naturalHeight * scale - anchorY;
        }}

        function fitDiagram() {{
          const available = Math.max(320, wrap.clientWidth - 24);
          applyScale(Math.min(1, available / naturalWidth));
        }}

        const toolbar = document.querySelector(".diagram-toolbar");
        if (toolbar) {{
          toolbar.addEventListener("pointerdown", (event) => {{
            event.stopPropagation();
          }});
        }}

        document.querySelectorAll("[data-diagram-action]").forEach((button) => {{
          button.addEventListener("pointerdown", (event) => {{
            event.stopPropagation();
          }});
          button.addEventListener("click", (event) => {{
            event.preventDefault();
            event.stopPropagation();
            const action = button.getAttribute("data-diagram-action");
            if (action === "zoom-in") applyScale(scale * 1.15);
            if (action === "zoom-out") applyScale(scale / 1.15);
            if (action === "fit") fitDiagram();
          }});
        }});

        let dragging = false;
        let startX = 0;
        let startY = 0;
        let startLeft = 0;
        let startTop = 0;

        wrap.addEventListener("pointerdown", (event) => {{
          if (event.button !== 0) return;
          const target = event.target;
          if (target instanceof Element && target.closest(".diagram-toolbar")) return;
          dragging = true;
          startX = event.clientX;
          startY = event.clientY;
          startLeft = wrap.scrollLeft;
          startTop = wrap.scrollTop;
          wrap.classList.add("is-panning");
          wrap.setPointerCapture(event.pointerId);
        }});

        wrap.addEventListener("pointermove", (event) => {{
          if (!dragging) return;
          wrap.scrollLeft = startLeft - (event.clientX - startX);
          wrap.scrollTop = startTop - (event.clientY - startY);
        }});

        function stopDragging(event) {{
          dragging = false;
          wrap.classList.remove("is-panning");
          if (event && wrap.hasPointerCapture(event.pointerId)) {{
            wrap.releasePointerCapture(event.pointerId);
          }}
        }}

        wrap.addEventListener("pointerup", stopDragging);
        wrap.addEventListener("pointercancel", stopDragging);
        wrap.addEventListener("wheel", (event) => {{
          if (!event.ctrlKey) return;
          event.preventDefault();
          const rect = wrap.getBoundingClientRect();
          applyScale(scale * (event.deltaY < 0 ? 1.12 : 0.88), {{
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
          }});
        }}, {{ passive: false }});

        applyScale(1);
        requestAnimationFrame(fitDiagram);
      }})();
    </script>
  </main>
</body>
</html>
"""


def require_deck_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DiagramError(f"{path} must be a non-empty string.")
    return value.strip()


def optional_deck_list(value: Any, path: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise DiagramError(f"{path} must be an array of non-empty strings.")
    return [item.strip() for item in value]


def read_bom_detail(bom_path: Path, bom_tool: Path = DEFAULT_BOM_TOOL) -> dict[str, Any]:
    if not bom_tool.exists():
        raise DiagramError(f"Oracle BoM validator not found: {bom_tool}")
    try:
        completed = subprocess.run(
            ["node", str(bom_tool), "detail", str(bom_path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise DiagramError("Node.js is required to validate the Oracle Cost Estimator JSON.") from exc
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown Oracle BoM validation error"
        raise DiagramError(f"Oracle Cost Estimator JSON rejected: {detail}")
    try:
        detail = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DiagramError("Oracle BoM validator returned invalid JSON.") from exc
    if not isinstance(detail, dict) or not isinstance(detail.get("summary"), dict) or not isinstance(detail.get("items"), list):
        raise DiagramError("Oracle BoM validator returned an incomplete detail payload.")
    return detail


def validate_deck_spec(
    deck: dict[str, Any],
    architecture: dict[str, Any],
    bom_detail: dict[str, Any],
) -> list[dict[str, Any]]:
    if deck.get("version") != 1:
        raise DiagramError("Case deck version must be 1.")
    case = deck.get("case")
    if not isinstance(case, dict):
        raise DiagramError("Case deck requires a case object.")
    require_deck_string(case.get("summary"), "case.summary")
    require_deck_string(case.get("objective"), "case.objective")
    if case.get("description") is not None:
        require_deck_string(case.get("description"), "case.description")
    for key in ("scope", "assumptions", "openDecisions"):
        optional_deck_list(case.get(key), f"case.{key}")

    bom = deck.get("bom")
    if not isinstance(bom, dict):
        raise DiagramError("Case deck requires a bom object.")
    if bom.get("scenario") not in {"low", "base", "high"}:
        raise DiagramError("bom.scenario must be low, base, or high.")
    if bom.get("validation") not in {"browser_validated", "locally_validated", "blocked"}:
        raise DiagramError("bom.validation must be browser_validated, locally_validated, or blocked.")
    if bom.get("priceFreshness") not in {"current", "unverified"}:
        raise DiagramError("bom.priceFreshness must be current or unverified.")

    components = deck.get("components")
    if not isinstance(components, list) or not components:
        raise DiagramError("Case deck requires at least one component.")
    if len(components) > 14:
        raise DiagramError("Case deck supports at most 14 components per 16:9 slide.")

    architecture_node_ids = {str(node["id"]) for node in architecture.get("nodes", [])}
    items_by_ref: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in bom_detail["items"]:
        key = (str(item["configuration"]), str(item["service"]))
        items_by_ref.setdefault(key, []).append(item)
    estimated_price_lines = {
        (str(item["configuration"]), str(item["service"]), str(item["sku"]))
        for item in bom_detail["items"]
        if float(item["monthlyCost"]) > 0
    }

    component_ids: set[str] = set()
    mapped_node_ids: set[str] = set()
    referenced_price_lines: set[tuple[str, str, str | None]] = set()
    covered_price_lines: set[tuple[str, str, str]] = set()
    validated_components: list[dict[str, Any]] = []
    for index, component in enumerate(components):
        base = f"components[{index}]"
        if not isinstance(component, dict):
            raise DiagramError(f"{base} must be an object.")
        component_id = require_deck_string(component.get("id"), f"{base}.id")
        if component_id in component_ids:
            raise DiagramError(f"Duplicate case deck component id: {component_id}")
        component_ids.add(component_id)
        node_id = require_deck_string(component.get("nodeId"), f"{base}.nodeId")
        if node_id not in architecture_node_ids:
            raise DiagramError(f"{base}.nodeId must reference an architecture node.")
        if node_id in mapped_node_ids:
            raise DiagramError(f"Duplicate case deck architecture node: {node_id}")
        mapped_node_ids.add(node_id)
        for key in ("service", "component", "role", "sizing"):
            require_deck_string(component.get(key), f"{base}.{key}")

        pricing_refs = component.get("pricingRefs", [])
        if not isinstance(pricing_refs, list) or not pricing_refs:
            raise DiagramError(f"{base}.pricingRefs must contain at least one estimated Oracle BoM line.")
        embedded_monthly_cost = 0.0
        for reference_index, reference in enumerate(pricing_refs):
            ref_base = f"{base}.pricingRefs[{reference_index}]"
            if not isinstance(reference, dict):
                raise DiagramError(f"{ref_base} must be an object.")
            configuration = require_deck_string(reference.get("configuration"), f"{ref_base}.configuration")
            service = require_deck_string(reference.get("service"), f"{ref_base}.service")
            sku = reference.get("sku")
            if sku is not None:
                sku = require_deck_string(sku, f"{ref_base}.sku")
            line_key = (configuration, service, sku)
            if line_key in referenced_price_lines:
                raise DiagramError(f"Duplicate Oracle BoM price reference: {configuration} / {service} / {sku or '*'}")
            matches = items_by_ref.get((configuration, service), [])
            if sku is not None:
                matches = [item for item in matches if str(item["sku"]) == sku]
            if not matches:
                raise DiagramError(f"Unknown Oracle BoM price reference: {configuration} / {service} / {sku or '*'}")
            referenced_price_lines.add(line_key)
            matched_price_lines = {
                (configuration, service, str(item["sku"]))
                for item in matches
                if float(item["monthlyCost"]) > 0
            }
            overlap = covered_price_lines & matched_price_lines
            if overlap:
                raise DiagramError(f"Oracle BoM price lines are referenced more than once: {configuration} / {service}")
            covered_price_lines.update(matched_price_lines)
            embedded_monthly_cost += sum(float(item["monthlyCost"]) for item in matches)
        if embedded_monthly_cost <= 0:
            raise DiagramError(f"{base} must have a positive monthly estimate in the Oracle BoM.")
        validated_components.append({**component, "embeddedMonthlyCost": embedded_monthly_cost})
    if mapped_node_ids != architecture_node_ids:
        missing = sorted(architecture_node_ids - mapped_node_ids)
        extra = sorted(mapped_node_ids - architecture_node_ids)
        detail = "; ".join(part for part in (
            f"architecture-only nodes: {', '.join(missing)}" if missing else "",
            f"component-only nodes: {', '.join(extra)}" if extra else "",
        ) if part)
        raise DiagramError(f"Architecture and estimated BoM components must match one-to-one ({detail}).")
    uncovered_price_lines = estimated_price_lines - covered_price_lines
    if uncovered_price_lines:
        configurations = sorted({configuration for configuration, _service, _sku in uncovered_price_lines})
        raise DiagramError(f"Estimated Oracle BoM lines are missing from the architecture: {', '.join(configurations)}")
    return validated_components


def render_deck_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f'<p class="empty-copy">{html.escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_deck_component_cards(components: list[dict[str, Any]]) -> str:
    return "".join(
        f"""
        <article class="service-card" data-node-id="{html.escape(str(component["nodeId"]))}" tabindex="0" aria-label="{html.escape(str(component["service"]))}: {html.escape(str(component["role"]))}">
          <strong>{html.escape(str(component["service"]))}</strong>
          <p>{html.escape(str(component["role"]))}</p>
        </article>"""
        for component in components
    )


def order_deck_components_by_architecture(
    components: list[dict[str, Any]], architecture: dict[str, Any]
) -> list[dict[str, Any]]:
    nodes, edges, groups, _warnings = validate_spec(architecture)
    positions = layout_nodes(nodes, edges)
    positions = resolve_group_overlaps(groups, nodes, positions)
    positions = normalize_canvas_origin(groups, nodes, positions)
    reading_order = {
        node_id: index
        for index, (node_id, _position) in enumerate(
            sorted(positions.items(), key=lambda item: (item[1][0], item[1][1], item[0]))
        )
    }
    return sorted(
        components,
        key=lambda component: (
            reading_order.get(str(component["nodeId"]), len(reading_order)),
            str(component["nodeId"]),
        ),
    )


def format_money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def render_deck_bom_rows(components: list[dict[str, Any]], currency: str) -> str:
    rows = []
    for component in components:
        amount = float(component["embeddedMonthlyCost"])
        price_text = format_money(amount, currency)
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(component["service"]))}</td>
              <td><strong>{html.escape(str(component["component"]))}</strong><span>{html.escape(str(component["role"]))}</span></td>
              <td>{html.escape(str(component["sizing"]))}</td>
              <td>{html.escape(price_text)}</td>
            </tr>"""
        )
    return "".join(rows)


def render_case_deck_html(
    architecture: dict[str, Any],
    deck: dict[str, Any],
    bom_detail: dict[str, Any],
    catalog: dict[str, Any],
    catalog_path: Path,
    bom_path: Path,
) -> str:
    components = validate_deck_spec(deck, architecture, bom_detail)
    architecture_components = order_deck_components_by_architecture(components, architecture)
    svg, warnings, _used_services = render_svg(architecture, catalog, catalog_path)
    case = deck["case"]
    bom = deck["bom"]
    summary = bom_detail["summary"]
    title = str(architecture.get("title", "OCI Architecture Case"))
    currency = str(summary["currency"])
    case_page_description = "Resumen del propósito y del contexto funcional del caso de uso analizado."
    architecture_page_description = "Vista de los servicios OCI, sus relaciones y el flujo de interacción de la solución."
    case_description = str(case.get("description") or f'Este caso de uso presenta la necesidad funcional de la solución: {case["objective"]}')
    bom_download = base64.b64encode(bom_path.read_bytes()).decode("ascii")
    try:
        deck_brand = "data:image/svg+xml;base64," + base64.b64encode(DECK_BRAND_FILE.read_bytes()).decode("ascii")
    except OSError as exc:
        raise DiagramError(f"Unable to embed deck brand asset: {DECK_BRAND_FILE}") from exc
    warnings_markup = "" if not warnings else (
        '<aside class="deck-warnings"><strong>Advertencias del diagrama</strong><ul>'
        + "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings)
        + "</ul></aside>"
    )
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} — Deck</title>
  <style>
    :root {{ color-scheme: light; --ink:#252a30; --muted:#52616f; --line:#ced6dd; --oci:#c74634; --teal:#235967; --soft:#f4f7f8; }}
    * {{ box-sizing:border-box; }}
    html, body {{ width:100%; min-width:320px; min-height:100%; margin:0; overflow:hidden; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#e8edf0; }}
    .deck-host {{ display:flex; width:100vw; min-height:100vh; align-items:center; justify-content:center; overflow:hidden; }}
    .deck {{ position:relative; width:1920px; height:1080px; flex:0 0 auto; overflow:hidden; background:#fff; box-shadow:0 16px 42px rgba(30, 47, 57, .18); transform-origin:center center; }}
    .deck-header {{ display:grid; grid-template-columns:minmax(0, 1fr) auto; gap:28px; height:146px; padding:34px 56px 0; border-bottom:1px solid var(--line); background:linear-gradient(105deg, #ffffff 0%, #edf4fb 52%, #f8d8d2 100%); }}
    .eyebrow {{ margin:0 0 8px; color:var(--oci); font-size:18px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ margin:0; font-size:38px; line-height:1.05; }} .case-summary {{ max-width:none; margin:10px 0 0; color:var(--muted); font-size:19px; line-height:1.32; white-space:nowrap; }}
    .header-actions {{ align-self:end; display:flex; align-items:center; gap:10px; }} [role="tablist"] {{ display:flex; gap:8px; }} [role="tab"] {{ min-width:132px; min-height:46px; border:1px solid var(--line); border-radius:7px 7px 0 0; padding:0 18px; color:#41515e; background:#fff; font-size:17px; font-weight:700; cursor:pointer; }} [role="tab"][aria-selected="true"] {{ border-color:var(--oci); color:#fff; background:var(--oci); }}
    .capture-status {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}
    [role="tabpanel"] {{ display:none; height:934px; padding:34px 56px 42px; }} [role="tabpanel"].is-active {{ display:block; }}
    .slide-title {{ margin:0; font-size:29px; line-height:1.15; }} .slide-subtitle {{ margin:8px 0 22px; color:var(--muted); font-size:18px; }}
    .case-layout {{ display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); gap:34px; height:100%; align-items:stretch; }}
    .case-visual {{ display:flex; flex-direction:column; min-width:0; margin:0; padding:32px; border:1px solid var(--line); background:linear-gradient(145deg,#f7fafb,#eef4f6); }} .case-image {{ width:100%; height:100%; min-height:0; }} .case-visual figcaption {{ margin-top:16px; color:var(--muted); font-size:16px; text-align:center; }}
    .case-content {{ display:flex; align-items:center; min-width:0; padding:28px 22px; border:1px solid var(--line); border-left:5px solid var(--oci); }} .case-content p {{ margin:0; color:var(--ink); font-size:30px; font-weight:700; line-height:1.42; }}
    .architecture-layout {{ display:grid; grid-template-columns:360px minmax(0, 1fr); grid-template-rows:1fr; gap:20px; height:858px; }}
    .architecture-canvas {{ position:relative; grid-column:2; grid-row:1; min-height:0; overflow:hidden; border:1px solid var(--line); background:#eef2f5; }}
    .architecture-canvas .canvas {{ fill:#eef2f5; }} .architecture-canvas .edge {{ fill:none; stroke:var(--muted); stroke-width:1.65; stroke-linecap:round; opacity:.9; }} .architecture-canvas .node {{ transition:opacity .16s ease; }} .architecture-canvas .node.is-muted {{ opacity:.28; }} .architecture-canvas .node-card {{ fill:#fff; stroke:#c9d1d9; stroke-width:1.2; filter:drop-shadow(0 2px 5px rgba(49,45,42,.10)); transition:stroke .16s ease,stroke-width .16s ease; }} .architecture-canvas .node.is-highlighted .node-card {{ stroke:var(--oci); stroke-width:3; filter:drop-shadow(0 4px 9px rgba(199,70,52,.24)); }} .architecture-canvas .node-service-name {{ fill:var(--ink); font-size:13px; font-weight:700; }}
    .architecture-canvas .edge-label {{ pointer-events:none; }}
    .architecture-canvas .edge-label rect {{ fill:rgba(255,255,255,.96); stroke:#c7d0da; stroke-width:1; }}
    .architecture-canvas .edge-label text {{ fill:var(--muted); font-size:10px; font-weight:700; }}
    .architecture-canvas .edge-label-traffic rect {{ stroke:#93b6bd; fill:#f1f9fa; }} .architecture-canvas .edge-label-traffic text {{ fill:#2c5967; }}
    .architecture-canvas .edge-label-data rect {{ stroke:#b3c99d; fill:#f6fbf1; }} .architecture-canvas .edge-label-data text {{ fill:#557537; }}
    .architecture-canvas .edge-label-events rect {{ stroke:#d2b18e; fill:#fff8f0; }} .architecture-canvas .edge-label-events text {{ fill:#865825; }}
    .architecture-canvas .edge-label-admin rect {{ stroke:#c0b7df; fill:#f7f5ff; }} .architecture-canvas .edge-label-admin text {{ fill:#5f4f98; }}
    .architecture-canvas .edge-label-security rect {{ stroke:#d6aaa5; fill:#fff5f3; }} .architecture-canvas .edge-label-security text {{ fill:#8f3f37; }}
    .architecture-canvas .edge-label-observability rect {{ stroke:#a6c6d1; fill:#f2f9fb; }} .architecture-canvas .edge-label-observability text {{ fill:#426f82; }}
    .service-band {{ grid-column:1; grid-row:1; align-self:stretch; overflow:hidden; padding:0 12px 0 0; border-right:5px solid var(--oci); background:transparent; }}
    .service-grid {{ display:grid; grid-template-columns:1fr; grid-auto-rows:auto; gap:7px; }} .service-card {{ min-height:0; padding:10px 12px; border:1px solid var(--line); background:#fff; overflow:hidden; cursor:pointer; transition:border-color .16s ease,background .16s ease,box-shadow .16s ease; }} .service-card:hover,.service-card:focus-visible,.service-card.is-active {{ border-color:var(--oci); background:#fff7f5; box-shadow:0 2px 8px rgba(199,70,52,.14); outline:none; }} .service-card strong,.service-card p {{ display:block; white-space:normal; }} .service-card strong {{ color:var(--teal); font-size:14px; }} .service-card p {{ margin:5px 0 0; color:var(--muted); font-size:13px; line-height:1.34; }}
    .diagram-viewport {{ position:absolute; inset:0; overflow:auto; background:#eef2f5; cursor:grab; scrollbar-color:#8ea0aa transparent; scrollbar-width:thin; }} .diagram-viewport.is-panning {{ cursor:grabbing; user-select:none; }} .diagram-stage {{ width:100%; min-width:100%; height:100%; min-height:100%; padding:0; }} .diagram-viewport .diagram {{ display:block; max-width:none; }}
    .diagram-toolbar {{ position:absolute; right:16px; bottom:16px; z-index:4; display:flex; flex-direction:column; gap:5px; }} .diagram-toolbar button {{ min-width:36px; height:30px; border:1px solid #c9d1d9; border-radius:5px; color:var(--ink); background:#fff; box-shadow:0 2px 5px rgba(49,45,42,.14); font:700 13px Arial,Helvetica,sans-serif; cursor:pointer; }} .diagram-toolbar button:hover {{ border-color:var(--teal); color:var(--teal); }} .diagram-toolbar .zoom-fit {{ min-width:46px; font-size:11px; }}
    .bom-head {{ display:grid; grid-template-columns:minmax(0, 420px) minmax(0, 1fr); gap:14px; margin-bottom:22px; }} .metric {{ padding:17px 20px; border:1px solid var(--line); background:var(--soft); }} .metric span {{ display:block; color:var(--muted); font-size:14px; font-weight:700; text-transform:uppercase; }} .metric strong {{ display:block; margin-top:6px; color:var(--teal); font-size:24px; line-height:1.12; }}
    .bom-actions {{ display:flex; align-items:center; justify-content:space-between; gap:24px; padding:14px 18px; border:1px solid var(--line); background:#fff; }} .bom-actions p {{ margin:0; color:var(--muted); font-size:15px; line-height:1.35; }} .bom-actions strong {{ color:var(--ink); }} .bom-action-links {{ display:flex; flex:0 0 auto; align-items:center; gap:10px; }} .bom-action-links a,.download-bom {{ display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:42px; border-radius:5px; padding:0 16px; font:700 15px Arial,Helvetica,sans-serif; text-decoration:none; cursor:pointer; }} .bom-action-links a {{ border:1px solid var(--teal); color:var(--teal); background:#fff; }} .download-bom {{ border:1px solid var(--oci); color:#fff; background:var(--oci); }} .bom-action-links .action-icon {{ width:20px; height:20px; flex:0 0 auto; }} .bom-action-links a:hover,.bom-action-links a:focus-visible,.download-bom:hover,.download-bom:focus-visible {{ outline:3px solid rgba(199,70,52,.18); outline-offset:2px; }}
    .bom-table {{ width:100%; border-collapse:collapse; table-layout:fixed; font-size:16px; }} .bom-table th {{ padding:12px 14px; color:#fff; background:var(--teal); text-align:left; font-size:14px; text-transform:uppercase; }} .bom-table td {{ padding:11px 14px; border-bottom:1px solid var(--line); vertical-align:top; line-height:1.25; }} .bom-table tbody tr:nth-child(even) {{ background:#f7f9fa; }} .bom-table th:nth-child(1) {{ width:20%; }} .bom-table th:nth-child(2) {{ width:26%; }} .bom-table th:nth-child(3) {{ width:38%; }} .bom-table th:nth-child(4) {{ width:16%; text-align:right; }} .bom-table td:nth-child(4) {{ text-align:right; font-weight:700; }} .bom-table td span {{ display:block; margin-top:4px; color:var(--muted); font-size:14px; }}
    .deck-warnings {{ position:absolute; right:20px; bottom:20px; max-width:440px; padding:12px 16px; border:1px solid #dfb6a9; background:#fff4f1; font-size:13px; }}
    .deck-brand {{ position:absolute; right:56px; bottom:0; z-index:6; width:80px; height:80px; padding:0; border:0; border-radius:0; background:transparent; box-shadow:none; pointer-events:none; }} .deck-brand img {{ display:block; width:100%; height:100%; object-fit:contain; }} #slide-architecture .diagram-toolbar {{ right:16px; bottom:54px; z-index:7; }}
    @media print {{ html, body {{ background:#fff; }} .deck {{ box-shadow:none; }} }}
  </style>
</head>
<body>
  <div class="deck-host"><main class="deck" data-capture-enabled>
    <header class="deck-header">
      <div><p class="eyebrow">Oracle Cloud</p><h1>Use Case</h1><p class="case-summary">{html.escape(case_page_description)}</p></div>
      <div class="header-actions"><div role="tablist" aria-label="Case deck tabs">
        <button type="button" role="tab" id="tab-case" aria-controls="slide-case" aria-selected="true" data-tab="case">Use Case</button>
        <button type="button" role="tab" id="tab-architecture" aria-controls="slide-architecture" aria-selected="false" data-tab="architecture">Architecture</button>
        <button type="button" role="tab" id="tab-bom" aria-controls="slide-bom" aria-selected="false" data-tab="bom">BoM</button>
      </div><span class="capture-status" data-capture-exclude aria-live="polite"></span></div>
    </header>
    <div class="deck-brand"><img src="{deck_brand}" alt="Oracle"/></div>
    <section id="slide-case" role="tabpanel" aria-labelledby="tab-case" class="is-active"><div class="case-layout"><figure class="case-visual"><svg class="case-image" viewBox="0 0 760 560" role="img" aria-labelledby="case-image-title case-image-description"><title id="case-image-title">Flujo visual del caso de uso</title><desc id="case-image-description">Una entrada es procesada por una solución OCI para producir un resultado útil.</desc><defs><marker id="case-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#235967"/></marker></defs><rect x="16" y="16" width="728" height="528" rx="24" fill="#ffffff" stroke="#ced6dd"/><path d="M220 280 H302" fill="none" stroke="#235967" stroke-width="5" marker-end="url(#case-arrow)"/><path d="M458 280 H540" fill="none" stroke="#235967" stroke-width="5" marker-end="url(#case-arrow)"/><g transform="translate(54 180)"><rect width="166" height="200" rx="16" fill="#f4f7f8" stroke="#93b6bd" stroke-width="2"/><path d="M54 48 H112 M54 72 H112 M54 96 H98" stroke="#235967" stroke-width="7" stroke-linecap="round"/><text x="83" y="150" text-anchor="middle" fill="#252a30" font-family="Arial,Helvetica,sans-serif" font-size="22" font-weight="700">Entrada</text></g><g transform="translate(302 154)"><rect width="156" height="252" rx="20" fill="#fff4f1" stroke="#c74634" stroke-width="3"/><circle cx="78" cy="76" r="36" fill="#ffffff" stroke="#c74634" stroke-width="3"/><path d="M60 76 H96 M78 58 V94" stroke="#c74634" stroke-width="7" stroke-linecap="round"/><text x="78" y="152" text-anchor="middle" fill="#252a30" font-family="Arial,Helvetica,sans-serif" font-size="22" font-weight="700">Solución</text><text x="78" y="180" text-anchor="middle" fill="#235967" font-family="Arial,Helvetica,sans-serif" font-size="22" font-weight="700">OCI</text></g><g transform="translate(540 180)"><rect width="166" height="200" rx="16" fill="#f6fbf1" stroke="#b3c99d" stroke-width="2"/><path d="M47 60 L72 85 L119 42" fill="none" stroke="#557537" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/><text x="83" y="150" text-anchor="middle" fill="#252a30" font-family="Arial,Helvetica,sans-serif" font-size="22" font-weight="700">Resultado</text></g></svg><figcaption>Entrada → solución OCI → resultado</figcaption></figure><article class="case-content"><p>{html.escape(case_description)}</p></article></div></section>
    <section id="slide-architecture" role="tabpanel" aria-labelledby="tab-architecture">
      <div class="architecture-layout"><section class="service-band" aria-label="Servicios y roles"><div class="service-grid">{render_deck_component_cards(architecture_components)}</div></section><div class="architecture-canvas"><div class="diagram-viewport"><div class="diagram-stage">{svg}</div></div><div class="diagram-toolbar" aria-label="Navegación del diagrama"><button type="button" class="zoom-out" aria-label="Alejar">−</button><button type="button" class="zoom-in" aria-label="Acercar">+</button><button type="button" class="zoom-fit" aria-label="Ajustar diagrama">100%</button></div></div></div>
    </section>
    <section id="slide-bom" role="tabpanel" aria-labelledby="tab-bom">
      <div class="bom-head"><article class="metric"><span>Total mensual estimado</span><strong>{html.escape(format_money(float(summary["embeddedMonthlyCost"]), currency))}</strong></article><aside class="bom-actions" aria-label="Uso del JSON"><p><strong>¿Dónde usarlo?</strong> En Oracle Cloud Cost Estimator, abra el menú de tres puntos, seleccione <em>Import</em> y cargue este archivo JSON.</p><div class="bom-action-links"><a href="https://www.oracle.com/cloud/costestimator.html" target="_blank" rel="noopener noreferrer" aria-label="Abrir Oracle Cloud Cost Estimator" title="Abrir Oracle Cloud Cost Estimator"><svg class="action-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.5h10a2.5 2.5 0 0 1 2.5 2.5v10A2.5 2.5 0 0 1 15 19.5H5A2.5 2.5 0 0 1 2.5 17V7A2.5 2.5 0 0 1 5 4.5Z M13 2.5h6.5V9 M11 13 19.5 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Cost Estimator</span></a><button type="button" class="download-bom" aria-label="Descargar JSON" title="Descargar JSON"><svg class="action-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11 M7.5 10.5 12 15l4.5-4.5 M4.5 18.5v1A2 2 0 0 0 6.5 21.5h11a2 2 0 0 0 2-2v-1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>JSON</span></button></div></aside></div>
      <table class="bom-table"><thead><tr><th>Servicio</th><th>Componente y rol</th><th>Sizing</th><th>Mensual</th></tr></thead><tbody>{render_deck_bom_rows(components, currency)}</tbody></table>
    </section>
    {warnings_markup}
    <script type="application/json" id="architecture-spec">{html.escape(json.dumps(architecture, ensure_ascii=False))}</script>
    <script type="application/json" id="case-deck-spec">{html.escape(json.dumps(deck, ensure_ascii=False))}</script>
    <script type="application/octet-stream" id="bom-download-data">{bom_download}</script>
  </main></div>
  <script>
    (() => {{
      const deck = document.querySelector(".deck");
      const host = document.querySelector(".deck-host");
      const tabs = [...document.querySelectorAll('[role="tab"]')];
      const panels = [...document.querySelectorAll('[role="tabpanel"]')];
      const allowed = new Set(["case", "architecture", "bom"]);
      const headerTitle = document.querySelector(".deck-header h1");
      const headerDescription = document.querySelector(".deck-header .case-summary");
      const captureStatus = document.querySelector(".capture-status");
      const headers = {{
        case: ["Use Case", {json.dumps(case_page_description, ensure_ascii=False)}],
        architecture: ["Architecture", {json.dumps(architecture_page_description, ensure_ascii=False)}],
        bom: ["Bill of Materials (BoM)", "Detalle de los servicios y componentes con importe mensual estimado en el BoM suministrado."]
      }};
      const canvas = document.querySelector(".architecture-canvas");
      const viewport = canvas?.querySelector(".diagram-viewport");
      const stage = canvas?.querySelector(".diagram-stage");
      const diagram = canvas?.querySelector("svg.diagram");
      const zoomOut = canvas?.querySelector(".zoom-out");
      const zoomIn = canvas?.querySelector(".zoom-in");
      const zoomFit = canvas?.querySelector(".zoom-fit");
      const serviceCards = [...document.querySelectorAll(".service-card[data-node-id]")];
      const diagramNodes = [...document.querySelectorAll(".architecture-canvas g.node")];
      const downloadBom = document.querySelector(".download-bom");
      const bomDownloadData = document.querySelector("#bom-download-data");
      let zoom = 1;
      let isFit = false;
      let initialized = false;
      let pan = null;
      function fitScale() {{ return 1; }}
      function renderDiagram(nextZoom, fitted = false) {{
        zoom = Math.max(0.35, Math.min(2, nextZoom));
        isFit = fitted;
        const width = Math.round(viewport.clientWidth * zoom);
        const height = Math.round(viewport.clientHeight * zoom);
        diagram.setAttribute("preserveAspectRatio", "none");
        diagram.style.width = width + "px";
        diagram.style.height = height + "px";
        stage.style.width = width + "px";
        stage.style.height = height + "px";
        zoomFit.textContent = Math.round(zoom * 100) + "%";
      }}
      function fitDiagram() {{ renderDiagram(fitScale(), true); viewport.scrollLeft = 0; viewport.scrollTop = 0; }}
      function initializeDiagram() {{
        if (initialized || !viewport || !stage || !diagram || !zoomFit) return;
        initialized = true;
        fitDiagram();
      }}
      function highlightService(card) {{
        const targetId = "node-" + card.dataset.nodeId;
        serviceCards.forEach((item) => item.classList.toggle("is-active", item === card));
        diagramNodes.forEach((node) => {{
          const selected = node.id === targetId;
          node.classList.toggle("is-highlighted", selected);
          node.classList.toggle("is-muted", !selected);
        }});
      }}
      function clearServiceHighlight() {{
        serviceCards.forEach((item) => item.classList.remove("is-active"));
        diagramNodes.forEach((node) => node.classList.remove("is-highlighted", "is-muted"));
      }}
      function selectTab(name, updateUrl) {{
        const selected = allowed.has(name) ? name : "case";
        tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === selected)));
        panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === "slide-" + selected));
        headerTitle.textContent = headers[selected][0];
        headerDescription.textContent = headers[selected][1];
        if (selected === "architecture") requestAnimationFrame(initializeDiagram);
        if (updateUrl) {{ const url = new URL(window.location.href); url.searchParams.set("tab", selected); window.history.replaceState({{}}, "", url); }}
      }}
      function fitDeck() {{
        const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
        deck.style.transform = "scale(" + scale + ")";
        host.style.width = (1920 * scale) + "px";
        host.style.height = (1080 * scale) + "px";
      }}
      function slideBox(rect, deckRect, scale) {{
        return {{ x:(rect.left - deckRect.left) / scale, y:(rect.top - deckRect.top) / scale, width:rect.width / scale, height:rect.height / scale }};
      }}
      function paintBorder(context, box, style, side) {{
        const width = parseFloat(style["border" + side + "Width"]);
        if (!width || style["border" + side + "Style"] === "none") return;
        context.fillStyle = style["border" + side + "Color"];
        if (side === "Top") context.fillRect(box.x, box.y, box.width, width);
        if (side === "Right") context.fillRect(box.x + box.width - width, box.y, width, box.height);
        if (side === "Bottom") context.fillRect(box.x, box.y + box.height - width, box.width, width);
        if (side === "Left") context.fillRect(box.x, box.y, width, box.height);
      }}
      function paintTextNode(context, node, deckRect, scale) {{
        const text = node.nodeValue || "";
        const parent = node.parentElement;
        if (!parent || !text.trim()) return;
        const style = getComputedStyle(parent);
        context.save();
        context.fillStyle = style.color;
        context.font = [style.fontStyle, style.fontWeight, style.fontSize, style.fontFamily].join(" ");
        context.textBaseline = "alphabetic";
        for (const match of text.matchAll(/\\S+/g)) {{
          const range = document.createRange();
          range.setStart(node, match.index);
          range.setEnd(node, match.index + match[0].length);
          const rect = range.getBoundingClientRect();
          if (!rect.width || !rect.height) continue;
          const box = slideBox(rect, deckRect, scale);
          const token = style.textTransform === "uppercase" ? match[0].toUpperCase() : match[0];
          context.fillText(token, box.x, box.y + parseFloat(style.fontSize) * .86);
        }}
        context.restore();
      }}
      async function paintSlideElement(context, element, deckRect, scale, styleText) {{
        if (element.hasAttribute?.("data-capture-exclude")) return;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        if (style.display === "none" || style.visibility === "hidden" || !rect.width || !rect.height) return;
        const box = slideBox(rect, deckRect, scale);
        context.save();
        context.globalAlpha = Number(style.opacity) || 1;
        if (style.backgroundColor !== "rgba(0, 0, 0, 0)" && style.backgroundColor !== "transparent") {{
          context.fillStyle = style.backgroundColor;
          context.fillRect(box.x, box.y, box.width, box.height);
        }}
        for (const side of ["Top", "Right", "Bottom", "Left"]) paintBorder(context, box, style, side);
        context.restore();
        if (element.tagName.toLowerCase() === "img") {{
          try {{
            if (!element.complete) await new Promise((resolve, reject) => {{ element.addEventListener("load", resolve, {{ once:true }}); element.addEventListener("error", reject, {{ once:true }}); }});
            if (element.naturalWidth) context.drawImage(element, box.x, box.y, box.width, box.height);
          }} catch (_error) {{}}
          return;
        }}
        if (element.namespaceURI === "http://www.w3.org/2000/svg" && element.tagName.toLowerCase() === "svg") {{
          const svgClone = element.cloneNode(true);
          svgClone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
          const svgStyle = document.createElementNS("http://www.w3.org/2000/svg", "style");
          svgStyle.textContent = styleText;
          svgClone.insertBefore(svgStyle, svgClone.firstChild);
          const objectUrl = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svgClone)], {{ type:"image/svg+xml;charset=utf-8" }}));
          const image = new Image();
          image.src = objectUrl;
          await image.decode();
          context.drawImage(image, box.x, box.y, box.width, box.height);
          URL.revokeObjectURL(objectUrl);
          return;
        }}
        for (const child of element.childNodes) {{
          if (child.nodeType === Node.TEXT_NODE) paintTextNode(context, child, deckRect, scale);
          else if (child.nodeType === Node.ELEMENT_NODE) await paintSlideElement(context, child, deckRect, scale, styleText);
        }}
      }}
      async function copySlide() {{
        if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {{
          if (captureStatus) captureStatus.textContent = "La copia de imagen no está disponible en este navegador.";
          return;
        }}
        try {{
          const canvas = document.createElement("canvas");
          canvas.width = 1920;
          canvas.height = 1080;
          const context = canvas.getContext("2d");
          context.fillStyle = "#ffffff";
          context.fillRect(0, 0, 1920, 1080);
          const deckRect = deck.getBoundingClientRect();
          const scale = deckRect.width / 1920;
          const styleText = [...document.querySelectorAll("style")].map((style) => style.textContent).join("\\n");
          await paintSlideElement(context, deck, deckRect, scale, styleText);
          const png = await new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("PNG capture failed")), "image/png"));
          await navigator.clipboard.write([new ClipboardItem({{ "image/png":png }})]);
          if (captureStatus) captureStatus.textContent = "Página 16:9 copiada al portapapeles.";
        }} catch (error) {{
          if (captureStatus) captureStatus.textContent = "No fue posible copiar la página 16:9.";
          console.error(error);
        }}
      }}
      zoomOut?.addEventListener("click", () => renderDiagram(zoom - 0.1));
      zoomIn?.addEventListener("click", () => renderDiagram(zoom + 0.1));
      zoomFit?.addEventListener("click", fitDiagram);
      viewport?.addEventListener("pointerdown", (event) => {{
        if (event.button !== 0) return;
        pan = {{ x:event.clientX, y:event.clientY, left:viewport.scrollLeft, top:viewport.scrollTop }};
        viewport.classList.add("is-panning");
        viewport.setPointerCapture(event.pointerId);
      }});
      viewport?.addEventListener("pointermove", (event) => {{
        if (!pan) return;
        viewport.scrollLeft = pan.left - (event.clientX - pan.x);
        viewport.scrollTop = pan.top - (event.clientY - pan.y);
      }});
      viewport?.addEventListener("pointerup", () => {{ pan = null; viewport.classList.remove("is-panning"); }});
      viewport?.addEventListener("pointercancel", () => {{ pan = null; viewport.classList.remove("is-panning"); }});
      serviceCards.forEach((card) => {{
        card.addEventListener("mouseenter", () => highlightService(card));
        card.addEventListener("mouseleave", () => {{ if (document.activeElement !== card) clearServiceHighlight(); }});
        card.addEventListener("focus", () => highlightService(card));
        card.addEventListener("blur", clearServiceHighlight);
      }});
      tabs.forEach((tab) => tab.addEventListener("click", () => selectTab(tab.dataset.tab, true)));
      window.ociCopyActiveSlide = copySlide;
      window.addEventListener("message", (event) => {{
        if (event.origin === window.location.origin && event.data?.type === "oci-copy-active-slide") copySlide();
      }});
      downloadBom?.addEventListener("click", () => {{
        const encoded = bomDownloadData?.textContent.trim();
        if (!encoded) return;
        const binary = atob(encoded);
        const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], {{ type:"application/json" }}));
        const link = document.createElement("a");
        link.href = url;
        link.download = {json.dumps(bom_path.name, ensure_ascii=False)};
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 0);
      }});
      window.addEventListener("resize", () => {{ fitDeck(); if (isFit) fitDiagram(); }});
      selectTab(new URLSearchParams(window.location.search).get("tab"), false);
      fitDeck();
    }})();
  </script>
</body>
</html>
"""


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static HTML OCI architecture diagram.")
    parser.add_argument("--spec", required=True, help="Path to normalized architecture JSON.")
    parser.add_argument("--out", required=True, help="Output HTML path.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Path to OCI icon catalog.json.")
    parser.add_argument("--deck", help="Path to a version 1 case-deck JSON manifest.")
    parser.add_argument("--bom", help="Path to the exact Oracle Cost Estimator JSON used by the case deck.")
    parser.add_argument("--validate-only", action="store_true", help="Validate the spec and exit without writing HTML.")
    args = parser.parse_args(argv)

    try:
        spec_path = resolve_path(args.spec)
        out_path = resolve_path(args.out)
        catalog_path = resolve_path(args.catalog)
        spec = read_json(spec_path)
        catalog = load_catalog(catalog_path)
        validate_spec(spec)
        if bool(args.deck) != bool(args.bom):
            raise DiagramError("--deck and --bom must be provided together.")
        if args.validate_only:
            if args.deck and args.bom:
                deck = read_json(resolve_path(args.deck))
                bom_detail = read_bom_detail(resolve_path(args.bom))
                validate_deck_spec(deck, spec, bom_detail)
            print(f"Valid diagram spec: {spec_path}")
            return 0
        if args.deck and args.bom:
            deck = read_json(resolve_path(args.deck))
            bom_path = resolve_path(args.bom)
            bom_detail = read_bom_detail(bom_path)
            html_output = render_case_deck_html(spec, deck, bom_detail, catalog, catalog_path, bom_path)
        else:
            html_output = render_html(spec, catalog, catalog_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(line.rstrip() for line in html_output.splitlines()) + "\n", encoding="utf-8")
    except DiagramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Generated {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
