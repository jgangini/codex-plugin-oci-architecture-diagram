from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
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
        r'<g class="edge-label[^"]*" transform="translate\(([-0-9.]+) ([-0-9.]+)\)"><rect x="([-0-9.]+)" y="([-0-9.]+)" width="([-0-9.]+)" height="([-0-9.]+)"',
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
    def test_src_gallery_lists_generated_oke_adb_architecture(self) -> None:
        src = PLUGIN_ROOT / "src"
        index = (src / "index.html").read_text(encoding="utf-8")
        architectures = (src / "architectures.js").read_text(encoding="utf-8")
        app = (src / "app.js").read_text(encoding="utf-8")
        styles = (src / "styles.css").read_text(encoding="utf-8")

        self.assertIn("./architectures.js", index)
        self.assertIn("./app.js", index)
        self.assertIn("diagram-frame", index)
        self.assertIn("viewer-logo", index)
        self.assertIn("menu-toggle", index)
        self.assertIn('scrolling="no"', index)
        self.assertIn("Search architectures", index)
        self.assertIn("Architectures", index)
        self.assertNotIn("architecture-category", index)
        self.assertNotIn('class="eyebrow"', index)
        self.assertNotIn("Abrir", index)
        self.assertNotIn("Filtrar", index)
        self.assertIn("arquitectura-web-oke-adb", architectures)
        self.assertIn("../examples/arquitectura-web-oke-adb.html", architectures)
        self.assertIn("arquitectura-web-oke-adb-generative-ai", architectures)
        self.assertIn("../examples/arquitectura-web-oke-adb-generative-ai.html", architectures)
        self.assertIn("window.OCI_ARCHITECTURES", architectures)
        self.assertIn("embeddedPath", app)
        self.assertIn("hideRepeatedFrameTitle", app)
        self.assertIn("resizeFrameToContent", app)
        self.assertIn('doc.documentElement.style.overflowY = "hidden"', app)
        viewer_header_css = styles.split(".viewer-header {", 1)[1].split("}", 1)[0]
        self.assertIn("position: sticky;", viewer_header_css)
        self.assertIn("top: 0;", viewer_header_css)
        self.assertIn("z-index: 10;", viewer_header_css)
        self.assertIn(".viewer-logo", styles)
        self.assertNotIn(".eyebrow", styles)
        self.assertNotIn("file://", index + architectures + app)

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


class SkillPackagingTests(unittest.TestCase):
    def test_plugin_is_published_as_repo_marketplace(self) -> None:
        manifest = renderer.read_json(PLUGIN_MANIFEST)
        marketplace = renderer.read_json(MARKETPLACE)
        plugin_entry = marketplace["plugins"][0]

        self.assertEqual("oci-architecture-diagram", manifest["name"])
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
        }

        self.assertGreaterEqual(len(list(SKILLS.glob("*/SKILL.md"))), 6)
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
