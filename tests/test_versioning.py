"""青蔓 QingMan · versioning / release 单元测试（§P0-2 T2）。

SemVer 三段式三语义：patch / minor / major；
以及 `release.do_bump` 的副作用与**提示时机**（审查报告 §P2-6）。
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import release  # noqa: E402
import versioning  # noqa: E402


class ParseTests(unittest.TestCase):

    def test_parse_valid(self):
        self.assertEqual(versioning.parse("V0.0.1"), (0, 0, 1))
        self.assertEqual(versioning.parse("V1.2.3"), (1, 2, 3))
        self.assertEqual(versioning.parse("  V0.10.20  "), (0, 10, 20))

    def test_parse_invalid(self):
        for bad in ("", "0.0.1", "v0.0.1", "V0.1", "V0.0.1.2", "V0.0.x", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                versioning.parse(bad)

    def test_is_legacy(self):
        self.assertTrue(versioning.is_legacy("V0.01"))
        self.assertTrue(versioning.is_legacy("V0.1"))
        self.assertFalse(versioning.is_legacy("V0.0.1"))
        self.assertFalse(versioning.is_legacy("V1.2.3"))

    def test_format_version(self):
        self.assertEqual(versioning.format_version((0, 0, 1)), "V0.0.1")
        with self.assertRaises(ValueError):
            versioning.format_version((0, -1, 0))


class BumpTests(unittest.TestCase):
    """三语义的**归零**行为是最容易写错的地方，逐条锁定。"""

    def test_patch(self):
        self.assertEqual(versioning.bump("V0.0.1"), "V0.0.2")
        self.assertEqual(versioning.bump("V0.0.3"), "V0.0.4")
        self.assertEqual(versioning.bump("V1.2.3", "patch"), "V1.2.4")

    def test_minor_resets_patch(self):
        self.assertEqual(versioning.bump("V0.0.2", "minor"), "V0.1.0")
        self.assertEqual(versioning.bump("V0.4.7", "minor"), "V0.5.0")
        self.assertEqual(versioning.bump("V1.2.3", "minor"), "V1.3.0")

    def test_major_resets_minor_and_patch(self):
        self.assertEqual(versioning.bump("V0.1.0", "major"), "V1.0.0")
        self.assertEqual(versioning.bump("V0.9.9", "major"), "V1.0.0")

    def test_default_kind_is_patch(self):
        self.assertEqual(versioning.bump("V0.0.1"), versioning.bump("V0.0.1", "patch"))

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            versioning.bump("V0.0.1", "hotfix")

    def test_kinds_exposed(self):
        self.assertEqual(versioning.KINDS, ("patch", "minor", "major"))


class ReleaseBumpTests(unittest.TestCase):
    """`release.do_bump` 的**副作用与提示时机**（审查报告 §P2-6）。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="qm_release_bump_"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_version(self, text: str) -> None:
        with (self.root / "VERSION").open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def test_bumps_and_writes_lf(self):
        self._write_version("V0.0.1\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = release.do_bump(self.root, "patch")
        self.assertEqual(rc, 0)
        self.assertEqual((self.root / "VERSION").read_bytes(), b"V0.0.2\n",
                         "bump 写盘必须是 LF（不得随平台漂移）")
        self.assertIn("[升级] V0.0.1 → V0.0.2", out.getvalue())

    def test_rollback_hint_precedes_version_change(self):
        """§P2-6：回退点提示必须在**改写 VERSION 之前**出现，否则用户看到时已太晚。"""
        self._write_version("V0.0.1\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            release.do_bump(self.root, "minor")
        lines = out.getvalue().splitlines()
        hint = next((i for i, s in enumerate(lines) if "回退点" in s), -1)
        bumped = next((i for i, s in enumerate(lines) if "[升级]" in s), -1)
        self.assertNotEqual(hint, -1, "缺少回退点提示")
        self.assertNotEqual(bumped, -1, "缺少升级提示")
        self.assertLess(hint, bumped, "回退点提示必须早于升级提示")

    def test_invalid_version_fails_without_touching_file(self):
        self._write_version("0.0.1\n")            # 缺少 V 前缀 → bump 应失败
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = release.do_bump(self.root, "patch")
        self.assertEqual(rc, 1)
        self.assertIn("[失败]", out.getvalue())
        self.assertNotIn("回退点", out.getvalue(), "失败路径不应给出回退点提示")
        self.assertEqual((self.root / "VERSION").read_text(encoding="utf-8"), "0.0.1\n",
                         "失败时不得改动 VERSION")


if __name__ == "__main__":
    unittest.main()
