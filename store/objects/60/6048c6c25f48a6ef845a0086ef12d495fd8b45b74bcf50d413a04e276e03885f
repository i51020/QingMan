"""青蔓 QingMan · 业务路由。

每个函数只负责「收数据 → 交给核心逻辑 → 返回可序列化 dict」，
不碰 HTTP 细节，便于后续 CLI / 测试直接调用。

**模块边界（V0.0.54 起）**：模板子系统整体迁至 `server/templates.py`（CRUD + 目录绑定判据），
原子写用的唯一临时名迁至 `server/common.py`。本文件保留**端点与请求/响应形状**，
并从两者**显式导入**被搬走的名字 —— 这样 `app.py` 的 `routes.<名字>` 调用面不变，
`mock.patch.object(routes, 名字)` 也仍然指向同一个函数对象。

**为什么拆**：本文件曾达 62,374 B / 单文件上限 65,536 B（余 4.8%），再加服务端功能必撞线。
历史上 `backups.py` / `modules/templates.js` / `modules/selection.js` 三次同因拆分，
结论一致 —— **拆模块，不是放宽阈值**。
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from server import config, dtree_core
from server.dtree_core import TreeError

# 模板子系统自 `routes.py` 迁出（V0.0.54 —— 理由与搬迁纪律见 `templates.py` 头部）。
# **显式 import**（不用 `import *`）：① 谁被搬走了，在这里一眼可数；
# ② `mock.patch.object(routes, name)` 仍指向同一个函数对象，打桩继续有效。
# ③ 共同助手 `_tmp_sibling` 单独进 `common.py` —— 否则本模块与 `templates` 会互相 import。
from server.common import _tmp_sibling
from server.templates import (  # noqa: F401  （端点经 app.py 调 routes.<名字>，此处为再导出）
    _template_trash_dir,
    _templates_dir_blocked,
    _templates_dir_reason,
    delete_template,
    export_template,
    import_template,
    list_templates,
    load_template,
    rename_template,
    save_template,
)

GENERATE_PATH = "/api/generate"
HEALTH_PATH = "/api/health"
EDITOR_PATH = "/api/editor"
SHORTCUT_PATH = "/api/shortcut"
TEMPLATES_PATH = "/api/templates"
# 用户模板库的「绑定目录」端点（V0.0.35）：GET 读取当前绑定，PUT 设定（写操作）。
TEMPLATES_DIR_PATH = "/api/templates-dir"
# 模板导入端点（V0.0.36 · 6C）：POST 上传 `.json` / `.md` 内容 → 归一 → 落盘。
TEMPLATES_IMPORT_PATH = "/api/templates/import"
# 模板导出端点（V0.0.38 · 6E）：GET 原文件文本，与导入成环（`.json` 进 `.json` 出）。
# **独立前缀**（`templates-export` ≠ `templates/`）—— 刻意避开 `/api/templates/` 的前缀
# 路由，免得重演「集合路由吞掉具体路由」那种顺序坑（见《错误笔记》前缀匹配一条）。
TEMPLATES_EXPORT_PATH = "/api/templates-export"
# 原生目录选择框（V0.0.38 · 6E）：POST 弹 `tkinter.filedialog.askdirectory`，只回报所选路径
# （**不落盘、不绑定** —— 绑定另发 `PUT /api/templates-dir`）。
TEMPLATES_DIR_PICK_PATH = "/api/templates-dir/pick"
# 关断原生目录框的 env：无头 / 自动化环境（CI、沙盒、`browser_smoke`）必须能关断，
# 否则模态框会**阻塞请求线程直到有人去点它**。
NO_GUI_PICK_ENV = "QM_NO_GUI_PICK"
# 「打开目录」端点（V0.0.51@r7 · 服务设置）：请求 OS 打开青蔓自己的目录。
# 只接受**枚举标识**（project / data / templates），不接任意路径 —— 见 open_directory。
OPEN_DIR_PATH = "/api/open-dir"
# 关断用的 env：无头 / 自动化环境（CI、沙盒、`browser_smoke`）必须能关断 ——
# 否则会真的弹出资源管理器窗口（不阻塞请求，但会污染测试机桌面、干扰后续用例）。
NO_GUI_OPEN_ENV = "QM_NO_GUI_OPEN"
# 皮肤联动的桌面图标上传（V0.0.15）：前端 canvas 绘制、后端只落盘与接线
ICON_PATH = "/api/launch-icon"
# 「跟随系统」要跟的是 **操作系统语言**，不是浏览器语言（V0.0.14）。
# 浏览器语言可被单独改写（装浏览器时选了英文、或用户手动调过），
# 与「系统显示语言」不是一回事 —— 故由后端取真值，再经本端点同步注入前端。
ENV_PATH = "/api/env.js"
# 可用语言清单（V0.0.44 · 动态语言包）：与 env.js 同样**同步注入** —— 语言选择器必须
# 在首屏就列全，否则会先只显示内置语言、拿到清单后再补出扩展语言（菜单跳变）。
LOCALES_PATH = "/api/locales.js"

# 编辑态文档结构版本；结构不兼容变更时递增（见 src/shared/schema.json）
EDITOR_SCHEMA_VERSION = 1

# 模板文件名白名单：单段（**不含路径分隔符**，从源头堵死路径穿越 `..` / 子目录），
# 「中英文、数字、下划线、连字符」+ 扩展名。**两个正则分工明确**（V0.0.36 · 6C）：
#   · `TEMPLATE_NAME` 只认 `.json` —— **新建 / 另存 / 改名目标**恒为 `.json`（规范化格式）；
#   · `TEMPLATE_FILE` 另认 `.md` —— **列表 / 读取 / 删除 / 导入**支持双格式（§P2 第 7 项）。
# 分开而非合并的原因：`save_template` 产出的永远是**规范 `.json`**，若白名单一并放开，
# 就会允许「另存为 `X.md`」，与「`.md` 是 AI/Agent 交换格式、由导入/导出产生」的设计相悖。

# PowerShell 子进程超时（秒）。CreateShortcut 正常毫秒级返回；设上限是为防「PowerShell
# 挂起 → 请求线程被**永久占用**」（A-P3-1：ThreadingHTTPServer 线程数无上限，挂起的线程
# 会一直堆积）。超时由 subprocess 终止子进程，再转成 OSError 交上层降级。
_PS_TIMEOUT_SEC = 30




def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "app": config.APP_NAME_EN,
        "nameZh": config.APP_NAME_ZH,
        "version": config.read_version(),
        # 数据目录（V0.0.51@r7 · 服务设置）：编辑草稿与备份所在处。出问题时
        # 用户要知道去哪找 —— 由后端算（前端无从推断本机磁盘路径）。
        "dataDir": str(config.resolve_path(config.DATA_DIR)),
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


# 语言包契约的两个导出（V0.0.44）：`LOCALE` 须与文件名一致；`NAME` 为母语自描述名。
# **只读文本 + 正则**，不执行语言包代码 —— 在服务端 import 前端 ES Module 既无必要也不安全。
_LOCALE_NAME_RE = re.compile(r"export\s+const\s+NAME\s*=\s*['\"]([^'\"]+)['\"]")
_LOCALE_FILE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\.js$")


def list_locales() -> List[Dict[str, str]]:
    """扫描语言包目录，返回 `[{"code", "name"}]`（按文件名排序，顺序稳定）。

    语言标签取自**文件名**（契约要求文件内 `LOCALE` 与之一致，由 verify 静态把关）；
    `NAME` 取不到时回落到文件名 —— 宁可名字难看，也不让这门语言从清单里凭空消失。
    目录不存在或为空返回空列表，前端据此降级为「仅内置语言」。
    """
    out: List[Dict[str, str]] = []
    try:
        entries = sorted(config.LOCALES_DIR.iterdir(), key=lambda p: p.name)
    except OSError:
        return out
    for path in entries:
        if not path.is_file() or not _LOCALE_FILE_RE.match(path.name):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hit = _LOCALE_NAME_RE.search(text)
        code = path.name[:-3]
        out.append({"code": code, "name": (hit.group(1).strip() if hit else "") or code})
    return out


def locales_script() -> str:
    """可用语言清单的**同步**注入脚本（响应 `GET /api/locales.js`）。

    与 `env_script` 同理：清单必须早于 module 脚本就位，语言选择器才能一次列全。
    值经 `json.dumps` 转义（`ensure_ascii=False` 保留母语名），杜绝注入面。
    """
    return "window.__QM_LOCALES__ = " + json.dumps(list_locales(), ensure_ascii=False) + ";\n"


def generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    tree = payload.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("treeMissing")

    root = payload.get("root")
    root = root.strip() if isinstance(root, str) else ""

    # 落盘安全边界（§P0-1 R1–R5）：规范化 + 黑名单校验，全在服务端完成。
    # 命中即抛 TreeError（明确的 4xx 错误码），绝不进入写盘流程。
    # `allow_drive_root=bool(root)`：根名非空时真实写入点是 `盘根/根名`，
    # 盘根本身作为「父目录」是合法的（2026-10-26：用户要在 E 盘生成项目被误拦）。
    base = dtree_core.check_target(payload.get("target"), allow_drive_root=bool(root))

    if root:
        ok, reason = dtree_core.validate_segment(root)
        if not ok:
            raise TreeError(
                "segmentInvalid", name=root, reason=dtree_core.message(reason, name=root)
            )
        base = base / root

    # dryRun 按**严格布尔**判定（A-P3-6）：`bool("false")` 为 True —— 若前端误传字符串
    # `"false"`，旧写法会把「真写盘」当成演练（或反之）。前端恒传 JSON 布尔，故
    # `is True` 既堵住字符串真值、又不改变既有行为。
    dry_run = payload.get("dryRun") is True
    result = dtree_core.build_tree(tree, base, dry_run=dry_run)
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
    except (OSError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError 属 ValueError，**不是** OSError：用户用别的编码编辑过
        # editor.json 时会抛它，只捕 OSError 会漏 → 冒泡到 do_GET 裸崩（A-P2-1）。
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


# 备份文件名里的时间戳：定宽、可排序、无冒号（跨平台安全）。
# 带**微秒**（`%f`）：名字全局单调 → 裁剪用「名字序 = 时间序」才成立。
# ⚠ 只到秒是不够的：同一秒内的多份备份靠后缀区分，而一旦某份被裁掉、其名字被
# **后一次保存重新占用**，新文件就排到了后缀文件的**前面**，会被当成最旧立刻裁掉
# —— 实测发生过「最新一份刚写就被删」。微秒级下名字不会复用，问题从根上消失。
_EDITOR_BACKUP_STAMP = "%Y%m%d-%H%M%S-%f"
_EDITOR_BACKUP_GLOB = "editor-*.json"
# 回收站子目录名用秒级戳即可（同秒内多次轮转共用一个目录，避免碎目录）
_EDITOR_BACKUP_TRASH_STAMP = "%Y%m%d-%H%M%S"


def _prune_editor_backups(bak_dir: Path) -> int:
    """把超出上限的旧备份**移入** `data/.bak/.trash/<时间戳>/`，返回迁移份数。

    **软删除，不真删** —— 项目总原则「只复制不删除」是全项目硬不变量
    （`verify.py` 7q 守卫禁止 `routes.py` 出现 `unlink`/`remove`），
    与 `templates/.trash/` 同一体例，误清可人工找回。

    `editor-<17 位定宽时间戳>.json` ⇒ **名字序即时间序**，无需解析时间戳。
    同微秒冲突的后缀用 `_NNN`（`_`(0x5F) > `.`(0x2E)，排在无后缀之后，与创建序一致）；
    补零到 3 位以免 `_2 > _10` 的字典序陷阱。**不可**改用 `-NNN`：`-`(0x2D) < `.`，
    会让后缀文件排到无后缀之前，淘汰的就是最新那份。
    """
    keep = max(config.EDITOR_BACKUP_KEEP, 1)
    files = sorted(bak_dir.glob(_EDITOR_BACKUP_GLOB))   # 非递归：.trash/ 内的不会被扫到
    excess = files[:-keep] if len(files) > keep else []
    if not excess:
        return 0

    trash = (bak_dir / config.EDITOR_BACKUP_TRASH_DIRNAME
             / datetime.now().strftime(_EDITOR_BACKUP_TRASH_STAMP))
    moved = 0
    for old in excess:
        try:
            trash.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(trash / old.name))
            moved += 1
        except OSError:
            pass
    return moved


def _backup_editor(path: Path) -> Dict[str, Any]:
    """把**当前**（即将被覆盖的那一版）编辑态文档轮转为一份带时间戳的备份。

    **绝不抛出**：备份是增强，不得因它失败而阻断保存（主契约是「存得下」）。
    返回 `{"ok": bool, "file": str | None, "pruned": int}`；`file=None` 表示此前无文档可备。
    """
    if not path.is_file():
        return {"ok": True, "file": None, "pruned": 0}

    bak_dir = config.EDITOR_BACKUP_DIR
    try:
        bak_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime(_EDITOR_BACKUP_STAMP)
        target = bak_dir / f"editor-{stamp}.json"
        seq = 2
        while target.exists():      # 同微秒（时钟精度不足时）兜底，不互相覆盖
            target = bak_dir / f"editor-{stamp}_{seq:03d}.json"
            seq += 1
        shutil.copy2(path, target)
    except OSError as exc:
        return {"ok": False, "file": None, "pruned": 0, "reason": str(exc)}

    return {"ok": True, "file": target.name, "pruned": _prune_editor_backups(bak_dir)}


def save_editor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """校验并**原子写入**编辑态文档。非法内容一律拒写。

    落盘前先把**上一版**轮转进 `data/.bak/`（保留最近 `EDITOR_BACKUP_KEEP` 份）——
    原子替换会覆盖上一版，而「合法但错误」的覆盖是 `load_editor` 的损坏保护挡不住的。
    """
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
    # 顺序不可颠倒：必须**先备份上一版、再替换**；颠倒则备份到的已是新内容
    backup = _backup_editor(path)
    tmp = _tmp_sibling(path)   # A-P3-2：唯一临时名，避免并发写互相覆盖
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
        "backup": backup,
    }






def _probe_writable(path: Path, create: bool = True) -> "tuple[bool, str]":
    """探测目录可写：`mkdir` + 真写一个临时文件（`TemporaryFile` 关闭即自清）。

    只看 `os.access` 在 Windows 上并不准 —— 真写一次才算数。探针文件交由 `tempfile`
    自行回收：调用方**不**直呼删除 API（项目总原则「只复制不删除」，`verify.py` 7q
    守卫禁止 `routes.py` 出现真删除调用）。`create=False` 时只探测已存在的目录
    （GET 是只读操作，不该顺手建目录）。返回 (可写, 原因)。
    """
    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return False, "无法创建目录：%s" % exc
    if not path.is_dir():
        return False, "目录不存在"
    try:
        with tempfile.TemporaryFile(dir=str(path)):
            pass
    except OSError as exc:
        return False, "目录不可写：%s" % exc
    return True, ""


class _PickUnavailable(Exception):
    """原生目录选择框不可用（`tkinter` 缺失 / 无 GUI 会话 / Tcl 初始化失败）。"""


class _OpenUnavailable(Exception):
    """系统无法打开目录（无桌面会话 / 无可用打开方式 / `os.startfile` 失败）。"""


def _env_truthy(name: str) -> bool:
    """该 env 是否设为真值（`1` / `true` / `yes` / `on`，大小写不敏感、忽略首尾空白）。"""
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _ask_directory_win32() -> "str | None":
    """Windows 原生目录框：`ctypes` 直连 `shell32.SHBrowseForFolderW`（V0.3.7）。

    **为什么不再首选 tkinter**（实测，非推断）：本机 managed CPython 3.13.12 上
    `import tkinter` 直接 `ModuleNotFoundError` —— 官方 Windows 安装包默认带 Tcl/Tk，
    但**精简 / 嵌入式 / 部分 conda 发行版不带**。此前实现把「缺 tkinter」当成
    「本机没有 GUI」，于是「选择…」在这些环境下 100% 降级，用户只得到一句
    「系统选择框打不开」，既不能自愈也无从判断原因。

    `ctypes` 是标准库，`SHBrowseForFolderW` 是系统 DLL，**两者都不需要额外组件**，
    但同样能拿到**绝对路径** —— 这正是浏览器侧 `showDirectoryPicker()` 给不了的
    （它只返回 opaque 句柄，无法交给后端绑定目录，故不能作为替代方案）。

    `-new dialog style` 带来地址栏、「新建文件夹」与路径输入框（`BIF_EDITBOX`），
    体验与 tkinter 版基本对齐。返回 `None` 表示用户取消；不可用抛 `_PickUnavailable`。
    """
    if not _has_interactive_desktop():
        # 无交互桌面（服务被跑在 session 0 / 计划任务里）：模态框永远不会出现，
        # 调用会一直阻塞到线程被杀。此处**先判后退**，绝不把它当"能弹"来试。
        raise _PickUnavailable("no interactive desktop")

    import ctypes
    from ctypes import wintypes as wt

    BIF_RETURNONLYFSDIRS = 0x0001   # 只收文件系统目录（排除「网上邻居」等虚拟节点）
    BIF_EDITBOX = 0x0010            # 允许直接输入/粘贴路径
    BIF_NEWDIALOGSTYLE = 0x0040     # 新式对话框：地址栏 + 新建文件夹 + 可调整大小
    COINIT_APARTMENTTHREADED = 0x2
    DESKTOP_READOBJECTS = 0x0001
    MAX_PATH_BUF = 260

    class BROWSEINFOW(ctypes.Structure):
        # `pszDisplayName` / `lpszTitle` 声明成 `c_void_p`：ctypes 对 `LPWSTR` 字段做
        # 类型校验，传 `c_wchar_Array` 会 `TypeError`（实测踩过），而 cast 成 void* 等价。
        _fields_ = [
            ("hwndOwner", wt.HWND),
            ("pidlRoot", ctypes.c_void_p),
            ("pszDisplayName", ctypes.c_void_p),
            ("lpszTitle", ctypes.c_void_p),
            ("ulFlags", wt.UINT),
            ("lpfn", ctypes.c_void_p),
            ("lParam", wt.LPARAM),
            ("iImage", ctypes.c_int),
        ]

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        # 64 位下句柄若走默认 `c_int` 会被截断 —— 显式声明 restype 是在 Windows 上
        # 「偶发把窗口放到别的 owner 上」这类玄学问题的根因，必须写死。
        user32.GetForegroundWindow.restype = wt.HWND
        shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
        shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
        shell32.SHGetPathFromIDListW.restype = wt.BOOL
        shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p,
                                                 ctypes.POINTER(ctypes.c_wchar)]
    except Exception as exc:  # noqa: BLE001 - 非 Windows / DLL 缺失
        raise _PickUnavailable(str(exc) or "shell32 unavailable") from exc

    hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    # S_OK(0) / S_FALSE(1) 都算成功，且都需配对 CoUninitialize（MSDN 约定）
    com_ok = (hr & 0xFFFFFFFF) in (0, 1)

    buf = ctypes.create_unicode_buffer(MAX_PATH_BUF)
    info = BROWSEINFOW()
    # 以当前前台窗口为 owner：对话框会随该窗口一同置顶，不会被浏览器窗口压到后面
    # （`tkinter` 版用 `-topmost` 达到同一目的；这里没有自己的窗口可用，故借前台窗口）。
    try:
        info.hwndOwner = user32.GetForegroundWindow()
    except Exception:  # noqa: BLE001
        info.hwndOwner = None
    info.pszDisplayName = ctypes.cast(buf, ctypes.c_void_p)
    info.lpszTitle = ctypes.cast(ctypes.c_wchar_p("选择模板目录"), ctypes.c_void_p)
    info.ulFlags = BIF_RETURNONLYFSDIRS | BIF_EDITBOX | BIF_NEWDIALOGSTYLE

    pidl = None
    try:
        pidl = shell32.SHBrowseForFolderW(ctypes.byref(info))
        if not pidl:
            return None      # 用户取消 / 关窗：不是错误
        path_buf = ctypes.create_unicode_buffer(MAX_PATH_BUF)
        ok = shell32.SHGetPathFromIDListW(pidl, path_buf)
        return path_buf.value if ok else None
    except Exception as exc:  # noqa: BLE001 - 访问冲突 / 调用失败
        raise _PickUnavailable(str(exc) or "cannot open directory dialog") from exc
    finally:
        if pidl:
            try:
                ole32.CoTaskMemFree(ctypes.c_void_p(pidl))
            except Exception:  # noqa: BLE001
                pass
        if com_ok:
            try:
                ole32.CoUninitialize()
            except Exception:  # noqa: BLE001
                pass


def _has_interactive_desktop() -> bool:
    """当前进程能否拿到**交互式桌面**（Windows）。

    用途只有一个：在弹模态框**之前**判断「弹出来有没有意义」。服务若跑在 session 0
    （Windows 服务 / 计划任务 / 部分 CI），`SHBrowseForFolderW` 不会返回、也不会报错，
    而是静默阻塞 —— 请求线程连同前端那次点击一起卡死，比直接降级糟得多。
    """
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.OpenInputDesktop.restype = ctypes.c_void_p
        user32.CloseDesktop.argtypes = [ctypes.c_void_p]
        desk = user32.OpenInputDesktop(0, False, 0x0001)   # DESKTOP_READOBJECTS
        if not desk:
            return False
        user32.CloseDesktop(desk)
        return True
    except Exception:  # noqa: BLE001 - 非 Windows / 调用失败一律按「无桌面」
        return False


def _ask_directory_tk() -> "str | None":
    """原生目录框的 tkinter 实现（非 Windows 平台的主通道，Windows 的后备）。

    在请求线程内调用是安全的：`ThreadingHTTPServer` 每请求一线程，模态框只阻塞**本线程**，
    服务照常响应其他请求。`withdraw()` + `-topmost` 让对话框置顶、且不闪出一个空主窗。
    """
    try:
        import tkinter
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001 - ImportError / 无 Tcl 运行时
        raise _PickUnavailable("tkinter 不可用：%s" % (str(exc) or "import failed")) from exc

    root = None
    try:
        root = tkinter.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:  # noqa: BLE001 - 个别 Tk 版本无该属性，非致命
            pass
        chosen = filedialog.askdirectory(parent=root, mustexist=True)
    except Exception as exc:  # noqa: BLE001 - TclError（无显示）/ 其他 GUI 失败
        raise _PickUnavailable(str(exc) or "cannot open directory dialog") from exc
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:  # noqa: BLE001 - 已销毁 / 无显示
                pass
    return chosen or None


def _ask_directory() -> "str | None":
    """弹原生目录选择框，返回所选**绝对路径**；用户取消 → `None`。

    通道优先级（V0.3.7）：Windows 先走 `SHBrowseForFolderW`（零依赖），失败再退
    `tkinter`；其他平台直接用 `tkinter`。两条都不可用才抛 `_PickUnavailable`，
    由 `pick_templates_dir` 转成 `available=false` 的**降级响应**。
    """
    if os.name == "nt":
        try:
            return _ask_directory_win32()
        except _PickUnavailable as first:
            if "no interactive desktop" in str(first):
                raise            # 无桌面时 tkinter 同样弹不出来，再试只会白阻塞
            try:
                return _ask_directory_tk()
            except _PickUnavailable as second:
                raise _PickUnavailable(
                    "Win32: %s；tkinter: %s" % (first, second)) from second
    return _ask_directory_tk()



def pick_templates_dir() -> Dict[str, Any]:
    """`POST /api/templates-dir/pick`：弹原生目录选择框，**只回报用户所选路径**。

    刻意**不落盘、不校验、不绑定** —— 「选择」与「绑定」是两个独立动作：用户在框里挑错
    目录不会立刻改写 settings；是否绑定由前端确认后另发 `PUT /api/templates-dir`。
    响应恒为 `ok=true`（「原生框用不了」是**能力缺失**，不是请求失败）：

      * `available=false, reason="disabled"`    —— env `QM_NO_GUI_PICK` 关断；
      * `available=false, reason="unavailable"` —— 两条通道都不可用（带 `message`，
        例如 `no interactive desktop` / `tkinter 不可用：...`）；
      * `available=true, cancelled=true`        —— 用户取消（`dir` 为空）；
      * `available=true, cancelled=false`       —— 选中路径（`dir` 为绝对路径）。

    `message` 会被前端原样展示（截断后）—— V0.3.7 起不再吞掉原因：此前「缺 tkinter」
    与「无桌面」「被 env 关断」在界面上长得一模一样，用户无从判断该修什么。
    """
    if _env_truthy(NO_GUI_PICK_ENV):
        return {"ok": True, "available": False, "reason": "disabled", "dir": ""}
    try:
        chosen = _ask_directory()
    except _PickUnavailable as exc:
        # 原因截断：这是要给用户看的一句话，不是堆栈。
        detail = str(exc).strip().replace("\n", " ")
        if len(detail) > 160:
            detail = detail[:157] + "..."
        return {"ok": True, "available": False, "reason": "unavailable",
                "message": detail, "dir": ""}
    return {"ok": True, "available": True, "reason": "",
            "cancelled": chosen is None, "dir": chosen or ""}


def _open_path(path: Path) -> None:
    """请求操作系统打开 `path`（资源管理器 / 访达 / 文件管理器）。

    平台分支：Windows 用 `os.startfile`（ShellExecute，等同双击）；macOS 用 `open`；
    其余 POSIX 用 `xdg-open`。后两者用 `Popen` **刻意不等待** —— 文件管理器是常驻
    进程，等它退出会把本请求线程一直占住（`ThreadingHTTPServer` 线程数无上限，
    堆积即成隐患）；`os.startfile` 本身即异步返回，无需处理。

    失败（无桌面会话 / 无可用打开方式）一律抛 `_OpenUnavailable`，由
    `open_directory` 转成 `available=false` 的降级响应。
    """
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(path))  # noqa: S606 - 仅 Windows 提供；语义等同双击
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen(
                [opener, str(path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except Exception as exc:  # noqa: BLE001 - OSError / 无桌面会话 / 无该命令
        raise _OpenUnavailable(str(exc) or "cannot open directory") from exc


def open_directory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """`POST /api/open-dir`：请求操作系统打开青蔓自己的某个目录（V0.0.51@r7）。

    只接受**枚举标识**（`project` / `data` / `templates`）而非任意路径 —— 白名单是
    **查表**式的：标识不在表内即拒，全程**不存在**把调用方字符串拼进文件路径的环节，
    故路径穿越从结构上无从谈起（比「先拼路径再校验是否落在允许列表内」更省事、也更难写错）。

    响应形态对齐 `pick_templates_dir`：**能力缺失不是请求失败**，故恒 `ok=true`：

      * `available=false, reason="disabled"`    —— env `QM_NO_GUI_OPEN` 关断；
      * `available=false, reason="missing"`     —— 目标目录尚不存在（带 `dir`）；
      * `available=false, reason="unavailable"` —— 无桌面 / 无可用打开方式（带 `message`）；
      * `available=true, dir=<绝对路径>`        —— 已请求系统打开。

    标识非法属**客户端错误**（而非能力缺失），抛 `TreeError` → 400。
    """
    target = payload.get("target")
    targets = {
        "project": config.PROJECT_DIR,
        "data": config.DATA_DIR,
        "templates": config.templates_dir(),
    }
    if not isinstance(target, str) or target not in targets:
        raise TreeError("openDirBadTarget", target=str(target))

    d = config.resolve_path(targets[target])
    if _env_truthy(NO_GUI_OPEN_ENV):
        return {"ok": True, "available": False, "reason": "disabled", "dir": str(d)}
    if not d.is_dir():
        return {"ok": True, "available": False, "reason": "missing", "dir": str(d)}
    try:
        _open_path(d)
    except _OpenUnavailable as exc:
        return {"ok": True, "available": False, "reason": "unavailable",
                "message": str(exc), "dir": str(d)}
    return {"ok": True, "available": True, "reason": "", "dir": str(d)}


def get_templates_dir() -> Dict[str, Any]:
    """读取当前绑定的模板目录与元信息（`GET /api/templates-dir`）。**只读，不落盘**。"""
    d = config.resolve_path(config.templates_dir())
    reason = _templates_dir_reason(d)
    if reason:
        writable, why = False, reason
    elif d.is_dir():
        writable, why = _probe_writable(d, create=False)
    else:
        writable, why = False, "目录不存在（PUT 设定时会自动创建）"
    return {
        "ok": True,
        "dir": str(d),
        "source": config.templates_dir_source(),
        "valid": not reason,
        "reason": reason,
        "writable": writable,
        "writableReason": why,
        "exists": d.is_dir(),
        "builtinDir": str(config.DEFAULT_TEMPLATES_DIR),
        "packDir": str(config.TEMPLATES_PACK_DIR),
        "settingsFiles": [str(p) for p in config.settings_candidates()],
        "schemaVersion": config.SETTINGS_SCHEMA_VERSION,
    }


def _settings_write(**updates: Any) -> Path:
    """原子写 settings（保留既有字段，合并 `updates`）；返回实际写入路径。

    复用 A-P3-2 的唯一临时名 + `os.replace` 原子替换；显式 `newline="\n"` 保 LF
    （§编码基线：Windows 默认会把换行翻成 CRLF）。
    """
    path = config.settings_path()
    data = config.load_settings()
    data.update(updates)
    data.setdefault("schemaVersion", config.SETTINGS_SCHEMA_VERSION)
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = _tmp_sibling(path)
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, path)
    except OSError as exc:
        raise TreeError("templateDirNotWritable", dir=str(path.parent), message=str(exc))
    return path


def set_templates_dir(payload: Dict[str, Any]) -> Dict[str, Any]:
    """设定绑定目录（`PUT /api/templates-dir`，**写操作**）。

    校验链（任一步失败即抛错，**不产生半完成态**）：
      非空 → resolve → 拒自绑 / 系统区（`_templates_dir_blocked`）→ 实测可写 → 写 settings。

    `create`（V0.3.5，默认 `True`）：`True` 允许顺手建目录；`False` 要求目录已存在。
    前端两条通道（手输 / 原生框）都传 `False` —— 理由见该参数处的注释。

    `QM_TEMPLATES_DIR` env 的优先级**高于** settings —— 被 env 覆盖时 `effectiveDir`
    会与请求值不同，响应如实回报 `applied=false`，供前端提示「需先清除环境变量」。
    """
    raw = payload.get("dir")
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        raise TreeError("templateDirBlocked", dir="", reason="目录不能为空")
    d = config.resolve_path(text)
    reason = _templates_dir_blocked(d)
    if reason:
        raise TreeError("templateDirBlocked", dir=str(d), reason=reason)
    # V0.3.5：`create` 默认 True —— 保持既有语义（绑定时顺手把目录建出来）。
    # 前端手输通道显式传 `false`：输入框让「打错一个字」变成常见操作，而自动 mkdir
    # 会**凭空建出一个空目录**、模板列表随即清空，用户却只看到「已绑定」。
    # 走 `create=False` 时，不存在的路径直接报错，由调用方回退到原目录。
    # 只认真正的布尔 False（JSON 传 `"false"` 之类的畸形值仍按默认放行）。
    create = payload.get("create", True)
    writable, why = _probe_writable(d, create=(create is not False))
    if not writable:
        raise TreeError("templateDirNotWritable", dir=str(d), message=why)

    path = _settings_write(templatesDir=str(d))
    effective = config.resolve_path(config.templates_dir())
    applied = os.path.normcase(str(effective)) == os.path.normcase(str(d))
    return {
        "ok": True,
        "dir": str(d),
        "effectiveDir": str(effective),
        "applied": applied,
        "source": config.templates_dir_source(),
        "writable": True,
        "settingsPath": str(path),
    }


def _write_lnk(path: Path, target: str, workdir: str, icon: str = "") -> None:
    """用 PowerShell WScript.Shell 写一个 Windows 快捷方式（.lnk）。

    `icon` 为空时不设 IconLocation（快捷方式沿用 .bat 的默认控制台图标）；
    给定时形如 `C:\\path\\qm-launch.ico,0` —— 皮肤联动图标（V0.0.15）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    script = _lnk_script(path, target, workdir, icon)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, check=False, timeout=_PS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        # A-P3-1：超时后 subprocess 已终止子进程；转成 OSError 交由上层降级
        # （桌面写失败 → 返回 .lnk 字节供下载），而不是让请求线程一直挂着。
        raise OSError(f"PowerShell CreateShortcut timed out after {_PS_TIMEOUT_SEC}s")
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
    每个目录项的 colorCount ∈ {0, 2, 16, 256} 且 planes == 1 且 bpp ∈ {0, 8, 24, 32}、
    图像数据偏移与长度落在文件范围内、每帧数据是完整 PNG。校验不过即抛 iconInvalid。

    **宽高（w/h）只读取、不校验**（A-P2-3 订正）：ICO 目录项的宽高是**单字节**字段
    （0 表示 256），格式本身允许任意 1–255 尺寸 —— 写死 16/32/48/64/128/256 白名单
    反而会**误拦**合法图标（如 24×24 / 96×96）。真正决定「能否显示」的是可执行尺寸与
    颜色深度，交系统按需缩放。原文 docstring 曾承诺「宽高值域校验」，与实际行为不符，
    此处**如实订正**，不留名实不一处。
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
        tmp = _tmp_sibling(path)   # A-P3-2：唯一临时名，避免并发写互相覆盖
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
    # A-P3-4：用系统认定的桌面（处理 OneDrive 重定向），而非硬拼 home/Desktop
    desktop = config.desktop_dir()
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
