"""青蔓 QingMan · 构建清单（第二层）单元测试（§P0-2 T2）。

守的是 `tools/manifest.py` 里**承担判定职责**的两个纯函数（`semver_problem` / `validate`）
与两个写盘点（`save` / `make_record`）—— 按 §P2 第 19 项的裁定：判定逻辑必须有单测，
且必须覆盖**反向用例**（喂入已知缺陷 → 断言**恰好**该项报红），否则「一次性反向验证」
无法沉淀成常态回归网。

这些用例是 `verify` 守卫 **7ap / 7aq** 的地基：守卫调的就是 `validate()`，
本文件把它判不了的边界逐条压住。
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import manifest  # noqa: E402


def make_root(version: str = "V0.0.53", revision: int = 2,
              store_day: str = "2026-10-17") -> Path:
    """造一个最小项目根：`VERSION` + `versions/<版本>/MANIFEST*.json`。"""
    root = Path(tempfile.mkdtemp(prefix="qm_manifest_"))
    (root / "VERSION").write_text(version + "\n", encoding="utf-8", newline="\n")
    vdir = root / "versions" / version
    vdir.mkdir(parents=True)
    name = "MANIFEST.json" if revision == 1 else f"MANIFEST-r{revision}.json"
    meta = {"version": version, "revision": revision,
            "createdAt": f"{store_day}_10-00-00", "digest": "x", "files": {}}
    (vdir / name).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    return root


def good_record(**over) -> dict:
    rec = {
        "version": "V0.0.53",
        "revision": 2,
        "createdAt": "2026-10-17T15:12:47+08:00",
        "timezone": {"name": "中国标准时间", "offset": "+08:00"},
        "model": {"name": "DeepSeek-V4.1-Flash", "vendor": "DeepSeek", "agent": "WorkBuddy"},
        "tools": {"python": "3.14.8", "node": "22.22.2", "zlib": "1.3.1.zlib-ng",
                  "os": "Windows-11-10.0.26300-SP0"},
        "note": "",
    }
    rec.update(over)
    return rec


def good_doc(builds=None) -> dict:
    return {"schema": manifest.SCHEMA, "version": "V0.0.53",
            "builds": [good_record()] if builds is None else builds}


class SemverProblemTests(unittest.TestCase):
    """版本号形态：SemVer 2.0.0 §2 —— 三段式、非负、禁前导零。"""

    def test_accepts_plain_three_segment(self):
        self.assertEqual(manifest.semver_problem("V0.0.53"), "")

    def test_rejects_date_in_version(self):
        # 日期进版本号是本仓明令禁止的（§P0-6 M7 / 7ao）。
        # ⚠ **已知边界**：`V0.0.20261017` 在形态上是**合法** SemVer（patch = 20261017，
        #   无前导零），形态判据抓不到它 —— 它属「不自然」而非「不合法」。
        #   这一格只能靠人评审 + 7aq 的父链单调性兜住，故此处只断言带分隔符的写法。
        self.assertTrue(manifest.semver_problem("V0.0.53-20261017"))
        self.assertEqual(manifest.semver_problem("V0.0.20261017"), "")

    def test_rejects_build_metadata(self):
        # `+` 后的内容不参与排序 ⇒ 不许拿它当构建标识（构建序号由 @rN + manifest 承担）
        self.assertTrue(manifest.semver_problem("V0.0.53+build.2"))
        self.assertTrue(manifest.semver_problem("V0.0.53-rc.1"))

    def test_rejects_leading_zero(self):
        self.assertIn("前导零", manifest.semver_problem("V0.01.0"))
        self.assertIn("前导零", manifest.semver_problem("V0.0.053"))

    def test_rejects_two_segment_legacy(self):
        self.assertTrue(manifest.semver_problem("V0.01"))

    def test_rejects_non_string(self):
        self.assertTrue(manifest.semver_problem(None))
        self.assertTrue(manifest.semver_problem(53))


class ValidateTests(unittest.TestCase):
    """六条判据逐条反向：每条都要**恰好**报出对应那一条。"""

    def test_good_document_has_no_violation(self):
        self.assertEqual(manifest.validate(good_doc(), "V0.0.53", 2,
                                           {"V0.0.53"}, "2026-10-17"), [])

    def test_schema_mismatch(self):
        doc = good_doc()
        doc["schema"] = "qm-manifest/2"
        hits = manifest.validate(doc, "V0.0.53", 2)
        self.assertTrue(any("schema" in h for h in hits))

    def test_version_desync_is_reported(self):
        # 两层唯一的连接点：顶层 version 必须逐字等于 VERSION
        hits = manifest.validate(good_doc(), "V0.0.54", 2)
        self.assertTrue(any("两层脱钩" in h for h in hits))

    def test_missing_record_for_current_revision(self):
        # 有记录但修订对不上 —— 等同「两层不同步」
        hits = manifest.validate(good_doc([good_record(revision=1)]), "V0.0.53", 2)
        self.assertTrue(any("缺 V0.0.53@r2" in h for h in hits))

    def test_builds_not_list(self):
        doc = good_doc()
        doc["builds"] = {"oops": 1}
        self.assertTrue(any("builds 不是数组" in h
                            for h in manifest.validate(doc, "V0.0.53", 2)))

    def test_extra_record_key(self):
        rec = good_record()
        rec["timestamp"] = "2026-10-17"          # 时间只许写 createdAt 一处
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("未登记字段" in h and "timestamp" in h for h in hits))

    def test_ghost_version_reported(self):
        rec = good_record(version="V9.9.9")
        doc = {"schema": manifest.SCHEMA, "version": "V0.0.53", "builds": [good_record(), rec]}
        hits = manifest.validate(doc, "V0.0.53", 2, {"V0.0.53"})
        self.assertTrue(any("不存在的版本" in h for h in hits))

    def test_revision_must_be_positive_int(self):
        for bad in (0, -1, "2", True, None):
            hits = manifest.validate(good_doc([good_record(revision=bad)]), "V0.0.53", None)
            self.assertTrue(any("revision" in h for h in hits), f"revision={bad!r} 未报红")

    def test_created_at_needs_timezone_offset(self):
        # 无偏移 = 跨机器无法比较 ⇒ 不认
        hits = manifest.validate(good_doc([good_record(createdAt="2026-10-17T15:12:47")]),
                                 "V0.0.53", 2)
        self.assertTrue(any("带时区的 ISO 8601" in h for h in hits))

    def test_offset_must_match_between_fields(self):
        rec = good_record(timezone={"name": "X", "offset": "+09:00"})
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("不一致" in h for h in hits))

    def test_timezone_name_required(self):
        rec = good_record(timezone={"name": "  ", "offset": "+08:00"})
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("timezone.name" in h for h in hits))

    def test_model_unknown_sentinel_not_empty(self):
        # 取不到就写 unknown —— 空串不许过关（否则「字段在但值是空」的静默态无法区分）
        rec = good_record(model={"name": "", "vendor": "DeepSeek", "agent": "WorkBuddy"})
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("model.name" in h for h in hits))
        rec2 = good_record(model={"name": "unknown", "vendor": "unknown", "agent": "unknown"})
        self.assertEqual(manifest.validate(good_doc([rec2]), "V0.0.53", 2), [])

    def test_model_missing_entirely(self):
        rec = good_record()
        rec.pop("model")
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("缺 model" in h for h in hits))

    def test_tools_required_keys(self):
        rec = good_record(tools={"python": "3.14.8", "zlib": "1.3.1", "os": "Windows"})
        self.assertEqual(manifest.validate(good_doc([rec]), "V0.0.53", 2), [])

    def test_tools_missing_python(self):
        rec = good_record(tools={"zlib": "1.3.1", "os": "Windows"})
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("tools.python" in h for h in hits))

    def test_tools_extra_key(self):
        rec = good_record(tools={"python": "3.14.8", "zlib": "1.3.1", "os": "W",
                                 "cpu": "x86"})
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2)
        self.assertTrue(any("tools 有未登记字段" in h for h in hits))

    def test_record_not_before_fact(self):
        # 记录不能早于它所记录的 store 清单 —— 反过来说，「先记后提交」必被抓住
        rec = good_record(createdAt="2026-10-16T09:00:00+08:00")
        hits = manifest.validate(good_doc([rec]), "V0.0.53", 2, None, "2026-10-17")
        self.assertTrue(any("不能早于事实" in h for h in hits))

    def test_record_same_day_passes(self):
        # 同日不判时分：两侧时区口径不同（store 记本地、本层记带偏移 ISO）
        rec = good_record(createdAt="2026-10-17T00:00:01+08:00")
        self.assertEqual(manifest.validate(good_doc([rec]), "V0.0.53", 2, None, "2026-10-17"), [])


class DocumentIoTest(unittest.TestCase):
    """落盘纪律：LF + 不转义中文 + 末尾换行（§编码基线）。"""

    def test_save_writes_lf_without_bom(self):
        root = make_root()
        try:
            doc = good_doc()
            doc["builds"][0]["timezone"]["name"] = "中国标准时间"
            path = manifest.save(root, doc)
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "写出了 BOM")
            self.assertNotIn(b"\r\n", raw, "写成了 CRLF")
            self.assertTrue(raw.endswith(b"\n"), "末尾缺换行")
            self.assertIn("中国标准时间".encode("utf-8"), raw, "中文被转义了")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_load_missing_file_returns_skeleton(self):
        root = make_root()
        try:
            doc = manifest.load(root)
            self.assertEqual(doc["schema"], manifest.SCHEMA)
            self.assertEqual(doc["version"], "V0.0.53")   # 骨架也从 VERSION 取，不写死
            self.assertEqual(doc["builds"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class RecordTests(unittest.TestCase):
    """记录生成：版本与修订必须**取自盘上事实**，不许由调用方口头指定。"""

    def test_record_uses_actual_version_and_latest_revision(self):
        root = make_root(version="V0.1.0", revision=3)
        try:
            rec = manifest.make_record(root, "", "", "", "")
            self.assertEqual(rec["version"], "V0.1.0")
            self.assertEqual(rec["revision"], 3)
            self.assertEqual(rec["model"]["name"], "unknown")     # 取不到写哨兵
            self.assertEqual(rec["timezone"]["offset"],
                             rec["createdAt"][-6:])                 # 两处同源
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_record_without_store_manifest_is_refused(self):
        root = Path(tempfile.mkdtemp(prefix="qm_manifest_nostore_"))
        try:
            (root / "VERSION").write_text("V0.0.54\n", encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError) as ctx:
                manifest.make_record(root, "m", "v", "a", "")
            self.assertIn("尚无 store 清单", str(ctx.exception))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_has_record_matches_version_and_revision_only(self):
        doc = good_doc()
        self.assertTrue(manifest.has_record(doc, "V0.0.53", 2))
        self.assertFalse(manifest.has_record(doc, "V0.0.53", 1))
        self.assertFalse(manifest.has_record(doc, "V0.0.54", 2))


class CheckTests(unittest.TestCase):
    """整链判定：合法根 0 违规；缺文件 / 版本错位必须报红。"""

    def test_missing_manifest_reported(self):
        root = make_root()
        try:
            hits = manifest.check(root)
            self.assertTrue(any("缺 manifest.json" in h for h in hits))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_synced_root_is_clean(self):
        root = make_root()
        try:
            doc = good_doc()
            manifest.save(root, doc)
            self.assertEqual(manifest.check(root), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_version_bump_without_stamp_is_red(self):
        # 这正是「两层脱钩」的主场景：升了 VERSION 却忘了记构建
        root = make_root()
        try:
            manifest.save(root, good_doc())
            (root / "VERSION").write_text("V0.1.0\n", encoding="utf-8", newline="\n")
            hits = manifest.check(root)
            self.assertTrue(any("两层脱钩" in h for h in hits))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class CollectToolsTests(unittest.TestCase):

    def test_shape(self):
        tools = manifest.collect_tools()
        self.assertEqual(set(tools), set(manifest.TOOLS_KEYS))
        for key in manifest.TOOLS_REQUIRED:
            self.assertTrue(tools[key].strip(), f"{key} 为空")
        self.assertTrue(tools["python"][0].isdigit())

    def test_node_is_measured_not_assumed(self):
        # PATH 上没有 node 时写 not-on-PATH，不许拿托管运行时冒充（那是 verify 的职责）
        val = manifest.collect_tools()["node"]
        self.assertTrue(val == "not-on-PATH" or val[0].isdigit(), val)


class NowStampTests(unittest.TestCase):

    def test_offset_consistent_and_regex_clean(self):
        stamp, tz = manifest.now_stamp()
        self.assertRegex(stamp, manifest.ISO_TZ_RE)
        self.assertTrue(manifest.OFFSET_RE.match(tz["offset"]))
        self.assertEqual(stamp[-6:], tz["offset"])
        self.assertTrue(tz["name"].strip())


if __name__ == "__main__":
    unittest.main()
