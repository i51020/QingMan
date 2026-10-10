"""青蔓 QingMan · promote 工具单元测试（§P0-2 T2 / 审查报告 §P2-7）。

重点：`list_files` 是「主线非空」拦截判据的基础 —— 必须把 `VERSION` 也算进去，
否则一个**只含 VERSION** 的主线会被误判为「空」而放行（`--force` 拦截失效）。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import promote  # noqa: E402


class ListFilesTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_promote_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_empty_root_is_empty(self):
        self.assertEqual(promote.list_files(self.root), set())

    def test_version_alone_counts_as_nonempty(self):
        # §P2-7 核心：只含 VERSION 的主线不得被判成「空」
        (self.root / "VERSION").write_text("V0.0.1\n", encoding="utf-8", newline="\n")
        self.assertEqual(promote.list_files(self.root), {"VERSION"})

    def test_includes_src_and_start_bat(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("x\n", encoding="utf-8")
        (self.root / "start.bat").write_text("@echo off\r\n", encoding="utf-8")
        self.assertEqual(promote.list_files(self.root), {"src/a.py", "start.bat"})

    def test_ignores_pycache(self):
        (self.root / "src" / "__pycache__").mkdir(parents=True)
        (self.root / "src" / "__pycache__" / "a.pyc").write_bytes(b"x")
        (self.root / "src" / "a.py").write_text("x\n", encoding="utf-8")
        self.assertEqual(promote.list_files(self.root), {"src/a.py"})


class DefaultSourceTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_promote_ds_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_derives_from_version(self):
        (self.root / "VERSION").write_text("V0.0.26\n", encoding="utf-8", newline="\n")
        self.assertEqual(promote.default_source(self.root), "preview/V0.0.26")

    def test_falls_back_when_version_missing(self):
        self.assertEqual(promote.default_source(self.root), "preview")


if __name__ == "__main__":
    unittest.main()
