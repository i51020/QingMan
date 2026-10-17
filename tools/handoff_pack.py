"""青蔓 QingMan · 接续包构建（V0.1.0 · 处理「接续包会过期」这条遗留风险）。

**问题**：换会话 / 换 AI 平台时，唯一能带走的是「接续包」。此前那份是**手工**拼的
（13 份文档 + 源码 zip），于是必然过期 —— 实测它停在 `V0.0.53`（113 项 / 499 用例 / 旧行号），
照它动手会改错行。`tools/` 里也没有打包脚本。

**本工具把「打包」变成一条命令**：进包内容由**白名单**决定，清单逐文件 sha256，
同一份输入两次构建**逐字节一致** —— 与 `package_release.py` / `pack_templates.py` 同体例。

**与发布包的区别**（两者**不互相替代**）：

| | 发布包 `package_release.py` | 接续包 `handoff_pack.py` | 完整开发包 `--full` |
|---|---|---|---|
| 给谁 | **最终用户** | **下一个接手的人 / AI** | **要继续开发并交付的人 / AI** |
| 内容 | `src/` + 模板 + 运行时 + 使用说明 | `src/` + `docs/` + `locales/` + 契约文档 | 工作树全量：上者 + `tools/` `tests/` `templates/` `templates-pack/` `store/` `versions/` `.git/` |
| 必不含 | `docs/`（开发者文档）、`store/` | `runtime/`、`store/`、`versions/`、`data/`、`.git/` | `data/`（用户草稿）、`dist/`（可再生产物） |

**为什么需要 `--full`（V0.3.0 实测后补）**：接续包**只能读代码、不能验证**——
实测把它解压后 `tools/gate.py` / `tools/verify.py` 都不存在，`unittest discover -s tests`
报 `Start directory is not importable`；`store/` `versions/` 也不在包里，于是**没有任何回退点**。
即「四件套」与「回退」在接续包里全部失效。要接着开发并交付，必须用 `--full`。

**用法**：`py -3 tools/handoff_pack.py`（接续包）、`--full`（完整开发包）；
可选 `--out-dir`、`--verify`、`--built-at`、`--no-git`（不带走 `.git/`，省约 7 MB）。
"""

from __future__ import annotations

import argparse
import os
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
FULL_PREFIX = f"QingMan-完整开发包_{VERSION}_{DATE}"

# 白名单：接手者**必然需要**的东西。少一件就交接不清。
INCLUDE_FILES = ("VERSION", "start.bat", "manifest.json", "README_使用说明.md",
                 "CHANGELOG.md", "README.md", "docs/项目约定.md", "docs/项目手册.md",
                 "docs/任务进度.md", "docs/接续说明.md", "docs/错误笔记.md")
# V0.3.0：语言包已迁出 src/ —— 交接包必须显式带上 `locales/`，
# 否则接手者拿到的是「没有文案的程序」（本次实测：包内文件 102 → 99，正是少了这三个）。
INCLUDE_DIRS = ("src", "docs", "locales")
EXCLUDE_DIR_NAMES = {"__pycache__", ".git", "data", "store", "versions", "dist"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log"}

# `--full`：语义是「整棵工作树」，故用**排除表**而非白名单 ——
# 白名单会让日后新增的目录（如 `legacy/`）静默漏出包外，而「完整包缺东西」正是最难发现的一类错。
FULL_EXCLUDE_TOP = {"data", "dist"}
FULL_EXCLUDE_ANY = {"__pycache__", ".trash"}



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


def iter_full_files(with_git: bool = True) -> "list[tuple[Path, str]]":
    """完整开发包的文件清单（整棵工作树 − 排除表），已排序。

    用 `os.walk` 而不是 `rglob`：可以在**进入之前**剪掉 `data/`、`dist/`、`__pycache__/`，
    否则要先遍历 `dist/` 里几十 MB 的既有 zip 再逐个丢弃。
    """
    out: "list[tuple[Path, str]]" = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT)
        keep: "list[str]" = []
        for name in sorted(dirnames):
            if name in FULL_EXCLUDE_ANY:
                continue
            if name == ".git" and not with_git:
                continue
            if rel_dir == Path(".") and name in FULL_EXCLUDE_TOP:
                continue
            keep.append(name)
        dirnames[:] = keep            # 必须原地改，os.walk 才会真的不进去
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            out.append((path, path.relative_to(ROOT).as_posix()))
    return out


def build(out_dir: Path, built_at: "str | None" = None, *, full: bool = False,
          with_git: bool = True) -> Path:
    """构建接续包（默认）或完整开发包（`full=True`）；`built_at` 用于复算一致性。"""
    files = iter_full_files(with_git) if full else iter_handoff_files()
    prefix = FULL_PREFIX if full else PREFIX
    staging = Path(tempfile.mkdtemp(prefix="qm_handoff_"))
    try:
        manifest = pr.build_staging(staging, files, None, built_at)
        manifest["package"] = "dev" if full else "handoff"
        pr.write_manifest(staging, manifest)
        out = out_dir / f"{prefix}.zip"
        pr.build_zip(staging, out, prefix=prefix)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return out


def verify(zip_path: Path, *, full: bool = False, with_git: bool = True) -> int:
    """结构自检。

    接续包：必需件齐全、**不含**开发期重资产（store/versions/data/runtime/.git）。
    完整开发包（`full`）：工具、测试、版本库、模板包、`.git` **都必须有** ——
    这几样任一缺失，「改完能验证 / 改坏能回退」就从成立变成不成立，而包本身不会报错。
    """
    problems: "list[str]" = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    prefix = names[0].split("/")[0] if names else ""
    if full:
        for must in ("VERSION", "manifest.json", "发布包清单.json",
                     "src/server/app.py", "locales/zh-CN.js", "locales/en-US.js",
                     "tools/gate.py", "tools/verify.py", "tools/package_release.py",
                     "tests/test_routes.py", "templates/P0_空白项目模板.json",
                     "templates-pack/pack.manifest.json"):
            if f"{prefix}/{must}" not in names:
                problems.append(f"缺 {must}")
        for need, why in ((f"{prefix}/store/objects/", "store/ 版本库（回退对象池）"),
                          (f"{prefix}/versions/", "versions/ 版本清单"),
                          (f"{prefix}/tools/gate.py", "四件套入口"),
                          (f"{prefix}/tests/", "回归测试网")):
            if not any(n.startswith(need) for n in names):
                problems.append(f"缺 {why}")
        if with_git and not any(n.startswith(f"{prefix}/.git/") for n in names):
            problems.append("缺 .git/（历史与 diff；如需省体积请加 --no-git）")
        for banned in ("/data/", "/dist/", "/__pycache__/", "/.trash/"):
            if any(banned in n for n in names):
                problems.append(f"误带 {banned}")
    else:
        for must in ("VERSION", "manifest.json", "docs/项目约定.md", "docs/任务进度.md",
                     "src/server/app.py", "locales/zh-CN.js", "locales/en-US.js",
                     "发布包清单.json"):
            if f"{prefix}/{must}" not in names:
                problems.append(f"缺 {must}")
        for banned in ("/store/", "/versions/", "/data/", "/runtime/", "/.git/"):
            if any(banned in n for n in names):
                problems.append(f"误带 {banned}")
    print(f"[{'完整开发包' if full else '接续包'}] {zip_path.name}  "
          f"{zip_path.stat().st_size/1024:.0f} KB  文件 {len(names)} 个")
    if problems:
        for item in problems:
            print(f"  [FAIL] {item}")
        return 1
    print("  [OK] 必需件齐全；" + ("已带 tools/tests/store/versions"
                                 + ("/.git" if with_git else "（无 .git）")
                                 + "，未带 data/dist"
                                 if full else "未带 store/versions/data/runtime"))
    return 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="构建青蔓接续包 / 完整开发包（交接用）")
    ap.add_argument("--out-dir", default=str(ROOT / "dist"))
    ap.add_argument("--verify", metavar="ZIP", help="只自检已构建的包")
    ap.add_argument("--built-at", help="固定构建时间（复算用）")
    ap.add_argument("--full", action="store_true",
                    help="构建完整开发包：含 tools/ tests/ templates/ templates-pack/ store/ versions/ .git/")
    ap.add_argument("--no-git", action="store_true",
                    help="配合 --full：不带走 .git/（省约 7 MB，但失去 diff 与历史）")
    args = ap.parse_args(argv)
    if args.verify:
        return verify(Path(args.verify), full=args.full, with_git=not args.no_git)
    out = build(Path(args.out_dir), args.built_at, full=args.full, with_git=not args.no_git)
    print(f"[构建] {out}")
    return verify(out, full=args.full, with_git=not args.no_git)


if __name__ == "__main__":
    raise SystemExit(main())
