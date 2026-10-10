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
from urllib.parse import unquote, urlparse, urlsplit

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


def host_of(value: str) -> str:
    """从 Host 头或 Origin 中取出主机名（小写、去端口、去 IPv6 方括号）。

    `127.0.0.1:8765` → `127.0.0.1`；`http://localhost:8765` → `localhost`；
    `[::1]:8765` → `::1`；空值或非法值 → `""`。
    """
    text = (value or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = "//" + text
    try:
        name = urlsplit(text).hostname
    except ValueError:
        return ""
    return (name or "").lower()


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

    # ---------- 调用来源校验（N1） ----------

    def _guard(self) -> bool:
        """校验调用来源。通过返回 True；不通过时已写出 403 并返回 False。

        两道检查：
          ① Host 必须指向回环地址 —— 阻断 DNS rebinding（攻击者域名解析到 127.0.0.1
             时，浏览器发出的 Host 仍是攻击者域名，不在白名单内）。
          ② 若带 Origin，其 host 也必须在白名单内 —— 阻断跨站页面调用。
        """
        raw_host = self.headers.get("Host") or ""
        if host_of(raw_host) not in config.ALLOWED_HOSTS:
            self._fail(403, "hostRejected", host=raw_host or "(缺失)")
            return False

        origin = (self.headers.get("Origin") or "").strip()
        if origin:
            # 严格要求与本站同源：scheme 必须是 http、host 在白名单、端口为绑定端口。
            # `Origin: null`（沙箱化 iframe / data: / file:）在此被拒（scheme 为空）。
            parts = urlsplit(origin)
            try:
                origin_port = parts.port
            except ValueError:
                origin_port = None
            bound_port = self.server.server_address[1]
            if (
                parts.scheme != "http"
                or (parts.hostname or "").lower() not in config.ALLOWED_HOSTS
                or origin_port != bound_port
            ):
                self._fail(403, "originRejected", origin=origin)
                return False
        return True

    def _guard_write(self) -> bool:
        """写操作额外门槛：必须携带自定义防护头。

        跨站页面要携带自定义头必然先触发 CORS 预检，而本服务不响应预检
        （do_OPTIONS 一律拒绝），故该头可阻断「跨站盲发 POST」。
        同源请求携带自定义头不触发预检，不影响正常使用。
        """
        value = (self.headers.get(config.GUARD_HEADER) or "").strip()
        if value != config.GUARD_HEADER_VALUE:
            self._fail(403, "missingGuardHeader", header=config.GUARD_HEADER)
            return False
        return True

    # ---------- 路由 ----------

    def do_GET(self) -> None:  # noqa: N802
        if not self._guard():
            return
        try:
            path = urlparse(self.path).path
            if path == routes.HEALTH_PATH:
                self._json(200, routes.health())
                return
            if path == routes.ENV_PATH:
                # 同步注入 OS 语言的小脚本：普通 <script src> 加载，早于 module 脚本执行，
                # 因此首屏就能按系统语言渲染，不会先画一遍再跳变（V0.0.14）
                body = routes.env_script().encode("utf-8")
                self._send(200, body, "text/javascript; charset=utf-8")
                return
            if path == routes.EDITOR_PATH:
                try:
                    self._json(200, routes.load_editor())
                except TreeError as exc:
                    self._fail(400, exc.code, **exc.detail)
                except OSError as exc:
                    self._fail(500, "ioError", message=str(exc))
                return
            if path == routes.TEMPLATES_PATH:
                self._json(200, routes.list_templates())
                return
            if path.startswith(routes.TEMPLATES_PATH + "/"):
                # 文件名经 URL 编码（模板名含中文），先解码再交给路由层过白名单
                name = unquote(path[len(routes.TEMPLATES_PATH) + 1:])
                try:
                    self._json(200, routes.load_template(name))
                except TreeError as exc:
                    self._fail(404, exc.code, **exc.detail)
                except OSError as exc:
                    self._fail(500, "ioError", message=str(exc))
                return
            self._serve_static(path)
        except Exception as exc:  # noqa: BLE001 - 兜底，避免服务崩溃（对齐 do_POST）
            self._fail(500, "internalError", message=str(exc))

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard() or not self._guard_write():
            return
        path = urlparse(self.path).path
        # POST /api/templates = 另存为模板（V0.0.13）；/api/templates/<name> = 重命名（V0.0.20）；
        # /api/launch-icon = 皮肤联动图标上传（V0.0.15）—— 与生成、快捷方式同为写操作
        is_rename = path.startswith(routes.TEMPLATES_PATH + "/")
        if not is_rename and path not in (routes.GENERATE_PATH, routes.SHORTCUT_PATH,
                                          routes.TEMPLATES_PATH, routes.ICON_PATH):
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
            if is_rename:
                name = unquote(path[len(routes.TEMPLATES_PATH) + 1:])
                self._json(200, routes.rename_template(name, payload))
            elif path == routes.GENERATE_PATH:
                self._json(200, routes.generate(payload))
            elif path == routes.TEMPLATES_PATH:
                self._json(200, routes.save_template(payload))
            elif path == routes.ICON_PATH:
                self._json(200, routes.save_launch_icon(payload))
            else:
                self._json(200, routes.create_shortcut(payload))
        except TreeError as exc:
            self._fail(400, exc.code, **exc.detail)
        except OSError as exc:
            self._fail(500, "ioError", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - 兜底，避免服务崩溃
            self._fail(500, "internalError", message=str(exc))

    def do_PUT(self) -> None:  # noqa: N802
        """PUT /api/editor —— 保存编辑态文档。

        属写操作：同样要过 _guard_write()（防护头）。PUT 无法由 HTML 表单发出，
        比 POST 更不易被跨站盲发，但仍按写操作同等对待。
        """
        if not self._guard() or not self._guard_write():
            return
        path = urlparse(self.path).path
        if path != routes.EDITOR_PATH:
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
            self._json(200, routes.save_editor(payload))
        except TreeError as exc:
            self._fail(400, exc.code, **exc.detail)
        except OSError as exc:
            self._fail(500, "ioError", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - 兜底，避免服务崩溃
            self._fail(500, "internalError", message=str(exc))

    def do_DELETE(self) -> None:  # noqa: N802
        """DELETE /api/templates/<name> —— 删除单套模板（V0.0.20，软删除入 .trash）。

        属写操作：与 POST/PUT 同等，要过 `_guard_write()`（防护头）。
        """
        if not self._guard() or not self._guard_write():
            return
        path = urlparse(self.path).path
        if not path.startswith(routes.TEMPLATES_PATH + "/"):
            self._fail(404, "notFound", path=path)
            return
        # 文件名经 URL 编码（模板名含中文），先解码再交给路由层过白名单
        name = unquote(path[len(routes.TEMPLATES_PATH) + 1:])
        try:
            self._json(200, routes.delete_template(name))
        except TreeError as exc:
            self._fail(404, exc.code, **exc.detail)
        except OSError as exc:
            self._fail(500, "ioError", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - 兜底，避免服务崩溃
            self._fail(500, "internalError", message=str(exc))

    def do_OPTIONS(self) -> None:  # noqa: N802
        # 刻意不提供 CORS 预检：本服务不接受跨站调用，
        # 预检失败会使浏览器放弃后续的实际请求，从而阻断跨站写操作。
        self._fail(403, "methodNotAllowed", method="OPTIONS")

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
