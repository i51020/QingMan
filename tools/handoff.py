"""青蔓 QingMan · 跨会话接续卡生成器。

把「项目实况」从盘上自动取出，写进 `docs/接续说明.md` 的实况段，
使新会话（或另一个 AI 平台）能以最小成本无损接手本项目。

用法：
    python tools/handoff.py            重新生成实况段并写回
    python tools/handoff.py --check    只比对不写盘；返回码 0=一致 1=不一致
    python tools/handoff.py --print    打印将写入的实况段，不写盘
    python tools/handoff.py --root DIR 指定项目根（缺省为脚本上一级）

设计约束（对应 docs/项目约定.md §P1-6）：
  * 只重写 `<!-- HANDOFF:BEGIN` 与 `<!-- HANDOFF:END -->` 之间的内容；
    锚点段与意图段属手工区，工具**绝不触碰**。标记缺失即报错，不代猜。
  * 实况段只收录**稳定的盘上数据**（VERSION / 清单链 / 版本 tag 与修订 tag / 文件数 /
    时间线首条），**不含当前时刻、也不含 git HEAD** —— 否则每次提交都会让本段自锁过期。
    因此可幂等比对（`--check`）。
  * 复用 `tools/store.py` 的接口，不重复实现；不依赖任何第三方包。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
sys.dont_write_bytecode = True  # 生成器不得在被处理的项目里留下 __pycache__
import store  # noqa: E402

HANDOFF_REL = "docs/接续说明.md"
BEGIN = "<!-- HANDOFF:BEGIN"
END = "<!-- HANDOFF:END -->"
_BLOCK = re.compile(r"(<!-- HANDOFF:BEGIN[^\n]*\n)(.*?)(<!-- HANDOFF:END -->)", re.S)

GIT_TIMEOUT = 20

# tag 形态：版本 tag = `V<x>.<y>.<z>`；修订 tag = `V<x>.<y>.<z>-r<n>`（§P0-6）
_VERSION_TAG = re.compile(r"^V\d+\.\d+\.\d+$")
_REV_TAG = re.compile(r"^V\d+\.\d+\.\d+-r\d+$")
TAG_SHOW = 5  # 实况段里列出的「最近 N 个版本 tag」


# ---------- 基础 ----------

def read_version(root: Path) -> str:
    f = root / "VERSION"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else "(无 VERSION 文件)"


def git(root: Path, *args: str) -> str | None:
    """执行 git 子命令；成功返回去尾换行的 stdout，失败或不可用返回 None。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def fingerprint_state(root: Path, version: str, rev: int | None) -> str:
    """主线（src/ + start.bat + VERSION）与指定修订清单的比对结论。"""
    meta = store.load_manifest(root, version, rev)
    if not meta:
        return "无法判定（未找到清单）"
    # 比对逻辑单点在 store.fingerprint_diff（§P2-9：原先与 verify 各写一份）。
    changed, added, missing = store.fingerprint_diff(root, meta.get("files", {}))
    if not (changed or added or missing):
        return "**完全一致**"
    return f"改动 {len(changed)} / 新增 {len(added)} / 缺失 {len(missing)}"


def count_blobs(root: Path) -> int:
    d = root / "store" / "objects"
    return sum(1 for f in d.rglob("*") if f.is_file()) if d.is_dir() else 0


def count_git_files(root: Path) -> int | None:
    out = git(root, "ls-files")
    return len(out.splitlines()) if out is not None else None


def _version_key(tag: str) -> tuple[int, int, int]:
    """`V0.0.25` → (0, 0, 25)；`V0.0.1-r2` → (0, 0, 1)。用于按版本号排序。"""
    core = tag.split("-r", 1)[0].lstrip("V")
    a, b, c = (int(p) for p in core.split("."))
    return (a, b, c)


def split_tags(root: Path) -> tuple[list[str], list[str]]:
    """把 git tag 分成（版本 tag 升序, 修订 tag 升序）。

    旧实现只列 `git tag -l "V*-r*"`（修订 tag），**版本 tag 全部缺席** —— 接续包会
    误导接手方以为项目最新 tag 停在 `V0.0.1-r3`（《审查报告_工具链_20261010》§P1-3a）。
    """
    raw = git(root, "tag", "-l", "V*") or ""
    names = [t.strip() for t in raw.splitlines() if t.strip()]
    version_tags = sorted((t for t in names if _VERSION_TAG.match(t)), key=_version_key)
    rev_tags = sorted((t for t in names if _REV_TAG.match(t)),
                      key=lambda t: (_version_key(t), int(t.rsplit("-r", 1)[1])))
    return version_tags, rev_tags


def timeline_latest(root: Path) -> str | None:
    """docs/任务进度.md 时间线（倒序）的首条：日期 + 时间 + 标题。

    日期正则**不得**要求整行只有日期 —— 标题形如 `### 2026-10-10（续十五）` 带后缀，
    原实现用 `\\s*$` 收尾会匹配失败，致日期恒显示 `(未标日期)`（§P1-3b）。
    """
    f = root / "docs" / "任务进度.md"
    if not f.is_file():
        return None
    date: str | None = None
    for raw in f.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = re.match(r"^###\s+(\d{4}-\d{2}-\d{2})", line)
        if m:
            date = m.group(1)
            continue
        m = re.match(r"^####\s+(.+?)\s*$", line)
        if m:
            return f"{date or '(未标日期)'} · {m.group(1)}"
    return None


# ---------- 渲染 ----------

def render_live(root: Path) -> str:
    """渲染实况段正文（不含 HANDOFF 标记）。纯函数：同一盘上状态必得同一输出。"""
    out: list[str] = []
    version = read_version(root)
    vers = store.list_versions(root)

    out.append(f"**项目根**：`{root}`")
    out.append("")

    if vers:
        cur = version if version in vers else vers[-1]
        rev = store.latest_revision(root, cur)
        same_version = "是" if cur == version else f"否（`VERSION` 文件为 `{version}`）"
        out.append(f"**当前版本**：`{cur}`　·　最新修订 `r{rev}`　·　与 `VERSION` 一致：{same_version}")
        out.append("")
        out.append("**修订链**")
        out.append("")
        out.append("| 引用 | 时间 | 说明 |")
        out.append("|---|---|---|")
        for v in vers:
            for r in store.revisions(root, v):
                meta = store.load_manifest(root, v, r) or {}
                note = (meta.get("note") or "—").replace("|", "\\|")
                out.append(f"| `{v}@r{r}` | {meta.get('createdAt', '—')} | {note} |")
        out.append("")
        out.append(f"**回退**：`python tools/store.py checkout {cur}`（最高修订）"
                   f" ／ `checkout {cur}@r1`（基线）")
        out.append("")
        out.append(f"**主线指纹**：与 `{cur}@r{rev}` {fingerprint_state(root, cur, rev)}")
        verify_ref = cur
    else:
        out.append(f"**版本**：`{version}`（尚无任何版本清单，未曾 `store.py commit`）")
        verify_ref = version
    out.append("")

    dirty = git(root, "status", "--porcelain")
    if dirty is None:
        out.append("**过程历史（git）**：未初始化仓库或 git 不可用")
    else:
        # 忽略接续说明自身 —— 它由本工具写入，若计入会让状态自锁
        others = [ln for ln in dirty.splitlines() if HANDOFF_REL not in ln]
        state = "工作区干净" if not others else f"工作区有 {len(others)} 处未提交改动"
        out.append(f"**过程历史（git）**：{state}　·　过程历史看 `git log --oneline`")
        out.append("")
        # 版本 tag 与修订 tag **分列**：旧实现只列 `V*-r*`，版本 tag 全部缺席（§P1-3a）
        version_tags, rev_tags = split_tags(root)
        if version_tags:
            shown = version_tags[-TAG_SHOW:]
            tag_text = "`" + "` `".join(shown) + "`"
            out.append(f"**版本 tag**：最近 {len(shown)} 个：{tag_text}　·　共 {len(version_tags)} 个")
        else:
            out.append("**版本 tag**：（无）")
        rev_text = "`" + "` `".join(rev_tags) + "`" if rev_tags else "（无）"
        out.append(f"**修订 tag**：{rev_text}")
    out.append("")

    tracked = len(store.collect_files(root))
    git_n = count_git_files(root)
    scope = f"版本清单跟踪 **{tracked}** 文件"
    if git_n is not None:
        scope += f"　·　git 跟踪 **{git_n}** 项"
    out.append(f"**规模**：{scope}　·　对象池 **{count_blobs(root)}** blob")
    out.append("")

    tl = timeline_latest(root)
    if tl:
        out.append(f"**时间线最新**：{tl}")
        out.append("")

    out.append(f"**校验**：`python tools/verify.py . --against {verify_ref}`")
    return "\n".join(out).rstrip() + "\n"


# ---------- 写回 ----------

def replace_block(text: str, body: str) -> str:
    """只替换 HANDOFF 标记之间的内容，其余原样保留。标记缺失即抛错。"""
    m = _BLOCK.search(text)
    if not m:
        raise ValueError(f"未找到标记 {BEGIN} ... {END}")
    return text[:m.start()] + m.group(1) + body.rstrip("\n") + "\n" + m.group(3) + text[m.end():]


def write_text(path: Path, text: str) -> None:
    """UTF-8 无 BOM + LF 写盘（兼容 Python 3.8，Path.write_text 的 newline 参数 3.10 才有）。"""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---------- 入口 ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 跨会话接续卡生成器")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--check", action="store_true", help="只比对不写盘；0=一致 1=不一致")
    parser.add_argument("--print", dest="do_print", action="store_true", help="打印将写入的实况段，不写盘")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    target = root / HANDOFF_REL
    if not target.is_file():
        print(f"[失败] 接续说明不存在：{target}")
        return 1

    try:
        body = render_live(root)
        text = target.read_text(encoding="utf-8")
        new_text = replace_block(text, body)
    except ValueError as exc:
        print(f"[失败] {target}：{exc}")
        return 1

    if args.do_print:
        print(body, end="")
        return 0

    if args.check:
        if new_text == text:
            print("[一致] 接续说明实况段与盘上一致")
            return 0
        print("[不一致] 实况段已过期，请运行：python tools/handoff.py")
        return 1

    if new_text == text:
        print(f"[跳过] 实况段已是最新：{target}")
        return 0

    write_text(target, new_text)
    print(f"[写入] {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
