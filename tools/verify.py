"""青蔓 QingMan · 交付校验。

用法：
    python tools/verify.py [版本根目录]

「版本根目录」需包含 src/ 与 VERSION；缺省为脚本所在项目的根目录。
校验项与《错误笔记》交付清单一致：
  1. 必需文件存在
  2. HTML 标签闭合、关键 id 存在
  3. main.js 中引用的 id 在 index.html 中真实存在
  4. JS 语法（ESM 方式交由 node --check 解析）
  5. CSS 大括号平衡
  6. Python 语法（ast 只读解析，不产生 __pycache__，保证校验不污染被校验目录）
  7. 指纹比对（--against <版本>）：与 versions/<版本>/MANIFEST.json 逐文件比对 SHA-256
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
from store import sha256_of  # noqa: E402

PAIRED_TAGS = (
    "html", "head", "body", "div", "section", "aside", "header", "footer",
    "main", "span", "button", "label", "ul", "li", "pre", "h1", "h2", "h3", "p", "code",
)

REQUIRED_IDS = (
    "topbar", "chipVersion", "chipBackend", "sidebar", "checklist",
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
    "src/web/css/tokens.css",
    "src/web/css/base.css",
    "src/web/css/layout.css",
    "src/web/js/main.js",
    "src/web/js/core/bus.js",
    "src/web/js/core/store.js",
    "src/web/js/core/api.js",
    "src/web/js/modules/tree-model.js",
    "src/web/js/ui/tree-view.js",
    "src/web/js/ui/inspector.js",
    "src/web/js/ui/toast.js",
)

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
    """与 versions/<版本>/MANIFEST.json 逐文件比对 SHA-256。

    输出三态语义由 check() 的 ok 决定：一致 / 有差异（列出改动·新增·缺失）/ 无法判定。
    """
    manifest = root / "versions" / version / "MANIFEST.json"
    if not manifest.is_file():
        check(False, f"指纹比对 {version}", "无法判定：未找到 MANIFEST.json")
        return

    meta = json.loads(manifest.read_text(encoding="utf-8"))
    recorded: dict[str, str] = meta.get("files", {})
    inner = meta.get("version")

    # 目录名必须与清单内容自洽，防止"快照名与内容不符"
    check(inner == version, f"清单自洽 {version}", f"内容 version={inner or '(空)'}")

    changed = [rel for rel, ref in recorded.items()
               if (root / rel).is_file() and sha256_of(root / rel) != ref.split(":", 1)[-1]]
    missing = [rel for rel in recorded if not (root / rel).is_file()]
    current = {rel for rel, _ in collect_tracked(root)}
    added = sorted(current - set(recorded))

    clean = not (changed or missing or added)
    detail = "完全一致" if clean else f"改动 {len(changed)} / 新增 {len(added)} / 缺失 {len(missing)}"
    check(clean, f"指纹比对 {version}", detail)
    for rel in (changed + added + missing)[:10]:
        print(f"        [差异] {rel}")


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

    # 7. 与版本清单比对指纹（仅在指定 --against 时启用）
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
