#!/usr/bin/env python3
"""Serve the local OCI architecture diagram gallery over HTTP."""

from __future__ import annotations

import argparse
import io
import json
import re
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_PATH = "/src/index.html"
MAX_DATABASE_BYTES = 2 * 1024 * 1024
MAX_CASE_IMAGE_BYTES = 3 * 1024 * 1024
PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CASE_IMAGE_URL = re.compile(r"^\.\./assets/project-images/([A-Za-z0-9][A-Za-z0-9._-]{0,127})/case-image\.(png|jpg|webp)$")
CASE_IMAGE_ROUTE = re.compile(r"^/api/projects/([A-Za-z0-9][A-Za-z0-9._-]{0,127})/case-image$")
CASE_IMAGE_TYPES = {
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
    "image/webp": ("webp", b"RIFF"),
}
DATABASE_LOCK = threading.Lock()


def validate_project_database(value: object) -> dict:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("Project database must be a version 1 JSON object.")
    projects = value.get("projects")
    if not isinstance(projects, list) or len(projects) > 500:
        raise ValueError("Project database must contain at most 500 projects.")
    seen_ids: set[str] = set()
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise ValueError(f"projects[{index}] must be an object.")
        project_id = project.get("id")
        if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
            raise ValueError(f"projects[{index}].id is invalid.")
        if project_id in seen_ids:
            raise ValueError(f"Duplicate project id: {project_id}")
        seen_ids.add(project_id)
        for field in ("title", "description", "category"):
            if not isinstance(project.get(field), str) or not project[field].strip():
                raise ValueError(f"projects[{index}].{field} must be a non-empty string.")
        if project.get("format") not in {"deck", "diagram"}:
            raise ValueError(f"projects[{index}].format must be deck or diagram.")
        if not isinstance(project.get("version"), int) or project["version"] < 1:
            raise ValueError(f"projects[{index}].version must be a positive integer.")
        path = project.get("path")
        if not isinstance(path, str) or not path.startswith("../examples/") or not path.endswith(".html"):
            raise ValueError(f"projects[{index}].path must reference ../examples/*.html.")
        family_id = project.get("familyId", project_id)
        if not isinstance(family_id, str) or not PROJECT_ID.fullmatch(family_id):
            raise ValueError(f"projects[{index}].familyId is invalid.")
        source_project_id = project.get("sourceProjectId")
        if source_project_id is not None and (
            not isinstance(source_project_id, str) or not PROJECT_ID.fullmatch(source_project_id)
        ):
            raise ValueError(f"projects[{index}].sourceProjectId is invalid.")
        case_image_url = project.get("caseImageUrl")
        if case_image_url is not None:
            match = CASE_IMAGE_URL.fullmatch(case_image_url) if isinstance(case_image_url, str) else None
            if match is None or match.group(1) != project_id:
                raise ValueError(f"projects[{index}].caseImageUrl is invalid.")
    if value.get("updatedAt") is not None and not isinstance(value.get("updatedAt"), str):
        raise ValueError("updatedAt must be a string.")
    return value


def safe_export_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or "project"


def resolve_project_html(root: Path, path: str) -> Path:
    examples_root = (root / "examples").resolve()
    resolved = (root / "src" / path).resolve()
    if resolved.parent != examples_root:
        raise ValueError("Project HTML must stay directly under examples/.")
    return resolved


def case_image_path(root: Path, project_id: str, extension: str) -> Path:
    image_root = (root / "assets" / "project-images").resolve()
    target = (image_root / project_id / f"case-image.{extension}").resolve()
    if target.parent.parent != image_root:
        raise ValueError("Case image path must stay within assets/project-images.")
    return target


def validate_case_image(content_type: str, payload: bytes) -> tuple[str, str]:
    media_type = content_type.split(";", 1)[0].strip().lower()
    metadata = CASE_IMAGE_TYPES.get(media_type)
    if metadata is None or not payload or len(payload) > MAX_CASE_IMAGE_BYTES:
        raise ValueError("Use a PNG, JPEG or WebP image up to 3 MB.")
    extension, signature = metadata
    if not payload.startswith(signature) or (media_type == "image/webp" and payload[8:12] != b"WEBP"):
        raise ValueError("The uploaded image does not match its declared format.")
    return media_type, extension


def save_case_image(root: Path, project_id: str, content_type: str, payload: bytes) -> str:
    _media_type, extension = validate_case_image(content_type, payload)
    with DATABASE_LOCK:
        database_path = root / "src" / "projects.json"
        database = validate_project_database(json.loads(database_path.read_text(encoding="utf-8")))
        project = next((item for item in database["projects"] if item["id"] == project_id), None)
        if project is None:
            raise ValueError("Unknown project id.")
        target = case_image_path(root, project_id, extension)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_image = target.with_suffix(target.suffix + ".tmp")
        temporary_database = database_path.with_suffix(".json.tmp")
        try:
            temporary_image.write_bytes(payload)
            project["caseImageUrl"] = f"../assets/project-images/{project_id}/case-image.{extension}"
            serialized = json.dumps(database, ensure_ascii=False, indent=2) + "\n"
            temporary_database.write_text(serialized, encoding="utf-8")
            temporary_image.replace(target)
            temporary_database.replace(database_path)
            for candidate_extension in {"png", "jpg", "webp"} - {extension}:
                case_image_path(root, project_id, candidate_extension).unlink(missing_ok=True)
        except OSError:
            temporary_image.unlink(missing_ok=True)
            temporary_database.unlink(missing_ok=True)
            raise
    return project["caseImageUrl"]


def delete_case_image(root: Path, project_id: str) -> None:
    with DATABASE_LOCK:
        database_path = root / "src" / "projects.json"
        database = validate_project_database(json.loads(database_path.read_text(encoding="utf-8")))
        project = next((item for item in database["projects"] if item["id"] == project_id), None)
        if project is None:
            raise ValueError("Unknown project id.")
        temporary_database = database_path.with_suffix(".json.tmp")
        project.pop("caseImageUrl", None)
        try:
            temporary_database.write_text(json.dumps(database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary_database.replace(database_path)
            for extension in ("png", "jpg", "webp"):
                case_image_path(root, project_id, extension).unlink(missing_ok=True)
        except OSError:
            temporary_database.unlink(missing_ok=True)
            raise


def materialize_project_versions(root: Path, current: dict, updated: dict) -> list[Path]:
    current_by_id = {project["id"]: project for project in current["projects"]}
    created: list[Path] = []
    created_images: list[Path] = []
    try:
        for project in updated["projects"]:
            if project["id"] in current_by_id:
                continue
            family_id = project.get("familyId", project["id"])
            candidates = [
                candidate
                for candidate in current["projects"]
                if candidate.get("familyId", candidate["id"]) == family_id
            ]
            if not candidates:
                raise ValueError(f"No source project found for version {project['id']}.")
            # A browser sends the complete project database. Its new version must
            # originate from the project that was duplicated, not merely from the
            # highest version in the same family.
            source_id = project.get("sourceProjectId")
            if source_id is not None:
                source_project = next((candidate for candidate in candidates if candidate["id"] == source_id), None)
                if source_project is None:
                    raise ValueError(f"Source project {source_id} is not in family {family_id}.")
            else:
                source_project = max(candidates, key=lambda candidate: candidate["version"])
            source = resolve_project_html(root, source_project["path"])
            target = resolve_project_html(root, project["path"])
            if target.exists():
                raise ValueError(f"Project HTML already exists for {project['id']}.")
            if not source.is_file():
                raise ValueError(f"Source HTML is missing for {source_project['id']}.")
            target.write_bytes(source.read_bytes())
            created.append(target)
            source_image_url = source_project.get("caseImageUrl")
            if source_image_url:
                image_match = CASE_IMAGE_URL.fullmatch(source_image_url)
                if image_match is None:
                    raise ValueError(f"Source project {source_project['id']} has an invalid case image.")
                source_image = case_image_path(root, source_project["id"], image_match.group(2))
                if not source_image.is_file():
                    raise ValueError(f"Source project {source_project['id']} case image is missing.")
                target_image = case_image_path(root, project["id"], image_match.group(2))
                target_image.parent.mkdir(parents=True, exist_ok=True)
                target_image.write_bytes(source_image.read_bytes())
                created_images.append(target_image)
                project["caseImageUrl"] = f"../assets/project-images/{project['id']}/case-image.{image_match.group(2)}"
    except (OSError, ValueError):
        for path in created:
            path.unlink(missing_ok=True)
        for path in created_images:
            path.unlink(missing_ok=True)
        raise
    return created


def build_project_export(root: Path, project_ids: list[str]) -> bytes:
    database_path = root / "src" / "projects.json"
    database = validate_project_database(json.loads(database_path.read_text(encoding="utf-8")))
    requested = set(project_ids)
    selected = [project for project in database["projects"] if project["id"] in requested]
    if not selected or len(selected) != len(requested):
        raise ValueError("Select one or more known project ids.")
    portable_projects = []
    export_files: list[tuple[str, bytes]] = []
    for project in selected:
        source = resolve_project_html(root, project["path"])
        if not source.is_file():
            raise ValueError(f"Missing portable HTML for project {project['id']}.")
        file_name = safe_export_name(project["id"]) + ".html"
        portable_projects.append({**project, "path": "../examples/" + file_name})
        export_files.append(("examples/" + file_name, source.read_bytes()))
        case_image_url = project.get("caseImageUrl")
        if case_image_url:
            match = CASE_IMAGE_URL.fullmatch(case_image_url)
            if match is None:
                raise ValueError(f"Invalid case image for project {project['id']}.")
            image = case_image_path(root, project["id"], match.group(2))
            if not image.is_file():
                raise ValueError(f"Missing case image for project {project['id']}.")
            export_files.append((case_image_url.removeprefix("../"), image.read_bytes()))
    portable_database = {
        "version": 1,
        "updatedAt": database.get("updatedAt", ""),
        "projects": portable_projects,
    }
    database_text = json.dumps(portable_database, ensure_ascii=False, indent=2) + "\n"
    index = (root / "src" / "index.html").read_text(encoding="utf-8")
    embedded = json.dumps(portable_database, ensure_ascii=False).replace("<", "\\u003c")
    portable_index, replacements = re.subn(
        r'<script id="project-database" type="application/json">[\s\S]*?</script>',
        f'<script id="project-database" type="application/json">{embedded}</script>',
        index,
        count=1,
    )
    if replacements != 1:
        raise ValueError("Portable gallery is missing its embedded project database.")
    export_files.extend(
        [
            ("src/index.html", portable_index.encode("utf-8")),
            ("src/app.js", (root / "src" / "app.js").read_bytes()),
            ("src/styles.css", (root / "src" / "styles.css").read_bytes()),
            ("src/projects.json", database_text.encode("utf-8")),
            ("assets/icon.svg", (root / "assets" / "icon.svg").read_bytes()),
            ("assets/ora.svg", (root / "assets" / "ora.svg").read_bytes()),
            (
                "README.txt",
                (
                    "OCI Architecture Projects\r\n\r\n"
                    "Abra src/index.html para navegar los proyectos incluidos. "
                    "Use serve_architecture_site.py para persistir ediciones directamente en projects.json.\r\n"
                ).encode("utf-8"),
            ),
        ]
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in export_files:
            archive.writestr(name, content)
    return output.getvalue()


def make_handler(root: Path) -> type[SimpleHTTPRequestHandler]:
    database_path = root / "src" / "projects.json"

    class GalleryRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def end_headers(self) -> None:
            if self.path.split("?", 1)[0] == "/src/projects.json":
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/export":
                super().do_GET()
                return
            try:
                project_ids = [item for value in parse_qs(parsed.query).get("ids", []) for item in value.split(",") if item]
                payload = build_project_export(root, project_ids)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self.send_error(400, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="oci-architecture-projects.zip"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_PUT(self) -> None:
            route = self.path.split("?", 1)[0]
            image_match = CASE_IMAGE_ROUTE.fullmatch(route)
            if image_match is not None:
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_error(403, "Project editing is local-only.")
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > MAX_CASE_IMAGE_BYTES:
                        raise ValueError("Use a PNG, JPEG or WebP image up to 3 MB.")
                    image_url = save_case_image(root, image_match.group(1), self.headers.get("Content-Type", ""), self.rfile.read(length))
                except (OSError, ValueError) as exc:
                    body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = json.dumps({"ok": True, "caseImageUrl": image_url}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if route != "/api/projects":
                self.send_error(404)
                return
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                self.send_error(403, "Project editing is local-only.")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_DATABASE_BYTES:
                    raise ValueError("Invalid project database size.")
                payload = validate_project_database(json.loads(self.rfile.read(length).decode("utf-8")))
                serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                temporary = database_path.with_suffix(".json.tmp")
                with DATABASE_LOCK:
                    current = validate_project_database(json.loads(database_path.read_text(encoding="utf-8")))
                    created = materialize_project_versions(root, current, payload)
                    try:
                        temporary.write_text(serialized, encoding="utf-8")
                        temporary.replace(database_path)
                    except OSError:
                        for path in created:
                            path.unlink(missing_ok=True)
                        raise
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self) -> None:
            image_match = CASE_IMAGE_ROUTE.fullmatch(self.path.split("?", 1)[0])
            if image_match is None:
                self.send_error(404)
                return
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                self.send_error(403, "Project editing is local-only.")
                return
            try:
                delete_case_image(root, image_match.group(1))
            except (OSError, ValueError) as exc:
                body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(204)
            self.end_headers()

    return GalleryRequestHandler


def make_server(host: str, port: int, root: Path) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(root))


def local_gallery_url(host: str, port: int, diagram: str = "") -> str:
    url = f"http://{host}:{port}{DEFAULT_PATH}"
    if diagram:
        url = f"{url}?{urlencode({'diagram': diagram})}"
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the OCI architecture diagram site.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--root", default=str(PLUGIN_ROOT))
    parser.add_argument("--diagram", default="", help="Optional architecture id to include in the local gallery URL.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "src" / "index.html").exists():
        raise SystemExit(f"Missing site entrypoint: {root / 'src' / 'index.html'}")

    server = make_server(args.host, args.port, root)
    url = local_gallery_url(args.host, args.port, args.diagram)
    print(f"Serving OCI Architecture Diagram site from {root}")
    print(f"Open {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
