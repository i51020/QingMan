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

# 请求体上限（防止超大 POST），单位：字节
MAX_BODY_BYTES = _env_int("QM_MAX_BODY", 256 * 1024)

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

# ---------- 编辑态持久化（N2） ----------

# 编辑态文档落盘位置：项目根 data/editor.json。
# 选后端文件而非 localStorage：端口自 PORT_START 起扫描、并不固定，
# 而 localStorage 按 origin（含端口）隔离 —— 端口一变，草稿即静默丢失。
DATA_DIR = PROJECT_DIR / "data"
EDITOR_FILE = DATA_DIR / "editor.json"

# 编辑态文档体积与节点数上限（防异常大文档落盘）
MAX_EDITOR_BYTES = _env_int("QM_MAX_EDITOR_BYTES", 8 * 1024 * 1024)
MAX_EDITOR_NODES = _env_int("QM_MAX_EDITOR_NODES", 20000)

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
