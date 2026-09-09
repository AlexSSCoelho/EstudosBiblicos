"""Serve the generated study library to the local network.

The editorial source and build pipeline live outside the serving layer. The
server exposes only ``dist/`` and never infers titles, types or summaries by
scraping generated HTML.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socket
import socketserver
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_ROOT = ROOT / "dist"
DEFAULT_PORT = 8000


def get_local_ip() -> str:
    """Return the preferred local-network address without sending a request."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def ensure_dist() -> None:
    """Build the library only when its generated entry point is unavailable."""
    if (DIST_ROOT / "index.html").is_file() and (DIST_ROOT / "manifest.json").is_file():
        return

    command = [sys.executable, str(ROOT / "build.py")]
    print("Saída gerada não encontrada; executando o build completo...")
    subprocess.run(command, cwd=ROOT, check=True)


class UTF8HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler with explicit UTF-8 text types and no-cache development headers."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a biblioteca gerada em dist/.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dist()
    handler = functools.partial(UTF8HttpRequestHandler, directory=str(DIST_ROOT))

    local_ip = get_local_ip()
    print("=" * 65)
    print(" SERVIDOR DE ESTUDOS BÍBLICOS INICIADO")
    print("=" * 65)
    print(f" Computador: http://localhost:{args.port}")
    print(f" Rede local: http://{local_ip}:{args.port}")
    print(" Para acesso externo, use o túnel/Tailscale já configurado.")
    print(" Pressione Ctrl+C para encerrar.")
    print("=" * 65)

    class ReusableThreadingServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ReusableThreadingServer(("0.0.0.0", args.port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
