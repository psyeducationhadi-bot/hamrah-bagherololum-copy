#!/usr/bin/env python3
"""Zero-risk lightweight static dev server for Hamrah Bagherololum Copy.

Features:
- Pure Python standard library (zero external dependencies).
- Strictly serves the repository root directory regardless of caller working directory.
- Injects standard CORS headers (Access-Control-Allow-Origin: *).
- Pre-registers correct MIME types for Persian web fonts (.woff2), PWA manifests (.webmanifest), and JSON.
- Clean startup banner and graceful shutdown on Ctrl+C.
"""

import argparse
import http.server
import mimetypes
import socketserver
import sys
from pathlib import Path

# Ensure critical web asset MIME types are accurately registered on all operating systems
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Canonical project root resolution: parent of scripts/ folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static HTTP request handler with CORS support and correct MIME types."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def run_server(host="127.0.0.1", port=8000):
    handler = CORSRequestHandler
    socketserver.TCPServer.allow_reuse_address = True

    try:
        with socketserver.TCPServer((host, port), handler) as httpd:
            print("=" * 70)
            print(" HAMRAH BAGHEROLOLUM -- LOCAL DEV SERVER")
            print("=" * 70)
            print(f" Serving Root   : {PROJECT_ROOT}")
            print(f" Server URL     : http://{host}:{port}/")
            print(f" Application SPA: http://{host}:{port}/index.html")
            print(" Press Ctrl+C to stop.")
            print("-" * 70)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDev server stopped gracefully.")
    except OSError as e:
        print(f"Error starting dev server on {host}:{port}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hamrah Bagherololum Dev Server")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--bind", "-b", default="127.0.0.1", help="Address to bind (default: 127.0.0.1)")
    args = parser.parse_args()
    run_server(host=args.bind, port=args.port)
