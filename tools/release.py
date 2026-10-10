"""青蔓 QingMan · 版本操作（bump）+ 旧命令兼容层。

快照功能自 2026-10-09 起由 store.py 的**内容寻址存储**取代：
    store.py commit      生成 blob + versions/<版本>/MANIFEST.json（取代 snapshot）
    store.py checkout    按 MANIFEST 重建，多余文件进回收区（取代手工 cp 回退）
    store.py log         列出版本链（取代 list）

本文件保留为兼容入口，旧命令仍可用：
    python tools/release.py bump [--kind patch|minor|major] [--root DIR]
    python tools/release.py snapshot [--note 说明]     → 转发 store commit
    python tools/release.py list                       → 转发 store log

版本规则：SemVer 三段式 V<MAJOR>.<MINOR>.<PATCH>，从 V0.0.1 起。
    patch = 修复 ／ minor = 逻辑迭代 ／ major = 不兼容变更
旧「V0.01 两段式 + 每次 +0.01」规则已作废。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
sys.dont_write_bytecode = True  # 工具不得在项目内留下 __pycache__
import store  # noqa: E402
import versioning  # noqa: E402


def read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def do_bump(root: Path, kind: str) -> int:
    path = root / "VERSION"
    old = read_version(root)
    try:
        new = versioning.bump(old, kind)
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1
    # 回退点提示必须在**写盘之前** —— 原实现写在写盘之后，等用户看到时 `VERSION`
    # 已被改动，提示已无意义（《审查报告_工具链_20261010》§P2-6）。
    print("[提示] 即将改写 VERSION：请确认已用 store.py commit 留好回退点，否则本版本无快照")
    # 显式 newline="\n" 写盘：Path.write_text 的 newline 参数 Python 3.10 才有（本项目下限 3.8），
    # 且默认 newline=None 会把 \n 译为 os.linesep —— Windows 下变 CRLF，破坏 SHA-256 指纹一致。
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new + "\n")
    print(f"[升级] {old} → {new}（{kind}）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 版本操作")
    parser.add_argument("action", choices=("bump", "snapshot", "list"))
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--note", default="")
    parser.add_argument("--kind", default="patch", choices=versioning.KINDS)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "VERSION").is_file():
        print(f"[失败] 未找到 VERSION：{root / 'VERSION'}")
        return 1

    if args.action == "bump":
        return do_bump(root, args.kind)
    if args.action == "snapshot":
        print("[提示] snapshot 已被 store.py 的内容寻址存储取代，本次转发到 store commit")
        return store.do_commit(root, root, args.note, "")
    return store.do_log(root)


if __name__ == "__main__":
    raise SystemExit(main())
