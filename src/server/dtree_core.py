"""青蔓 QingMan · 目录树核心逻辑。

只做「校验 / 统计 / 落盘」三件事，不依赖 HTTP，可被 CLI 与后端共用。
错误码统一从 src/shared/error-codes.json 读取，前后端同一份文案。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from server import config

ILLEGAL_CHARS = set('/\\:*?"<>|')
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# 生成文件换行：**按扩展名**分流（§P2 第 12 项）。
# 判据必须是**扩展名**，**绝不能是 os.linesep** —— 后者会把"平台差异"重新引入产出，
# 正是 §P2 第 11 项要消灭的东西。按扩展名是**规则确定**的：同一输入在任何平台产同一字节。
CRLF_SUFFIXES = (".bat", ".cmd", ".ps1")


def newline_for(name: str) -> str:
    """返回该文件名应使用的换行串：批处理族 → CRLF，其余 → LF。"""
    return "\r\n" if name.lower().endswith(CRLF_SUFFIXES) else "\n"


def _load_error_codes() -> Dict[str, str]:
    try:
        raw = (config.SHARED_DIR / "error-codes.json").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # 本函数在**模块顶层**执行（`_ERROR_CODES = _load_error_codes()`）：漏捕编码错误
        # 会让 `import server` 直接崩、服务起不来（A-P2-4）。同 load_editor 一并扩捕获。
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


_ERROR_CODES: Dict[str, str] = _load_error_codes()


class TreeError(Exception):
    """带错误码的目录树异常，由上层转成 JSON 错误响应。"""

    def __init__(self, code: str, **detail: Any) -> None:
        self.code = code
        self.detail = detail
        super().__init__(message(code, **detail))


def message(code: str, **kwargs: Any) -> str:
    tpl = _ERROR_CODES.get(code, code)
    try:
        return tpl.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return tpl


def validate_segment(name: str) -> Tuple[bool, str]:
    """校验单个目录/文件名。返回 (是否合法, 错误码)。"""
    if not isinstance(name, str):
        return False, "segmentNotString"
    s = name.strip()
    if not s:
        return False, "segmentEmpty"
    if s in (".", ".."):
        return False, "segmentDot"
    if len(s) > 120:
        return False, "segmentTooLong"
    for ch in s:
        if ch in ILLEGAL_CHARS or ord(ch) < 32:
            return False, "segmentIllegalChar"
    if s.split(".")[0].upper() in RESERVED_NAMES:
        return False, "segmentReserved"
    # A-P2-2：首尾空白 / 尾随点会被 Windows 文件系统**规范化**（"a " → "a"、"abc." → "abc"），
    # 于是落盘报告里的名字与磁盘实际名不符（用户照着报告去找会落空）。宁可在此拒绝，
    # 也不让「记录名 ≠ 磁盘名」传到用户面前。判据用**原始** name 与 strip 后的 s 对比。
    if s != name or s.endswith("."):
        return False, "segmentTrailing"
    return True, ""


def count_tree(tree: Any) -> Tuple[int, int]:
    """统计 (目录数, 文件数)。

    用**显式栈**而非递归（A-P3-5）：模板树深度由内容决定，递归实现在极深嵌套下会撞
    Python 递归上限抛 `RecursionError` —— 模板虽是本机资产、深树罕见，但「深」不该
    等于「崩」。显式栈把栈从 C 栈搬到堆，深度不再受 `sys.getrecursionlimit()` 约束。
    计数口径与旧递归实现保持一致（逐节点累加，仅目录/文件二分）。
    """
    dirs = files = 0
    if not isinstance(tree, dict):
        return 0, 0
    stack: List[Dict[str, Any]] = [tree]
    while stack:
        node = stack.pop()
        for _name, value in node.items():
            if isinstance(value, dict):
                dirs += 1
                stack.append(value)
            else:
                files += 1
    return dirs, files


def validate_document(root: Any) -> Dict[str, int]:
    """校验整篇编辑态文档：结构、命名、id 唯一、同层不重名、规模上限。

    返回 {"dirs": n, "files": n}（根节点不计入目录数，与前端 countTree 口径一致）。
    任一项不合法即抛 TreeError —— 服务端**绝不落盘非法文档**。
    """
    if not isinstance(root, dict):
        raise TreeError("editorRootMissing")
    if root.get("type") != "dir":
        raise TreeError("editorRootNotDir")

    seen_ids: Dict[str, str] = {}
    limit = config.MAX_EDITOR_NODES

    def walk(node: Any, path: str) -> Tuple[int, int]:
        if not isinstance(node, dict):
            raise TreeError("editorNodeNotObject", path=path)
        kind = node.get("type")
        if kind not in ("dir", "file"):
            raise TreeError("editorNodeBadType", path=path)

        name = node.get("name")
        if not isinstance(name, str):
            raise TreeError("editorNodeBadName", path=path)
        if not name.strip():
            # V0.0.42（手册 10.2 节 #12 · 方案 C）：根节点名**即**「根文件夹名」——
            # 允许为空（空名 = 不建根，与 routes.generate 的 `root` 留空同义）；
            # 其余节点名仍须非空。空根名不参与 validate_segment（空串必不合法）。
            if path != "$":
                raise TreeError("editorNodeBadName", path=path)
        else:
            ok, reason = validate_segment(name)
            if not ok:
                raise TreeError("segmentInvalid", name=name, reason=message(reason, name=name))

        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise TreeError("editorNodeBadId", path=path)
        if node_id in seen_ids:
            raise TreeError("editorIdDuplicated", id=node_id,
                            first=seen_ids[node_id], again=path)
        seen_ids[node_id] = path
        if len(seen_ids) > limit:
            raise TreeError("editorTooManyNodes", limit=limit)

        if kind == "file":
            if not isinstance(node.get("content", ""), str):
                raise TreeError("editorNodeBadContent", path=path)
            return 0, 1

        children = node.get("children", [])
        if not isinstance(children, list):
            raise TreeError("editorNodeBadChildren", path=path)

        # 同层重名：大小写不敏感 —— 落盘目标多为 Windows 文件系统
        names = set()
        for index, child in enumerate(children):
            child_name = child.get("name") if isinstance(child, dict) else None
            if isinstance(child_name, str):
                key = child_name.strip().lower()
                if key and key in names:
                    raise TreeError("editorSiblingDuplicated", name=child_name,
                                    path=f"{path}.children[{index}]")
                names.add(key)

        dirs, files = 1, 0
        for index, child in enumerate(children):
            sub_dirs, sub_files = walk(child, f"{path}.children[{index}]")
            dirs += sub_dirs
            files += sub_files
        return dirs, files

    dirs, files = walk(root, "$")
    return {"dirs": dirs - 1, "files": files}


def check_target(raw: Any, allow_drive_root: bool = False) -> Path:
    """落盘安全边界（§P0-1 R1–R5）：规范化 target 并逐条比对黑名单。

    返回规范化后的**绝对路径**；任一规则命中即抛 TreeError，错误码明确
    （由上层映射为 4xx，而非笼统 500）。本函数**不产生任何 IO**。

    `allow_drive_root`（2026-10-26 加）：调用方**已经确认根名非空**时传 True ——
    此时真实写入点是「盘根/根名」（一个普通子目录），把盘根拦下来属于误伤
    （用户诉求：在 E 盘生成项目，目标位置填 `E:\\`、根名填项目名）。根名为空时
    仍然拒绝：那才是「把整棵树直接铺到盘根」。
    """
    if not isinstance(raw, str) or not raw.strip():
        raise TreeError("targetMissing")

    text = raw.strip()
    try:
        path = Path(text).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TreeError("targetInvalid", target=text, reason=str(exc))

    # R2 盘根：至少两级（C:\ / D:\ / / 一律拒），否则等于「往整个盘写」。
    # 例外：根名非空（见 docstring）—— 那时只写 `盘根/根名` 这一棵子树。
    at_root = path.parent == path
    if at_root and allow_drive_root:
        pass
    elif at_root or len(path.parts) < 2:
        raise TreeError("targetTooShallow", target=str(path))

    # R5 项目自身及其上级目录：防止工具改到自己（或改到项目所在的工作区）
    project = config.PROJECT_DIR_RESOLVED
    if path == project or config.is_within(project, path):
        raise TreeError("targetReserved", target=str(path), reason="青蔓项目自身或其上级目录")

    # R3 系统目录：整棵子树禁止（含 System32）
    for blocked, label in config.BLOCKED_SUBTREES:
        if config.is_within(path, blocked):
            raise TreeError("targetBlocked", target=str(path), reason=label)

    # R4 用户关键目录：仅根本身禁止（子目录放行）
    for blocked, label in config.BLOCKED_ROOTS:
        if path == blocked:
            raise TreeError("targetBlocked", target=str(path), reason=f"{label}根目录")

    return path


def _preflight_tree(tree: Dict[str, Any], base: Path) -> None:
    """写盘**之前**把整棵树的名字检查一遍：不合法段名、同层仅大小写不同。

    为什么要预检而不是边走边报（2026-10-26）：边走边报会在中途抛错，**前面已经建出来的
    目录留在磁盘上** —— 用户看到「生成失败」，却已多出半棵树，属于污染。预检不写任何东西，
    失败时磁盘保持原样；代价是一次额外的纯内存遍历。
    """
    def walk(node: Dict[str, Any], current: Path) -> None:
        seen: Dict[str, str] = {}
        for name, value in node.items():
            ok, reason = validate_segment(name)
            if not ok:
                raise TreeError("segmentInvalid", name=name, reason=message(reason, name=name))
            folded = name.casefold()
            if folded in seen:
                raise TreeError("treeSiblingDuplicated", name=name,
                                first=seen[folded], path=str(current / name))
            seen[folded] = name
            if isinstance(value, dict):
                walk(value, current / name)

    walk(tree, base)


def build_tree(tree: Any, base: Path, dry_run: bool = False) -> Dict[str, Any]:
    """按 tree 结构在 base 下真实建目录与文件。

    dry_run=True 时只演练：不写盘，但返回同样的 planned 结构。

    R6：规模超限由服务端直接拒绝（dry_run 同样拦截 —— 上限针对的是「计划规模」本身）。
    R7：目录已存在 → 复用；文件已存在 → 跳过、不覆盖、不比对内容，计入 existed。
    R8：全程只新建，**绝不删除**任何既有文件或目录。
    P3-13：同名但**类型相反**（树要目录/磁盘是文件、树要文件/磁盘是目录）一律报错，
    不再对后者静默跳过 —— 避免用户误以为文件已生成。
    """
    if not isinstance(tree, dict):
        raise TreeError("treeMissing")

    planned_dirs, planned_files = count_tree(tree)
    total = planned_dirs + planned_files
    if total > config.MAX_NODES:
        raise TreeError("tooManyNodes", dirs=planned_dirs, files=planned_files,
                        total=total, limit=config.MAX_NODES)

    base = Path(base).expanduser()
    # 先整树预检（名字合法性 + 同层大小写重复），**再**动磁盘：失败时不留半棵树
    _preflight_tree(tree, base)
    # 根名与磁盘上的**同名文件**冲突：不能让后续 `mkdir` 撞 NotADirectoryError（那是 500）
    if base.exists() and not base.is_dir():
        raise TreeError("pathConflict", path=str(base))
    created_dirs: List[str] = []
    created_files: List[str] = []
    existed: List[str] = []

    def walk(node: Dict[str, Any], current: Path) -> None:
        # **同层子项不得仅大小写不同**（2026-10-26）：Windows 文件系统不区分大小写，
        # `A/` 与 `a/` 会落到**同一个**目录 —— 旧实现第一个建出来、第二个「已存在 → 复用」，
        # 于是两份本意不同的内容被悄悄合并进一个目录（污染且无提示）。
        # 判据与编辑态契约的「同级重名大小写不敏感」同一口径。
        seen: Dict[str, str] = {}
        for name, value in node.items():
            ok, reason = validate_segment(name)
            if not ok:
                raise TreeError("segmentInvalid", name=name, reason=message(reason, name=name))
            folded = name.casefold()
            if folded in seen:
                raise TreeError("treeSiblingDuplicated", name=name,
                                first=seen[folded], path=str(current / name))
            seen[folded] = name
            target = current / name
            if isinstance(value, dict):
                if target.exists():
                    if not target.is_dir():
                        raise TreeError("pathConflict", path=str(target))
                    existed.append(str(target))
                else:
                    if not dry_run:
                        target.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(target))
                walk(value, target)
            else:
                if target.exists():
                    # P3-13：与「要建目录、磁盘是文件」对称 —— 要建文件、磁盘同名是目录
                    # 同样报错，而不是静默计入 existed 让用户误以为已生成。
                    if target.is_dir():
                        raise TreeError("pathConflictDir", path=str(target))
                    existed.append(str(target))
                    continue
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # 换行**按扩展名**分流（§P2 第 12 项）：批处理族 CRLF、其余 LF。
                    # 先把值里的 CR / CRLF 归一为 LF，再交给 open 按 newline 翻译 ——
                    # 否则原值含 CRLF 时会被译成 \r\r\n（§编码基线）。
                    with target.open("w", encoding="utf-8",
                                     newline=newline_for(target.name)) as fh:
                        fh.write(str(value).replace("\r\n", "\n").replace("\r", "\n"))
                created_files.append(str(target))

    if not dry_run:
        base.mkdir(parents=True, exist_ok=True)
    walk(tree, base)

    return {
        "root": str(base),
        "dryRun": bool(dry_run),
        "plannedDirs": planned_dirs,
        "plannedFiles": planned_files,
        "createdDirs": created_dirs,
        "createdFiles": created_files,
        "existed": existed,
    }


# ---------------------------------------------------------------------------
# 模板：结构校验 + `.md` 双格式（§P2 第 7 项 · 设计方案见《模板系统重设计_方案原型_20261011》）
#
# 模板的 `tree` 是**嵌套字典**（目录 = dict、文件 = 内容字符串），与编辑态文档的
# 「id / type / children」结构**不同** —— 故不复用 `validate_document`。
#
# `.md` 是本项目为「AI / Agent / Skill 生态」选定的交换格式（§P2 第 7 项）。本节的
# `parse_md_template` 与 `render_md_template` 必须是一对**互逆且确定性**的纯函数：
# `parse(render(doc)) == doc`（导出→再导入不丢内容），且 `render` 幂等
# （`render(parse(render(doc))) == render(doc)`）。任一不成立都意味着「往返成环」
# 会在某类内容上静默丢数据。
# ---------------------------------------------------------------------------

# 围栏最短 3 个反引号；内容含更长的反引号串时写端自动加长（保证可闭合）。
_MD_FENCE_MIN = 3
# 列表项：行首缩进（**仅空格**）+ "- " + 内容。Tab 缩进一律判非法（严格文法）。
_MD_ITEM_RE = re.compile(r"^( *)- +(.*)$")
# 目录名判据：尾部 "/"（权威形）；解析端另兼容 "📁" 前缀（历史 / 手工书写）。
_MD_DIR_MARK = "\U0001F4C1"  # 📁


def _validate_template_tree(tree: Dict[str, Any], max_nodes: int) -> Tuple[int, int]:
    """校验模板 `tree`（嵌套字典）：逐段名校验 + 同层重名 + 规模上限。

    用**显式栈**（同 `count_tree`）以免深树撞递归上限。返回 (dirs, files)。
    """
    dirs = files = total = 0
    stack: List[Dict[str, Any]] = [tree]
    while stack:
        node = stack.pop()
        seen: Dict[str, str] = {}
        for name, value in node.items():
            if not isinstance(name, str):
                raise TreeError("templateBadJson")
            ok, reason = validate_segment(name)
            if not ok:
                raise TreeError("segmentInvalid", name=name,
                                reason=message(reason, name=name))
            # 同层重名（**大小写不敏感**）：落盘目标多为 Windows 文件系统。
            key = name.strip().lower()
            if key in seen:
                raise TreeError("templateSiblingDuplicated", name=name)
            seen[key] = name
            total += 1
            if total > max_nodes:
                raise TreeError("templateTooManyNodes", total=total, limit=max_nodes)
            if isinstance(value, dict):
                dirs += 1
                stack.append(value)
            elif isinstance(value, str):
                files += 1
            else:
                raise TreeError("templateBadJson")
    return dirs, files


def validate_template(doc: Any, max_nodes: "int | None" = None) -> Tuple[int, int]:
    """校验整套模板文档 `{name, description, updated?, tree}`，返回 (dirs, files)。

    非法结构一律抛 `TreeError`（错误码与既有 `template*` 体例一致）。`tree` 内每个
    段名都过 `validate_segment`，同层重名（大小写不敏感）与规模上限同 `save_template`。
    """
    limit = config.MAX_NODES if max_nodes is None else max_nodes
    if not isinstance(doc, dict):
        raise TreeError("templateBadJson")
    for field in ("name", "description"):
        value = doc.get(field)
        if value is not None and not isinstance(value, str):
            raise TreeError("templateBadJson")
    tree = doc.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("templateTreeMissing")
    return _validate_template_tree(tree, limit)


def _md_fence_for(content: str) -> str:
    """按内容里最长连续反引号串决定围栏长度（至少 3）。"""
    longest = run = 0
    for ch in content:
        if ch == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return "`" * max(_MD_FENCE_MIN, longest + 1)


def _render_md_tree(node: Dict[str, Any], depth: int, out: List[str]) -> None:
    indent = "  " * depth
    body_indent = "  " * (depth + 1)
    for name, value in node.items():
        if isinstance(value, dict):
            out.append(f"{indent}- {name}/")
            _render_md_tree(value, depth + 1, out)
            continue
        content = value if isinstance(value, str) else ""
        out.append(f"{indent}- {name}")
        if content:
            fence = _md_fence_for(content)
            out.append(f"{body_indent}{fence}md")
            for line in content.split("\n"):
                # 空行不留缩进（写端规范化；解析端把围栏内空行当正文空行）。
                out.append(f"{body_indent}{line}" if line else "")
            out.append(f"{body_indent}{fence}")


def render_md_template(doc: Dict[str, Any]) -> str:
    """模板文档 → `.md` 文本（确定性、可再被 `parse_md_template` 还原）。"""
    if not isinstance(doc, dict):
        raise TreeError("templateBadJson")
    tree = doc.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("templateTreeMissing")

    out: List[str] = []
    name = doc.get("name")
    if isinstance(name, str) and name.strip():
        out.append("# " + name.strip())
    description = doc.get("description")
    if isinstance(description, str) and description:
        for line in description.split("\n"):
            out.append(("> " + line) if line else ">")
    if out:
        out.append("")
    _render_md_tree(tree, 0, out)
    return "\n".join(out) + "\n"


def parse_md_template(text: str) -> Dict[str, Any]:
    """`.md` 文本 → 模板文档 `{name, description, tree}`（严格文法，非法即抛）。

    文法（《模板系统重设计_方案原型》第三节提案）：文档首个 `# ` 行 = 模板名；紧随的
    `> ` 引用块 = 描述；`- ` 行 = 节点（**每 2 空格一级**）；名尾 `/`（或 📁 前缀）=
    目录，否则文件；文件正文用**再缩进一级**的围栏块承载。
    """
    if not isinstance(text, str):
        raise TreeError("templateBadMarkdown", reason="not a string")
    src = text.replace("\r\n", "\n").replace("\r", "\n")
    if src.startswith("\ufeff"):
        src = src[1:]
    lines = src.split("\n")
    n = len(lines)
    idx = 0

    while idx < n and not lines[idx].strip():
        idx += 1
    name = ""
    if idx < n and lines[idx].startswith("# "):
        name = lines[idx][2:].strip()
        idx += 1
    desc_lines: List[str] = []
    while idx < n and (lines[idx] == ">" or lines[idx].startswith("> ")):
        line = lines[idx]
        desc_lines.append(line[2:] if line.startswith("> ") else line[1:])
        idx += 1

    tree: Dict[str, Any] = {}
    # 显式栈：(-1, 根)。目录项入栈（供其子项挂靠）；文件项不入栈 ——
    # 于是「文件下再缩进的项」会因父级深度对不上而判 indent-jump 非法。
    stack: List[Tuple[int, Dict[str, Any]]] = [(-1, tree)]
    while idx < n:
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue
        match = _MD_ITEM_RE.match(line)
        if not match:
            raise TreeError("templateBadMarkdown", reason="unexpected line", line=line[:60])
        indent = len(match.group(1))
        if indent % 2:
            raise TreeError("templateBadMarkdown", reason="odd indent", line=line[:60])
        depth = indent // 2
        rest = match.group(2).strip()
        is_dir = rest.endswith("/")
        seg = rest[:-1].strip() if is_dir else rest
        if seg.startswith(_MD_DIR_MARK):
            is_dir = True
            seg = seg[len(_MD_DIR_MARK):].strip()
        if not seg:
            raise TreeError("templateBadMarkdown", reason="empty name", line=line[:60])

        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack or stack[-1][0] != depth - 1:
            raise TreeError("templateBadMarkdown", reason="indent jump", line=line[:60])
        parent = stack[-1][1]
        if seg in parent:
            raise TreeError("templateSiblingDuplicated", name=seg)
        idx += 1

        if is_dir:
            child: Dict[str, Any] = {}
            parent[seg] = child
            stack.append((depth, child))
            continue

        content = ""
        if idx < n:
            body_indent = "  " * (depth + 1)
            nxt = lines[idx]
            if nxt.startswith(body_indent) and nxt[len(body_indent):].startswith("`"):
                head = nxt[len(body_indent):]
                run = 0
                while run < len(head) and head[run] == "`":
                    run += 1
                if run >= _MD_FENCE_MIN:
                    fence = "`" * run
                    idx += 1
                    body: List[str] = []
                    closed = False
                    while idx < n:
                        cur = lines[idx]
                        if cur.strip() == fence:
                            closed = True
                            idx += 1
                            break
                        if cur == "":
                            body.append("")
                        elif cur.startswith(body_indent):
                            body.append(cur[len(body_indent):])
                        else:
                            raise TreeError("templateBadMarkdown",
                                            reason="malformed body", line=cur[:60])
                        idx += 1
                    if not closed:
                        raise TreeError("templateBadMarkdown", reason="unclosed fence")
                    content = "\n".join(body)
        parent[seg] = content

    return {"name": name, "description": "\n".join(desc_lines), "tree": tree}
