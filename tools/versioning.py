"""青蔓 QingMan · 版本号工具（SemVer 三段式）。

格式：V<MAJOR>.<MINOR>.<PATCH>，从 **V0.0.1** 起。

递增语义（bump 的 kind 参数）：
    patch  —— 修复、纠错（默认）
    minor  —— 新增功能或逻辑迭代（向后兼容）
    major  —— 不兼容变更（接口契约、数据格式破坏）

作废规则：旧「V0.01 两段式 + 每次 +0.01」自 2026-10-09 起不再使用。
兼容处理：旧两段式编号（如 V0.01）仍可解析，标记为 legacy，但不参与递增运算。
"""

from __future__ import annotations

import re

_NEW = re.compile(r"^V(\d+)\.(\d+)\.(\d+)$")
_LEGACY = re.compile(r"^V(\d+)\.(\d{1,2})$")

KINDS = ("patch", "minor", "major")


def parse(text: str) -> tuple[int, int, int]:
    """'V0.0.1' -> (0, 0, 1)。非法格式抛 ValueError。"""
    s = (text or "").strip()
    m = _NEW.match(s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    raise ValueError(f"版本号格式非法：{text!r}，应为 V0.0.1 形式")


def is_legacy(text: str) -> bool:
    """是否为旧两段式编号（如 V0.01）。"""
    s = (text or "").strip()
    return bool(_LEGACY.match(s)) and not bool(_NEW.match(s))


def format_version(parts: tuple[int, int, int]) -> str:
    if any(p < 0 for p in parts):
        raise ValueError("版本号各段不能为负")
    major, minor, patch = parts
    return f"V{major}.{minor}.{patch}"


def bump(text: str, kind: str = "patch") -> str:
    """按语义递增。

    patch: V0.0.1 -> V0.0.2
    minor: V0.0.2 -> V0.1.0（PATCH 归零）
    major: V0.1.0 -> V1.0.0（MINOR/PATCH 归零）
    """
    major, minor, patch = parse(text)
    if kind == "patch":
        return format_version((major, minor, patch + 1))
    if kind == "minor":
        return format_version((major, minor + 1, 0))
    if kind == "major":
        return format_version((major + 1, 0, 0))
    raise ValueError(f"未知递增类型：{kind!r}，应为 {'/'.join(KINDS)}")
