"""青蔓 QingMan · 业务路由。

每个函数只负责「收数据 → 交给核心逻辑 → 返回可序列化 dict」，
不碰 HTTP 细节，便于后续 CLI / 测试直接调用。
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from server import config, dtree_core
from server.dtree_core import TreeError

GENERATE_PATH = "/api/generate"
HEALTH_PATH = "/api/health"
EDITOR_PATH = "/api/editor"
SHORTCUT_PATH = "/api/shortcut"
TEMPLATES_PATH = "/api/templates"

# 编辑态文档结构版本；结构不兼容变更时递增（见 src/shared/schema.json）
EDITOR_SCHEMA_VERSION = 1

# 模板文件名白名单：仅允许「中英文、数字、下划线、连字符」+ `.json`。
# 不含路径分隔符，从源头堵死路径穿越（`..` / 子目录）。
TEMPLATE_NAME = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff-]+\.json$")


def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "app": config.APP_NAME_EN,
        "nameZh": config.APP_NAME_ZH,
        "version": config.read_version(),
    }


def generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    tree = payload.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("treeMissing")

    # 落盘安全边界（§P0-1 R1–R5）：规范化 + 黑名单校验，全在服务端完成。
    # 命中即抛 TreeError（明确的 4xx 错误码），绝不进入写盘流程。
    base = dtree_core.check_target(payload.get("target"))

    root = payload.get("root")
    root = root.strip() if isinstance(root, str) else ""
    if root:
        ok, reason = dtree_core.validate_segment(root)
        if not ok:
            raise TreeError(
                "segmentInvalid", name=root, reason=dtree_core.message(reason, name=root)
            )
        base = base / root

    result = dtree_core.build_tree(tree, base, dry_run=bool(payload.get("dryRun")))
    result["ok"] = True
    result["target"] = str(base)
    return result


def load_editor() -> Dict[str, Any]:
    """读取编辑态文档。

    文档不存在或为空 → `doc=None`（前端据此回落到默认示例）。
    文档存在但损坏 → 抛 editorCorrupt，**不静默当成空文档**（否则会悄悄覆盖用户数据）。
    """
    path = config.EDITOR_FILE
    if not path.is_file():
        return {"ok": True, "doc": None, "path": str(path)}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TreeError("editorReadFailed", message=str(exc))

    if not raw.strip():
        return {"ok": True, "doc": None, "path": str(path)}

    try:
        doc = json.loads(raw)
    except ValueError:
        raise TreeError("editorCorrupt", path=str(path))

    if not isinstance(doc, dict) or not isinstance(doc.get("root"), dict):
        raise TreeError("editorCorrupt", path=str(path))

    stats = dtree_core.validate_document(doc["root"])
    return {"ok": True, "doc": doc, "path": str(path), "stats": stats}


def save_editor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """校验并**原子写入**编辑态文档。非法内容一律拒写。"""
    doc = payload.get("doc")
    if not isinstance(doc, dict):
        raise TreeError("editorRootMissing")

    stats = dtree_core.validate_document(doc.get("root"))

    saved = {
        "schemaVersion": EDITOR_SCHEMA_VERSION,
        "savedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": doc["root"],
    }
    body = json.dumps(saved, ensure_ascii=False, indent=2) + "\n"
    size = len(body.encode("utf-8"))
    if size > config.MAX_EDITOR_BYTES:
        raise TreeError("editorTooLarge", limit=config.MAX_EDITOR_BYTES, actual=size)

    path = config.EDITOR_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    # 显式 newline="\n"：默认 newline=None 在 Windows 下会写成 CRLF，
    # 使返回的 bytes 与磁盘实际字节不符，且破坏跨平台字节一致性（§编码基线）。
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    os.replace(tmp, path)   # 原子替换：避免断电/中断留下半截文件

    return {
        "ok": True,
        "path": str(path),
        "savedAt": saved["savedAt"],
        "bytes": size,
        "stats": stats,
    }


def list_templates() -> Dict[str, Any]:
    """列出模板库。

    `templates/` **不在版本交付清单内**，预览副本里根本没有它 —— 目录缺失时
    返回 `available=False` + 空列表，**不报错**（否则预览版一启动就满屏红）。
    单套模板损坏也只跳过该套，不拖垮整个列表。
    """
    d = config.TEMPLATES_DIR
    if not d.is_dir():
        return {"ok": True, "available": False, "items": [], "path": str(d)}

    items: list[Dict[str, Any]] = []
    for p in sorted(d.glob("*.json")):
        if not TEMPLATE_NAME.match(p.name):
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("tree"), dict):
            continue
        dirs, files = dtree_core.count_tree(doc["tree"])
        items.append({
            "file": p.name,
            "name": doc.get("name") or p.stem,
            "description": doc.get("description") or "",
            "dirs": dirs,
            "files": files,
        })

    return {
        "ok": True,
        "available": True,
        "items": items,
        "path": str(d),
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
    }


def load_template(name: str) -> Dict[str, Any]:
    """读取单套模板的完整树。

    安全顺序：**先过文件名白名单**（不含路径分隔符，源头堵死穿越），
    **再校验解析后的绝对路径仍在 `templates/` 之内**（防符号链接等绕过）。
    """
    if not name or not TEMPLATE_NAME.match(name):
        raise TreeError("templateNotFound", name=str(name))

    base = config.resolve_path(config.TEMPLATES_DIR)
    path = config.resolve_path(base / name)
    if not config.is_within(path, base) or not path.is_file():
        raise TreeError("templateNotFound", name=name)

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TreeError("templateReadFailed", name=name, message=str(exc))
    try:
        doc = json.loads(raw)
    except ValueError:
        raise TreeError("templateBadJson", name=name)

    if not isinstance(doc, dict) or not isinstance(doc.get("tree"), dict):
        raise TreeError("templateBadJson", name=name)

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
        # 老模板没有该字段，一律视为当前版本（读取容忍缺失，写入必带 —— §P2 第 7 项）
        "schemaVersion": doc.get("schemaVersion", config.TEMPLATE_SCHEMA_VERSION),
    }


def save_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    """把一棵目录树另存为模板文件 `templates/<name>.json`（V0.0.13）。

    与 `generate()` 的关键差别：这里的落盘路径**不由用户给出** —— 恒定拼在
    `TEMPLATES_DIR` 之下，用户输入只有模板名，且必须过文件名白名单，
    因此不存在路径穿越面。仍保留 `is_within` 复核，防符号链接等绕过。

    **同名一律拒写**：静默覆盖会毁掉既有模板，改名是用户该做的决定
    （与落盘规则 R7/R8「已存在即跳过、永不删除」同一套取舍）。

    写入时必带 `schemaVersion` —— 只读阶段可以没有版本戳，一旦开始写就必须有，
    否则日后无法区分新旧格式（§P2 第 7 项）。
    """
    raw_name = payload.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not name:
        raise TreeError("templateNameEmpty")

    # 用户可能顺手带上 .json：剥掉再统一补回，避免 `X.json.json`
    stem = name[:-5] if name.lower().endswith(".json") else name
    stem = stem.strip()
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

    base = config.resolve_path(config.TEMPLATES_DIR)
    path = config.resolve_path(base / filename)
    if not config.is_within(path, base):
        raise TreeError("templateNameInvalid", name=name)
    if path.exists():
        raise TreeError("templateExists", name=name)

    body = json.dumps({
        "schemaVersion": config.TEMPLATE_SCHEMA_VERSION,
        "name": stem,
        "description": description,
        "updated": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "tree": tree,
    }, ensure_ascii=False, indent=2) + "\n"
    size = len(body.encode("utf-8"))
    if size > config.TEMPLATE_MAX_BYTES:
        raise TreeError("templateTooLarge", limit=config.TEMPLATE_MAX_BYTES, actual=size)

    try:
        base.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        # 显式 newline="\n"：默认在 Windows 下会写成 CRLF，破坏跨平台字节一致（§编码基线）
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, path)   # 原子替换，避免中断留下半截文件
    except OSError:
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
    }


def _write_lnk(path: Path, target: str, workdir: str) -> None:
    """用 PowerShell WScript.Shell 写一个 Windows 快捷方式（.lnk）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$sc = $ws.CreateShortcut({str(path)!r}); "
        f"$sc.TargetPath = {target!r}; "
        f"$sc.WorkingDirectory = {workdir!r}; "
        "$sc.Save()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise OSError(result.stderr or "PowerShell CreateShortcut failed")


def create_shortcut(payload: Dict[str, Any]) -> Dict[str, Any]:
    """在桌面生成启动快捷方式；若桌面不可写，降级为返回 .lnk 字节（base64）供下载。"""
    target = str(config.START_BAT)
    if not config.START_BAT.is_file():
        raise TreeError("shortcutTargetMissing", target=target)

    workdir = str(config.PROJECT_DIR)
    name = f"{config.APP_NAME_ZH} {config.APP_NAME_EN}.lnk"
    desktop = Path.home() / "Desktop"
    lnk = desktop / name

    try:
        _write_lnk(lnk, target, workdir)
        return {"ok": True, "path": str(lnk)}
    except OSError:
        # 桌面写入失败时，在临时目录生成同一份 .lnk 并返回 base64
        tmp = Path(tempfile.gettempdir()) / name
        try:
            _write_lnk(tmp, target, workdir)
            data = base64.b64encode(tmp.read_bytes()).decode("ascii")
            return {"ok": True, "fallback": True, "name": name, "data": data}
        except OSError as exc:
            raise TreeError("shortcutFailed", message=str(exc)) from exc
