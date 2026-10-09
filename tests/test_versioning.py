"""青蔓 QingMan · versioning 单元测试（§P0-2 T2）。

SemVer 三段式三语义：patch / minor / major。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

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


if __name__ == "__main__":
    unittest.main()
