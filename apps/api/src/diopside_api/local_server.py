from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import diopside_api.handler as api_handler
from diopside_core import MemoryRepository


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def _handle(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else None
        event = {
            "rawPath": parsed.path,
            "requestContext": {"http": {"method": self.command}},
            "queryStringParameters": {k: v[-1] for k, v in parse_qs(parsed.query).items()},
            "headers": dict(self.headers.items()),
            "body": body,
        }
        result = api_handler.lambda_handler(event, None)
        self.send_response(result["statusCode"])
        for key, value in result["headers"].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(result["body"].encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    seed_local_fixture_repository()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"diopside api listening on http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


def seed_local_fixture_repository() -> None:
    if os.environ.get("DIOPSIDE_LOCAL_FIXTURE_MODE") != "true":
        return
    root = Path(os.environ.get("DIOPSIDE_PUBLIC_DATA_DIR", "data/fixtures/public"))
    manifest_path = root / "latest-manifest.json"
    if not manifest_path.exists():
        return
    repo = MemoryRepository()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_path = root / str(manifest.get("indexes", {}).get("videos_latest", "")).lstrip("/")
    if not index_path.exists():
        return
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in index.get("items", []):
        detail = {}
        detail_path = root / str(item.get("detail_path", "")).lstrip("/")
        if detail_path.exists():
            detail = json.loads(detail_path.read_text(encoding="utf-8")).get("video", {})
        repo.put_video({**item, **detail, "public": True})
    api_handler._REPOSITORY = repo


if __name__ == "__main__":
    main()
