"""青蔓 QingMan · 模板包校验与打包（§十.3 E 分发层 · 批 6D）。

把「`templates-pack/` 的 16 套业务模板 + 内置 `templates/P0_空白项目模板.json`」固化为
**可复算**的分发包：逐套校验 → 反向解析 `.md` 与原 `.json` **逐节点等价** → 写
`pack.manifest.json`（含逐套 sha256 与整份清单 digest）→ 确定性构建 `QingMan-模板包.zip`。

用法：
    python tools/pack_templates.py [--check] [--zip PATH] [--pack-dir DIR] [--templates-dir DIR]

退出码：0 通过；1 环境 / IO 错误（包目录或内置件缺失，抛 `PackIOError`）；
        2 内容校验不通过（等价性 / 规范渲染 / 孤儿 `.md` / 缺同名件 / 清单不一致）。

        两类必须分开：内容坏了要人改模板，环境缺件多半是路径 / 部署问题。同码会让
        CI 把「模板被改坏」误报成「环境没配好」（本契约由 `tests/test_pack_templates.py`
        的 `CheckModeTests` 与反向验证 N7a 共同锁住）。

约定：
  * `.md` 为**主分发格式**（AI / Agent / Skill 直读），`.json` 为等价副本。
  * `P0_空白项目模板.md` 与内置 `templates/P0_空白项目模板.json` **同源**；该 `.json`
    **不在本包内**（它是工具唯一内置模板，随工具交付）。
  * 清单**入版本库**（纯文本、可 diff、digest 可复算）；`*.zip` **不入库** —— 它是
    可由包目录恒定推导的**可再生产物**（`.gitignore` 收口，§P1-4 / §P1-7 R3 同理）。
  * **确定性**：zip 条目时间戳固定 + 名字典序 + 固定压缩参数 → 同一份源连跑两次
    字节相同（§P1-4「工具幂等」）。跨 Python 运行时不做字节承诺。
  * 本工具**不进** `store.TRACK_ITEMS`；`templates/` 与 `templates-pack/` 同样不进
    （版本清单只跟踪 `src` / `start.bat` / `VERSION`，见 §P0-6）。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from server import dtree_core as dtree_core  # noqa: E402

DEFAULT_PACK_DIR = PROJECT_ROOT / "templates-pack"
DEFAULT_TEMPLATES_DIR = PROJECT_ROOT / "templates"
BUILTIN_JSON = "P0_空白项目模板.json"
MANIFEST_NAME = "pack.manifest.json"
ZIP_NAME = "QingMan-模板包.zip"
# 包目录内的**非模板**说明件（没有 `.json` 等价件，不算孤儿）
PACK_DOC_FILES = ("模板库来源说明.md",)
SCHEMA_VERSION = 1

# 清单 digest 的**规范化规则**（同时写入清单的 `digestRule` 字段，便于第三方独立复算）：
#   sha256(utf8(json.dumps(<清单去掉 digest / zip 两键>, ensure_ascii=False,
#                         sort_keys=True, separators=(",", ":"))))
# 说明：`digestRule` 自身**参与**运算（只有 `digest` 与 `zip` 两键被排除），
# 故改动规则文本同样会使 digest 失配。
DIGEST_RULE = ('sha256(utf8(json.dumps(<本清单去掉 digest / zip 两键>, '
               'ensure_ascii=False, sort_keys=True, separators=(",", ":"))))')

ZIP_STAMP = (1980, 1, 1, 0, 0, 0)
ZIP_MODE = 0o644 << 16


class PackError(Exception):
    """模板包校验失败（内容不对等 / 结构非法 / 清单失配）。"""


class PackIOError(PackError):
    """环境 / IO 类失败（包目录或内置件缺失）—— 与「内容不通过」区分：本类返回 1。

    反向验证 N7a（2026-10-11）暴露：孤儿 `.md` 与缺同名件原本也走 `discover()`，
    与环境错误同码 1，而 docstring 声称其为 2。拆类后由 `main()` 分流，契约自洽。
    """


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rel_to(path: Path, base: Path) -> str:
    """相对 `base` 的 POSIX 风格路径；不在其下则退化为 `..` 相对路径。"""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), base.resolve()).replace(os.sep, "/")


def discover(pack_dir: Path, templates_dir: Path) -> List[Dict[str, Any]]:
    """盘点 17 套模板：内置 P0（`.json` 在 `templates_dir`）+ 16 套（`pack_dir` 内成对）。

    每套记为 `{stem, json_path, md_path, json_rel, md_rel}`；按 stem 升序。
    """
    if not pack_dir.is_dir():
        raise PackIOError(f"找不到模板包目录：{pack_dir}")
    if not templates_dir.is_dir():
        raise PackIOError(f"找不到内置模板目录：{templates_dir}")

    entries: List[Dict[str, Any]] = []

    builtin_json = templates_dir / BUILTIN_JSON
    builtin_md = pack_dir / (BUILTIN_JSON[:-5] + ".md")
    if not builtin_json.is_file():
        raise PackIOError(f"缺内置模板：{builtin_json}")
    if not builtin_md.is_file():
        raise PackIOError(f"缺内置模板的 .md 同源件：{builtin_md}")
    entries.append({
        "stem": BUILTIN_JSON[:-5],
        "json_path": builtin_json,
        "md_path": builtin_md,
        "json_rel": _rel_to(builtin_json, pack_dir),
        "md_rel": _rel_to(builtin_md, pack_dir),
        "builtin": True,
    })

    for json_path in sorted(pack_dir.glob("*.json")):
        if json_path.name == MANIFEST_NAME:
            continue
        md_path = pack_dir / (json_path.stem + ".md")
        if not md_path.is_file():
            raise PackError(f"{json_path.name} 缺同名 .md 等价件")
        entries.append({
            "stem": json_path.stem,
            "json_path": json_path,
            "md_path": md_path,
            "json_rel": _rel_to(json_path, pack_dir),
            "md_rel": _rel_to(md_path, pack_dir),
            "builtin": False,
        })

    # 孤儿 `.md`：没有 `.json` 等价件（也非说明件）—— 只按 `.json` 收集会让它**静默消失**，
    # 套数悄悄少一套而无人察觉，故此处显式拒绝。
    paired = {e["stem"] for e in entries}
    known_docs = set(PACK_DOC_FILES)
    for md_path in sorted(pack_dir.glob("*.md")):
        if md_path.stem in paired or md_path.name in known_docs:
            continue
        raise PackError(f"孤儿 {md_path.name}：缺同名 .json 等价件（或登记进 PACK_DOC_FILES）")

    entries.sort(key=lambda e: e["stem"])
    return entries


def load_doc(entry: Dict[str, Any]) -> Dict[str, Any]:
    """读并缓存该套的 `.json` 文档（同一轮内避免重复解析）。"""
    if "doc" not in entry:
        try:
            entry["doc"] = json.loads(entry["json_path"].read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise PackError(f"{entry['stem']}：.json 无法解析（{exc}）") from exc
    return entry["doc"]


def validate_entry(entry: Dict[str, Any]) -> Tuple[int, int]:
    """校验单套：`.json` 结构合法 + `.md` **逐节点等价** + `.md` 自身为往返不动点。

    返回 `(dirs, files)`。任一不符抛 `PackError`。等价口径为 `name` / `description` /
    `tree` 三字段（`.md` 不承载 `updated` / `schemaVersion`，见 6A 设计）。
    """
    stem = entry["stem"]
    doc = load_doc(entry)
    dirs, files = dtree_core.validate_template(doc)

    md_text = entry["md_path"].read_text(encoding="utf-8")
    try:
        back = dtree_core.parse_md_template(md_text)
    except Exception as exc:                       # TreeError 基类为 Exception
        raise PackError(f"{stem}：.md 解析失败（{exc}）") from exc

    for field in ("name", "description"):
        a = doc.get(field) or ""
        b = back.get(field) or ""
        if a != b:
            raise PackError(f"{stem}：.md 与 .json 的 {field} 不等价")
    if doc.get("tree") != back.get("tree"):
        raise PackError(f"{stem}：.md 与 .json 的 tree 不等价（逐节点比对失败）")

    if dtree_core.render_md_template(back) != md_text:
        raise PackError(f"{stem}：.md 不是规范渲染（往返不定点；请按 .json 重生成）")

    return dirs, files


def validate_pack(entries: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """逐套校验，返回 `(套数, 目录总数, 文件总数)`。"""
    tot_d = tot_f = 0
    for entry in entries:
        d, f = validate_entry(entry)
        tot_d += d
        tot_f += f
    return len(entries), tot_d, tot_f


def build_payload(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构造清单主体（**不含** `digest` / `zip` 两键，二者由 `finalize_manifest` 补）。"""
    items = []
    tot_d = tot_f = 0
    for entry in entries:
        d, f = validate_entry(entry)
        tot_d += d
        tot_f += f
        doc = load_doc(entry)
        items.append({
            "stem": entry["stem"],
            "name": doc.get("name") or "",
            "description": doc.get("description") or "",
            "dirs": d,
            "files": f,
            "builtin": bool(entry["builtin"]),
            "md": {"file": entry["md_rel"], "sha256": sha256_bytes(entry["md_path"].read_bytes())},
            "json": {"file": entry["json_rel"],
                     "sha256": sha256_bytes(entry["json_path"].read_bytes())},
        })
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": "tools/pack_templates.py",
        "digestRule": DIGEST_RULE,
        "count": len(items),
        "totals": {"dirs": tot_d, "files": tot_f},
        "templates": items,
    }


def canonical_bytes(payload: Dict[str, Any]) -> bytes:
    """`digest` / `zip` 两键之外的规范化序列化（键名升序、无多余空白、UTF-8）。"""
    body = {k: v for k, v in payload.items() if k not in ("digest", "zip")}
    return json.dumps(body, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def payload_digest(payload: Dict[str, Any]) -> str:
    return "sha256:" + sha256_bytes(canonical_bytes(payload))


def zip_members(pack_dir: Path) -> List[Path]:
    """zip 收录规则：包目录内**除清单与既有 zip 外**的全部文件，按名字典序。"""
    out = []
    for p in sorted(pack_dir.iterdir(), key=lambda q: q.name):
        if not p.is_file():
            continue
        if p.name == MANIFEST_NAME or p.suffix.lower() == ".zip":
            continue
        out.append(p)
    return out


def build_zip_bytes(pack_dir: Path) -> bytes:
    """确定性 zip：固定条目时间戳 / 权限位 / 创建系统 + 名字典序 + 固定压缩级。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        for p in zip_members(pack_dir):
            info = zipfile.ZipInfo(p.name, date_time=ZIP_STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = ZIP_MODE
            zf.writestr(info, p.read_bytes())
    return buf.getvalue()


def finalize_manifest(payload: Dict[str, Any], pack_dir: Path,
                      zip_file_field: str, zip_bytes: bytes) -> Dict[str, Any]:
    out = dict(payload)
    out["digest"] = payload_digest(payload)
    out["zip"] = {
        "file": zip_file_field,
        "members": len(zip_members(pack_dir)),
        "sha256": sha256_bytes(zip_bytes),
    }
    return out


def render_manifest(manifest: Dict[str, Any]) -> bytes:
    """清单落盘字节：缩进 2、键名升序、UTF-8、LF 结尾（§编码基线）。"""
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return text.replace("\r\n", "\n").encode("utf-8")


def _write_atomic(path: Path, data: bytes) -> None:
    """唯一临时名 + `os.replace` 原子替换（§A-P3-2 体例）。"""
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def load_manifest(pack_dir: Path) -> Dict[str, Any]:
    path = pack_dir / MANIFEST_NAME
    if not path.is_file():
        raise PackError(f"清单缺失：{path}（先跑一次默认模式生成）")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise PackError(f"{MANIFEST_NAME} 无法解析（{exc}）") from exc


def main(argv: "List[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="校验 templates-pack/（17 套）并生成清单与确定性 zip")
    parser.add_argument("--check", action="store_true",
                        help="只校验：17/17 + md/json 等价 + 清单与盘上一致 + digest/zip 可复算；不写盘")
    parser.add_argument("--zip", dest="zip_path", default=None,
                        help=f"zip 落点（默认 <包目录>/{ZIP_NAME}）")
    parser.add_argument("--pack-dir", dest="pack_dir", default=str(DEFAULT_PACK_DIR))
    parser.add_argument("--templates-dir", dest="templates_dir",
                        default=str(DEFAULT_TEMPLATES_DIR))
    args = parser.parse_args(argv)

    pack_dir = Path(args.pack_dir).resolve()
    templates_dir = Path(args.templates_dir).resolve()

    try:
        entries = discover(pack_dir, templates_dir)
    except PackIOError as exc:            # 包目录 / 内置件缺失 —— 环境类，返回 1
        print(f"[失败] {exc}")
        return 1
    except PackError as exc:              # 孤儿 `.md` / 缺同名件 —— 内容类，返回 2
        print(f"[失败] {exc}")
        return 2

    try:
        n, tot_d, tot_f = validate_pack(entries)
    except PackError as exc:
        print(f"[失败] {exc}")
        return 2
    print(f"[校验] 套数 {n} / 目录 {tot_d} / 文件 {tot_f} —— 逐套 md↔json 逐节点等价通过")

    try:
        payload = build_payload(entries)
    except PackError as exc:
        print(f"[失败] {exc}")
        return 2
    if payload["count"] != n or payload["totals"] != {"dirs": tot_d, "files": tot_f}:
        print("[失败] 清单合计与逐套校验不一致")
        return 2

    zip_default = pack_dir / ZIP_NAME
    zip_out = Path(args.zip_path).resolve() if args.zip_path else zip_default
    zip_field = (zip_out.name if zip_out.parent == pack_dir
                 else zip_out.as_posix())
    zip_bytes = build_zip_bytes(pack_dir)
    manifest = finalize_manifest(payload, pack_dir, zip_field, zip_bytes)

    if args.check:
        return _run_check(pack_dir, manifest, zip_out, zip_bytes)

    _write_atomic(pack_dir / MANIFEST_NAME, render_manifest(manifest))
    _write_atomic(zip_out, zip_bytes)
    print(f"[清单] {MANIFEST_NAME}  digest={manifest['digest']}")
    print(f"[打包] {zip_out}  members={manifest['zip']['members']}  "
          f"sha256={manifest['zip']['sha256']}")
    print("[结论] 全部通过")
    return 0


def _run_check(pack_dir: Path, manifest: Dict[str, Any], zip_out: Path,
               zip_bytes: bytes) -> int:
    """校验模式：清单内容 + digest + zip sha256 三项复算；不写盘。"""
    bad = []
    try:
        on_disk = load_manifest(pack_dir)
    except PackError as exc:
        print(f"[失败] {exc}")
        return 2

    want_can = canonical_bytes(manifest)
    got_can = canonical_bytes(on_disk)
    if want_can != got_can:
        bad.append("清单主体与盘上模板不一致（有人改了模板未重生成清单）")

    if on_disk.get("digest") != payload_digest(on_disk):
        bad.append("清单 digest 复算失配")
    elif manifest["digest"] != on_disk.get("digest"):
        bad.append("清单 digest 与当前模板不符")

    got_zip = (on_disk.get("zip") or {})
    if got_zip.get("sha256") != sha256_bytes(zip_bytes):
        bad.append("zip sha256 复算失配")
    if got_zip.get("members") != len(zip_members(pack_dir)):
        bad.append("zip 条目数与盘上不符")
    if zip_out.is_file():
        if sha256_bytes(zip_out.read_bytes()) != sha256_bytes(zip_bytes):
            bad.append(f"{zip_out.name} 实体与确定性构建不一致")
    else:
        print(f"[提示] {zip_out.name} 不在盘上（可再生产物不入库），仅核 sha256 复算值")

    print(f"[校验] 清单 digest={on_disk.get('digest')}  "
          f"zip sha256={got_zip.get('sha256')}")
    if bad:
        for item in bad:
            print(f"  [不一致] {item}")
        print("[结论] --check 不通过")
        return 2
    print("[结论] --check 通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
