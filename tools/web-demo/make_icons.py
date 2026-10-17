"""青蔓 QingMan · PWA 图标生成（纯标准库，无 Pillow）

为什么要自己画：这个环境没有 Pillow，也不能可靠地用 `msedge --screenshot` 截图
（本机实测恒不产文件）。但 PWA 的安装条件要求真实 PNG，故用 `zlib` + 手写 PNG
chunk 直接生成 —— 确定性、零依赖，构建期跑一次。

图形：深色圆角底 + 三级「目录树」横条（上窄下宽错位），呼应青蔓的目录树主线。
留 12% 内边距，使其同时可用作 maskable 图标（安全区内）。
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

BG = (43, 47, 54)        # #2B2F36 深墨
BAR = (233, 196, 138)    # #E9C48A 暖琥珀（与出厂皮肤的强调色同族）
DIM = (150, 158, 168)    # #969EA8 次级灰


def _rounded(px: int, py: int, size: int, radius: float) -> bool:
    """点是否落在圆角矩形内（四角按圆判）。"""
    r = radius
    if px < r and py < r:
        return (px - r) ** 2 + (py - r) ** 2 <= r * r
    if px > size - r and py < r:
        return (px - (size - r)) ** 2 + (py - r) ** 2 <= r * r
    if px < r and py > size - r:
        return (px - r) ** 2 + (py - (size - r)) ** 2 <= r * r
    if px > size - r and py > size - r:
        return (px - (size - r)) ** 2 + (py - (size - r)) ** 2 <= r * r
    return True


def _bars(size: int) -> "list[tuple[float, float, float, float, tuple[int, int, int]]]":
    """三级目录树：返回 (x0, y0, x1, y1, color)，坐标为 0..1 归一值。

    每级左侧一个方块（目录），右侧一条横条（子项），逐级右移且变短 ——
    远看就是一棵缩进的树，与产品的核心心智一致。
    """
    pad = 0.12
    top = 0.30
    gap = 0.155
    height = 0.075
    rows = []
    for i, (indent, width, color) in enumerate((
        (0.00, 0.34, BAR),
        (0.12, 0.30, DIM),
        (0.24, 0.26, DIM),
    )):
        y0 = top + i * gap
        x0 = pad + indent
        rows.append((x0, y0, x0 + height, y0 + height, color))          # 目录方块
        rows.append((x0 + height + 0.055, y0 + height * 0.22,
                     min(x0 + height + 0.055 + width, 1 - pad), y0 + height * 0.78, color))
    return rows


def make_png(size: int) -> bytes:
    pad_px = size * 0.12
    radius = size * 0.22
    bars = _bars(size)
    rows: "list[bytearray]" = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            inside = _rounded(x, y, size, radius)
            if not inside:
                row += bytes((0, 0, 0, 0))
                continue
            color = BG
            for x0, y0, x1, y1, bar_color in bars:
                if x0 * size <= x <= x1 * size and y0 * size <= y <= y1 * size:
                    color = bar_color
                    break
            row += bytes((color[0], color[1], color[2], 255))
        rows.append(row)
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_icons(dest: Path) -> "list[Path]":
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for size in (192, 512):
        path = dest / f"icon-{size}.png"
        path.write_bytes(make_png(size))
        out.append(path)
    return out


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "icons")
    for p in write_icons(target):
        print(f"{p}  {p.stat().st_size} B")
