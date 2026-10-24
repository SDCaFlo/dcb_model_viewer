"""Web server for the interactive 3D Digimon Model & Animation Viewer."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dcb_viewer.formats.card_db import load_model_name_map


class DcbViewerHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the Web 3D viewer and GLB models."""

    models_dir: Path = Path("original_iso/extracted/models")
    cdd_path: Path = Path("original_iso/extracted/B/CARD2.CDD")
    static_dir: Path = Path(__file__).parent / "static"
    _cached_catalog: list[dict] | None = None

    @classmethod
    def get_catalog(cls) -> list[dict]:
        if cls._cached_catalog is not None:
            return cls._cached_catalog

        names_map = {}
        if cls.cdd_path.is_file():
            try:
                names_map = load_model_name_map(cls.cdd_path)
            except Exception:
                pass

        catalog: list[dict] = []
        if cls.models_dir.is_dir():
            glb_files = sorted(list(cls.models_dir.glob("*.glb")) + list(cls.models_dir.glob("*.GLB")))
            # Deduplicate
            found = {p.resolve(): p for p in glb_files}
            for p in sorted(found.values(), key=lambda x: x.name.upper()):
                stem = p.stem.upper()
                name = stem

                # Check if stem is numeric (e.g. '003', '004')
                try:
                    m_id = int(stem)
                    if m_id in names_map:
                        name = f"{names_map[m_id]} (#{m_id:03d})"
                    else:
                        name = f"Digimon #{m_id:03d}"
                except ValueError:
                    if stem.startswith("BG"):
                        name = f"Stage Arena ({stem})"
                    elif stem.startswith("AREA"):
                        name = f"Battle Arena ({stem})"

                catalog.append({
                    "id": p.stem,
                    "name": name,
                    "filename": p.name,
                    "size": p.stat().st_size,
                    "anim_count": 8 if not stem.startswith("BG") and not stem.startswith("AREA") else 0,
                })

        cls._cached_catalog = catalog
        return catalog

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            index_file = self.static_dir / "index.html"
            if index_file.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(index_file.read_bytes())
                return

        elif path == "/api/models":
            catalog = self.get_catalog()
            data = json.dumps(catalog).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        elif path.startswith("/models/"):
            filename = urllib.parse.unquote(path[len("/models/"):])
            glb_path = self.models_dir / filename
            if glb_path.is_file():
                data = glb_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "model/gltf-binary")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_error(404, f"Model file not found: {filename}")
                return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format: str, *args) -> None:
        # Cleaner console logs
        sys.stdout.write(f"[DCB Server] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()


def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
    models_dir: str | Path | None = None,
) -> None:
    """Launches the Web 3D Viewer server."""
    if models_dir is not None:
        DcbViewerHandler.models_dir = Path(models_dir)

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, DcbViewerHandler)
    url = f"http://{host}:{port}/"

    print("=" * 65)
    print("  DCB MODEL VIEWER - INTERACTIVE 3D WEB VIEWER")
    print("=" * 65)
    print(f"  * Serving models from: {DcbViewerHandler.models_dir.resolve()}")
    print(f"  * Total models indexed: {len(DcbViewerHandler.get_catalog())}")
    print(f"  * Viewer URL: {url}")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 65)

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()
