from __future__ import annotations

import base64
import importlib.util
import json
import re
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
OCI_SOURCE = REPO_ROOT / "oci"
CATALOG = PLUGIN_ROOT / "assets" / "oci-icons" / "catalog.json"
SKILLS = PLUGIN_ROOT / "skills"
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


renderer = load_module("generate_oci_diagram", SCRIPTS / "generate_oci_diagram.py")
extractor = load_module("extract_oci_icons", SCRIPTS / "extract_oci_icons.py")
svg_importer = load_module("import_oci_svg_icons", SCRIPTS / "import_oci_svg_icons.py")
cases_module = load_module("architecture_prompt_cases", SCRIPTS / "architecture_prompt_cases.py")
suite_renderer = load_module("render_architecture_prompt_suite", SCRIPTS / "render_architecture_prompt_suite.py")
site_server = load_module("serve_architecture_site", SCRIPTS / "serve_architecture_site.py")


def overlaps(first, second, pad: float = 0) -> bool:
    return (
        first[0] < second[2] + pad
        and first[2] > second[0] - pad
        and first[1] < second[3] + pad
        and first[3] > second[1] - pad
    )


def node_boxes_from_html(html: str):
    node_boxes = []
    for match in re.finditer(r'<g class="node"[^>]*transform="translate\(([-0-9.]+) ([-0-9.]+)\)"', html):
        x = float(match.group(1))
        y = float(match.group(2))
        node_boxes.append((x, y, x + renderer.NODE_W, y + renderer.NODE_H))
    return node_boxes


def edge_label_boxes_from_html(html: str):
    label_boxes = []
    for match in re.finditer(
        r'<g class="edge-label[^"]*"[^>]*transform="translate\(([-0-9.]+) ([-0-9.]+)\)"[^>]*><rect x="([-0-9.]+)" y="([-0-9.]+)" width="([-0-9.]+)" height="([-0-9.]+)"',
        html,
    ):
        x = float(match.group(1))
        y = float(match.group(2))
        rx = float(match.group(3))
        ry = float(match.group(4))
        width = float(match.group(5))
        height = float(match.group(6))
        label_boxes.append((x + rx, y + ry, x + rx + width, y + ry + height))
    return label_boxes


def group_boxes_from_html(html: str):
    group_boxes = {}
    for match in re.finditer(
        r'<g class="diagram-group depth-\d+" data-group-id="([^"]+)"><rect x="([-0-9.]+)" y="([-0-9.]+)" width="([-0-9.]+)" height="([-0-9.]+)"',
        html,
    ):
        group_id = match.group(1)
        x = float(match.group(2))
        y = float(match.group(3))
        width = float(match.group(4))
        height = float(match.group(5))
        group_boxes[group_id] = (x, y, x + width, y + height)
    return group_boxes


def sibling_group_pairs(spec):
    children = {}
    for group in spec["groups"]:
        children.setdefault(group.get("parent", ""), []).append(group["id"])
    for sibling_ids in children.values():
        for index, first_id in enumerate(sibling_ids):
            for second_id in sibling_ids[index + 1 :]:
                yield first_id, second_id


def skill_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


class ExtractorTests(unittest.TestCase):
    def test_extracts_known_oci_services_from_visio_stencils(self) -> None:
        if not any(OCI_SOURCE.glob("*.vssx")):
            self.skipTest(f"OCI Visio stencils not found at {OCI_SOURCE}")

        with tempfile.TemporaryDirectory() as tmp:
            catalog = extractor.extract_icons(OCI_SOURCE, Path(tmp))
            services = catalog["services"]
            aliases = catalog["aliases"]

            self.assertGreaterEqual(catalog["serviceCount"], 200)
            self.assertIn("virtual-machine", services)
            self.assertIn("virtual-cloud-network", services)
            self.assertIn("internet-gateway", services)
            self.assertIn("object-storage", services)
            self.assertIn("oracle-autonomous-database", services)
            self.assertIn("container-engine-for-kubernetes", services)
            self.assertEqual(aliases["vm"], "virtual-machine")
            self.assertEqual(aliases["oke"], "container-engine-for-kubernetes")

            for slug in [
                "virtual-machine",
                "virtual-cloud-network",
                "internet-gateway",
                "object-storage",
                "oracle-autonomous-database",
                "container-engine-for-kubernetes",
            ]:
                icon_path = Path(tmp) / services[slug]["file"]
                self.assertTrue(icon_path.exists(), slug)
                ET.fromstring(icon_path.read_text(encoding="utf-8"))

    def test_importer_sanitizes_and_maps_local_svg_icons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source"
            out_dir = tmp_path / "out"
            source.mkdir()
            out_dir.mkdir()
            catalog_path = out_dir / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    {
                        "services": {
                            "dns": {
                                "name": "DNS",
                                "file": "dns.svg",
                                "warnings": ["old conversion warning"],
                            }
                        },
                        "aliases": {"dns": "dns"},
                    }
                ),
                encoding="utf-8",
            )
            (source / "Domain Name System DNS.svg").write_text(
                """<?xml version="1.0"?>
<svg viewBox="0 0 44.45 42">
  <metadata>noise</metadata>
  <style>.st0{fill:#fff;}.st1{fill:#2C5967;}</style>
  <g id="Layer_1"><path class="st1" d="M0 0h10v10z"/></g>
</svg>
""",
                encoding="utf-8",
            )

            report = svg_importer.import_icons(source, out_dir, catalog_path)

            self.assertEqual(1, report["imported"])
            icon = (out_dir / "dns.svg").read_text(encoding="utf-8")
            catalog = renderer.read_json(catalog_path)
            self.assertIn('viewBox="0 0 44.45 42"', icon)
            self.assertNotIn("<metadata>", icon)
            self.assertNotIn("<style>", icon)
            self.assertIn("oci-dns-st1", icon)
            self.assertIn('style="fill:#2C5967;"', icon)
            self.assertIn('id="oci-dns-Layer_1"', icon)
            self.assertEqual("local-svg", catalog["services"]["dns"]["iconSource"])
            self.assertEqual([], catalog["services"]["dns"]["warnings"])


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = renderer.load_catalog(CATALOG)

    def test_valid_example_renders_portable_html(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "web-architecture.json")
        output = renderer.render_html(spec, self.catalog, CATALOG)

        self.assertIn("<!doctype html>", output)
        self.assertIn("OCI Web Architecture", output)
        self.assertIn("<style>", output)
        self.assertIn("<svg class=\"diagram\"", output)
        self.assertIn("diagram-toolbar", output)
        self.assertIn('class="zoom-percent"', output)
        self.assertIn("body.embedded main > header", output)
        self.assertIn('get("embed") === "1"', output)
        self.assertIn('data-diagram-action="fit"', output)
        self.assertIn('title="Fit diagram"', output)
        self.assertNotIn('data-diagram-action="actual"', output)
        self.assertIn("script type=\"application/json\"", output)
        self.assertIn("Public Load Balancer", output)
        self.assertIn("Oracle Autonomous Database", output)
        self.assertIn("Architecture Services", output)
        self.assertIn('class="service-inventory"', output)
        self.assertIn('class="service-table"', output)
        self.assertIn('<th scope="col">Service</th>', output)
        self.assertIn('<th scope="col">Component</th>', output)
        self.assertIn('<th scope="col">Role</th>', output)
        self.assertNotIn('class="service-inventory-scroll"', output)
        self.assertNotIn("max-height: clamp(320px, 42vh, 560px);", output)
        self.assertNotIn('class="legend-item"', output)
        self.assertNotIn("static architecture diagram", output)
        self.assertNotIn("Unknown OCI service", output)

    def test_svg_uses_an_accessible_label_without_a_hover_tooltip(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "web-architecture.json")

        svg, _warnings, _services = renderer.render_svg(spec, self.catalog, CATALOG)

        self.assertIn('role="img" aria-label="OCI Web Architecture"', svg)
        self.assertNotIn('<title id="diagram-title">', svg)

    def test_case_deck_renders_three_16_by_9_tabs_from_validated_bom(self) -> None:
        architecture = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web-architecture.json")
        deck = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web.json")
        bom_path = PLUGIN_ROOT / "examples" / "case-deck-web-bom.json"
        bom_detail = renderer.read_bom_detail(bom_path)

        output = renderer.render_case_deck_html(architecture, deck, bom_detail, self.catalog, CATALOG, bom_path)

        self.assertIn('width:1920px', output)
        self.assertIn('height:1080px', output)
        self.assertIn('role="tab" id="tab-case"', output)
        self.assertIn('role="tab" id="tab-architecture"', output)
        self.assertIn('role="tab" id="tab-bom"', output)
        self.assertIn('aria-label="Case deck tabs"', output)
        self.assertIn('data-tab="case">Use Case</button>', output)
        self.assertIn('data-tab="architecture">Architecture</button>', output)
        self.assertIn('architecture: ["Architecture",', output)
        self.assertIn('<p class="eyebrow">Oracle Cloud</p>', output)
        self.assertNotIn('OCI Architecture + BoM', output)
        self.assertIn("<h1>Use Case</h1>", output)
        self.assertIn("Resumen del propósito y del contexto funcional del caso de uso analizado.", output)
        self.assertIn("Vista de los servicios OCI, sus relaciones y el flujo de interacción de la solución.", output)
        self.assertIn('class="case-content"', output)
        self.assertIn('class="case-layout"', output)
        self.assertIn('case-image-slot', output)
        self.assertIn('case-image-upload', output)
        self.assertIn('case-image-prompt-toggle', output)
        self.assertIn('case-prompt-dialog', output)
        self.assertIn('case-prompt-text-wrap', output)
        self.assertIn('case-prompt-copy', output)
        self.assertIn('case-dialog-actions', output)
        self.assertIn('width:30px', output)
        self.assertIn('background:transparent!important', output)
        self.assertIn('.case-prompt-copy:hover', output)
        self.assertIn('case-prompt-save', output)
        self.assertIn('case-image-actions-dialog', output)
        self.assertIn('case-image-actions-download', output)
        self.assertIn('case-image-actions-delete', output)
        self.assertIn('case-image-dimensions', output)
        self.assertIn('function imageFormat()', output)
        self.assertIn('.case-uploaded-image[hidden] { display:none; }', output)
        self.assertIn('.case-image-upload[hidden] { display:none; }', output)
        self.assertIn('showToast("Prompt copiado.")', output)
        self.assertIn('file.size > 3 * 1024 * 1024', output)
        self.assertIn('Use una imagen PNG, JPEG o WebP de hasta 3 MB.', output)
        self.assertIn('reader.addEventListener("error"', output)
        self.assertIn('background:#2f7d32', output)
        self.assertIn('deckToast.classList.toggle("is-error", kind === "error")', output)
        self.assertIn('scrollbar-width:thin', output)
        self.assertIn('width:6px; height:6px', output)
        self.assertIn('font:14px/1.35 Arial,Helvetica,sans-serif', output)
        self.assertIn('top:24px; right:24px; min-width:260px', output)
        self.assertIn('async function renderAllSlidesPngs()', output)
        self.assertIn('window.ociRenderAllSlides = renderAllSlidesPngs;', output)
        self.assertIn('object-fit:cover', output)
        self.assertNotIn('Agregar imagen', output)
        self.assertIn('Prompt para generar imagen en GPT', output)
        self.assertIn('Client and project context:', output)
        self.assertIn('file.type = "file"', output)
        self.assertIn('function bindEditable', output)
        self.assertIn('data-source="', output)
        self.assertIn('id="arrow-highlight"', output)
        self.assertIn('function highlightService(nodeId)', output)
        self.assertIn('const diagramEdges', output)
        self.assertIn('is-flow-target', output)
        self.assertIn('edge.classList.toggle("is-highlighted", selected)', output)
        self.assertIn('localStorage.setItem(editStorageKey', output)
        self.assertIn('Editar el nombre del servicio', output)
        self.assertIn('class="deck-editor-dialog"', output)
        self.assertNotIn('<label for="deck-editor-input">Texto</label>', output)
        self.assertIn('aria-label="Contenido editable"', output)
        self.assertIn('showToast(message);', output)
        self.assertIn("grid-template-columns:minmax(0, 1fr) minmax(0, 1fr)", output)
        self.assertIn(str(deck["case"]["description"]), output)
        self.assertNotIn('class="capture-slide"', output)
        self.assertIn('data-capture-enabled', output)
        self.assertNotIn("navigator.clipboard.write([{", output)
        self.assertIn('canvas.width = 1920', output)
        self.assertIn('canvas.height = 1080', output)
        self.assertNotIn('new ClipboardItem({ "image/png":png })', output)
        self.assertIn("async function paintSlideElement", output)
        self.assertIn("function serializableSvgClone", output)
        self.assertNotIn('"marker-end": style.markerEnd', output)
        self.assertIn('svgClone.classList.add("architecture-canvas")', output)
        self.assertIn('styleNode.textContent = styleText', output)
        self.assertIn('const brand = deck.querySelector(".deck-brand")', output)
        self.assertIn('paintSlideElement(context, brand, deckRect, scale, styleText, true)', output)
        self.assertIn("document.createRange()", output)
        self.assertIn("await paintSlideElement(context, deck", output)
        self.assertNotIn("<foreignObject", output)
        self.assertIn(".case-content { display:flex; align-items:center; min-width:0; padding:28px 22px; border:1px solid var(--line); border-left:5px solid var(--oci); }", output)
        self.assertNotIn("background:#fff7f5; } .case-content", output)
        self.assertIn("white-space:nowrap", output)
        self.assertNotIn('class="case-single"', output)
        self.assertNotIn("Servicios, componentes y rol", output)
        self.assertIn("Container Engine for Kubernetes", output)
        self.assertIn("USD 75.00", output)
        self.assertIn('<div class="bom-metrics">', output)
        self.assertIn("Costo anual estimado</span><strong>USD 900.00</strong>", output)
        self.assertIn("Total mensual estimado</span><strong>USD 75.00</strong>", output)
        self.assertIn(".bom-metrics { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px; }", output)
        self.assertIn("Bill of Materials (BoM)", output)
        self.assertIn('aria-label="Descargar JSON de Oracle Cost Estimator"', output)
        self.assertIn('aria-label="Abrir Oracle Cloud Cost Estimator"', output)
        self.assertIn('<th>SKU</th>', output)
        self.assertIn('class="bom-sku"', output)
        self.assertIn('Exportación homologada:', output)
        self.assertNotIn('aria-label="Descargar Excel"', output)
        self.assertNotIn('downloadBomExcel?.addEventListener("click"', output)
        self.assertNotIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', output)
        self.assertIn('<span>JSON</span>', output)
        self.assertIn('<span>Cost Estimator</span>', output)
        self.assertIn('class="action-icon"', output)
        self.assertNotIn(">Abrir Cost Estimator<", output)
        self.assertIn('class="deck-brand"', output)
        self.assertIn('alt="Oracle"', output)
        self.assertIn('data:image/svg+xml;base64,', output)
        self.assertIn('right:56px; bottom:0;', output)
        self.assertIn('padding:0; border:0; border-radius:0; background:transparent; box-shadow:none;', output)
        self.assertIn('#slide-architecture .diagram-toolbar { right:16px; bottom:54px; z-index:7; }', output)
        self.assertIn('.diagram-toolbar button { min-width:36px; height:30px;', output)
        self.assertIn('.diagram-toolbar .zoom-fit { min-width:46px; font-size:11px; }', output)
        self.assertIn('context.drawImage(element, box.x, box.y, box.width, box.height)', output)
        self.assertIn("https://www.oracle.com/cloud/costestimator.html", output)
        self.assertIn("Exportación homologada:", output)
        embedded_bom = re.search(r'<script type="application/octet-stream" id="bom-download-data">([^<]+)</script>', output)
        self.assertIsNotNone(embedded_bom)
        self.assertEqual(base64.b64decode(embedded_bom.group(1)), bom_path.read_bytes())
        self.assertIn('class="diagram-toolbar"', output)
        self.assertIn(".architecture-canvas .edge-label rect", output)
        self.assertIn(".architecture-canvas .edge-label text", output)
        self.assertIn(".architecture-canvas .edge-label-traffic text", output)
        self.assertIn("font-size:10px", output)
        self.assertIn("grid-template-columns:1fr", output)
        self.assertIn(".architecture-layout { display:grid; grid-template-columns:360px minmax(0, 1fr);", output)
        self.assertIn(".service-band { grid-column:1; grid-row:1; align-self:stretch;", output)
        self.assertIn("border-right:5px solid var(--oci); background:transparent;", output)
        self.assertIn("background:linear-gradient(105deg, #ffffff 0%, #edf4fb 52%, #f8d8d2 100%)", output)
        self.assertIn("height:146px; padding:34px 56px 0; border-bottom:1px solid var(--line);", output)
        self.assertIn(".service-card strong { color:var(--teal); font-size:14px; }", output)
        self.assertIn(".service-card p { margin:5px 0 0; color:var(--muted); font-size:13px; line-height:1.34; }", output)
        self.assertIn(".architecture-canvas { position:relative; grid-column:2; grid-row:1; min-height:0; overflow:hidden; border:1px solid var(--line); background:#eef2f5; }", output)
        self.assertIn(".architecture-canvas .canvas { fill:#eef2f5; }", output)
        self.assertIn(".diagram-stage { width:100%; min-width:100%; height:100%; min-height:100%; padding:0; }", output)
        self.assertIn("function fitScale() { return 1; }", output)
        self.assertIn("const width = Math.round(viewport.clientWidth * zoom);", output)
        self.assertIn('diagram.setAttribute("preserveAspectRatio", "none");', output)
        self.assertIn("zoom = Math.max(0.35, Math.min(2, nextZoom));", output)
        self.assertIn("initialized = true;\n        fitDiagram();", output)
        self.assertIn('data-node-id="oke"', output)
        self.assertIn('tabindex="0"', output)
        self.assertIn("is-highlighted", output)
        self.assertNotIn("<span>Pods de aplicación</span>", output)
        self.assertNotIn("Validación local; importación pendiente", output)
        self.assertNotIn("Frescura de precio no verificada", output)
        self.assertNotIn("No valorizado", output)

    def test_case_deck_cards_follow_diagram_visual_reading_order(self) -> None:
        architecture = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web-architecture.json")
        deck = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web.json")

        ordered = renderer.order_deck_components_by_architecture(list(reversed(deck["components"])), architecture)

        self.assertEqual([component["nodeId"] for component in ordered], ["lb", "oke", "adb", "object-storage"])

    def test_case_deck_rejects_unknown_architecture_node(self) -> None:
        architecture = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web-architecture.json")
        deck = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web.json")
        deck["components"][0]["nodeId"] = "missing"
        bom_detail = renderer.read_bom_detail(PLUGIN_ROOT / "examples" / "case-deck-web-bom.json")

        with self.assertRaisesRegex(renderer.DiagramError, "must reference an architecture node"):
            renderer.validate_deck_spec(deck, architecture, bom_detail)

    def test_case_deck_requires_priced_components_to_match_architecture(self) -> None:
        architecture = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web-architecture.json")
        deck = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web.json")
        bom_detail = renderer.read_bom_detail(PLUGIN_ROOT / "examples" / "case-deck-web-bom.json")

        deck["components"][0]["pricingRefs"] = []
        with self.assertRaisesRegex(renderer.DiagramError, "at least one estimated Oracle BoM line"):
            renderer.validate_deck_spec(deck, architecture, bom_detail)

        deck = renderer.read_json(PLUGIN_ROOT / "examples" / "case-deck-web.json")
        architecture["nodes"].append({"id": "extra", "label": "Extra", "service": "Logging", "group": ""})
        with self.assertRaisesRegex(renderer.DiagramError, "must match one-to-one"):
            renderer.validate_deck_spec(deck, architecture, bom_detail)

    def test_duplicate_node_ids_are_rejected(self) -> None:
        spec = {
            "title": "bad",
            "layout": "left-to-right",
            "groups": [{"id": "g", "label": "G", "type": "group"}],
            "nodes": [
                {"id": "a", "label": "A", "service": "Virtual Machine", "group": "g"},
                {"id": "a", "label": "B", "service": "Virtual Machine", "group": "g"},
            ],
            "edges": [],
        }
        with self.assertRaisesRegex(renderer.DiagramError, "Duplicate node id"):
            renderer.validate_spec(spec)

    def test_missing_edge_endpoint_is_rejected(self) -> None:
        spec = {
            "title": "bad",
            "layout": "left-to-right",
            "groups": [{"id": "g", "label": "G", "type": "group"}],
            "nodes": [{"id": "a", "label": "A", "service": "Virtual Machine", "group": "g"}],
            "edges": [{"from": "a", "to": "missing"}],
        }
        with self.assertRaisesRegex(renderer.DiagramError, "missing target node"):
            renderer.validate_spec(spec)

    def test_unknown_service_uses_generic_icon_with_warning(self) -> None:
        spec = {
            "title": "fallback",
            "layout": "left-to-right",
            "groups": [{"id": "g", "label": "G", "type": "group"}],
            "nodes": [{"id": "a", "label": "Made Up", "service": "Imaginary Cloud Thing", "group": "g"}],
            "edges": [],
        }
        html = renderer.render_html(spec, self.catalog, CATALOG)
        self.assertIn("Unknown OCI service", html)
        self.assertIn("Imaginary Cloud Thing", html)

    def test_live_query_edge_labels_do_not_land_on_node_cards(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)
        node_boxes = node_boxes_from_html(html)
        label_boxes = edge_label_boxes_from_html(html)

        self.assertEqual(len(spec["edges"]), len(label_boxes))
        for label in label_boxes:
            for node in node_boxes:
                self.assertFalse(overlaps(label, node), f"edge label overlaps node card: label={label} node={node}")

    def test_live_query_sibling_groups_do_not_overlap(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)
        group_boxes = group_boxes_from_html(html)

        for first_id, second_id in sibling_group_pairs(spec):
            first = group_boxes.get(first_id)
            second = group_boxes.get(second_id)
            if not first or not second:
                continue
            self.assertFalse(overlaps(first, second), f"sibling groups overlap: {first_id}={first} {second_id}={second}")

    def test_node_card_shows_only_icon_and_service_name(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)
        start = html.index('id="node-dns"')
        end = html.index('id="node-waf"', start)
        node_html = html[start:end]

        self.assertLess(node_html.index('class="node-icon"'), node_html.index('class="node-service-name"'))
        self.assertNotIn("Public DNS", node_html)
        self.assertNotIn('class="node-service"', node_html)
        self.assertNotIn('class="icon-tile"', node_html)
        self.assertIn(">DNS</tspan>", node_html)

    def test_node_card_keeps_the_service_name_clear_of_the_icon(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)

        self.assertEqual(renderer.NODE_H, 128)
        self.assertIn('class="node-icon" x="66" y="15"', html)
        self.assertIn('class="node-service-name" text-anchor="middle" x="92" y="98"', html)

    def test_edge_label_adjustment_stays_close_to_its_connector(self) -> None:
        x, y, _ = renderer.adjust_edge_label_position(
            "object API",
            626,
            298,
            [],
            [renderer.edge_label_box("test SQL", 626, 298)],
        )

        self.assertEqual(x, 626)
        self.assertEqual(y, 322)
        self.assertLessEqual(abs(y - 298), 24)

    def test_live_query_group_palette_and_vcn_label_visibility(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)

        self.assertIn('data-group-id="region"><rect', html)
        self.assertIn('fill="#f4f5f6"', html)
        self.assertIn('data-group-id="edge-subnet"><rect', html)
        self.assertIn('fill="#e4e8eb"', html)
        self.assertNotIn('data-group-id="vcn"><rect', html)
        label_section = html.split('<g class="group-labels">', 1)[1].split('<g class="nodes">', 1)[0]
        self.assertNotIn("Commerce VCN", label_section)

    def test_live_query_title_is_architecture_name_only(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)

        self.assertEqual("E-commerce Platform", spec["title"])
        self.assertIn("<h1>E-commerce Platform</h1>", html)
        self.assertNotIn("OCI Live Query -", html)

    def test_edge_styles_include_semantic_colors(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)

        for edge_class in ["edge-traffic", "edge-data", "edge-events", "edge-admin", "edge-security", "edge-observability"]:
            self.assertIn(edge_class, html)

    def test_common_dns_icon_uses_imported_official_svg(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "live-query-ecommerce.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)
        start = html.index('id="node-dns"')
        end = html.index('id="node-waf"', start)
        node_html = html[start:end]

        self.assertEqual("local-svg", self.catalog["services"]["dns"].get("iconSource"))
        self.assertIn('class="node-icon"', node_html)
        self.assertIn('viewBox="0 0 44.45 42"', node_html)
        self.assertIn("oci-dns-st1", node_html)

    def test_suite_subnets_keep_horizontal_room_for_edge_labels(self) -> None:
        case = next(item for item in cases_module.architecture_prompt_cases() if item["id"] == "web-oke-adb-08")
        html = renderer.render_html(case["spec"], self.catalog, CATALOG)
        group_boxes = group_boxes_from_html(html)

        public_subnet = group_boxes["public-subnet"]
        app_subnet = group_boxes["private-subnet"]
        data_subnet = group_boxes["data-subnet"]

        self.assertGreaterEqual(app_subnet[0] - public_subnet[2], 70)
        self.assertGreaterEqual(data_subnet[0] - app_subnet[2], 70)

    def test_service_inventory_replaces_footer_legend_chips(self) -> None:
        case = next(item for item in cases_module.architecture_prompt_cases() if item["id"] == "web-oke-adb-08")
        html = renderer.render_html(case["spec"], self.catalog, CATALOG)

        self.assertNotIn("<footer class=\"legend\"", html)
        self.assertNotIn('class="legend-item"', html)
        self.assertIn('<section class="service-inventory"', html)
        self.assertIn("<h2>Architecture Services</h2>", html)
        self.assertIn('<table class="service-table">', html)
        self.assertIn("<thead>", html)
        self.assertIn("<tbody>", html)
        self.assertNotIn('class="service-inventory-scroll"', html)
        self.assertIn("Container Engine for Kubernetes", html)
        self.assertIn("Ejecuta los microservicios", html)
        self.assertIn("Email Delivery", html)

    def test_diagram_toolbar_is_fixed_overlay_scoped_to_diagram_shell(self) -> None:
        spec = renderer.read_json(PLUGIN_ROOT / "examples" / "web-architecture.json")
        html = renderer.render_html(spec, self.catalog, CATALOG)
        shell_start = html.index('<section class="diagram-shell">')
        wrap_start = html.index('<div class="diagram-wrap"', shell_start)
        stage_start = html.index('<div class="diagram-stage">', wrap_start)
        toolbar_start = html.index('<div class="diagram-toolbar"', shell_start)
        toolbar_css = html.split(".diagram-toolbar {", 1)[1].split("}", 1)[0]
        control_css = html.split(".diagram-toolbar button,\n    .zoom-percent {", 1)[1].split("}", 1)[0]
        button_css = html.split(".diagram-toolbar button {", 1)[1].split("}", 1)[0]
        wrap_css = html.split(".diagram-wrap {", 1)[1].split("}", 1)[0]

        self.assertGreater(toolbar_start, stage_start)
        self.assertIn('      </div>\n      <div class="diagram-toolbar"', html)
        self.assertIn("position: relative;", wrap_css)
        self.assertIn("position: absolute;", toolbar_css)
        self.assertIn("right: 12px;", toolbar_css)
        self.assertIn("bottom: 32px;", toolbar_css)
        self.assertIn("flex-direction: column;", toolbar_css)
        self.assertIn("padding: 0;", toolbar_css)
        self.assertIn("border: 0;", toolbar_css)
        self.assertIn("background: transparent;", toolbar_css)
        self.assertIn("box-shadow: none;", toolbar_css)
        self.assertIn("width: 34px;", control_css)
        self.assertIn("height: 26px;", control_css)
        self.assertIn("border: 1px solid #c9d1d9;", control_css)
        self.assertIn("box-shadow: 0 2px 5px rgba(49, 45, 42, 0.10);", control_css)
        self.assertIn("cursor: pointer;", button_css)
        self.assertIn(".zoom-percent", html)
        self.assertIn("Math.round(scale * 100)", html)
        self.assertIn('class="zoom-percent" data-diagram-action="fit"', html)
        self.assertIn('if (action === "fit") fitDiagram();', html)
        self.assertIn('target.closest(".diagram-toolbar")', html)
        self.assertIn("event.stopPropagation();", html)
        self.assertNotIn('data-diagram-action="actual"', html)
        self.assertNotIn("border-bottom: 1px solid var(--line);", toolbar_css)


class PromptSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = renderer.load_catalog(CATALOG)
        cls.cases = cases_module.architecture_prompt_cases()

    def test_suite_has_100_compound_architecture_questions(self) -> None:
        self.assertEqual(100, len(self.cases))
        prompts = [case["prompt"] for case in self.cases]
        self.assertEqual(len(prompts), len(set(prompts)))
        for prompt in prompts:
            self.assertGreaterEqual(prompt.count(";"), 2)
            self.assertIn("arquitectura OCI", prompt)
            self.assertIn("conexiones criticas", prompt)

    def test_all_100_architecture_specs_validate_and_render_coherently(self) -> None:
        patterns = {case["sourcePattern"] for case in self.cases}
        self.assertGreaterEqual(len(patterns), 10)

        for case in self.cases:
            with self.subTest(case=case["id"]):
                nodes, edges, groups, warnings = renderer.validate_spec(case["spec"])
                self.assertGreaterEqual(len(nodes), 6)
                self.assertGreaterEqual(len(edges), 5)
                self.assertGreaterEqual(len(groups), 3)
                self.assertEqual([], warnings)
                html = renderer.render_html(case["spec"], self.catalog, CATALOG)
                self.assertIn(case["spec"]["title"], html)
                self.assertIn("<svg class=\"diagram\"", html)
                self.assertNotIn("Unknown OCI service", html)
                self.assertLess(html.count("<g class=\"node\""), 20)
                node_boxes = node_boxes_from_html(html)
                for index, first in enumerate(node_boxes):
                    for second in node_boxes[index + 1 :]:
                        self.assertFalse(overlaps(first, second), f"node cards overlap: {first} {second}")
                label_boxes = edge_label_boxes_from_html(html)
                for label in label_boxes:
                    for node in node_boxes:
                        self.assertFalse(overlaps(label, node), f"edge label overlaps node card: label={label} node={node}")
                group_boxes = group_boxes_from_html(html)
                for first_id, second_id in sibling_group_pairs(case["spec"]):
                    first = group_boxes.get(first_id)
                    second = group_boxes.get(second_id)
                    if not first or not second:
                        continue
                    self.assertFalse(
                        overlaps(first, second),
                        f"sibling groups overlap: {first_id}={first} {second_id}={second}",
                    )

    def test_render_suite_writes_root_gallery_with_100_visible_diagram_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "generated-suite"
            diagram_count = suite_renderer.render_suite(out_dir, CATALOG)
            root_index = out_dir.parent / "index.html"
            suite_index = out_dir / "index.html"

            self.assertEqual(100, diagram_count)
            self.assertTrue(root_index.exists())
            self.assertTrue(suite_index.exists())
            root_html = root_index.read_text(encoding="utf-8")
            self.assertIn("OCI Architecture Diagram Gallery", root_html)
            self.assertNotIn('class="count"', root_html)
            self.assertNotIn("100 diagramas", root_html)
            self.assertEqual(100, root_html.count('<li><a href="generated-suite/'))


class LocalArchitectureSiteTests(unittest.TestCase):
    def test_src_gallery_uses_portable_json_project_database(self) -> None:
        src = PLUGIN_ROOT / "src"
        index = (src / "index.html").read_text(encoding="utf-8")
        projects = json.loads((src / "projects.json").read_text(encoding="utf-8"))
        app = (src / "app.js").read_text(encoding="utf-8")
        styles = (src / "styles.css").read_text(encoding="utf-8")

        self.assertNotIn("./architectures.js", index)
        self.assertIn("./app.js", index)
        self.assertIn("diagram-frame", index)
        self.assertIn("viewer-logo", index)
        self.assertIn("menu-toggle", index)
        self.assertIn("download-pptx", index)
        self.assertIn("export-projects", index)
        self.assertIn("project-footer", index)
        self.assertIn('id="action-confirmation"', index)
        self.assertIn('id="confirm-action"', index)
        self.assertIn('aria-label="Exportar proyectos seleccionados como ZIP"', index)
        self.assertIn("<svg", index)
        self.assertNotIn('id="duplicate-project"', index)
        self.assertNotIn("Seleccione proyectos para compartir", index)
        self.assertIn("project-database", index)
        self.assertIn('data-edit-field="title"', index)
        self.assertNotIn('id="architecture-summary"', index)
        self.assertNotIn('data-edit-field="description"', index)
        self.assertIn('scrolling="no"', index)
        self.assertIn("Buscar proyectos", index)
        self.assertIn("Casos, arquitecturas y BoM", index)
        self.assertNotIn("architecture-category", index)
        self.assertNotIn('class="eyebrow"', index)
        self.assertEqual(1, projects["version"])
        self.assertGreaterEqual(len(projects["projects"]), 4)
        self.assertTrue(all(project["path"].startswith("../examples/") for project in projects["projects"]))
        self.assertIn('fetch(DATABASE_URL', app)
        self.assertIn('method: "PUT"', app)
        self.assertIn('const SAVE_URL = "/api/projects"', app)
        self.assertIn("STORAGE_FALLBACK_KEY", app)
        self.assertIn("embeddedPath", app)
        self.assertIn("resizeFrameToContent", app)
        self.assertIn("const maxFrameHeight = Math.max(1, window.innerHeight - headerHeight);", app)
        self.assertIn('frame.style.width = Math.round(frameHeight * 16 / 9) + "px";', app)
        self.assertIn("beginInlineEdit", app)
        self.assertIn('addEventListener("dblclick"', app)
        self.assertIn("duplicateProject", app)
        self.assertIn("deleteProject", app)
        self.assertIn("projectListTitle", app)
        self.assertIn("button.title = project.title;", app)
        self.assertIn("database.projects = projects;", app)
        self.assertIn("confirmAction", app)
        self.assertNotIn("requestInlineEdit", app)
        self.assertIn('"Guardar cambios"', app)
        self.assertIn("ociRenderAllSlides", app)
        self.assertIn("buildPptx", app)
        self.assertIn("pptxThemeXml", app)
        self.assertIn('ppt/theme/theme1.xml', app)
        self.assertIn("supportsPptx", app)
        self.assertIn("requestExport", app)
        self.assertIn('duplicate.className = "duplicate-project"', app)
        self.assertIn('remove.className = "delete-project"', app)
        self.assertNotIn("<span>Duplicar</span>", app)
        self.assertIn('selectionLabel.className = "project-selection"', app)
        self.assertIn("updateExportControl", app)
        self.assertIn("exportSelectedProjects", app)
        self.assertIn("zipStore", app)
        self.assertIn('type: "application/zip"', app)
        self.assertIn('frame.classList.contains("is-deck")', app)
        self.assertIn('doc.documentElement.style.overflowY = "hidden"', app)
        viewer_header_css = styles.split(".viewer-header {", 1)[1].split("}", 1)[0]
        self.assertIn("position: sticky;", viewer_header_css)
        self.assertIn("top: 0;", viewer_header_css)
        self.assertIn("z-index: 10;", viewer_header_css)
        self.assertIn('document.body.classList.toggle("showing-deck", isDeck);', app)
        self.assertIn("body.showing-deck .app-shell", styles)
        self.assertIn("overflow: hidden;", styles)
        self.assertIn(".viewer-logo", styles)
        self.assertIn(".diagram-frame.is-deck", styles)
        self.assertIn(".download-pptx", styles)
        self.assertIn(".viewer-toast", styles)
        self.assertIn("border: 1px solid #b8c5cf;", styles)
        self.assertIn(".project-footer", styles)
        self.assertIn(".duplicate-project", styles)
        self.assertIn(".delete-project", styles)
        self.assertIn(".action-confirmation", styles)
        self.assertIn(".project-row", styles)
        self.assertIn(".architecture-version", styles)
        self.assertIn("text-overflow: ellipsis;", styles)
        self.assertNotIn(".architecture-meta", styles)
        self.assertIn('[data-edit-field].is-editing', styles)
        self.assertNotIn(".eyebrow", styles)
        self.assertNotIn("file://", index + app)
        self.assertNotIn("Seleccione al menos un proyecto para generar el ZIP.", index + app)

    def test_local_server_defaults_to_src_gallery(self) -> None:
        self.assertEqual("127.0.0.1", site_server.DEFAULT_HOST)
        self.assertEqual(8765, site_server.DEFAULT_PORT)
        self.assertEqual("/src/index.html", site_server.DEFAULT_PATH)
        self.assertEqual(PLUGIN_ROOT, site_server.PLUGIN_ROOT)
        self.assertEqual(
            "http://127.0.0.1:8765/src/index.html",
            site_server.local_gallery_url("127.0.0.1", 8765),
        )
        self.assertEqual(
            "http://127.0.0.1:8765/src/index.html?diagram=web-architecture",
            site_server.local_gallery_url("127.0.0.1", 8765, "web-architecture"),
        )

    def test_local_server_validates_project_database_before_writing(self) -> None:
        database = json.loads((PLUGIN_ROOT / "src" / "projects.json").read_text(encoding="utf-8"))

        self.assertIs(database, site_server.validate_project_database(database))
        invalid = json.loads(json.dumps(database))
        invalid["projects"][0]["path"] = "https://example.com/project.html"
        with self.assertRaisesRegex(ValueError, "must reference"):
            site_server.validate_project_database(invalid)

        invalid_image = json.loads(json.dumps(database))
        invalid_image["projects"][0]["caseImageUrl"] = "../assets/project-images/other/case-image.png"
        with self.assertRaisesRegex(ValueError, "caseImageUrl"):
            site_server.validate_project_database(invalid_image)

    def test_case_image_is_persisted_with_a_project_relative_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "assets").mkdir()
            database = {
                "version": 1,
                "updatedAt": "",
                "projects": [{"id": "2026-08-12-10-11-12-123", "familyId": "case", "version": 1, "title": "Case", "description": "Case description", "category": "Case Deck", "format": "deck", "path": "../examples/case.html"}],
            }
            (root / "src" / "projects.json").write_text(json.dumps(database), encoding="utf-8")

            image_url = site_server.save_case_image(root, "2026-08-12-10-11-12-123", "image/png", b"\x89PNG\r\n\x1a\nimage")
            stored = json.loads((root / "src" / "projects.json").read_text(encoding="utf-8"))

            self.assertEqual("../assets/project-images/2026-08-12-10-11-12-123/case-image.png", image_url)
            self.assertEqual(image_url, stored["projects"][0]["caseImageUrl"])
            self.assertEqual(b"\x89PNG\r\n\x1a\nimage", (root / image_url.removeprefix("../")).read_bytes())

            site_server.delete_case_image(root, "2026-08-12-10-11-12-123")
            self.assertNotIn("caseImageUrl", json.loads((root / "src" / "projects.json").read_text(encoding="utf-8"))["projects"][0])
            self.assertFalse((root / "assets" / "project-images" / "2026-08-12-10-11-12-123" / "case-image.png").exists())

    def test_project_export_contains_only_selected_portable_html(self) -> None:
        payload = site_server.build_project_export(PLUGIN_ROOT, ["case-deck-web"])

        with zipfile.ZipFile(BytesIO(payload)) as archive:
            names = set(archive.namelist())
            exported = json.loads(archive.read("src/projects.json"))
            index = archive.read("src/index.html").decode("utf-8")

        self.assertIn("examples/case-deck-web.html", names)
        self.assertIn("src/app.js", names)
        self.assertIn("src/styles.css", names)
        self.assertIn("assets/icon.svg", names)
        self.assertIn("assets/ora.svg", names)
        self.assertEqual(["case-deck-web"], [project["id"] for project in exported["projects"]])
        self.assertIn('"id": "case-deck-web"', index)
        self.assertNotIn('"id": "live-query-ecommerce"', index)

    def test_project_version_materializes_independent_html_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "examples").mkdir()
            source = root / "examples" / "case.html"
            source.write_text("<html>case v1</html>", encoding="utf-8")
            current = {
                "version": 1,
                "updatedAt": "",
                "projects": [
                    {
                        "id": "case",
                        "familyId": "case",
                        "version": 1,
                        "title": "Case",
                        "description": "Case description",
                        "category": "Case Deck",
                        "format": "deck",
                        "path": "../examples/case.html",
                    }
                ],
            }
            updated = json.loads(json.dumps(current))
            updated["projects"].append(
                {
                    **current["projects"][0],
                    "id": "case-v2",
                    "sourceProjectId": "case",
                    "version": 2,
                    "title": "Case — v2",
                    "path": "../examples/case-v2.html",
                }
            )

            created = site_server.materialize_project_versions(root, current, updated)

            self.assertEqual([root / "examples" / "case-v2.html"], created)
            self.assertEqual(source.read_bytes(), created[0].read_bytes())

    def test_project_version_materializes_the_selected_source_within_a_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "examples").mkdir()
            first = root / "examples" / "case.html"
            second = root / "examples" / "case-v2.html"
            first.write_text("<html>first</html>", encoding="utf-8")
            second.write_text("<html>second</html>", encoding="utf-8")
            current = {
                "version": 1,
                "updatedAt": "",
                "projects": [
                    {"id": "case", "familyId": "case", "version": 1, "title": "Case", "description": "Case description", "category": "Case Deck", "format": "deck", "path": "../examples/case.html"},
                    {"id": "case-v2", "familyId": "case", "version": 2, "title": "Case v2", "description": "Case description", "category": "Case Deck", "format": "deck", "path": "../examples/case-v2.html"},
                ],
            }
            updated = json.loads(json.dumps(current))
            updated["projects"].append(
                {**current["projects"][0], "id": "case-v3", "version": 3, "sourceProjectId": "case", "path": "../examples/case-v3.html"}
            )

            created = site_server.materialize_project_versions(root, current, updated)

            self.assertEqual("<html>first</html>", created[0].read_text(encoding="utf-8"))

    def test_project_version_copies_the_selected_case_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "examples").mkdir()
            (root / "assets" / "project-images" / "case").mkdir(parents=True)
            (root / "examples" / "case.html").write_text("<html>case</html>", encoding="utf-8")
            (root / "assets" / "project-images" / "case" / "case-image.png").write_bytes(b"image")
            current = {
                "version": 1,
                "updatedAt": "",
                "projects": [{"id": "case", "familyId": "case", "version": 1, "title": "Case", "description": "Case description", "category": "Case Deck", "format": "deck", "path": "../examples/case.html", "caseImageUrl": "../assets/project-images/case/case-image.png"}],
            }
            updated = json.loads(json.dumps(current))
            updated["projects"].append({**current["projects"][0], "id": "case-v2", "sourceProjectId": "case", "version": 2, "path": "../examples/case-v2.html", "caseImageUrl": "../assets/project-images/case-v2/case-image.png"})

            site_server.materialize_project_versions(root, current, updated)

            self.assertEqual(b"image", (root / "assets" / "project-images" / "case-v2" / "case-image.png").read_bytes())

    def test_portfolio_duplicates_use_timestamp_ids(self) -> None:
        app = (PLUGIN_ROOT / "src" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function timestampProjectId", app)
        self.assertIn("nextTimestampProjectId()", app)
        self.assertIn("const id = nextTimestampProjectId();", app)
        self.assertIn("selectProject(selectedId);", app)

    def test_case_image_prompt_uses_the_actual_case_context(self) -> None:
        prompt = renderer.build_case_image_prompt(
            "Agente de Cobranza",
            {"description": "Consulta información de cobranza por usuarios autorizados."},
        )

        self.assertIn("Agente de Cobranza", prompt)
        self.assertIn("información de cobranza", prompt)
        self.assertNotIn("field-service technicians", prompt)
        self.assertNotIn("autorizados..", prompt)


class SkillPackagingTests(unittest.TestCase):
    def test_plugin_is_published_as_repo_marketplace(self) -> None:
        manifest = renderer.read_json(PLUGIN_MANIFEST)
        marketplace = renderer.read_json(MARKETPLACE)
        plugin_entry = marketplace["plugins"][0]

        self.assertEqual("oci-architecture-diagram", manifest["name"])
        self.assertEqual("0.4.7", manifest["version"])
        self.assertEqual("Joel Gangini", manifest["author"]["name"])
        self.assertEqual("Joel Gangini", manifest["interface"]["developerName"])
        self.assertEqual("oci-architecture", marketplace["name"])
        self.assertEqual("OCI Architecture", marketplace["interface"]["displayName"])
        self.assertEqual(1, len(marketplace["plugins"]))
        self.assertEqual("oci-architecture-diagram", plugin_entry["name"])
        self.assertEqual(
            {"source": "local", "path": "./plugins/oci-architecture-diagram"},
            plugin_entry["source"],
        )
        self.assertEqual(
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            plugin_entry["policy"],
        )
        self.assertEqual("OCI", plugin_entry["category"])

    def test_plugin_exposes_focused_specialist_skills(self) -> None:
        expected = {
            "oci-architecture-diagram": [
                "oci-spec-normalizer",
                "oci-architecture-validator",
                "oci-icon-catalog",
                "oci-diagram-renderer",
                "oci-diagram-visual-qa",
                "Final Delivery Contract",
            ],
            "oci-spec-normalizer": ["Schema v1", "Common Service Synonyms"],
            "oci-architecture-validator": ["Deterministic Validation", "Architecture Checks"],
            "oci-icon-catalog": ["extract_oci_icons.py", "import_oci_svg_icons.py"],
            "oci-diagram-renderer": [
                "generate_oci_diagram.py",
                "render_architecture_prompt_suite.py",
                "serve_architecture_site.py",
                "?diagram=<diagram-id>",
            ],
            "oci-diagram-visual-qa": ["Browser Checks", "diagram-toolbar", "Browser plugin", "Browser Delivery"],
            "oci-architecture-case-deck": ["Start gate", "Workflow", "Delivery"],
            "oci-architecture-commercial-discovery": ["facts", "assumptions"],
            "oci-architecture-solution": ["service map", "sizing driver"],
            "oci-architecture-sizing": ["Oracle Cost Estimator JSON", "pricing"],
            "oci-architecture-curation": ["Audit", "customer evidence"],
        }

        self.assertGreaterEqual(len(list(SKILLS.glob("*/SKILL.md"))), 11)
        for skill_name, required_phrases in expected.items():
            with self.subTest(skill=skill_name):
                skill_path = SKILLS / skill_name / "SKILL.md"
                self.assertTrue(skill_path.exists(), skill_name)
                text = skill_path.read_text(encoding="utf-8")
                metadata = skill_frontmatter(text)
                self.assertEqual(skill_name, metadata.get("name"))
                self.assertGreater(len(metadata.get("description", "")), 40)
                for phrase in required_phrases:
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
