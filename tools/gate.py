"""青蔓 QingMan · 单一交付门禁（V0.1.0 · 处理两条遗留风险）。

**它解决的两个真实摩擦**（都不是"代码 bug"，而是**流程会漏**）：

1. **`handoff` 与提交顺序耦合**（《项目手册》§十三 #5）：改了文件忘记刷 `handoff.py`，
   `verify` 第 8 项就红 —— 但人往往在跑完四件套之后才发现，又得重跑一遍。
   本工具**先刷实况段，再跑门禁**，顺序不再靠记忆。
2. **体积两条线**（`src/` ≤ 640K、单文件 ≤ 64K）只在越线时才被想起：
   `verify` 会判红，但没人知道"还剩多少"。本工具**每次都把两条线的余量打出来**，
   让预算在写代码时就在视野里（《错误笔记》§三.70）。

**顺带（默认关闭）**：`--doc-claims` 会把「文档里带版本号的断言」扫一遍，列出与当前
`VERSION` 不符的条目供人工核对。**为什么默认关**：实测 8 条命中里 7 条是**历史记录**
（《错误笔记》/ 手册沿革段本来就该写旧版本），精确度不足就是噪音 ——
**噪音一旦出现，人就会开始忽略它**，这比漏报更糟。精确判据仍是守卫 7ah（只钉「当前断言」的版本行）。

**用法**：

    py -3 tools/gate.py            # 全量：handoff + 四件套 + 两层清单 + 预算
    py -3 tools/gate.py --quick    # 跳过页面冒烟（最快，约 15 s）
    py -3 tools/gate.py --no-handoff   # 不刷实况段（只读检查）

**边界**：本工具**只调用**既有命令并汇总，不自己判断对错 ——
`verify` / `unittest` 才是判据的权威；这里多算一遍必然漂移。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
SRC_LIMIT = 640 * 1024        # 与 verify 的体积守卫同值；判红以 verify 为准
FILE_LIMIT = 64 * 1024
# 历史快照：里面的旧版本号是**记录**，不是断言，扫描时跳过
FROZEN_DOCS = {"任务进度.md", "接续说明.md"}
CLAIM_RE = re.compile(r"V\d+\.\d+\.\d+\s*实测")


def run(name: str, args: "list[str]", expect: "str | None" = None) -> "tuple[str, bool, float]":
    """跑一条命令，返回（摘要行, 是否成功, 耗时）。

    `expect` 是摘要行的正则：`unittest` 会往 stderr 写结论，而**被测代码自身的 stdout**
    （如单测里调 `store.py` 的提交日志）会夹在中间 —— 取"最后一行"会取到无关内容。
    实测过一次：摘要显示成 `[提交] 同版本第 2 次修订`，而不是 `Ran 559 tests / OK`。
    """
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, "-B", *args], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    cost = time.perf_counter() - started
    lines = ([ln.strip() for ln in (proc.stderr or "").splitlines()]
             + [ln.strip() for ln in (proc.stdout or "").splitlines()])
    tail = ""
    if expect:
        tail = next((ln for ln in reversed(lines) if re.match(expect, ln)), "")
    if not tail:
        tail = next((ln for ln in reversed(lines) if ln), "")
    ok = proc.returncode == 0
    return (f"{tail[:96]}", ok, cost) if ok else (f"RC={proc.returncode} {(tail or '')[:80]}", ok, cost)


def budget(root: Path = ROOT, src_limit: int = SRC_LIMIT,
           file_limit: int = FILE_LIMIT) -> "list[tuple[str, str]]":
    """两条体积线的当前值与余量（口径与 verify 一致：按字节求和）。"""
    src = root / "src"
    files = [p for p in src.rglob("*") if p.is_file()
             and "__pycache__" not in str(p)]
    total = sum(p.stat().st_size for p in files)
    biggest = max(files, key=lambda p: p.stat().st_size) if files else None
    rows = [("src/ 合计", f"{total:,} B / {src_limit:,} B（余 {src_limit - total:,}）"),
            ("单文件最大", f"{biggest.relative_to(root).as_posix()} {biggest.stat().st_size:,} B"
                            f" / {file_limit:,} B（余 {file_limit - biggest.stat().st_size:,}）"
             if biggest else "—")]
    return rows


def budget_alert(remaining: int, limit: int) -> str:
    """预算余量的预警级别：`ok` / `warn`（<5%）/ `crit`（<2%）。

    为什么要分级：只在「越线」时才报错，等于**永远在最后一刻才发现** —— 本仓已经历过一次
    「余 1,081 B 时被迫现场压注释」。预警线让「还能不能再加一个功能」在动手前就有答案。
    """
    if limit <= 0:
        return "ok"
    ratio = remaining / limit
    if ratio < 0.02:
        return "crit"
    if ratio < 0.05:
        return "warn"
    return "ok"


def budget_detail(root: Path = ROOT) -> "list[str]":
    """预算明细：总量、Top 文件、按类别占比、注释占比。

    它回答的不是「还剩多少」，而是「**下一次该从哪里省**」—— 没有明细时，
    人只会想到"删注释"，而注释恰恰是本项目最贵的资产（每条都记着为什么）。
    """
    src = root / "src"
    files = [p for p in src.rglob("*") if p.is_file() and "__pycache__" not in str(p)]
    total = sum(p.stat().st_size for p in files)
    rows = [f"总量 {total:,} B / {SRC_LIMIT:,} B（余 {SRC_LIMIT - total:,}，"
            f"{(SRC_LIMIT - total) / SRC_LIMIT:.1%}）"]
    rows.append("Top 文件：")
    for p in sorted(files, key=lambda x: -x.stat().st_size)[:6]:
        rows.append(f"  {p.stat().st_size:7,} B  {p.relative_to(src).as_posix()}")
    by_ext: "dict[str, int]" = {}
    for p in files:
        by_ext[p.suffix.lower()] = by_ext.get(p.suffix.lower(), 0) + p.stat().st_size
    rows.append("按类型：" + "  ".join(f"{k or '(无扩展名)'} {v:,}" for k, v in
                                     sorted(by_ext.items(), key=lambda kv: -kv[1])[:6]))
    comment = blank = 0
    for p in files:
        if p.suffix.lower() not in (".js", ".css", ".py"):
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            st = line.strip()
            if not st:
                blank += len(line.encode("utf-8")) + 1
            elif st.startswith(("//", "/*", "*", "#")):
                comment += len(line.encode("utf-8")) + 1
    rows.append(f"注释行 {comment:,} B（{comment/max(total,1):.1%}）/ 空行 {blank:,} B —— "
                f"**注释是资产，不是垃圾**：要省先省「历史沿革」类长注释（搬 docs），别省不变式说明")
    return rows


def doc_claims(root: Path = ROOT, version: str = VERSION) -> "list[str]":
    """文档里「V<x> 实测」且版本不是当前的条目（只提示，供人核对）。"""
    hits: "list[str]" = []
    for path in sorted((root / "docs").glob("*.md")):
        if path.name in FROZEN_DOCS or path.name.startswith("验收基线"):
            continue
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in CLAIM_RE.finditer(line):
                ver = match.group(0).split()[0]
                if ver != version:
                    hits.append(f"docs/{path.name}:{no} 写 {ver} 实测（当前 {version}）")
    return hits


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="青蔓交付门禁（一条命令跑全量）")
    ap.add_argument("--quick", action="store_true", help="跳过页面冒烟")
    ap.add_argument("--no-handoff", action="store_true", help="不刷新接续说明实况段")
    ap.add_argument("--budget", action="store_true", help="打印预算明细（Top 文件 / 类型 / 注释占比）")
    ap.add_argument("--doc-claims", action="store_true",
                    help="扫描文档里与当前版本不符的「V<x> 实测」断言（默认关：历史记录会误报）")
    args = ap.parse_args(argv)

    # (名称, 命令, 摘要行的匹配正则 —— 只对 unittest 必需，其余取最后一行)
    steps: "list[tuple[str, list[str], str | None]]" = []
    if not args.no_handoff:
        steps.append(("实况段刷新", ["tools/handoff.py"], None))
    steps += [
        ("交付校验", ["tools/verify.py", "."], r"^\[校验\] 结论"),
        ("单元测试", ["-m", "unittest", "discover", "-s", "tests"], r"^Ran "),
        ("端到端冒烟", ["tools/smoke.py"], r"^\[冒烟\] 结论"),
    ]
    if not args.quick:
        steps.append(("页面冒烟", ["tools/browser_smoke.py"], r"^\[冒烟·页面\] 结论"))
    steps.append(("两层清单", ["tools/manifest.py", "check"], r"^\[同步\]"))

    failures = 0
    print(f"[门禁] 版本 {VERSION}")
    for name, cmd, expect in steps:
        detail, ok, cost = run(name, cmd, expect)
        failures += 0 if ok else 1
        print(f"  {'OK  ' if ok else 'FAIL'} {name:8s} {cost:5.1f}s  {detail}")

    print("  ── 预算（两条线）──")
    rows = budget()
    for label, text in rows:
        print(f"     {label:8s} {text}")
    src_total = int(rows[0][1].split("/")[0].replace(",", "").replace("B", "").strip())
    level = budget_alert(SRC_LIMIT - src_total, SRC_LIMIT)
    if level != "ok":
        mark = "⚠ 预警" if level == "warn" else "⛔ 临界"
        print(f"     {mark}：src 余量 {(SRC_LIMIT - src_total)/SRC_LIMIT:.1%} —— "
              f"下一批请先做「减重或迁出内容」，不要再直接加功能")
    if args.budget:
        print("  ── 预算明细 ──")
        for line in budget_detail():
            print("     " + line)

    claims = doc_claims() if args.doc_claims else []
    if claims:
        print(f"  ── 文档断言提示（{len(claims)} 条，需人工核对）──")
        for item in claims[:5]:
            print(f"     {item}")
        if len(claims) > 5:
            print(f"     … 另 {len(claims) - 5} 条")

    print(f"[门禁] 结论：{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
