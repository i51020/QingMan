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
  9. 编辑态持久化契约（§P0-7）：schema.json 的 editorDocument/editorNode + 接口标识 + 错误码
 9b. 落盘安全边界（§P0-1）：config 黑名单 / dtree_core.check_target / routes 接线 / 错误码
 9c. 回归测试网（§P0-2）：tests/ 四模块 + tools/smoke.py（仅项目根，预览目录跳过）
 10. 指纹比对（--against <版本>）：与该版本**最高修订**清单逐文件比对 SHA-256
退出码：0 全部通过；1 存在失败项。
"""

from __future__ import annotations

import ast
import json
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
    "topbar", "chipSave", "chipBackend", "btnHelp", "sidebar", "checklist",
    "center", "genBar", "inRoot", "inTarget", "inDryRun",
    "toolbar", "btnAddChild", "btnRename", "btnDelete",
    "btnExpandAll", "btnCollapseAll", "btnGenerate",
    "treeCanvas", "statusText", "statusCount",
    "inspector", "propName", "propType", "propPath", "propDirs", "propFiles", "propDepth",
    "genResult", "toastHost",
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
    "src/web/css/tokens.css",
    "src/web/css/base.css",
    "src/web/css/layout.css",
    "src/web/css/help.css",
    "src/web/js/main.js",
    "src/web/js/help.js",
    "src/web/js/i18n/index.js",
    "src/web/js/i18n/zh-CN.js",
    "src/web/js/core/bus.js",
    "src/web/js/core/store.js",
    "src/web/js/core/api.js",
    "src/web/js/modules/tree-model.js",
    "src/web/js/ui/tree-view.js",
    "src/web/js/ui/inspector.js",
    "src/web/js/ui/toast.js",
)

CJK = re.compile(r"[\u4e00-\u9fff]")

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


def find_node() -> str | None:
    for name in ("node", "node.exe"):
        hit = shutil.which(name)
        if hit:
            return hit
    candidate = Path.home() / ".workbuddy/binaries/node/versions/22.22.2-6/node.exe"
    return str(candidate) if candidate.is_file() else None


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
        check(False, "JS 语法", "未找到 node，跳过（【待核实】）")
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
    #     本项目以 SHA-256 指纹校验内容，字节随平台漂移会直接造成指纹失配，故必须把关。
    eol_bad = []
    for f in sorted((root / "src").rglob("*")):
        if f.is_file() and b"\r" in f.read_bytes():
            eol_bad.append(f"{f.relative_to(root).as_posix()}(含 CR)")
    vf = root / "VERSION"
    if vf.is_file() and b"\r" in vf.read_bytes():
        eol_bad.append("VERSION(应为 LF)")
    bat = root / "start.bat"
    if bat.is_file():
        b = bat.read_bytes()
        if not (b"\r\n" in b and b.replace(b"\r\n", b"").count(b"\n") == 0):
            eol_bad.append("start.bat(应为纯 CRLF)")
    check(not eol_bad, "换行一致性",
          "; ".join(eol_bad) if eol_bad else "src/ 与 VERSION = LF，start.bat = CRLF")

    # 7. 帮助页不得硬编码中文（§P0-3 L1：文案必须经取词表，页面只留 data-i18n 键名）
    help_html = root / "src/web/help.html"
    if help_html.is_file():
        text = help_html.read_text(encoding="utf-8")
        hits = CJK.findall(text)
        check(not hits, "帮助页无硬编码中文",
              f"发现 {len(hits)} 处字面量：{''.join(hits[:6])}" if hits else "文案全部走 data-i18n 取词")
    else:
        check(False, "帮助页无硬编码中文", "help.html 未读到")

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
    for js in sorted((root / "src/web/js").rglob("*.js")):
        if "i18n" in js.parts:
            continue   # 取词表自身就是文案的存放处
        body = strip_comments(js.read_text(encoding="utf-8"), "js")
        for _quote, text in re.findall(r"""(['"`])((?:\\.|(?!\1).)*?)\1""", body, flags=re.S):
            if CJK.search(text):
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
    for page in ("src/web/index.html", "src/web/help.html"):
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

    # 8. 接续说明实况段须与盘上一致（§P1-6 H4；文件未建立则跳过，不阻塞预览目录的校验）
    handoff_file = root / "docs/接续说明.md"
    if handoff_file.is_file():
        try:
            from handoff import render_live, replace_block
            raw = handoff_file.read_text(encoding="utf-8")
            same = replace_block(raw, render_live(root)) == raw
            check(same, "接续说明实况段", "与盘上一致" if same else "已过期，运行 python tools/handoff.py")
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
            "tests/test_store.py", "tests/test_versioning.py",
            "tools/smoke.py",
        ) if not (root / rel).is_file()]
        check(not net_missing, "回归测试网 §P0-2",
              f"缺失：{', '.join(net_missing)}" if net_missing
              else "tests/ 四模块 + tools/smoke.py 齐备")

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
