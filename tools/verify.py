"""青蔓 QingMan · 交付校验。

用法：
    python tools/verify.py [版本根目录]

「版本根目录」需包含 src/ 与 VERSION；缺省为脚本所在项目的根目录。
`--against <版本>` 的清单**只在该根目录之下的 versions/<版本>/ 查找**（不从项目根兜底）。
校验项与《错误笔记》交付清单一致：
  1. 必需文件存在
  2. HTML 标签闭合、关键 id 存在；**已退场 id 未回流**（`REMOVED_IDS`，V0.0.51@r12；
     与「关键 id 存在」是一对方向相反的清单 —— 只记前者等于只记住一半决定）
     ⚠ V0.0.53：标签配对数**先剥注释再数** —— 注释里写出被删标签的字面量曾让本项误报
     （见 7. 之后的「2.」段内注释）。
  3. main.js 中引用的 id 在 index.html 中真实存在
  4. JS 语法（ESM 方式交由 node --check 解析）
  5. CSS 大括号平衡
  6. Python 语法（ast 只读解析，不产生 __pycache__，保证校验不污染被校验目录）
 7. 帮助页无硬编码中文（§P0-3 L1：文案必须经取词表，页面只留 data-i18n 键名）
 7b. 双语与皮肤预留（§P0-3）：主界面无硬编码中文 / JS 无中文串字面量 / 组件 CSS 无裸色值 /
     组件 CSS 不感知皮肤 / 皮肤目录契约 / 偏好键名（**4 键**，权威清单见 §P0-3 L6；
     V0.0.51@r9 撤销生成参数区折叠，`qm.genBar` 退场）
 7ai. 偏好键名「三方一致」（§P0-3 L6）：实现（`i18n/index.js` 的 `_KEY` 声明）/ 守卫
     （本文件 `PREF_KEYS`）/ 文档（§P0-3 L6 规则行）三处键集合必须相等
 7aj. 图标契约（§P0-3 L8）：`.ic-*` 定义↔使用双向配对 / 形状类须声明 `--m` /
     禁 `background-image`、`<img>` 引 SVG 与 `@font-face` / 图标按钮可访问名（顶栏另须 tooltip）/
     字形图标白名单与图标册三方一致（实现 / 本文件 `ICON_SHAPES` / §P0-3 L8 规则行）
     ＋ **动态**图标按钮（模板行 ⋮，V0.0.51@r11）的可访问名与「与右键同源」接线：
     上一条只扫静态 `index.html`，故 JS 造出来的按钮改判产出方源码（补盲区）
 7al. 「历史版本」端点接线（V0.0.51@r9）：后端常量/枚举/恢复（**须复用 `routes.save_editor`**）
     → 分发两处 → 前端封装 → 接线（**须真拉列表**）→ 错误码，七处任一断开即红
 7am. 顶栏状态区契约（V0.0.53）：两个状态读数改**纯图标**后的接线 —— 文字形态（`btn-txt`）
     不得回流 / `#chipBackend` 仍须带状态点与下三角 / `setServiceState` 须写 `aria-label` /
     `#chipSave` 不得再挂 `data-i18n`（会覆盖图标）/ 旋转须留 reduced-motion 退出口
 7an. 帮助页文案无 Markdown 标记（V0.0.53@r2）：两个渲染器都不解析 Markdown ⇒ `help.*`
     里出现的 `**` / 反引号 / `~~` / `[文字](链接)` 会原样上屏。**只查 `help.*`**
     （`sample.readmeContent` 是生成的 README 正文，那里的 Markdown 是应当的）；
     抽到的条数低于哨兵即报红，防「抽取式失配 → 循环空转 → 判据恒真」（§三.87 / §三.88）
 7ao. 清单元数据契约（V0.0.53）：**日期只进元数据、不进版本号**（SemVer 2.0.0 §10：
     build metadata 不参与优先级比较，当不了回退点；同版多次构建由 `@rN` 承担）。
     全部存量清单逐份查：`version` 纯三段式 / `createdAt` 在已登记写法内 /
     `createdAtIso` 带时区 / `build` 块字段白名单
 7ap. 版本—清单双层契约（§P0-6 M10）：版本号**只答兼容性**，时间/模型/工具链全在根
     `manifest.json`。判据＝顶层 `version` 与 `VERSION` 逐字相等 / 当前 `(版本, 最新修订)`
     必有记录 / 记录带时区且不早于 store 清单日期 / `model`·`tools` 字段白名单非空 /
     记录里的版本必须真实存在于 `versions/`（判定本体是 `tools/manifest.py::validate`，
     本项与 CLI `manifest.py check` 同源 —— 两处不得各写一份）
 7aq. 版本号形态与单调性（SemVer 2.0.0 §2）：`versions/` 的**目录名**是版本号的另一半
     身份证（7ao 只查清单内部字段，查不到目录被改名/错位）。判据＝目录名纯三段式且
     无前导零 / 目录名与该目录**每份**清单的 `version` 一致 / 每目录至少一份清单 /
     **父链连续**（数值排序后第 i 个版本的 r1 清单 `parent` 必须是第 i-1 个版本）
 7d-9. 皮肤文件**顶层只许 `:root` + `--qm-*` 声明**（§P0-3 L5）：与 7d「组件 CSS 不感知皮肤」
     **方向相反**，两者合起来才是完整的**双向隔离**（`skins/README.md` 契约「皮肤 == 一组变量
     覆盖值，不是一整套组件样式」的机器化；§P2 第 45 项）
 7e. CSS 类名形态（§P2 第 1 项）：一律 kebab-case，不得含下划线或大写
 7f. 体积上限（§P2 第 4 项）：src/** 合计 ≤ 640K，单文件 ≤ 64K
 7g. 帮助页键位登记（§P2 第 8 项）：源码若有修饰键快捷键监听（ctrlKey/metaKey/altKey），
     帮助页键位小节必须登记至少一条**具体键位**，不得只留「待定 / 留空」占位
 8. 接续说明实况段与盘上一致（§P1-6 H4；文件未建立则跳过）
 8b. 源码 § 引用可解析（《错误笔记》§三.22；约定文档不在则跳过）
 8c. 实况段两处渲染失真（不升版，§P1-3）：版本 tag 行必须列出真实版本 tag；
     时间线最新日期必须解析成功（不得为「未标日期」）
 9. 编辑态持久化契约（§P0-7）：schema.json 的 editorDocument/editorNode + 接口标识 + 错误码
 9a. 共享契约版本戳（V0.0.23）：schema.json 的 version 必须等于 VERSION（防契约漂移）
 9b. 落盘安全边界（§P0-1）：config 黑名单 / dtree_core.check_target / routes 接线 / 错误码
 9c. 回归测试网（§P0-2）：tests/ 全部 test_*.py + tools/smoke.py + tools/browser_smoke.py
     + tools/pack_templates.py（仅项目根，预览目录跳过）
 7s. 请求体上限一致性（V0.0.22）：MAX_BODY_BYTES ≥ 各业务上限（编辑态/模板/图标），
     否则业务错误码 editorTooLarge / templateTooLarge 不可达
 7t. 帮助页分节渲染幂等（V0.0.22）：renderSections 必须清空容器，语言切换不得累积
 7u. 默认示例取词前置（V0.0.22）：initPrefs() 必须早于 defaultRoot()（否则固化出厂语言）
 7v. P3 整洁与健壮性（V0.0.24）：currentId 声明顺序 / 图标指纹持久化 /
     canMove missing / 模板失败回滚 / import 合并 / pathConflictDir 对称
 7w. 浏览器冒烟覆盖（V0.0.25）：tools/browser_smoke.py 必须仍然锚定
     未捕获异常判定 / 漏翻判定 / 帮助页分节幂等 / 默认示例语言 / 沙盒隔离
     —— 防止这条「页面跑起来才现形」的守卫被削成空壳（§P0-2 T7）
 10. 指纹比对（--against <版本>）：与该版本**最高修订**清单逐文件比对 SHA-256
退出码：0 全部通过；1 存在失败项。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
sys.dont_write_bytecode = True  # 校验工具不得在项目内留下 __pycache__
from store import (STAMP_PATTERNS, fingerprint_diff, latest_revision,  # noqa: E402
                   load_manifest, manifest_filename)
# 7ap 的判定本体在 manifest.py（CLI `manifest.py check` 与本守卫同源，不各写一份）
import manifest  # noqa: E402

PAIRED_TAGS = (
    "html", "head", "body", "div", "section", "aside", "header", "footer",
    "main", "span", "button", "label", "ul", "li", "pre", "h1", "h2", "h3", "p", "code",
)

REQUIRED_IDS = ("topbar", "chipSave", "chipBackend", "btnHelp", "btnSupport", "btnLogo",
    # V0.0.40：语言 / 皮肤由 `<select>` 改为「图标按钮 + 浮层」（设计提案 §2）；
    # 窄窗低频入口折入 btnMore。故 langSelect / skinSelect 退场，换为下列 id。
    "btnLang", "btnSkin", "btnMore",
    "popLang", "popSkin", "popMore", "skinGrid",
    "sidebar", "templateList",
    # V0.0.41：模板编辑区「新建模板」入口 + 应用内弹窗（手册 9.2 节 #7 / 10.2 节 #4）
    "btnNewTemplate", "dlgNewTemplate", "newTplName", "newTplDesc", "newTplBase", "newTplConfirm",
    "center", "genBar", "inTarget", "inDryRun",
    # V0.0.40：目标位置「选择…」按钮（手册 §10.2 #13；复用模板目录的原生目录选择器）
    "btnPickTarget",
    "toolbar", "btnAddChild", "btnRename", "btnDelete",
    "btnUndo", "btnRedo",
    # V0.0.51@r3：视图组「全部展开」「全部折叠」两颗合一为单颗切换 → btnExpandAll/btnCollapseAll 退场
    "btnToggleAll", "btnGenerate",
    "treeCanvas", "statusText", "statusCount",
    # V0.0.43：F 组批量操作条（多选 ≥2 时出现）
    "batchBar", "batchInfo", "btnBatchCopy", "btnBatchDelete", "btnBatchClear",
    "inspector", "propName", "propType", "propPath", "propDirs", "propFiles", "propDepth",
    "propNote", "btnCopyName", "btnCopyPath", "btnCopyNote",
    # V0.0.43：H 组「属性 ⇄ 源码」双模式（分段控件 + 两个面板）
    "inspMode", "btnInspProp", "btnInspSrc", "inspPropPane", "inspSrcPane", "inspSource",
    "genResult", "toastHost", "ctxMenu",
    # V0.0.40：应用内弹层（需求 §10.2 #9 支持/帮助内嵌；#7 服务设置）
    "scrim", "dlgHelp", "dlgSupport", "dlgService",
    # V0.0.51@r7 · 服务设置补全（手册 §10.2 #3）：常驻「状态/版本/数据目录」三行
    # + 两颗「打开目录」按钮（替代原来唯一那颗「测试连接」）
    # @r8：第一颗的靶子由 `btnOpenProject`（项目根）换成 `btnOpenTpl`（模板库目录）
    # @r9：加第三颗 `btnBackups`（历史版本入口）+ 历史版本弹窗 `dlgBackups` / 列表 `bakList`
    "svcStatus", "svcVersion", "svcDataDir", "btnOpenTpl", "btnOpenData",
    "btnBackups", "dlgBackups", "bakList",
)

# 已退场 id（V0.0.51@r12 立）：这些 id 曾属主界面结构，**删掉它们是一个决定**，故反向钉住
# —— 不得在 `index.html` 里复活。它与 `REQUIRED_IDS` 是一对方向相反的清单：一个管「必须
# 还在」，一个管「不许回来」。只登记前者，等于只记住了一半（§三.81「读起来像完成」）。
# 注：`checklist` 的「已移除」由 7m 单独把关（它带着上下文：左栏自检收敛为顶栏三态按钮），
# 此处不重复登记，避免同一条属性日后在两个判据里分叉。
REMOVED_IDS = (
    # V0.0.51@r12：左栏面板标题下的解说句。它在 @r6 先被摘掉第一行（硬编码的
    # `templates/`），本批摘掉最后一行 ⇒ 外层 `<p>` 一并删除，而不是留一个空盒子。
    # 那句文案讲的是 `help.quickStart.3` 的同一件事，解说归帮助页。
    "tplNote",
)

REQUIRED_FILES = (
    "VERSION",
    "start.bat",
    "src/server/__init__.py",
    "src/server/__main__.py",
    "src/server/config.py",
    "src/server/dtree_core.py",
    "src/server/routes.py",
    "src/server/app.py",
    "src/shared/schema.json",
    "src/shared/error-codes.json",
    "src/web/index.html",
    "src/web/help.html",
    "src/web/support.html",
    "src/web/assets/logo.svg",
    "src/web/assets/sponsor-wechat.png",
    "src/web/css/tokens.css",
    "src/web/css/base.css",
    "src/web/css/layout.css",
    "src/web/css/help.css",
    "src/web/js/main.js",
    "src/web/js/help.js",
    "src/web/js/support.js",
    "src/web/js/i18n/index.js",
    "src/web/locales/zh-CN.js",
    "src/web/locales/en-US.js",
    "src/web/locales/README.md",
    "src/web/js/i18n/skins.js",
    "src/web/js/core/bus.js",
    "src/web/js/core/store.js",
    "src/web/js/core/api.js",
    "src/web/js/modules/tree-model.js",
    # V0.0.43：选择集合的语义运算（F 组）—— 从 main.js 拆出，兼解单文件体积上限
    "src/web/js/modules/selection.js",
    # V0.0.48：模板库（目录绑定 / 列表与轮询 / 行操作 / 另存为·新建）—— 从 main.js 拆出，同一理由
    "src/web/js/modules/templates.js",
    "src/web/js/ui/tree-view.js",
    "src/web/js/ui/inspector.js",
    "src/web/js/ui/toast.js",
)

CJK = re.compile(r"[\u4e00-\u9fff]")

# 二进制扩展名：换行检查豁免（PNG/JPEG 等含 CR 字节属正常）。
# 同时单文件体积上限仍约束它们（SRC_FILE_LIMIT）。
# `.zip` 于 V0.0.37（6D）加入：`templates-pack/*.zip` 是**可再生的分发件**（deflate 流
# 天然含 0x0D 字节），且 §P1-4 的 `legacy/trash-archive-<日期>.zip` 同属此类。
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
                   ".woff", ".woff2", ".ttf", ".otf", ".eot", ".zip"}

# 换行一致性守卫的扫描范围 = **纳入版本控制的文本文件全集**（含 versions/**/MANIFEST*.json）。
# 排除运行时与派生内容：data/（运行时数据，见 §P0-7）、store/（对象库 blob 副本）、.git/。
# 曾因只扫 src/ 而漏检 versions/ 下全部 29 份清单 —— 见《审查报告_工具链_20261010》§P1-1。
EOL_EXCLUDE_TOP = {"data", "store", ".git"}
EOL_EXCLUDE_DIRNAMES = {"__pycache__", ".trash"}

# 源码 § 引用守卫：`§<标签>` 的标签语法（ASCII 编号如 P0-1，或纯中文名如 编码基线）。
# 契约：引用**必须紧贴书写**（`§P0-1`）—— `§` 后带空白视为散文（"§ 引用…"），不参与校验；
# 否则中文散文会被误当成编号（实证：`_sandbox/srcref_probe_20261009/`）。
SRC_REF = re.compile(r"§([A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*|[\u4e00-\u9fff]+)")
# 约定文档里「已定义编号」的判据：标题行（含 `## 三、P2 …` 这类带序号的写法）
SECTION_LABEL = re.compile(
    r"^#+\s+(?:[一二三四五六七八九十]+、)?\s*(P\d+(?:-\d+)?|编码基线)(?=[\s、（(]|$)"
)
# § 引用只在源码文本里查（文档自身引用的编号体系另属 docs/ 维护规则）
SRC_REF_EXTS = (".py", ".js", ".css", ".html", ".json", ".md")

results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, note: str = "") -> None:
    results.append((bool(ok), name, note))


def node_version_key(name: str) -> tuple[int, ...]:
    """版本目录名 → 可比较的版本键（`22.22.2-6` → `(22,22,2,6)`；无数字 → `()`）。

    用于「托管 node 取最新」—— 必须按**数字**比较，不能按字典序
    （字典序会把 `9.x` 排在 `24.x` 之后）。
    """
    return tuple(int(x) for x in re.findall(r"\d+", name))


def iter_managed_nodes(base: Path) -> list[Path]:
    """`<base>/<版本>/node.exe` 中真实存在的那些，**按版本从新到旧**排序。

    旧实现硬编码 `versions/22.22.2-6/node.exe` —— 托管运行时一升级即失效（§P2-2）。
    """
    if not base.is_dir():
        return []
    hits = [d / "node.exe" for d in base.iterdir() if (d / "node.exe").is_file()]
    return sorted(hits, key=lambda p: node_version_key(p.parent.name), reverse=True)


def find_node() -> str | None:
    """定位 node：先 PATH，再扫描托管目录下的**全部版本**取最新。"""
    for name in ("node", "node.exe"):
        hit = shutil.which(name)
        if hit:
            return hit
    managed = iter_managed_nodes(Path.home() / ".workbuddy" / "binaries" / "node" / "versions")
    return str(managed[0]) if managed else None


# ---------- 皮肤色板：绑定与对比度（V0.0.39 · §十三.3 / §十三.4）----------
_CSS_VAR_RE = re.compile(r"(--qm-[a-z0-9-]+)\s*:\s*([^;]+);")

# 文本配对（AA 4.5）—— 配对集**由组件 CSS 的实际共现反查得出**（grep `color:` 与
# `background:` 的搭配），非凭空设定。列 `(说明, 前景变量, 背景变量)`。
SKIN_TEXT_PAIRS = (
    ("正文·面板", "--qm-text", "--qm-surface"),
    ("正文·页底", "--qm-text", "--qm-bg"),
    ("正文·控件", "--qm-text", "--qm-surface-2"),
    ("次要·面板", "--qm-text-dim", "--qm-surface"),
    ("次要·页底", "--qm-text-dim", "--qm-bg"),
    ("强调墨·面板", "--qm-accent-ink", "--qm-surface"),
    ("强调墨·软底", "--qm-accent-ink", "--qm-accent-soft"),
    ("主按钮字", "--qm-on-accent", "--qm-btn-bg"),
    ("主按钮字·悬停", "--qm-on-accent", "--qm-btn-bg-hi"),
    ("危险·面板", "--qm-danger", "--qm-surface"),
    ("危险·控件", "--qm-danger", "--qm-surface-2"),
    ("危险·软底", "--qm-danger", "--qm-danger-soft"),
    ("警告·面板", "--qm-warn", "--qm-surface"),
)
# 非文本配对（AA 1.4.11 → 3.0）：`--qm-accent` 在组件 CSS 里**从不作 `color`**，
# 只作描边 / 轮廓 / 选中态，故按「UI 组件边界」的 3:1 门槛校验。
SKIN_NONTEXT_PAIRS = (
    ("描边·页底", "--qm-accent", "--qm-bg"),
    ("描边·面板", "--qm-accent", "--qm-surface"),
    ("描边·软底", "--qm-accent", "--qm-accent-soft"),
)
SKIN_CONTRAST_MIN_TEXT = 4.5
SKIN_CONTRAST_MIN_NONTEXT = 3.0


def css_vars(text: str) -> dict[str, str]:
    """抽取 `--qm-*` 的**字面量**取值（跳过 `var(...)` / `url(...)` 这类间接引用）。"""
    out: dict[str, str] = {}
    for key, val in _CSS_VAR_RE.findall(text):
        val = val.strip()
        if "var(" in val or "url(" in val:
            continue
        out[key] = val
    return out


def split_light_dark(css_text: str) -> tuple[dict[str, str], dict[str, str]]:
    """tokens.css → (浅色块, 深色块生效值)。深色块只覆盖子集，故须叠在浅色之上。"""
    idx = css_text.find("@media")
    light = css_vars(css_text[:idx]) if idx >= 0 else css_vars(css_text)
    dark = dict(light)
    if idx >= 0:
        dark.update(css_vars(css_text[idx:]))
    return light, dark


def _hex_rgb(val: str) -> tuple[int, int, int] | None:
    val = val.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", val)
    if m:
        s = m.group(1)
        return (int(s[0] * 2, 16), int(s[1] * 2, 16), int(s[2] * 2, 16))
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", val)
    if m:
        s = m.group(1)
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    return None


def rel_luminance(rgb: tuple[int, int, int]) -> float:
    def ch(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def _lstar(Y: float) -> float:
    """CIE L*（D65，Yn = 1）。「三阶落差」用它而非相对亮度差 ΔL ——
    后者**不是感知均匀量、不可跨明暗比较**（7d-8 的判据来源见《错误笔记》）。"""
    return 116.0 * (Y ** (1.0 / 3.0)) - 16.0 if Y > (6.0 / 29.0) ** 3 else Y * 903.2963


def contrast_ratio(fg: str, bg: str) -> float | None:
    """WCAG 对比度。任一侧不是 `#rgb` / `#rrggbb` 字面量 → None（调用方须显式报错）。"""
    rf, rb = _hex_rgb(fg), _hex_rgb(bg)
    if rf is None or rb is None:
        return None
    lf, lb = rel_luminance(rf), rel_luminance(rb)
    if lf < lb:
        lf, lb = lb, lf
    return (lf + 0.05) / (lb + 0.05)


def strip_comments(text: str, kind: str) -> str:
    if kind == "js":
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"(?m)^\s*//.*$", "", text)
    else:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


# 组件 CSS 的「裸色值」判据：须覆盖**所有**字面量色值写法 —— 只查 `#hex` 会让
# `rgb()/rgba()/hsl()/hsla()` 逃逸（D-P2-1：base.css 的 2 处裸 rgba 即由此漏过）。
# 按「函数名 + 左括号」判定，与具体数值无关，故不会误伤 `var(--qm-*)`。
RAW_COLOR_LIKE = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|rgba|hsl|hsla)\s*\(", re.I)
# 裸字号：`font-size` 的取值**未经 `var(--qm-*)`**（§P0-3 L4「禁止裸尺寸」的**字号档**）。
# 刻意**不**写成「未以 px 结尾即通过」—— `1rem` / `inherit` 同属"不走 token"，不能因为
# "不是 px"就放过；故判据取**白名单式**：取值必须以 `var(--qm-` 打头。
RAW_FONT_SIZE_LIKE = re.compile(r"font-size\s*:\s*([^;{}]+)")


def raw_color_hits(body: str) -> list[str]:
    """返回 CSS 文本中出现的**字面量色值**（`#hex` / `rgb()` / `rgba()` / `hsl()` / `hsla()`）。

    §P0-3 L4：组件 CSS 不得写裸色值，唯一允许字面量的地方是 `tokens.css`。
    承担判定职责，故提为模块级函数以便单测（§P2 第 19 项裁定）。
    """
    return RAW_COLOR_LIKE.findall(body)


def raw_font_size_hits(body: str) -> list[str]:
    """返回 CSS 文本中出现的**裸字号**声明（取值未经 `var(--qm-*)`）。

    §P0-3 L4（强制范围 ＝ 色值 + 字号）：组件 CSS 不得写**裸字号**。字号已收敛为 `tokens.css` 的 `--qm-fs-*` 尺度
    （V0.0.51@r10），故判据取**白名单式** —— 取值须以 `var(--qm-` 打头；`12px` /
    `1rem` / `inherit` 一律计入。与 `raw_color_hits` 对称，提为模块级函数以便单测
    （§P2 第 19 项同款理由）。**本判据只管字号**，其余尺寸档位（间距 / 描边 / 圆角…）
    已裁定**不做机器化**（§P2 第 44 项，2026-10-16），不得据本条反推「L4 已全部落地」。
    """
    hits: list[str] = []
    for m in RAW_FONT_SIZE_LIKE.finditer(body):
        val = m.group(1).strip()
        if not val.startswith("var(--qm-"):
            hits.append(f"font-size:{val}")
    return hits


# 「取词表里到底有哪些键」的**唯一**口径（V0.0.51@r12 立，检查项 7b-2 与 7b-3 共用）。
#   ⚠ 必须①按**键位**取 ②**先剥注释**。两条都是踩过的坑：
#     ① 旧 7b-2 用「任何带点的引号串」，于是把**值**也算了进来 ——
#        `'help.versionFallback': 'V0.0.51'` 的值 `V0.0.51` 被当成一个键（取词表因此
#        虚记 442 键，实为 441）；
#     ② 旧 7b-3 用带 `^...$` 锚点的整串匹配且**未加 `re.M`**，而取词表是「缩进 +
#        `'键': '值',`」的多行字典 ⇒ 正则要求「整个文件就是一个键名」才匹配，
#        **两侧永远各得 0 个键 ⇒ 本项恒 PASS**（一条不可能失败的守卫）。
#   键位形态：行首缩进之后紧跟 `'键':`。
KEY_ENTRY = re.compile(r"""^\s*'([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+)'\s*:""", re.M)


def locale_dict_keys(text: str) -> set[str]:
    """取词表源码文本 → 条目**键**集合（剥注释后按键位取；键值对里的**值**不参与）。"""
    return set(KEY_ENTRY.findall(strip_comments(text, "js")))


def skin_toplevel_violations(body: str) -> list[str]:
    """返回皮肤 CSS 里违反「顶层只许 `:root` 块 + 块内只许 `--qm-*` 声明」的项。

    §P0-3 L5 与 `src/web/css/skins/README.md` 契约首行：皮肤 == **一组 `--qm-*` 变量的
    覆盖值**，**不是一整套组件样式**（16 / 16 款文件头亦各写「不写组件选择器」）。
    既有守卫只覆盖另两个维度 —— **7d-5** 按**变量名**拦、**7c / 7c-1** 按**字面量**拦 ——
    于是「**用 `var()` 去写组件样式**」这条路无人看守（§P2 第 45 项；由 7c-1 反向验证的
    **负向对照 N6** 查出：往皮肤追加 `.rev-probe { font-size: var(--qm-fs-md); }` 竟零红项）。

    判据**白名单式**（同 `raw_font_size_hits` 的理由）：选择器须**恰为** `:root`，
    块内声明名须以 `--qm-` 打头 —— 黑名单只能枚举"已知的坏形态"。
    传入的 `body` 须**已剥注释**，否则注释里的 `:root` / 示例选择器会成假阳性（§三.62 一族）。

    已知边界：本函数不解析 `@` 规则（皮肤不该有 —— 深浅主题归 `tokens.css`），
    顶层出现 `@…{` 会被当作「其它选择器」计入；嵌套块亦计入。
    """
    hits: list[str] = []
    i, n = 0, len(body)
    while i < n:
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        j = i
        while j < n and body[j] not in "{;}":
            j += 1
        head = body[i:j].strip()
        if j >= n:                       # 末尾只剩文本（无括号）
            if head:
                hits.append(f"顶层游离文本:{head[:30]}")
            break
        if body[j] == ";":               # 顶层声明（不在任何块内）
            hits.append(f"顶层游离声明:{head[:30] or '(空)'}")
            i = j + 1
            continue
        if head != ":root":
            hits.append(f"选择器:{head[:30] or '(空)'}")
        depth, k = 1, j + 1
        while k < n and depth:
            if body[k] == "{":
                depth += 1
            elif body[k] == "}":
                depth -= 1
            k += 1
        inner = body[j + 1:k - 1] if depth == 0 else body[j + 1:]
        for piece in inner.split(";"):
            d = piece.strip()
            if not d:
                continue
            if "{" in d:                 # 嵌套块（如 @media 里再包 :root）
                hits.append(f"嵌套块:{d[:30]}")
                continue
            prop = d.split(":", 1)[0].strip()
            if not prop.startswith("--qm-"):
                hits.append(f"非变量声明:{prop[:30] or d[:30]}")
        i = k
    return hits


def template_row_more_violations(js: str, layout: str, soft: str) -> list[str]:
    """返回「模板行 ⋮ 常驻入口」的接线 / 配对违规项（V0.0.51@r11 · 补 7aj ⑤ 的盲区）。

    入参须为**已剔注释**的正文 —— 本仓注释习惯逐字复述类名，裸查必大量假阳性
    （§三.69 / §三.71），与 7aj / 7c / 7d-9 同一口径。

    **为什么需要它**：7aj ⑤ 的「图标按钮可访问名」只扫 `src/web/index.html` 的
    **静态**标记，而本入口由 `modules/templates.js` **动态创建** ⇒ 静态扫描天然扫不到，
    等于给这类按钮开了一条无守卫通道（本批勘察实测确认）。故改从**产出方源码**判。

    四条判据（只锚声明形态，不锚具体文案 / 变量名）：
      ① 标记产出：JS 里须有 `tpl-more`（类名）/ `ic-more`（图标）/ `template.more`（可访问名）
      ② 接线在：`openTemplateContextMenu` 的**调用点** ≥ 2（右键盘路 + ⋮ 盘路）
      ③ 不复造：`ctxMenu.showAt` 在 JS 里**恰 1 处** —— 菜单只许由该函数开。⋮ 若另写一套
         菜单，这里会变成 2 ⇒ 当场红。这是「动作来源唯一」的机器化，也是设计稿
         「行尾 ⋮：打开既有 #ctxMenu …… 不另造一套」的落地保证。
      ④ 样式配对：`layout.css` 有 `.tpl-more` 基础态、`soft.css` 有 `.tpl-row .tpl-more` 复位
    """
    hits: list[str] = []
    # ① 标记产出
    # ⚠ 两侧口径不同：**JS 里类名不带前导点**（`el.className = '… tpl-more'`），
    #   只有 CSS 才写 `.tpl-more` —— 初版把 JS 判据写成 `.tpl-more`，当场误报自己的实现。
    # ⚠ 可访问名的判据**必须带引号锚定**：`template.more` 是 `template.moreTip` 的**子串**，
    #   裸查会让「只写了 tooltip、没写 aria-label」照样判过（本批写单测时发现的判据弱点）。
    for token, why in (("tpl-more", "类名"), ("ic-more", "图标"),
                       ("'template.more'", "可访问名")):
        if token not in js:
            hits.append(f"templates.js 缺 ⋮ 的{why}（{token.strip(chr(39))}）"
                        " —— 常驻入口被摘除？")
    # ② 调用点在（减去 1 处函数定义）
    calls = js.count("openTemplateContextMenu(") - js.count("function openTemplateContextMenu(")
    if calls < 2:
        hits.append(f"openTemplateContextMenu 调用点 {calls} 处（应 ≥2：右键 + ⋮）"
                    " —— ⋮ 可能绕开了同一份菜单")
    # ③ 不另造菜单
    showat = js.count("ctxMenu.showAt(")
    if showat != 1:
        hits.append(f"ctxMenu.showAt 出现 {showat} 处（应恰 1：菜单只由 openTemplateContextMenu 开）"
                    " —— 疑似为 ⋮ 另造了一套")
    # ④ 样式配对
    if ".tpl-more" not in layout:
        hits.append("layout.css 缺 .tpl-more 基础态（占位 / 显隐）")
    if ".tpl-row .tpl-more" not in soft:
        hits.append("soft.css 缺 .tpl-row .tpl-more 复位（该组规则会退回死码）")
    return hits


def status_chip_violations(index_html: str, main_js: str, layout_css: str) -> list[str]:
    """返回「顶栏状态区改成纯图标后」的接线违规项（V0.0.53）。

    背景：文字一旦退场，「状态」就搬进了**图标 / 颜色 / aria-label** 这三样
    **不会报错**的东西里 —— 被顺手删掉时页面照常渲染，只是信息没了。本函数把
    「东西还在不在」机器化。五条判据，每条对应一种「改完还能跑、但东西丢了」的失效：

      ① `btn-txt` 不得回流（回流即文字又上屏，与用户裁定相反）
      ② `#chipBackend` 仍须带 `.dot` 与 `.caret`（文字退场后仅剩的两个可见信号）
      ③ `setServiceState` 须写 `aria-label`（文字退场后状态唯一的无障碍出口）
      ④ `#chipSave` 不得再挂 `data-i18n`（applyStatic 会用文本节点覆盖图标）
      ⑤ 保存中的旋转须留 `prefers-reduced-motion` 退出口

    两侧口径（写单测时踩出来的）：
      ⚠ ④ 必须锚 `data-i18n="`（**带等号**）。写成裸 `data-i18n` 会同时命中同一标签上
        合规的 `data-i18n-title=` ⇒ 恒真 —— 与 `template.more` ⊂ `template.moreTip`
        （V0.0.51@r11）是同一族「子串判据」陷阱。
      ⚠ 三个入参一律**先剥注释**再判：注释里提一句 `btn-txt` / 写出那段标记的字面量
        都不算「还在用」（本批实测：一条说明注释就让标签配对数误报，同类坑）。
    """
    html = re.sub(r"<!--.*?-->", "", index_html, flags=re.S)
    js = strip_comments(main_js, "js")
    css = strip_comments(layout_css, "css")
    hits: list[str] = []

    if "btn-txt" in html:
        hits.append("index.html 又出现 btn-txt（服务 chip 的文字形态回流）")

    block = re.search(r'<button[^>]*id="chipBackend"[^>]*>([\s\S]*?)</button>', html)
    if not block:
        hits.append("index.html 未找到 #chipBackend 按钮")
    else:
        for token, why in (('class="dot"', "状态点"), ('class="caret"', "下三角")):
            if token not in block.group(1):
                hits.append(f"#chipBackend 缺{why}（{token}）")

    fn = re.search(r"function setServiceState\([\s\S]*?\n\}", js)
    if not fn or "aria-label" not in fn.group(0):
        hits.append("setServiceState 未写 aria-label（状态将失去无障碍出口）")

    tag = re.search(r'<[^>]*id="chipSave"[^>]*>', html)
    if not tag:
        hits.append("index.html 未找到 #chipSave")
    elif 'data-i18n="' in tag.group(0):
        hits.append('#chipSave 又挂了 data-i18n（applyStatic 会覆盖图标）')

    if ".ic.is-spinning" not in css:
        hits.append("layout.css 缺 .ic.is-spinning（保存中不再有动效）")
    elif "prefers-reduced-motion" not in css:
        # ⚠ 本分支是**写这条守卫的单测时踩出来的洞**：只写下面那句 `split(...)[-1]`，
        #   在「文件里根本没有 prefers-reduced-motion」时 `split()` 返回**整串** ⇒
        #   整串里当然有 `.ic.is-spinning` ⇒ 判过。即「退出口缺失」这种最该报的情形
        #   反而被漏掉。同族教训见 §三.87 一带：**用「切分后取某段」表达「某段里要有
        #   某物」时，必须先确认切分真的发生过**。
        hits.append("layout.css 无 prefers-reduced-motion（旋转动画缺退出口）")
    elif ".ic.is-spinning" not in css.split("prefers-reduced-motion")[-1]:
        hits.append("旋转动画缺 prefers-reduced-motion 退出口")

    return hits


# 帮助页文案的「Markdown 标记」判据（V0.0.53@r2）。
# 背景：帮助页的**两个**渲染器（`help.js` 的打分节 / `help-doc.js` 的应用内弹窗）
# 都**不解析 Markdown** —— 文案里写的 `**常驻**` 会把两个星号**原样显示给用户**。
# 该缺陷在待办里挂了三个版本，一直靠人眼看，故机器化。
# ⚠ 只查 `help.*` 键 —— `sample.readmeContent` 是**生成出来的 README 正文**，那里的
#   `#` 与 `\n` 是**应当存在的 Markdown**，一并禁掉会把正常功能判红。
HELP_ITEM_RE = re.compile(r"^  '(help\.[^']+)':\s*'(.*)',$", re.M)
HELP_MD_PATTERNS = (
    (re.compile(r"\*\*"), "粗体标记 `**`"),
    (re.compile(r"`"), "反引号"),
    (re.compile(r"~~"), "删除线 `~~`"),
    (re.compile(r"\[[^\]]+\]\([^)]+\)"), "Markdown 链接"),
)
# 抽取式失效的哨兵：`help.*` 实测 59 条（2026-10-17）。低于此即视为「没抽到东西」，
# 不许当成「全都合规」放过 —— 见下方 docstring 的 ⚠ 段。
HELP_ITEM_MIN = 50


def help_markdown_violations(locale_text: str, label: str) -> list[str]:
    """返回某个语言包里 `help.*` 文案**残留的 Markdown 标记**（V0.0.53@r2）。

    为什么值得一条守卫：两个渲染器都不解析 Markdown，写进去的 `**`、反引号、`~~`、
    `[文字](链接)` 会**原样上屏**。它不是崩溃，是「看起来像乱码」—— 页面照常工作，
    所以只能靠机器盯。

    口径：
      ⚠ 入参**先剥注释**再抽。取词表里的 `/* V0.0.53：… `` `sidebar.title` `` … */`
        这类说明注释本身带反引号，不剥就会把自己写的沿革当成违规。
      ⚠ **只查 `help.*`**。`sample.readmeContent` 是生成出来的 README 正文，
        那里的 `#` 与 `\n` 是应当存在的 Markdown。
      ⚠ 抽到的条数低于 `HELP_ITEM_MIN` 时**直接报红**，不返回空列表。这是本仓
        反复踩过的一族坑（《错误笔记》§三.87 / §三.88）：**收集式判据必须先证明
        「收集到东西」**，否则缩进/引号一改，循环体空转、判据恒真、文件里再多星号也不响。
    """
    body = strip_comments(locale_text, "js")
    pairs = HELP_ITEM_RE.findall(body)
    if len(pairs) < HELP_ITEM_MIN:
        return [f"{label} 只抽到 {len(pairs)} 条 help.*（< {HELP_ITEM_MIN}，抽取式可能已失配）"
                "—— 此时判定不作数，先修抽取式"]
    hits: list[str] = []
    for key, val in pairs:
        for pat, why in HELP_MD_PATTERNS:
            found = pat.search(val)
            if found:
                hits.append(f"{label} 的 {key} 含{why}（渲染器不解析 Markdown，会原样上屏）")
    return hits


# 清单元数据判据（V0.0.53）：**日期只进元数据、不进版本号**。
# 依据：SemVer 2.0.0 §10 —— build metadata 不参与优先级比较，因此它当不了「回退点标识」；
# 本项目「同一版本的多次构建」由 `revision` / `@rN` 承担（§P0-6），两种机制不叠加。
MANIFEST_VERSION_RE = re.compile(r"^V\d+\.\d+\.\d+$")
MANIFEST_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")
MANIFEST_BUILD_KEYS = {"author", "task", "evidence"}


def manifest_meta_violations(meta: dict, label: str) -> list[str]:
    """返回一份 store 清单的**元数据违规**项（V0.0.53 · 守卫 7ao）。

    守的是三条**不会自己报错**的约定（写错了清单照常能读，只是语义悄悄变了）：

      ① `version` 必须是纯 SemVer 三段式 —— 日期不得进版本号。塞成 `V0.0.53+2026-…`
         也能被 `store.py checkout` 跑通，但会与 `rN` 语义重复、且污染
         `schema.json` 契约字段与 `help.versionFallback` 这种**用户可见**的串。
      ② 时间字段必须是**已登记的写法**之一（`STAMP_PATTERNS`：新下划线式 / 历史空格式）。
         新增写法必须同时改 `store.py` 的常量 —— 否则下游按格式取值的代码会静默错位。
      ③ `build` 块只许登记过的三个键。**多出来的键一律报红**：本仓反复踩过
         「字段悄悄加、无人同步」的坑（§三.88 同族），故这里取白名单式而非黑名单式。
      ⚠ `build` 与 `createdAtIso` 是**同批引入**的 ⇒ 有 `build` 就必须有 `createdAtIso`；
        缺一个说明清单被人手改过。
    """
    hits: list[str] = []
    ver = meta.get("version")
    if not isinstance(ver, str) or not MANIFEST_VERSION_RE.match(ver):
        hits.append(f"{label} 的 version 不是纯 SemVer 三段式：{ver!r}（日期不得进版本号）")
    stamp = meta.get("createdAt")
    if not isinstance(stamp, str) or not any(re.match(p, stamp) for p in STAMP_PATTERNS):
        hits.append(f"{label} 的 createdAt 不在已登记写法内：{stamp!r}")
    iso = meta.get("createdAtIso")
    if iso is not None and (not isinstance(iso, str) or not MANIFEST_ISO_RE.match(iso)):
        hits.append(f"{label} 的 createdAtIso 不是带时区的 ISO 8601：{iso!r}")
    build = meta.get("build")
    if build is not None:
        if not isinstance(build, dict):
            hits.append(f"{label} 的 build 不是对象")
        else:
            extra = sorted(set(build) - MANIFEST_BUILD_KEYS)
            if extra:
                hits.append(f"{label} 的 build 有未登记字段 {extra}（新增须同步本守卫的白名单）")
        if iso is None:
            hits.append(f"{label} 有 build 却缺 createdAtIso（两者同批引入，缺一说明被手改）")
    return hits


def version_dir_violations(root: Path) -> list[str]:
    """返回 `versions/` 目录树的违规项（守卫 7aq 的**判定本体**，纯只读、可单测）。

    7ao 只查清单**内部**的 `version` 字段；目录名是版本号的另一半身份证，此前无人守。
    四条判据：

      ① 目录名纯三段式、**无前导零**（`V0.01.0` 会被 `versioning.parse` 读成 `0.1.0`，
         形态判据必须比解析器更严）
      ② 目录名与该目录**每份**清单的 `version` 一致（防「清单被错位复制进隔壁目录」）
      ③ 每个版本目录至少一份 `MANIFEST*.json`（无清单的目录不是版本，是垃圾）
      ④ **父链连续**：按数值排序后第 i 个版本的 r1 `parent` 必须是第 i-1 个版本
         （手工塞一个目录进来，链条立刻断 —— 这条把「版本序列」本身变成可验证对象）

    取不到 `versions/` 时只报一条，不逐项爆炸。
    """
    hits: list[str] = []
    vdir = root / "versions"
    dirs = [p for p in vdir.iterdir() if p.is_dir()] if vdir.is_dir() else []
    if not dirs:
        return ["versions/ 下无版本目录"]
    keyed: list[tuple[tuple[int, ...], Path]] = []
    for path in dirs:
        problem = manifest.semver_problem(path.name)
        if problem:
            hits.append(f"目录名 {problem}")
            continue
        keyed.append((tuple(int(x) for x in manifest.SEMVER_RE.match(path.name).groups()), path))
    keyed.sort(key=lambda kv: kv[0])
    for idx, (_num, path) in enumerate(keyed):
        manifests = sorted(path.glob("MANIFEST*.json"))
        if not manifests:
            hits.append(f"{path.name} 目录下无清单")
            continue
        for man in manifests:
            try:
                meta = json.loads(man.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                hits.append(f"{path.name}/{man.name} 读不成 JSON")
                continue
            if meta.get("version") != path.name:
                hits.append(f"{path.name}/{man.name} 的 version={meta.get('version')!r} 与目录名错位")
        base = path / "MANIFEST.json"
        if base.is_file():
            try:
                bm = json.loads(base.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                bm = {}
            want = keyed[idx - 1][1].name if idx else None
            if bm.get("parent") != want:
                hits.append(f"{path.name} 的父指针为 {bm.get('parent')!r}，"
                            f"按数值排序应为 {want!r}（版本链断裂）")
    return hits


def check_fingerprint(root: Path, version: str) -> None:
    """与 versions/<版本>/ 的**最高修订**清单逐文件比对 SHA-256。

    同版本多修订（§P0-6）下，r1 基线往往已落后于主线，因此默认对齐最新修订；
    需要比对某一具体修订时，改传 `版本@rN` 形式（如 `V0.0.1@r1`）。
    输出三态语义由 check() 的 ok 决定：一致 / 有差异（列出改动·新增·缺失）/ 无法判定。
    """
    ref = version
    if "@" in version:
        head, _, tag = version.partition("@")
        version = head.strip()
        tag = tag.strip().lstrip("r")
        # 非法修订引用须**显式报错**，不得含糊成「下无任何清单」（§P2-3）。
        if not tag.isdigit() or int(tag) < 1:
            check(False, f"指纹比对 {ref}",
                  f"修订引用非法：应为 <版本>@r<N>（N ≥ 1）形式，收到 {ref!r}")
            return
        rev = int(tag)
    else:
        rev = latest_revision(root, version)

    # `--against` 只在「传入根目录」之下查找；缺失时把实际查找路径点出来，
    # 免得把「路径结构问题」误读成「内容不符」——见《错误笔记》§三.24。
    vdir = root / "versions" / version
    if rev is None:
        check(False, f"指纹比对 {version}",
              f"无法判定：{vdir} 下无任何清单（--against 只查本目录的 versions/<版本>/）")
        return

    manifest = vdir / manifest_filename(rev)
    if not manifest.is_file():
        check(False, f"指纹比对 {version}@r{rev}",
              f"无法判定：{vdir} 下无 {manifest.name}（--against 只查本目录的 versions/<版本>/）")
        return

    meta = load_manifest(root, version, rev) or {}
    recorded: dict[str, str] = meta.get("files", {})
    inner = meta.get("version")
    label = f"{version}@r{rev}"

    # 目录名必须与清单内容自洽，防止"快照名与内容不符"
    check(inner == version, f"清单自洽 {label}", f"内容 version={inner or '(空)'}，取自 {manifest.name}")

    changed, added, missing = fingerprint_diff(root, recorded)

    clean = not (changed or added or missing)
    detail = "完全一致" if clean else f"改动 {len(changed)} / 新增 {len(added)} / 缺失 {len(missing)}"
    check(clean, f"指纹比对 {label}", detail)
    for rel in (changed + added + missing)[:10]:
        print(f"        [差异] {rel}")


def defined_section_labels(root: Path) -> set[str]:
    """`docs/项目约定.md` 中**已定义**的约定编号（取自标题行）。

    `### P0-1 落盘安全边界` → `P0-1`；`### 编码基线` → `编码基线`；
    `## 三、P2 台账（…）` → `P2`（序号前缀与括号后缀均被剥离）。
    """
    doc = root / "docs" / "项目约定.md"
    if not doc.is_file():
        return set()
    return {m.group(1) for line in doc.read_text(encoding="utf-8").splitlines()
            if (m := SECTION_LABEL.match(line))}


def collect_src_refs(root: Path) -> dict[str, list[str]]:
    """`src/**` 下全部 `§<标签>` 引用：标签 → 出现位置（`相对路径:行号`）。"""
    found: dict[str, list[str]] = {}
    src = root / "src"
    if not src.is_dir():
        return found
    for path in sorted(src.rglob("*")):
        if not (path.is_file() and path.suffix in SRC_REF_EXTS):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for label in SRC_REF.findall(line):
                found.setdefault(label, []).append(f"{rel}:{lineno}")
    return found


def main() -> int:
    argv = list(sys.argv[1:])
    against = ""
    if "--against" in argv:
        i = argv.index("--against")
        against = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
        if not against:
            print("[失败] --against 需要一个版本号，如 --against V0.0.1")
            return 1

    # 只接受「一个根目录」这一个位置参数；多余参数须报错，不得静默忽略（§P2-16）。
    if len(argv) > 1:
        print(f"[失败] 多余的参数：{' '.join(argv[1:])}（只接受一个根目录参数）")
        return 1

    root = Path(argv[0]).resolve() if argv else PROJECT_ROOT
    print(f"[校验] 版本根目录：{root}")
    if not root.is_dir():
        print(f"[失败] 目录不存在：{root}")
        return 1

    # 1. 必需文件
    for rel in REQUIRED_FILES:
        path = root / rel
        if path.is_file():
            check(True, f"存在 {rel}", f"{path.stat().st_size} B")
        else:
            check(False, f"存在 {rel}", "缺失")

    version_text = ""
    version_file = root / "VERSION"
    if version_file.is_file():
        version_text = version_file.read_text(encoding="utf-8").strip()
    ok_version = bool(re.match(r"^V\d+\.\d+\.\d+$", version_text))
    check(ok_version, f"VERSION 格式 {version_text or '(空)'}", "应为 V0.0.1 三段式")

    html_path = root / "src/web/index.html"
    html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""

    # 2. HTML 标签闭合
    #    ⚠ V0.0.53：计数前**必须先剥掉 HTML 注释**。原判据直接在原文上数尖括号，
    #    而注释为了说明「删掉了哪个标签」天然会写出该标签的**字面量** ⇒ 一句注释就能
    #    把配对数数成 `header(2/1)`（本批实测：一条写着 `<header class="center-head">`
    #    的说明注释，让本项在一片「标签其实是平衡的」盘面上报红）。注释不是标记，
    #    不该参与**结构**判定。
    #    只改这一处计数：下面两项 id 判据仍是**文本**比对（`id="x"` 字面查找），
    #    故意保守不动 —— 「退场 id 未回流」宁可严一点，误报比漏报可接受。
    html_markup = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    if html:
        unbalanced = []
        for tag in PAIRED_TAGS:
            opens = len(re.findall(rf"<{tag}[\s>]", html_markup))
            closes = len(re.findall(rf"</{tag}>", html_markup))
            if opens != closes:
                unbalanced.append(f"{tag}({opens}/{closes})")
        check(not unbalanced, "HTML 标签闭合", ", ".join(unbalanced) if unbalanced else "全部平衡")

        missing = [i for i in REQUIRED_IDS if f'id="{i}"' not in html]
        check(not missing, "HTML 关键 id", ", ".join(missing) if missing else f"{len(REQUIRED_IDS)} 项齐全")

        # 反向：已退场 id 不得回流（V0.0.51@r12）。与上一项合起来才是一份完整的结构清单。
        back = [i for i in REMOVED_IDS if f'id="{i}"' in html]
        check(not back, "HTML 退场 id 未回流",
              f"{', '.join(back)} 又回来了 —— 若确要恢复，请从 REMOVED_IDS 摘除并说明理由"
              if back else f"{len(REMOVED_IDS)} 项确认不在")
    else:
        check(False, "HTML 标签闭合", "index.html 未读到")
        check(False, "HTML 退场 id 未回流", "index.html 未读到")
        check(False, "HTML 关键 id", "index.html 未读到")

    # 3. 主界面模块引用的 id 必须真实存在。
    #    V0.0.48：扫描面 = **装配主界面的模块**（main.js + 自其拆出的 modules/templates.js）。
    #    若漏掉拆出的那个，「引用面」会随搬迁悄悄变薄 —— 覆盖变薄看起来和「全过」一样（§三.33）。
    id_srcs = [root / "src/web/js/main.js", root / "src/web/js/modules/templates.js"]
    if all(p.is_file() for p in id_srcs) and html:
        used = sorted(set(re.findall(r"el\(['\"]([\w-]+)['\"]\)",
                                     "\n".join(p.read_text(encoding="utf-8") for p in id_srcs))))
        unknown = [i for i in used if f'id="{i}"' not in html]
        check(not unknown, "JS 引用的 id 均已定义",
              ", ".join(unknown) if unknown else f"{len(used)} 个引用全部命中（main + modules/templates）")
    else:
        check(False, "JS 引用的 id 均已定义", "main.js / modules/templates.js 或 index.html 未读到")

    # 4. JS 语法（ESM）
    node = find_node()
    js_files = sorted((root / "src/web/js").rglob("*.js"))
    if not node:
        # 语义裁定（§P2 第 20 项）：**不做「真跳过」** —— JS 语法是交付门禁的一项，
        # 静默少一项会让「覆盖变薄」看起来和「全过」一样（同 §三.33 的教训）。
        # 故保留为失败，只把文案从误导性的「跳过」改为准确表述。
        check(False, "JS 语法", "未找到 node —— JS 语法检查无法执行（本条为必需项）")
    else:
        bad = []
        with tempfile.TemporaryDirectory() as tmp:
            for js in js_files:
                target = Path(tmp) / (js.stem + ".mjs")
                target.write_text(js.read_text(encoding="utf-8"), encoding="utf-8")
                proc = subprocess.run(
                    [node, "--check", str(target)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
                if proc.returncode != 0:
                    bad.append(f"{js.name}: {(proc.stderr or '').strip().splitlines()[:2]}")
        check(not bad, "JS 语法", "; ".join(bad) if bad else f"{len(js_files)} 个文件通过")

    # 5. CSS 括号平衡
    css_files = sorted((root / "src/web/css").rglob("*.css"))
    bad_css = []
    for css in css_files:
        text = strip_comments(css.read_text(encoding="utf-8"), "css")
        if text.count("{") != text.count("}"):
            bad_css.append(f"{css.name}({text.count('{')}/{text.count('}')})")
    check(not bad_css, "CSS 大括号平衡", ", ".join(bad_css) if bad_css else f"{len(css_files)} 个文件平衡")

    # 6. Python 语法（ast 只读解析：不生成 __pycache__，校验不得污染被校验目录）
    py_files = sorted((root / "src/server").glob("*.py"))
    py_bad = []
    for py in py_files:
        try:
            ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError as exc:
            py_bad.append(f"{py.name}: 第 {exc.lineno} 行 {exc.msg}")
        except (OSError, UnicodeDecodeError) as exc:
            py_bad.append(f"{py.name}: {exc}")
    check(not py_bad, "Python 语法", "; ".join(py_bad) if py_bad else f"{len(py_files)} 个文件通过")

    # 6b. 换行一致性（§编码基线：start.bat 用 CRLF，其余纳入版本控制的文本文件用 LF）
    #     扫描范围＝版本控制的文本文件全集（含 versions/ 清单）；排除运行时/派生目录
    #     （见 EOL_EXCLUDE_TOP）。start.bat 例外：须纯 CRLF 供 cmd.exe。
    #     本项目以 SHA-256 指纹校验内容，字节随平台漂移会直接造成指纹失配，故必须把关。
    eol_bad: list[str] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        for entry in cur.iterdir():
            if entry.relative_to(root).parts[0] in EOL_EXCLUDE_TOP:
                continue
            if entry.is_dir():
                if entry.name not in EOL_EXCLUDE_DIRNAMES:
                    stack.append(entry)
                continue
            if not entry.is_file():
                continue
            if entry.suffix.lower() in BINARY_SUFFIXES or entry.name == "start.bat":
                continue
            if b"\r" in entry.read_bytes():
                eol_bad.append(f"{entry.relative_to(root).as_posix()}(含 CR)")
    bat = root / "start.bat"
    if bat.is_file():
        b = bat.read_bytes()
        if not (b"\r\n" in b and b.replace(b"\r\n", b"").count(b"\n") == 0):
            eol_bad.append("start.bat(应为纯 CRLF)")
    check(not eol_bad, "换行一致性",
          "; ".join(eol_bad) if eol_bad else "版本控制文本 = LF，start.bat = CRLF")

    # 7. 帮助/支持页不得硬编码中文（§P0-3 L1：文案必须经取词表，页面只留 data-i18n 键名）
    cjk_pages: list[str] = []
    for page in ("src/web/help.html", "src/web/support.html"):
        page_file = root / page
        if page_file.is_file():
            hits = CJK.findall(page_file.read_text(encoding="utf-8"))
            if hits:
                cjk_pages.append(f"{Path(page).name}:{''.join(hits[:4])}")
        else:
            cjk_pages.append(f"{Path(page).name}:未读到")
    check(not cjk_pages, "帮助支持页无硬编码中文",
          "；".join(cjk_pages) if cjk_pages else "文案全部走 data-i18n 取词")

    # 7b. 文案一律经取词表（§P0-3 L1–L2）：页面只留键名，JS 模块不直写中文串
    idx_html = root / "src/web/index.html"
    if idx_html.is_file():
        idx_hits = CJK.findall(idx_html.read_text(encoding="utf-8"))
        check(not idx_hits, "主界面无硬编码中文",
              f"发现 {len(idx_hits)} 处字面量：{''.join(idx_hits[:6])}" if idx_hits
              else "文案全部走 data-i18n 取词")
    else:
        check(False, "主界面无硬编码中文", "index.html 未读到")

    literal_bad = []
    # 数据字面量豁免（非文案）：约定文件名是**数据标识**，不进取词表（V0.0.17 note 提炼）
    LITERAL_DATA_ALLOW = {"说明文档.md"}
    for js in sorted((root / "src/web/js").rglob("*.js")):
        if "i18n" in js.parts:
            continue   # 取词表自身就是文案的存放处
        body = strip_comments(js.read_text(encoding="utf-8"), "js")
        for _quote, text in re.findall(r"""(['"`])((?:\\.|(?!\1).)*?)\1""", body, flags=re.S):
            if CJK.search(text) and text not in LITERAL_DATA_ALLOW:
                literal_bad.append(f"{js.name}：{text.strip()[:24]}")
    check(not literal_bad, "JS 文案经取词表 §P0-3 L1",
          f"直写文案 {len(literal_bad)} 处：{'; '.join(literal_bad[:3])}" if literal_bad
          else "除 i18n/ 外无中文串字面量")

    # 7b-2. 取词键闭包（§P0-3 L2）：页面与 JS 引用的键必须在取词表里存在
    KEY_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+$")
    #   键集合取自模块级 `locale_dict_keys()`（V0.0.51@r12 统一口径：剥注释 + 按键位取，
    #   值不参与）。旧写法拿「任何带点的引号串」当键，会把值 `V0.0.51` 也算成键 ——
    #   判据偏宽，遇到「真的少了某个键」时可能被一个幻影键掩盖。
    dict_file = root / "src/web/locales/zh-CN.js"
    known: set[str] = (locale_dict_keys(dict_file.read_text(encoding="utf-8"))
                       if dict_file.is_file() else set())
    used_keys: dict[str, str] = {}
    for page in ("src/web/index.html", "src/web/help.html", "src/web/support.html"):
        page_file = root / page
        if not page_file.is_file():
            continue
        for key in re.findall(
                r'''data-i18n(?:-title|-placeholder|-aria-label|-alt)?="([^"]+)"''',
                page_file.read_text(encoding="utf-8")):
            used_keys.setdefault(key, page)
    for js in sorted((root / "src/web/js").rglob("*.js")):
        if "i18n" in js.parts:
            continue
        body = strip_comments(js.read_text(encoding="utf-8"), "js")
        for text in re.findall(r"""['"]([^'"\n]+)['"]""", body):
            if KEY_SHAPE.match(text):
                used_keys.setdefault(text, js.name)
    absent_keys = sorted(key for key in used_keys if key not in known)
    check(not absent_keys, "取词键闭包 §P0-3 L2",
          f"取词表缺少 {len(absent_keys)} 个键：{', '.join(absent_keys[:5])}" if absent_keys
          else f"{len(used_keys)} 个引用键全部命中（取词表 {len(known)} 键）")

    # 7b-3. 中英取词表键对齐（§P0-3 L1）：en-US.js 必须与 zh-CN.js 键集一致
    #   ⚠ V0.0.51@r12 **据实修复一条不可能失败的守卫**。原判据是
    #       `set(re.findall(KEY_SHAPE, text))`，而 KEY_SHAPE 自带 `^...$` 且**未加
    #       `re.M`**，取词表又是「缩进 + '键': '值',」的多行字典 ⇒ 正则要求「整个
    #       文件就是一个键名」才匹配，**两侧永远各得 0 个键，本项恒 PASS**。
    #       反向验证（沙盒 `E:\qm_r12_rev`，只改 `en-US.js`）：删掉 `help.quickStart.1`
    #       整行后本项仍打印「中英键集一致」—— 即「中英键对齐」自设立起从未真正生效。
    #       （《任务进度》282–287 行曾以「7b-3 要求中英键集一致」为由解释一次删键，
    #        该理由当时**引用了一条空守卫**，属 §三.85 家族「守卫自身失效」。）
    #   现改用与 7b-2 同一份 `locale_dict_keys()` 口径（剥注释 + 按键位取）。
    zh_file = root / "src/web/locales/zh-CN.js"
    en_file = root / "src/web/locales/en-US.js"
    align_bad = ""
    if zh_file.is_file() and en_file.is_file():
        zh_keys = locale_dict_keys(zh_file.read_text(encoding="utf-8"))
        en_keys = locale_dict_keys(en_file.read_text(encoding="utf-8"))
        only_zh = sorted(zh_keys - en_keys)
        only_en = sorted(en_keys - zh_keys)
        if only_zh or only_en:
            align_bad = f"zh 独有 {len(only_zh)}：{', '.join(only_zh[:3])}；en 独有 {len(only_en)}：{', '.join(only_en[:3])}"
    elif not en_file.is_file():
        align_bad = "缺少 en-US.js"
    check(not align_bad, "中英取词键对齐 §P0-3 L1",
          align_bad if align_bad else f"中英键集一致（各 {len(zh_keys)} 键）")

    # 7b-4. 错误码本地化闭包 + 占位符一致性（§P0-3 L1）
    # 后端返回结构化 {code, detail}，前端按 `err.<code>` 重新成句 —— 因此每个
    # 错误码都必须在两份取词表里有对应键，且占位符集合三方（原文/中文/英文）
    # 完全一致。否则切到英文后要么占位符原样残留，要么整条回退中文。
    codes_file = root / "src/shared/error-codes.json"
    need = []
    err_bad = ""
    if codes_file.is_file() and zh_file.is_file() and en_file.is_file():
        try:
            codes = json.loads(codes_file.read_text(encoding="utf-8"))
        except ValueError:
            codes = {}
        ERR_KV = re.compile(r"'err\.([A-Za-z0-9]+)':\s*'((?:[^'\\]|\\.)*)'")
        zh_err = {m.group(1): m.group(2)
                  for m in ERR_KV.finditer(zh_file.read_text(encoding="utf-8"))}
        en_err = {m.group(1): m.group(2)
                  for m in ERR_KV.finditer(en_file.read_text(encoding="utf-8"))}
        need = [c for c in codes if c != "ok"]

        def ph(text):
            return sorted(set(re.findall(r"\{(\w+)\}", text)))

        miss_zh = [c for c in need if c not in zh_err]
        miss_en = [c for c in need if c not in en_err]
        ph_bad = []
        for c in need:
            base = ph(str(codes.get(c, "")))
            if c in zh_err and ph(zh_err[c]) != base:
                ph_bad.append(f"{c} zh{ph(zh_err[c])}≠{base}")
            if c in en_err and ph(en_err[c]) != base:
                ph_bad.append(f"{c} en{ph(en_err[c])}≠{base}")
            if c in zh_err and c in en_err and ph(zh_err[c]) != ph(en_err[c]):
                ph_bad.append(f"{c} zh≠en")
        if miss_zh or miss_en:
            err_bad = f"缺键 zh {len(miss_zh)} / en {len(miss_en)}：{', '.join((miss_zh + miss_en)[:3])}"
        elif ph_bad:
            err_bad = f"占位符不一致 {len(ph_bad)} 处：{', '.join(ph_bad[:3])}"
    elif not codes_file.is_file():
        err_bad = "缺少 error-codes.json"
    check(not err_bad, "错误码本地化闭包",
          err_bad if err_bad else f"{len(need)} 个错误码中英齐备且占位符一致")

    # 7b-5. 语言策略：跟随系统必须是显式可选的一档，且具备降级匹配与跨页同步
    i18n_file = root / "src/web/js/i18n/index.js"
    picker_file = root / "src/web/js/ui/lang-picker.js"
    lang_bad = ""
    if not i18n_file.is_file():
        lang_bad = "缺少 i18n/index.js"
    else:
        body = i18n_file.read_text(encoding="utf-8")
        # 锚**导出形态**而非裸名：裸名会被「函数还在、只是不再 export」这种真实回归蒙混过关
        # （调用方 `import { loadLocale }` 立刻 undefined，但字面量仍在文件里）。
        # V0.0.44 起含动态语言包运行时（loadLocale / supportedLocales / localeName）——
        # 删掉即「新增语言包不再被发现」，而 auto / 降级匹配照旧通过，故一并锚定。
        for token in ("export const AUTO_LOCALE",
                      "export function matchLocale", "export function resolveLocale",
                      "export function watchLocale", "export function loadLocale",
                      "export function supportedLocales", "export function localeName"):
            if token not in body:
                lang_bad = lang_bad or f"i18n/index.js 缺少 {token}"
    if not lang_bad:
        if not picker_file.is_file():
            lang_bad = "缺少 ui/lang-picker.js"
        elif not re.search(r"\[\s*AUTO_LOCALE\b", picker_file.read_text(encoding="utf-8")):
            # 判据必须落在「选项列表里真的有 auto 这一档」，而非「文件里出现过 AUTO_LOCALE」——
            # 后者会被 labelOf() 之类的残留引用蒙混过关（反向实证场景 c 抓到过这个漏洞）
            lang_bad = "lang-picker.js 未把「跟随系统」列为独立一档"
    check(not lang_bad, "语言策略（跟随系统）",
          lang_bad if lang_bad else "auto 一档 + BCP 47 降级匹配 + 跨页同步 齐备")

    # 7b-6. 动态语言包（V0.0.44）：语言包目录契约 + 清单同步注入
    #     ① 每个语言包必须导出 LOCALE / NAME / dict，且 LOCALE 与**文件名**一致 ——
    #        后端按文件名生成清单、按 NAME 取显示名，契约不成立清单即失真（选择器显示
    #        的名字对不上实际加载的文件）；
    #     ② 三个页面必须**同步**引入 /api/locales.js 且早于 module 脚本 —— 否则语言
    #        选择器会先只列内置语言、拿到清单后再补出扩展语言（菜单跳变）。
    locales_dir = root / "src/web/locales"
    pkg_bad: list[str] = []
    if not locales_dir.is_dir():
        pkg_bad.append("缺少 src/web/locales/ 目录")
    else:
        packs = sorted(locales_dir.glob("*.js"))
        if not packs:
            pkg_bad.append("locales/ 下无语言包")
        for pack in packs:
            body = pack.read_text(encoding="utf-8")
            for token in ("export const LOCALE", "export const NAME", "export const dict"):
                if token not in body:
                    pkg_bad.append(f"{pack.name} 缺 {token}")
            if m := re.search(r"export\s+const\s+LOCALE\s*=\s*'([^']+)'", body):
                if m.group(1) != pack.stem:
                    pkg_bad.append(f"{pack.name} 的 LOCALE({m.group(1)}) 与文件名不符")
            else:
                pkg_bad.append(f"{pack.name} 未以单引号字面量声明 LOCALE")
    if not pkg_bad:
        for page in ("src/web/index.html", "src/web/help.html", "src/web/support.html"):
            page_file = root / page
            text = page_file.read_text(encoding="utf-8") if page_file.is_file() else ""
            i_loc, i_mod = text.find("./api/locales.js"), text.find('type="module"')
            if i_loc < 0:
                pkg_bad.append(f"{Path(page).name}:未引入 locales.js")
            elif i_mod < 0 or i_loc > i_mod:
                pkg_bad.append(f"{Path(page).name}:locales.js 未早于 module 脚本")
    # ③ 端到端接线：`smoke.py` 必须真的经 HTTP 拉一次 /api/locales.js（删掉即
    #    「清单注入接线断了也照样绿」—— 单测只调函数、静态只查标签，都盖不到这一层）。
    #    锚**请求调用**而非路径字面量：判定名里也含 `api/locales.js`，只查字面量会被
    #    「请求删了、名字还在」骗过（反向验证实测抓到过这一漏洞）。
    #    此处不能用 main() 后段定义的 `_read`（那是更靠后的局部函数，会 UnboundLocalError）。
    _smoke_p = root / "tools/smoke.py"
    _smoke_t = _smoke_p.read_text(encoding="utf-8") if _smoke_p.is_file() else ""
    if 'client.request("GET", "/api/locales.js")' not in _smoke_t:
        pkg_bad.append("smoke.py 未做 /api/locales.js 端到端检查")
    check(not pkg_bad, "动态语言包 V0.0.44",
          f"缺失：{', '.join(pkg_bad)}" if pkg_bad
          else f"{len(list((root / 'src/web/locales').glob('*.js')))} 个语言包契约齐备 + 三页同步注入")

    # 7c. 组件 CSS 只允许 var(--qm-*)（§P0-3 L4）；判据见 raw_color_hits（覆盖 #hex 与 rgb()/rgba()/hsl()）
    raw_color = []
    for css in sorted((root / "src/web/css").glob("*.css")):
        if css.name == "tokens.css":
            continue   # 变量的唯一来源，字面量只能写在这里
        for hit in raw_color_hits(strip_comments(css.read_text(encoding="utf-8"), "css")):
            raw_color.append(f"{css.name}:{hit}")
    check(not raw_color, "组件 CSS 无裸色值 §P0-3 L4",
          f"发现 {len(raw_color)} 处：{', '.join(raw_color[:4])}" if raw_color
          else "组件样式全部经 var(--qm-*) 取色")

    # 7c-1. 组件 CSS 只允许 var(--qm-*) 取字号（§P0-3 L4 强制范围之一的**字号档**）。
    #       与 7c 同一姿态：`tokens.css` 豁免（尺度定义处）。覆盖面用 rglob（含 skins/）——
    #       §P0-3 L5 规定皮肤**只供配色 + 影色**，故皮肤里出现字号同样违规（实测 16 款皮肤
    #       0 处，收紧零假阳性；款数由 `skins/*.css` 派生，加款即自动纳入 —— 故此处数字
    #       仅记**写这段时的实测值**，不参与判据）。**本条只管字号**：其余尺寸档位（间距 / 描边 / 圆角…）**已裁定**
    #       **不做机器化**（§P2 第 44 项）—— 不得据本条反推「L4 已全部落地」。
    raw_fs: list[str] = []
    for css in sorted((root / "src/web/css").rglob("*.css")):
        if css.name == "tokens.css":
            continue   # 尺度定义处，字号字面量只能写在这里
        for hit in raw_font_size_hits(strip_comments(css.read_text(encoding="utf-8"), "css")):
            raw_fs.append(f"{css.name}:{hit}")
    check(not raw_fs, "组件 CSS 无裸字号 §P0-3 L4",
          f"发现 {len(raw_fs)} 处：{', '.join(raw_fs[:4])}" if raw_fs
          else "组件样式字号全部经 var(--qm-fs-*) 取用")

    # 7d. 组件 CSS 不得感知皮肤（§P0-3 L5）—— 换肤只靠覆盖变量
    skin_aware = []
    for css in sorted((root / "src/web/css").rglob("*.css")):
        if "skins" in css.parts:
            continue
        body = strip_comments(css.read_text(encoding="utf-8"), "css")
        if "data-qm-skin" in body or re.search(r"\.skin-", body):
            skin_aware.append(css.name)
    check(not skin_aware, "组件 CSS 不感知皮肤 §P0-3 L5",
          f"含皮肤选择器：{', '.join(skin_aware)}" if skin_aware
          else "组件不引用皮肤，换肤只靠变量覆盖")

    # 7d-1. CSS 变量闭包（§P0-3 L4–L5）：组件 / 皮肤只能引用 tokens.css 已定义的 --qm-* 变量。
    #       **皮肤亦须遵守「只做重新赋值」**（`skins/README.md` 契约）：皮肤文件**声明**的
    #       变量同样必须在 tokens.css 已有定义 —— 不得借皮肤引入新变量名（否则等于让皮肤
    #       「定义」变量，与「皮肤 = 一组覆盖值」的定位相悖）。本段原注释误写「皮肤例外、
    #       允许引入新变量」，与契约相反（2026-10-15 订正）。实测 16 款皮肤各声明 21 个
    #       变量、越界 0 个，故本收紧零假阳性。
    tokens_file = root / "src/web/css/tokens.css"
    defined_vars: set[str] = set()
    if tokens_file.is_file():
        defined_vars = set(re.findall(r"(--qm-[\w-]+)\s*:",
                                      tokens_file.read_text(encoding="utf-8")))
    used_vars: dict[str, set[str]] = {}
    skin_declared: dict[str, set[str]] = {}      # 皮肤**声明**的变量（契约：须 ⊆ tokens 定义域）
    for css in sorted((root / "src/web/css").rglob("*.css")):
        if css.name == "tokens.css":
            continue
        body = strip_comments(css.read_text(encoding="utf-8"), "css")
        if "skins" in css.parts:
            skin_declared[css.name] = set(re.findall(r"(--qm-[\w-]+)\s*:", body))
        for m in re.finditer(r"var\(\s*(--qm-[\w-]+)\s*\)", body):
            used_vars.setdefault(css.name, set()).add(m.group(1))
    missing_vars = {
        name: sorted(vars_ - defined_vars)
        for name, vars_ in used_vars.items()
        if vars_ - defined_vars
    }
    # 皮肤**声明**的变量越界（契约：皮肤只做重新赋值，不得引入新变量名）。
    skin_extra_vars = {
        name: sorted(vars_ - defined_vars)
        for name, vars_ in skin_declared.items()
        if vars_ - defined_vars
    }
    closure_errs: list[str] = []
    if missing_vars:
        closure_errs.append("引用未定义变量：" + "; ".join(
            f"{name}:{', '.join(m[:3])}" for name, m in missing_vars.items()))
    if skin_extra_vars:
        closure_errs.append("皮肤引入新变量名：" + "; ".join(
            f"{name}:{', '.join(v[:3])}" for name, v in skin_extra_vars.items()))
    check(not closure_errs, "CSS 变量闭包 §P0-3 L4",
          "；".join(closure_errs) if closure_errs
          else "所有 --qm-* 引用均有 tokens.css 定义；皮肤亦未引入新变量名")

    skins_doc = root / "src/web/css/skins/README.md"
    check(skins_doc.is_file(), "皮肤目录契约 §P0-3 L5",
          "src/web/css/skins/ 与契约就位" if skins_doc.is_file()
          else "缺少 src/web/css/skins/README.md")

    prefs_js = root / "src/web/js/i18n/index.js"
    # V0.0.15 起的第五键 `qm.launchIcon`（快捷方式图标持久化）此前**不在守卫内** ——
    # 属盲区：删掉 `ICON_KEY` 声明无人报错。2026-10-15 据实补齐（见表 §P0-3 L6）。
    # V0.0.51@r9：`qm.genBar`（生成栏折叠态）随折叠撤销一并退场 → 5 键降为 4 键。
    PREF_KEYS = ("qm.lang", "qm.skin", "qm.inspMode", "qm.launchIcon")
    prefs_body = prefs_js.read_text(encoding="utf-8") if prefs_js.is_file() else ""
    prefs_missing = [key for key in PREF_KEYS if key not in prefs_body]
    check(not prefs_missing, "偏好键名 §P0-3 L6",
          " / ".join(PREF_KEYS) + " 齐备" if not prefs_missing
          else "i18n/index.js 缺少：" + ", ".join(prefs_missing))

    # 7d-2. 皮肤注册表与文件一一对应
    skin_errs = []
    default_cid: str | None = None      # 默认皮肤号，取自注册表 DEFAULT_SKIN_CID（§P2-15）
    skins_dir = root / "src/web/css/skins"
    reg_file = root / "src/web/js/i18n/skins.js"
    if reg_file.is_file():
        reg_text = reg_file.read_text(encoding="utf-8")
        cids = re.findall(r"cid:\s*(\d+)", reg_text)
        files = re.findall(r"file:\s*['\"]([^'\"]+)['\"]", reg_text)
        labels = re.findall(r"label:\s*['\"]([^'\"]+)['\"]", reg_text)
        if len({len(cids), len(files), len(labels)}) != 1:
            skin_errs.append("注册表字段数量不一致")
        else:
            for cid, file, label in zip(cids, files, labels):
                css = skins_dir / f"{file}.css"
                if not css.is_file():
                    skin_errs.append(f"缺少皮肤文件 {file}.css")
                if not label.startswith("skin."):
                    skin_errs.append(f"label 须为 skin.* 键：{label}")
        if "DEFAULT_SKIN_CID" in reg_text:
            m = re.search(r"DEFAULT_SKIN_CID\s*=\s*(\d+)", reg_text)
            if m:
                default_cid = m.group(1)
                prefix = f"s{default_cid.zfill(2)}-"
                if not any(f.startswith(prefix) for f in files):
                    skin_errs.append(f"默认皮肤前缀 {prefix} 未注册")
        else:
            skin_errs.append("注册表缺少 DEFAULT_SKIN_CID")
    else:
        skin_errs.append("缺少 skins.js")
    def_note = "；".join(skin_errs) if skin_errs else f"{len(cids)} 款皮肤注册表与文件一致"
    if not skin_errs and cids and default_cid is not None:
        def_note += f"，默认 S{int(default_cid):02d}"
    check(not skin_errs, "皮肤注册表 §P0-3 L5", def_note)

    # 7d-3. 皮肤注册表 swatch 与 skins/*.css **逐值一致**（V0.0.39 · §十三.4）
    #       swatch = [--qm-bg, --qm-accent, --qm-surface]；其唯一消费者是 skin-picker 的
    #       **排序键**（按背景明度亮 → 暗）。本守卫把「改了皮肤取值却忘同步 swatch」从
    #       **静默漂移**变成**立刻报错** —— 这正是 §十三.4「无绑定」的机器解法
    #       （运行时 getComputedStyle 只能读到**当前生效那一款**，拿不到其余 14 款，故
    #        绑定只能落在**校验期**而非运行期）。
    swatch_errs: list[str] = []
    swatch_n = 0
    if reg_file.is_file() and skins_dir.is_dir():
        reg_text2 = reg_file.read_text(encoding="utf-8")
        sw_pat = re.compile(
            r"file:\s*'([^']+)',\s*label:\s*'[^']+',\s*swatch:\s*\[\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\s*\]"
        )
        t_light_s, _t_dark_s = split_light_dark(
            (root / "src/web/css/tokens.css").read_text(encoding="utf-8"))
        for m in sw_pat.finditer(reg_text2):
            fname, s_bg, s_accent, s_surface = m.groups()
            swatch_n += 1
            css_path = skins_dir / f"{fname}.css"
            if not css_path.is_file():
                swatch_errs.append(f"{fname}: 缺皮肤文件，无法比对 swatch")
                continue
            eff = dict(t_light_s)
            eff.update(css_vars(css_path.read_text(encoding="utf-8")))
            for tag, sw, var in (("bg", s_bg, "--qm-bg"),
                                 ("accent", s_accent, "--qm-accent"),
                                 ("surface", s_surface, "--qm-surface")):
                want = eff.get(var)
                if want is None:
                    swatch_errs.append(f"{fname}: {var} 未定义")
                elif want.lower() != sw.lower():
                    swatch_errs.append(f"{fname}.{tag}: swatch={sw} ≠ CSS={want}")
    else:
        swatch_errs.append("缺少 skins.js 或 skins/ 目录")
    check(not swatch_errs, "皮肤 swatch 与 CSS 绑定 V0.0.39",
          "; ".join(swatch_errs[:4]) if swatch_errs
          else f"{swatch_n} 款 swatch 三色与各自 CSS 逐值一致")

    # 7d-4. 皮肤 WCAG AA 对比度（V0.0.39 · §十三.3）
    #       基座 = **无皮肤时的 tokens 浅/深两套**（README：未选皮肤即不注入样式表，
    #       故 tokens 默认值直接生效）+ **16 款皮肤**（皮肤覆盖叠在 tokens 浅色之上；
    #       款数由注册表 / 目录派生，加款即自动 +1）。
    contrast_errs: list[str] = []
    base_n = 0
    tokens_path = root / "src/web/css/tokens.css"
    if tokens_path.is_file() and skins_dir.is_dir():
        t_light_c, t_dark_c = split_light_dark(tokens_path.read_text(encoding="utf-8"))
        bases: list[tuple[str, dict[str, str]]] = [
            ("tokens·浅", t_light_c), ("tokens·深", t_dark_c),
        ]
        reg_for_bases = reg_file.read_text(encoding="utf-8") if reg_file.is_file() else ""
        for m in re.finditer(r"file:\s*'([^']+)'", reg_for_bases):
            fname = m.group(1)
            css_path = skins_dir / f"{fname}.css"
            if not css_path.is_file():
                continue
            eff = dict(t_light_c)
            eff.update(css_vars(css_path.read_text(encoding="utf-8")))
            bases.append((fname, eff))
        for label, eff in bases:
            base_n += 1
            for name, fk, bk in SKIN_TEXT_PAIRS:
                fg, bg_ = eff.get(fk, ""), eff.get(bk, "")
                r = contrast_ratio(fg, bg_)
                if r is None:
                    contrast_errs.append(f"{label}/{name}: 非字面量色值 {fg!r} / {bg_!r}")
                elif r < SKIN_CONTRAST_MIN_TEXT:
                    contrast_errs.append(f"{label}/{name}={r:.2f}<{SKIN_CONTRAST_MIN_TEXT}")
            for name, fk, bk in SKIN_NONTEXT_PAIRS:
                fg, bg_ = eff.get(fk, ""), eff.get(bk, "")
                r = contrast_ratio(fg, bg_)
                if r is None:
                    contrast_errs.append(f"{label}/{name}: 非字面量色值 {fg!r} / {bg_!r}")
                elif r < SKIN_CONTRAST_MIN_NONTEXT:
                    contrast_errs.append(f"{label}/{name}={r:.2f}<{SKIN_CONTRAST_MIN_NONTEXT}")
    else:
        contrast_errs.append("缺少 tokens.css 或 skins/ 目录")
    n_pairs = len(SKIN_TEXT_PAIRS) + len(SKIN_NONTEXT_PAIRS)
    check(not contrast_errs, "皮肤 WCAG AA 对比度 V0.0.39",
          f"{len(contrast_errs)} 处不达标：" + "; ".join(contrast_errs[:4]) if contrast_errs
          else f"{base_n} 基座 × {n_pairs} 配对（文本 ≥4.5 / 非文本 ≥3.0）全部达标")

    # 7d-5. 皮肤「只供配色 + 影色」（V0.0.45 · 形态归一）：**全部皮肤**（现 16 款，由目录
    #       派生）**不得**定义形态合成
    #       表达式。实测它们原本各自复制、**取值完全一致**（纯冗余），已于 V0.0.45 剥离并上移
    #       tokens.css（引用 --qm-shadow-* / --qm-edge-*，仍随皮肤明暗自动适配）。本守卫防
    #       「新增皮肤时又抄一份形态表达式进来」，把刚统一的「设计风格」重新拆散。
    SHAPE_VARS = ("--qm-shadow-raise", "--qm-inset")
    shape_leak: list[str] = []
    skin_files: list = []
    if skins_dir.is_dir():
        skin_files = sorted(skins_dir.glob("s*.css"))
        for css in skin_files:
            body = strip_comments(css.read_text(encoding="utf-8"), "css")
            for v in SHAPE_VARS:
                if re.search(rf"^\s*{re.escape(v)}\s*:", body, re.M):
                    shape_leak.append(f"{css.name}:{v}")
    # V0.0.50：计数改为**派生** —— 原为写死的「15 款」，加第 16 款皮肤后
    # 遍历已覆盖新皮肤、提示串却仍说 15，属「报告口径与实况不符」。
    check(not shape_leak, "皮肤只供配色影色 V0.0.45",
          "皮肤不得定义形态变量：" + ", ".join(shape_leak[:4]) if shape_leak
          else f"{len(skin_files)} 款皮肤均未定义 {' / '.join(SHAPE_VARS)}（形态唯一来源 = tokens.css）")

    # 7d-6. Soft 转基础层（V0.0.45）：三页 <html> 不得再挂 data-soft；soft.css 选择器不得再带
    #       [data-soft] 前缀；形态字面量（位移 / 模糊）必须已收敛为 var(--qm-*)。另外锚定两处
    #       **实测补丁** —— 去属性使本层特异性整体降一档（(0,2,1) → (0,1,1)），实测**仅**这两处
    #       被「其它文件带伪类的高特异性规则」反超（detail 见《错误笔记》第 67 条）。删掉即复发。
    soft_path = root / "src/web/css/soft.css"
    soft_errs: list[str] = []
    for page in ("index.html", "help.html", "support.html"):
        pg = root / "src/web" / page
        if pg.is_file() and "data-soft" in pg.read_text(encoding="utf-8"):
            soft_errs.append(f"{page} 仍挂 data-soft")
    if soft_path.is_file():
        # 先剥注释：本文件头注释里保留了「[data-soft] / 形态字面量」等历史说明文字，
        # 不剥会把说明当成违规（§三.62 一族：观测手段的盲区 / 假阳性）。
        sbody = strip_comments(soft_path.read_text(encoding="utf-8"), "css")
        if "[data-soft]" in sbody:
            soft_errs.append("soft.css 仍带 [data-soft] 前缀")
        for m in re.finditer(r"box-shadow\s*:([^;]+);", sbody):
            if re.search(r"\d+px", m.group(1)):
                soft_errs.append("soft.css 含形态字面量：" + m.group(1).strip()[:40])
                break
        for pat, name in (("html .tpl-row .tpl-item:hover", "tpl-item:hover 压制"),
                          ('html input[type="text"]:focus', "input:focus 描边")):
            if pat not in sbody:
                soft_errs.append(f"缺实测补丁：{name}")
    else:
        soft_errs.append("缺少 soft.css")
    check(not soft_errs, "Soft 转基础层 V0.0.45",
          "；".join(soft_errs[:4]) if soft_errs
          else "三页无 data-soft / soft.css 无前缀与形态字面量 / 两处实测补丁在位")

    # 7d-7. 形态语法变量齐备（V0.0.45 · 「变量切换」）：soft.css 里原本硬编码的位移 / 模糊
    #       已全部收敛为这 6 个 tokens 变量 —— 删掉任一即「形态又有了第二处出口」。
    SYNTAX_VARS = ("--qm-card-edge", "--qm-topbar-shadow", "--qm-layer-shadow",
                   "--qm-pop-shadow", "--qm-qr-shadow", "--qm-btn-edge")
    tokens_txt = (root / "src/web/css/tokens.css").read_text(encoding="utf-8") \
        if (root / "src/web/css/tokens.css").is_file() else ""
    missing_syntax = [v for v in SYNTAX_VARS if v not in tokens_txt]
    check(not missing_syntax, "形态语法变量 V0.0.45",
          "tokens.css 缺少：" + ", ".join(missing_syntax) if missing_syntax
          else f"{len(SYNTAX_VARS)} 个形态语法变量齐备（形态只有一处出口）")

    # 7d-8. 皮肤「三阶落差」统一（V0.0.46 立规 / V0.0.47 收口全域 · §十三.6 裁定 = 乙方案）。
    #       --qm-surface-2 是**填充色**，不承担凸凹语义（凸凹归 soft.css 的
    #       --qm-tap / --qm-tap-in 阴影 + 1px 描边），故它与 --qm-surface 的
    #       **CIE L\* 落差必须小**：|ΔL*| ≤ 1.5，且方向随区制 ——
    #       浅色区制为负（次级面略暗于面板）、深色区制为正（次级面略亮于面板）。
    #       V0.0.46 只覆盖 15 款皮肤；V0.0.47 起**连 tokens 浅 / 深两段一并覆盖** ——
    #       二者本就是 7d-4 的一等基座（help / support 无皮肤选择器，tokens 取值直接生效），
    #       只查皮肤会让本项的「统一」二字**被静默架空**（§十三.6 的反面教材）。
    #       实测 2026-10-15：15 款原为浅色 −0.34~−1.37（合规）/ 深色 +3.79~+5.45（**过大**），
    #       深色 4 款已收窄至 +0.89~+1.16；tokens 两段 +2.49 / +3.70 于 V0.0.47 归位。
    #       本守卫防「新增 / 修改皮肤、或调 tokens 基座时又把落差拉开」（§十三.6 机器化约定）。
    TIER_LIMIT = 1.5
    TIER_MID_L = 50.0          # L* 分界：面板 L* > 50 视为浅色区制
    tier_errs: list[str] = []
    tier_dls: list[float] = []
    _tier_light, _tier_dark = split_light_dark(tokens_txt) if tokens_txt else ({}, {})
    # 待查「配色面」= tokens 浅 / 深两段（无皮肤时的基座）+ 各款皮肤（皮肤色叠在 tokens 浅色之上）。
    # V0.0.46 只覆盖 15 款皮肤；V0.0.47 起连 tokens 浅 / 深两段一并覆盖；V0.0.50 起随 s16 增为 18 面。
    tier_faces: list[tuple[str, dict[str, str]]] = [
        ("tokens.css 浅色段", _tier_light), ("tokens.css 深色段", _tier_dark),
    ]
    if skins_dir.is_dir():
        for css in sorted(skins_dir.glob("s*.css")):
            eff_t = dict(_tier_light)
            eff_t.update(css_vars(css.read_text(encoding="utf-8")))
            tier_faces.append((css.name, eff_t))
    for face, eff_t in tier_faces:
        rs, r2 = _hex_rgb(eff_t.get("--qm-surface", "")), _hex_rgb(eff_t.get("--qm-surface-2", ""))
        if rs is None or r2 is None:
            tier_errs.append(f"{face}: surface / surface-2 非字面量色值")
            continue
        l_s, l_2 = _lstar(rel_luminance(rs)), _lstar(rel_luminance(r2))
        d_l = l_2 - l_s
        tier_dls.append(d_l)
        if abs(d_l) > TIER_LIMIT:
            tier_errs.append(f"{face}: |ΔL*|={abs(d_l):.2f} > {TIER_LIMIT}")
        elif l_s > TIER_MID_L and d_l > 0:
            tier_errs.append(f"{face}: 浅色区制 ΔL*={d_l:+.2f} 应为负")
        elif l_s <= TIER_MID_L and d_l < 0:
            tier_errs.append(f"{face}: 深色区制 ΔL*={d_l:+.2f} 应为正")
    check(not tier_errs, "皮肤三阶落差统一 V0.0.46",
          "；".join(tier_errs[:4]) if tier_errs
          else f"{len(tier_dls)} 个配色面 ΔL* {min(tier_dls):+.2f} ~ {max(tier_dls):+.2f}"
               f"（含 tokens 浅/深；|ΔL*| ≤ {TIER_LIMIT}，方向随区制）")

    # 7d-9. 皮肤文件**顶层只许 `:root` + `--qm-*` 声明**（§P0-3 L5；V0.0.51@r10 后续新增）。
    #       契约原文 = `skins/README.md` 首行「皮肤 == **一组 `--qm-*` 变量的覆盖值**，
    #       **不是一整套组件样式**」；16 / 16 款文件头亦各写「**不写组件选择器**」。
    #       **与 7d「组件 CSS 不感知皮肤」方向相反** —— 7d 管「组件不许知道皮肤存在」，
    #       本条管「皮肤不许写组件样式」；**合起来才是完整的双向隔离**。只做半边正是
    #       §P0-3 L4「只做前半句」的教训（《错误笔记》§三.81），故本项按 §P2 第 45 项
    #       的建议与 7d 成对考虑。
    #       发现方式（据实）：7c-1 反向验证的**负向对照 N6** 往皮肤追加
    #       `.rev-probe { font-size: var(--qm-fs-md); }` → **全量零新增红项** ⇒ 无人拦。
    #       现状自查（立守卫前的**前提**，同 7d-1 / 7c-1 立档做法）：16 款**各恰 1 个
    #       `:root` 块**、非 `:root` 选择器 **0 处**、非 `--qm-*` 声明 **0 处** ⇒
    #       本收紧**零假阳性**。款数由 `skins/s*.css` **派生**，加款即自动纳入。
    skin_shape_errs: list[str] = []
    if skins_dir.is_dir():
        for css in sorted(skins_dir.glob("s*.css")):
            sbody = strip_comments(css.read_text(encoding="utf-8"), "css")
            for hit in skin_toplevel_violations(sbody):
                skin_shape_errs.append(f"{css.name}:{hit}")
    check(not skin_shape_errs, "皮肤顶层只许 :root + 变量声明 §P0-3 L5",
          f"发现 {len(skin_shape_errs)} 处：{', '.join(skin_shape_errs[:4])}" if skin_shape_errs
          else f"{len(sorted(skins_dir.glob('s*.css')))} 款皮肤各恰 1 个 :root 块、声明全为 --qm-*")

    # 7e. CSS 类名形态：kebab-case，不得含下划线或大写（§P2 第 1 项）
    #     先剥掉 url(...) —— 否则 url("../assets/logo.svg") 里的 `.svg` 会被当成类名。
    CLS_NAME = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
    URL_LIKE = re.compile(r"url\([^)]*\)")
    bad_names = []
    for css in sorted((root / "src/web/css").rglob("*.css")):
        body = URL_LIKE.sub("", strip_comments(css.read_text(encoding="utf-8"), "css"))
        for m in CLS_NAME.finditer(body):
            name = m.group(1)
            if "_" in name or name.lower() != name:
                bad_names.append(f"{css.name}:{name}")
    check(not bad_names, "CSS 类名形态 §P2 第 1 项",
          f"违反 kebab-case：{', '.join(sorted(set(bad_names))[:4])}" if bad_names
          else "类名全部 kebab-case（无下划线、无大写）")

    # 7f. 体积上限（§P2 第 4 项）：src/** 合计 ≤ 640K，单文件 ≤ 64K
    #     400K → 512K（V0.0.40，用户裁决）：设计提案层（顶栏图标化 / 弹窗内嵌 /
    #     模板批处理 / 检视器双模式）是一整块**新功能层**，不是零散修补。
    #     并入软皮肤层后 src 已达 411K，本来就压线；再叠 808 行提案 CSS 与配套
    #     DOM/JS，预估峰值约 480K。放宽到 512K 既容纳该层、又保留守门本意。
    #     512K → 576K（V0.0.49，用户裁决）：V0.0.48 拆 `main.js` 模板子系统已实测
    #     「省单文件线、却花总量线」—— 搬迁挤出 18,866 B，新模块骨架净吃回 2,690 B，
    #     src 余量降至 1,081 B。两条线自此进入**互斥区**：单文件线逼你拆、总量线罚
    #     你拆；继续拆只是用「总量」换「单文件」，等于让产品停止生长（《错误笔记》§三.70）。
    #     故只抬总量、**单文件 64K 不动**（它才是「一个文件别太胖」的本意）；
    #     放宽 64K 后余量恢复约 65K，下一批（编辑态乐观锁等）不必再压缩注释。
    #     576K → 640K（V0.0.51@r9，用户裁决）：历史版本（备份取回）是一个**新功能层**
    #     —— 一对端点（GET /api/editor-backups、POST /api/editor-restore）+ 新后端模块
    #     `server/backups.py` + 弹窗模块 + 一条跨文件链守卫 + 测试。实测 +③ 前端前
    #     余量仅 2.8K，远不足容纳。抬额幅度与 V0.0.49 同幅（+64K），理由同型：新功能
    #     层、非零散修补。**单文件 64K 仍不动**。
    SRC_TOTAL_LIMIT = 640 * 1024
    SRC_FILE_LIMIT = 64 * 1024
    # 仅统计**源码**：排除运行/测试生成的编译产物（__pycache__/*.pyc）。
    # 这些产物已被 .gitignore 忽略、不进版本，计入体积上限会与「源码预算」本意相悖
    # （实测 src/server/__pycache__ 约 89K，会把 325K 的真实源码总量虚抬过 400K 上限造成误报）。
    src_files = [
        p for p in (root / "src").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]
    if not src_files:
        # 缺 src/ 必须**显式 FAIL**，而不是静默少产生一项（§P2-14）。
        check(False, "体积上限 §P2 第 4 项", f"未找到 {root / 'src'} 下任何文件（src/ 缺失？）")
    else:
        total_bytes = sum(p.stat().st_size for p in src_files)
        oversize = [f"{p.relative_to(root)}（{p.stat().st_size // 1024}K）"
                    for p in src_files if p.stat().st_size > SRC_FILE_LIMIT]
        budget_ok = total_bytes <= SRC_TOTAL_LIMIT and not oversize
        check(budget_ok, "体积上限 §P2 第 4 项",
              f"{total_bytes // 1024}K / 上限 {SRC_TOTAL_LIMIT // 1024}K" +
              (f"；超限单文件：{', '.join(oversize)}" if oversize else "；单文件均在 64K 内"))

    # 7g. 帮助页键位登记（§P2 第 8 项）：源码若有修饰键快捷键监听，
    #     帮助页键位小节必须登记至少一条**具体键位**，不得只留"待定 / 留空"占位。
    #     背景：「本表暂留空」是**会被代码沉默推翻**的断言 —— Ctrl/Cmd+S 自 V0.0.2 起
    #     即在 main.js 中生效，该文案却一路带过 V0.0.2–V0.0.6 五个版本无人发现
    #     （《错误笔记》§三.27 / §三.30）。本守卫把这类断言变成**可被机器推翻**的。
    MOD_KEY = re.compile(r"\b(?:ctrlKey|metaKey|altKey)\b")
    shortcut_sites: list[str] = []
    for js in sorted((root / "src/web/js").rglob("*.js")):
        if "i18n" in js.parts:
            continue
        body = strip_comments(js.read_text(encoding="utf-8"), "js")
        for lineno, line in enumerate(body.splitlines(), 1):
            if MOD_KEY.search(line):
                shortcut_sites.append(f"{js.name}:{lineno}")
    # 键位小节的登记项 = zh-CN.js 中 `id: 'kbd'` 那条的 items 列表
    KBD_SECTION = re.compile(r"id:\s*'kbd'[^\n}]*items:\s*\[([^\]]*)\]")
    kbd_items: list[str] = []
    if dict_file.is_file():
        if m := KBD_SECTION.search(dict_file.read_text(encoding="utf-8")):
            kbd_items = re.findall(r"'([^']+)'", m.group(1))
    kbd_real = [k for k in kbd_items if k != "help.kbd.pending"]
    if not shortcut_sites:
        check(True, "帮助页键位登记 §P2 第 8 项", "源码无修饰键快捷键监听，跳过")
    elif not kbd_items:
        check(False, "帮助页键位登记 §P2 第 8 项",
              "未在 zh-CN.js 中定位到键位小节（`id: 'kbd'` 的 items）")
    elif kbd_real:
        check(True, "帮助页键位登记 §P2 第 8 项",
              f"源码 {len(shortcut_sites)} 处修饰键监听 → 已登记 {len(kbd_real)} 项："
              + ", ".join(kbd_real))
    else:
        check(False, "帮助页键位登记 §P2 第 8 项",
              f"源码有 {len(shortcut_sites)} 处修饰键监听（{shortcut_sites[0]} 等），"
              "但帮助页键位小节只剩 help.kbd.pending 占位 —— 键位存在却未登记")

    # 7h. 帮助页版本号兜底不得漂移（§P0-3 L1）
    #     背景：`help.versionFallback` 自 V0.0.5 起被写死，一路带到 V0.0.9 无人发现 ——
    #     后端离线时帮助页会向用户显示**错误的版本号**，而静态校验看不见。
    #     判据：zh-CN.js / en-US.js 中该键的值必须等于项目根 VERSION 文件的内容。
    version_file = root / "VERSION"
    VFB = re.compile(r"'help\.versionFallback'\s*:\s*'([^']*)'")
    if not version_file.is_file():
        check(True, "版本兜底一致 §P0-3 L1", "无 VERSION 文件（预览目录），跳过")
    else:
        want = version_file.read_text(encoding="utf-8").strip()
        got: dict[str, str] = {}
        for name in ("zh-CN.js", "en-US.js"):
            p = root / "src/web/locales" / name
            if p.is_file():
                if m := VFB.search(p.read_text(encoding="utf-8")):
                    got[name] = m.group(1)
        stale = [f"{n}={v}" for n, v in sorted(got.items()) if v != want]
        missing = [n for n in ("zh-CN.js", "en-US.js") if n not in got]
        if missing:
            check(False, "版本兜底一致 §P0-3 L1",
                  "未找到 help.versionFallback：" + ", ".join(missing))
        elif stale:
            check(False, "版本兜底一致 §P0-3 L1",
                  f"VERSION={want}，取词表写死为 " + " / ".join(stale)
                  + " —— 后端离线时帮助页会显示错误版本")
        else:
            check(True, "版本兜底一致 §P0-3 L1",
                  f"两份取词表与 VERSION 均为 {want}")

    # 7i. 默认皮肤不可缺省（§P0-3 L5）
    #     背景：applySkin() 曾在 `qm.skin` 为空时**不注入任何样式表**，而选择器显示的是
    #     默认皮肤名 —— 首次启动「下拉写着 S06、界面却是裸色」，用户裁定的默认皮肤从未生效。
    #     判据：i18n/index.js 必须引用 DEFAULT_SKIN_CID（否则无偏好时无从装载出厂默认）。
    prefs_i18n = root / "src/web/js/i18n/index.js"
    body_i18n = prefs_i18n.read_text(encoding="utf-8") if prefs_i18n.is_file() else ""
    if not body_i18n:
        check(False, "默认皮肤不可缺省 §P0-3 L5", "缺少 src/web/js/i18n/index.js")
    elif "DEFAULT_SKIN_CID" not in body_i18n:
        check(False, "默认皮肤不可缺省 §P0-3 L5",
              "i18n/index.js 未引用 DEFAULT_SKIN_CID —— 未选皮肤时会退化为「无皮肤」裸色，"
              "与选择器显示的默认皮肤不一致")
    else:
        check(True, "默认皮肤不可缺省 §P0-3 L5",
              "i18n/index.js 已接线出厂默认皮肤，未选过时装载默认皮肤而非裸色")

    # 7j. 模板保存契约（§P2 第 7 项 · V0.0.13「另存为模板」）
    #     背景：模板库长期只读，顶层一直没有 schemaVersion；一旦开始**写**模板，
    #     就必须带上版本戳 —— 否则日后无法区分新旧格式（这是 §P2 第 7 项当时留的重议条件）。
    #     判据两端：① 写入必带 schemaVersion；② 读取容忍缺失（老模板无该字段，视为 v1）。
    #     判据只认「save_template 函数体里真的写了 schemaVersion」—— 用 ast 取函数体，
    #     否则 `list_templates` 里的同名字面量会让守卫在删掉写入后照样通过（反向实证抓到过）。
    tpl_anchors = (
        ("src/server/app.py", "routes.save_template(payload)"),
        ("src/server/config.py", "TEMPLATE_MAX_BYTES"),
        ("src/web/js/core/api.js", "saveTemplate"),
    )
    tpl_absent: list[str] = []
    for rel, token in tpl_anchors:
        target = root / rel
        if not target.is_file() or token not in target.read_text(encoding="utf-8"):
            tpl_absent.append(f"{rel}:{token}")

    routes_py = root / "src/server/routes.py"
    bodies: dict[str, str] = {}
    funcs: dict[str, ast.FunctionDef] = {}
    if not routes_py.is_file():
        tpl_absent.append("routes.py:未读到")
    else:
        rtext = routes_py.read_text(encoding="utf-8")
        rlines = rtext.splitlines()
        try:
            rtree = ast.parse(rtext)
        except SyntaxError:
            tpl_absent.append("routes.py:无法解析")
            rtree = None
        if rtree is not None:
            for node in ast.walk(rtree):
                if isinstance(node, ast.FunctionDef) and node.name in ("save_template", "load_template"):
                    funcs[node.name] = node
                    bodies[node.name] = "\n".join(
                        rlines[node.lineno - 1:(node.end_lineno or node.lineno)])
    for fn in ("save_template", "load_template"):
        if fn not in bodies:
            tpl_absent.append(f"routes.py:缺少 {fn}")

    def dict_key_sets(node: ast.FunctionDef | None) -> list[set[str]]:
        """函数体内每个字典字面量的**常量键集合**。"""
        out: list[set[str]] = []
        if node is None:
            return out
        for sub in ast.walk(node):
            if isinstance(sub, ast.Dict):
                out.append({k.value for k in sub.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)})
        return out

    # 落盘载荷 = 同时含 tree 与 schemaVersion 的那个字典。
    # 只查「有没有 schemaVersion 字样」不够 —— 返回值里也有同名字段，
    # 删掉写入照样蒙混过关（反向实证抓到过）。
    payload_ok = any({"schemaVersion", "tree"} <= keys
                     for keys in dict_key_sets(funcs.get("save_template")))
    if not payload_ok:
        tpl_absent.append("save_template 落盘载荷未带 schemaVersion")
    if 'get("schemaVersion"' not in bodies.get("load_template", ""):
        tpl_absent.append("load_template 未容忍 schemaVersion 缺失")
    if "templateExists" not in bodies.get("save_template", ""):
        tpl_absent.append("save_template 未拒绝覆盖同名")
    codes_file = root / "src/shared/error-codes.json"
    try:
        tpl_codes = json.loads(codes_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tpl_codes = {}
    for code in ("templateNameEmpty", "templateExists", "templateTooManyNodes",
                 "templateTooLarge", "templateWriteFailed"):
        if code not in tpl_codes:
            tpl_absent.append(f"error-codes.json:{code}")
    try:
        tpl_schema = json.loads((root / "src/shared/schema.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tpl_schema = {}
    if not isinstance(tpl_schema.get("template"), dict) or "schemaVersion" not in tpl_schema["template"]:
        tpl_absent.append("schema.json:template.schemaVersion")
    check(not tpl_absent, "模板保存契约 §P2 第 7 项",
          f"缺失：{', '.join(tpl_absent)}" if tpl_absent
          else "写入带 schemaVersion / 读取容忍缺失 / 拒绝覆盖同名 / 规模与体积上限 齐备")

    # 7k. OS 语言注入（V0.0.14：「跟随系统」跟的是**操作系统语言**，不是浏览器语言）
    #     ① 浏览器语言可被单独改写，不等于系统显示语言 —— 真值只能问 OS；
    #     ② 必须**同步注入**（`<script src>` 早于 module 脚本），否则首屏会先按浏览器
    #        语言画一遍、拿到结果后再跳变（语言闪烁）。两处缺一即失去意义。
    os_bad: list[str] = []
    routes_py = root / "src/server/routes.py"
    rtext2 = routes_py.read_text(encoding="utf-8") if routes_py.is_file() else ""
    for token in ("def env_script", "GetUserDefaultLocaleName"):
        if token not in rtext2:
            os_bad.append(f"routes.py:{token}")
    app_py = root / "src/server/app.py"
    if not app_py.is_file() or "routes.ENV_PATH" not in app_py.read_text(encoding="utf-8"):
        os_bad.append("app.py:routes.ENV_PATH")
    i18n_js = root / "src/web/js/i18n/index.js"
    itext = i18n_js.read_text(encoding="utf-8") if i18n_js.is_file() else ""
    if "__QM_OS_LOCALE__" not in itext:
        os_bad.append("i18n/index.js:__QM_OS_LOCALE__")
    if m := re.search(r"function systemLocales\(\).*?\n\}", itext, flags=re.S):
        body = m.group(0)
        i_os, i_nav = body.find("osLocale()"), body.find("navigator")
        if i_os < 0 or i_nav < 0 or i_os > i_nav:
            os_bad.append("systemLocales 未让 OS 语言优先于浏览器语言")
    else:
        os_bad.append("i18n/index.js:缺 systemLocales")
    for page in ("src/web/index.html", "src/web/help.html", "src/web/support.html"):
        page_file = root / page
        text = page_file.read_text(encoding="utf-8") if page_file.is_file() else ""
        i_env, i_mod = text.find("./api/env.js"), text.find('type="module"')
        name = Path(page).name
        if i_env < 0:
            os_bad.append(f"{name}:未引入 env.js")
        elif i_mod < 0 or i_env > i_mod:
            os_bad.append(f"{name}:env.js 未早于 module 脚本")
    check(not os_bad, "OS 语言注入（跟随系统）",
          f"缺失：{', '.join(os_bad)}" if os_bad
          else "后端取 OS 语言 + env.js 同步注入 + OS 优先于浏览器 齐备")

    # 7l. 快捷方式图标契约（V0.0.15 · 皮肤联动桌面图标）
    #     判据用 AST 钉函数体（字面量锚点会被同名字段蒙混 —— 模板契约守卫的教训）：
    #     ① _lnk_script 必须真的拼 IconLocation（否则删掉图标接线后守卫照过）；
    #     ② create_shortcut 必须调用 save_launch_icon 且落盘后刷新缓存；
    #     ③ save_launch_icon 落盘前必须过 validate_ico（结构校验不得绕过）。
    icon_bad: list[str] = []
    icon_anchors = (
        ("src/server/config.py", "ICON_FILE"),
        ("src/server/routes.py", "ICON_PATH"),
        ("src/server/app.py", "routes.ICON_PATH"),
        ("src/web/js/core/api.js", "saveLaunchIcon"),
        ("src/web/js/ui/launch-icon.js", "buildIco"),
        ("src/web/js/main.js", "qmskinchange"),
        ("src/web/js/i18n/index.js", "qmskinchange"),
    )
    for rel, token in icon_anchors:
        target = root / rel
        if not target.is_file() or token not in target.read_text(encoding="utf-8"):
            icon_bad.append(f"{rel}:{token}")
    if routes_py.is_file():
        try:
            itree = ast.parse(routes_py.read_text(encoding="utf-8"))
        except SyntaxError:
            itree = None
            icon_bad.append("routes.py:无法解析")
        if itree is not None:
            fn_bodies: dict[str, str] = {}
            for node in ast.walk(itree):
                if isinstance(node, ast.FunctionDef) and node.name in (
                    "_lnk_script", "create_shortcut", "save_launch_icon", "validate_ico"
                ):
                    fn_bodies[node.name] = ast.get_source_segment(
                        routes_py.read_text(encoding="utf-8"), node) or ""
            if "IconLocation" not in fn_bodies.get("_lnk_script", ""):
                icon_bad.append("_lnk_script 未拼 IconLocation")
            cs = fn_bodies.get("create_shortcut", "")
            if "save_launch_icon" not in cs:
                icon_bad.append("create_shortcut 未串联图标落盘")
            if "_refresh_icon_cache" not in cs:
                icon_bad.append("create_shortcut 未刷新图标缓存")
            sl = fn_bodies.get("save_launch_icon", "")
            if "validate_ico" not in sl:
                icon_bad.append("save_launch_icon 未过 validate_ico")
            if "os.replace" not in sl:
                icon_bad.append("save_launch_icon 未原子替换")
            if "IEND" not in fn_bodies.get("validate_ico", ""):
                icon_bad.append("validate_ico 未校验 PNG 帧完整性")
    codes_file = root / "src/shared/error-codes.json"
    try:
        icon_codes = json.loads(codes_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        icon_codes = {}
    for code in ("iconDataMissing", "iconInvalid", "iconTooLarge", "iconWriteFailed"):
        if code not in icon_codes:
            icon_bad.append(f"error-codes.json:{code}")
    check(not icon_bad, "快捷方式图标契约 V0.0.15",
          f"缺失：{', '.join(icon_bad)}" if icon_bad
          else "IconLocation / 落盘串联 / validate_ico / 缓存刷新 / 错误码 齐备")

    # 7ak. 「打开目录」端点接线（V0.0.51@r7 · 服务设置补全，手册 §10.2 #3）。
    #      为何值得单列一条守卫：这条链**跨六处**（常量定位 → POST 允许清单 → 分发 →
    #      前端 API 封装 → 前端接线 → 错误码），而断链的后果是**静默的** —— 点按钮
    #      毫无反应，静态检查却照绿（脚本能跑、体积不超、i18n 齐备、id 都在）。
    #      故把「链」本身钉住：任一处被删或改名，本条即红。
    #      @r8 追加两锚点：① `recheckService`（无轮询缺口的手动补丁 → 自动复查）；
    #      ② `openServiceDir('templates')` —— 换靶后**前端必须指向合规标识**：
    #      写成 `'project'` 后端也照收（白名单里有），错靶不会被任何一端报错拦下。
    opendir_bad: list[str] = []
    for rel, token in (
        ("src/server/routes.py", "OPEN_DIR_PATH"),
        ("src/server/routes.py", "def open_directory"),
        ("src/server/routes.py", "NO_GUI_OPEN_ENV"),
        ("src/server/app.py", "is_open_dir"),
        ("src/server/app.py", "routes.open_directory(payload)"),
        ("src/web/js/core/api.js", "openDir(target)"),
        ("src/web/js/main.js", "openServiceDir"),
        ("src/web/js/main.js", "openServiceDir('templates')"),
        ("src/web/js/main.js", "recheckService"),
        ("src/shared/error-codes.json", "openDirBadTarget"),
    ):
        p = root / rel
        if not p.is_file() or token not in p.read_text(encoding="utf-8"):
            opendir_bad.append(f"{rel}:{token}")
    check(not opendir_bad, "「打开目录」端点接线",
          f"缺失：{', '.join(opendir_bad)}" if opendir_bad
          else "常量 / 允许清单 / 分发 / 前端封装 / 接线 / 错误码 六处齐备")

    # 7al. 「历史版本」端点接线（V0.0.51@r9 · 备份取回）。
    #      与 7ak 同因单列：链跨**七处**（后端模块常量 → 枚举 → 恢复 → 分发两处 →
    #      前端封装 → 前端接线 → 错误码），断链后果同样是静默的 —— 按钮点下去毫无
    #      反应，而静态检查照绿。特别钉住三条**语义**锚点（不是普通引用）：
    #        ① `routes.save_editor` —— 恢复**刻意复用保存路径**，于是自动获得
    #           「恢复前那版先进 .bak」与「结构校验/原子替换不漂移」两条正确性；
    #           若有人重写成自建写盘，本条即红（那会是静默的语义倒退）。
    #        ② `_iter_editor_backups()` 被恢复端点**二次调用做白名单比对** ——
    #           换成直接拼路径就会绕过白名单，是路径穿越的入口。
    #        ③ 前端 `backups.open()` —— 打开弹窗必须真的去拉列表。
    history_bad: list[str] = []
    for rel, token in (
        ("src/server/backups.py", "EDITOR_BACKUPS_PATH"),
        ("src/server/backups.py", "EDITOR_RESTORE_PATH"),
        ("src/server/backups.py", "def list_editor_backups"),
        ("src/server/backups.py", "def restore_editor"),
        ("src/server/backups.py", "routes.save_editor"),          # ① 复用保存路径
        ("src/server/backups.py", "for bid, _stamp, path in _iter_editor_backups()"),  # ② 白名单比对
        ("src/server/app.py", "backups.EDITOR_BACKUPS_PATH"),
        ("src/server/app.py", "backups.EDITOR_RESTORE_PATH"),
        ("src/server/app.py", "backups.list_editor_backups()"),
        ("src/server/app.py", "backups.restore_editor(payload)"),
        ("src/web/js/core/api.js", "listEditorBackups()"),
        ("src/web/js/core/api.js", "restoreEditor(id)"),
        ("src/web/js/main.js", "createBackups"),
        ("src/web/js/main.js", "backups.open()"),                  # ③ 开窗真去拉列表
        ("src/web/index.html", 'id="btnBackups"'),
        ("src/web/index.html", 'id="bakList"'),
        ("src/shared/error-codes.json", "editorBackupNotFound"),
    ):
        p = root / rel
        if not p.is_file() or token not in p.read_text(encoding="utf-8"):
            history_bad.append(f"{rel}:{token}")
    check(not history_bad, "「历史版本」端点接线",
          f"缺失：{', '.join(history_bad)}" if history_bad
          else "常量 / 枚举 / 恢复（复用 save_editor）/ 分发 / 前端封装 / 接线 / 错误码 齐备")

    # 7m. 服务状态三态（V0.0.16：左栏自检收敛为顶栏「服务状态」三态）
    #     判据三端：① 左栏 checklist 已移除（页面不再有该清单元素）；
    #     ② 顶栏接线三态（#chipBackend + .is-offline + setServiceState，V0.0.40 由
    #        只读 chip 升级为可点按钮，故以 chipBackend / is-offline 替下旧的类常量名）；
    #     ③ 三态取词键齐备。防「删了清单却忘了接线三态」或反向回归。
    svc_bad: list[str] = []
    idx_html = root / "src/web/index.html"
    ihtml = idx_html.read_text(encoding="utf-8") if idx_html.is_file() else ""
    if 'id="checklist"' in ihtml:
        svc_bad.append("index.html 仍含 checklist")
    mjs = root / "src/web/js/main.js"
    mtext = mjs.read_text(encoding="utf-8") if mjs.is_file() else ""
    for token in ("chipBackend", "is-offline", "setServiceState"):
        if token not in mtext:
            svc_bad.append(f"main.js:{token}")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        t = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("topbar.backend.connecting", "topbar.backend.ready", "topbar.backend.offline"):
            if k not in t:
                svc_bad.append(f"{name}:{k}")
    check(not svc_bad, "服务状态三态 V0.0.16",
          f"缺失：{', '.join(svc_bad)}" if svc_bad
          else "左栏清单已移除 / 顶栏三态接线 / 三态取词键齐备")

    # 7am. 顶栏状态区契约（V0.0.53）：两个状态读数都改成**纯图标**之后的接线判据。
    #      为什么需要它：文字一旦退场，「状态」就搬进了**图标 / 颜色 / aria-label** 三样
    #      **不会报错**的东西里 —— 它们被顺手删掉时页面照常渲染，只是信息没了。
    #      五条判据与两侧口径（含「④ 必须锚 `data-i18n=` 带等号、三个入参一律先剥注释」）
    #      全部写在模块级 `status_chip_violations()` 的 docstring 里 —— 提到模块级
    #      是为了能被单测锚住（`tests/test_verify.py::StatusChipTests`）。
    #      ⚠ 这里**不能**用本文件后文的 `_read()` —— 它是 main() 内、7x 段才定义的闭包，
    #        在本行位置还是未绑定名字（实测：`UnboundLocalError`）。故直接读盘。
    _lay_file = root / "src/web/css/layout.css"
    status_bad = status_chip_violations(
        ihtml, mtext,
        _lay_file.read_text(encoding="utf-8") if _lay_file.is_file() else "")
    check(not status_bad, "顶栏状态区契约 V0.0.53",
          "；".join(status_bad) if status_bad
          else "文字形态已退场 / 状态点与下三角齐备 / aria-label 有出口 / 图标不与 i18n 抢位 / 动效有退出")

    # 7an. 帮助页文案无 Markdown 标记（V0.0.53@r2）。
    #      两个渲染器（help.js / help-doc.js）都不解析 Markdown ⇒ 文案里的 `**` / 反引号 /
    #      `~~` / `[文字](链接)` 会**原样上屏**。不崩、不报错，只是看着像乱码，故只能靠机器盯。
    #      判据与三条口径（先剥注释 / 只查 help.* / 抽取式失效即报红）见模块级
    #      `help_markdown_violations()` 的 docstring（提到模块级才能被单测锚住）。
    #      ⚠ 同 7am：此处不可用后文 main() 内的 `_read()` 闭包，直接读盘。
    _md_bad: list[str] = []
    for _rel, _label in (("src/web/locales/zh-CN.js", "zh-CN"),
                         ("src/web/locales/en-US.js", "en-US")):
        _f = root / _rel
        if not _f.is_file():
            _md_bad.append(f"{_rel} 不存在")
            continue
        _md_bad += help_markdown_violations(_f.read_text(encoding="utf-8"), _label)
    check(not _md_bad, "帮助页文案无 Markdown 标记 V0.0.53@r2",
          "；".join(_md_bad) if _md_bad
          else "两包 help.* 全为纯文本 —— 无粗体 / 反引号 / 删除线 / 链接残留")

    # 7ao. 清单元数据契约（V0.0.53）：**日期只进元数据、不进版本号**。
    #      三条判据与口径见模块级 `manifest_meta_violations()` 的 docstring。
    #      覆盖面＝**全部存量清单**而不只是最新那份 —— 历史清单被手改同样要在意
    #      （这正是本仓「只查最新 = 只守一半」的老毛病，§三.87 同族）。
    _meta_bad: list[str] = []
    _vers_dir = root / "versions"
    _manifests = sorted(_vers_dir.rglob("MANIFEST*.json")) if _vers_dir.is_dir() else []
    if not _manifests:
        _meta_bad.append("未找到任何 MANIFEST*.json（store 尚未建立基线？）")
    for _mf in _manifests:
        try:
            _m = json.loads(_mf.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _meta_bad.append(f"{_mf.relative_to(root).as_posix()} 读不成 JSON：{exc}")
            continue
        _meta_bad += manifest_meta_violations(_m, _mf.relative_to(root).as_posix())
    check(not _meta_bad, "清单元数据契约 V0.0.53",
          "；".join(_meta_bad[:4]) if _meta_bad
          else f"{len(_manifests)} 份清单：版本号纯 SemVer / 时间写法已登记 / build 字段白名单")

    # 7ap. 版本—清单双层契约（§P0-6 M10）：版本号只答兼容性，构建事实全在根 manifest.json。
    #      判定本体走 `manifest.validate()` —— 与 CLI `manifest.py check` **同源**。
    #      两处各写一份判定是本仓反复踩过的病（§P2 第 19 项：判定逻辑必须单一来源）。
    _mf_bad: list[str] = []
    _mf_doc = None
    if not (root / manifest.FILENAME).is_file():
        _mf_bad.append(f"缺 {manifest.FILENAME}（第二层未建立；"
                       f"用 `python tools/manifest.py stamp` 建档）")
    else:
        try:
            _mf_doc = manifest.load(root)
        except (OSError, ValueError) as exc:
            _mf_bad.append(f"{manifest.FILENAME} 读不成 JSON：{exc}")
    if _mf_doc is not None:
        _mf_latest = latest_revision(root, version_text) if version_text else None
        _mf_known = {p.name for p in (root / "versions").iterdir() if p.is_dir()} \
            if (root / "versions").is_dir() else set()
        _mf_day = manifest.store_day(root, version_text, _mf_latest) if _mf_latest else ""
        _mf_bad += manifest.validate(_mf_doc, version_text, _mf_latest, _mf_known, _mf_day)
    check(not _mf_bad, "版本—清单双层契约 §P0-6 M10",
          "；".join(_mf_bad[:4]) if _mf_bad
          else f"version={version_text} 与清单一致 · 当前修订有构建记录 · 模型/工具链已登记")

    # 7aq. 版本号形态与单调性（SemVer 2.0.0 §2）：`versions/` 的**目录名**是版本号的
    #      另一半身份证 —— 7ao 只查清单内部字段，查不到「目录被改名 / 清单被错位复制」。
    #      父链判据：数值排序后第 i 个版本的 r1 清单 `parent` 必须是第 i-1 个版本。
    #      这条把「版本号序列」本身变成可验证对象：手工塞一个目录进来，链条立刻断。
    _vdirs = [p for p in (root / "versions").iterdir() if p.is_dir()] \
        if (root / "versions").is_dir() else []
    _ver_bad = version_dir_violations(root)
    check(not _ver_bad, "版本号形态与单调性",
          "；".join(_ver_bad[:4]) if _ver_bad
          else f"{len(_vdirs)} 个版本目录：三段式无前导零 / 目录名与清单一致 / 父链连续")

    # 7n. note 契约与 .md 边界（V0.0.17：节点说明 + 三粒度复制）
    #     裁定：note 与 .md content 一律**纯文本** —— 工具不解析、不渲染、不校验 Markdown。
    #     判据：① note 序列化两端（toDocumentNode / fromDocumentNode）都在函数体里带 note
    #     （AST 钉函数体，防字面量蒙混）；② 属性栏 textarea 纯文本（不用 innerHTML 渲染 note）；
    #     ③ toPlainTree 不含 note（note 不参与生成落盘）。
    note_bad: list[str] = []
    for rel, token in (
        ("src/web/index.html", 'id="propNote"'),
        ("src/web/js/modules/templates.js", "adoptTemplateNote"),  # V0.0.48 随 applyTemplate 迁出
        ("src/web/js/main.js", "btnCopyNote"),
        ("src/shared/schema.json", '"note"'),
    ):
        target = root / rel
        if not target.is_file() or token not in target.read_text(encoding="utf-8"):
            note_bad.append(f"{rel}:{token}")
    # routes.py 不感知 note（note 不出前端，契约层零后端改动）—— 无判据
    tm = root / "src/web/js/modules/tree-model.js"
    tmtext = tm.read_text(encoding="utf-8") if tm.is_file() else ""
    for fn in ("toDocumentNode", "fromDocumentNode"):
        m = re.search(rf"export function {fn}\(.*?\n\}}", tmtext, flags=re.S)
        if not m or "note" not in m.group(0):
            note_bad.append(f"tree-model.js:{fn} 未带 note")
    m = re.search(r"export function toPlainTree\(.*?\n\}", tmtext, flags=re.S)
    if not m:
        note_bad.append("tree-model.js:缺 toPlainTree")
    elif re.search(r"\bnote\b", m.group(0)):
        note_bad.append("toPlainTree 不应含 note（note 不参与生成落盘）")
    ins = root / "src/web/js/ui/inspector.js"
    itext = ins.read_text(encoding="utf-8") if ins.is_file() else ""
    if re.search(r"innerHTML", itext):
        note_bad.append("inspector.js 用了 innerHTML（note 须纯文本）")
    check(not note_bad, "note 契约与 .md 边界 V0.0.17",
          f"缺失：{', '.join(note_bad)}" if note_bad
          else "note 序列化往返 / 模板提炼 / 三粒度复制 / 纯文本边界（无 innerHTML、生成不含 note） 齐备")

    # 7o. 帮助/支持拆两页（V0.0.18）：支持=独立页，帮助=纯使用说明
    #     判据：① helpSections 中英两份都不再含 support 分节；② support.html/js 仍存在；
    #     ③ 互链齐备（help.js about 表跳转 ./support.html + 主界面支持入口）。
    #     V0.0.40（§10.2 #9）：主界面的支持入口由「新标签打开 support.html」改为**应用内弹窗**
    #     （#dlgSupport），故判据③的主界面一侧改钉 dlgSupport；support.html 作为独立页保留，
    #     仍由 help.html 的 about 表可达（判据第三条不变）。取词键闭包由 7b-2 统一覆盖。
    split_bad: list[str] = []
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if re.search(r"\{\s*id:\s*'support'", text):
            split_bad.append(f"{name}:helpSections 仍含 support 分节")
        for k in ("support.titleTag", "support.docTitle", "support.back", "support.toHelp",
                  "help.support.goto"):
            if k not in text:
                split_bad.append(f"{name}:{k}")
    mjs18 = root / "src/web/js/main.js"
    m18 = mjs18.read_text(encoding="utf-8") if mjs18.is_file() else ""
    if "dlgSupport" not in m18:
        split_bad.append("main.js 缺应用内支持弹窗 dlgSupport")
    if "'help.html#support'" in m18:
        split_bad.append("main.js 仍用旧锚点 #support")
    hj = root / "src/web/js/help.js"
    h18 = hj.read_text(encoding="utf-8") if hj.is_file() else ""
    if "./support.html" not in h18:
        split_bad.append("help.js 缺 about 表跳转链接")
    zc18 = root / "src/web/locales/zh-CN.js"
    z18 = zc18.read_text(encoding="utf-8") if zc18.is_file() else ""
    if re.search(r"kind:\s*'support'", z18):
        split_bad.append("zh-CN.js 仍注册 support 渲染分支")
    check(not split_bad, "帮助支持拆两页 V0.0.18",
          f"缺失：{', '.join(split_bad)}" if split_bad
          else "help 无 support 分节 / support 页接线 / about 表互链 齐备")

    # 7p. 树交互增强（V0.0.19）：拖拽移动 + 右键菜单 + Delete/F2 快捷键
    #     判据：① 模型层 moveNode 带防环与同名拦截（AST 钉函数体，防字面量蒙混）；
    #     ② 视图层接线 dragstart/dragover/drop/contextmenu；③ main.js 有 canMove 前置校验
    #     （保证 pushHistory 快照在改动前）+ 菜单动作复用 doAddChild/doRename/doDelete；
    #     ④ Delete / F2 键位在 keydown 内接线；⑤ 键位表已登记两键；⑥ 右键菜单容器存在。
    interact_bad: list[str] = []
    tm19 = root / "src/web/js/modules/tree-model.js"
    t19 = tm19.read_text(encoding="utf-8") if tm19.is_file() else ""
    m = re.search(r"export function moveNode\(.*?\n\}", t19, flags=re.S)
    if not m:
        interact_bad.append("tree-model.js:缺 moveNode")
    else:
        body = m.group(0)
        if "canMove" not in body:
            interact_bad.append("moveNode 未复用 canMove（校验单一来源）")
    m = re.search(r"export function canMove\(.*?\n\}", t19, flags=re.S)
    if not m:
        interact_bad.append("tree-model.js:缺 canMove")
    else:
        body = m.group(0)
        for token, why in (("isSelfOrDescendant", "缺防环"), ("hasSiblingName", "缺同名拦截")):
            if token not in body:
                interact_bad.append(f"canMove {why}")
    tv = root / "src/web/js/ui/tree-view.js"
    v19 = tv.read_text(encoding="utf-8") if tv.is_file() else ""
    for token in ("'dragstart'", "'dragover'", "'drop'", "'contextmenu'", "draggable"):
        if token not in v19:
            interact_bad.append(f"tree-view.js 缺 {token}")
    cm = root / "src/web/js/ui/ctx-menu.js"
    if not cm.is_file():
        interact_bad.append("缺 ui/ctx-menu.js")
    mjs19 = root / "src/web/js/main.js"
    m19 = mjs19.read_text(encoding="utf-8") if mjs19.is_file() else ""
    for token, why in (
        ("canMove(", "缺拖拽前置校验"),
        ("moveNode(", "缺移动接线"),
        ("createContextMenu", "缺右键菜单接线"),
        ("doAddChild", "缺菜单复用的新建函数"),
        ("event.key === 'Delete'", "缺 Delete 键接线"),
        ("event.key === 'F2'", "缺 F2 键接线"),
    ):
        if token not in m19:
            interact_bad.append(why)
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("help.kbd.delete", "help.kbd.rename", "tree.copyPath", "status.moved"):
            if k not in text:
                interact_bad.append(f"{name}:{k}")
    idx19 = root / "src/web/index.html"
    i19 = idx19.read_text(encoding="utf-8") if idx19.is_file() else ""
    if 'id="ctxMenu"' not in i19:
        interact_bad.append("index.html 缺 ctxMenu 容器")
    check(not interact_bad, "树交互增强 V0.0.19",
          f"缺失：{', '.join(interact_bad)}" if interact_bad
          else "moveNode 防环/同名 / 拖拽与右键接线 / Delete-F2 键位与登记 齐备")

    # 7q. 模板 CRUD 补全 + note 编辑会话（V0.0.20）
    #     判据：① 后端 delete_template / rename_template 存在，且删除是**软删除**
    #     （走 .trash，不真删 —— 项目总原则「只复制不删除」）；② 路径校验复用
    #     `_template_path_or_raise`（白名单 + is_within 单一来源）；③ app.py 有 do_DELETE
    #     与重命名子路径分发；④ 前端 api 有 rename/delete 且列表项有操作按钮接线；
    #     ⑤ note 编辑按**会话**入栈（`noteHistoryId`）而非每次输入；⑥ 错误码登记齐备。
    crud_bad: list[str] = []
    rt = root / "src/server/routes.py"
    rtext = rt.read_text(encoding="utf-8") if rt.is_file() else ""
    for fn in ("delete_template", "rename_template", "_template_path_or_raise"):
        if not re.search(rf"def {fn}\(", rtext):
            crud_bad.append(f"routes.py:缺 {fn}")
    m = re.search(r"def delete_template\(.*?\n    return", rtext, flags=re.S)
    if not m:
        crud_bad.append("routes.py:delete_template 体不可解析")
    elif not re.search(r"TEMPLATE_TRASH_DIRNAME|trash", m.group(0)):
        crud_bad.append("delete_template 未走回收站（应软删除）")
    if re.search(r"\.unlink\(|os\.remove\(", rtext):
        crud_bad.append("routes.py 出现真删除（unlink/remove），违反「只复制不删除」")
    ap = root / "src/server/app.py"
    atext = ap.read_text(encoding="utf-8") if ap.is_file() else ""
    if "def do_DELETE(" not in atext:
        crud_bad.append("app.py:缺 do_DELETE")
    if "routes.rename_template" not in atext:
        crud_bad.append("app.py:POST 子路径未分发到 rename_template")
    api = root / "src/web/js/core/api.js"
    apit = api.read_text(encoding="utf-8") if api.is_file() else ""
    for token in ("renameTemplate(", "deleteTemplate("):
        if token not in apit:
            crud_bad.append(f"api.js:缺 {token}")
    mjs20 = root / "src/web/js/main.js"
    m20 = mjs20.read_text(encoding="utf-8") if mjs20.is_file() else ""
    # V0.0.48：模板行操作迁至 modules/templates.js，note 编辑会话仍在 main.js —— 按归属分文件自查。
    mjs20t = root / "src/web/js/modules/templates.js"
    m20t = mjs20t.read_text(encoding="utf-8") if mjs20t.is_file() else ""
    for token, why, where20 in (
        ("renameTemplateItem", "缺模板重命名接线", m20t),
        ("deleteTemplateItem", "缺模板删除接线", m20t),
        ("noteHistoryId", "缺 note 编辑会话（连续输入应只入栈一次）", m20),
        ("resetEditing", "缺撤销后属性栏暂存作废（note 框会显示旧文本）", m20),
    ):
        if token not in where20:
            crud_bad.append(why)
    # note 会话：pushHistory 必须包在 noteHistoryId 守卫内（否则退化为每键入栈）
    m = re.search(r"onNoteChange\(id, value\) \{.*?\n  \}", m20, flags=re.S)
    if not m:
        crud_bad.append("main.js:onNoteChange 体不可解析")
    elif not re.search(r"noteHistoryId !== id", m.group(0)):
        crud_bad.append("onNoteChange 未按会话守卫入栈")
    codes = root / "src/shared/error-codes.json"
    ct = codes.read_text(encoding="utf-8") if codes.is_file() else ""
    for k in ("templateDeleteFailed", "templateRenameFailed"):
        if k not in ct:
            crud_bad.append(f"error-codes.json:{k}")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("template.rename", "template.delete", "template.renamed", "template.deleted",
                  "err.templateDeleteFailed", "err.templateRenameFailed"):
            if k not in text:
                crud_bad.append(f"{name}:{k}")
    check(not crud_bad, "模板 CRUD + note 会话 V0.0.20",
          f"缺失：{', '.join(crud_bad)}" if crud_bad
          else "模板 删除(软)/重命名 后端-前端贯通 / note 编辑按会话入栈 齐备")

    # 7r. 模板覆盖写（V0.0.21）
    #     判据：① save_template 以**严格 `is True`** 判定 overwrite（防真值字符串误开）；
    #     ② **默认仍拒写**（templateExists 保留）；③ 覆盖前旧文件**先入回收站**
    #     （`_template_trash_dir`，延续「只复制不删除」）；④ 返回值带 overwritten 标记；
    #     ⑤ 前端 saveAsTemplate 捕获 templateExists → 二次确认 → 带 overwrite 重发；
    #     ⑥ 两语取词齐备。
    overwrite_bad: list[str] = []
    m = re.search(r"def save_template\(.*?\n    return \{", rtext, flags=re.S)
    if not m:
        overwrite_bad.append("routes.py:save_template 体不可解析")
    else:
        body21 = m.group(0)
        if 'payload.get("overwrite") is not True' not in body21:
            overwrite_bad.append("save_template 未严格判定 overwrite（应为 is True）")
        if "templateExists" not in body21:
            overwrite_bad.append("save_template 丢了默认拒写（templateExists）")
        if not re.search(r"templateExists[\s\S]*?_template_trash_dir\(", body21):
            overwrite_bad.append("覆盖分支未先入回收站（应紧跟 _template_trash_dir）")
        if "overwritten" not in body21:
            overwrite_bad.append("save_template 返回缺 overwritten 标记")
    # V0.0.48：saveAsTemplate 已迁至 modules/templates.js（AST 钉函数体的判据不变）。
    tpl21 = root / "src/web/js/modules/templates.js"
    t21 = tpl21.read_text(encoding="utf-8") if tpl21.is_file() else ""
    m = re.search(r"async function saveAsTemplate\(\) \{.*?\n\}", t21, flags=re.S)
    if not m:
        overwrite_bad.append("templates.js:saveAsTemplate 体不可解析")
    else:
        body21 = m.group(0)
        if "templateExists" not in body21:
            overwrite_bad.append("saveAsTemplate 未捕获 templateExists")
        if "overwrite: true" not in body21:
            overwrite_bad.append("saveAsTemplate 未带 overwrite 重发")
        if "confirm(" not in body21:
            overwrite_bad.append("saveAsTemplate 缺二次确认")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("template.overwriteConfirm", "template.overwritten"):
            if k not in text:
                overwrite_bad.append(f"{name}:{k}")
    check(not overwrite_bad, "模板覆盖写 V0.0.21",
          f"缺失：{', '.join(overwrite_bad)}" if overwrite_bad
          else "overwrite 严格判定 / 默认仍拒写 / 覆盖前入回收站 / 前端二次确认 / 取词 齐备")

    # 7s. 请求体传输上限 ≥ 业务上限（V0.0.22）
    #     背景：`_read_body()` 用 MAX_BODY_BYTES 先拦下所有请求体，早于各业务检查。
    #     该值曾固定 256KB，低于编辑态 8MB / 模板 2MB —— 业务层 editorTooLarge /
    #     templateTooLarge 永远不可达，用户只拿到误导性的 413 bodyTooLarge。
    #     判据：**实测导入** config（子进程 -B 免写 __pycache__），比对数值关系。
    body_bad = ""
    body_note = ""
    if not (root / "src/server/config.py").is_file():
        body_bad = "缺少 config.py"
    else:
        probe = ("import sys;sys.path.insert(0,'src');from server import config as c;"
                 "print(c.MAX_BODY_BYTES,c.MAX_EDITOR_BYTES,c.TEMPLATE_MAX_BYTES,c.MAX_ICON_BYTES)")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, "-B", "-c", probe], cwd=str(root), env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            body_bad = "无法导入 config：" + (tail[-1] if tail else "未知错误")
        else:
            try:
                body, editor, tpl, icon = (int(x) for x in proc.stdout.split()[:4])
            except ValueError:
                body_bad = f"输出无法解析：{proc.stdout.strip()[:60]}"
            else:
                need = max(editor, tpl, icon)
                if body < need:
                    body_bad = (f"传输上限 {body} < 业务上限 {need}"
                                f"（编辑态 {editor} / 模板 {tpl} / 图标 {icon}）"
                                " —— 大请求会在 _read_body 被 413 拦下，业务错误码不可达")
                else:
                    body_note = (f"传输 {body} ≥ 业务 {need}"
                                 f"（编辑态 {editor} / 模板 {tpl} / 图标 {icon}），业务上限可达")
    check(not body_bad, "请求体上限一致性 V0.0.22", body_bad or body_note)

    # 7t. 帮助页分节渲染幂等（V0.0.22）
    #     背景：`renderSections()` 只 appendChild、从不清空；语言切换监听每次都调它，
    #     分节与导航成倍累积（无头 Edge 实测 7 → 14 → 21）。判据：函数体内必须有清空语句。
    help_bad = ""
    hj_file = root / "src/web/js/help.js"
    if not hj_file.is_file():
        help_bad = "缺少 help.js"
    else:
        htext = hj_file.read_text(encoding="utf-8")
        m = re.search(r"function renderSections\(\)\s*\{(.*?)\n\}", htext, flags=re.S)
        if not m:
            help_bad = "help.js:renderSections 体不可解析"
        else:
            fbody = m.group(1)
            clears = (re.search(r"\.textContent\s*=\s*(?:''|\"\")", fbody)
                      or re.search(r"\.(?:replaceChildren|innerHTML)\s*=\s*(?:''|\"\"|\w*\()", fbody)
                      or "removeChild" in fbody)
            if not clears:
                help_bad = "renderSections 未清空容器 —— 语言切换会令分节成倍累积"
    check(not help_bad, "帮助页分节渲染幂等 V0.0.22",
          help_bad or "renderSections 渲染前清空，语言切换后分节数不累积")

    # 7u. 默认示例取词早于偏好恢复（V0.0.22）
    #     背景：`defaultRoot()` 跑在模块顶层，早于底部的 `initPrefs()` —— 此时 i18n 仍是
    #     出厂 zh-CN，英文环境首屏示例为中文名，且随即被 saveNow() 永久落盘。
    #     判据：`const rootNode = defaultRoot()` 之前必须已调用 `initPrefs()`。
    pref_bad = ""
    mjs22 = root / "src/web/js/main.js"
    m22 = mjs22.read_text(encoding="utf-8") if mjs22.is_file() else ""
    if not m22:
        pref_bad = "缺少 main.js"
    else:
        anchor = re.search(r"const rootNode\s*=\s*defaultRoot\(\)", m22)
        if not anchor:
            pref_bad = "main.js:未找到 defaultRoot() 调用点"
        elif "initPrefs()" not in m22[:anchor.start()]:
            pref_bad = ("defaultRoot() 早于 initPrefs() —— 默认示例取到的是出厂语言，"
                        "且会被落盘固化")
    check(not pref_bad, "默认示例取词前置 V0.0.22",
          pref_bad or "initPrefs() 已在 defaultRoot() 之前调用，默认示例随语言")

    # 7v. P3 代码整洁与健壮性（V0.0.24，全项目审查 P3-8 ~ P3-13）
    #     判据逐条：
    #     ① P3-8  inspector.js：`let currentId` 必须声明在 input 监听器**之前**（顺序反直觉易踩坑）；
    #     ② P3-9  launch-icon.js：上传指纹**持久化**（readPref/writePref + ICON_KEY），
    #             不再用模块级变量（页面重载即归零 → 每次开页白传一次图标）；
    #     ③ P3-10 tree-model.js：canMove 对「节点不存在」返回 'missing'（不再是语义混淆的 'root'），
    #             且 main.js 有对应提示键 + 双语取词齐备；
    #     ④ P3-11 routes.py：save_template 体积检查**在覆盖之前**、写失败回滚旧件；rename 亦有回滚；
    #     ⑤ P3-12 main.js：inspector 只有**一条** import（含 createInspector 与 copyText）、
    #             顶层 `async function` 不残留行首空格；
    #     ⑥ P3-13 dtree_core.py + 契约：`pathConflictDir` 对称报错 + 错误码三处齐备。
    p3_bad: list[str] = []

    insp_p3 = root / "src/web/js/ui/inspector.js"
    if insp_p3.is_file():
        itext_p3 = insp_p3.read_text(encoding="utf-8")
        pos_decl = itext_p3.find("let currentId")
        pos_listener = itext_p3.find("refs.note.addEventListener('input'")
        if pos_decl < 0:
            p3_bad.append("inspector.js:缺 currentId 声明")
        elif pos_listener >= 0 and pos_decl > pos_listener:
            p3_bad.append("inspector.js:currentId 声明在监听器之后（P3-8 未修）")
    else:
        p3_bad.append("缺 inspector.js")

    li = root / "src/web/js/ui/launch-icon.js"
    if li.is_file():
        ltext = li.read_text(encoding="utf-8")
        for token in ("readPref(ICON_KEY)", "writePref(ICON_KEY", "lastUploadedKey"):
            hit = (token in ltext)
            if token == "lastUploadedKey":
                if hit:
                    p3_bad.append("launch-icon.js 仍用模块级 lastUploadedKey（P3-9 未修）")
            elif not hit:
                p3_bad.append(f"launch-icon.js:缺 {token}")
    else:
        p3_bad.append("缺 launch-icon.js")
    i18n_p3 = root / "src/web/js/i18n/index.js"
    if i18n_p3.is_file():
        i3 = i18n_p3.read_text(encoding="utf-8")
        for token in ("export const ICON_KEY", "export function readPref", "export function writePref"):
            if token not in i3:
                p3_bad.append(f"i18n/index.js:缺 {token}")
    else:
        p3_bad.append("缺 i18n/index.js")

    tm_p3 = root / "src/web/js/modules/tree-model.js"
    if tm_p3.is_file():
        m = re.search(r"export function canMove\(.*?\n\}", tm_p3.read_text(encoding="utf-8"), flags=re.S)
        if not m:
            p3_bad.append("tree-model.js:canMove 体不可解析")
        elif "'missing'" not in m.group(0):
            p3_bad.append("canMove 未对不存在节点返回 'missing'（P3-10 未修）")
    mjs_p3 = root / "src/web/js/main.js"
    m3 = mjs_p3.read_text(encoding="utf-8") if mjs_p3.is_file() else ""
    if "toast.moveMissing" not in m3:
        p3_bad.append("main.js:缺 toast.moveMissing 映射")
    if m3.count("from './ui/inspector.js'") != 1:
        p3_bad.append("main.js:inspector import 未合并为一条（P3-12 未修）")
    # V0.0.48：applyTemplate 迁至 modules/templates.js（迁入时**保留原顶层缩进**，行首仍无空格）。
    mjs_p3t = root / "src/web/js/modules/templates.js"
    m3t = mjs_p3t.read_text(encoding="utf-8") if mjs_p3t.is_file() else ""
    if not re.search(r"^async function applyTemplate\(", m3t, flags=re.M):
        p3_bad.append("templates.js:applyTemplate 行首空格未清（或函数缺失）")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/locales" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("toast.moveMissing", "err.pathConflictDir"):
            if k not in text:
                p3_bad.append(f"{name}:{k}")

    if rtext:
        m = re.search(r"def save_template\(.*?\n    return \{", rtext, flags=re.S)
        if not m:
            p3_bad.append("routes.py:save_template 体不可解析")
        else:
            body_p3 = m.group(0)
            if "trashed_old" not in body_p3 or "os.replace(trashed_old, path)" not in body_p3:
                p3_bad.append("save_template 覆盖失败未回滚旧件（P3-11 未修）")
            # 体积检查必须早于同名覆盖分支（否则超限时旧件已入回收站）
            pos_size = body_p3.find("templateTooLarge")
            pos_overwrite = body_p3.find("templateExists")
            if pos_size < 0 or (pos_overwrite >= 0 and pos_size > pos_overwrite):
                p3_bad.append("save_template 体积检查未前置到覆盖之前（P3-11 未修）")
        m = re.search(r"def rename_template\(.*?\n    return \{", rtext, flags=re.S)
        if not m:
            p3_bad.append("routes.py:rename_template 体不可解析")
        elif "templateRenameFailed" not in m.group(0) or (
                "os.replace(new_path" not in m.group(0) and "trash / new_filename" not in m.group(0)):
            p3_bad.append("rename_template 旧件入回收站失败未回滚（P3-11 未修）")
    else:
        p3_bad.append("缺 routes.py")
    dtree_p3 = root / "src/server/dtree_core.py"
    if dtree_p3.is_file():
        if "pathConflictDir" not in dtree_p3.read_text(encoding="utf-8"):
            p3_bad.append("dtree_core.py:缺 pathConflictDir 对称报错（P3-13 未修）")
    else:
        p3_bad.append("缺 dtree_core.py")
    codes_p3 = root / "src/shared/error-codes.json"
    if codes_p3.is_file():
        try:
            if "pathConflictDir" not in json.loads(codes_p3.read_text(encoding="utf-8")):
                p3_bad.append("error-codes.json:缺 pathConflictDir")
        except ValueError:
            p3_bad.append("error-codes.json 无法解析")
    check(not p3_bad, "P3 整洁与健壮性 V0.0.24",
          f"缺失：{', '.join(p3_bad)}" if p3_bad
          else "currentId 顺序 / 图标指纹持久化 / canMove missing / 模板回滚 / import 合并 / "
               "pathConflictDir 对称 齐备")

    # 7w. 浏览器冒烟脚本的断言覆盖（V0.0.25，§P0-2 T7）
    #     背景：P1-1（帮助页切语言累积加分节）与 P1-2（默认示例固化出厂语言）当时
    #     verify / unittest / smoke **三项全绿** —— 它们只在页面真跑起来时才现形。
    #     `tools/browser_smoke.py` 把这类缺陷变成常态守卫；这里静态锚定它的关键断言，
    #     防止日后有人把断言削成空壳（守卫的守卫）。
    #     V0.0.29：再锚 2 个 token —— C-P3-5（非法皮肤回落出厂默认）与 D-P3-2（箭头色随 --qm-text-dim）。
    bsmoke_p = root / "tools/browser_smoke.py"
    b_bad: list[str] = []
    if not bsmoke_p.is_file():
        b_bad.append("缺 tools/browser_smoke.py")
    else:
        btext = bsmoke_p.read_text(encoding="utf-8")
        anchors_bsmoke = (
            ("--enable-logging=stderr", "未开浏览器控制台日志（捕获不到未捕获异常）"),
            ("Uncaught", "缺未捕获异常判定"),
            ("[i18n] missing key", "缺漏翻判定"),
            (".help-section", "缺帮助页分节断言（P1-1 回归位）"),
            ("qm.lang", "缺默认示例语言断言（P1-2 回归位）"),
            ("new Event('change')", "缺语言切换驱动（未走真实用户路径）"),
            (".tree-name", "缺默认示例节点名采集"),
            ("CJK", "缺中文名判定"),   # 稳定标识符锚点（原 "\\u4e00" 依赖三层转义，§P2-18）
            ("copytree", "缺沙盒隔离（会污染真实 data/）"),
            ("_probe_ui.html", "缺同源探针页"),
            # V0.0.29 增：C-P3-5（非法皮肤回落）/ D-P3-2（箭头色随 --qm-text-dim）/ C-P3-1（滚动保持）
            ("not-a-real-skin", "缺非法皮肤回落断言（C-P3-5 回归位）"),
            ("--qm-text-dim", "缺箭头随皮肤变量断言（D-P3-2 回归位）"),
            ("treeWrap", "缺滚动位置保持断言（C-P3-1 回归位）"),
            # V0.0.32 增：C-P3-2（拖拽落点预判自身子树）/ C-P3-3（划子元素不摘高亮）/ C-P3-4（提示条上限）
            ("dragDesc", "缺拖拽落点预判断言（C-P3-2 回归位）"),
            ("dlChild", "缺划子元素不摘高亮断言（C-P3-3 回归位）"),
            ("MAX_TOASTS", "缺提示条数量上限断言（C-P3-4 回归位）"),
        )
        for token, why in anchors_bsmoke:
            if token not in btext:
                b_bad.append(why)
    check(not b_bad, "浏览器冒烟覆盖 V0.0.25",
          f"缺失：{', '.join(b_bad)}" if b_bad
          else "控制台异常 / 漏翻 / 分节幂等 / 默认示例语言 / 切换驱动 / 沙盒隔离 / "
               "皮肤回落 / 箭头随皮肤 / 滚动保持 / 拖拽落点预判 / 高亮不闪 / 提示条上限 齐备")

    # 7x. 后端防御批（V0.0.30，src 审查第四档 A-P3-1~8）
    #     逐条钉住「防御补丁」的关键 token —— 防止日后被无意回退（守卫的守卫）。
    def _read(rel: str) -> str:
        p = root / rel
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    srcs = {
        "routes": _read("src/server/routes.py"),
        "app": _read("src/server/app.py"),
        "config": _read("src/server/config.py"),
        "core": _read("src/server/dtree_core.py"),
    }
    def_bad: list[str] = []
    anchors_def = (
        ("A-P3-1", "routes", "_PS_TIMEOUT_SEC = 30", "缺 PowerShell 超时常量"),
        ("A-P3-1", "routes", "timeout=_PS_TIMEOUT_SEC", "subprocess.run 未接超时"),
        ("A-P3-1", "routes", "subprocess.TimeoutExpired", "未捕获超时异常"),
        ("A-P3-4", "config", "def desktop_dir(", "缺真实桌面解析"),
        ("A-P3-4", "routes", "config.desktop_dir()", "create_shortcut 未用真实桌面"),
        ("A-P3-6", "routes", 'payload.get("dryRun") is True', "dryRun 未严格布尔判定"),
        ("A-P3-3", "routes", "seq:03d", "模板回收站目录未唯一化"),
        ("A-P3-7", "app", "_read_chunked_body", "未支持 chunked body"),
        ("A-P3-8", "app", "timer.daemon = True", "Timer 未设守护"),
        ("A-P3-5", "core", "while stack:", "count_tree 未迭代化（未见显式栈循环）"),
    )
    for code, key, token, why in anchors_def:
        if token not in srcs[key]:
            def_bad.append(f"{code} {why}")
    # A-P3-2：助手存在 + 四处原子写均已改用 + 旧固定名已清除
    rt = srcs["routes"]
    if "_tmp_sibling(" not in rt:
        def_bad.append("A-P3-2 缺唯一临时名助手")
    elif rt.count("_tmp_sibling(") < 5:   # 1 定义 + 4 调用点
        def_bad.append("A-P3-2 原子写未全部改用 _tmp_sibling")
    if 'path.name + ".tmp"' in rt or 'new_path.name + ".tmp"' in rt:
        def_bad.append("A-P3-2 仍残留固定临时名")
    check(not def_bad, "后端防御批 V0.0.30",
          f"缺失：{', '.join(def_bad)}" if def_bad
          else "超时 / 唯一临时名 / 唯一回收站 / 真实桌面 / 迭代计数 / 严格布尔 / chunked / 守护 Timer 齐备")

    # 7y. 前端核心防御批（V0.0.31，src 审查第四档 B-P3-1~6）
    api_js = _read("src/web/js/core/api.js")
    bus_js = _read("src/web/js/core/bus.js")
    tm_js = _read("src/web/js/modules/tree-model.js")
    main_js = _read("src/web/js/main.js")
    insp_js = _read("src/web/js/ui/inspector.js")
    codes_json = _read("src/shared/error-codes.json")
    zh_js = _read("src/web/locales/zh-CN.js")
    en_js = _read("src/web/locales/en-US.js")
    fe_bad: list[str] = []
    fe_anchors = (
        ("B-P3-1", api_js, "code = 'networkError'", "api 未归一网络失败"),
        ("B-P3-1", api_js, "catch (cause)", "api 未捕 fetch 失败"),
        ("B-P3-1", codes_json, '"networkError"', "error-codes.json 缺 networkError"),
        ("B-P3-1", zh_js, "'err.networkError'", "zh-CN 缺 err.networkError"),
        ("B-P3-1", en_js, "'err.networkError'", "en-US 缺 err.networkError"),
        ("B-P3-2", main_js, "let saveInFlight = false;", "main 缺在途保护标志"),
        ("B-P3-2", main_js, "if (saveInFlight) {", "main 未按在途标志提前返回"),
        ("B-P3-2", main_js, "let saveQueued = false;", "main 缺排队合并标志"),
        ("B-P3-3", tm_js, "if (!validateSegment(name).ok) return false;", "renameNode 未自校验合法性"),
        ("B-P3-3", tm_js, "if (hasSiblingName(findParent(root, id), name, id)) return false;",
         "renameNode 未自校验同层重名"),
        ("B-P3-4", tm_js, "hasOwnProperty.call(out, child.name)", "toPlainTree 未检同层重名"),
        ("B-P3-5", tm_js, "while (stack.length)", "tree-model 查询族未迭代化"),
        ("B-P3-5", insp_js, "const stack = [node]", "inspector.findAny 未迭代化"),
        ("B-P3-6", bus_js, "listeners.delete(type)", "bus.off 未清空集合"),
    )
    for code, text, token, why in fe_anchors:
        if token not in text:
            fe_bad.append(f"{code} {why}")
    check(not fe_bad, "前端核心防御批 V0.0.31",
          f"缺失：{', '.join(fe_bad)}" if fe_bad
          else "网络归一 / 在途保护 / 改名自校验 / 重名告警 / 迭代查询 / bus 清理 齐备")

    # 7z. UI 防御批（V0.0.32，src 审查第四档 C-P3-2~4）
    #     同 7x / 7y：把「防御补丁」的关键 token 钉住，防止日后被无意回退（守卫的守卫）。
    tv_js = _read("src/web/js/ui/tree-view.js")
    toast_js = _read("src/web/js/ui/toast.js")
    ui_bad: list[str] = []
    ui_anchors = (
        ("C-P3-2", tv_js, "isSelfOrDescendant(draggingNode, node.id)",
         "dragover 未预判「自身 / 自身子孙」（防环规则退化成只挡自身）"),
        ("C-P3-2", tv_js, "let draggingNode = null;", "缺被拖节点对象缓存"),
        ("C-P3-3", tv_js, "function leftRow(", "缺「指针是否真离开本行」判定"),
        ("C-P3-3", tv_js, "if (leftRow(row, event))", "dragleave 未走离开判定（会再次闪烁）"),
        ("C-P3-4", toast_js, "const MAX_TOASTS = 4;", "缺提示条数上限常量"),
        ("C-P3-4", toast_js, "items.length - MAX_TOASTS", "缺超限淘汰逻辑"),
    )
    for code, text, token, why in ui_anchors:
        if token not in text:
            ui_bad.append(f"{code} {why}")
    # C-P3-2：旧的「只挡自身」写法必须已清除（防两套判据并存）
    if "draggingId !== node.id" in tv_js:
        ui_bad.append("C-P3-2 仍残留「只挡自身」的旧判据")
    check(not ui_bad, "UI 防御批 V0.0.32",
          f"缺失：{', '.join(ui_bad)}" if ui_bad
          else "拖拽落点预判 / 含子元素语义的 dragleave / 提示条上限 齐备")

    # 7aa. 序列化族迭代化（V0.0.33，第四档同族残留收口）
    #      背景：B-P3-5 只迭代化了「查询族」，同族的 toDocumentNode / fromDocumentNode
    #      仍是递归 —— 深链（MAX_EDITOR_NODES = 20000）下依旧会 RangeError。
    #      判据：① 两函数改迭代（正锚点）；② 旧递归写法已清除（防两套并存）。
    tm_ser = _read("src/web/js/modules/tree-model.js")
    ser_bad: list[str] = []
    ser_anchors = (
        ("4D-1", tm_ser, "const outRoot = build(node);", "toDocumentNode 未改为迭代构建"),
        ("4D-1", tm_ser, "const stack = [[node, outRoot]];", "toDocumentNode 缺显式栈遍历"),
        ("4D-2", tm_ser, "const stack = [{ src: raw", "fromDocumentNode 未改为迭代构建"),
        ("4D-2", tm_ser, "kidsOf(frame.kids[idx])", "fromDocumentNode 未按帧下潜子节点"),
    )
    for code, text, token, why in ser_anchors:
        if token not in text:
            ser_bad.append(f"{code} {why}")
    for leftover in ("node.children.map(toDocumentNode)",
                     "children.map((child, i) => fromDocumentNode("):
        if leftover in tm_ser:
            ser_bad.append(f"仍残留旧递归写法（{leftover}）")
    check(not ser_bad, "序列化族迭代化 V0.0.33",
          f"缺失：{', '.join(ser_bad)}" if ser_bad
          else "toDocumentNode / fromDocumentNode 均迭代化，旧递归写法已清除")

    # 7ab. 模板双格式批（V0.0.34，§十.3 E/G · 6A）
    #      模板 `.md` 是「导出→再导入」成环的载体：render / parse 必须**成对**存在，
    #      围栏自适应（正文含反引号）与重名/解析错误码也必须就位 —— 任一缺失即
    #      说明某类内容会在往返中静默丢数据（§十.3 往返成环要求）。
    core_tpl = _read("src/server/dtree_core.py")
    codes_tpl = _read("src/shared/error-codes.json")
    tpl_bad: list[str] = []
    tpl_anchors = (
        ("6A-1", core_tpl, "def validate_template(", "缺 validate_template"),
        ("6A-1", core_tpl, "def _validate_template_tree(", "缺模板树校验（段名/重名/上限）"),
        ("6A-2", core_tpl, "def render_md_template(", "缺 render_md_template"),
        ("6A-2", core_tpl, "def parse_md_template(", "缺 parse_md_template"),
        ("6A-2", core_tpl, "def _md_fence_for(", "缺围栏自适应（正文含反引号）"),
        ("6A-2", core_tpl, "_MD_ITEM_RE = re.compile", "缺列表项正则"),
        ("6A-2", core_tpl, "_MD_DIR_MARK", "缺目录标记（📁 兼容）"),
        ("6A-2", core_tpl, "templateSiblingDuplicated", "缺同层重名判据"),
        ("6A-2", core_tpl, "templateBadMarkdown", "缺 Markdown 解析错误码"),
        ("6A-2", codes_tpl, "templateBadMarkdown", "error-codes.json 缺 templateBadMarkdown"),
        ("6A-2", codes_tpl, "templateSiblingDuplicated", "error-codes.json 缺 templateSiblingDuplicated"),
    )
    for code, text, token, why in tpl_anchors:
        if token not in text:
            tpl_bad.append(f"{code} {why}")
    check(not tpl_bad, "模板双格式批 V0.0.34",
          f"缺失：{', '.join(tpl_bad)}" if tpl_bad
          else "validate_template / render_md_template / parse_md_template + 围栏自适应 + 重名/解析错误码 齐备")

    # 7ac. 模板目录绑定批（V0.0.35，§十.3 F · 6B）
    #      绑定目录是「唯一可写模板库」的落点，三条不变量：
    #      ① 解析入口**只能有一个**（`config.templates_dir()`），旧固定常量必须清零；
    #      ② 「绑定判据」与「运行态判据」必须**分开** —— 默认 `templates/` 可用、
    #         却不可被绑定（否则要么工具一启动就不可用，要么用户能绑到只读内置层）；
    #      ③ 所有写路径自己再校验一次（`QM_TEMPLATES_DIR` 可绕过 UI 直指受保护位置）。
    cfg_tpl = _read("src/server/config.py")
    app_tpl = _read("src/server/app.py")
    bind_bad: list[str] = []
    bind_anchors = (
        ("6B-1", cfg_tpl, "def templates_dir()", "config 缺 templates_dir 解析入口"),
        ("6B-1", cfg_tpl, "def settings_candidates()", "config 缺 settings 候选位置"),
        ("6B-1", cfg_tpl, "TEMPLATES_DIR_ENV", "config 缺绑定目录 env 名"),
        ("6B-1", cfg_tpl, "DEFAULT_TEMPLATES_DIR", "config 缺内置默认目录常量"),
        ("6B-2", rtext, "def _templates_dir_blocked(", "routes 缺绑定判据"),
        ("6B-2", rtext, "def _templates_dir_reason(", "routes 缺运行态判据"),
        ("6B-2", rtext, "def _templates_dir_or_raise(", "routes 缺写路径校验入口"),
        ("6B-2", rtext, "def get_templates_dir(", "routes 缺 GET 处理器"),
        ("6B-2", rtext, "def set_templates_dir(", "routes 缺 PUT 处理器"),
        ("6B-2", rtext, "TEMPLATES_DIR_PATH = ", "routes 缺端点常量"),
        ("6B-2", app_tpl, "routes.get_templates_dir()", "app.py 未接线 GET"),
        ("6B-2", app_tpl, "routes.set_templates_dir(", "app.py 未接线 PUT"),
        ("6B-2", codes_tpl, "templateDirBlocked", "error-codes.json 缺 templateDirBlocked"),
        ("6B-2", codes_tpl, "templateDirNotWritable", "error-codes.json 缺 templateDirNotWritable"),
    )
    for code, text, token, why in bind_anchors:
        if token not in text:
            bind_bad.append(f"{code} {why}")
    # 旧写法清零：写路径若仍直接读固定常量，绑定形同虚设
    if re.search(r"config\.TEMPLATES_DIR\b", rtext):
        bind_bad.append("routes.py 仍在直接读 config.TEMPLATES_DIR（应走 templates_dir()）")
    check(not bind_bad, "模板目录绑定批 V0.0.35",
          f"缺失：{', '.join(bind_bad)}" if bind_bad
          else "解析入口 / 绑定与运行态双判据 / GET+PUT 接线 / 两枚错误码 齐备")

    # 7ad. 模板双格式批（V0.0.36，§十.3 · 6C）
    #      列表 / 读取 / 导入 / 删除必须**共用同一套白名单与读取口径**，否则
    #      「列表里看得到、单读读不到」会成为静默坑。三条不变量：
    #      ① **白名单分工**：`TEMPLATE_FILE`（双格式）管读/列/删/导入，`TEMPLATE_NAME`
    #         （仅 `.json`）管新建/改名 —— 若顺手把 `TEMPLATE_NAME` 也放宽，`.md` 就会
    #         参与「另存为」，破坏「`.md` 只由导入/导出产生」的格式契约；
    #      ② 读取走**同一分派函数**（`_read_template_doc`），列表与单读同口径；
    #      ③ 导入**全量校验**（`validate_template`）且 `.md` 走 `render_md_template`
    #         **规范化重渲染**（否则手工书写的 md 落盘后与导出侧不同字节，往返不成环）。
    zh_i18n = _read("src/web/locales/zh-CN.js")
    en_i18n = _read("src/web/locales/en-US.js")
    fmt_bad: list[str] = []
    fmt_anchors = (
        ("6C-1", rtext, "TEMPLATE_FILE = re.compile(", "routes 缺双格式白名单"),
        ("6C-1", rtext, "def _template_source(", "routes 缺格式判定"),
        ("6C-1", rtext, "def _strip_template_ext(", "routes 缺扩展名剥离助手"),
        ("6C-1", rtext, "def _read_template_doc(", "routes 缺统一读取分派"),
        ("6C-1", rtext, 'd.glob("*.md")', "list_templates 未扫 .md"),
        ("6C-1", rtext, '"source": _template_source(', "列表项未标 source"),
        ("6C-2", rtext, "TEMPLATES_IMPORT_PATH = ", "routes 缺导入端点常量"),
        ("6C-2", rtext, "def import_template(", "routes 缺导入处理器"),
        ("6C-2", rtext, "dtree_core.validate_template(", "导入未走全量校验"),
        ("6C-2", rtext, "dtree_core.render_md_template(", "导入 .md 未规范化重渲染"),
        ("6C-2", app_tpl, "routes.import_template(", "app.py 未接线导入"),
        ("6C-2", app_tpl, "is_import = path == routes.TEMPLATES_IMPORT_PATH",
         "app.py 缺 is_import 判定（会被 is_rename 前缀吞掉）"),
        ("6C-2", codes_tpl, "templateEmpty", "error-codes.json 缺 templateEmpty"),
        ("6C-2", zh_i18n, "err.templateEmpty", "zh-CN 缺 err.templateEmpty"),
        ("6C-2", en_i18n, "err.templateEmpty", "en-US 缺 err.templateEmpty"),
    )
    for code, text, token, why in fmt_anchors:
        if token not in text:
            fmt_bad.append(f"{code} {why}")
    # 分工判据：`TEMPLATE_NAME` 必须仍是**只认 `.json`**（防被顺手放宽成双格式）
    if '_TPL_STEM_PATTERN + r"\\.json$"' not in rtext:
        fmt_bad.append("TEMPLATE_NAME 不再是「只认 .json」（新建/改名的格式契约被破坏）")
    # 列表若仍用旧白名单，会漏掉 `.md`
    if "TEMPLATE_NAME.match(p.name)" in rtext:
        fmt_bad.append("list_templates 仍用 TEMPLATE_NAME（应改 TEMPLATE_FILE）")
    check(not fmt_bad, "模板双格式批 V0.0.36",
          f"缺失：{', '.join(fmt_bad)}" if fmt_bad
          else "双格式列表+source / 统一读取分派 / 导入归一+全量校验+格式保持 / 接线 / 错误码 齐备")

    # 7ae. 模板迁移与打包批（V0.0.37，§十.3 E · 6D；2026-10-16 收窄为「包内 16 套」）
    #      交付形态：**项目内只有一套空模板**（`templates/P0_空白项目模板.json`，随工具交付），
    #      16 套业务模板独立成包。五条不变量：
    #      ① **内置层收窄**：`templates/` 只允许内置 P0 —— 业务模板回流必须被抓（否则
    #         「工具不带业务模板」在无人察觉的情况下回退）；
    #      ② **分发层成形**：`templates-pack/` 内 16 套 `.md` + 16 套 `.json` + 说明 + 清单；
    #      ③ **清单可复算**：`digest` 由本校验**按 digestRule 独立复算**（不调用工具函数 ——
    #         调工具就等于拿工具证明它自己，改坏规则也照样通过）；
    #      ④ **zip 不入库**：可再生产物必须被 `.gitignore` 收口（否则每次改模板都产生新 blob）；
    #      ⑤ **只有一套空模板**：包内**不得**再收 P0 的同名件（否则导入后列表里会有第二套），
    #         且清单**不得**有 builtin 项、**不得**有任何引用越出包目录。
    pack_bad: list[str] = []
    tpl_dir = root / "templates"
    tpl_names = sorted(p.name for p in tpl_dir.iterdir()) if tpl_dir.is_dir() else []
    if tpl_names != ["P0_空白项目模板.json"]:
        pack_bad.append(f"templates/ 应只留 P0_空白项目模板.json，实测 {tpl_names}")

    pack_dir = root / "templates-pack"
    if not pack_dir.is_dir():
        pack_bad.append("缺 templates-pack/")
    else:
        pack_names = sorted(p.name for p in pack_dir.iterdir())
        n_md = sum(1 for n in pack_names if n.endswith(".md"))
        n_json = sum(1 for n in pack_names if n.endswith(".json") and n != "pack.manifest.json")
        if n_md != 17:
            pack_bad.append(f"包内 .md 应 17（16 套 + 1 说明），实测 {n_md}")
        if n_json != 16:
            pack_bad.append(f"包内 .json 应 16，实测 {n_json}")
        for rel in ("模板库来源说明.md", "pack.manifest.json"):
            if rel not in pack_names:
                pack_bad.append(f"缺 templates-pack/{rel}")
        # ⑤ 负向：包内不得再收内置空模板的同名件 —— 「项目内只有一套空模板」。
        for stray in ("P0_空白项目模板.md", "P0_空白项目模板.json"):
            if stray in pack_names:
                pack_bad.append(f"包内不得出现内置空模板的同名件：{stray}")

    man_path = pack_dir / "pack.manifest.json"
    if not man_path.is_file():
        pack_bad.append("缺 pack.manifest.json（清单可复算之前提）")
    else:
        try:
            man = json.loads(man_path.read_text(encoding="utf-8"))
        except ValueError:
            man = None
            pack_bad.append("pack.manifest.json 无法解析")
        if isinstance(man, dict):
            # 独立复算：规则照 digestRule 的表述（排除 digest / zip 两键的规范化 JSON）
            body = {k: v for k, v in man.items() if k not in ("digest", "zip")}
            canon = json.dumps(body, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
            want_digest = "sha256:" + hashlib.sha256(canon).hexdigest()
            if man.get("digest") != want_digest:
                pack_bad.append("清单 digest 复算失配（规则见清单 digestRule）")
            if man.get("count") != 16:
                pack_bad.append(f"清单套数 {man.get('count')} ≠ 16")
            if (man.get("totals") or {}) != {"dirs": 475, "files": 18}:
                pack_bad.append("清单合计 ≠ 475 目录 / 18 文件")
            if not (man.get("zip") or {}).get("sha256"):
                pack_bad.append("清单缺 zip.sha256（确定性构建不可复算）")
            # ⑤ 负向：包内不得再有内置项，且引用不得越出包目录（P0 的 `.json` 曾以
            #    `../templates/...` 跨目录指向，2026-10-16 已消除）。
            builtin_items = [t for t in (man.get("templates") or []) if t.get("builtin")]
            if builtin_items:
                pack_bad.append("清单仍有 builtin=true 项（包内不该再有内置空模板）")
            for t in man.get("templates") or []:
                for key in ("md", "json"):
                    rel = ((t.get(key) or {}).get("file") or "")
                    if ".." in rel or "/" in rel:
                        pack_bad.append(
                            f"清单条目 {t.get('stem')}.{key} 引用越出包目录：{rel}")

    # 另锚工具自身的**退出码契约**：环境类（PackIOError）与内容类必须分码，否则 CI 会把
    # 「模板被改坏」误报成「环境没配好」（2026-10-11 反向验证 N7a 暴露并修复）。
    pt_tpl = _read("tools/pack_templates.py")
    for token, why in (
        ("DIGEST_RULE = ", "pack_templates 缺 digestRule 常量"),
        ("PACK_DOC_FILES = ", "pack_templates 缺说明件白名单（孤儿 .md 判定会误伤）"),
        ("def discover(", "pack_templates 缺模板盘点"),
        ("def validate_entry(", "pack_templates 缺逐套校验"),
        ("def payload_digest(", "pack_templates 缺清单摘要"),
        ("def build_zip_bytes(", "pack_templates 缺确定性打包"),
        ("孤儿", "pack_templates 未拒孤儿 .md（只按 .json 收集会静默少一套）"),
        ('zipfile.ZIP_DEFLATED', "pack_templates 未固定压缩方式（确定性无从谈起）"),
        ("class PackIOError(", "pack_templates 未区分环境错误（孤儿 .md 退回与环境错误同码 1）"),
        ("except PackIOError", "pack_templates main 未按 PackIOError 分流退出码（契约失效）"),
    ):
        if token not in pt_tpl:
            pack_bad.append(why)
    if "templates-pack/*.zip" not in _read(".gitignore"):
        pack_bad.append(".gitignore 未忽略 templates-pack/*.zip（可再生产物会入库）")
    # browser_smoke 侧：模板数断言必须收紧为「恰好 1」（≥1 时业务模板回流照样通过），
    # 且必须把沙盒内置目录显式喂给服务（否则本机 settings 里的绑定会污染断言）。
    bs_tpl = _read("tools/browser_smoke.py")
    for token, why in (
        ("QM_TEMPLATES_DIR", "browser_smoke 未绑定沙盒内置目录（模板数断言会被本机 settings 污染）"),
        ("tpl == 1", "browser_smoke 模板断言未收紧为「恰好 1」（业务模板回流抓不到）"),
    ):
        if token not in bs_tpl:
            pack_bad.append(why)

    check(not pack_bad, "模板迁移与打包批 V0.0.37",
          f"缺失：{', '.join(pack_bad)}" if pack_bad
          else "内置仅 P0 一套 / 包 16 套 .md+16 .json（引用全在包内）/ 清单 digest 独立复算一致 / zip 收口 齐备")

    # 7af. 模板前端批（V0.0.38，§十.3 6E）——「绑定 UI / 轮询 / 右键菜单 / 导入导出」四件事。
    #      本段守的是**接线**（后端能力另有单测与 smoke），因为 6E 的性质恰恰是「后端早就
    #      就绪、前端一直没接」：导入端点 6C 就有了，直到 6E 才接线。故：
    #      ① 目录绑定 UI 的入口与轮询参数必须在；
    #      ② 模板行操作必须真的挂在**右键菜单**上，且 `.tpl-ops` 那套常驻按钮**不得复活**；
    #      ③ 导入 / 导出 / 目录选择必须接线（含「原生框用不了 → 手动粘贴」的降级）；
    #      ④ 页面级断言不得被削（「轮询**实证**」那条尤其容易在重构里被删成弱断言，
    #         删掉后「轮询被整个摘除」也照样通过）。
    fe_bad: list[str] = []
    # V0.0.48：本批 7 个源码锚点随模板子系统整体迁至 modules/templates.js（main.js 只留装配）。
    tpl_js = _read("src/web/js/modules/templates.js")
    main_js = _read("src/web/js/main.js")
    api_js = _read("src/web/js/core/api.js")
    idx_html = _read("src/web/index.html")
    rt_tpl = _read("src/server/routes.py")
    bs_front = _read("tools/browser_smoke.py")
    for token, why in (
        ("const TPL_POLL_MS = 2500", "6E 轮询间隔被改（设计裁决 2500ms）"),
        ("addEventListener('visibilitychange'", "6E 轮询未在页面隐藏时暂停（纯空转）"),
        ("function templateSignature", "6E 缺 file+mtime+size 变化判据（轮询会每 2.5s 重建 DOM）"),
        ("function openTemplateContextMenu", "6E 模板右键菜单缺失"),
        ("function chooseTemplatesDir", "6E 目录选择（含手动粘贴降级）缺失"),
        ("function importTemplateFlow", "6E 导入未接线"),
        ("function exportTemplateItem", "6E 导出未接线"),
    ):
        if token not in tpl_js:
            fe_bad.append(why)
    for token, why in (
        ("'/api/templates-dir/pick'", "api.js 未接线原生目录选择端点"),
        ("'/api/templates-export/'", "api.js 未接线导出端点"),
    ):
        if token not in api_js:
            fe_bad.append(why)
    for token, why in (
        ('id="tplDirRow"', "index.html 缺绑定行"),
        ('id="btnPickDir"', "index.html 缺「选择…」按钮"),
        ('id="btnImportTemplate"', "index.html 缺「导入」按钮"),
    ):
        if token not in idx_html:
            fe_bad.append(why)
    for token, why in (
        ("TEMPLATES_DIR_PICK_PATH", "routes 缺原生目录选择端点常量"),
        ("TEMPLATES_EXPORT_PATH", "routes 缺导出端点常量"),
        ('NO_GUI_PICK_ENV = "QM_NO_GUI_PICK"', "routes 缺原生框关断 env（自动化会弹窗挂起）"),
        ("def export_template(", "routes 缺导出实现"),
        ("def pick_templates_dir(", "routes 缺选择实现"),
    ):
        if token not in rt_tpl:
            fe_bad.append(why)
    for token, why in (
        ("tplDirBtns", "browser_smoke 缺绑定 UI 断言"),
        ("tplMenuN", "browser_smoke 缺右键菜单项断言"),
        ("function pollProbe", "browser_smoke 缺轮询实证（删掉后「轮询被摘除」也照样通过）"),
    ):
        if token not in bs_front:
            fe_bad.append(why)
    # 反锚：常驻按钮那套类名不得在 JS / HTML 里复活（V0.0.38 起操作走右键菜单）。
    # 只查这两处 —— CSS 里保留了「为何移除」的说明性注释，含该类名属正常。
    if "tpl-ops" in main_js or "tpl-ops" in tpl_js or "tpl-ops" in idx_html:
        fe_bad.append("模板行常驻按钮（.tpl-ops）复活 —— 6E 的「去按钮」被回退")
    # smoke 侧：原生框必须被关断，否则 CI / 沙盒里会**弹窗挂起**。
    if "QM_NO_GUI_PICK" not in _read("tools/smoke.py"):
        fe_bad.append("smoke 未关断原生目录框（自动化环境会弹窗挂起）")

    check(not fe_bad, "模板前端批 V0.0.38",
          f"缺失：{', '.join(fe_bad)}" if fe_bad
          else "绑定 UI / 2500ms 轮询+变化判据 / 右键菜单 / 导入导出接线 / 页面断言 齐备")

    # 7ag. 皮肤体系守卫批（V0.0.39，§十三.3 对比度 / §十三.4 swatch 绑定）
    #      三件事：
    #      ① `--qm-btn-bg-hi` 必须在 tokens.css 定义并被 base.css 的 `.btn-primary:hover`
    #         使用，且 `.btn-primary:hover` **不得**再拿 `--qm-accent-ink` 当底色
    #         （那是「墨色」，暗色皮肤下为浅色，配 `--qm-on-accent` 必翻车）；
    #      ② 16 款皮肤的 `--qm-btn-bg-hi` 与 `--qm-danger` 必须**各自显式给出**
    #         （继承 tokens 默认会与本皮肤色系不符）；
    #      ③ 页面层的 swatch 排序断言（`skinOrder` + 独立复算函数）不得被摘除。
    #         该断言反过来把「swatch 与 CSS 绑定」落到**运行期可见效果**上。
    skin_bad: list[str] = []
    tokens_css = _read("src/web/css/tokens.css")
    base_css = _read("src/web/css/base.css")
    bs_skin = _read("tools/browser_smoke.py")
    if tokens_css.count("--qm-btn-bg-hi") < 2:
        skin_bad.append("tokens.css 缺 --qm-btn-bg-hi（浅/深两套各需一条）")
    hover_block = re.search(r"\.btn-primary:hover[^{]*\{[^}]*\}",
                            strip_comments(base_css, "css"))
    if not hover_block:
        skin_bad.append("base.css 缺 .btn-primary:hover 规则")
    else:
        if "var(--qm-btn-bg-hi)" not in hover_block.group(0):
            skin_bad.append(".btn-primary:hover 未改用 --qm-btn-bg-hi")
        if "--qm-accent-ink" in hover_block.group(0):
            skin_bad.append(".btn-primary:hover 又把「墨色」当按钮底色（对比度会翻车）")
    _skins_dir_v = root / "src/web/css/skins"
    _skin_files_v = sorted(p for p in _skins_dir_v.glob("s*.css")) if _skins_dir_v.is_dir() else []
    missing_hi = [p.stem for p in _skin_files_v
                  if "--qm-btn-bg-hi" not in p.read_text(encoding="utf-8")]
    if missing_hi:
        skin_bad.append(f"皮肤缺 --qm-btn-bg-hi：{', '.join(missing_hi[:3])}")
    for token, why in (
        ("skinOrder", "browser_smoke 缺皮肤排序抓取（swatch 唯一可见效果）"),
        ("def expected_skin_order", "browser_smoke 缺期望序列独立复算（删掉即退化为自证）"),
    ):
        if token not in bs_skin:
            skin_bad.append(why)
    # 7d-8 / 7d-9 的「防静默摘除」元检查（§十三.6 机器化约定 / §P2 第 45 项）。
    # ⚠ 判据必须查**运行时已注册的判项名**（`results`，由 `check()` 追加），
    #   **不可**查源码字符串 —— 后者是**自证**：被判串必然在本元检查**自己的字面量 /
    #   条件表达式**里再出现一次 ⇒ 文件里恒存在 ⇒ 永远绿。
    #   此坑由反向验证 **N5 / N7** 实测抓到：**N7** 证明本条原为**存量死检查**
    #   （改掉 7d-8 的 `check(...)` 整串后，「皮肤体系守卫批」**不红**）；**N5** 证明
    #   新写的 7d-9 元检查照抄该模式后同样死。两处现统一改为查 `results`。
    _ran_names = {name for _ok, name, _note in results}
    for _guard in ("皮肤三阶落差统一 V0.0.46",
                   "皮肤顶层只许 :root + 变量声明 §P0-3 L5"):
        if _guard not in _ran_names:
            skin_bad.append(f"未执行守卫「{_guard}」（防静默摘除 · 反向验证 N5/N7）")

    check(not skin_bad, "皮肤体系守卫批 V0.0.39",
          f"缺失：{', '.join(skin_bad)}" if skin_bad
          else f"hover 专用底色 / {len(_skin_files_v)} 款皮肤显式取值 / 页面排序断言 齐备")

    # 7ah. 进度状态表的版本字段与 VERSION 一致（V0.0.48）。
    #      背景：`docs/任务进度.md` 的「当前状态」表是「当前做到哪一步」的权威答案，
    #      但它是一大块**逐版追加的长散文**，行极易漏 —— 已**实质滞后两次**：
    #      V0.0.39→V0.0.41（5 处，见该文件时间线）、V0.0.46→V0.0.47（当前版本 / 主线 /
    #      回退点 / 已封存 四行全停在上版）。教训同 §三.30：**否定性断言要能被机器推翻**。
    #      判据：三行各自**首个** V-版本号必须 == `VERSION`。
    #      不纳入：已封存版本 / 未决事项 / 下一步候选（天然含大量历史版本号）；
    #      也不纳入「N 项」计数 —— 它会随本文件新增守卫自变，属自指，机器无法自洽。
    prog_bad: list[str] = []
    ver_txt = _read("VERSION").strip()
    if not ver_txt:
        prog_bad.append("VERSION 未读到")
    else:
        for rel, row, why in (
            ("docs/任务进度.md", "| 当前版本 |", "任务进度「当前版本」行"),
            ("docs/任务进度.md", "| 主线 |", "任务进度「主线」行"),
            ("docs/任务进度.md", "| 回退点 |", "任务进度「回退点」行"),
            ("README.md", "- 当前版本：", "README「当前版本」行"),
            ("docs/项目手册.md", "更新日期：", "手册头部行"),
        ):
            rel_txt = _read(rel)
            if not rel_txt:
                prog_bad.append(f"{rel} 未读到")
                continue
            row_txt = next((ln for ln in rel_txt.splitlines() if ln.startswith(row)), "")
            if not row_txt:
                prog_bad.append(f"未找到{why}")
                continue
            m_ver = re.search(r"V\d+\.\d+\.\d+", row_txt)
            if not m_ver:
                prog_bad.append(f"{why}无版本号")
            elif m_ver.group(0) != ver_txt:
                prog_bad.append(f"{why}首版本 {m_ver.group(0)} ≠ VERSION {ver_txt}")
    # 同理：「偏好键名三方一致」守卫一旦被整体摘除，§P0-3 L6 的多处漂移会重新隐身，
    # 而它自己无法自检（那段代码已不在）→ 由本段做元检查（同 7ag 对 7d-8 的做法）。
    if "偏好键名三方一致" not in _read("tools/verify.py"):
        prog_bad.append("verify.py 缺偏好键三方一致守卫（2026-10-15 · §P0-3 L6）")
    # 同理：「图标系统契约」守卫被整体摘除后，图标册 / 字形白名单的漂移会重新隐身。
    if "图标系统契约" not in _read("tools/verify.py"):
        prog_bad.append("verify.py 缺图标系统守卫（2026-10-15 · §P0-3 L8）")
    check(not prog_bad, "进度状态表与 VERSION 一致 V0.0.48",
          "；".join(prog_bad) if prog_bad
          else f"任务进度 3 行 + README + 手册头部，首版本均为 {ver_txt}")

    # 7ai. 偏好键名「三方一致」（2026-10-15 · UI 设计约定检查 · §P0-3 L6）。
    #      背景：§P0-3 L6 的偏好键清单有**三处载体** —— 实现（`i18n/index.js` 的
    #      `export const *_KEY = 'qm.*'` 声明）、守卫（本文件 `PREF_KEYS`）、约定
    #      （`docs/项目约定.md` §P0-3 L6 规则行）。实测三处曾各不相同（实现 5 / 守卫 4 /
    #      文档 3 / 本文件摘要 2、`i18n` 头部注释 3 —— **同一约定出现五个数字**），且
    #      `qm.launchIcon`（V0.0.15 引入）长期不在守卫覆盖面内（盲区）。故本守卫把三者
    #      绑死：键**集合**相等（顺序无关），新增 / 删除偏好键必须三处同改。
    #      教训同 §三.30：否定性断言要能被机器推翻 ——「文档说三键」与「守卫断言四键」
    #      这种**描述与实现不符**，靠人读是发现不了的。
    #      2026-10-16（V0.0.51@r9）补一处**解析边界**：该规则行后半段是解释与沿革，
    #      撤销一个偏好键时必然要在那里写明「哪个键退场」—— 而整行收集会把退场键
    #      当成仍在用的键，7ai 立刻误报。故只解析「**本行是权威清单**」之前的枚举段。
    pref_bad: list[str] = []
    _i18n_txt = _read("src/web/js/i18n/index.js")
    # 引号类型须两种都认 —— `i18n` 的 `_KEY` 用**单引号**、`PREF_KEYS` 用**双引号**；
    # 首版只认单引号，致守卫侧恒为空集（2026-10-15 本守卫首跑即自曝 → 《错误笔记》§三.72）。
    pref_impl = set(re.findall(r"^export const \w+_KEY\s*=\s*['\"](qm\.[A-Za-z]+)['\"];",
                               _i18n_txt, re.M))
    _vf_txt = _read("tools/verify.py")
    _m_pk = re.search(r"PREF_KEYS\s*=\s*\(([^)]*)\)", _vf_txt)
    pref_guard = set(re.findall(r"['\"](qm\.[A-Za-z]+)['\"]", _m_pk.group(1))) if _m_pk else set()
    _conv_txt = _read("docs/项目约定.md")
    _l6_row = next((ln for ln in _conv_txt.splitlines() if ln.startswith("| L6 |")), "")
    # ⚠ 只取「权威清单」标记**之前**的枚举段。该行后半段是解释与沿革，会写到**已退场**
    # 的键（如 V0.0.51@r9 退场的生成栏折叠态键）—— 若整行一并收集，退场键会被当成仍
    # 在用的键，7ai 立刻误报「实现 ≠ 文档」。锚点用行内自述的分界语「本行是权威清单」，
    # 它本就是这条约定自己划的界限。锚点缺失时退化为整行（与旧行为一致，不静默变松）。
    _l6_list = _l6_row.split("**本行是权威清单**")[0]
    pref_doc = set(re.findall(r"`(qm\.[A-Za-z]+)`", _l6_list))
    if not pref_impl:
        pref_bad.append("i18n/index.js 未解析到 _KEY 声明")
    if not pref_guard:
        pref_bad.append("verify.py 未解析到 PREF_KEYS")
    if not pref_doc:
        pref_bad.append("§P0-3 L6 规则行未解析到键名")
    if pref_impl and pref_guard and pref_impl != pref_guard:
        pref_bad.append(f"实现 {sorted(pref_impl)} ≠ 守卫 {sorted(pref_guard)}")
    if pref_impl and pref_doc and pref_impl != pref_doc:
        pref_bad.append(f"实现 {sorted(pref_impl)} ≠ 文档 {sorted(pref_doc)}")
    check(not pref_bad, "偏好键名三方一致 §P0-3 L6",
          "；".join(pref_bad) if pref_bad
          else f"实现 / 守卫 / §P0-3 L6 三方均 {len(pref_impl)} 键："
               f"{' / '.join(sorted(pref_impl))}")

    # 7aj. 图标系统契约（2026-10-15 · UI 图标设计约定检查 · §P0-3 L8）。
    #      背景：项目「图标」概念盘上有 **4 条并行实现路径**，而 §P0-3 L8 原只覆盖
    #      「SVG 资源」两支，且**无任何机器判据**：
    #        A 形状内联 data-URI（`base.css` 的 `.ic-*`，声明局部 `--m`）—— 23 个
    #        B 形状存 `tokens.css` 变量（`--qm-select-arrow-mask`）—— 1 个
    #        C 形状指向文件（`.brand-logo` → `assets/logo.svg`）—— 1 个
    #        D **文字字形**（`.caret` U+25BE，服务 chip 的下三角）—— **1 处**（V0.0.52 后），
    #          此前**无任何成文记载**。V0.0.51@r9：`#genCaret`（U+25BC·U+25B6）随生成参数区
    #          折叠撤销而退场（白名单 5 个字符 → 3 个）；V0.0.52：`.tree-icon` 的
    #          📁 / 📄（U+1F4C1·U+1F4C4）归一为 `.ic-folder` / `.ic-file` mask
    #          （白名单 3 个字符 → 1 个）。**本条只许缩小、不许长大。**
    #      且 `base.css` 头注释断言「图标**全部**为 currentColor SVG mask」—— 对 B / C
    #      的着色描述已不准（B 取 `--qm-text-dim`、C 取 `--qm-accent-ink`），对 D 直接为假。
    #      判据只锚**声明形态**、不锚裸字面量（§三.69 / §三.71：本仓库注释习惯逐字复述
    #      类名与字符，裸查必大量假阳性）；字形抽取**全程不写正则反斜杠**（§三.72）。
    ic_bad: list[str] = []
    # 图标册（形状类）—— base.css 定义域 / 本元组 / §P0-3 L8 规则行，**三方一致**（同 7ai）。
    # V0.0.50 · I 组：工作区按钮由文字改为纯线性图标，形状表按设计稿补齐 → 7 → 21。
    # V0.0.52：树行图标归一，补 `.ic-folder` / `.ic-file` → 21 → **23**。
    # 设计稿另备 ic-checkbox / ic-export / ic-load，本项目无对应控件，**故意不引入**
    # （引入即「定义了但无人使用」，本段 ① 会立刻报出来）。
    ICON_SHAPES = ("ic-globe", "ic-heart", "ic-help", "ic-gear",
                   "ic-close", "ic-check", "ic-more",
                   "ic-folder", "ic-folder-plus", "ic-folder-open", "ic-file", "ic-refresh",
                   "ic-undo", "ic-redo", "ic-node-plus", "ic-pencil", "ic-trash",
                   "ic-expand-all", "ic-collapse-all", "ic-copy",
                   "ic-import", "ic-save", "ic-spark")
    # 字形图标白名单（**新代码禁止新增** —— 新图标一律走 `.ic` mask；D 类不许再长大）。
    # V0.0.51@r9：`#genCaret` 的实心下 / 右三角随折叠撤销退场。
    # V0.0.52：`.tree-icon` 的 📁 / 📄 归一为 `.ic-folder` / `.ic-file` mask ⇒ **再减 2 个**。
    # 现仅剩服务 chip 的下三角 —— 本条只减不增，若将来连它也 mask 化，本元组应为空。
    GLYPH_ICONS = (chr(0x25BE),)                 # 下三角 .caret（#chipBackend 服务 chip）
    # 顶栏操作区图标按钮：除可访问名外**另须** tooltip（《项目手册》§九.2-2 / §十四.1）。
    TOPBAR_ICON_IDS = ("btnLang", "btnSkin", "btnSupport", "btnHelp", "btnMore")

    _idx_html = _read("src/web/index.html")
    _ic_css = strip_comments(_read("src/web/css/base.css"), "css")

    def _ic_lits(body: str) -> list[str]:
        """只收集**类名声明形态**的字面量（class= / className= / classList.add）。
        不用含反斜杠转义的引号字符类 —— 本环境该形态在写盘通道会被改写（§三.72）。"""
        out = re.findall(r'class="([^"]*)"', body)
        out += re.findall(r"class='([^']*)'", body)
        out += re.findall(r"className\s*=\s*'([^']*)'", body)
        out += re.findall(r'className\s*=\s*"([^"]*)"', body)
        out += re.findall(r"classList\.add\('([^']*)'\)", body)
        out += re.findall(r'classList\.add\("([^"]*)"\)', body)
        return out

    # ① 定义 ↔ 使用 双向配对（「定义未使用」与「使用未定义」都要报）。
    # V0.0.50 修正：原式为 `(?:-[a-z0-9]+)?`，**只允许一个连字符** —— 于是
    # `.ic-expand-all` / `.ic-folder-plus` / `.ic-node-plus` 这类双连字符形状
    # **根本抽不到**（此前 7 枚全为单连字符，缺陷从未暴露；I 组一落地即现形）。
    # 判据锚「`.ic` 开头的类名声明形态」，故改为可重复的 `(?:-[a-z0-9]+)*`。
    ic_defined = set(re.findall(r"\.(ic(?:-[a-z0-9]+)*)(?![\w-])", _ic_css))
    ic_used: dict[str, set[str]] = {}
    for _p in sorted((root / "src/web").rglob("*")):
        if not _p.is_file() or _p.suffix not in (".html", ".js"):
            continue
        _rel = str(_p.relative_to(root)).replace(chr(92), "/")
        _body = _p.read_text(encoding="utf-8", errors="ignore")
        for _lit in _ic_lits(_body):
            for _tok in _lit.split():
                # V0.0.50 修正：同 `ic_defined` —— 单连字符写法漏掉 `ic-expand-all`
                # 这类双连字符形状，会把「已使用」误判为「定义未使用」。
                if re.fullmatch(r"ic(?:-[a-z0-9]+)*", _tok):
                    ic_used.setdefault(_tok, set()).add(_rel)
        # V0.0.53 补：**间接引用**也要算「使用」。保存状态 chip 的图标名不写在
        # `className = '…'` 里，而是存在 `SAVE_CHIP_ICON` 这张**表**中、由模板串拼出
        # —— 上面那条只认「类名声明形态」，故表里的名字对守卫**完全隐形**。
        # 后果不小：名字一写错 ⇒ `--m` 取不到 ⇒ `mask` 整条声明失效 ⇒ 该处渲染成
        # 一个 14×14 **实心方块**（`.ic` 的 `background-color: currentColor` 仍在）。
        # 故对 JS 补扫「形如 ic-xxx 的**引号包裹**字面量」，且**先剥注释**
        # （注释里提一句名字不算使用）。只放宽**「使用」**方向，另一半判据不动。
        if _p.suffix == ".js":
            for _tok in re.findall(r"['\"`](ic(?:-[a-z0-9]+)*)['\"`]",
                                   strip_comments(_body, "js")):
                ic_used.setdefault(_tok, set()).add(_rel)
    for _miss in sorted(ic_defined - set(ic_used)):
        ic_bad.append(f"base.css 定义了 .{_miss} 但无人使用")
    for _miss in sorted(set(ic_used) - ic_defined):
        ic_bad.append(f"{'/'.join(sorted(ic_used[_miss]))} 用了未定义的 .{_miss}")

    # ② 形状类须声明 `--m`；尺寸修饰符 `.ic-sm` 不得声明；基类 `.ic` 须消费 `var(--m)`。
    for _shape in ICON_SHAPES:
        _blk = re.search(r"\." + _shape + r"\s*\{[^}]*\}", _ic_css)
        if not _blk or not re.search(r"--m\s*:", _blk.group(0)):
            ic_bad.append(f".{_shape} 未声明 --m（形状只能经 mask 提供）")
    _sm_blk = re.search(r"\.ic-sm\s*\{[^}]*\}", _ic_css)
    if _sm_blk and re.search(r"--m\s*:", _sm_blk.group(0)):
        ic_bad.append(".ic-sm 是尺寸修饰符，不得声明 --m")
    _base_blk = re.search(r"\.ic\s*\{[^}]*\}", _ic_css)
    if not _base_blk or "var(--m)" not in _base_blk.group(0):
        ic_bad.append(".ic 未消费 var(--m)")

    # ③ `.ic*` 规则块不得用 background-image（形状只能走 mask，禁位图 / 图片图标）。
    for _blk in re.findall(r"\.ic(?:-[\w-]+)?\s*\{[^}]*\}", _ic_css):
        if "background-image" in _blk:
            ic_bad.append("图标规则用了 background-image：" + _blk[:48])

    # ④ 全 src 禁 `<img>` 引 SVG（§P0-3 L8：`<img>` 内 currentColor 不继承）
    #    与 `@font-face`（第三方图标字体，版权合规）。注释先剥离，免误伤说明文字。
    for _p in sorted((root / "src").rglob("*")):
        if not _p.is_file() or _p.suffix not in (".html", ".css", ".js"):
            continue
        _rel = str(_p.relative_to(root)).replace(chr(92), "/")
        _raw = _p.read_text(encoding="utf-8", errors="ignore")
        if _p.suffix == ".html":
            _scan = re.sub(r"<!--.*?-->", "", _raw, flags=re.S)
        else:
            _scan = strip_comments(_raw, "css" if _p.suffix == ".css" else "js")
        if "@font-face" in _scan:
            ic_bad.append(f"{_rel} 含 @font-face（禁用图标字体）")
        for _img in re.findall(r"<img[^>]*>", _scan, re.I):
            if "src=" in _img and ".svg" in _img.lower():
                ic_bad.append(f"{_rel} 用 <img> 引 SVG：{_img[:40]}")

    # ⑤ 图标按钮：可访问名必填；顶栏操作区另须 tooltip（把手册 §十四.1 由建议升为判据）。
    #    V0.0.50 起覆盖面含工作区的纯图标按钮 `.btn-ic`（此前只扫顶栏 / 弹窗的 `.icon-btn`，
    #    而 I 组落地后界面上的图标按钮达 29 颗；不扩面就等于给新按钮开了一条无守卫通道）。
    _ic_btns = re.findall(r'<button[^>]*class="[^"]*(?:icon-btn|btn-ic)[^"]*"[^>]*>',
                          _idx_html, re.S)
    for _tag in _ic_btns:
        _m_id = re.search(r'id="([^"]+)"', _tag)
        _bid = _m_id.group(1) if _m_id else "(匿名)"
        if "aria-label=" not in _tag and "data-i18n-aria-label=" not in _tag:
            ic_bad.append(f"icon-btn#{_bid} 缺可访问名（aria-label / data-i18n-aria-label）")
        if _bid in TOPBAR_ICON_IDS and "title=" not in _tag and "data-i18n-title=" not in _tag:
            ic_bad.append(f"顶栏 icon-btn#{_bid} 缺 tooltip（title / data-i18n-title）")
    for _bid in TOPBAR_ICON_IDS:
        if 'id="' + _bid + '"' not in _idx_html:
            ic_bad.append(f"index.html 已无顶栏图标按钮 #{_bid}（守卫清单须同步）")

    # ⑤b. **动态**图标按钮的可访问名（V0.0.51@r11 · 补 ⑤ 的盲区）。
    #      ⑤ 只扫 `src/web/index.html` 的**静态**标记，而模板行行尾 ⋮ 由
    #      `modules/templates.js` **动态创建** ⇒ 静态扫描天然扫不到 —— 等于给「JS 造出来的
    #      图标按钮」开了一条无守卫通道（本批勘察实测确认）。故改从**产出方源码**判。
    #      顺带把「⋮ 与右键**同源**」（复用同一函数、不另造菜单、CSS 两处配对）机器化 ——
    #      那是本批采纳「丙-1」的**核心不变量**，也是设计稿「行尾 ⋮：打开既有 #ctxMenu……
    #      不另造一套」的落地保证。判据实现见模块级 `template_row_more_violations()`（可单测）。
    ic_bad.extend(template_row_more_violations(
        strip_comments(_read("src/web/js/modules/templates.js"), "js"),
        strip_comments(_read("src/web/css/layout.css"), "css"),
        strip_comments(_read("src/web/css/soft.css"), "css")))

    # ⑥ 字形图标白名单：只从**声明形态**抽取，实况集合必须 == 白名单（新增即 FAIL）。
    ic_glyphs: list[str] = []

    def _de_u(js: str) -> str:
        """把 JS 源码里的 uXXXX 转义（含代理对）还原为真实字符。"""
        _t = js.encode("utf-8").decode("unicode_escape")
        return _t.encode("utf-16", "surrogatepass").decode("utf-16")

    for _g in re.findall(r"const CARET_(?:OPEN|CLOSED)\s*=\s*'([^']*)'",
                         _read("src/web/js/main.js")):
        ic_glyphs.append(_de_u(_g))
    # ⚠ V0.0.52：树行图标已由 emoji 归一为 `.ic` mask ⇒ 下式**当前恒无命中**。
    #   但它**刻意保留**：「谁把 emoji 写回来」正是本条唯一的看守对象。下式在，
    #   则 `icon.textContent = dir ? '📁' : '📄'` 一写回，字形集合立刻多出两个未登记
    #   字符，本段当场 FAIL；下式删掉，emoji 回流便无人看守 —— 等于把刚做完的归一
    #   重新交还给纪律（同 §三.86：把「已移除」写成史实之前，先确认看守还在不在）。
    for _a, _b in re.findall(r"textContent\s*=\s*dir\s*\?\s*'([^']*)'\s*:\s*'([^']*)'",
                             _read("src/web/js/ui/tree-view.js")):
        ic_glyphs.append(_de_u(_a))
        ic_glyphs.append(_de_u(_b))
    for _cp in re.findall(r'class="caret"[^>]*>&#(\d+);', _idx_html):
        ic_glyphs.append(chr(int(_cp)))
    for _g in sorted(set(ic_glyphs) - set(GLYPH_ICONS)):
        ic_bad.append(f"新增字形图标 U+{ord(_g):04X} 未登记 —— 新图标须走 .ic mask")
    for _g in GLYPH_ICONS:
        if _g not in ic_glyphs:
            ic_bad.append(f"白名单字形 U+{ord(_g):04X} 已不在源码中（白名单须同步）")

    # ⑦ 图标册三方一致：base.css 形状类 == 本元组 == §P0-3 L8 规则行（标「图标册」者）。
    # ⚠ 抽取口径：该行里**反引号包裹**的 `ic-*` 才算册内条目 ⇒ 该行的**权威枚举只能有一处**，
    #   沿革 / 修订注记里提到的形状名**一律不加反引号**（本行原本就这么处置设计稿那三枚
    #   备选名，并写明理由）。V0.0.52 本批**实测踩到过**：我在修订注记里又写了一次
    #   「（补 `ic-folder` / `ic-file`）」，于是把权威枚举里那份的反引号摘掉后，集合仍是 23、
    #   本项照旧 PASS —— 反向验证 **R4** 当场不命中才暴露「同一个名字在行内出现两次」。
    #   教训同 7ai 的「退场键被当成仍在用的键」：**收集式判据必须先划定唯一的权威区段**，
    #   否则判据会被**自己写的沿革文字**喂饱，看起来在把关、实际上永远绿。
    ic_css_shapes = {_s for _s in ic_defined if _s.startswith("ic-") and _s != "ic-sm"}
    if ic_css_shapes != set(ICON_SHAPES):
        ic_bad.append(f"图标册漂移：base.css {sorted(ic_css_shapes)} ≠ 守卫 {sorted(ICON_SHAPES)}")
    _l8_row = next((_ln for _ln in _read("docs/项目约定.md").splitlines()
                    if _ln.startswith("| L8 |") and "图标册" in _ln), "")
    if not _l8_row:
        ic_bad.append("§P0-3 L8 未标出「图标册」权威清单行")
    else:
        ic_doc_shapes = {_s for _s in re.findall(r"`(ic-[a-z0-9-]+)`", _l8_row)
                         if _s != "ic-sm"}
        if ic_doc_shapes != set(ICON_SHAPES):
            ic_bad.append(f"图标册漂移：实现/守卫 {sorted(ICON_SHAPES)} ≠ §P0-3 L8 {sorted(ic_doc_shapes)}")

    check(not ic_bad, "图标系统契约 §P0-3 L8",
          "；".join(ic_bad) if ic_bad
          else f"{len(ICON_SHAPES)} 个 mask 形状定义↔使用配对 / "
               f"{len(_ic_btns)} 个静态图标按钮可访问名齐备 / "
               f"字形图标 {len(GLYPH_ICONS)} 个未增长 / 动态按钮（⋮）接线同源")

    # 8. 接续说明实况段须与盘上一致（§P1-6 H4；文件未建立则跳过，不阻塞预览目录的校验）
    handoff_file = root / "docs/接续说明.md"
    if handoff_file.is_file():
        try:
            from handoff import git as hgit, render_live, replace_block, split_tags
            raw = handoff_file.read_text(encoding="utf-8")
            body = render_live(root)
            same = replace_block(raw, body) == raw
            check(same, "接续说明实况段", "与盘上一致" if same else "已过期，运行 python tools/handoff.py")

            # 8c. 实况段两处渲染失真守卫（不升版，2026-10-10；源自《审查报告_工具链_20261010》§P1-3）
            #     自洽检查（上一项）只能证「未过期」，证不了「内容正确」—— 这两项补上。
            #     P1-3a：旧实现只用 `git tag -l "V*-r*"` → 版本 tag 全部缺席，
            #            接手方会误以为最新 tag 停在 V0.0.1-r3；
            #     P1-3b：日期正则不容忍 `（续十五）` 后缀 → 「时间线最新」日期恒为 (未标日期)。
            if hgit(root, "rev-parse", "--is-inside-work-tree") is not None:
                # git 不可用（如无 .git 的副本）时渲染器本就降级为「未初始化仓库」——不误报
                tag_line = next((ln for ln in body.splitlines() if ln.startswith("**版本 tag**")), "")
                vtags, _rtags = split_tags(root)
                ver_file8 = root / "VERSION"
                cur_ver = ver_file8.read_text(encoding="utf-8").strip() if ver_file8.is_file() else ""
                if cur_ver and cur_ver in vtags:
                    # 当前版本已打 tag：必须出现在行内（正常发布后的稳态）
                    tag_ok = f"`{cur_ver}`" in tag_line
                    tag_why = f"版本 tag 行漏列当前 {cur_ver}"
                else:
                    # 当前版本尚未打 tag（发布流中途：bump 后、git tag 前）——
                    # 此时不要求含 VERSION，否则会在**合法的中间态**产生假红；
                    # 但仍必须至少列出一个形态合法的版本 tag（正是旧实现的缺陷所在）。
                    tag_ok = bool(re.search(r"V\d+\.\d+\.\d+", tag_line))
                    tag_why = "版本 tag 行无任何版本 tag（旧实现只列 V*-r* 的回潮）"
                check(tag_ok, "实况段·版本 tag 行",
                      f"{len(vtags)} 个版本 tag，最新 {vtags[-1]}" if tag_ok and vtags else tag_why)

            tl_line = next((ln for ln in body.splitlines() if ln.startswith("**时间线最新**")), "")
            if tl_line:
                # 正则已能容忍 `### 2026-10-10（续十五）` 这类带后缀标题（§P1-3b）
                check("(未标日期)" not in tl_line, "实况段·时间线日期",
                      tl_line.split("：", 1)[-1][:40] if "(未标日期)" not in tl_line
                      else f"日期未解析：{tl_line}")
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            check(False, "接续说明实况段", f"无法生成：{exc}")

    # 8b. 源码 § 引用必须能解析到 docs 中真实存在的编号（防「悬空引用」复发 —— 《错误笔记》§三.22；
    #     约定文档不在（预览目录）则跳过）
    if (root / "docs" / "项目约定.md").is_file():
        refs = collect_src_refs(root)
        known = defined_section_labels(root)
        dangling = {lab: locs for lab, locs in refs.items() if lab not in known}
        if dangling:
            detail = "；".join(f"`{lab}`（{locs[0]}）" for lab, locs in sorted(dangling.items()))
            check(False, "源码 § 引用可解析", f"指向不存在的编号：{detail}")
        else:
            check(True, "源码 § 引用可解析",
                  f"{len(refs)} 个编号全部可解析 —— " + " / ".join(sorted(refs)))

    # 9. 编辑态持久化：共享契约、接口标识与错误码齐备（§P0-7）
    schema_file = root / "src/shared/schema.json"
    contract_ok = False
    contract_note = "schema.json 未读到"
    if schema_file.is_file():
        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except ValueError:
            schema = None
        if isinstance(schema, dict):
            absent_keys = [k for k in ("editorDocument", "editorNode") if k not in schema]
            contract_ok = not absent_keys
            contract_note = (f"schema.json 缺少：{', '.join(absent_keys)}" if absent_keys
                             else "editorDocument / editorNode 齐备")
        else:
            contract_note = "schema.json 无法解析"
    check(contract_ok, "编辑态契约", contract_note)

    # 9a. 共享契约版本戳必须与 VERSION 同步（防「契约漂移」—— 全项目审查 P2-1）。
    # schema.json 是对外数据契约，其 version 应随版本推进同步；停在旧版即漂移。
    ver_file = root / "VERSION"
    contract_ver: str | None = None
    if schema_file.is_file():
        try:
            _s = json.loads(schema_file.read_text(encoding="utf-8"))
            _v = _s.get("version") if isinstance(_s, dict) else None
            contract_ver = _v if isinstance(_v, str) else None
        except ValueError:
            contract_ver = None
    if not ver_file.is_file():
        check(True, "共享契约版本戳", "无 VERSION 文件（预览目录），跳过")
    elif contract_ver is None:
        check(False, "共享契约版本戳", "schema.json 缺 version 字段或无法解析")
    else:
        cur_ver = ver_file.read_text(encoding="utf-8").strip()
        same_ver = contract_ver == cur_ver
        check(same_ver, "共享契约版本戳",
              (f"schema.json version={contract_ver} 与 VERSION 一致" if same_ver
               else f"漂移：schema.json version={contract_ver} ≠ VERSION {cur_ver}（须同步）"))

    anchors = (
        ("src/server/config.py", "EDITOR_FILE"),
        ("src/server/config.py", "EDITOR_BACKUP_KEEP"),   # V0.0.26 轮转备份
        ("src/server/routes.py", "EDITOR_PATH"),
        ("src/server/routes.py", "_backup_editor"),       # V0.0.26 轮转备份
        ("src/server/app.py", "do_PUT"),
        ("src/web/js/core/api.js", "saveDoc"),
    )
    absent = []
    for rel, token in anchors:
        target = root / rel
        if not target.is_file() or token not in target.read_text(encoding="utf-8"):
            absent.append(f"{rel}:{token}")

    codes_file = root / "src/shared/error-codes.json"
    codes_ok = False
    if codes_file.is_file():
        try:
            codes = json.loads(codes_file.read_text(encoding="utf-8"))
            codes_ok = isinstance(codes, dict) and "editorIdDuplicated" in codes
        except ValueError:
            codes_ok = False
    if not codes_ok:
        absent.append("error-codes.json:editorIdDuplicated")

    check(not absent, "编辑态接口与错误码",
          f"缺失：{', '.join(absent)}" if absent else "config / routes / app / api / 错误码 齐备")

    # 9b. 落盘安全边界（§P0-1）：边界必须落在服务端，不得只做前端限制
    guard_anchors = (
        ("src/server/config.py", "BLOCKED_SUBTREES"),
        ("src/server/config.py", "MAX_NODES"),
        ("src/server/dtree_core.py", "check_target"),
        ("src/server/routes.py", "check_target"),
    )
    guard_absent = []
    for rel, token in guard_anchors:
        target = root / rel
        if not target.is_file() or token not in target.read_text(encoding="utf-8"):
            guard_absent.append(f"{rel}:{token}")
    if codes_file.is_file():
        try:
            codes = json.loads(codes_file.read_text(encoding="utf-8"))
        except ValueError:
            codes = {}
        for code in ("targetTooShallow", "targetBlocked", "targetReserved", "tooManyNodes"):
            if not isinstance(codes, dict) or code not in codes:
                guard_absent.append(f"error-codes.json:{code}")
    else:
        guard_absent.append("error-codes.json:未读到")
    check(not guard_absent, "落盘安全边界 §P0-1",
          f"缺失：{', '.join(guard_absent)}" if guard_absent
          else "config 黑名单 / dtree_core.check_target / routes 接线 / 错误码 齐备")

    # 9c. 回归测试网（§P0-2）：仅在项目根（含 tests/）校验，预览目录自动跳过
    if (root / "tests").is_dir():
        net_missing = [rel for rel in (
            "tests/test_dtree_core.py", "tests/test_routes.py",
            "tests/test_config.py", "tests/test_launch_icon.py",
            "tests/test_store.py", "tests/test_versioning.py",
            "tests/test_browser_smoke.py", "tests/test_handoff.py",
            "tests/test_verify.py", "tests/test_promote.py",
            "tests/test_smoke.py", "tests/test_frontend_js.py",
            "tests/test_pack_templates.py",
            "tools/smoke.py", "tools/browser_smoke.py",
            "tools/pack_templates.py",
        ) if not (root / rel).is_file()]
        n_modules = len(sorted((root / "tests").glob("test_*.py")))
        # 轻量内容判据（§P2-17）：文件在 ≠ 内含用例；防「空壳测试文件」蒙混过关。
        hollow = [p.name for p in sorted((root / "tests").glob("test_*.py"))
                  if "def test_" not in p.read_text(encoding="utf-8")]
        net_bad = net_missing + [f"{name}（无用例）" for name in hollow]
        check(not net_bad, "回归测试网 §P0-2",
              f"缺失/空壳：{', '.join(net_bad)}" if net_bad
              else f"tests/ {n_modules} 模块（均含用例）+ tools/smoke.py + tools/browser_smoke.py 齐备")

    # 10. 与版本清单比对指纹（仅在指定 --against 时启用）
    if against:
        check_fingerprint(root, against)

    # 汇总
    width = max(len(name) for _, name, _ in results) + 2
    failed = 0
    print("-" * 78)
    for ok, name, note in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name.ljust(width)} {note}")
        if not ok:
            failed += 1
    print("-" * 78)
    print(f"[校验] 版本 {version_text or '?'} · 共 {len(results)} 项 · 失败 {failed} 项")
    if failed:
        print("[校验] 结论：不通过")
        return 1
    print("[校验] 结论：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
