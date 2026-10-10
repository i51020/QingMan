"""青蔓 QingMan · 皮肤联动图标单元测试（V0.0.15 · §P0-2）。

覆盖：validate_ico 结构校验的正反例、_lnk_script 的 IconLocation 拼装、
save_launch_icon 的落盘往返（临时目录内，不触碰主线 data/）。
"""

from __future__ import annotations

import base64
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve()
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _HERE.parents[1] / "src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import config, routes  # noqa: E402
from server.dtree_core import TreeError  # noqa: E402


def make_ico(sizes=(16, 32), payload: bytes = b"\x89PNG\r\n\x1a\nFAKE" + b"IEND\xaeB`\x82") -> bytes:
    """构造一个结构合法的 PNG-in-ICO（帧数据为带 PNG 头尾的假数据）。"""
    count = len(sizes)
    offset = 6 + 16 * count
    total = offset + count * len(payload)
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, count)
    for size in sizes:
        out += struct.pack("<BBBBHHII", 0 if size == 256 else size, 0, 0, 0, 1, 32,
                           len(payload), offset)
        offset += len(payload)
    for _ in range(count):
        out += payload
    assert len(out) == total
    return bytes(out)


class ValidateIcoTests(unittest.TestCase):
    """validate_ico：只认结构完整的 PNG-in-ICO。"""

    def test_valid_ico_passes(self):
        routes.validate_ico(make_ico())   # 不抛即通过

    def test_valid_256_encoding(self):
        routes.validate_ico(make_ico(sizes=(256,)))   # 256 编码为 0 也要通过

    def test_short_header_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.validate_ico(b"\x00\x00\x01")
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_wrong_type_rejected(self):
        bad = make_ico()
        bad = b"\x00\x00\x02\x00" + bad[4:]   # type=2（光标）
        with self.assertRaises(TreeError) as ctx:
            routes.validate_ico(bad)
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_zero_entries_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.validate_ico(struct.pack("<HHH", 0, 1, 0) + b"\x00" * 32)
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_bmp_frame_rejected(self):
        # 帧数据不是 PNG（无签名 / 无 IEND）→ 拒
        payload = b"\x89PNG\r\n\x1a\nFAKE" + b"XXXXXXXX"   # 有头无尾
        with self.assertRaises(TreeError) as ctx:
            routes.validate_ico(make_ico(payload=payload))
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_offset_out_of_range_rejected(self):
        good = bytearray(make_ico())
        good[6 + 12:6 + 16] = struct.pack("<I", 0xFFFFFF)   # 偏移越界
        with self.assertRaises(TreeError) as ctx:
            routes.validate_ico(bytes(good))
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_too_large_rejected(self):
        big = make_ico()
        with mock.patch.object(config, "MAX_ICON_BYTES", 8):
            with self.assertRaises(TreeError) as ctx:
                routes.validate_ico(big)
            self.assertEqual(ctx.exception.code, "iconTooLarge")


class LnkScriptTests(unittest.TestCase):
    """_lnk_script：IconLocation 只在给定时拼装（纯函数，不碰 I/O）。"""

    def test_without_icon(self):
        script = routes._lnk_script(Path("C:/t/a.lnk"), "C:/t/start.bat", "C:/t")
        self.assertIn("TargetPath", script)
        self.assertNotIn("IconLocation", script)
        self.assertIn("Save", script)

    def test_with_icon(self):
        script = routes._lnk_script(Path("C:/t/a.lnk"), "C:/t/start.bat", "C:/t",
                                    "C:/t/data/qm-launch.ico,0")
        self.assertIn("IconLocation", script)
        self.assertIn("qm-launch.ico,0", script)

    def test_no_double_backslash(self):
        # 回归锁：反斜杠路径不得被 repr 加倍成 \\\\（PowerShell 单引号里反斜杠是字面量）
        script = routes._lnk_script(Path(r"C:\t\a.lnk"), r"C:\t\start.bat", r"C:\t",
                                    r"C:\t\data\qm-launch.ico,0")
        self.assertNotIn("\\\\", script)
        self.assertIn("C:/t/start.bat", script)
        self.assertIn("C:/t/data/qm-launch.ico,0", script)

    def test_single_quote_escaped(self):
        script = routes._lnk_script(Path("C:/t/a.lnk"), "C:/t/start.bat", "C:/t", "")
        # _ps_quote 应把单引号翻倍；本例路径无单引号，确认产物不含裸露单引号缺陷
        self.assertTrue(script.count("'") % 2 == 0)


class SaveLaunchIconTests(unittest.TestCase):
    """save_launch_icon：校验 + 原子落盘往返。全程临时目录。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_icon_")
        self.addCleanup(self.tmp.cleanup)
        self.icon_file = Path(self.tmp.name) / "qm-launch.ico"
        patcher = mock.patch.object(config, "ICON_FILE", self.icon_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_roundtrip(self):
        ico = make_ico(sizes=(16, 32, 48, 256))
        result = routes.save_launch_icon({"data": base64.b64encode(ico).decode("ascii")})
        self.assertTrue(result["ok"])
        self.assertEqual(result["bytes"], len(ico))
        self.assertEqual(self.icon_file.read_bytes(), ico)

    def test_missing_data_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.save_launch_icon({})
        self.assertEqual(ctx.exception.code, "iconDataMissing")

    def test_bad_base64_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.save_launch_icon({"data": "!!not-base64@@"})
        self.assertEqual(ctx.exception.code, "iconInvalid")

    def test_invalid_structure_rejected_and_not_written(self):
        with self.assertRaises(TreeError) as ctx:
            routes.save_launch_icon({"data": base64.b64encode(b"garbage").decode("ascii")})
        self.assertEqual(ctx.exception.code, "iconInvalid")
        self.assertFalse(self.icon_file.exists())


if __name__ == "__main__":
    unittest.main()
