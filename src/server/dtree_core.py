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


def _load_error_codes() -> Dict[str, str]:
    try:
        raw = (config.SHARED_DIR / "error-codes.json").read_text(encoding="utf-8")
    except OSError:
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
    return True, ""


def count_tree(tree: Any) -> Tuple[int, int]:
    """统计 (目录数, 文件数)。"""
    dirs = files = 0
    if not isinstance(tree, dict):
        return 0, 0
    for _name, value in tree.items():
        if isinstance(value, dict):
            dirs += 1
            sub_dirs, sub_files = count_tree(value)
            dirs += sub_dirs
            files += sub_files
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


def build_tree(tree: Any, base: Path, dry_run: bool = False) -> Dict[str, Any]:
    """按 tree 结构在 base 下真实建目录与文件。

    dry_run=True 时只演练：不写盘，但返回同样的 planned 结构。
    """
    if not isinstance(tree, dict):
        raise TreeError("treeMissing")

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
                    existed.append(str(target))
                    continue
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(value), encoding="utf-8")
                created_files.append(str(target))

    if not dry_run:
        base.mkdir(parents=True, exist_ok=True)
    walk(tree, base)

    dirs, files = count_tree(tree)
    return {
        "root": str(base),
        "dryRun": bool(dry_run),
        "plannedDirs": dirs,
        "plannedFiles": files,
        "createdDirs": created_dirs,
        "createdFiles": created_files,
        "existed": existed,
    }
