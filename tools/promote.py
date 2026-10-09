"""青蔓 QingMan · 预览版落地主线。

用法：
    python tools/promote.py [--from preview/V<版本>] [--root DIR] [--dry-run] [--force]

把预览版（<from>/src、<from>/start.bat）复制进主线根目录，并把 VERSION 写为主线的当前版本。
规则：
  * 单向：只从预览流向主线，绝不反向。
  * 只复制，不删除。主线中不存在于预览版的旧文件会被明确列出（需 --force 才继续）。
  * 默认要求主线为空，避免误覆盖正在开发的版本；--force 显式放行。
  * `preview/` 平时为空 —— 需要试跑时**按版本新建** `preview/V<版本>/`（见项目约定 §P1-4）。
    `--from` 缺省时按主线 `VERSION` 推导为 `preview/<当前版本>`，不写死任何旧编号。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent

COPY_DIRS = ("src",)
COPY_FILES = ("start.bat",)
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def default_source(root: Path) -> str:
    """缺省预览目录：`preview/<当前 VERSION>`，如 `preview/V0.0.1`。

    `preview/` 是试运行区，不是常驻目录：需要试跑时按版本新建，试完可整体归档。
    因此这里不写死任何具体版本号，一律按主线 `VERSION` 推导。
    """
    try:
        current = (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "preview"
    return f"preview/{current}" if current else "preview"


def list_files(base: Path) -> set[str]:
    if not base.exists():
        return set()
    out = set()
    for item in COPY_DIRS:
        target = base / item
        if target.is_dir():
            for f in target.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    out.add(str(f.relative_to(base)).replace("\\", "/"))
    for item in COPY_FILES:
        if (base / item).is_file():
            out.add(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 预览版落地主线")
    parser.add_argument("--from", dest="source", default=None,
                        help="预览目录，缺省按主线 VERSION 推导为 preview/<当前版本>")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    source_arg = args.source or default_source(root)
    source = Path(source_arg) if Path(source_arg).is_absolute() else (root / source_arg).resolve()

    if not (source / "src").is_dir():
        print(f"[失败] 预览版 src/ 不存在：{source / 'src'}")
        print(f"[提示] preview/ 为按需新建的试运行区。请先建好 {source_arg}/ 再落地，或显式指定 --from")
        return 1

    existing = list_files(root)
    if existing and not args.force:
        print(f"[拦截] 主线已有 {len(existing)} 个文件，未使用 --force，拒绝覆盖：")
        for name in sorted(existing)[:10]:
            print(f"        {name}")
        if len(existing) > 10:
            print(f"        …另有 {len(existing) - 10} 个")
        print("[提示] 请先 release.py snapshot 留好回退点，确认后再加 --force")
        return 1

    source_files = list_files(source)
    stale = sorted(existing - source_files)

    print(f"[预览] 源：{source}")
    print(f"[预览] 目标：{root}")
    print(f"[预览] 将复制 {len(source_files)} 个文件")
    if stale:
        print(f"[提示] 主线存在 {len(stale)} 个预览版没有的旧文件（不会被删除）：")
        for name in stale[:10]:
            print(f"        {name}")

    if args.dry_run:
        print("[演练] --dry-run，未写入任何文件")
        return 0

    for item in COPY_DIRS:
        src_item = source / item
        if src_item.is_dir():
            shutil.copytree(src_item, root / item, dirs_exist_ok=True, ignore=IGNORE)
    for item in COPY_FILES:
        src_item = source / item
        if src_item.is_file():
            shutil.copy2(src_item, root / item)

    version = (source / "VERSION").read_text(encoding="utf-8").strip()
    # 显式 newline="\n"：默认 newline=None 会把 \n 译为 os.linesep（Windows 下 CRLF），
    # 使 VERSION 字节随平台漂移，导致 store digest 与 verify --against 失配。
    with (root / "VERSION").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(version + "\n")

    print(f"[落地] 完成，主线版本 = {version}")
    print("[下一步] python tools/verify.py  →  python tools/release.py snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
