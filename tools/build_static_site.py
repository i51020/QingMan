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

**用法**：`py -3 tools/build_static_site.py [--out dist/static-site]`
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1]
WEB_DIR = ROOT / "src" / "web"
LOCALES_DIR = ROOT / "locales"
DEFAULT_OUT = ROOT / "dist" / "static-site"

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
    """把 `src/web/` + `locales/` 装配成可直接托管的静态目录。"""
    if out.exists():
        shutil.rmtree(out)
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

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    files = sum(1 for p in out.rglob("*") if p.is_file())
    return {"files": files, "bytes": total, "web": copied, "locales": locale_count}


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
    print("  [注意] 线上版为静态预览：可看、可编辑（仅内存），不能生成目录 / 保存 / 用模板库")
    return 0


if __name__ == "__main__":
    sys.exit(main())
