"""青蔓 QingMan · 版本快照与递增。

用法：
    python tools/release.py snapshot [--root DIR] [--note 说明]
    python tools/release.py bump     [--root DIR]
    python tools/release.py list     [--root DIR]

snapshot：把当前 src/ + start.bat + VERSION 完整复制到 versions/<当前版本>/，
          并生成 SNAPSHOT.json（时间、来源、文件清单与 MD5）。只复制，不删除。
bump    ：把 VERSION 提升 +0.01 并写回，打印升级前后版本。
永远先 snapshot 再 bump —— 这样任何一次升级都可回退。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from versioning import bump as bump_version  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent

SNAPSHOT_ITEMS = ("src", "start.bat", "VERSION")


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def collect_manifest(base: Path) -> dict:
    manifest: dict[str, str] = {}
    for item in SNAPSHOT_ITEMS:
        target = base / item
        if target.is_file():
            manifest[item] = md5(target)
        elif target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    manifest[str(f.relative_to(base)).replace("\\", "/")] = md5(f)
    return manifest


def do_snapshot(root: Path, note: str) -> int:
    version = read_version(root)
    dest = root / "versions" / version
    if not (root / "src").is_dir():
        print(f"[失败] 主线 src/ 不存在：{root / 'src'}")
        return 1
    if dest.exists():
        print(f"[跳过] 快照已存在：{dest}（不覆盖，避免破坏历史版本）")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    for item in SNAPSHOT_ITEMS:
        src_item = root / item
        if not src_item.exists():
            continue
        dst_item = dest / item
        if src_item.is_dir():
            shutil.copytree(src_item, dst_item, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src_item, dst_item)

    manifest = collect_manifest(dest)
    meta = {
        "version": version,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(root),
        "note": note,
        "fileCount": len(manifest),
        "files": manifest,
    }
    (dest / "SNAPSHOT.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[快照] {version} → {dest}")
    print(f"[快照] 收录 {len(manifest)} 个文件，SNAPSHOT.json 已写入")
    return 0


def do_bump(root: Path) -> int:
    version_file = root / "VERSION"
    old = read_version(root)
    new = bump_version(old)
    version_file.write_text(new + "\n", encoding="utf-8")
    print(f"[升级] {old} → {new}")
    print("[提示] 请确认已在改动前执行 snapshot，否则本版本无回退点")
    return 0


def do_list(root: Path) -> int:
    versions_dir = root / "versions"
    if not versions_dir.is_dir():
        print("[列表] 尚无任何快照")
        return 0
    rows = sorted(p for p in versions_dir.iterdir() if p.is_dir())
    if not rows:
        print("[列表] 尚无任何快照")
        return 0
    for item in rows:
        meta_file = item / "SNAPSHOT.json"
        note = "—"
        count = "?"
        if meta_file.is_file():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                note = meta.get("note") or "—"
                count = str(meta.get("fileCount", "?"))
            except ValueError:
                pass
        print(f"  {item.name}  文件 {count:>3}  {note}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 版本快照与递增")
    parser.add_argument("action", choices=("snapshot", "bump", "list"))
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "VERSION").is_file():
        print(f"[失败] 未找到 VERSION：{root / 'VERSION'}")
        return 1

    if args.action == "snapshot":
        return do_snapshot(root, args.note)
    if args.action == "bump":
        return do_bump(root)
    return do_list(root)


if __name__ == "__main__":
    raise SystemExit(main())
