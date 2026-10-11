"""青蔓 QingMan · 目录树核心逻辑。

只做「校验 / 统计 / 落盘」三件事，不依赖 HTTP，可被 CLI 与后端共用。
错误码统一从 src/shared/error-codes.json 读取，前后端同一份文案。
"""

from __future__ import annotations

import json
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
        if not isinstance(name, str) or not name.strip():
            raise TreeError("editorNodeBadName", path=path)
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


def check_target(raw: Any) -> Path:
    """落盘安全边界（§P0-1 R1–R5）：规范化 target 并逐条比对黑名单。

    返回规范化后的**绝对路径**；任一规则命中即抛 TreeError，错误码明确
    （由上层映射为 4xx，而非笼统 500）。本函数**不产生任何 IO**。
    """
    if not isinstance(raw, str) or not raw.strip():
        raise TreeError("targetMissing")

    text = raw.strip()
    try:
        path = Path(text).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TreeError("targetInvalid", target=text, reason=str(exc))

    # R2 盘根：至少两级（C:\ / D:\ / / 一律拒），否则等于「往整个盘写」
    if path.parent == path or len(path.parts) < 2:
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
    created_dirs: List[str] = []
    created_files: List[str] = []
    existed: List[str] = []

    def walk(node: Dict[str, Any], current: Path) -> None:
        for name, value in node.items():
            ok, reason = validate_segment(name)
            if not ok:
                raise TreeError("segmentInvalid", name=name, reason=message(reason, name=name))
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
