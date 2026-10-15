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
_TPL_STEM_PATTERN = r"[A-Za-z0-9_\u4e00-\u9fff-]+"
TEMPLATE_NAME = re.compile(r"^" + _TPL_STEM_PATTERN + r"\.json$")
TEMPLATE_FILE = re.compile(r"^" + _TPL_STEM_PATTERN + r"\.(?:json|md)$")
# 可被「剥离」的模板扩展名（另存 / 改名时用户顺手带上 `.json` / `.md` 不报错）。
_TEMPLATE_EXTS = (".json", ".md")

# PowerShell 子进程超时（秒）。CreateShortcut 正常毫秒级返回；设上限是为防「PowerShell
# 挂起 → 请求线程被**永久占用**」（A-P3-1：ThreadingHTTPServer 线程数无上限，挂起的线程
# 会一直堆积）。超时由 subprocess 终止子进程，再转成 OSError 交上层降级。
_PS_TIMEOUT_SEC = 30


def _tmp_sibling(path: Path) -> Path:
    """返回与 `path` **同目录**、**唯一命名**的临时文件路径（原子写用）。

    固定名 `<name>.tmp` 会让两个并发写**互相覆盖临时文件**、再各自 `os.replace` 抢结果
    （A-P3-2）。唯一名（pid + 随机 token）消除该竞争；仍在同一目录 → `os.replace` 依旧是
    同盘原子替换（跨盘会退化为非原子复制，故**不可**用系统临时目录）。
    """
    token = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
    return path.with_name(f"{path.name}.{token}.tmp")


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
        return {"ok": True, "available": False, "items": [], "path": str(d),
                "reason": blocked}

    items: list[Dict[str, Any]] = []
    # 两个 glob 合并后统一排序（按小写名 + 原名，跨平台确定性；`.trash/` 是子目录，扫不到）。
    found = sorted(list(d.glob("*.json")) + list(d.glob("*.md")),
                   key=lambda q: (q.name.lower(), q.name))
    for p in found:
        if not TEMPLATE_FILE.match(p.name):
            continue
        try:
            doc = _read_template_doc(p, name=p.name)
        except (TreeError, OSError, ValueError):
            continue   # 单套损坏只跳过该套（含 `.md` 解析失败）
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


def export_template(name: str) -> Dict[str, Any]:
    """读取模板**原文件文本**（`GET /api/templates-export/<name>`，V0.0.38 · 6E）。

    导出＝把盘上那份文件**原样**交回，**不做任何再序列化** —— 「导出 → 再导入」因此
    与原件内容一致（单一真源；若前端另写一套 `.md` 渲染器，两侧迟早漂移）。
    前端据 `file` 的扩展名决定下载文件名（`.json` 进 `.json` 出、`.md` 进 `.md` 出）。

    路径校验与读取共用 `_template_path_or_raise`（白名单 + `is_within` + 必须是文件）；
    读失败由上层转 `ioError`（`OSError`），不新增错误码。
    """
    path = _template_path_or_raise(name)
    return {
        "ok": True,
        "file": name,
        "name": path.stem,
        "source": _template_source(name),
        "text": path.read_text(encoding="utf-8"),
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


def _ask_directory() -> "str | None":
    """弹原生目录选择框，返回所选**绝对路径**；用户取消 → `None`。

    不能用（`import tkinter` 失败 / 无显示 / `Tk()` 抛错）一律抛 `_PickUnavailable`，
    由 `pick_templates_dir` 转成 `available=false` 的**降级响应**（前端改用手动粘贴路径）。

    在请求线程内调用是安全的：`ThreadingHTTPServer` 每请求一线程，模态框只阻塞**本线程**，
    服务照常响应其他请求。`withdraw()` + `-topmost` 让对话框置顶、且不闪出一个空主窗。
    """
    try:
        import tkinter
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001 - ImportError / 无 Tcl 运行时
        raise _PickUnavailable(str(exc) or "tkinter unavailable") from exc

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


def pick_templates_dir() -> Dict[str, Any]:
    """`POST /api/templates-dir/pick`：弹原生目录选择框，**只回报用户所选路径**。

    刻意**不落盘、不校验、不绑定** —— 「选择」与「绑定」是两个独立动作：用户在框里挑错
    目录不会立刻改写 settings；是否绑定由前端确认后另发 `PUT /api/templates-dir`。
    响应恒为 `ok=true`（「原生框用不了」是**能力缺失**，不是请求失败）：

      * `available=false, reason="disabled"`    —— env `QM_NO_GUI_PICK` 关断；
      * `available=false, reason="unavailable"` —— `tkinter` / GUI 会话缺失（带 `message`）；
      * `available=true, cancelled=true`        —— 用户取消（`dir` 为空）；
      * `available=true, cancelled=false`       —— 选中路径（`dir` 为绝对路径）。
    """
    if _env_truthy(NO_GUI_PICK_ENV):
        return {"ok": True, "available": False, "reason": "disabled", "dir": ""}
    try:
        chosen = _ask_directory()
    except _PickUnavailable as exc:
        return {"ok": True, "available": False, "reason": "unavailable",
                "message": str(exc), "dir": ""}
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
    writable, why = _probe_writable(d)
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
