"""青蔓 QingMan · 构建清单 `manifest.json`（版本之外的第二层，§P0-6 M9/M10）。

## 为什么要分两层

第一层（`VERSION` + `versions/<版本>/MANIFEST*.json`）只回答一件事：
**这个修订由哪些文件、什么指纹构成** —— 它必须能被 `store.py checkout` 逐字节还原，
因此不能承载会随每次重建而变的信息。

第二层（项目根 `manifest.json`）只回答另一件事：
**这次构建发生在何时（含时区）、由哪个模型、用什么工具链产生**。

把时间/模型/工具塞进 store 清单有三个坏处，都是实测过的：

  ① **自指** —— store 清单的 `digest` 是「相对路径 + 指纹」排序后的 SHA-256。
     一旦 `manifest.json` 进了 store 的文件集，「记录构建」这个动作本身就会改变
     被记录的对象，指纹比对永远差一格。
  ② **历史不可迁移** —— 76 份存量清单里根本没有模型/工具信息，迁移只能编造或留空。
  ③ **双写必然漂移** —— 同一事实写两处，迟早一处改了一处没改（§P0-6 M8 同一理由）。

## 同步：单向锚定，双向可查

  · 顶层 `version` **必须逐字等于** `VERSION` —— 这是两层唯一的连接点。
  · `builds[]` 必须含当前 `(version, 最新 store 修订)` 的记录 —— 少一条即「两层脱钩」。
  · 记录时间**不得早于**它所记录的 store 清单的 `createdAt` —— 记录不能早于事实。

判定逻辑集中在 `validate()`，由 `check` 子命令与 `tools/verify.py` 守卫 **7ap** 共用
（§P0-2 T2：承担判定职责的工具函数必须单一来源 + 必须有单元测试）。

## 刻意不做的事

  · **不检测托管 node**：只记「当前 PATH 上有什么」，取不到写 `not-on-PATH`。
    托管运行时的兜底扫描是 `verify.find_node()` 的职责，两处目的不同，不合并 —— 否则
    清单会记下「verify 用到的那份」而掩盖「构建时 PATH 上其实没有 node」。
  · **不写 `createdAtLocal`**：人读形态 `YYYY-MM-DD_HH-mm-ss` 已由 store 清单承担，
    同一时刻写两遍必然漂移（M8 已因此放弃过一次重复字段）。
  · **模型信息不猜**：取不到就写 `unknown` 哨兵，绝不从进程名/环境猜一个像真的值。

用法：

    python tools/manifest.py stamp --model <名字> [--vendor V] [--agent A] [--note T] [--force]
    python tools/manifest.py check
    python tools/manifest.py show [--last N]
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
sys.dont_write_bytecode = True  # 工具不得在项目内留下 __pycache__
from store import latest_revision, load_manifest  # noqa: E402

SCHEMA = "qm-manifest/1"
FILENAME = "manifest.json"

#: 记录键白名单（白名单式而非黑名单式：本仓反复踩过「字段悄悄加、无人同步」的坑）
RECORD_KEYS = ("version", "revision", "createdAt", "timezone", "model", "tools", "note")
MODEL_KEYS = ("name", "vendor", "agent")
TOOLS_KEYS = ("python", "node", "zlib", "os")
#: `node` 允许缺席（构建本身不依赖它），另外三项是构建事实的必需项
TOOLS_REQUIRED = ("python", "zlib", "os")

SEMVER_RE = re.compile(r"^V(\d+)\.(\d+)\.(\d+)$")
#: 带时区偏移的 ISO 8601（本项目唯一认可的时间写法：无偏移 = 无法跨机器比较）
ISO_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")
OFFSET_RE = re.compile(r"^(?:[+-]\d{2}:\d{2}|Z)$")
#: store 清单的两代人读时间写法（与 store.STAMP_PATTERNS 同源，只用于「记录不早于事实」比较）
STORE_STAMP_RES = (re.compile(r"^(\d{4}-\d{2}-\d{2})[ _]\d{2}[-:]\d{2}[-:]\d{2}$"),)


# ---------- 版本号形态 ----------

def semver_problem(text: Any) -> str:
    """返回版本号的问题描述；合法时返回空串。

    刻意不复用 `versioning.parse()`：它的正则 `(\\d+)` **接受前导零**
    （`V0.01.0` 会被读成 `0.1.0`），而 SemVer 2.0.0 §2 明文禁止前导零。
    """
    if not isinstance(text, str):
        return f"不是字符串：{text!r}"
    m = SEMVER_RE.match(text.strip())
    if not m:
        return f"不是 V<MAJOR>.<MINOR>.<PATCH> 三段式：{text!r}"
    for seg in m.groups():
        if len(seg) > 1 and seg.startswith("0"):
            return f"含前导零：{text!r}（SemVer 2.0.0 §2 禁止）"
    return ""


def read_version(root: Path) -> str:
    path = root / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


# ---------- 采集 ----------

def _node_version() -> str:
    """当前 PATH 上的 node 版本；取不到返回 `not-on-PATH`（不编造、不做托管兜底）。"""
    exe = shutil.which("node")
    if not exe:
        return "not-on-PATH"
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return "not-on-PATH"
    text = (out.stdout or "").strip().lstrip("v")
    return text or "not-on-PATH"


def collect_tools() -> Dict[str, str]:
    """构建工具链指纹。四项都取**实测值**，不写常量。"""
    return {
        "python": platform.python_version(),
        "node": _node_version(),
        "zlib": getattr(zlib, "ZLIB_RUNTIME_VERSION", zlib.ZLIB_VERSION),
        "os": platform.platform(),
    }


def now_stamp() -> "tuple[str, Dict[str, str]]":
    """（带偏移的 ISO 时间, 时区对象）。

    用 `astimezone()` 取本机时区而非 `utcnow()`：清单是给人看的历史记录。
    偏移必须与时间串一致 —— 两者由**同一个 `now`** 派生，不各算一次。
    """
    now = datetime.now().astimezone()
    raw = now.strftime("%z")
    offset = (raw[:3] + ":" + raw[3:]) if len(raw) == 5 else "Z"
    return now.isoformat(timespec="seconds"), {"name": now.tzname() or "unknown", "offset": offset}


# ---------- 读写 ----------

def empty_document(version: str = "") -> Dict[str, Any]:
    return {"schema": SCHEMA, "version": version, "builds": []}


def load(root: Path) -> Dict[str, Any]:
    """读清单；文件不存在时返回空骨架（**不建文件** —— `check` 必须能只读判定）。"""
    path = root / FILENAME
    if not path.is_file():
        return empty_document(read_version(root))
    return json.loads(path.read_text(encoding="utf-8"))


def save(root: Path, doc: Dict[str, Any]) -> Path:
    """落盘：LF 换行 + 两空格缩进 + 不转义中文。

    `newline="\\n"` 显式声明 —— `Path.write_text` 的 `newline` 参数 3.10 才有，
    本项目下限 3.8（§编码基线；同坑见《审查报告_工具链_20261010》§P1-1）。
    """
    path = root / FILENAME
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


# ---------- 记录 ----------

def has_record(doc: Dict[str, Any], version: str, revision: int) -> bool:
    for rec in doc.get("builds") or []:
        if isinstance(rec, dict) and rec.get("version") == version \
                and rec.get("revision") == revision:
            return True
    return False


def make_record(root: Path, model: str, vendor: str, agent: str, note: str) -> Dict[str, Any]:
    """按当前 `VERSION` 与 store 最新修订造一条记录。无 store 清单即报错（不造无主记录）。"""
    version = read_version(root)
    problem = semver_problem(version)
    if problem:
        raise ValueError(f"VERSION 不可用：{problem}")
    revision = latest_revision(root, version)
    if not revision:
        raise ValueError(f"{version} 尚无 store 清单 —— 先 `python tools/store.py commit` 再记构建")
    created_at, timezone = now_stamp()
    return {
        "version": version,
        "revision": revision,
        "createdAt": created_at,
        "timezone": timezone,
        "model": {"name": model or "unknown", "vendor": vendor or "unknown",
                  "agent": agent or "unknown"},
        "tools": collect_tools(),
        "note": note or "",
    }


# ---------- 判定（check 与 verify 7ap 共用） ----------

def store_day(root: Path, version: str, revision: int) -> str:
    """store 清单的日期前缀（`YYYY-MM-DD`）；取不到返回空串。

    只比**日期**不比起始时刻：两侧时区口径不同（store 记本地时间、本层记带偏移 ISO），
    逐秒比对会在跨时区构建时假红；「记录不早于事实」这个判据用日期就够。
    """
    meta = load_manifest(root, version, revision) or {}
    stamp = meta.get("createdAt")
    if not isinstance(stamp, str):
        return ""
    for pat in STORE_STAMP_RES:
        m = pat.match(stamp)
        if m:
            return m.group(1)
    return ""


def validate(doc: Any, version_text: str, latest_rev: Optional[int],
             known_versions: Optional[set] = None, store_day: str = "") -> List[str]:
    """返回清单的违规项列表；空表＝两层同步。

    `store_day` 是当前修订在 store 清单里的日期前缀（`YYYY-MM-DD`）—— 由调用方查好传进来，
    本函数**不读盘**（纯判定，才好单测）。空串表示不判「记录不早于事实」那一项。

    六个判据（每一条都对应一个**不会自己报错**的失配）：

      ① 结构：`schema` 必须是 `qm-manifest/1`；`builds` 必须是数组
      ② 连接：顶层 `version` **逐字**等于 `VERSION`（唯一连接点，不许模糊匹配）
      ③ 形态：`version` 是纯三段式、无前导零（日期/构建号一律不得进版本号）
      ④ 在场：存在当前 `(version, 最新修订)` 的记录 —— 少一条即两层脱钩
      ⑤ 时间：`createdAt` 带时区偏移、与时区对象一致、**不早于** store 清单日期
      ⑥ 字段：`model` 三键 / `tools` 三必需键齐全非空，记录键不得越出白名单
    """
    hits: List[str] = []
    if not isinstance(doc, dict):
        return ["manifest.json 不是 JSON 对象"]
    if doc.get("schema") != SCHEMA:
        hits.append(f"schema 应为 {SCHEMA!r}，实为 {doc.get('schema')!r}")

    top = doc.get("version")
    problem = semver_problem(top)
    if problem:
        hits.append(f"顶层 version {problem}")
    if isinstance(top, str) and isinstance(version_text, str) and top.strip() != version_text.strip():
        hits.append(f"顶层 version {top!r} 与 VERSION {version_text!r} 不一致（两层脱钩）")

    builds = doc.get("builds")
    if not isinstance(builds, list):
        hits.append("builds 不是数组")
        return hits

    if isinstance(top, str) and latest_rev:
        if not any(isinstance(r, dict) and r.get("version") == top
                   and r.get("revision") == latest_rev for r in builds):
            hits.append(f"缺 {top}@r{latest_rev} 的构建记录"
                        f"（当前版本的最新修订必须有记录，否则两层不同步）")

    for idx, rec in enumerate(builds):
        where = f"builds[{idx}]"
        if not isinstance(rec, dict):
            hits.append(f"{where} 不是对象")
            continue
        extra = sorted(set(rec) - set(RECORD_KEYS))
        if extra:
            hits.append(f"{where} 有未登记字段 {extra}（新增须同步 RECORD_KEYS 与守卫 7ap）")
        rv = rec.get("version")
        rp = semver_problem(rv)
        if rp:
            hits.append(f"{where} 的 version {rp}")
        if known_versions is not None and isinstance(rv, str) and rv not in known_versions:
            hits.append(f"{where} 记着不存在的版本 {rv!r}（versions/ 下无此目录）")
        rev = rec.get("revision")
        if not isinstance(rev, int) or isinstance(rev, bool) or rev < 1:
            hits.append(f"{where} 的 revision 应为 ≥1 的整数，实为 {rev!r}")

        created = rec.get("createdAt")
        tz = rec.get("timezone")
        if not isinstance(created, str) or not ISO_TZ_RE.match(created):
            hits.append(f"{where} 的 createdAt 不是带时区的 ISO 8601：{created!r}")
        if not isinstance(tz, dict):
            hits.append(f"{where} 的 timezone 不是对象")
        else:
            tz_extra = sorted(set(tz) - {"name", "offset"})
            if tz_extra:
                hits.append(f"{where} 的 timezone 有未登记字段 {tz_extra}")
            if not isinstance(tz.get("name"), str) or not tz.get("name", "").strip():
                hits.append(f"{where} 的 timezone.name 为空")
            off = tz.get("offset")
            if not isinstance(off, str) or not OFFSET_RE.match(off):
                hits.append(f"{where} 的 timezone.offset 非法：{off!r}")
            elif isinstance(created, str) and ISO_TZ_RE.match(created):
                tail = "Z" if created.endswith("Z") else created[-6:]
                if tail != off:
                    hits.append(f"{where} 的 createdAt 偏移 {tail} 与 timezone.offset {off} 不一致")

        model = rec.get("model")
        if not isinstance(model, dict):
            hits.append(f"{where} 缺 model 对象（模型信息必须显式记录，取不到写 unknown）")
        else:
            m_extra = sorted(set(model) - set(MODEL_KEYS))
            if m_extra:
                hits.append(f"{where} 的 model 有未登记字段 {m_extra}")
            for key in MODEL_KEYS:
                val = model.get(key)
                if not isinstance(val, str) or not val.strip():
                    hits.append(f"{where} 的 model.{key} 为空（取不到须写 unknown，不得留空）")

        tools = rec.get("tools")
        if not isinstance(tools, dict):
            hits.append(f"{where} 缺 tools 对象")
        else:
            t_extra = sorted(set(tools) - set(TOOLS_KEYS))
            if t_extra:
                hits.append(f"{where} 的 tools 有未登记字段 {t_extra}")
            for key in TOOLS_REQUIRED:
                val = tools.get(key)
                if not isinstance(val, str) or not val.strip():
                    hits.append(f"{where} 的 tools.{key} 缺失（工具链是构建事实，不得为空）")

    # ⑤ 记录不得早于它所记录的 store 清单（只在能定位到当前记录时判，避免历史噪声）
    if store_day and isinstance(top, str) and latest_rev:
        for rec in builds:
            if not isinstance(rec, dict) or rec.get("version") != top \
                    or rec.get("revision") != latest_rev:
                continue
            created = rec.get("createdAt")
            if isinstance(created, str) and created[:10] < store_day:
                hits.append(f"{top}@r{latest_rev} 的记录日期 {created[:10]} "
                            f"早于 store 清单日期 {store_day}（记录不能早于事实）")
            break
    return hits


def check(root: Path) -> List[str]:
    """读盘判定（供 CLI 与单测使用）。"""
    path = root / FILENAME
    if not path.is_file():
        return [f"缺 {FILENAME}（第二层未建立；用 `python tools/manifest.py stamp` 建档）"]
    try:
        doc = load(root)
    except (OSError, ValueError) as exc:
        return [f"{FILENAME} 读不成 JSON：{exc}"]
    version = read_version(root)
    known = {p.name for p in (root / "versions").iterdir() if p.is_dir()} \
        if (root / "versions").is_dir() else set()
    latest = latest_revision(root, version) if version else None
    fact_day = store_day(root, version, latest) if latest else ""
    return validate(doc, version, latest, known, fact_day)


# ---------- CLI ----------

def _cmd_stamp(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        doc = load(root)
    except (OSError, ValueError) as exc:
        print(f"[失败] {FILENAME} 读不成 JSON：{exc}（先修文件，不要覆盖）")
        return 1
    if not isinstance(doc, dict):
        print(f"[失败] {FILENAME} 不是 JSON 对象")
        return 1
    doc.setdefault("schema", SCHEMA)
    doc["builds"] = list(doc.get("builds") or [])
    version = read_version(root)
    doc["version"] = version          # 单向锚定：每次 stamp 都把连接点对齐 VERSION
    try:
        rec = make_record(root, args.model, args.vendor, args.agent, args.note)
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1
    if has_record(doc, rec["version"], rec["revision"]) and not args.force:
        print(f"[跳过] {rec['version']}@r{rec['revision']} 已有构建记录"
              f"（同一修订不重复记；确需再记一次用 --force）")
        return 0
    doc["builds"].append(rec)
    path = save(root, doc)
    print(f"[记录] {rec['version']}@r{rec['revision']} → {path}")
    print(f"[记录] 时间 {rec['createdAt']}（{rec['timezone']['name']}）"
          f" 模型 {rec['model']['name']}  Python {rec['tools']['python']}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    hits = check(root)
    if hits:
        print(f"[不同步] {len(hits)} 项：")
        for hit in hits:
            print(f"  · {hit}")
        return 2
    doc = load(root)
    print(f"[同步] version={doc['version']}　构建记录 {len(doc['builds'])} 条　"
          f"最新 {doc['builds'][-1]['version']}@r{doc['builds'][-1]['revision']}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    doc = load(root)
    builds = doc.get("builds") or []
    print(f"[清单] version={doc.get('version')}　共 {len(builds)} 条记录")
    for rec in builds[-args.last:]:
        tz = (rec.get("timezone") or {}).get("offset", "?")
        model = (rec.get("model") or {}).get("name", "?")
        tools = rec.get("tools") or {}
        print(f"  {rec.get('version')}@r{rec.get('revision')}  {rec.get('createdAt')} ({tz})"
              f"  {model}  py{tools.get('python', '?')}  {tools.get('os', '?')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 构建清单（版本之外的第二层）")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="项目根（默认本仓）")
    sub = parser.add_subparsers(dest="action", required=True)

    p_stamp = sub.add_parser("stamp", help="为当前版本的最新修订追加一条构建记录")
    p_stamp.add_argument("--model", default="unknown", help="模型名（取不到写 unknown，不要猜）")
    p_stamp.add_argument("--vendor", default="unknown")
    p_stamp.add_argument("--agent", default="unknown")
    p_stamp.add_argument("--note", default="")
    p_stamp.add_argument("--force", action="store_true", help="同一修订已有记录时仍追加（重建）")
    p_stamp.set_defaults(func=_cmd_stamp)

    p_check = sub.add_parser("check", help="判定两层是否同步（RC=0 同步 / 2 不同步）")
    p_check.set_defaults(func=_cmd_check)

    p_show = sub.add_parser("show", help="人读最后 N 条记录")
    p_show.add_argument("--last", type=int, default=5)
    p_show.set_defaults(func=_cmd_show)

    # --root 放在主解析器上，子命令用 args.root 读取；也允许写在动作之后
    for p in (p_stamp, p_check, p_show):
        p.add_argument("--root", dest="root", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
