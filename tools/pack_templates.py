"""青蔓 QingMan · 模板包校验与打包（§十.3 E 分发层 · 批 6D）。

把 `templates-pack/` 的 **16 套业务模板**固化为**可复算**的分发包：逐套校验 →
反向解析 `.md` 与原 `.json` **逐节点等价** → 写 `pack.manifest.json`（含逐套 sha256
与整份清单 digest）→ 确定性构建 `QingMan-模板包.zip`。

用法：
    python tools/pack_templates.py [--check] [--zip PATH] [--pack-dir DIR] [--templates-dir DIR]

**三种模式**（2026-10-16 裁定：把「打包到别处」与「改仓内清单」解耦，见《错误笔记》§三.79）：
  * 默认（不带 `--zip`）：校验 → **写清单** → 打 zip 到 `<包目录>/QingMan-模板包.zip`；
  * `--zip PATH`：校验 → **只产 zip 到 PATH**，**不触碰**仓内清单（清单只由默认模式刷新）；
  * `--check`：只校验，不写盘。

退出码：0 通过；1 环境 / IO 错误（包目录或内置件缺失，抛 `PackIOError`）；
        2 内容校验不通过（等价性 / 规范渲染 / 孤儿 `.md` / 缺同名件 / 清单不一致）。

        两类必须分开：内容坏了要人改模板，环境缺件多半是路径 / 部署问题。同码会让
        CI 把「模板被改坏」误报成「环境没配好」（本契约由 `tests/test_pack_templates.py`
        的 `CheckModeTests` 与反向验证 N7a 共同锁住）。

约定：
  * `.md` 为**主分发格式**（AI / Agent / Skill 直读），`.json` 为等价副本。
  * **项目内只有一套空模板**：`templates/P0_空白项目模板.json` 是工具唯一内置空模板，随
    工具交付；本包**只放 16 套业务模板**，**不得**再收它的同名件（2026-10-16 裁定：原
    `P0_空白项目模板.md` 同源件已移出）。包内引用自此**全部落在包目录内**，不再跨目录
    指向 `../templates/`。`--templates-dir` 因此不产出任何条目，只作该约束的**负向守卫**。
  * 清单**入版本库**（纯文本、可 diff、digest 可复算）；`*.zip` **不入库** —— 它是
    可由包目录恒定推导的**可再生产物**（`.gitignore` 收口，§P1-4 / §P1-7 R3 同理）。
  * **确定性**：zip 条目时间戳固定 + 名字典序 + 固定压缩参数 → 同一份源连跑两次
    字节相同（§P1-4「工具幂等」）。跨 Python 运行时不做字节承诺。
  * **运行时指纹**（V0.0.51 修订，见《错误笔记》§三.78）：既然上面的字节承诺**只限
    同一运行时**，清单 `zip.env` 就登记**构建时**的 `python` / `zlib` 指纹 —— 使
    「同一运行时」这一前提**可判定**，不再靠假设。`--check` 与单测据此分流：
    指纹一致 → 比绝对 `sha256`；不一致 → 降级为**自洽断言**（本运行时连跑两次字节
    相同）并**显式声明降级**，不静默放过。
    ⚠️ 病根是实测出来的：CPython 3.14 的 Windows 构建用 **zlib-ng**，其 deflate 输出
    与上游 zlib 不同 —— 同一份源在两个解释器下重建出 **24,693 B vs 24,270 B** 两个
    zip，绝对 `sha256` 必然失配。原实现「文档说不承诺、机器却强判」自相矛盾（§三.7
    的镜像形态）。
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
import zlib
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


def build_env_fingerprint() -> Dict[str, str]:
    """本运行时指纹：决定 zip 字节的那两个变量（§三.78）。

    `zlib` 取 **运行时** 版本（`ZLIB_RUNTIME_VERSION`）而非编译期常量 —— 实测
    CPython 3.14 的 Windows 构建把它报成 `1.3.1.zlib-ng`，与上游 zlib 的 `1.3.1`
    可区分；这正是 deflate 输出分叉的判据来源。**承担判定职责 → 有单测。**
    """
    return {
        "python": sys.version.split()[0],
        "zlib": zlib.ZLIB_RUNTIME_VERSION,
    }


def _rel_to(path: Path, base: Path) -> str:
    """相对 `base` 的 POSIX 风格路径；不在其下则退化为 `..` 相对路径。"""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), base.resolve()).replace(os.sep, "/")


def discover(pack_dir: Path, templates_dir: Path) -> List[Dict[str, Any]]:
    """盘点**包内 16 套业务模板**（`pack_dir` 内 `.md` / `.json` 成对）。

    每套记为 `{stem, json_path, md_path, json_rel, md_rel}`；按 stem 升序。

    `templates_dir` **不产出条目**，只作两条**负向守卫**，把「项目内只有一套空模板」
    变成机器可判的事实（2026-10-16 裁定）：
      ① 内置层有且仅有那**一套**空模板 —— 业务模板回流到 `templates/` 即报错；
      ② 包内**不得**出现该空模板的同名件 —— 否则导入后列表会多出第二套空模板。
    """
    if not pack_dir.is_dir():
        raise PackIOError(f"找不到模板包目录：{pack_dir}")
    if not templates_dir.is_dir():
        raise PackIOError(f"找不到内置模板目录：{templates_dir}")

    # ① 内置件缺失 → 环境类（返回 1，与「内容不通过」分码）。
    if not (templates_dir / BUILTIN_JSON).is_file():
        raise PackIOError(f"缺内置空模板：{templates_dir / BUILTIN_JSON}")
    # ② 内置层**混入了别的件** → 内容类（返回 2）：这是「工具不带业务模板」失守。
    built_ins = sorted(p.name for p in templates_dir.iterdir() if p.is_file())
    if built_ins != [BUILTIN_JSON]:
        raise PackError(f"templates/ 应只留内置空模板 {BUILTIN_JSON}，实测 {built_ins}")
    # ③ 包内不得再放同一套空模板 —— 「项目内只有一套空模板」的正面判据。
    builtin_stem = BUILTIN_JSON[:-5]
    for stray_name in (builtin_stem + ".md", builtin_stem + ".json"):
        if (pack_dir / stray_name).is_file():
            raise PackError(
                f"包内不得再收内置空模板的同名件：{stray_name}"
                f"（项目内只允许 {templates_dir.name}/{BUILTIN_JSON} 一套空模板）")

    entries: List[Dict[str, Any]] = []

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


def zip_self_consistent(pack_dir: Path, reference: "bytes | None" = None) -> bool:
    """自洽判据：`reference`（省略则现构建一次）与**再构建一次**的字节是否相同。

    这是「确定性」的真实语义 —— 工具 docstring 承诺的从来不是**跨运行时**同一串
    字节，而是**同一份源连跑两次字节相同**（§P1-4「工具幂等」）。**承担判定职责
    → 有单测，含反向用例。**
    """
    if reference is None:
        reference = build_zip_bytes(pack_dir)
    return build_zip_bytes(pack_dir) == reference


def _fmt_env(env: "Dict[str, str] | None") -> str:
    """把指纹渲染成人读串；缺失（旧清单）显式写「未登记」而非空白。"""
    if not env:
        return "未登记"
    return f"python {env.get('python', '?')} / zlib {env.get('zlib', '?')}"


def finalize_manifest(payload: Dict[str, Any], pack_dir: Path,
                      zip_file_field: str, zip_bytes: bytes) -> Dict[str, Any]:
    out = dict(payload)
    out["digest"] = payload_digest(payload)
    out["zip"] = {
        "file": zip_file_field,
        "members": len(zip_members(pack_dir)),
        "sha256": sha256_bytes(zip_bytes),
        # 构建时运行时指纹：让「同运行时才比绝对 sha256」这一前提**可判定**（§三.78）。
        # 放在 `zip` 块内 → 由 `canonical_bytes` 规则自动**不进 digest**，
        # 故登记指纹不会改动已入库的 `digest`（零 ripple）。
        "env": build_env_fingerprint(),
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
        description="校验 templates-pack/（16 套）并生成清单与确定性 zip")
    parser.add_argument("--check", action="store_true",
                        help="只校验：16/16 + md/json 等价 + 清单与盘上一致 + digest/zip 可复算；不写盘")
    parser.add_argument("--zip", dest="zip_path", default=None,
                        help=f"只产 zip 到该落点（默认 <包目录>/{ZIP_NAME}）；**不写清单**"
                             "（清单只由默认模式刷新）")
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
    zip_bytes = build_zip_bytes(pack_dir)
    # 清单 `zip.file` **恒为**仓内规范分发件名 —— 不再随 `--zip` 落点漂移（§三.79）：
    # 「这次打到哪儿」是一次性诉求，不是包的结构事实，不该写进仓内产物。
    manifest = finalize_manifest(payload, pack_dir, ZIP_NAME, zip_bytes)

    if args.check:
        return _run_check(pack_dir, manifest, zip_default, zip_bytes)

    if args.zip_path:
        # `--zip <路径>` = **只产 zip、不动清单**（2026-10-16 裁定）。诊断 / 实验用它时，
        # 仓内清单不再被顺带改写 —— 原先那种耦合正是 §三.79 记录的那个坑。
        _write_atomic(zip_out, zip_bytes)
        print(f"[打包] {zip_out}  members={manifest['zip']['members']}  "
              f"sha256={manifest['zip']['sha256']}")
        print(f"[清单] 未触碰（--zip 只产 zip；要刷新 {MANIFEST_NAME} 请不带 --zip 跑默认模式）")
        print("[结论] 全部通过")
        return 0

    _write_atomic(pack_dir / MANIFEST_NAME, render_manifest(manifest))
    _write_atomic(zip_default, zip_bytes)
    print(f"[清单] {MANIFEST_NAME}  digest={manifest['digest']}")
    print(f"[打包] {zip_default}  members={manifest['zip']['members']}  "
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
    env_now = build_env_fingerprint()
    env_rec = got_zip.get("env")
    # 条目数与运行时无关 → 恒比（它不依赖 zlib 实现）
    if got_zip.get("members") != len(zip_members(pack_dir)):
        bad.append("zip 条目数与盘上不符")
    if env_rec == env_now:
        # 同一运行时：字节承诺成立，绝对 sha256 与实体都可比
        if got_zip.get("sha256") != sha256_bytes(zip_bytes):
            bad.append("zip sha256 复算失配")
        if zip_out.is_file():
            if sha256_bytes(zip_out.read_bytes()) != sha256_bytes(zip_bytes):
                bad.append(f"{zip_out.name} 实体与确定性构建不一致")
        else:
            print(f"[提示] {zip_out.name} 不在盘上（可再生产物不入库），仅核 sha256 复算值")
    else:
        # 运行时指纹不同 → **字节不可比**（工具 docstring 本就写明「跨运行时不做字节
        # 承诺」，§三.78）。降级为自洽断言，且**显式声明降级** —— 静默少一项会让
        # 「覆盖变薄」看起来和「全过」一样（§P2 第 20 项）。
        if not zip_self_consistent(pack_dir, zip_bytes):
            bad.append("本运行时 zip 自洽断言失败（同一份源连跑两次字节不同）")
        print(f"[提示] 运行时指纹与清单不一致：清单 {_fmt_env(env_rec)} → 本机 {_fmt_env(env_now)}")
        print("[提示] 跨运行时字节不作承诺（工具 docstring / §三.78）→ 已降级为**自洽断言**，"
              "绝对 sha256 未比对")
        if zip_out.is_file():
            print(f"[提示] {zip_out.name} 实体亦未比对（它可能由另一运行时构建）")
        print("[提示] 需比对绝对 sha256 时，请在构建该清单的同一运行时下重跑 `--check`")

    print(f"[校验] 清单 digest={on_disk.get('digest')}  "
          f"zip sha256={got_zip.get('sha256')}  zip env={_fmt_env(env_rec)}")
    if bad:
        for item in bad:
            print(f"  [不一致] {item}")
        print("[结论] --check 不通过")
        return 2
    print("[结论] --check 通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
