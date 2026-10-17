"""青蔓 QingMan · 配色对比度审计（WCAG 2.1 AA / AAA）。

**为什么要有这个脚本**：皮肤与 tokens 的注释里写了「按 WCAG AA 做过钳制」，但注释只是
声明、不是证据 —— 16 款皮肤 × 明暗两套 × 十几种前景/背景配对，靠人眼不可能每次都核。
本脚本把「变量 → 配对 → 对比度」算成表，任何一次配色改动都能立刻看到有没有跌破门槛。

**口径**（WCAG 2.1）：
  * 正常字号正文：**4.5:1**（AA）
  * 大字号（≥18.66px 粗体 或 ≥24px 常规）：**3:1**
  * 非文本（图标 / 边框 / 选中态等承担语义的图形）：**3:1**
  * AAA（正文 7:1）只作为参考列输出，不作门槛 —— 本项目定位是 AA。

**它不做什么**：不解析 CSS 层叠与继承，只算**设计令牌**之间的配对。真实 DOM 上
某个元素如果用了别的颜色（没有走变量），本脚本看不见 —— 那类问题要靠浏览器实测补。

用法：
    py -3 tools/contrast_audit.py            # 打印全表
    py -3 tools/contrast_audit.py --fails    # 只打印不达标项
    py -3 tools/contrast_audit.py --json     # 机读输出
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
_CSS = _ROOT / "src" / "web" / "css"
_TOKENS = _CSS / "tokens.css"
_SKINS = _CSS / "skins"

# 配对：(说明, 前景变量, 背景变量, 门槛, 备注, 是否仅记录)
# `advisory=True` 的项**不参与判定** —— 它不是 WCAG 指标，只是记录一个设计事实
# （比如"面板与页面底色的差有多小"）。拿它当门槛，等于用自造标准否定一套刻意压平的设计。
PAIRS = (
    ("正文 / 页面底色", "text", "bg", 4.5, "", False),
    ("正文 / 面板", "text", "surface", 4.5, "", False),
    ("正文 / 次级面板", "text", "surface-2", 4.5, "", False),
    ("次要文字 / 面板", "text-dim", "surface", 4.5, "小字，按正文门槛", False),
    ("次要文字 / 页面底色", "text-dim", "bg", 4.5, "小字，按正文门槛", False),
    ("次要文字 / 次级面板", "text-dim", "surface-2", 4.5, "小字，按正文门槛", False),
    ("主按钮文字 / 按钮底", "on-accent", "btn-bg", 4.5, "", False),
    ("主按钮文字 / 悬停底", "on-accent", "btn-bg-hi", 4.5, "", False),
    ("强调文字 / 面板", "accent-ink", "surface", 4.5, "", False),
    ("强调文字 / 强调底", "accent-ink", "accent-soft", 4.5, "徽标 / 选中行", False),
    # 悬停/选中行只换底色、不换字色，行内的次要文字仍是 `--qm-text-dim` 压 `--qm-accent-soft`。
    # 这条是 2026-10-17 补的：s06 当时 4.35，DOM 实测才暴露 —— 光算 ink 会漏。
    ("次要文字 / 强调底", "text-dim", "accent-soft", 4.5, "悬停 / 选中行的次要文字", False),
    ("危险文字 / 面板", "danger", "surface", 4.5, "", False),
    ("危险文字 / 危险底", "danger", "danger-soft", 4.5, "错误提示条", False),
    ("警告文字 / 面板", "warn", "surface", 4.5, "", False),
    ("强调图形 / 面板", "accent", "surface", 3.0, "非文本：描边 / 选中 / 进度点", False),
    # 原先还有一条「勾选符号 / 强调底」= on-accent on accent。2026-10-17 实测发现这条
    # 配对在 DOM 里已经不存在了：`--qm-accent` 是**非文本图形色**（各皮肤按 3:1 校准），
    # 白字压它必然不够，所以皮肤选中角标改走 `--qm-btn-bg`（各皮肤为文字专门钳制过）。
    # 全项目 `color: var(--qm-on-accent)` 只与 `btn-bg` / `btn-bg-hi` 配对，这里删掉
    # 这条过期配对 —— 留着只会每天误报 s03 / s12，让 `--fails` 失去门禁价值。
    # 结论记进 docs/项目约定.md：`--qm-accent` 不得用作文字底色。
    ("面板 / 页面底色", "surface", "bg", 1.0, "仅记录：soft UI 靠阴影分层，不靠底色差", True),
)

_DECL = re.compile(r"--qm-([a-z0-9-]+)\s*:\s*([^;]+);")
_HEX = re.compile(r"^#([0-9a-fA-F]{3,8})$")


def read_vars(text: str) -> dict[str, str]:
    """抓一段 CSS 里的 `--qm-*: value;`（忽略含 `var(` 的引用型变量）。"""
    out: dict[str, str] = {}
    for name, value in _DECL.findall(text):
        value = value.strip()
        if "var(" in value:
            continue
        out[name] = value
    return out


def split_dark(tokens: str) -> tuple[str, str]:
    """把 tokens.css 拆成「亮色主体」与「prefers-color-scheme: dark 段」。"""
    mark = tokens.find("@media (prefers-color-scheme: dark)")
    if mark < 0:
        return tokens, ""
    return tokens[:mark], tokens[mark:]


def parse_color(value: str) -> tuple[int, int, int] | None:
    """只支持十六进制（本项目所有文本/背景令牌都是 hex；rgba 的是边框与阴影）。"""
    m = _HEX.match(value.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:      # #RRGGBBAA —— 透明度不为 0 时按 RGB 处理（近似，够用）
        h = h[:6]
    if len(h) != 6:
        return None
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lin(channel: int) -> float:
    s = channel / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float | None:
    a, b = parse_color(fg), parse_color(bg)
    if a is None or b is None:
        return None
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def themes() -> list[tuple[str, dict[str, str]]]:
    """返回 [(主题名, 变量表)]：默认亮色、默认深色、16 款皮肤。"""
    tokens_text = _TOKENS.read_text(encoding="utf-8")
    light_part, dark_part = split_dark(tokens_text)
    light = read_vars(light_part)
    out: list[tuple[str, dict[str, str]]] = [("默认（亮色）", light)]

    if dark_part:
        dark = dict(light)
        dark.update(read_vars(dark_part))
        out.append(("默认（深色）", dark))

    for path in sorted(_SKINS.glob("s*.css")):
        skin = dict(light)
        skin.update(read_vars(path.read_text(encoding="utf-8")))
        out.append((path.stem, skin))
    return out


def audit() -> list[dict]:
    rows: list[dict] = []
    for theme, variables in themes():
        for label, fg_key, bg_key, floor, note, advisory in PAIRS:
            fg, bg = variables.get(fg_key), variables.get(bg_key)
            if not fg or not bg:
                rows.append({
                    "theme": theme, "pair": label, "fg": fg or "—", "bg": bg or "—",
                    "ratio": None, "floor": floor, "pass": False, "note": "缺变量",
                    "advisory": advisory,
                })
                continue
            ratio = contrast(fg, bg)
            rows.append({
                "theme": theme, "pair": label, "fg": fg, "bg": bg,
                "ratio": ratio, "floor": floor,
                "pass": ratio is not None and ratio >= floor, "note": note,
                "advisory": advisory,
            })
    return rows


def report(rows: list[dict], *, only_fails: bool, as_json: bool) -> int:
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0 if all(r["pass"] for r in rows) else 1

    themes_seen: list[str] = []
    for r in rows:
        if r["theme"] not in themes_seen:
            themes_seen.append(r["theme"])

    graded = [r for r in rows if not r["advisory"]]
    fails = [r for r in graded if not r["pass"]]
    print(f"[对比度审计] 主题 {len(themes_seen)} 个 × 配对 {len(PAIRS)} 组 = {len(rows)} 条"
          f"（判定 {len(graded)} 条 / 仅记录 {len(rows) - len(graded)} 条）")
    print(f"[对比度审计] 不达标 {len(fails)} 条\n")

    for theme in themes_seen:
        mine = [r for r in rows if r["theme"] == theme]
        bad = [r for r in mine if not r["pass"]]
        if only_fails and not bad:
            continue
        worst = min((r for r in mine if r["ratio"] is not None and not r["advisory"]),
                    key=lambda r: r["ratio"], default=None)
        head = f"── {theme}"
        if worst:
            head += f"　最低 {worst['ratio']:.2f}（{worst['pair']}）"
        print(head)
        for r in (bad if only_fails else mine):
            if r["ratio"] is None:
                print(f"   ?  {r['pair']}: {r['note']}")
                continue
            flag = "REC" if r["advisory"] else ("OK " if r["pass"] else "FAIL")
            mark = "" if (r["pass"] or r["advisory"]) else "  ← 低于门槛"
            print(f"   {flag} {r['ratio']:5.2f} (≥{r['floor']:.1f})  {r['pair']}"
                  f"  {r['fg']} on {r['bg']}{mark}")
        print()

    if fails:
        print("[对比度审计] 不达标明细：")
        for r in fails:
            ratio = "—" if r["ratio"] is None else f"{r['ratio']:.2f}"
            print(f"  · {r['theme']} · {r['pair']}：{ratio} < {r['floor']:.1f}（{r['note'] or '正文'}）")
    return 0 if not fails else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="配色对比度审计（WCAG 2.1）")
    ap.add_argument("--fails", action="store_true", help="只打印不达标项")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)
    return report(audit(), only_fails=args.fails, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
