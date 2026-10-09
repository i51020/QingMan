"""青蔓 QingMan · 本地 HTTP 服务入口。

职责：端口扫描、静态文件服务、JSON 接口分发、启动后打开浏览器。
仅监听 127.0.0.1，不对外暴露。
"""

from __future__ import annotations

import json
import mimetypes
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from server import config, routes
from server.dtree_core import TreeError, message

STATIC_SUFFIX_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "QingMan/" + config.read_version()

    # ---------- 基础工具 ----------

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[%s] %s\n" % (config.APP_NAME_EN, fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj: object) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _fail(self, http_code: int, code: str, **detail: object) -> None:
        self._json(http_code, {
            "ok": False,
            "code": code,
            "message": message(code, **detail),
            "detail": detail,
        })

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > config.MAX_BODY_BYTES:
            raise TreeError("bodyTooLarge", limit=config.MAX_BODY_BYTES)
        return self.rfile.read(length) if length > 0 else b""

    # ---------- 路由 ----------

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == routes.HEALTH_PATH:
            self._json(200, routes.health())
            return
        self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != routes.GENERATE_PATH:
            self._fail(404, "notFound", path=path)
            return
        try:
            raw = self._read_body()
        except TreeError as exc:
            self._fail(413, exc.code, **exc.detail)
            return
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._fail(400, "badJson")
            return
        if not isinstance(payload, dict):
            self._fail(400, "badJson")
            return
        try:
            self._json(200, routes.generate(payload))
        except TreeError as exc:
            self._fail(400, exc.code, **exc.detail)
        except OSError as exc:
            self._fail(500, "ioError", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - 兜底，避免服务崩溃
            self._fail(500, "internalError", message=str(exc))

    # ---------- 静态文件 ----------

    def _serve_static(self, url_path: str) -> None:
        rel = unquote(url_path).lstrip("/") or "index.html"
        if rel.endswith("/"):
            rel += "index.html"

        web_root = config.WEB_DIR.resolve()
        candidate = (web_root / rel).resolve()

        try:
            candidate.relative_to(web_root)
        except ValueError:
            self._fail(403, "badPath")
            return

        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            self._fail(404, "notFound", path=url_path)
            return

        ctype = STATIC_SUFFIX_TYPES.get(candidate.suffix.lower())
        if ctype is None:
            ctype = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        try:
            self._send(200, candidate.read_bytes(), ctype)
        except OSError as exc:
            self._fail(500, "ioError", message=str(exc))


def _bind_server() -> ThreadingHTTPServer:
    last_error: OSError | None = None
    for port in range(config.PORT_START, config.PORT_END + 1):
        try:
            return ThreadingHTTPServer((config.HOST, port), Handler)
        except OSError as exc:
            last_error = exc
            continue
    raise SystemExit(
        f"[{config.APP_NAME_EN}] 端口 {config.PORT_START}-{config.PORT_END} 全部被占用：{last_error}"
    )


def _open_browser_later(url: str) -> None:
    if not config.OPEN_BROWSER:
        return
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()


def main() -> None:
    version = config.read_version()
    httpd = _bind_server()
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{port}/"

    print(f"[{config.APP_NAME_ZH} {config.APP_NAME_EN}] 版本 {version}")
    print(f"[{config.APP_NAME_ZH}] 服务地址 {url}")
    print(f"[{config.APP_NAME_ZH}] 项目根目录 {config.PROJECT_DIR}")
    print(f"[{config.APP_NAME_ZH}] 按 Ctrl+C 停止服务")

    _open_browser_later(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{config.APP_NAME_ZH}] 服务已停止")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
