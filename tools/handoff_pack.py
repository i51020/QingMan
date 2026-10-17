"""青蔓 QingMan · 接续包构建（V0.1.0 · 处理「接续包会过期」这条遗留风险）。

**问题**：换会话 / 换 AI 平台时，唯一能带走的是「接续包」。此前那份是**手工**拼的
（13 份文档 + 源码 zip），于是必然过期 —— 实测它停在 `V0.0.53`（113 项 / 499 用例 / 旧行号），
照它动手会改错行。`tools/` 里也没有打包脚本。

**本工具把「打包」变成一条命令**：进包内容由**白名单**决定，清单逐文件 sha256，
同一份输入两次构建**逐字节一致** —— 与 `package_release.py` / `pack_templates.py` 同体例。

**与发布包的区别**（两者**不互相替代**）：

| | 发布包 `package_release.py` | 接续包 `handoff_pack.py` |
|---|---|---|
| 给谁 | **最终用户** | **下一个接手的人 / AI** |
| 内容 | `src/` + 模板 + 运行时 + 使用说明 | `src/` + `docs/` + `manifest.json` + 契约文档 |
| 必不含 | `docs/`（开发者文档）、`store/` | `runtime/`（40 MB 级，与接手无关） |

**用法**：`py -3 tools/handoff_pack.py`（可选 `--out-dir`、`--verify`）。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE.parent))

import package_release as pr  # noqa: E402  （复用确定性打包与 sha256 清单）

VERSION = pr.VERSION
DATE = time.strftime("%Y%m%d")
PREFIX = f"QingMan-接续包_{VERSION}_{DATE}"

# 白名单：接手者**必然需要**的东西。少一件就交接不清。
INCLUDE_FILES = ("VERSION", "start.bat", "manifest.json", "README_使用说明.md",
                 "CHANGELOG.md", "README.md", "docs/项目约定.md", "docs/项目手册.md",
                 "docs/任务进度.md", "docs/接续说明.md", "docs/错误笔记.md")
# V0.3.0：语言包已迁出 src/ —— 交接包必须显式带上 `locales/`，
# 否则接手者拿到的是「没有文案的程序」（本次实测：包内文件 102 → 99，正是少了这三个）。
INCLUDE_DIRS = ("src", "docs", "locales")
EXCLUDE_DIR_NAMES = {"__pycache__", ".git", "data", "store", "versions", "dist"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log"}


def iter_handoff_files() -> "list[tuple[Path, str]]":
    """接续包的文件清单（白名单 + 排除），已排序。"""
    out: "list[tuple[Path, str]]" = []
    for name in INCLUDE_FILES:
        path = ROOT / name
        if path.is_file():
            out.append((path, name))
    for name in INCLUDE_DIRS:
        base = ROOT / name
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in EXCLUDE_DIR_NAMES for part in rel.parts):
                continue
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            out.append((path, rel.as_posix()))
    return sorted({rel: (src, rel) for src, rel in out}.values(), key=lambda kv: kv[1])


def build(out_dir: Path, built_at: "str | None" = None) -> Path:
    """构建接续包；`built_at` 用于复算一致性（默认当前时间）。"""
    files = iter_handoff_files()
    staging = Path(tempfile.mkdtemp(prefix="qm_handoff_"))
    try:
        manifest = pr.build_staging(staging, files, None, built_at)
        manifest["package"] = "handoff"
        pr.write_manifest(staging, manifest)
        out = out_dir / f"{PREFIX}.zip"
        pr.build_zip(staging, out, prefix=PREFIX)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return out


def verify(zip_path: Path) -> int:
    """结构自检：必需件齐全、**不含**开发期重资产（store/versions/data/runtime）。"""
    problems: "list[str]" = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for must in ("VERSION", "manifest.json", "docs/项目约定.md", "docs/任务进度.md",
                 "src/server/app.py", "locales/zh-CN.js", "locales/en-US.js",
                 "发布包清单.json"):
        if f"{PREFIX}/{must}" not in names:
            problems.append(f"缺 {must}")
    for banned in ("/store/", "/versions/", "/data/", "/runtime/", "/.git/"):
        if any(banned in n for n in names):
            problems.append(f"误带 {banned}")
    print(f"[接续包] {zip_path.name}  {zip_path.stat().st_size/1024:.0f} KB  文件 {len(names)} 个")
    if problems:
        for item in problems:
            print(f"  [FAIL] {item}")
        return 1
    print("  [OK] 必需件齐全；未带 store/versions/data/runtime")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="构建青蔓接续包（交接用）")
    ap.add_argument("--out-dir", default=str(ROOT / "dist"))
    ap.add_argument("--verify", metavar="ZIP", help="只自检已构建的接续包")
    ap.add_argument("--built-at", help="固定构建时间（复算用）")
    args = ap.parse_args(argv)
    if args.verify:
        return verify(Path(args.verify))
    out = build(Path(args.out_dir), args.built_at)
    print(f"[构建] {out}")
    return verify(out)


if __name__ == "__main__":
    raise SystemExit(main())
