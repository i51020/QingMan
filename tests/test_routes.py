"""青蔓 QingMan · routes 单元测试（§P0-1 / §P0-2 T2）。

覆盖：参数校验、落盘安全边界的错误码透出、编辑态读写往返与拒写分支。
全部在临时目录内进行，不触碰主线 `data/`。
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _HERE.parents[1] / "src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import config, routes  # noqa: E402
from server.dtree_core import TreeError  # noqa: E402

SIMPLE_TREE = {"素材": {"原图": {}}, "说明.md": "内容\n"}


class GenerateGuardTests(unittest.TestCase):
    """§P0-1：服务端必须自己拦，不依赖前端。"""

    def test_tree_missing(self):
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"target": "D:/x/y"})
        self.assertEqual(ctx.exception.code, "treeMissing")

    def test_target_missing(self):
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": SIMPLE_TREE})
        self.assertEqual(ctx.exception.code, "targetMissing")

    def test_drive_root_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": SIMPLE_TREE, "target": str(Path.cwd().anchor)})
        self.assertEqual(ctx.exception.code, "targetTooShallow")

    def test_system_dir_rejected(self):
        blocked, _ = config.BLOCKED_SUBTREES[0]
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": SIMPLE_TREE, "target": str(blocked / "evil")})
        self.assertEqual(ctx.exception.code, "targetBlocked")

    def test_project_self_rejected(self):
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": SIMPLE_TREE,
                             "target": str(config.PROJECT_DIR_RESOLVED)})
        self.assertEqual(ctx.exception.code, "targetReserved")

    def test_oversize_rejected_before_write(self):
        target = Path(tempfile.mkdtemp(prefix="qm_routes_")) / "big"
        self.addCleanup(lambda: __import__("shutil").rmtree(target.parent, ignore_errors=True))
        tree = {f"d{i}": {} for i in range(config.MAX_NODES + 1)}
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": tree, "target": str(target)})
        self.assertEqual(ctx.exception.code, "tooManyNodes")
        self.assertFalse(target.exists())


class GenerateWriteTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_gen_")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "demo"

    def test_dry_run_no_write(self):
        result = routes.generate({"tree": SIMPLE_TREE, "target": str(self.base), "dryRun": True})
        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertFalse(self.base.exists())

    def test_real_write_and_root_folder(self):
        result = routes.generate({"tree": SIMPLE_TREE, "target": str(self.base),
                                  "root": "我的项目", "dryRun": False})
        self.assertTrue(result["ok"])
        self.assertEqual(result["target"], str(self.base / "我的项目"))
        self.assertTrue((self.base / "我的项目" / "素材" / "原图").is_dir())
        self.assertTrue((self.base / "我的项目" / "说明.md").is_file())

    def test_invalid_root_segment(self):
        with self.assertRaises(TreeError) as ctx:
            routes.generate({"tree": SIMPLE_TREE, "target": str(self.base), "root": "a/b"})
        self.assertEqual(ctx.exception.code, "segmentInvalid")


class EditorRoundTripTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_editor_")
        self.addCleanup(self.tmp.cleanup)
        self.editor = Path(self.tmp.name) / "data" / "editor.json"
        self._orig = config.EDITOR_FILE
        config.EDITOR_FILE = self.editor
        self.addCleanup(setattr, config, "EDITOR_FILE", self._orig)

    def _doc(self):
        return {"schemaVersion": 1, "root": {
            "type": "dir", "id": "d1", "name": "根", "children": [
                {"type": "file", "id": "f1", "name": "a.md", "content": "hi"},
            ]}}

    def test_load_missing_returns_none(self):
        self.assertIsNone(routes.load_editor()["doc"])

    def test_save_then_load(self):
        res = routes.save_editor({"doc": self._doc()})
        self.assertTrue(res["ok"])
        self.assertEqual(res["stats"], {"dirs": 0, "files": 1})
        loaded = routes.load_editor()["doc"]
        self.assertEqual(loaded["root"]["children"][0]["name"], "a.md")

    def test_saved_bytes_match_disk(self):
        res = routes.save_editor({"doc": self._doc()})
        self.assertEqual(res["bytes"], self.editor.stat().st_size,
                         "返回的 bytes 必须等于磁盘实际字节（换行不得漂移）")
        self.assertNotIn(b"\r", self.editor.read_bytes(), "editor.json 必须为 LF")

    def test_rejects_invalid_document(self):
        bad = {"root": {"type": "dir", "id": "d1", "name": "根", "children": [
            {"type": "file", "id": "dup", "name": "a", "content": ""},
            {"type": "file", "id": "dup", "name": "b", "content": ""},
        ]}}
        with self.assertRaises(TreeError) as ctx:
            routes.save_editor({"doc": bad})
        self.assertEqual(ctx.exception.code, "editorIdDuplicated")
        self.assertFalse(self.editor.exists(), "非法文档必须被拒写")

    def test_corrupt_document_not_silently_empty(self):
        self.editor.parent.mkdir(parents=True, exist_ok=True)
        self.editor.write_text("{不是合法 json", encoding="utf-8")
        with self.assertRaises(TreeError) as ctx:
            routes.load_editor()
        self.assertEqual(ctx.exception.code, "editorCorrupt")

    def test_note_field_tolerated_and_preserved(self):
        """V0.0.17：节点 note 字段可选 —— 有则原样保存，无则不报错。"""
        doc = {"root": {"type": "dir", "id": "d1", "name": "根", "note": "根说明", "children": [
            {"type": "file", "id": "f1", "name": "a.md", "content": "hi"},
        ]}}
        res = routes.save_editor({"doc": doc})
        self.assertTrue(res["ok"])
        loaded = routes.load_editor()["doc"]
        self.assertEqual(loaded["root"]["note"], "根说明")
        # 老文档（无 note）依旧可存
        res2 = routes.save_editor({"doc": self._doc()})
        self.assertTrue(res2["ok"])


class TemplateTests(unittest.TestCase):
    """V0.0.11 模板库接口。

    `templates/` **不在版本交付清单内**，预览副本里没有它 —— 因此测试一律自建
    临时目录，靠替换 `config.TEMPLATES_DIR` 隔离，不依赖主线真实模板。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_tpl_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.old = config.TEMPLATES_DIR
        config.TEMPLATES_DIR = self.tmp
        self.addCleanup(setattr, config, "TEMPLATES_DIR", self.old)

    def _write(self, name, body):
        p = self.tmp / name
        p.write_text(body, encoding="utf-8")
        return p

    def test_missing_dir_is_unavailable_not_error(self):
        """目录不存在 → available=False + 空列表（预览副本的常态，不得报错）。"""
        config.TEMPLATES_DIR = self.tmp / "不存在"
        res = routes.list_templates()
        self.assertFalse(res["available"])
        self.assertEqual(res["items"], [])

    def test_list_stats(self):
        self._write("a.json", json.dumps(
            {"name": "甲模板", "description": "d", "tree": {"素材": {"原图": {}}, "说明.md": "x"}},
            ensure_ascii=False))
        self._write("b.json", json.dumps(
            {"name": "乙模板", "description": "", "tree": {"日志": {}}}, ensure_ascii=False))
        res = routes.list_templates()
        self.assertTrue(res["available"])
        self.assertEqual(len(res["items"]), 2)
        first = res["items"][0]
        self.assertEqual(first["name"], "甲模板")
        self.assertEqual((first["dirs"], first["files"]), (2, 1))

    def test_corrupt_file_skipped_not_fatal(self):
        """单套损坏只跳过该套，不拖垮整个列表。"""
        self._write("bad.json", "{不是合法 json")
        self._write("ok.json", json.dumps({"name": "好", "tree": {"a": {}}}, ensure_ascii=False))
        res = routes.list_templates()
        self.assertEqual([i["name"] for i in res["items"]], ["好"])

    def test_non_json_suffix_ignored(self):
        self._write("readme.md", "不是模板")
        self.assertEqual(routes.list_templates()["items"], [])

    def test_load_returns_nested_tree(self):
        tree = {"素材": {"原图": {}}, "说明.md": "内容\n"}
        self._write("t.json", json.dumps({"name": "测试模板", "tree": tree}, ensure_ascii=False))
        res = routes.load_template("t.json")
        self.assertEqual(res["name"], "测试模板")
        self.assertEqual(res["tree"], tree)
        self.assertEqual(res["stats"], {"dirs": 2, "files": 1})

    def test_path_traversal_rejected(self):
        """文件名不含路径分隔符 → 穿越名在白名单处即被拒，读不到 templates/ 之外。"""
        for bad in ("../secret.json", "..%2fsecret.json", "sub/x.json", "../../etc/passwd"):
            with self.assertRaises(TreeError) as ctx:
                routes.load_template(bad)
            self.assertEqual(ctx.exception.code, "templateNotFound", bad)

    def test_bad_suffix_and_empty_rejected(self):
        for bad in ("", None, "x.txt", "x.json.bak"):
            with self.assertRaises(TreeError) as ctx:
                routes.load_template(bad)
            self.assertEqual(ctx.exception.code, "templateNotFound", repr(bad))

    def test_load_corrupt_is_bad_json(self):
        self._write("bad.json", "{不是合法 json")
        with self.assertRaises(TreeError) as ctx:
            routes.load_template("bad.json")
        self.assertEqual(ctx.exception.code, "templateBadJson")

    def test_load_missing_key_is_bad_json(self):
        self._write("notree.json", json.dumps({"name": "缺 tree"}, ensure_ascii=False))
        with self.assertRaises(TreeError) as ctx:
            routes.load_template("notree.json")
        self.assertEqual(ctx.exception.code, "templateBadJson")

    # ---------- V0.0.13 另存为模板 ----------

    def test_save_roundtrip_includes_schema_version(self):
        """写入必带 schemaVersion，且落盘后能被正常读回（§P2 第 7 项）。"""
        tree = {"素材": {"原图": {}}, "说明.md": "内容\n"}
        res = routes.save_template({"name": "我的模板", "tree": tree})
        self.assertTrue(res["ok"])
        self.assertEqual(res["file"], "我的模板.json")
        self.assertEqual(res["stats"], {"dirs": 2, "files": 1})
        raw = (self.tmp / "我的模板.json").read_bytes()
        self.assertNotIn(b"\r", raw)          # §编码基线：落盘一律 LF
        doc = json.loads(raw.decode("utf-8"))
        self.assertEqual(doc["schemaVersion"], config.TEMPLATE_SCHEMA_VERSION)
        self.assertEqual(doc["name"], "我的模板")
        self.assertEqual(doc["tree"], tree)
        self.assertEqual(routes.load_template("我的模板.json")["tree"], tree)

    def test_save_strips_redundant_json_suffix(self):
        """用户顺手带上 .json 时不得叠成 `甲.json.json`。"""
        routes.save_template({"name": "甲.json", "tree": {"a": {}}})
        self.assertTrue((self.tmp / "甲.json").is_file())
        self.assertFalse((self.tmp / "甲.json.json").exists())

    def test_save_refuses_overwrite(self):
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        with self.assertRaises(TreeError) as ctx:
            routes.save_template({"name": "甲", "tree": {"b": {}}})
        self.assertEqual(ctx.exception.code, "templateExists")
        # 原文件必须原样保留：拒写不是「先覆盖再报错」
        doc = json.loads((self.tmp / "甲.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["tree"], {"a": {}})

    def test_save_rejects_bad_names(self):
        for bad in ("", "   ", "a/b", "../x", "x.txt", None, 123):
            with self.assertRaises(TreeError) as ctx:
                routes.save_template({"name": bad, "tree": {"a": {}}})
            self.assertIn(ctx.exception.code,
                          ("templateNameEmpty", "templateNameInvalid"), repr(bad))
        self.assertEqual(list(self.tmp.glob("*.json")), [])

    def test_save_rejects_too_long_name(self):
        long_name = "甲" * (config.TEMPLATE_NAME_MAX + 1)
        with self.assertRaises(TreeError) as ctx:
            routes.save_template({"name": long_name, "tree": {"a": {}}})
        self.assertEqual(ctx.exception.code, "templateNameTooLong")

    def test_save_rejects_bad_tree(self):
        for bad in (None, [], "x"):
            with self.assertRaises(TreeError) as ctx:
                routes.save_template({"name": "甲", "tree": bad})
            self.assertEqual(ctx.exception.code, "templateTreeMissing", repr(bad))

    def test_save_rejects_oversize_tree(self):
        old = config.MAX_NODES
        config.MAX_NODES = 1
        self.addCleanup(setattr, config, "MAX_NODES", old)
        with self.assertRaises(TreeError) as ctx:
            routes.save_template({"name": "甲", "tree": {"a": {}, "b": {}}})
        self.assertEqual(ctx.exception.code, "templateTooManyNodes")
        self.assertFalse((self.tmp / "甲.json").exists())


class OsLocaleTests(unittest.TestCase):
    """V0.0.14「跟随系统」= 真 OS 语言，经 /api/env.js 同步注入前端。"""

    BCP47 = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")

    def test_os_locale_is_string_or_empty(self):
        value = routes.os_locale()
        self.assertIsInstance(value, str)
        if value:
            self.assertTrue(self.BCP47.match(value), value)

    def test_env_script_shape(self):
        """产物必须是**可解析的 JS 赋值**，且值恒为 JSON 字符串字面量。"""
        script = routes.env_script()
        m = re.match(r'^window\.__QM_OS_LOCALE__ = (".*");\n$', script)
        self.assertIsNotNone(script and m, repr(script))
        self.assertIsInstance(json.loads(m.group(1)), str)
        self.assertEqual(json.loads(m.group(1)), routes.os_locale())
        self.assertTrue(script.isascii(), "注入脚本必须是纯 ASCII")

    def test_env_script_safe_when_locale_unavailable(self):
        """取不到 OS 语言时返回空串，而不是把异常或未定义拼进脚本。"""
        old = routes.os_locale
        routes.os_locale = lambda: ""
        self.addCleanup(setattr, routes, "os_locale", old)
        self.assertEqual(routes.env_script(), 'window.__QM_OS_LOCALE__ = "";\n')


class HealthTests(unittest.TestCase):

    def test_health_shape(self):
        info = routes.health()
        self.assertTrue(info["ok"])
        self.assertEqual(info["app"], config.APP_NAME_EN)
        self.assertIn("version", info)
        json.dumps(info)  # 必须可序列化


if __name__ == "__main__":
    unittest.main()
