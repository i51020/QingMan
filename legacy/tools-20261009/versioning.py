"""青蔓 QingMan · 版本号工具。

版本规则：V<主>.<两位次>，从 V0.01 起，每次升级 +0.01。
内部用「百分位整数」运算，避免浮点误差。
"""

from __future__ import annotations

import re

_PATTERN = re.compile(r"^V(\d+)\.(\d{1,2})$")


def parse(text: str) -> int:
    """'V0.01' -> 1（百分位整数）。非法格式抛 ValueError。"""
    m = _PATTERN.match((text or "").strip())
    if not m:
        raise ValueError(f"版本号格式非法：{text!r}，应为 V0.01 形式")
    major, minor = int(m.group(1)), int(m.group(2))
    if minor > 99:
        raise ValueError(f"次版本号超出两位：{text!r}")
    return major * 100 + minor


def format_cents(cents: int) -> str:
    if cents < 0:
        raise ValueError("版本号不能为负")
    return f"V{cents // 100}.{cents % 100:02d}"


def bump(text: str, step: int = 1) -> str:
    """版本号 +step（默认 +0.01，即 +1 百分位）。"""
    return format_cents(parse(text) + step)
