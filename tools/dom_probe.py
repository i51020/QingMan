"""青蔓 QingMan · DOM 级对比度实测（配合 tools/dom_probe.js）。

**为什么不是纯词表审计**：`contrast_audit.py` 只能算「设计令牌 A vs 设计令牌 B」。
如果某个选择器写死了颜色、或者文字压在了错误的变量上，词表看不见 —— 2026-10-17
的 s06「选中行次要文字 4.35」就是这么漏出去的（词表只算了 ink 没算 dim）。

**做法**：
  1. 从 tokens.css + skins/*.css 现算 18 套主题的变量（复用 contrast_audit.themes()）；
  2. 把 `_qae_index.html` / `_qae_help.html` 注入构建产物目录：主题表 + dom_probe.js；
  3. 起一个本地 http.server（顺带收探针打回来的 `__qaE` 日志）；
  4. 用无头 Edge 打开这两个页面，等它报 DONE，然后收工；
  5. 解析 SUMMARY，打印每套主题的「测了几个节点 / 不达标几条 / 最差三条」。

**为什么不看退出码**：无头浏览器什么时候退出不由我们控制（`--dump-dom` 在 load 就截），
探针是异步的（等 OPFS/IndexedDB/渲染）。所以进程超时被 kill 是**预期行为**，
判据只有日志里的 DONE 与 SUMMARY。

用法：
    py -3 tools/dom_probe.py --dir dist/dom-probe       # 已构建好的目录
    py -3 tools/dom_probe.py --dir dist/dom-probe --pages index
    py -3 tools/dom_probe.py --dir dist/dom-probe --wait 90
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE.parent))

import contrast_audit as ca  # noqa: E402  （同目录模块）

_PROBE_JS = _HERE.parent / "dom_probe.js"
_EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)

_LOGS: list[str] = []
_DONE = threading.Event()


class _Handler(SimpleHTTPRequestHandler):
    """静态站 + 一条 `__qaE` 回传通道（探针把结果打成查询串回来）。"""

    def do_GET(self):  # noqa: N802（http.server 的约定用驼峰）
        if self.path.startswith("/__qaE?"):
            payload = unquote(urlparse(self.path).query)
            _LOGS.append(payload)
            if payload.startswith("DONE") or payload == "DONE":
                _DONE.set()
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, *args):  # 静音：只在失败时自己打印
        return


def themes_js() -> str:
    """把 `contrast_audit.themes()` 变成探针要的 `[{name, vars}]`（键名去掉 `qm-`）。"""
    items = [{"name": name, "vars": {k: v for k, v in variables.items()}}
             for name, variables in ca.themes()]
    return "window.__QM_THEMES = " + json.dumps(items, ensure_ascii=False) + ";"


def inject(site: Path, page: str) -> Path:
    """生成 `_qae_<page>.html`：原页面 + 主题表 + 探针。"""
    src = site / f"{page}.html"
    if not src.is_file():
        raise SystemExit(f"[dom-probe] 找不到页面：{src}")
    html = src.read_text(encoding="utf-8")
    block = ("\n<script>\n" + themes_js() + "\n</script>\n"
             "<script>\n" + _PROBE_JS.read_text(encoding="utf-8") + "\n</script>\n")
    anchor = "</body>"
    if anchor not in html:
        raise SystemExit(f"[dom-probe] {src} 里没有 </body>，无法注入")
    out = site / f"_qae_{page}.html"
    # newline="\n"：Windows 上默认会把 \n 翻成 \r\n，`verify` 的换行一致性守卫会判红
    out.write_text(html.replace(anchor, block + anchor, 1), encoding="utf-8", newline="\n")
    return out


def serve(site: Path) -> tuple[ThreadingHTTPServer, int]:
    handler = lambda *a, **kw: _Handler(*a, directory=str(site), **kw)  # noqa: E731
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def run_page(browser: str, url: str, wait: float) -> list[dict]:
    """开一次无头浏览器，等 DONE（或超时），返回本页的 SUMMARY 列表。"""
    _LOGS.clear()
    _DONE.clear()
    profile = tempfile.mkdtemp(prefix="qm-probe-")
    args = [browser, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions",
            f"--user-data-dir={profile}", "--window-size=1280,900", url]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + wait
    try:
        while time.time() < deadline and not _DONE.is_set():
            time.sleep(0.2)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    rows: list[dict] = []
    for line in _LOGS:
        if line.startswith("SUMMARY "):
            rows.extend(json.loads(line[len("SUMMARY "):]))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DOM 级对比度实测")
    ap.add_argument("--dir", required=True, help="已构建的静态站目录")
    ap.add_argument("--pages", default="index,help", help="要测的页面，逗号分隔")
    ap.add_argument("--wait", type=float, default=75.0, help="单页等待秒数上限")
    args = ap.parse_args(argv)

    site = (_ROOT / args.dir).resolve() if not Path(args.dir).is_absolute() else Path(args.dir)
    if not site.is_dir():
        raise SystemExit(f"[dom-probe] 目录不存在：{site}")

    browser = next((p for p in _EDGE_CANDIDATES if os.path.isfile(p)), None)
    if not browser:
        raise SystemExit("[dom-probe] 找不到 Edge / Chrome，无法实测")
    print(f"[dom-probe] 浏览器：{browser}")
    print(f"[dom-probe] 站点：{site}")

    pages = [p.strip() for p in args.pages.split(",") if p.strip()]
    for page in pages:
        inject(site, page)

    httpd, port = serve(site)
    print(f"[dom-probe] 本地端口：{port}\n")

    total_bad = 0
    try:
        for page in pages:
            # 只有主界面有那些弹窗触发器；别的页面只测整页。
            scen = "" if page == "index" else "?scen=main"
            rows = run_page(browser, f"http://127.0.0.1:{port}/_qae_{page}.html{scen}", args.wait)
            if not rows:
                print(f"── {page}：没有收到任何结果（探针未跑完，可加大 --wait）")
                total_bad += 1
                continue
            print(f"── {page}：{len(rows)} 条结果")
            order: list[str] = []
            for r in rows:
                if r["scenario"] not in order:
                    order.append(r["scenario"])
            for scen in order:
                mine = [r for r in rows if r["scenario"] == scen]
                nodes = sum(r["n"] for r in mine)
                bad = sum(r["bad"] for r in mine)
                empty = [r for r in mine if r["n"] == 0]
                flag = "OK  " if bad == 0 and not empty else "FAIL"
                print(f"   {flag} {scen:<15} {len(mine)} 套主题 / {nodes} 节点 / 不达标 {bad} 条"
                      + ("（该层未打开，未测）" if empty else ""))
                for r in mine:
                    if not r["bad"]:
                        continue
                    print(f"        · {r['theme']}")
                    for w in r["worst"]:
                        print(f"            {w}")
                total_bad += bad + len(empty)
            print()
    finally:
        httpd.shutdown()

    print(f"[dom-probe] {'全部达标' if not total_bad else f'存在不达标项（{total_bad}）'}")
    return 0 if not total_bad else 1


if __name__ == "__main__":
    sys.exit(main())
