"""本機網頁伺服器：提供耳機麥克風操作介面與 Agent Runtime API。"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from .pipeline import AgentRuntime


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
INDEX_FILE = WEB_ROOT / "index.html"


class DeafRequestHandler(BaseHTTPRequestHandler):
    runtime = AgentRuntime()

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            body = INDEX_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/health":
            self._send_json(200, {"status": "ok", "service": "deaf-agent-runtime"})
            return
        self._send_json(404, {"error": "找不到這個路徑"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/api/process":
            self._send_json(404, {"error": "找不到這個 API"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON 必須是物件")
            result = self.runtime.run(payload)
            self._send_json(200, result)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
            self._send_json(400, {"error": f"輸入資料格式錯誤：{exc}"})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[Deaf Web] {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DeafRequestHandler)
    print("Deaf Agent 網頁已啟動： http://127.0.0.1:8000")
    print("按 Ctrl+C 停止伺服器")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n正在停止網頁伺服器")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

