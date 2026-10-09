"""青蔓 QingMan · 内容寻址存储（借鉴 Git 思路）。

设计：
    blob 池   store/objects/<sha256[:2]>/<sha256>     路径即内容的 SHA-256，天然去重
    版本清单  versions/<版本>/MANIFEST.json           路径 → blob 指纹 + 元数据（parent/note/digest）

命令：
    commit   [--note 说明] [--alias 旧编号]   扫 src/ + start.bat + VERSION，写 blob，生成 MANIFEST
    checkout <版本> [--dry-run]               按 MANIFEST 重建；多余文件移入 store/.trash/
    log                                       列出版本链
    diff     <版本A> <版本B>                  输出 改动 / 新增 / 缺失
    fsck                                      校验 blob 池完整性（文件名 == 内容指纹）

原则：只复制不删除。checkout 的多余文件先复制进回收区并逐字节校验，通过后才移除原文件。
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
sys.dont_write_bytecode = True  # 工具不得在项目内留下 __pycache__
import versioning  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent

TRACK_ITEMS = ("src", "start.bat", "VERSION")
IGNORE_PARTS = {"__pycache__"}
IGNORE_SUFFIX = {".pyc"}
CHUNK = 1 << 20


# ---------- 基础 ----------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def blob_path(root: Path, digest: str) -> Path:
    return root / "store" / "objects" / digest[:2] / digest


def collect_files(base: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for item in TRACK_ITEMS:
        target = base / item
        if target.is_file():
            out.append((item, target))
        elif target.is_dir():
            for f in sorted(target.rglob("*")):
                if not f.is_file():
                    continue
                if IGNORE_PARTS & set(f.parts):
                    continue
                if f.suffix in IGNORE_SUFFIX:
                    continue
                out.append((str(f.relative_to(base)).replace("\\", "/"), f))
    return out


def manifest_digest(files: dict[str, str]) -> str:
    """对「相对路径 + 指纹」按路径排序后整体求 SHA-256 —— 路径参与运算，改名可检出。"""
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(path.encode("utf-8"))
        h.update(b"\0")
        h.update(files[path].encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def version_key(v: str) -> tuple[int, int, int]:
    try:
        return versioning.parse(v)
    except ValueError:
        return (-1, -1, -1)


def list_versions(root: Path) -> list[str]:
    vdir = root / "versions"
    if not vdir.is_dir():
        return []
    out = [p.name for p in vdir.iterdir() if p.is_dir() and (p / "MANIFEST.json").is_file()]
    return sorted(out, key=version_key)


def load_manifest(root: Path, version: str) -> dict | None:
    f = root / "versions" / version / "MANIFEST.json"
    if not f.is_file():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


# ---------- commit ----------

def do_commit(root: Path, source: Path, note: str, alias: str) -> int:
    raw = (root / "VERSION").read_text(encoding="utf-8").strip()
    try:
        version = versioning.format_version(versioning.parse(raw))
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1

    dest = root / "versions" / version
    if (dest / "MANIFEST.json").is_file():
        print(f"[跳过] 版本 {version} 的清单已存在（不覆盖，避免破坏历史版本）：{dest}")
        return 0

    files = collect_files(source)
    if not files:
        print(f"[失败] 未在 {source} 找到任何待跟踪文件")
        return 1

    files_map: dict[str, str] = {}
    new_blobs = reused = 0
    for rel, path in files:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        target = blob_path(root, digest)
        if target.is_file():
            reused += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            new_blobs += 1
        files_map[rel] = "sha256:" + digest

    previous = [v for v in list_versions(root) if v != version]
    meta = {
        "version": version,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(source),
        "note": note,
        "parent": previous[-1] if previous else None,
        "legacyAlias": alias or None,
        "fileCount": len(files_map),
        "digest": "sha256:" + manifest_digest(files_map),
        "files": files_map,
    }
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "MANIFEST.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[提交] {version} → {dest}")
    print(f"[提交] 文件 {len(files_map)} 个：新增 blob {new_blobs} 个，复用已有 {reused} 个（去重生效）")
    print(f"[提交] 清单指纹 {meta['digest'][:23]}…  parent={meta['parent'] or '—'}")
    if alias:
        print(f"[提交] 旧编号别名：{alias}")
    return 0


# ---------- checkout ----------

def do_checkout(root: Path, version: str, dry_run: bool) -> int:
    meta = load_manifest(root, version)
    if meta is None:
        print(f"[失败] 未找到版本 {version} 的 MANIFEST.json")
        return 1

    files: dict[str, str] = meta.get("files", {})
    absent = [rel for rel, ref in files.items() if not blob_path(root, ref.split(":", 1)[-1]).is_file()]
    if absent:
        print(f"[失败] {len(absent)} 个 blob 缺失，无法完整回退：")
        for rel in absent[:10]:
            print(f"        {rel}")
        return 1

    current = {rel for rel, _ in collect_files(root)}
    stale = sorted(current - set(files))

    print(f"[回退] 目标版本 {version}，共 {len(files)} 个文件")
    if stale:
        print(f"[回退] 当前有 {len(stale)} 个文件不在目标版本内，将移入回收区（不真删）：")
        for rel in stale[:10]:
            print(f"        {rel}")
        if len(stale) > 10:
            print(f"        …另有 {len(stale) - 10} 个")

    if dry_run:
        print("[演练] --dry-run，未写入任何文件")
        return 0

    trash = root / "store" / ".trash" / datetime.now().strftime("%Y%m%d-%H%M%S")
    trashed = blocked = 0
    for rel in stale:
        src = root / rel
        if not src.is_file():
            continue
        dst = trash / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha256_of(dst) != sha256_of(src):   # 回收区副本逐字节校验，通过才移除原文件
            print(f"[警告] 回收区副本校验失败，保留原文件：{rel}")
            blocked += 1
            continue
        src.unlink()
        trashed += 1

    restored = 0
    for rel, ref in files.items():
        digest = ref.split(":", 1)[-1]
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob_path(root, digest), dst)
        restored += 1

    print(f"[回退] 恢复 {restored} 个文件；移入回收区 {trashed} 个（校验失败保留 {blocked} 个）")
    if trashed:
        print(f"[回退] 回收区：{trash}")
    print(f"[回退] 完成，当前 VERSION = {(root / 'VERSION').read_text(encoding='utf-8').strip()}")
    return 0


# ---------- log / diff / fsck ----------

def do_log(root: Path) -> int:
    versions = list_versions(root)
    if not versions:
        print("[日志] 尚无任何版本清单")
        return 0
    print(f"[日志] 共 {len(versions)} 个版本（按版本号排序）")
    for v in versions:
        meta = load_manifest(root, v) or {}
        note = meta.get("note") or "—"
        parent = meta.get("parent") or "—"
        alias = meta.get("legacyAlias")
        tail = f"  [旧编号 {alias}]" if alias else ""
        print(f"  {v:<9} {meta.get('createdAt', '?'):<20} 文件 {meta.get('fileCount', '?'):>3}  parent={parent}  {note}{tail}")
    return 0


def do_diff(root: Path, a: str, b: str) -> int:
    ma, mb = load_manifest(root, a), load_manifest(root, b)
    if ma is None:
        print(f"[失败] 未找到版本 {a}")
        return 1
    if mb is None:
        print(f"[失败] 未找到版本 {b}")
        return 1
    fa, fb = ma.get("files", {}), mb.get("files", {})
    changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    added = sorted(set(fb) - set(fa))
    removed = sorted(set(fa) - set(fb))
    print(f"[差异] {a} → {b}：改动 {len(changed)} / 新增 {len(added)} / 缺失 {len(removed)}")
    for label, items in (("改动", changed), ("新增", added), ("缺失", removed)):
        for rel in items[:20]:
            print(f"        [{label}] {rel}")
        if len(items) > 20:
            print(f"        [{label}] …另有 {len(items) - 20} 个")
    return 0


def do_fsck(root: Path) -> int:
    objdir = root / "store" / "objects"
    if not objdir.is_dir():
        print("[巡检] 对象池尚未建立")
        return 0
    total = 0
    bad: list[str] = []
    for f in sorted(objdir.rglob("*")):
        if not f.is_file():
            continue
        total += 1
        if sha256_of(f) != f.name:
            bad.append(str(f.relative_to(objdir)))
    print(f"[巡检] 对象池 {total} 个 blob，损坏 {len(bad)} 个")
    for name in bad[:10]:
        print(f"        [损坏] {name}")
    return 1 if bad else 0


# ---------- 入口 ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 内容寻址存储")
    parser.add_argument("action", choices=("commit", "checkout", "log", "diff", "fsck"))
    parser.add_argument("args", nargs="*", help="checkout: <版本>；diff: <版本A> <版本B>")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--from", dest="source", default=None)
    parser.add_argument("--note", default="")
    parser.add_argument("--alias", default="")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()

    root = Path(opts.root).resolve()
    source = Path(opts.source).resolve() if opts.source else root

    if opts.action == "commit":
        return do_commit(root, source, opts.note, opts.alias)
    if opts.action == "checkout":
        if not opts.args:
            parser.error("checkout 需要一个版本号，如 V0.0.1")
        return do_checkout(root, opts.args[0], opts.dry_run)
    if opts.action == "diff":
        if len(opts.args) < 2:
            parser.error("diff 需要两个版本号")
        return do_diff(root, opts.args[0], opts.args[1])
    if opts.action == "log":
        return do_log(root)
    return do_fsck(root)


if __name__ == "__main__":
    raise SystemExit(main())
