#!/usr/bin/env python3
"""Serve the local OCI architecture diagram gallery over HTTP."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_PATH = "/src/index.html"


def make_server(host: str, port: int, root: Path) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    return ThreadingHTTPServer((host, port), handler)


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
