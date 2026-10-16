"""青蔓 QingMan · verify 工具层判定单元测试（§P0-2 T2 / §P2 第 19、20 项）。

覆盖 `tools/verify.py` 里**承担判定职责**的纯函数 —— 按 §P2 第 19 项的裁定：
「凡承担判定职责的工具函数，必须有单元测试」。当前覆盖「托管 node 取最新」这一组
（§P2 第 20 项 / 审查报告 §P2-2：旧实现硬编码 `versions/22.22.2-6/node.exe`，
托管运行时一升级即失效）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import verify  # noqa: E402


def rmtree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


class NodeVersionKeyTests(unittest.TestCase):

    def test_parses_digits(self):
        self.assertEqual(verify.node_version_key("22.22.2-6"), (22, 22, 2, 6))
        self.assertEqual(verify.node_version_key("24.21.0"), (24, 21, 0))

    def test_ordered_by_number_not_lexicographically(self):
        # 字典序会把 "9" 排在 "24" 之后 —— 必须按数字比较
        self.assertGreater(verify.node_version_key("24.21.0"),
                           verify.node_version_key("9.11.2"))

    def test_non_numeric_yields_empty(self):
        self.assertEqual(verify.node_version_key("current"), ())
        self.assertEqual(verify.node_version_key(".locks"), ())


class RawColorHitsTests(unittest.TestCase):
    """D-P2-1：「组件 CSS 无裸色值」判据须覆盖 rgb()/rgba()/hsl()/hsla()，不能只认 #hex。"""

    def test_detects_hex(self):
        self.assertIn("#1e2732", verify.raw_color_hits("color: #1e2732;"))

    def test_detects_rgb_and_rgba(self):
        self.assertTrue(verify.raw_color_hits("box-shadow: inset 1px 1px 3px rgba(0, 0, 0, .25);"))
        self.assertTrue(verify.raw_color_hits("background: rgb(1 2 3);"))

    def test_detects_hsl(self):
        self.assertTrue(verify.raw_color_hits("color: hsl(120 50% 50%);"))

    def test_ignores_var_reference(self):
        self.assertEqual(
            verify.raw_color_hits("color: var(--qm-text); box-shadow: var(--qm-inset);"), [])


class RawFontSizeHitsTests(unittest.TestCase):
    """§P0-3 L4「禁止裸尺寸」的**字号档**：判据须**白名单式** —— 取值必须以 `var(--qm-` 打头。

    只否掉 px 会让 `1rem` / `inherit` 溜过去（"不是 px"≠"走了 token"）。
    """

    def test_detects_px_literal(self):
        self.assertIn("font-size:12px", verify.raw_font_size_hits(".a { font-size: 12px; }"))

    def test_detects_non_px_literal(self):
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: 1rem; }"))
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: inherit; }"))

    def test_detects_without_trailing_semicolon(self):
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: 13px }"))

    def test_ignores_token_reference(self):
        self.assertEqual(
            verify.raw_font_size_hits(".a { font-size: var(--qm-fs-md); }"), [])
        self.assertEqual(
            verify.raw_font_size_hits(".a{font-size:var(--qm-fs-3xl)}"), [])

    def test_ignores_other_size_properties(self):
        # 本条**只管字号**：间距 / 圆角的裸值不在判据内（已知缺口，见 §P2 第 44 项）
        self.assertEqual(
            verify.raw_font_size_hits(".a { padding: 6px 10px; border-radius: 4px; }"), [])


class IterManagedNodesTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="qm_verify_nodes_"))

    def tearDown(self):
        rmtree(self.root)

    def _mk(self, name: str, *, with_exe: bool = True) -> None:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        if with_exe:
            (d / "node.exe").write_bytes(b"stub")

    def test_picks_newest_first(self):
        for name in ("22.22.2-6", "24.21.0", "23.11.1"):
            self._mk(name)
        got = [p.parent.name for p in verify.iter_managed_nodes(self.root)]
        self.assertEqual(got, ["24.21.0", "23.11.1", "22.22.2-6"])

    def test_ignores_dirs_without_node_exe(self):
        self._mk("24.21.0")
        self._mk("current", with_exe=False)
        (self.root / ".locks").mkdir()
        got = [p.parent.name for p in verify.iter_managed_nodes(self.root)]
        self.assertEqual(got, ["24.21.0"])

    def test_missing_base_returns_empty(self):
        self.assertEqual(verify.iter_managed_nodes(self.root / "nope"), [])

    def test_empty_base_returns_empty(self):
        self.assertEqual(verify.iter_managed_nodes(self.root), [])


class FindNodeTests(unittest.TestCase):

    def test_returns_existing_node_or_none(self):
        node = verify.find_node()
        if node is None:
            self.skipTest("本机无 node —— find_node 返回 None 属正确降级")
        self.assertTrue(Path(node).is_file(), f"find_node 返回了不存在的路径：{node}")


class ArgParsingTests(unittest.TestCase):
    """§P2-16：多余位置参数须报错，不得静默忽略。"""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(_TOOLS / "verify.py"), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_extra_positional_arg_rejected(self):
        proc = self._run("root1", "root2")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("多余的参数", proc.stdout)

    def test_single_arg_not_flagged_as_extra(self):
        # 只传一个根目录（不存在）→ 应走「目录不存在」，绝非「多余的参数」
        proc = self._run(str(_TOOLS / "nonexistent_root_xyz"))
        self.assertNotIn("多余的参数", proc.stdout)


if __name__ == "__main__":
    unittest.main()
