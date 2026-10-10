"""青蔓 QingMan · 内容寻址存储（借鉴 Git 思路）。

设计：
    blob 池   store/objects/<sha256[:2]>/<sha256>     路径即内容的 SHA-256，天然去重
    版本基线  versions/<版本>/MANIFEST.json           首个清单（修订 r1，只增不改）
    同版修订  versions/<版本>/MANIFEST-r<N>.json      同版本后续修订（r2、r3 …）

修订引用语法：`V0.0.1`（= 该版本最高修订）／`V0.0.1@r1`（基线）／`V0.0.1@r2`（第 2 次修订）

命令：
    commit   [--note 说明] [--alias 旧编号]   扫 src/ + start.bat + VERSION，写 blob，追加修订
    checkout <版本[@rN]> [--dry-run]          按清单重建；多余文件移入 store/.trash/
    log                                       列出版本链（含同版本各修订）
    diff     <版本[@rN]> <版本[@rN]>          输出 改动 / 新增 / 缺失
    fsck                                      校验 blob 池完整性（文件名 == 内容指纹）

原则：
    * 只复制不删除。checkout 的多余文件先复制进回收区并逐字节校验，通过后才移除原文件。
    * 同一版本的清单文件永不覆盖：已存在 MANIFEST.json 时，新改动一律追加为 MANIFEST-r<N>.json，
      使「不升版但要留回退点」的场景也能从 blob 池完整取回。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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

BASE_MANIFEST = "MANIFEST.json"
_REV_FILE = re.compile(r"^MANIFEST(?:-r(\d+))?\.json$")


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


def fingerprint_diff(root: Path, recorded: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """主线现状 vs 清单记录 →（改动, 新增, 缺失）三个**已排序**的路径列表。

    单一来源：`handoff.fingerprint_state` 与 `verify.check_fingerprint` 原先各写一份
    同样的「改动/新增/缺失」逻辑（《审查报告_工具链_20261010》§P2-9），此处抽出复用。
    判据：`recorded` 是清单里的 `{相对路径: "sha256:<hex>"}`。
    """
    changed = sorted(p for p, d in recorded.items()
                     if (root / p).is_file() and sha256_of(root / p) != d.split(":", 1)[-1])
    missing = sorted(p for p in recorded if not (root / p).is_file())
    current = {p for p, _ in collect_files(root)}
    added = sorted(current - set(recorded))
    return changed, added, missing


def is_within(child: Path, parent: Path) -> bool:
    """child 是否等于 parent 或位于 parent 之下（对齐 `src/server/config.py` 同名函数语义）。

    不用 `Path.is_relative_to`：本项目下限 3.8，该 API 3.9 才有。
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def version_key(v: str) -> tuple[int, int, int]:
    try:
        return versioning.parse(v)
    except ValueError:
        return (-1, -1, -1)


# ---------- 修订：命名 / 解析 ----------

def manifest_filename(rev: int) -> str:
    """修订号 → 清单文件名。r1 为基线 MANIFEST.json，r2 起为 MANIFEST-r<N>.json。"""
    if rev < 1:
        raise ValueError(f"修订号必须 ≥ 1，收到 {rev}")
    return BASE_MANIFEST if rev == 1 else f"MANIFEST-r{rev}.json"


def revision_of(filename: str) -> int | None:
    """清单文件名 → 修订号；不是清单文件返回 None。"""
    m = _REV_FILE.match(filename)
    if not m:
        return None
    return int(m.group(1)) if m.group(1) else 1


def parse_ref(ref: str) -> tuple[str, int | None]:
    """`V0.0.1` → ('V0.0.1', None)；`V0.0.1@r2` / `V0.0.1@2` → ('V0.0.1', 2)。"""
    text = (ref or "").strip()
    if "@" not in text:
        return text, None
    version, _, tag = text.partition("@")
    tag = tag.strip().lower().lstrip("r")
    if not tag.isdigit() or int(tag) < 1:
        raise ValueError(f"修订引用非法：{ref!r}，应为 V0.0.1 或 V0.0.1@r2 形式")
    return version.strip(), int(tag)


def revisions(root: Path, version: str) -> list[int]:
    """某版本下全部修订号（升序）。"""
    vdir = root / "versions" / version
    if not vdir.is_dir():
        return []
    out: list[int] = []
    for f in vdir.iterdir():
        if not f.is_file():
            continue
        rev = revision_of(f.name)
        if rev is not None:
            out.append(rev)
    return sorted(out)


def latest_revision(root: Path, version: str) -> int | None:
    revs = revisions(root, version)
    return revs[-1] if revs else None


def list_versions(root: Path) -> list[str]:
    vdir = root / "versions"
    if not vdir.is_dir():
        return []
    out = [p.name for p in vdir.iterdir() if p.is_dir() and revisions(root, p.name)]
    return sorted(out, key=version_key)


def load_manifest(root: Path, version: str, rev: int | None = None) -> dict | None:
    """读某版本某修订的清单；rev 为 None 时取最高修订。"""
    if rev is None:
        rev = latest_revision(root, version)
        if rev is None:
            return None
    f = root / "versions" / version / manifest_filename(rev)
    if not f.is_file():
        return None
    meta = json.loads(f.read_text(encoding="utf-8"))
    meta.setdefault("revision", rev)   # 早期清单无 revision 字段，按文件名补足
    return meta


# ---------- commit ----------

def do_commit(root: Path, source: Path, note: str, alias: str) -> int:
    raw = (root / "VERSION").read_text(encoding="utf-8").strip()
    try:
        version = versioning.format_version(versioning.parse(raw))
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1

    files = collect_files(source)
    if not files:
        print(f"[失败] 未在 {source} 找到任何待跟踪文件")
        return 1

    files_map: dict[str, str] = {}
    new_blobs = reused = 0
    for rel, path in files:
        data = path.read_bytes()
        # 内层＝**文件级** blob 指纹；改名 `blob_digest` 以区别外层清单级 `digest`
        # （§P2-4：原名两处都叫 `digest`，易误读）。
        blob_digest = hashlib.sha256(data).hexdigest()
        target = blob_path(root, blob_digest)
        if target.is_file():
            reused += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            new_blobs += 1
        files_map[rel] = "sha256:" + blob_digest

    digest = "sha256:" + manifest_digest(files_map)

    existing = revisions(root, version)
    prev_rev = existing[-1] if existing else None
    prev_meta = load_manifest(root, version, prev_rev) if prev_rev else None

    if prev_meta is not None and prev_meta.get("digest") == digest:
        print(f"[跳过] {version} 现行修订 r{prev_rev} 的内容与当前 src/ 完全一致，无需新修订")
        return 0

    rev = (prev_rev or 0) + 1
    filename = manifest_filename(rev)
    dest = root / "versions" / version
    dest.mkdir(parents=True, exist_ok=True)

    previous_versions = [v for v in list_versions(root) if v != version]
    meta = {
        "version": version,
        "revision": rev,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(source),
        "note": note,
        "parent": previous_versions[-1] if previous_versions else None,
        "parentManifest": manifest_filename(prev_rev) if prev_rev else None,
        "legacyAlias": alias or None,
        "fileCount": len(files_map),
        "digest": digest,
        "files": files_map,
    }
    # 落盘换行固定为 LF：`Path.write_text` 默认 newline=None，Windows 上会把 \n 译成
    # CRLF，使清单字节随平台漂移（§编码基线：纳入版本控制的文本文件一律 LF）。
    # 这里曾是全项目**唯一**漏写 newline 的写盘点 —— 见《审查报告_工具链_20261010》§P1-1。
    with (dest / filename).open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, indent=2))

    label = f"{version}" if rev == 1 else f"{version}@r{rev}"
    print(f"[提交] {label} → {dest / filename}")
    print(f"[提交] 文件 {len(files_map)} 个：新增 blob {new_blobs} 个，复用已有 {reused} 个（去重生效）")
    print(f"[提交] 清单指纹 {digest[:23]}…  parent={meta['parent'] or '—'}  parentManifest={meta['parentManifest'] or '—'}")
    if rev > 1:
        print(f"[提交] 同版本第 {rev} 次修订（未升版）—— 回退点：python tools/store.py checkout {version}@r{rev}")
    if alias:
        print(f"[提交] 旧编号别名：{alias}")
    return 0


# ---------- checkout ----------

def do_checkout(root: Path, ref: str, dry_run: bool) -> int:
    try:
        version, rev = parse_ref(ref)
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1

    meta = load_manifest(root, version, rev)
    if meta is None:
        avail = revisions(root, version)
        if not avail:
            print(f"[失败] 未找到版本 {version} 的任何清单")
        else:
            listing = "、".join(f"r{r}" for r in avail)
            print(f"[失败] {version} 不存在修订 r{rev}；现有修订：{listing}")
        return 1

    label = f"{version}@r{meta['revision']}"
    files: dict[str, str] = meta.get("files", {})
    absent = [rel for rel, r in files.items() if not blob_path(root, r.split(":", 1)[-1]).is_file()]
    if absent:
        print(f"[失败] {len(absent)} 个 blob 缺失，无法完整回退：")
        for rel in absent[:10]:
            print(f"        {rel}")
        return 1

    current = {rel for rel, _ in collect_files(root)}
    stale = sorted(current - set(files))

    print(f"[回退] 目标 {label}，共 {len(files)} 个文件")
    if stale:
        print(f"[回退] 当前有 {len(stale)} 个文件不在目标版本内，将移入回收区（不真删）：")
        for rel in stale[:10]:
            print(f"        {rel}")
        if len(stale) > 10:
            print(f"        …另有 {len(stale) - 10} 个")

    if dry_run:
        print("[演练] --dry-run，未写入任何文件")
        return 0

    # 同秒内连续两次 checkout 会撞同一个回收目录（后一次的副本覆盖前一次）→ 加序号后缀
    # （§P2-5）。回收区是「只复制不删除」的兜底，撞目录会让前一次的被移出文件丢失副本。
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    trash = root / "store" / ".trash" / stamp
    seq = 2
    while trash.exists():
        trash = root / "store" / ".trash" / f"{stamp}_{seq:02d}"
        seq += 1
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
    for rel, r in files.items():
        digest = r.split(":", 1)[-1]
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
    total = sum(len(revisions(root, v)) for v in versions)
    print(f"[日志] {len(versions)} 个版本 / {total} 条清单（同版本内按修订倒序）")
    for v in versions:
        for rev in reversed(revisions(root, v)):
            meta = load_manifest(root, v, rev) or {}
            note = meta.get("note") or "—"
            parent = meta.get("parent") or "—"
            alias = meta.get("legacyAlias")
            tail = f"  [旧编号 {alias}]" if alias else ""
            base = "基线" if rev == 1 else f"修订{rev}"
            print(
                f"  {v:<9} r{rev:<2} {base:<4} {meta.get('createdAt', '?'):<20}"
                f" 文件 {meta.get('fileCount', '?'):>3}  parent={parent}  {note}{tail}"
            )
    return 0


def do_diff(root: Path, ref_a: str, ref_b: str) -> int:
    try:
        va, ra = parse_ref(ref_a)
        vb, rb = parse_ref(ref_b)
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1

    ma, mb = load_manifest(root, va, ra), load_manifest(root, vb, rb)
    if ma is None:
        print(f"[失败] 未找到 {ref_a}")
        return 1
    if mb is None:
        print(f"[失败] 未找到 {ref_b}")
        return 1

    fa, fb = ma.get("files", {}), mb.get("files", {})
    changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    added = sorted(set(fb) - set(fa))
    removed = sorted(set(fa) - set(fb))

    la = f"{va}@r{ma['revision']}"
    lb = f"{vb}@r{mb['revision']}"
    print(f"[差异] {la} → {lb}：改动 {len(changed)} / 新增 {len(added)} / 缺失 {len(removed)}")
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
    parser.add_argument("args", nargs="*", help="checkout: <版本[@rN]>；diff: <版本[@rN]> <版本[@rN]>")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--from", dest="source", default=None)
    parser.add_argument("--note", default="")
    parser.add_argument("--alias", default="")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()

    root = Path(opts.root).resolve()
    source = Path(opts.source).resolve() if opts.source else root

    if opts.action == "commit":
        # `--from` 复核（§P2-8）：清单里的相对路径以顶层 `src/` `start.bat` `VERSION` 为锚，
        # 因此 --from 指向 --root **之内的子目录**（如 `--from preview/V0.0.9`）必然错位
        # —— 会把该子树的 src/ 当成主线的 src/ 记进清单 → 硬拦。
        # 指向 --root **之外**的同构树快照属合法历史用法（N1→r2），只警告不拦。
        if source != root:
            if is_within(source, root):
                print(f"[失败] --from 不得指向 --root 之内的子目录：{source}")
                print("        清单相对路径以 root 为锚，子目录会令 manifest 与主线错位；")
                print("        若要提交同构树快照，请把内容先落回主线，或用 --root 指到该树。")
                return 1
            print(f"[警告] --from 不在 --root 之下：{source}")
            print("        清单相对路径以顶层 src/start.bat/VERSION 为锚，")
            print("        请确认该目录布局与主线同构，否则 verify --against 会失配。")
        return do_commit(root, source, opts.note, opts.alias)
    if opts.action == "checkout":
        if not opts.args:
            parser.error("checkout 需要一个版本号，如 V0.0.1 或 V0.0.1@r2")
        return do_checkout(root, opts.args[0], opts.dry_run)
    if opts.action == "diff":
        if len(opts.args) < 2:
            parser.error("diff 需要两个版本引用")
        return do_diff(root, opts.args[0], opts.args[1])
    if opts.action == "log":
        return do_log(root)
    return do_fsck(root)


if __name__ == "__main__":
    raise SystemExit(main())
