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

**浏览器内演示后端**（`tools/web-demo/demo-backend.js`）：线上没有 Python，若 `/api/*`
全 404，界面只能显示「后端未连接」，访客会以为站点坏了。故注入一个按**同一套 HTTP 契约**
实现的演示后端：健康检查通过、编辑态存 `localStorage`（刷新不丢）、模板库给内置空白模板，
**写盘类动作明确说明做不到**（浏览器本来也不该能写用户磁盘）。它只存在于静态产物里，
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
SEED_TEMPLATE = ROOT / "templates" / "P0_空白项目模板.json"
VERSION_FILE = ROOT / "VERSION"
DEFAULT_OUT = ROOT / "dist" / "static-site"

# 注入点在 module 脚本**之前**：演示后端必须在 main.js 发出第一个 /api 请求前就位。
INJECT_ANCHOR = '<script type="module" src="./js/main.js"></script>'
INJECT_SCRIPTS = (
    '  <script src="./js/demo-data.js"></script>\n'
    '  <script src="./js/demo-backend.js"></script>\n'
)

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

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    files = sum(1 for p in out.rglob("*") if p.is_file())
    return {"files": files, "bytes": total, "web": copied, "locales": locale_count,
            "demo": demo}


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
    print("  演示后端：" + ("已注入（编辑态存 localStorage，写盘类动作给明确说明）"
                          if info["demo"] else "未注入（缺 tools/web-demo/demo-backend.js）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
