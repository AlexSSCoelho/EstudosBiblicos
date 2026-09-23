"""Serve the generated study library to the local network.

The editorial source and build pipeline live outside the serving layer. The
server exposes only ``dist/`` and never infers titles, types or summaries by
scraping generated HTML.
"""

from __future__ import annotations

import argparse
import errno
import functools
import http.server
import socket
import socketserver
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
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
    parser.add_argument("--open", action="store_true", help="Abre a biblioteca no navegador uma vez.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dist()
    handler = functools.partial(UTF8HttpRequestHandler, directory=str(DIST_ROOT))
    library_url = f"http://127.0.0.1:{args.port}/"

    class ReusableThreadingServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        httpd = ReusableThreadingServer(("0.0.0.0", args.port), handler)
    except OSError as exc:
        if not args.open or exc.errno not in (errno.EADDRINUSE, errno.EACCES):
            raise

        try:
            with urllib.request.urlopen(library_url, timeout=2) as response:
                is_library = b'<body class="library-page">' in response.read(2048)
        except (OSError, urllib.error.URLError):
            is_library = False

        if not is_library:
            raise RuntimeError(f"A porta {args.port} não está disponível para esta biblioteca.") from exc

        print("A biblioteca já está em execução; abrindo a página existente.")
        webbrowser.open(library_url)
        return

    with httpd:
        local_ip = get_local_ip()
        print("=" * 65)
        print(" SERVIDOR DE ESTUDOS BÍBLICOS INICIADO")
        print("=" * 65)
        print(f" Computador: http://localhost:{args.port}")
        print(f" Rede local: http://{local_ip}:{args.port}")
        print(" Para acesso externo, use o túnel/Tailscale já configurado.")
        print(" Pressione Ctrl+C para encerrar.")
        print("=" * 65)

        if args.open:
            webbrowser.open(library_url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
