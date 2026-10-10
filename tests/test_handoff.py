"""青蔓 QingMan · handoff 单元测试（§P0-2 T2 / 审查报告 §P1-3、§P1-4）。

`tools/handoff.py` 决定**跨会话接续卡**的内容 —— 它是新会话（或另一个 AI 平台）
无损接手本项目的唯一载体，渲染失真即等于误导接手方。此前它**零单测**，
只靠 `verify` 的「实况段与盘上一致」自洽比对 —— 而那**证不了内容正确**
（比对两端都出自同一个函数）。

本文件把 §P1-3 的两处失真固化为**常态回归网**：
  * P1-3a：版本 tag 必须与修订 tag **分列**，且按**语义版本**升序（不是字典序）；
  * P1-3b：「时间线最新」必须解析出日期 —— 标题带 `（续十五）` 这类后缀也要认。
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import handoff  # noqa: E402

HAS_GIT = shutil.which("git") is not None


def rmtree_force(path: Path) -> None:
    """清理临时目录。

    ⚠️ Windows 下 `.git/objects` 里的文件是**只读**的，裸 `shutil.rmtree` 会抛
    `PermissionError` 并**留下残留**（实测：本文件首版即因它在 `%TEMP%` 里留下一串
    `qm_handoff_*`）。故先把整棵树改回可写再删。
    """
    for p in [path, *path.rglob("*")]:
        try:
            os.chmod(p, stat.S_IWRITE)
        except OSError:
            pass
    shutil.rmtree(path, ignore_errors=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def make_repo(root: Path, tags: tuple[str, ...]) -> None:
    """在 root 里建一个最小 git 仓库并打好指定 tag（供 tag / render 相关用例）。"""
    git(root, "init", "-q")
    git(root, "-c", "user.email=t@example.com", "-c", "user.name=t",
        "commit", "-q", "--allow-empty", "-m", "init")
    for t in tags:
        git(root, "tag", t)


class VersionKeyTests(unittest.TestCase):

    def test_parses_three_segments(self):
        self.assertEqual(handoff._version_key("V0.0.25"), (0, 0, 25))
        self.assertEqual(handoff._version_key("V1.2.10"), (1, 2, 10))

    def test_ignores_revision_suffix(self):
        self.assertEqual(handoff._version_key("V0.0.1-r2"), (0, 0, 1))
        self.assertEqual(handoff._version_key("V0.0.3-r11"), (0, 0, 3))


class GitFallbackTests(unittest.TestCase):

    def test_returns_none_outside_repo(self):
        tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_nogit_"))
        try:
            self.assertIsNone(handoff.git(tmp, "tag", "-l", "V*"))
        finally:
            rmtree_force(tmp)

    def test_split_tags_empty_outside_repo(self):
        tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_nogit2_"))
        try:
            self.assertEqual(handoff.split_tags(tmp), ([], []))
        finally:
            rmtree_force(tmp)


@unittest.skipUnless(HAS_GIT, "git 不可用")
class SplitTagsTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_tags_"))
        make_repo(self.tmp, ("V0.0.10", "V0.0.2", "V0.0.1",
                             "V0.0.1-r3", "V0.0.1-r2",
                             "notatag", "V0.1.0-rc1"))

    def tearDown(self):
        rmtree_force(self.tmp)

    def test_version_tags_sorted_semantically_not_lexically(self):
        version_tags, _rev = handoff.split_tags(self.tmp)
        # 字典序会把 V0.0.10 排在 V0.0.2 之前 —— 必须是语义序（§P1-3a）
        self.assertEqual(version_tags, ["V0.0.1", "V0.0.2", "V0.0.10"])

    def test_revision_tags_kept_separate_and_sorted(self):
        _ver, rev_tags = handoff.split_tags(self.tmp)
        self.assertEqual(rev_tags, ["V0.0.1-r2", "V0.0.1-r3"])

    def test_non_matching_tags_ignored(self):
        version_tags, rev_tags = handoff.split_tags(self.tmp)
        for odd in ("notatag", "V0.1.0-rc1"):
            self.assertNotIn(odd, version_tags)
            self.assertNotIn(odd, rev_tags)


class TimelineLatestTests(unittest.TestCase):

    def _root(self, body: str) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_tl_"))
        write(tmp / "docs" / "任务进度.md", body)
        return tmp

    def test_parses_date_with_parenthetical_suffix(self):
        """P1-3b 回归位：`### 2026-10-10（续十六）` 必须解析出日期。"""
        tmp = self._root(
            "# 任务进度\n\n## 时间线（倒序，最新在上）\n\n"
            "### 2026-10-10（续十六）\n\n"
            "#### 22:16 – 22:20 · 工具链整改 2.2\n\n"
        )
        try:
            got = handoff.timeline_latest(tmp)
            self.assertEqual(got, "2026-10-10 · 22:16 – 22:20 · 工具链整改 2.2")
            self.assertNotIn("(未标日期)", got)
        finally:
            rmtree_force(tmp)

    def test_parses_bare_date_heading(self):
        tmp = self._root("### 2026-10-09\n\n#### 09:00 · 某步\n")
        try:
            self.assertEqual(handoff.timeline_latest(tmp), "2026-10-09 · 09:00 · 某步")
        finally:
            rmtree_force(tmp)

    def test_first_entry_wins(self):
        tmp = self._root("### 2026-10-10（续二）\n\n#### 新的一条\n\n"
                         "### 2026-10-09\n\n#### 旧的一条\n")
        try:
            self.assertEqual(handoff.timeline_latest(tmp), "2026-10-10 · 新的一条")
        finally:
            rmtree_force(tmp)

    def test_unlabelled_heading_degrades_visibly(self):
        # 没有日期标题时显式降级为哨兵值 —— verify 的 8c 断言正是抓这个
        tmp = self._root("### 待整理\n\n#### 某步\n")
        try:
            self.assertEqual(handoff.timeline_latest(tmp), "(未标日期) · 某步")
        finally:
            rmtree_force(tmp)

    def test_missing_file_returns_none(self):
        tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_tl2_"))
        try:
            self.assertIsNone(handoff.timeline_latest(tmp))
        finally:
            rmtree_force(tmp)


class ReplaceBlockTests(unittest.TestCase):

    DOC = ("前言\n<!-- HANDOFF:BEGIN -->\n旧内容\n<!-- HANDOFF:END -->\n后记\n")

    def test_replaces_only_inside_markers(self):
        out = handoff.replace_block(self.DOC, "新内容\n")
        self.assertEqual(out, "前言\n<!-- HANDOFF:BEGIN -->\n新内容\n<!-- HANDOFF:END -->\n后记\n")
        self.assertIn("前言", out)
        self.assertIn("后记", out)
        self.assertNotIn("旧内容", out)

    def test_raises_when_markers_missing(self):
        with self.assertRaises(ValueError):
            handoff.replace_block("没有任何标记\n", "x\n")


@unittest.skipUnless(HAS_GIT, "git 不可用")
class RenderLiveTests(unittest.TestCase):
    """`render_live` 是实况段的唯一来源 —— 直接断言它的两处关键输出（§P1-3）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_handoff_render_"))
        write(self.tmp / "VERSION", "V0.0.2\n")
        write(self.tmp / "docs" / "任务进度.md",
              "### 2026-10-10（续十六）\n\n#### 22:16 · 工具链整改\n")
        make_repo(self.tmp, ("V0.0.1", "V0.0.2", "V0.0.1-r2"))
        self.body = handoff.render_live(self.tmp)

    def tearDown(self):
        rmtree_force(self.tmp)

    def _line(self, prefix: str) -> str:
        return next((ln for ln in self.body.splitlines() if ln.startswith(prefix)), "")

    def test_version_tag_line_exists_and_contains_version(self):
        line = self._line("**版本 tag**")
        self.assertTrue(line, "实况段缺「版本 tag」行")
        self.assertIn("`V0.0.2`", line, "当前 VERSION 已打 tag，必须出现在行内（§P1-3a）")
        self.assertIn("`V0.0.1`", line)

    def test_revision_tag_line_separate(self):
        line = self._line("**修订 tag**")
        self.assertIn("V0.0.1-r2", line)
        self.assertNotIn("V0.0.2`", line, "版本 tag 不得混进修订 tag 行")

    def test_timeline_line_has_real_date(self):
        line = self._line("**时间线最新**")
        self.assertTrue(line, "实况段缺「时间线最新」行")
        self.assertNotIn("(未标日期)", line, "日期未解析（§P1-3b 回归）")
        self.assertIn("2026-10-10", line)

    def test_render_is_pure(self):
        self.assertEqual(handoff.render_live(self.tmp), self.body,
                         "同一盘上状态必须渲染出逐字节相同的实况段（可幂等比对）")

    def _process_line(self) -> str:
        return next((ln for ln in handoff.render_live(self.tmp).splitlines()
                     if ln.startswith("**过程历史")), "")

    def test_clean_tree_reports_clean(self):
        git(self.tmp, "add", "-A")
        git(self.tmp, "-c", "user.email=t@example.com", "-c", "user.name=t",
            "commit", "-q", "-m", "all")
        line = self._process_line()
        self.assertIn("工作区干净", line)
        self.assertNotIn("未跟踪", line)

    def test_dirty_state_splits_modified_and_untracked(self):
        # §P2-19：既有未跟踪（setUp 写的 VERSION/docs 未提交），再制造一个「已修改」
        write(self.tmp / "tracked.txt", "a\n")
        git(self.tmp, "add", "tracked.txt")
        git(self.tmp, "-c", "user.email=t@example.com", "-c", "user.name=t",
            "commit", "-q", "-m", "add tracked")
        write(self.tmp / "tracked.txt", "b\n")            # 已修改（跟踪文件）
        line = self._process_line()
        self.assertIn("未提交改动", line)
        self.assertIn("已修改", line)
        self.assertIn("未跟踪", line)


if __name__ == "__main__":
    unittest.main()
