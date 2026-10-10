"""青蔓 QingMan · verify 工具层判定单元测试（§P0-2 T2 / §P2 第 19、20 项）。

覆盖 `tools/verify.py` 里**承担判定职责**的纯函数 —— 按 §P2 第 19 项的裁定：
「凡承担判定职责的工具函数，必须有单元测试」。当前覆盖「托管 node 取最新」这一组
（§P2 第 20 项 / 审查报告 §P2-2：旧实现硬编码 `versions/22.22.2-6/node.exe`，
托管运行时一升级即失效）。
"""

from __future__ import annotations

import shutil
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


if __name__ == "__main__":
    unittest.main()
