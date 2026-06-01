#!/usr/bin/env python3
"""Render a normalized OCI architecture spec as a portable HTML/SVG diagram."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
import textwrap
import unicodedata
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = PLUGIN_ROOT / "assets" / "oci-icons" / "catalog.json"

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
    parser.add_argument("--validate-only", action="store_true", help="Validate the spec and exit without writing HTML.")
    args = parser.parse_args(argv)

    try:
        spec_path = resolve_path(args.spec)
        out_path = resolve_path(args.out)
        catalog_path = resolve_path(args.catalog)
        spec = read_json(spec_path)
        catalog = load_catalog(catalog_path)
        validate_spec(spec)
        if args.validate_only:
            print(f"Valid diagram spec: {spec_path}")
            return 0
        html_output = render_html(spec, catalog, catalog_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_output, encoding="utf-8")
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
