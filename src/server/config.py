"""青蔓 QingMan · 全局配置常量。

本文件是唯一的路径与端口来源，其余模块一律从这里取值，不自行拼路径。
"""

from __future__ import annotations

import json
import os
import shutil
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
# 语言包目录（V0.0.44 · 动态语言包）：新增一门语言 = 往这里放一个 `<tag>.js`，后端自动枚举。
LOCALES_DIR = WEB_DIR / "locales"
SHARED_DIR = SRC_DIR / "shared"
VERSION_FILE = PROJECT_DIR / "VERSION"
START_BAT = PROJECT_DIR / "start.bat"

# ---------- 模板库（V0.0.11） ----------
#
# 模板库位于**项目根**而非 `src/`：它是内容资产、不是运行时代码，
# 也因此**不在版本交付清单内**（清单只覆盖 `src/**` + `start.bat` + `VERSION`）。
# 后果：预览副本（`preview/V<版本>/`）里没有 templates/ —— 后端必须优雅降级，
# 目录缺失时返回「不可用」而不是报错（见 routes.list_templates）。
# 内置层（只读）：随工具交付的**唯一**内置模板目录。
# V0.0.35 起它只是「默认值」—— 运行态目录由 `templates_dir()` 解析（env > settings > 此处），
# 保留了 `TEMPLATES_DIR` 这个旧名会误导（它已**不是**当前生效目录），故据此改名。
DEFAULT_TEMPLATES_DIR = PROJECT_DIR / "templates"
# 内置层**基线**：`templates/` 里只有这一个文件是随包交付的。出现别的 `.json`
# 即视为「用户自己放过模板」—— 那是旧布局的真实数据，运行态目录必须继续指向它。
BUNDLED_TEMPLATE_NAMES = frozenset({"P0_空白项目模板.json"})
# 分发层：仓库内独立可分发的模板包（`.md` 主 + `.json` 等价），同样不在交付清单内。
TEMPLATES_PACK_DIR = PROJECT_DIR / "templates-pack"
# 用户层绑定目录的环境变量名（解析优先级最高，见 `templates_dir()`）。
TEMPLATES_DIR_ENV = "QM_TEMPLATES_DIR"

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

# 编辑态文档落盘位置：`data/editor.json`（默认随项目，见下方解析链）。
# 选后端文件而非 localStorage：端口自 PORT_START 起扫描、并不固定，
# 而 localStorage 按 origin（含端口）隔离 —— 端口一变，草稿即静默丢失。
#
# ⚠ **V0.1.0 起此路径由解析链决定**，不再写死 `项目根/data`：
#   ① `QM_DATA_DIR` 环境变量（显式指定，最高优先）
#   ② 项目内 `data/editor.json` **已存在** → 沿用（旧布局，绝不搬动用户已有数据）
#   ③ 项目根**可写** → 项目内（便携用法：数据随目录走）
#   ④ `%APPDATA%/QingMan/data` → 只读安装 / 共享安装的兜底
# 为什么必须这么做：分发给其他用户后，程序目录可能落在只读位置
# （`Program Files`、网络盘、受管终端），写 `data/` 直接失败；同一台机器的多个
# Windows 用户也可能共用一份安装目录。**解析全部无副作用**（不 mkdir、不探测写文件，
# 只用 `os.access`），因此 import 时计算是安全的，测试也不会被拉着写盘。
DATA_DIR_ENV = "QM_DATA_DIR"


def _writable(path: Path) -> bool:
    """`path` 是否可写（只读判定，不产生任何文件）。"""
    try:
        return os.access(path, os.W_OK)
    except OSError:                     # 极端路径（非法字符 / 无权限查询）一律视为不可写
        return False


def resolve_data_dir(project_dir: Path, override: str = "",
                     per_user_root: "Path | None" = None) -> Path:
    """按四级优先解析运行态数据目录（**纯函数**，便于单测，无副作用）。"""
    raw = (override or "").strip()
    if raw:
        return Path(raw).expanduser()
    legacy = project_dir / "data"
    if (legacy / "editor.json").is_file():      # 旧布局有真实数据 → 不搬
        return legacy
    if _writable(project_dir):
        return legacy
    if per_user_root is not None:
        return per_user_root / "data"
    return legacy                                # 连 APPDATA 都没有：退回旧行为


def per_user_root() -> "Path | None":
    """每用户根目录 `%APPDATA%/QingMan`；无 APPDATA（非 Windows / 精简环境）返回 None。"""
    appdata = os.environ.get("APPDATA", "").strip()
    return Path(appdata).expanduser() / APP_NAME_EN if appdata else None


DATA_DIR = resolve_data_dir(PROJECT_DIR, os.environ.get(DATA_DIR_ENV, ""), per_user_root())
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

def desktop_dir() -> Path:
    """真实「桌面」目录：优先读注册表的「用户 Shell 文件夹」，处理 OneDrive 重定向。

    `Path.home() / "Desktop"` 在启用 OneDrive「备份桌面」后**不是**用户看到的桌面
    （真实路径被重定向到 `%OneDrive%\\Desktop` 之类），快捷方式会落在用户找不到的位置
    （A-P3-4）。系统认定的桌面存在
    `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders`
    的 `Desktop` 值里，可能含 `%USERPROFILE%` / `%OneDrive%` 环境变量，须 `expandvars`。

    取不到（非 Windows、键缺失、值非法）一律回落 `Path.home() / "Desktop"` ——
    **绝不因探测失败改变既有行为**。
    """
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                raw, _kind = winreg.QueryValueEx(key, "Desktop")
            expanded = os.path.expandvars(str(raw)).strip()
            if expanded and Path(expanded).is_dir():
                return resolve_path(expanded)
        except (OSError, ImportError, ValueError):
            pass
    return Path.home() / "Desktop"


# ---------- 运行态配置持久化（V0.0.35 · 模板目录绑定） ----------
#
# 用户绑定的模板库目录要跨重启保留，落点选**用户级**配置而非项目内：
# 安装态的程序目录可能只读，写进项目内会直接失败（安装态落点见《项目手册》第十节）。
# 位置按可写性择优：`%APPDATA%/QingMan/settings.json` → 便携回落 `<项目根>/.qingman/`。
# `QM_SETTINGS` 可**覆写**该位置（自动化测试 / 便携分发用）；一旦设定则只认它。
SETTINGS_ENV = "QM_SETTINGS"
SETTINGS_SCHEMA_VERSION = 1


def settings_candidates() -> "tuple[Path, ...]":
    """settings 文件的候选位置（顺序即优先级）。"""
    override = os.environ.get(SETTINGS_ENV, "").strip()
    if override:
        return (resolve_path(override),)
    out: "list[Path]" = []
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        out.append(resolve_path(appdata) / APP_NAME_EN / "settings.json")
    out.append(PROJECT_DIR / ".qingman" / "settings.json")
    return tuple(out)


def settings_path() -> Path:
    """settings 文件的**写入**位置：首个父目录可创建的候选（择优）。

    读取按 `settings_candidates()` 顺序（首个可解析者胜）；写入按可写性择优。
    全部候选都不可创建时返回首选 —— 由调用方把写失败转成明确错误码。
    **注意**：本函数会尝试 `mkdir` 父目录（这就是「择优」的探针）。
    """
    for path in settings_candidates():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return path
    return settings_candidates()[0]


def load_settings() -> dict:
    """读取 settings（首个可解析的候选）。缺失 / 损坏一律返回空表，**不抛异常**。"""
    for path in settings_candidates():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def _has_user_templates(path: Path) -> bool:
    """该目录里是否有**用户自建**模板（`BUNDLED_TEMPLATE_NAMES` 之外的 `.json`）。"""
    try:
        names = {p.name for p in path.glob("*.json")}
    except OSError:
        return False
    return bool(names - BUNDLED_TEMPLATE_NAMES)


def seed_templates(dest: Path) -> list[str]:
    """把内置模板**复制**到 `dest`（只补缺失，`dest` 已有用户模板则整体跳过）。

    仅用于「只读安装 → 每用户模板库为空」这一种情形：用户打开模板列表至少要看到
    那张空白模板。**只复制、不删除**（项目硬不变量）；失败静默（模板不是启动前提）。
    返回实际复制出的文件名（便于测试与日志）。
    """
    if _has_user_templates(dest):
        return []
    copied: "list[str]" = []
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for src in sorted(DEFAULT_TEMPLATES_DIR.glob("*.json")):
            target = dest / src.name
            if target.exists():
                continue
            shutil.copy2(src, target)
            copied.append(src.name)
    except OSError:
        return copied
    return copied


def default_runtime_templates_dir() -> Path:
    """默认运行态模板目录（`templates_dir()` 在 env / settings 都没有时的答案）。

    与数据目录同一取舍：**旧布局优先、可写则随项目、只读则每用户**。
    区别是这里会**播种**内置模板 —— 否则只读安装的用户打开模板列表是空的。
    """
    legacy = DEFAULT_TEMPLATES_DIR
    if _has_user_templates(legacy) or _writable(PROJECT_DIR):
        return legacy
    root = per_user_root()
    if root is None:
        return legacy
    dest = root / "templates"
    seed_templates(dest)
    return dest


def templates_dir_source() -> str:
    """当前运行态模板目录的来源：`env` / `settings` / `default`。"""
    if os.environ.get(TEMPLATES_DIR_ENV, "").strip():
        return "env"
    saved = load_settings().get("templatesDir")
    if isinstance(saved, str) and saved.strip():
        return "settings"
    return "default"


def templates_dir() -> Path:
    """运行态模板库目录：`QM_TEMPLATES_DIR` env > settings 文件 > 默认 `templates/`。

    **每次调用重新解析**（不缓存）—— `PUT /api/templates-dir` 改完即刻生效、无需重启。
    解析失败一律回落默认目录，绝不把异常抛给调用方（与 `resolve_path` 同取舍）。
    """
    raw = os.environ.get(TEMPLATES_DIR_ENV, "").strip()
    if raw:
        return resolve_path(raw)
    saved = load_settings().get("templatesDir")
    if isinstance(saved, str) and saved.strip():
        return resolve_path(saved.strip())
    return default_runtime_templates_dir()


DEFAULT_VERSION = "V0.00"


def read_version() -> str:
    """读取项目根 VERSION 文件；缺失时返回 DEFAULT_VERSION。"""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_VERSION
    return text or DEFAULT_VERSION
