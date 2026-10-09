"""青蔓 QingMan · 业务路由。

每个函数只负责「收数据 → 交给核心逻辑 → 返回可序列化 dict」，
不碰 HTTP 细节，便于后续 CLI / 测试直接调用。
"""

from __future__ import annotations

import base64
import json
import os
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

# 编辑态文档结构版本；结构不兼容变更时递增（见 src/shared/schema.json）
EDITOR_SCHEMA_VERSION = 1


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
