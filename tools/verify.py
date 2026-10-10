"""青蔓 QingMan · 交付校验。

用法：
    python tools/verify.py [版本根目录]

「版本根目录」需包含 src/ 与 VERSION；缺省为脚本所在项目的根目录。
`--against <版本>` 的清单**只在该根目录之下的 versions/<版本>/ 查找**（不从项目根兜底）。
校验项与《错误笔记》交付清单一致：
  1. 必需文件存在
  2. HTML 标签闭合、关键 id 存在
  3. main.js 中引用的 id 在 index.html 中真实存在
  4. JS 语法（ESM 方式交由 node --check 解析）
  5. CSS 大括号平衡
  6. Python 语法（ast 只读解析，不产生 __pycache__，保证校验不污染被校验目录）
 7. 帮助页无硬编码中文（§P0-3 L1：文案必须经取词表，页面只留 data-i18n 键名）
 7b. 双语与皮肤预留（§P0-3）：主界面无硬编码中文 / JS 无中文串字面量 / 组件 CSS 无裸色值 /
     组件 CSS 不感知皮肤 / 皮肤目录契约 / 偏好键名 qm.lang · qm.skin
 7e. CSS 类名形态（§P2 第 1 项）：一律 kebab-case，不得含下划线或大写
 7f. 体积上限（§P2 第 4 项）：src/** 合计 ≤ 400K，单文件 ≤ 64K
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
     （仅项目根，预览目录跳过）
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
from store import collect_files as collect_tracked  # noqa: E402
from store import latest_revision, load_manifest, manifest_filename  # noqa: E402
from store import sha256_of  # noqa: E402

PAIRED_TAGS = (
    "html", "head", "body", "div", "section", "aside", "header", "footer",
    "main", "span", "button", "label", "ul", "li", "pre", "h1", "h2", "h3", "p", "code",
)

REQUIRED_IDS = (
    "topbar", "chipSave", "chipBackend", "btnHelp", "btnSupport", "btnLogo",
    "langSelect", "skinSelect",
    "sidebar", "templateList",
    "center", "genBar", "inRoot", "inTarget", "inDryRun",
    "toolbar", "btnAddChild", "btnRename", "btnDelete",
    "btnUndo", "btnRedo",
    "btnExpandAll", "btnCollapseAll", "btnGenerate",
    "treeCanvas", "statusText", "statusCount",
    "inspector", "propName", "propType", "propPath", "propDirs", "propFiles", "propDepth",
    "propNote", "btnCopyName", "btnCopyPath", "btnCopyNote",
    "genResult", "toastHost", "ctxMenu",
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
    "src/web/js/i18n/zh-CN.js",
    "src/web/js/i18n/en-US.js",
    "src/web/js/i18n/skins.js",
    "src/web/js/core/bus.js",
    "src/web/js/core/store.js",
    "src/web/js/core/api.js",
    "src/web/js/modules/tree-model.js",
    "src/web/js/ui/tree-view.js",
    "src/web/js/ui/inspector.js",
    "src/web/js/ui/toast.js",
)

CJK = re.compile(r"[\u4e00-\u9fff]")

# 二进制扩展名：换行检查豁免（PNG/JPEG 等含 CR 字节属正常）。
# 同时单文件体积上限仍约束它们（SRC_FILE_LIMIT）。
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
                   ".woff", ".woff2", ".ttf", ".otf", ".eot"}

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


def strip_comments(text: str, kind: str) -> str:
    if kind == "js":
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"(?m)^\s*//.*$", "", text)
    else:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def check_fingerprint(root: Path, version: str) -> None:
    """与 versions/<版本>/ 的**最高修订**清单逐文件比对 SHA-256。

    同版本多修订（§P0-6）下，r1 基线往往已落后于主线，因此默认对齐最新修订；
    需要比对某一具体修订时，改传 `版本@rN` 形式（如 `V0.0.1@r1`）。
    输出三态语义由 check() 的 ok 决定：一致 / 有差异（列出改动·新增·缺失）/ 无法判定。
    """
    if "@" in version:
        head, _, tag = version.partition("@")
        version = head.strip()
        tag = tag.strip().lstrip("r")
        rev = int(tag) if tag.isdigit() else None
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

    changed = [rel for rel, ref in recorded.items()
               if (root / rel).is_file() and sha256_of(root / rel) != ref.split(":", 1)[-1]]
    missing = [rel for rel in recorded if not (root / rel).is_file()]
    current = {rel for rel, _ in collect_tracked(root)}
    added = sorted(current - set(recorded))

    clean = not (changed or missing or added)
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
    if html:
        unbalanced = []
        for tag in PAIRED_TAGS:
            opens = len(re.findall(rf"<{tag}[\s>]", html))
            closes = len(re.findall(rf"</{tag}>", html))
            if opens != closes:
                unbalanced.append(f"{tag}({opens}/{closes})")
        check(not unbalanced, "HTML 标签闭合", ", ".join(unbalanced) if unbalanced else "全部平衡")

        missing = [i for i in REQUIRED_IDS if f'id="{i}"' not in html]
        check(not missing, "HTML 关键 id", ", ".join(missing) if missing else f"{len(REQUIRED_IDS)} 项齐全")
    else:
        check(False, "HTML 标签闭合", "index.html 未读到")
        check(False, "HTML 关键 id", "index.html 未读到")

    # 3. main.js 引用的 id 必须真实存在
    main_js = root / "src/web/js/main.js"
    if main_js.is_file() and html:
        used = sorted(set(re.findall(r"el\(['\"]([\w-]+)['\"]\)", main_js.read_text(encoding="utf-8"))))
        unknown = [i for i in used if f'id="{i}"' not in html]
        check(not unknown, "JS 引用的 id 均已定义", ", ".join(unknown) if unknown else f"{len(used)} 个引用全部命中")
    else:
        check(False, "JS 引用的 id 均已定义", "main.js 或 index.html 未读到")

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
    dict_file = root / "src/web/js/i18n/zh-CN.js"
    known: set[str] = set()
    if dict_file.is_file():
        known = set(re.findall(
            r"""['"]([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+)['"]""",
            dict_file.read_text(encoding="utf-8")))
    used_keys: dict[str, str] = {}
    for page in ("src/web/index.html", "src/web/help.html", "src/web/support.html"):
        page_file = root / page
        if not page_file.is_file():
            continue
        for key in re.findall(
                r'''data-i18n(?:-title|-placeholder|-aria-label)?="([^"]+)"''',
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
    zh_file = root / "src/web/js/i18n/zh-CN.js"
    en_file = root / "src/web/js/i18n/en-US.js"
    align_bad = ""
    if zh_file.is_file() and en_file.is_file():
        zh_keys = set(re.findall(KEY_SHAPE, zh_file.read_text(encoding="utf-8")))
        en_keys = set(re.findall(KEY_SHAPE, en_file.read_text(encoding="utf-8")))
        only_zh = sorted(zh_keys - en_keys)
        only_en = sorted(en_keys - zh_keys)
        if only_zh or only_en:
            align_bad = f"zh 独有 {len(only_zh)}：{', '.join(only_zh[:3])}；en 独有 {len(only_en)}：{', '.join(only_en[:3])}"
    elif not en_file.is_file():
        align_bad = "缺少 en-US.js"
    check(not align_bad, "中英取词键对齐 §P0-3 L1",
          align_bad if align_bad else "中英键集一致")

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
        for token in ("AUTO_LOCALE", "matchLocale", "resolveLocale", "watchLocale"):
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

    # 7c. 组件 CSS 只允许 var(--qm-*)（§P0-3 L4）
    HEX_LIKE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    raw_color = []
    for css in sorted((root / "src/web/css").glob("*.css")):
        if css.name == "tokens.css":
            continue   # 变量的唯一来源，字面量只能写在这里
        for m in HEX_LIKE.finditer(strip_comments(css.read_text(encoding="utf-8"), "css")):
            raw_color.append(f"{css.name}:{m.group(0)}")
    check(not raw_color, "组件 CSS 无裸色值 §P0-3 L4",
          f"发现 {len(raw_color)} 处：{', '.join(raw_color[:4])}" if raw_color
          else "组件样式全部经 var(--qm-*) 取色")

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
    #       皮肤文件例外：允许声明未在 tokens.css 定义的新变量（由 skins/<name>.css 自身覆盖）。
    tokens_file = root / "src/web/css/tokens.css"
    defined_vars: set[str] = set()
    if tokens_file.is_file():
        defined_vars = set(re.findall(r"(--qm-[\w-]+)\s*:",
                                      tokens_file.read_text(encoding="utf-8")))
    used_vars: dict[str, set[str]] = {}
    for css in sorted((root / "src/web/css").rglob("*.css")):
        if css.name == "tokens.css":
            continue
        if "skins" in css.parts:
            # 皮肤文件只检查 var() 使用，允许引入新变量；但为保持契约，仍建议引用 tokens 变量。
            pass
        body = strip_comments(css.read_text(encoding="utf-8"), "css")
        for m in re.finditer(r"var\(\s*(--qm-[\w-]+)\s*\)", body):
            used_vars.setdefault(css.name, set()).add(m.group(1))
    missing_vars = {
        name: sorted(vars_ - defined_vars)
        for name, vars_ in used_vars.items()
        if vars_ - defined_vars
    }
    if missing_vars:
        detail = "; ".join(f"{name}:{', '.join(missing[:3])}"
                           for name, missing in missing_vars.items())
    check(not missing_vars, "CSS 变量闭包 §P0-3 L4",
          f"引用未定义变量：{detail}" if missing_vars
          else "所有 --qm-* 引用均有 tokens.css 定义")

    skins_doc = root / "src/web/css/skins/README.md"
    check(skins_doc.is_file(), "皮肤目录契约 §P0-3 L5",
          "src/web/css/skins/ 与契约就位" if skins_doc.is_file()
          else "缺少 src/web/css/skins/README.md")

    prefs_js = root / "src/web/js/i18n/index.js"
    PREF_KEYS = ("qm.lang", "qm.skin", "qm.genBar")
    prefs_body = prefs_js.read_text(encoding="utf-8") if prefs_js.is_file() else ""
    prefs_missing = [key for key in PREF_KEYS if key not in prefs_body]
    check(not prefs_missing, "偏好键名 §P0-3 L6",
          " / ".join(PREF_KEYS) + " 齐备" if not prefs_missing
          else "i18n/index.js 缺少：" + ", ".join(prefs_missing))

    # 7d-2. 皮肤注册表与文件一一对应
    skin_errs = []
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
                prefix = f"s{m.group(1).zfill(2)}-"
                if not any(f.startswith(prefix) for f in files):
                    skin_errs.append(f"默认皮肤前缀 {prefix} 未注册")
        else:
            skin_errs.append("注册表缺少 DEFAULT_SKIN_CID")
    else:
        skin_errs.append("缺少 skins.js")
    def_note = "；".join(skin_errs) if skin_errs else f"{len(cids)} 款皮肤注册表与文件一致"
    if not skin_errs and cids:
        def_note += f"，默认 S{int(cids[5] if len(cids) > 5 else cids[0]):02d}"
    check(not skin_errs, "皮肤注册表 §P0-3 L5", def_note)

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

    # 7f. 体积上限（§P2 第 4 项）：src/** 合计 ≤ 400K，单文件 ≤ 64K
    SRC_TOTAL_LIMIT = 400 * 1024
    SRC_FILE_LIMIT = 64 * 1024
    src_files = [p for p in (root / "src").rglob("*") if p.is_file()]
    if src_files:
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
            p = root / "src/web/js/i18n" / name
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

    # 7m. 服务状态三态（V0.0.16：左栏自检收敛为顶栏「服务状态」三态）
    #     判据三端：① 左栏 checklist 已移除（页面不再有该清单元素）；
    #     ② 顶栏接线三态（SERVICE_CHIP_CLASS + setServiceState）；
    #     ③ 三态取词键齐备。防「删了清单却忘了接线三态」或反向回归。
    svc_bad: list[str] = []
    idx_html = root / "src/web/index.html"
    ihtml = idx_html.read_text(encoding="utf-8") if idx_html.is_file() else ""
    if 'id="checklist"' in ihtml:
        svc_bad.append("index.html 仍含 checklist")
    mjs = root / "src/web/js/main.js"
    mtext = mjs.read_text(encoding="utf-8") if mjs.is_file() else ""
    for token in ("SERVICE_CHIP_CLASS", "setServiceState"):
        if token not in mtext:
            svc_bad.append(f"main.js:{token}")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/js/i18n" / name
        t = p.read_text(encoding="utf-8") if p.is_file() else ""
        for k in ("topbar.backend.connecting", "topbar.backend.ready", "topbar.backend.offline"):
            if k not in t:
                svc_bad.append(f"{name}:{k}")
    check(not svc_bad, "服务状态三态 V0.0.16",
          f"缺失：{', '.join(svc_bad)}" if svc_bad
          else "左栏清单已移除 / 顶栏三态接线 / 三态取词键齐备")

    # 7n. note 契约与 .md 边界（V0.0.17：节点说明 + 三粒度复制）
    #     裁定：note 与 .md content 一律**纯文本** —— 工具不解析、不渲染、不校验 Markdown。
    #     判据：① note 序列化两端（toDocumentNode / fromDocumentNode）都在函数体里带 note
    #     （AST 钉函数体，防字面量蒙混）；② 属性栏 textarea 纯文本（不用 innerHTML 渲染 note）；
    #     ③ toPlainTree 不含 note（note 不参与生成落盘）。
    note_bad: list[str] = []
    for rel, token in (
        ("src/web/index.html", 'id="propNote"'),
        ("src/web/js/main.js", "adoptTemplateNote"),
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
    #     判据：① helpSections 中英两份都不再含 support 分节；② support.html/js 存在且接线
    #     （main.js 打开 support.html）；③ 互链齐备（about 表跳转 + 支持页回链）；④ 取词键闭包
    #     由 7b-2 守卫统一覆盖，此处只查结构。
    split_bad: list[str] = []
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/js/i18n" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if re.search(r"\{\s*id:\s*'support'", text):
            split_bad.append(f"{name}:helpSections 仍含 support 分节")
        for k in ("support.titleTag", "support.docTitle", "support.back", "support.toHelp",
                  "help.support.goto"):
            if k not in text:
                split_bad.append(f"{name}:{k}")
    mjs18 = root / "src/web/js/main.js"
    m18 = mjs18.read_text(encoding="utf-8") if mjs18.is_file() else ""
    if "./support.html" not in m18:
        split_bad.append("main.js 未打开 support.html")
    if "'help.html#support'" in m18:
        split_bad.append("main.js 仍用旧锚点 #support")
    hj = root / "src/web/js/help.js"
    h18 = hj.read_text(encoding="utf-8") if hj.is_file() else ""
    if "./support.html" not in h18:
        split_bad.append("help.js 缺 about 表跳转链接")
    if re.search(r"kind:\s*'support'", root.joinpath("src/web/js/i18n/zh-CN.js").read_text(encoding="utf-8")):
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
        p = root / "src/web/js/i18n" / name
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
    for token, why in (
        ("renameTemplateItem", "缺模板重命名接线"),
        ("deleteTemplateItem", "缺模板删除接线"),
        ("noteHistoryId", "缺 note 编辑会话（连续输入应只入栈一次）"),
        ("resetEditing", "缺撤销后属性栏暂存作废（note 框会显示旧文本）"),
    ):
        if token not in m20:
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
        p = root / "src/web/js/i18n" / name
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
    m = re.search(r"async function saveAsTemplate\(\) \{.*?\n\}", m20, flags=re.S)
    if not m:
        overwrite_bad.append("main.js:saveAsTemplate 体不可解析")
    else:
        body21 = m.group(0)
        if "templateExists" not in body21:
            overwrite_bad.append("saveAsTemplate 未捕获 templateExists")
        if "overwrite: true" not in body21:
            overwrite_bad.append("saveAsTemplate 未带 overwrite 重发")
        if "confirm(" not in body21:
            overwrite_bad.append("saveAsTemplate 缺二次确认")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/js/i18n" / name
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
    if not re.search(r"^async function applyTemplate\(", m3, flags=re.M):
        p3_bad.append("main.js:applyTemplate 行首空格未清（或函数缺失）")
    for name in ("zh-CN.js", "en-US.js"):
        p = root / "src/web/js/i18n" / name
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
            ("\\u4e00", "缺中文名判定"),
            ("copytree", "缺沙盒隔离（会污染真实 data/）"),
            ("_probe_ui.html", "缺同源探针页"),
        )
        for token, why in anchors_bsmoke:
            if token not in btext:
                b_bad.append(why)
    check(not b_bad, "浏览器冒烟覆盖 V0.0.25",
          f"缺失：{', '.join(b_bad)}" if b_bad
          else "控制台异常 / 漏翻 / 分节幂等 / 默认示例语言 / 切换驱动 / 沙盒隔离 齐备")

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
        ("src/server/routes.py", "EDITOR_PATH"),
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
            "tests/test_verify.py",
            "tools/smoke.py", "tools/browser_smoke.py",
        ) if not (root / rel).is_file()]
        n_modules = len(sorted((root / "tests").glob("test_*.py")))
        check(not net_missing, "回归测试网 §P0-2",
              f"缺失：{', '.join(net_missing)}" if net_missing
              else f"tests/ {n_modules} 模块 + tools/smoke.py + tools/browser_smoke.py 齐备")

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
