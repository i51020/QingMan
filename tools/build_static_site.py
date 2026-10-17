"""青蔓 QingMan · 静态预览构建（部署到 EdgeOne Makers / 任意静态托管用）。

**为什么需要它**：青蔓是**本地离线**工具 —— 真正的价值在「把目录写到用户磁盘」，
而那件事只可能发生在用户本机（`http.server` + `127.0.0.1` + 本地目录选择 + 桌面快捷方式）。
线上托管**拿不到用户磁盘**，所以线上版只能是**静态预览**：

| 能 | 不能 |
|---|---|
| 看界面、切皮肤、切语言、读帮助 | 生成目录（`/api/generate` 不存在） |
| 编辑目录树（**仅内存**，刷新即还原） | 保存编辑态 / 模板库 / 历史版本 / 桌面快捷方式 |

前端对这种状态是**设计内**的：`main.js` 的 `init()` 在 `/api/health` 失败时走
`serviceDown` → `setServiceState('offline')` → 提示「后端未连接」并 `return`，
**不做任何写盘尝试**（`i18n` 也有 `BUILTIN_LOCALES` 兜底）。所以静态版是「可用的演示」，
不是「坏掉的程序」。

**两处必须补的静态替身**：页面用 `<script src="./api/env.js">` / `./api/locales.js`
**同步注入**首屏语言（走同步脚本是为了不闪烁）。静态托管没有后端，这两条会 404，
于是这里生成同形的静态文件 —— 内容与 `routes.env_script()` / `routes.locales_script()` 对齐。

**浏览器内在线后端**（`tools/web-demo/demo-backend.js`）：线上没有 Python，若 `/api/*`
全 404，界面只能显示「后端未连接」。故注入一个按**同一套 HTTP 契约**实现的后端：
健康检查通过、编辑态存 `localStorage`（刷新不丢）、模板库存内置空白模板，
而**生成目录改走浏览器的文件夹授权**（File System Access API）—— 由用户当场点选目录，
逐个创建真实文件夹与文件。也就是说线上版**真的能建目录**，只是写盘通道从 Python 换成了浏览器，
代价是需要 Edge / Chrome 且位置靠点选（不能填路径）。它只存在于静态产物里，
`src/` 不感知 —— 生产代码一个字都不为演示让步。

**用法**：`py -3 tools/build_static_site.py [--out dist/static-site]`
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1]
WEB_DIR = ROOT / "src" / "web"
LOCALES_DIR = ROOT / "locales"
DEMO_BACKEND = _HERE.parent / "web-demo" / "demo-backend.js"
MD_MODULE = _HERE.parent / "web-demo" / "md-template.js"
ICON_MAKER = _HERE.parent / "web-demo" / "make_icons.py"
SEED_TEMPLATE = ROOT / "templates" / "P0_空白项目模板.json"
VERSION_FILE = ROOT / "VERSION"
DEFAULT_OUT = ROOT / "dist" / "static-site"

# 注入点在 module 脚本**之前**：演示后端必须在 main.js 发出第一个 /api 请求前就位。
INJECT_ANCHOR = '<script type="module" src="./js/main.js"></script>'
INJECT_SCRIPTS = (
    '  <script src="./js/demo-data.js"></script>\n'
    '  <script src="./js/md-template.js"></script>\n'
    '  <script src="./js/demo-backend.js"></script>\n'
    '  <script src="./js/pwa.js"></script>\n'
)
# PWA：manifest 与 theme-color 进 <head> —— 有它们浏览器才允许「安装到桌面/开始菜单」。
INJECT_HEAD = ('  <link rel="manifest" href="./manifest.webmanifest">\n'
               '  <meta name="theme-color" content="#2b2f36">\n')
HEAD_ANCHOR = "</head>"

# 与 `routes._LOCALE_NAME_RE` 同形：只取语言包的自描述名，不执行语言包代码。
NAME_RE = re.compile(r"export\s+const\s+NAME\s*=\s*['\"]([^'\"]+)['\"]")
# Windows 上非法、且会被静态托管当成路径的那些文件，不进构建产物。
SKIP_SUFFIXES = {".pyc", ".pyo", ".log"}


def list_locales() -> "list[dict[str, str]]":
    """`[{code, name}]`，按文件名排序 —— 与后端 `/api/locales.js` 的顺序口径一致。"""
    out: "list[dict[str, str]]" = []
    for path in sorted(LOCALES_DIR.glob("*.js")):
        code = path.stem
        match = NAME_RE.search(path.read_text(encoding="utf-8"))
        out.append({"code": code, "name": match.group(1) if match else code})
    return out


def build(out: Path, os_locale: str = "zh-CN") -> dict:
    """把 `src/web/` + `locales/` 装配成可直接托管的静态目录。

    ⚠ 产物目录已存在时**改名让路，不做删除**（与项目「只复制不删除」同一原则）：
    `shutil.rmtree` 在本环境会撞上 WorkBuddy 的批量删除保护（`[safe-delete]` 直接抛
    `OSError`），而这类失败的报错离真正原因很远、极易误判。改名的代价只是多占一点
    磁盘，却让「重建」永远可重复 —— 旧产物留在旁边还能比对差异。
    """
    if out.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        aside = out.with_name(f"{out.name}.old-{stamp}")
        shutil.move(str(out), str(aside))
        print(f"[静态] 旧产物已改名让路：{aside.name}")
    out.mkdir(parents=True)

    copied = 0
    for src in sorted(WEB_DIR.rglob("*")):
        if not src.is_file() or src.suffix.lower() in SKIP_SUFFIXES:
            continue
        dest = out / src.relative_to(WEB_DIR)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    # 语言包在项目根（V0.3.0 迁出 src/）：页面用相对路径 `../../../../locales/…`
    # 从 `/js/i18n/` 往上走到站点根 —— 故产物里必须落在 `<out>/locales/`。
    locale_count = 0
    for src in sorted(LOCALES_DIR.glob("*.js")):
        dest = out / "locales" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        locale_count += 1

    api = out / "api"
    api.mkdir(exist_ok=True)
    (api / "env.js").write_text(
        "window.__QM_OS_LOCALE__ = " + json.dumps(os_locale) + ";\n",
        encoding="utf-8", newline="\n")
    (api / "locales.js").write_text(
        "window.__QM_LOCALES__ = " + json.dumps(list_locales(), ensure_ascii=False) + ";\n",
        encoding="utf-8", newline="\n")

    demo = install_demo(out)
    pwa = install_pwa(out)

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    files = sum(1 for p in out.rglob("*") if p.is_file())
    return {"files": files, "bytes": total, "web": copied, "locales": locale_count,
            "demo": demo, "pwa": pwa}


PWA_REGISTER_JS = """/* 青蔓 QingMan · PWA 注册（由 build_static_site.py 生成）
 *
 * 在线版没有 .lnk 可写，但「安装到桌面 / 开始菜单」这件事浏览器自己做得到：
 * 只要站点有 manifest + service worker，用户点地址栏的「安装」即可得到
 * 独立窗口的图标，并且离线可用。这就是桌面快捷方式在 Web 上的等价物。
 *
 * service worker 取「网络优先、离线回落缓存」：宁可多一次请求，也不让用户
 * 拿到过期页面 —— 静态站每次发布都会换内容，缓存优先会把人锁在旧版。
 */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;
  if (location.protocol !== 'https:' && ['localhost', '127.0.0.1'].indexOf(location.hostname) < 0) return;
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('./sw.js').catch(function (err) {
      console.warn('[QingMan] service worker 注册失败：', err && err.message);
    });
  });
})();
"""

SW_JS = """/* 青蔓 QingMan · service worker（构建期生成，缓存名随版本变化） */
const CACHE = 'qm-static-__VERSION__';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE && key.indexOf('qm-static-') === 0)
          .map((key) => caches.delete(key))))
      .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf('/api/') === 0) return;   // 在线后端在页面内拦截，不走网络
  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
        return response;
      })
      .catch(() => caches.match(request).then((hit) => hit || caches.match('./index.html'))));
});
"""


def install_pwa(out: Path) -> bool:
    """生成 manifest / service worker / 图标，并在 <head> 挂上 manifest。

    图标用 `tools/web-demo/make_icons.py` 现画（纯标准库 PNG）：本机没有 Pillow，
    `msedge --screenshot` 也不产文件，与其依赖外部工具，不如自己确定性生成。
    """
    import json as _json
    import sys as _sys
    _sys.path.insert(0, str(_HERE.parent / "web-demo"))
    import make_icons  # noqa: E402  （同目录工具，仅在构建期使用）

    make_icons.write_icons(out / "icons")
    version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.is_file() else "V0"

    manifest = {
        "name": "青蔓 QingMan",
        "short_name": "青蔓",
        "description": "目录结构设计工具：编辑目录树，生成真实目录（在线版写入你选择的文件夹）",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f3f5f8",
        "theme_color": "#2b2f36",
        "lang": "zh-CN",
        "icons": [
            {"src": "./icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "./icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (out / "manifest.webmanifest").write_text(
        _json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "sw.js").write_text(SW_JS.replace("__VERSION__", version), encoding="utf-8", newline="\n")
    js = out / "js"
    js.mkdir(exist_ok=True)
    (js / "pwa.js").write_text(PWA_REGISTER_JS, encoding="utf-8", newline="\n")

    page = out / "index.html"
    html = page.read_text(encoding="utf-8")
    if HEAD_ANCHOR not in html:
        raise SystemExit(f"[FAIL] index.html 里找不到 {HEAD_ANCHOR}")
    if "manifest.webmanifest" not in html:
        html = html.replace(HEAD_ANCHOR, INJECT_HEAD + HEAD_ANCHOR, 1)
        page.write_text(html, encoding="utf-8", newline="\n")
    return True


def install_demo(out: Path) -> bool:
    """装入浏览器内演示后端 + 内置空白模板，并在 index.html 里挂上两条脚本。

    返回 False 表示素材缺失（此时产物退回「纯静态」：界面仍是后端未连接）。
    """
    if not DEMO_BACKEND.is_file():
        return False
    version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.is_file() else ""
    seed = {}
    if SEED_TEMPLATE.is_file():
        seed = json.loads(SEED_TEMPLATE.read_text(encoding="utf-8"))
    data = {
        "version": version,
        "template": {
            "file": SEED_TEMPLATE.name,
            "name": seed.get("name") or "空白项目模板",
            "description": seed.get("description") or "",
            "tree": seed.get("tree") or {},
        },
    }

    js = out / "js"
    js.mkdir(exist_ok=True)
    if not MD_MODULE.is_file():
        raise SystemExit(f"[FAIL] 缺 {MD_MODULE}（模板 .md 文法的 JS 移植）")
    shutil.copy2(MD_MODULE, js / "md-template.js")
    shutil.copy2(DEMO_BACKEND, js / "demo-backend.js")
    (js / "demo-data.js").write_text(
        "window.__QM_DEMO__ = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8", newline="\n")

    page = out / "index.html"
    html = page.read_text(encoding="utf-8")
    if INJECT_ANCHOR not in html:
        raise SystemExit(f"[FAIL] index.html 里找不到注入锚点：{INJECT_ANCHOR}")
    if "demo-backend.js" not in html:
        html = html.replace(INJECT_ANCHOR, INJECT_SCRIPTS + INJECT_ANCHOR)
        page.write_text(html, encoding="utf-8", newline="\n")
    return True


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="构建青蔓静态预览（线上演示用）")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--os-locale", default="zh-CN", help="首屏语言（静态版无法探测 OS 语言）")
    args = ap.parse_args(argv)

    out = Path(args.out).resolve()
    if not (WEB_DIR / "index.html").is_file():
        print(f"[FAIL] 找不到 {WEB_DIR / 'index.html'}")
        return 1
    info = build(out, args.os_locale)
    print(f"[静态] {out}")
    print(f"  web {info['web']} 个 + locales {info['locales']} 个 → 共 {info['files']} 文件，"
          f"{info['bytes'] / 1024:.0f} KB")
    print("  在线后端：" + ("已注入（草稿存 localStorage；生成走浏览器文件夹授权，真写磁盘）"
                          if info["demo"] else "未注入（缺 tools/web-demo/demo-backend.js）"))
    print("  可安装（PWA）：" + ("manifest + service worker + 图标 已生成"
                              if info["pwa"] else "未生成"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
