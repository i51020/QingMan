"""青蔓 QingMan · 全局配置常量。

本文件是唯一的路径与端口来源，其余模块一律从这里取值，不自行拼路径。
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME_ZH = "青蔓"
APP_NAME_EN = "QingMan"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    items = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return items or default


# 仅监听本机回环地址，不对外暴露
HOST = os.environ.get("QM_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT_START = _env_int("QM_PORT", 8765)
PORT_END = _env_int("QM_PORT_END", PORT_START + 10)

# 启动后是否自动打开浏览器（自动化测试可用 QM_OPEN_BROWSER=0 关闭）
OPEN_BROWSER = _env_flag("QM_OPEN_BROWSER", True)

# ---------- 调用来源校验（N1 · 本地服务防护） ----------

# 允许的调用来源主机名（Host 头的 host 部分 / Origin 的 host 部分）。
# 只允许回环地址：即使攻击者用域名做 DNS rebinding 把域名解析到 127.0.0.1，
# 浏览器发出的 Host 仍是攻击者域名，不在白名单内，请求即被拒。
ALLOWED_HOSTS = _env_list("QM_ALLOWED_HOSTS", ("127.0.0.1", "localhost", "::1"))

# 写操作防护头。跨站页面要携带自定义头必然先触发 CORS 预检，
# 而本服务不响应预检（do_OPTIONS 一律拒绝），故该头能阻断「跨站盲发 POST」。
# 同源请求携带自定义头不会触发预检，因此不影响正常使用。
GUARD_HEADER = "X-QingMan"
GUARD_HEADER_VALUE = "1"

PACKAGE_DIR = Path(__file__).resolve().parent   # src/server
SRC_DIR = PACKAGE_DIR.parent                    # src
PROJECT_DIR = SRC_DIR.parent                    # 项目根
WEB_DIR = SRC_DIR / "web"
SHARED_DIR = SRC_DIR / "shared"
VERSION_FILE = PROJECT_DIR / "VERSION"
START_BAT = PROJECT_DIR / "start.bat"

# ---------- 模板库（V0.0.11） ----------
#
# 模板库位于**项目根**而非 `src/`：它是内容资产、不是运行时代码，
# 也因此**不在版本交付清单内**（清单只覆盖 `src/**` + `start.bat` + `VERSION`）。
# 后果：预览副本（`preview/V<版本>/`）里没有 templates/ —— 后端必须优雅降级，
# 目录缺失时返回「不可用」而不是报错（见 routes.list_templates）。
TEMPLATES_DIR = PROJECT_DIR / "templates"

# 模板文件的格式版本。现有 17 套模板**顶层无版本字段**，一律视为 v1。
# 读取时容忍缺失（用 `doc.get("schemaVersion", 1)`）；自 V0.0.13 起「另存为模板」会写入该字段
# —— 一旦开始写模板就必须带上版本戳，否则日后无法区分新旧格式（§P2 第 7 项）。
TEMPLATE_SCHEMA_VERSION = 1

# 另存为模板时的上限：模板名 60 字符（留出 `.json` 与文件系统 255 字节余量）、
# 单文件 2 MB。二者都在服务端判定，前端提示不具约束力。
TEMPLATE_NAME_MAX = _env_int("QM_TEMPLATE_NAME_MAX", 60)
TEMPLATE_MAX_BYTES = _env_int("QM_TEMPLATE_MAX_BYTES", 2 * 1024 * 1024)

# 删除模板时的回收站目录名（V0.0.20）：软删除，落在 `templates/.trash/<时间戳>/` 下。
# 项目总原则「只复制不删除」—— 用户可能误删，移入回收站可人工找回。
# 该目录以 `.` 开头且**非递归**，`list_templates` 的 `glob("*.json")` 天然扫不到。
TEMPLATE_TRASH_DIRNAME = ".trash"

# ---------- 编辑态持久化（N2） ----------

# 编辑态文档落盘位置：项目根 data/editor.json。
# 选后端文件而非 localStorage：端口自 PORT_START 起扫描、并不固定，
# 而 localStorage 按 origin（含端口）隔离 —— 端口一变，草稿即静默丢失。
DATA_DIR = PROJECT_DIR / "data"
EDITOR_FILE = DATA_DIR / "editor.json"

# 编辑态文档体积与节点数上限（防异常大文档落盘）
MAX_EDITOR_BYTES = _env_int("QM_MAX_EDITOR_BYTES", 8 * 1024 * 1024)
MAX_EDITOR_NODES = _env_int("QM_MAX_EDITOR_NODES", 20000)

# 编辑态**轮转备份**（V0.0.26）
#
# `save_editor` 是「写 `.tmp` → `os.replace` 原子替换」，**替换即覆盖上一版**；
# `load_editor` 只在**文件损坏**时保护，防不住「合法但错误」的覆盖
# —— 用户一次误操作 + 一次保存，上一版就永久消失。
# 故每次落盘前，把**当前**文档复制一份到 `data/.bak/editor-<时间戳>.json`，
# 只保留最近 N 份。
#
# 超出的旧备份**不真删**，而是移入 `data/.bak/.trash/<时间戳>/`（**软删除**）——
# 项目总原则「只复制不删除」是全项目硬不变量（`verify.py` 7q 守卫禁止
# `routes.py` 出现 `unlink`/`remove`），与 `templates/.trash/` 同一体例，可人工找回。
#
# 备份是**增强**：失败**不阻断保存**，只在响应里回报（见 `routes._backup_editor`）。
EDITOR_BACKUP_DIR = DATA_DIR / ".bak"
EDITOR_BACKUP_KEEP = _env_int("QM_EDITOR_BACKUP_KEEP", 5)
# 轮转淘汰下来的旧备份的去处（软删除），延续 `TEMPLATE_TRASH_DIRNAME` 体例
EDITOR_BACKUP_TRASH_DIRNAME = ".trash"

# ---------- 桌面快捷方式图标（V0.0.15） ----------
#
# 皮肤联动的启动图标：前端按当前皮肤配色用 canvas 绘制多尺寸 ICO，
# 上传后端落盘到 data/ 下（随编辑态同目录：内容数据，不是运行时代码），
# 快捷方式的 IconLocation 指向它 —— 换肤后前端重传，图标随之变色。
# 路径恒定，由后端单点决定，不存在用户可控的路径穿越面。
ICON_DIR = DATA_DIR
ICON_FILE = DATA_DIR / "qm-launch.ico"
# 多尺寸 PNG-in-ICO（16/32/48/256）上限：256px PNG 约 20-60K，留足余量
MAX_ICON_BYTES = _env_int("QM_MAX_ICON_BYTES", 256 * 1024)

# ---------- 请求体传输上限（V0.0.22 修正：必须 ≥ 业务上限） ----------
#
# `app.py._read_body()` 用本值先拦下所有请求体，**早于**各业务检查
# （`save_editor` 的 `MAX_EDITOR_BYTES`、`save_template` 的 `TEMPLATE_MAX_BYTES`、
# `save_launch_icon` 的 `MAX_ICON_BYTES`）。若本值低于业务上限，业务层的
# `editorTooLarge` / `templateTooLarge` / `iconTooLarge` **永远不可达** ——
# 用户只会收到误导性的 413 `bodyTooLarge`（旧值固定 256KB，低于编辑态 8MB 与模板 2MB）。
#
# 因此本值**从业务上限派生**，并留「组帧余量」：JSON 外层开销，加上图标以 base64
# 传输的 4/3 膨胀（用 2× 覆盖）。`QM_MAX_BODY` 只能**抬高**该值 —— 调低会重新制造
# 上述不一致，故此处 `max()` 兜底。一致性由 `tools/verify.py`「请求体上限一致性」守卫把关。
BUSINESS_MAX_BYTES = max(MAX_EDITOR_BYTES, TEMPLATE_MAX_BYTES, 2 * MAX_ICON_BYTES)
BODY_OVERHEAD = 256 * 1024
MAX_BODY_BYTES = max(BUSINESS_MAX_BYTES, _env_int("QM_MAX_BODY", BUSINESS_MAX_BYTES + BODY_OVERHEAD))

# ---------- 落盘安全边界（§P0-1） ----------
#
# 生成目录是青蔓唯一会写用户磁盘的动作，边界必须落在服务端（此文件 + dtree_core.py），
# 不得只靠前端弹窗 —— UI 层可绕过。
#
# R6 规模阈值：一次生成允许的「目录 + 文件」总数上限，服务端直接拒绝（不依赖前端确认）。
MAX_NODES = _env_int("QM_MAX_NODES", 500)
# R7（已存在即跳过、不覆盖）与 R8（永不删除）由 dtree_core.build_tree 保证，无需配置项。


def resolve_path(value: "str | os.PathLike[str]") -> Path:
    """路径规范化（§P0-1 R1）：expanduser + resolve，**不要求路径已存在**。

    解析失败（极少数权限/盘符异常）时退化为绝对路径，绝不把异常抛给调用方。
    """
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return Path(value).expanduser().absolute()


def is_within(child: Path, parent: Path) -> bool:
    """child 是否等于 parent 或位于 parent 之下。

    不用 `Path.is_relative_to`：那是 Python 3.9+ 才有的 API，本项目下限 3.8。
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _blocked_subtrees() -> tuple[tuple[Path, str], ...]:
    """R3 系统目录：**整棵子树**禁止写入（C:\\Windows\\ 下任何位置都不行）。"""
    entries = (
        (os.environ.get("SystemRoot") or r"C:\Windows", "系统目录 SystemRoot"),
        (os.environ.get("ProgramFiles") or r"C:\Program Files", "系统目录 Program Files"),
        (os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)", "系统目录 Program Files (x86)"),
        (os.environ.get("ProgramData") or r"C:\ProgramData", "系统目录 ProgramData"),
    )
    out: list[tuple[Path, str]] = []
    for raw, label in entries:
        try:
            out.append((resolve_path(raw), label))
        except (OSError, ValueError):
            continue
    return tuple(out)


def _blocked_roots() -> tuple[tuple[Path, str], ...]:
    """R4 用户关键目录：仅**根本身**禁止，允许其子目录（`桌面\\我的项目` 是正常目标）。"""
    home = Path.home()
    entries = (
        (home, "用户主目录"),
        (home / "Desktop", "桌面"),
        (home / "Documents", "文档"),
        (home / "Downloads", "下载"),
    )
    out: list[tuple[Path, str]] = []
    for raw, label in entries:
        try:
            out.append((resolve_path(raw), label))
        except (OSError, ValueError):
            continue
    return tuple(out)


# R5 项目自身：工具的落盘目标绝不能指向青蔓自己或其上级目录
PROJECT_DIR_RESOLVED = resolve_path(PROJECT_DIR)
BLOCKED_SUBTREES = _blocked_subtrees()
BLOCKED_ROOTS = _blocked_roots()

DEFAULT_VERSION = "V0.00"


def read_version() -> str:
    """读取项目根 VERSION 文件；缺失时返回 DEFAULT_VERSION。"""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_VERSION
    return text or DEFAULT_VERSION
