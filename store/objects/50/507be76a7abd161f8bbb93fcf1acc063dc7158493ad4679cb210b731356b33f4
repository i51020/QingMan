"""青蔓 QingMan · 模板子系统（目录绑定判据 / 列表 / 读取 / 保存 / 改名 / 导入导出）。

**为什么从 `routes.py` 迁出**（V0.0.54，§P0-6 M9「只改实现、契约不动」→ 升 PATCH）：
`routes.py` 已到 62,374 B / 单文件上限 65,536 B（余 4.8%），再加服务端功能必撞线。
历史上 `backups.py`（V0.0.51@r9）/ `modules/templates.js`（V0.0.48）/
`modules/selection.js`（V0.0.43）三次同因拆分，结论一致 —— **拆模块，不是放宽阈值**。

## 与 `routes.py` 的分工

  · **本模块**：模板是什么、放哪、怎么读写 —— 含**目录绑定判据**（CRUD 的落点由它决定）
  · **`routes.py`**：HTTP 端点与请求/响应形状（`get_templates_dir` / `set_templates_dir` /
    `pick_templates_dir` 仍留在那边，只 import 本模块的判据）

导出方式刻意用**显式 import**（不用 `import *`）：让「谁被搬走了」在 `routes.py` 里一眼可数，
也让 `mock.patch.object(routes, name)` 继续有效。

## 搬迁纪律（硬约束）

函数体**逐字节照搬** —— 不顺手改逻辑、不顺手改注释、不顺手改名。验收三条：
  ① 每个函数的**新旧源码逐字节等价**（本文件保持原顶层缩进 ⇒ 应 0 差异）
  ② 四件套全绿（`verify` / `unittest` / `smoke` / `browser_smoke`）
  ③ 对外端点、错误码、响应字段**一字不变**
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from server import config, dtree_core
from server.common import _tmp_sibling
from server.dtree_core import TreeError


_TPL_STEM_PATTERN = r"[A-Za-z0-9_\u4e00-\u9fff-]+"
TEMPLATE_NAME = re.compile(r"^" + _TPL_STEM_PATTERN + r"\.json$")
TEMPLATE_FILE = re.compile(r"^" + _TPL_STEM_PATTERN + r"\.(?:json|md)$")
# 可被「剥离」的模板扩展名（另存 / 改名时用户顺手带上 `.json` / `.md` 不报错）。
_TEMPLATE_EXTS = (".json", ".md")


def _template_source(filename: str) -> str:
    """按扩展名判模板格式来源：`"md"` 或 `"json"`（大小写不敏感）。"""
    return "md" if filename.lower().endswith(".md") else "json"


def _strip_template_ext(name: str) -> str:
    """剥掉模板扩展名（`.json` / `.md`，大小写不敏感）—— 用户顺手带上不报错。"""
    low = name.lower()
    for ext in _TEMPLATE_EXTS:
        if low.endswith(ext):
            return name[: -len(ext)]
    return name


def _read_template_doc(path: Path, *, name: str) -> Dict[str, Any]:
    """按扩展名**分派读取**并把模板归一为 `{name?, description?, tree}`。

    · `.md` → `dtree_core.parse_md_template`（严格文法；非法抛 `templateBadMarkdown` /
      `templateSiblingDuplicated`）；
    · `.json` → `json.loads`，随后要求「是对象且 `tree` 是对象」—— **错误码与语义同本函数
      引入前逐字一致**（一律 `templateBadJson`），以免改变既有 `.json` 的对外行为。

    读取失败统一抛 `templateReadFailed`。列表侧调用时会吞掉这些异常（单套损坏只跳过）。
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # 同 load_editor：非法 UTF-8 抛 UnicodeDecodeError（ValueError 族），须一并捕获。
        raise TreeError("templateReadFailed", name=name, message=str(exc))
    if _template_source(path.name) == "md":
        return dtree_core.parse_md_template(raw)
    try:
        doc = json.loads(raw)
    except ValueError:
        raise TreeError("templateBadJson", name=name)
    if not isinstance(doc, dict) or not isinstance(doc.get("tree"), dict):
        raise TreeError("templateBadJson", name=name)
    return doc


def list_templates() -> Dict[str, Any]:
    """列出模板库（**双格式**：`*.json` + `*.md`，V0.0.36 · 6C）。

    `templates/` **不在版本交付清单内**，预览副本里根本没有它 —— 目录缺失时
    返回 `available=False` + 空列表，**不报错**（否则预览版一启动就满屏红）。
    单套模板损坏也只跳过该套，不拖垮整个列表。

    每项带 `source`（`"json"` / `"md"`）标明来源格式；两种格式**同一套读取与计数口径**，
    故列表里能看到的，`load_template` 一定能读到（共用 `_read_template_doc`）。

    每项另带 `mtime`（`st_mtime`，float 秒）与 `size`（字节，V0.0.38 · 6E）—— 供前端
    轮询做「`file + mtime + size` 三元组签名」变化判据：**内容没变就不重渲染**，
    否则每 2.5s 一次的重建会让正在浏览的列表跳回去
    （风险与缓解见《模板系统重设计_方案原型_20261011.md》第八节）。
    统计失败（列表期间文件被外部删除）只跳过该套，与「单套损坏只跳过」同一取舍。
    """
    d = config.resolve_path(config.templates_dir())
    # 绑定目录非法（自绑 / 系统区）或缺失 → 一律「不可用」，既不报错、也不去 glob
    # 一个本就不该被读的位置（`QM_TEMPLATES_DIR` 可绕过 UI 直接指定目录，这是兜底）。
    # 用**运行态**判据：默认 `templates/` 是合法运行目录，故 `_templates_dir_reason`。
    blocked = _templates_dir_reason(d)
    if blocked or not d.is_dir():
        return {"ok": True, "available": False, "items": [], "skipped": [],
                "path": str(d), "reason": blocked}

    items: list[Dict[str, Any]] = []
    # **被跳过的条目要留痕**（V0.4.0）：此前解析失败的模板被静默 `continue` ——
    # 用户看到的是「文件明明在目录里，列表里却没有」，且**完全没有任何提示**，
    # 只能靠人肉猜测（2026-10-21 实证：一份围栏未闭合的 `.md` 就这样消失了）。
    # 现在把「跳过了谁、为什么」一并回传，由前端提示；判据仍是「单套坏了不拖垮整个列表」。
    skipped: list[Dict[str, Any]] = []
    # 两个 glob 合并后统一排序（按小写名 + 原名，跨平台确定性；`.trash/` 是子目录，扫不到）。
    found = sorted(list(d.glob("*.json")) + list(d.glob("*.md")),
                   key=lambda q: (q.name.lower(), q.name))
    for p in found:
        if not TEMPLATE_FILE.match(p.name):
            continue
        try:
            doc = _read_template_doc(p, name=p.name)
        except (TreeError, OSError, ValueError) as exc:
            # 单套损坏只跳过该套（含 `.md` 解析失败）—— 但**必须记进 skipped**
            code = getattr(exc, "code", "") or ("ioError" if isinstance(exc, OSError) else "templateBadJson")
            detail = getattr(exc, "detail", None) or {}
            skipped.append({
                "file": p.name,
                "code": code,
                # `reason` 取解析器给的机器可读原因（如 `unclosed fence`），缺则留空
                "reason": str(detail.get("reason", "") or ""),
            })
            continue
        try:
            st = p.stat()
        except OSError:
            continue   # 列表期间被外部删除：跳过该套，不拖垮整个列表
        dirs, files = dtree_core.count_tree(doc["tree"])
        items.append({
            "file": p.name,
            "name": doc.get("name") or p.stem,
            "description": doc.get("description") or "",
            "dirs": dirs,
            "files": files,
            "mtime": st.st_mtime,
            "size": st.st_size,
            "source": _template_source(p.name),
        })

    return {
        "ok": True,
        "available": True,
        "reason": "",
        "items": items,
        # V0.4.0：被跳过的条目（文件名 + 错误码 + 原因）。前端据此提示，
        # 让「目录里有、列表里没有」不再无从解释。空列表 = 全部解析正常。
        "skipped": skipped,
        "path": str(d),
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
    }


def load_template(name: str) -> Dict[str, Any]:
    """读取单套模板的完整树（**双格式分派**：`.json` / `.md`，V0.0.36 · 6C）。

    安全顺序：**先过文件名白名单**（不含路径分隔符，源头堵死穿越），
    **再校验解析后的绝对路径仍在 `templates/` 之内**（防符号链接等绕过）。
    该两步已收敛到 `_template_path_or_raise`（删除/重命名共用同一来源）。
    """
    path = _template_path_or_raise(name)
    doc = _read_template_doc(path, name=name)

    # 模板 `tree` 是**嵌套字典**（目录=dict、文件=内容字符串），与编辑态文档的
    # 「id / type / children」结构**不同** —— 故统计用 count_tree 而非 validate_document。
    # 两者格式的差异与演进策略登记在 docs/项目约定.md §P2 第 7 项。
    dirs, files = dtree_core.count_tree(doc["tree"])
    return {
        "ok": True,
        "file": name,
        "name": doc.get("name") or path.stem,
        "description": doc.get("description") or "",
        "tree": doc["tree"],
        "stats": {"dirs": dirs, "files": files},
        "source": _template_source(name),
        # 老模板没有该字段，一律视为当前版本（读取容忍缺失，写入必带 —— §P2 第 7 项）
        "schemaVersion": doc.get("schemaVersion", config.TEMPLATE_SCHEMA_VERSION),
    }


def export_template(name: str, fmt: str = "") -> Dict[str, Any]:
    """导出模板文本（`GET /api/templates-export/<name>[?format=json|md]`，V0.0.38 · 6E）。

    **不传 `format`（或与源格式相同）＝ 原样交回**，不做任何再序列化 ——
    「导出 → 再导入」因此与原件一致（单一真源；前端另写一套渲染器必然漂移）。

    **V0.2.0 起可选目标格式**（用户裁定：模板默认 `.json`，但导出时两种都该给）：
      · `.json` 源要 `.md` → `render_md_template`（与「另存为模板」同一渲染器）
      · `.md` 源要 `.json` → `parse_md_template` + `json.dumps`
    转换前后都过 `validate_template`（全量校验），**坏模板不借导出洗白**。
    未知格式值按原样返回，不新增错误码（调用方只可能是本前端）。
    """
    path = _template_path_or_raise(name)
    raw = path.read_text(encoding="utf-8")
    source = _template_source(name)
    want = (fmt or "").strip().lower()
    if want and want != source and want in ("json", "md"):
        if want == "md":
            doc = json.loads(raw)
            dtree_core.validate_template(doc)
            text, out_name = dtree_core.render_md_template(doc), path.stem + ".md"
        else:
            doc = dtree_core.parse_md_template(raw)
            dtree_core.validate_template(doc)
            text, out_name = json.dumps(doc, ensure_ascii=False, indent=2) + "\n", path.stem + ".json"
        return {"ok": True, "file": out_name, "name": path.stem, "source": want, "text": text}
    return {
        "ok": True,
        "file": name,
        "name": path.stem,
        "source": source,
        "text": raw,
    }


def save_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    """把一棵目录树另存为模板文件 `templates/<name>.json`（V0.0.13）。

    与 `generate()` 的关键差别：这里的落盘路径**不由用户给出** —— 恒定拼在
    `TEMPLATES_DIR` 之下，用户输入只有模板名，且必须过文件名白名单，
    因此不存在路径穿越面。仍保留 `is_within` 复核，防符号链接等绕过。

    **同名默认仍一律拒写**：静默覆盖会毁掉既有模板，改名是用户该做的决定
    （与落盘规则 R7/R8「已存在即跳过、永不删除」同一套取舍）。**V0.0.21 起**
    允许用户在**显式确认**后覆盖：载荷带 `overwrite: true` 时，旧模板先移入
    `templates/.trash/<时间戳>/` 再写新文件 —— 延续「只复制不删除」，误覆盖可人工找回。
    未带该字段（或非严格 true）时行为与旧版完全一致。

    写入时必带 `schemaVersion` —— 只读阶段可以没有版本戳，一旦开始写就必须有，
    否则日后无法区分新旧格式（§P2 第 7 项）。
    """
    raw_name = payload.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not name:
        raise TreeError("templateNameEmpty")

    # 用户可能顺手带上扩展名：剥掉再统一补回 `.json`，避免 `X.json.json`（V0.0.36 起
    # 同时剥 `.md` —— 双格式列表上线后，「另存为 X.md」应是「存为模板 X」而非报错）。
    stem = _strip_template_ext(name).strip()
    if not stem:
        raise TreeError("templateNameEmpty")
    if len(stem) > config.TEMPLATE_NAME_MAX:
        raise TreeError("templateNameTooLong", name=name)
    filename = stem + ".json"
    if not TEMPLATE_NAME.match(filename):
        raise TreeError("templateNameInvalid", name=name)

    tree = payload.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("templateTreeMissing")

    dirs, files = dtree_core.count_tree(tree)
    total = dirs + files
    if total > config.MAX_NODES:
        raise TreeError(
            "templateTooManyNodes",
            dirs=dirs, files=files, total=total, limit=config.MAX_NODES,
        )

    description = payload.get("description")
    description = description.strip() if isinstance(description, str) else ""

    base = _templates_dir_or_raise()
    path = config.resolve_path(base / filename)
    if not config.is_within(path, base):
        raise TreeError("templateNameInvalid", name=name)

    body = json.dumps({
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
        "name": stem,
        "description": description,
        "updated": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "tree": tree,
    }, ensure_ascii=False, indent=2) + "\n"
    size = len(body.encode("utf-8"))
    # 体积检查**必须在覆盖旧文件之前**（P3-11）：否则超限抛错时旧模板已入回收站，
    # 原位置凭空消失，形成半完成态。
    if size > config.TEMPLATE_MAX_BYTES:
        raise TreeError("templateTooLarge", limit=config.TEMPLATE_MAX_BYTES, actual=size)

    # 同名处理（V0.0.21）：默认拒写；仅当载荷显式 overwrite=true 时覆盖，
    # 且旧模板**先入回收站**再写（延续「只复制不删除」；`is True` 严格判定，
    # 避免 "true" 等真值字符串被误当开关）。
    overwritten = False
    trashed_old = None
    if path.exists():
        if payload.get("overwrite") is not True:
            raise TreeError("templateExists", name=name)
        trash = _template_trash_dir()
        try:
            trash.mkdir(parents=True, exist_ok=True)
            os.replace(path, trash / filename)   # 同盘移动，原子；误覆盖可人工找回
        except OSError:
            raise TreeError("templateWriteFailed", name=name)
        trashed_old = trash / filename
        overwritten = True

    try:
        base.mkdir(parents=True, exist_ok=True)
        tmp = _tmp_sibling(path)   # A-P3-2：唯一临时名，避免并发写互相覆盖
        # 显式 newline="\n"：默认在 Windows 下会写成 CRLF，破坏跨平台字节一致（§编码基线）
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, path)   # 原子替换，避免中断留下半截文件
    except OSError:
        # P3-11 写失败回滚：旧模板已入回收站时把它移回原位，免得「覆盖失败 → 模板消失」。
        # 回滚本身再失败也不抛新错 —— 旧文件仍在 .trash，可人工找回。
        if trashed_old is not None:
            try:
                os.replace(trashed_old, path)
            except OSError:
                pass
        # 不把 OSError 原文拼进错误码：那会在英文界面里混排 Python 异常原文
        raise TreeError("templateWriteFailed", name=name)

    return {
        "ok": True,
        "file": filename,
        "name": stem,
        "path": str(path),
        "bytes": size,
        "stats": {"dirs": dirs, "files": files},
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
        "overwritten": overwritten,
    }


def _template_path_or_raise(name: str) -> "Path":
    """把模板名解析为绑定目录下的真实路径（过白名单 + is_within 复核）。

    与 `load_template` 同一套校验：先过文件名白名单（源头堵死路径穿越），
    再校验解析后的绝对路径仍在模板目录之内（防符号链接绕过）。
    **白名单用 `TEMPLATE_FILE`（`.json` / `.md` 双格式）** —— 读取 / 删除 / 改名共用。
    """
    if not name or not TEMPLATE_FILE.match(name):
        raise TreeError("templateNotFound", name=str(name))
    base = _templates_dir_or_raise()
    path = config.resolve_path(base / name)
    if not config.is_within(path, base) or not path.is_file():
        raise TreeError("templateNotFound", name=name)
    return path


def _template_trash_dir() -> "Path":
    """本次软删除**独占**的回收站目录：`templates/.trash/<YYYYMMDD-HHMMSS[-NNN]>/`。

    秒级戳不够（A-P3-3）：同一秒内对**同名模板**二次覆盖/删除会复用同一目录，后一次
    把前一次刚移入的旧版**原地覆盖**（软删除内丢失，找不回来）。故目录已存在即追加
    `-NNN` 序号；序号补零到 3 位避免字典序陷阱，同一秒内至多几次，不会产生碎目录。
    """
    base = _templates_dir_or_raise() / config.TEMPLATE_TRASH_DIRNAME
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    candidate = base / stamp
    seq = 2
    while candidate.exists():
        candidate = base / f"{stamp}-{seq:03d}"
        seq += 1
    return candidate


def delete_template(name: str) -> Dict[str, Any]:
    """删除单套模板（V0.0.20）—— **软删除**：移入 `templates/.trash/<时间戳>/`。

    不真删的原因：项目总原则「只复制不删除」，且模板是用户资产，误删可人工找回。
    回收站目录以 `.` 开头且非递归，`list_templates` 的 `glob("*.json")` 扫不到它。
    """
    path = _template_path_or_raise(name)
    trash = _template_trash_dir()
    try:
        trash.mkdir(parents=True, exist_ok=True)
        os.replace(path, trash / name)   # 同盘移动，原子
    except OSError:
        raise TreeError("templateDeleteFailed", name=name)
    return {"ok": True, "file": name, "trashedTo": str(trash / name)}


def rename_template(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """重命名单套模板（V0.0.20）。

    **同时改文件名与文件内 `name` 字段** —— 前者决定 URL，后者决定列表显示名，
    两者不一致会让用户看到「点了 A 却载入 B」。目标模板名已存在一律拒绝（沿用
    `templateExists` 拒写取舍）。旧文件移入回收站保底，不直接删除。
    **V0.0.36 起保持原格式**：`.json` / `.md` 各自改名后仍是原格式（不跨格式转换）。
    """
    path = _template_path_or_raise(name)
    # 改名**保持原格式**（V0.0.36 · 6C）：`.md` 进则 `.md` 出 —— 不把用户的 md 偷偷转成 json。
    ext = ".md" if _template_source(name) == "md" else ".json"

    raw_new = payload.get("name")
    new_name = raw_new.strip() if isinstance(raw_new, str) else ""
    if not new_name:
        raise TreeError("templateNameEmpty")
    stem = _strip_template_ext(new_name).strip()
    if not stem:
        raise TreeError("templateNameEmpty")
    if len(stem) > config.TEMPLATE_NAME_MAX:
        raise TreeError("templateNameTooLong", name=new_name)
    new_filename = stem + ext
    if not TEMPLATE_FILE.match(new_filename):
        raise TreeError("templateNameInvalid", name=new_name)
    if new_filename == name:
        return {"ok": True, "file": name, "name": path.stem, "unchanged": True}

    base = _templates_dir_or_raise()
    new_path = config.resolve_path(base / new_filename)
    if not config.is_within(new_path, base):
        raise TreeError("templateNameInvalid", name=new_name)
    if new_path.exists():
        raise TreeError("templateExists", name=new_name)

    if ext == ".md":
        try:
            doc = dtree_core.parse_md_template(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # 读不到 / 非法 UTF-8（`.md` 解析自身抛的 `TreeError` 不在此列，原样上抛）
            raise TreeError("templateRenameFailed", name=name)
        doc["name"] = stem
        body = dtree_core.render_md_template(doc)
    else:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise TreeError("templateBadJson", name=name)
        if not isinstance(doc, dict):
            raise TreeError("templateBadJson", name=name)
        doc["name"] = stem
        body = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    trash = _template_trash_dir()
    try:
        tmp = _tmp_sibling(new_path)   # A-P3-2：唯一临时名，避免并发写互相覆盖
        # 显式 newline="\n"：跨平台字节一致（§编码基线）
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, new_path)        # ① 先落新文件（原子）
        trash.mkdir(parents=True, exist_ok=True)
        os.replace(path, trash / name)   # ② 旧文件移入回收站保底，不真删
    except OSError:
        # P3-11 回滚：新文件已落而旧文件入回收站失败 → 把新文件也移入回收站，
        # 恢复「原位置只有旧文件」的状态（避免新旧并存）。仍不真删（只复制不删除）。
        try:
            if new_path.is_file():
                trash.mkdir(parents=True, exist_ok=True)
                os.replace(new_path, trash / new_filename)
        except OSError:
            pass
        raise TreeError("templateRenameFailed", name=name)

    return {
        "ok": True,
        "file": new_filename,
        "name": stem,
        "path": str(new_path),
        "bytes": len(body.encode("utf-8")),
    }


def import_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    """导入一套模板（V0.0.36 · 6C）—— 收 `.json` / `.md` **原文**，**归一后落盘**。

    与 `save_template` 的分工：

    | | 输入 | 产出格式 | 校验强度 |
    |---|---|---|---|
    | `save_template` | 前端已结构化的 `tree` 对象 | 恒 `.json` | 段名 + 规模（沿用既有） |
    | `import_template` | 模板**文件原文**（字符串） | **保持原格式**（`.md` 进 `.md` 出） | **全量** `validate_template` |

    「归一」＝内容先解析成内部文档、过 `validate_template`、再按规范**重新序列化**：

    · `.md` → `parse_md_template` → `render_md_template`（手工书写的多余空行 / 缩进随手，
      导入后变成确定性产物，与导出侧逐字节对齐 —— 「导入 → 导出」可成环）；
    · `.json` → `json.loads` → 补 `schemaVersion` / `updated` 后重 dump。

    落盘路径**不由用户给出**：恒定拼在**绑定模板目录**之下，文件名过 `TEMPLATE_FILE`
    白名单，仍保留 `is_within` 复核。同名默认**拒写**；载荷带严格 `overwrite: true` 时
    覆盖，且旧模板**先入 `.trash/`** 保底（比照 `save_template`，延续「只复制不删除」）。
    """
    raw_name = payload.get("filename")
    filename = raw_name.strip() if isinstance(raw_name, str) else ""
    if not filename:
        raise TreeError("templateNameEmpty")
    if not TEMPLATE_FILE.match(filename):
        raise TreeError("templateNameInvalid", name=filename)
    source = _template_source(filename)

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        raise TreeError("templateEmpty")

    # 解析 + **全量校验**（导入是质量闸门：段名 / 同层重名 / 规模一并拦下）
    if source == "md":
        doc = dtree_core.parse_md_template(content)
    else:
        try:
            doc = json.loads(content)
        except ValueError:
            raise TreeError("templateBadJson", name=filename)
        if not isinstance(doc, dict):
            raise TreeError("templateBadJson", name=filename)
    dirs, files = dtree_core.validate_template(doc)
    if dirs + files == 0:
        raise TreeError("templateEmpty")

    # 显示名：优先内容自带 `name`，缺省回落文件名主干（文件决定 URL，name 决定显示）
    stem = _strip_template_ext(filename)
    doc_name = doc.get("name")
    name = doc_name.strip() if isinstance(doc_name, str) else ""
    name = name or stem
    description = doc.get("description")
    description = description if isinstance(description, str) else ""

    if source == "md":
        body = dtree_core.render_md_template({
            "name": name, "description": description, "tree": doc["tree"]})
    else:
        body = json.dumps({
            "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
            "name": name,
            "description": description,
            "updated": datetime.now().astimezone().strftime("%Y-%m-%d"),
            "tree": doc["tree"],
        }, ensure_ascii=False, indent=2) + "\n"

    size = len(body.encode("utf-8"))
    # 体积检查**必须在覆盖旧文件之前**（比照 save_template P3-11），否则超限抛错时旧模板已入回收站。
    if size > config.TEMPLATE_MAX_BYTES:
        raise TreeError("templateTooLarge", limit=config.TEMPLATE_MAX_BYTES, actual=size)

    base = _templates_dir_or_raise()
    path = config.resolve_path(base / filename)
    if not config.is_within(path, base):
        raise TreeError("templateNameInvalid", name=filename)

    overwritten = False
    trashed_old = None
    if path.exists():
        if payload.get("overwrite") is not True:
            raise TreeError("templateExists", name=filename)
        trash = _template_trash_dir()
        try:
            trash.mkdir(parents=True, exist_ok=True)
            os.replace(path, trash / filename)   # 同盘移动，原子；误覆盖可人工找回
        except OSError:
            raise TreeError("templateWriteFailed", name=filename)
        trashed_old = trash / filename
        overwritten = True

    try:
        base.mkdir(parents=True, exist_ok=True)
        tmp = _tmp_sibling(path)   # A-P3-2：唯一临时名，避免并发写互相覆盖
        # 显式 newline="\n"：跨平台字节一致（§编码基线）
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, path)
    except OSError:
        # 写失败回滚：旧模板已入回收站时移回原位（同 save_template P3-11）。
        if trashed_old is not None:
            try:
                os.replace(trashed_old, path)
            except OSError:
                pass
        raise TreeError("templateWriteFailed", name=filename)

    return {
        "ok": True,
        "file": filename,
        "name": name,
        "source": source,
        "path": str(path),
        "bytes": size,
        "stats": {"dirs": dirs, "files": files},
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
        "overwritten": overwritten,
    }


# ---------- 模板目录绑定（V0.0.35 · §P2 第 7 项 · 设计方案见《模板系统重设计_方案原型_20261011》） ----------


def _same_path(a: Path, b: Path) -> bool:
    """路径等同判定：Windows 下须大小写不敏感（`Path.__eq__` 是大小写敏感的）。"""
    try:
        return os.path.normcase(str(a)) == os.path.normcase(str(b))
    except (OSError, ValueError):
        return a == b


def _templates_dir_blocked(path: Path) -> str:
    """**绑定**判据：返回拒绝原因（空串＝可绑定）。

    复用既有落盘边界（§P0-1 R3/R4/R5），只新增「拒自绑」两条：
      * 等于内置 `templates/` 本身 —— 它是只读内置层，用户不该把**用户库**绑到它；
      * 等于项目根、或是项目根的**祖先**（`is_within(PROJECT_DIR, d)`）——
        后者会把青蔓自身乃至整盘当成模板库。
    用户关键目录（R4）只拒**根本身**，其子目录是正常目标（与 `check_target` 同口径）。
    """
    resolved = config.resolve_path(path)
    if _same_path(resolved, config.resolve_path(config.DEFAULT_TEMPLATES_DIR)):
        return "内置模板目录不可作为用户库"
    if config.is_within(config.PROJECT_DIR_RESOLVED, resolved):
        return "指向青蔓自身或其上级目录"
    for root, label in config.BLOCKED_SUBTREES:
        if config.is_within(resolved, root):
            return label
    for root, label in config.BLOCKED_ROOTS:
        if _same_path(resolved, root):
            return label
    return ""


def _templates_dir_reason(path: Path) -> str:
    """**运行态**判据：默认目录（内置层）天生合法，其余复用绑定判据。

    与 `_templates_dir_blocked` 只差这一条 —— 未绑定时运行态目录**就是**内置
    `templates/`（`list_templates` 与「另存为模板」的既有行为都依赖它），若一并判
    非法，工具一启动就「模板库不可用」，那是把「不许绑定」错当成「不许使用」。
    """
    resolved = config.resolve_path(path)
    if _same_path(resolved, config.resolve_path(config.DEFAULT_TEMPLATES_DIR)):
        return ""
    return _templates_dir_blocked(resolved)


def _templates_dir_or_raise() -> Path:
    """解析并校验运行态模板目录；不合法即抛 `templateDirBlocked`。

    **所有**模板写路径（另存 / 改名 / 删除 / 回收站）都先过这里 —— `QM_TEMPLATES_DIR`
    可绕过 UI 直接指定目录，若只在绑定端点把关，写操作就能落到受保护位置。
    """
    d = config.resolve_path(config.templates_dir())
    reason = _templates_dir_reason(d)
    if reason:
        raise TreeError("templateDirBlocked", dir=str(d), reason=reason)
    return d
