"""青蔓 QingMan · 业务路由。

每个函数只负责「收数据 → 交给核心逻辑 → 返回可序列化 dict」，
不碰 HTTP 细节，便于后续 CLI / 测试直接调用。
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import struct
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
# 皮肤联动的桌面图标上传（V0.0.15）：前端 canvas 绘制、后端只落盘与接线
ICON_PATH = "/api/launch-icon"
# 「跟随系统」要跟的是 **操作系统语言**，不是浏览器语言（V0.0.14）。
# 浏览器语言可被单独改写（装浏览器时选了英文、或用户手动调过），
# 与「系统显示语言」不是一回事 —— 故由后端取真值，再经本端点同步注入前端。
ENV_PATH = "/api/env.js"

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
        # 便于诊断：OS 语言与浏览器语言不一致时，看这一项就知道前端会采信谁
        "osLocale": os_locale(),
    }


def os_locale() -> str:
    """操作系统 UI 语言的 BCP 47 标签（如 `zh-CN` / `en-US`）；取不到返回空串。

    浏览器只暴露**自己的**语言偏好（`navigator.languages`），它可以被单独改写
    （安装时选了别的语言、或用户在设置里调过），并不等于系统显示语言。
    真值只能问 OS：Windows 用 `GetUserDefaultLocaleName`（Vista+，返回 `zh-CN` 形态）。

    取不到（非 Windows、API 缺失、调用失败）一律返回空串 —— 调用方据此回落到
    浏览器语言，绝不因为探测失败就改变既有行为。
    """
    if os.name != "nt":
        return ""
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(85)
        # LOCALE_NAME_MAX_LENGTH = 85
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, len(buf)):
            return (buf.value or "").strip()
    except (OSError, AttributeError, ValueError):
        return ""
    return ""


def env_script() -> str:
    """一段**同步**注入 OS 语言的小脚本（响应 `GET /api/env.js`）。

    为什么不是接口：语言必须在**首屏渲染之前**定下来。若走 `fetch('/api/health')`
    这类异步接口，界面会先按浏览器语言画一遍、拿到结果后再跳变 —— 即语言闪烁。
    用普通 `<script src>` 同步加载，执行时机早于 module 脚本，取值零延迟。

    内容恒为 ASCII（BCP 47 标签），仍用 json.dumps 转义，杜绝注入面。
    """
    return "window.__QM_OS_LOCALE__ = " + json.dumps(os_locale()) + ";\n"


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
    该两步已收敛到 `_template_path_or_raise`（删除/重命名共用同一来源）。
    """
    path = _template_path_or_raise(name)

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

    # 同名处理（V0.0.21）：默认拒写；仅当载荷显式 overwrite=true 时覆盖，
    # 且旧模板**先入回收站**再写（延续「只复制不删除」；`is True` 严格判定，
    # 避免 "true" 等真值字符串被误当开关）。
    overwritten = False
    if path.exists():
        if payload.get("overwrite") is not True:
            raise TreeError("templateExists", name=name)
        trash = _template_trash_dir()
        try:
            trash.mkdir(parents=True, exist_ok=True)
            os.replace(path, trash / filename)   # 同盘移动，原子；误覆盖可人工找回
        except OSError:
            raise TreeError("templateWriteFailed", name=name)
        overwritten = True

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
        "overwritten": overwritten,
    }


def _template_path_or_raise(name: str) -> "Path":
    """把模板名解析为 `templates/` 下的真实路径（过白名单 + is_within 复核）。

    与 `load_template` 同一套校验：先过文件名白名单（源头堵死路径穿越），
    再校验解析后的绝对路径仍在 `templates/` 之内（防符号链接绕过）。
    """
    if not name or not TEMPLATE_NAME.match(name):
        raise TreeError("templateNotFound", name=str(name))
    base = config.resolve_path(config.TEMPLATES_DIR)
    path = config.resolve_path(base / name)
    if not config.is_within(path, base) or not path.is_file():
        raise TreeError("templateNotFound", name=name)
    return path


def _template_trash_dir() -> "Path":
    """本次软删除的回收站目录：`templates/.trash/<YYYYMMDD-HHMMSS>/`。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return config.resolve_path(config.TEMPLATES_DIR) / config.TEMPLATE_TRASH_DIRNAME / stamp


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
    """
    path = _template_path_or_raise(name)

    raw_new = payload.get("name")
    new_name = raw_new.strip() if isinstance(raw_new, str) else ""
    if not new_name:
        raise TreeError("templateNameEmpty")
    stem = new_name[:-5] if new_name.lower().endswith(".json") else new_name
    stem = stem.strip()
    if not stem:
        raise TreeError("templateNameEmpty")
    if len(stem) > config.TEMPLATE_NAME_MAX:
        raise TreeError("templateNameTooLong", name=new_name)
    new_filename = stem + ".json"
    if not TEMPLATE_NAME.match(new_filename):
        raise TreeError("templateNameInvalid", name=new_name)
    if new_filename == name:
        return {"ok": True, "file": name, "name": path.stem, "unchanged": True}

    base = config.resolve_path(config.TEMPLATES_DIR)
    new_path = config.resolve_path(base / new_filename)
    if not config.is_within(new_path, base):
        raise TreeError("templateNameInvalid", name=new_name)
    if new_path.exists():
        raise TreeError("templateExists", name=new_name)

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise TreeError("templateBadJson", name=name)
    if not isinstance(doc, dict):
        raise TreeError("templateBadJson", name=name)
    doc["name"] = stem

    body = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    try:
        tmp = new_path.with_name(new_path.name + ".tmp")
        # 显式 newline="\n"：跨平台字节一致（§编码基线）
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, new_path)        # 先落新文件（原子）
        trash = _template_trash_dir()
        trash.mkdir(parents=True, exist_ok=True)
        os.replace(path, trash / name)   # 旧文件移入回收站保底，不真删
    except OSError:
        raise TreeError("templateRenameFailed", name=name)

    return {
        "ok": True,
        "file": new_filename,
        "name": stem,
        "path": str(new_path),
        "bytes": len(body.encode("utf-8")),
    }


def _write_lnk(path: Path, target: str, workdir: str, icon: str = "") -> None:
    """用 PowerShell WScript.Shell 写一个 Windows 快捷方式（.lnk）。

    `icon` 为空时不设 IconLocation（快捷方式沿用 .bat 的默认控制台图标）；
    给定时形如 `C:\\path\\qm-launch.ico,0` —— 皮肤联动图标（V0.0.15）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    script = _lnk_script(path, target, workdir, icon)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise OSError(result.stderr or "PowerShell CreateShortcut failed")


def _lnk_script(path: Path, target: str, workdir: str, icon: str = "") -> str:
    """_write_lnk 的纯函数体：只拼 PowerShell 语句，不做任何 I/O（便于单测）。

    路径统一经 `_ps_quote` 处理：反斜杠转正斜杠（Windows API 完全接受）、
    单引号翻倍 —— 绝不依赖 Python repr，否则反斜杠会被 repr 加倍成 `\\\\`，
    而 PowerShell 单引号里反斜杠是字面量，会把 `D:\\\\Data` 这类错路径写进 .lnk。
    """
    lines = [
        "$ws = New-Object -ComObject WScript.Shell; ",
        f"$sc = $ws.CreateShortcut({_ps_quote(str(path))}); ",
        f"$sc.TargetPath = {_ps_quote(target)}; ",
        f"$sc.WorkingDirectory = {_ps_quote(workdir)}; ",
    ]
    if icon:
        lines.append(f"$sc.IconLocation = {_ps_quote(icon)}; ")
    lines.append("$sc.Save()")
    return "".join(lines)


def _ps_quote(value: str) -> str:
    """把字符串包成 PowerShell 单引号字面量：反斜杠→正斜杠，单引号→两个单引号。

    PowerShell 单引号字符串只有单引号是转义（`''`），反斜杠是普通字符；
    Windows 各 API 均接受正斜杠路径，故统一转正斜杠，避免 repr 的反斜杠加倍问题。
    """
    return "'" + value.replace("\\", "/").replace("'", "''") + "'"


def validate_ico(data: bytes) -> None:
    """校验 ICO 二进制结构（V0.0.15）：只认 PNG-in-ICO，防任意文件挂名上传。

    检查项：魔数（6 字节头，保留字 0）、目录项数量 ≥ 1 且 ≤ 16、
    每个目录项的尺寸字段合法（宽高 0(=256)/16/32/48/64/128/256、色彩数 0）、
    图像数据偏移与长度落在文件范围内、每帧数据是完整 PNG。
    校验不过即抛 iconInvalid。
    """
    def fail() -> "TreeError":
        return TreeError("iconInvalid")

    if len(data) > config.MAX_ICON_BYTES:
        raise TreeError("iconTooLarge", limit=config.MAX_ICON_BYTES, actual=len(data))
    if len(data) < 6:
        raise fail()
    reserved, typ, count = struct.unpack("<HHH", data[:6])
    if reserved != 0 or typ != 1 or not (1 <= count <= 16):
        raise fail()
    pos = 6
    frames = []
    for _ in range(count):
        if pos + 16 > len(data):
            raise fail()
        (w, h, colors, _res, planes, bpp,
         size, offset) = struct.unpack("<BBBBHHII", data[pos:pos + 16])
        pos += 16
        if colors not in (0, 2, 16, 256):
            raise fail()
        if planes != 1 or bpp not in (0, 8, 24, 32):
            raise fail()
        if offset + size > len(data):
            raise fail()
        frames.append((w, h, size, offset))
    if not frames:
        raise fail()
    for w, h, size, offset in frames:
        blob = data[offset:offset + size]
        # PNG 签名 89 50 4E 47 0D 0A 1A 0A + IEND 块（12 字节收尾）
        if not blob.startswith(b"\x89PNG\r\n\x1a\n") or not blob.endswith(b"IEND\xaeB`\x82"):
            raise fail()


def save_launch_icon(payload: Dict[str, Any]) -> Dict[str, Any]:
    """保存皮肤联动启动图标（V0.0.15）：base64 ICO → 原子写 `data/qm-launch.ico`。

    图标由前端按当前皮肤配色用 canvas 绘制 —— 色值与皮肤的单一事实源
    都在前端 CSS 变量里，后端不镜像调色板。后端只做三件事：
    结构校验（validate_ico）、体积上限、原子落盘。
    落盘后**不主动改桌面**：`refresh` 由 create_shortcut 的正常流程做，
    换肤时前端重传同一文件，桌面 .lnk 的 IconLocation 不变、内容已更新。
    """
    raw = payload.get("data")
    if not isinstance(raw, str) or not raw.strip():
        raise TreeError("iconDataMissing")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise TreeError("iconInvalid")

    validate_ico(data)

    path = config.ICON_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)   # 原子替换，避免中断留下半截文件
    except OSError:
        raise TreeError("iconWriteFailed")

    return {"ok": True, "path": str(path), "bytes": len(data)}


def _refresh_icon_cache() -> None:
    """通知 Explorer 图标缓存已失效（SHChangeNotify，尽力而为）。

    Windows 的图标缓存很固执：只替换 .ico 文件常被忽略。广播
    SHCNE_ASSOCCHANGED 让 Explorer 重读关联图标。失败不抛错 ——
    缓存刷新是尽力而为，不构成功能的成败判据。
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        shell32 = ctypes.windll.shell32
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except (OSError, AttributeError, ValueError):
        pass


def create_shortcut(payload: Dict[str, Any]) -> Dict[str, Any]:
    """在桌面生成启动快捷方式；若桌面不可写，降级为返回 .lnk 字节（base64）供下载。

    皮肤联动图标（V0.0.15）：请求带 `icon`（base64 ICO，前端按当前皮肤绘制）时
    先落盘 `data/qm-launch.ico` 再写 .lnk 的 IconLocation 指向它；不带则沿用
    默认图标 —— 下载降级路径**刻意不主题化**（.lnk 指向的绝对路径在用户机器上
    不存在，主题化只会换来一个裂开的图标）。
    """
    target = str(config.START_BAT)
    if not config.START_BAT.is_file():
        raise TreeError("shortcutTargetMissing", target=target)

    icon_ref = ""
    raw_icon = payload.get("icon")
    if isinstance(raw_icon, str) and raw_icon.strip():
        save_launch_icon({"data": raw_icon})
        icon_ref = f"{config.ICON_FILE},0"

    workdir = str(config.PROJECT_DIR)
    name = f"{config.APP_NAME_ZH} {config.APP_NAME_EN}.lnk"
    desktop = Path.home() / "Desktop"
    lnk = desktop / name

    try:
        _write_lnk(lnk, target, workdir, icon_ref)
        if icon_ref:
            _refresh_icon_cache()
        return {"ok": True, "path": str(lnk), "icon": bool(icon_ref)}
    except OSError:
        # 桌面写入失败时，在临时目录生成同一份 .lnk 并返回 base64
        tmp = Path(tempfile.gettempdir()) / name
        try:
            _write_lnk(tmp, target, workdir)   # 降级路径不设图标（见 docstring）
            data = base64.b64encode(tmp.read_bytes()).decode("ascii")
            return {"ok": True, "fallback": True, "name": name, "data": data}
        except OSError as exc:
            raise TreeError("shortcutFailed", message=str(exc)) from exc
