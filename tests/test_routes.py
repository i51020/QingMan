"""青蔓 QingMan · routes 单元测试（§P0-1 / §P0-2 T2）。

覆盖：参数校验、落盘安全边界的错误码透出、编辑态读写往返与拒写分支。
全部在临时目录内进行，不触碰主线 `data/`。
"""

from __future__ import annotations

import json
import io
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve()
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _HERE.parents[1] / "src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import app, config, routes  # noqa: E402
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
        # V0.0.26：保存会轮转备份到 EDITOR_BACKUP_DIR —— 必须一并隔离，
        # 否则测试会往**主线真实** data/.bak/ 里写文件（污染仓库）
        self._orig_bak = config.EDITOR_BACKUP_DIR
        config.EDITOR_BACKUP_DIR = Path(self.tmp.name) / "data" / ".bak"
        self.addCleanup(setattr, config, "EDITOR_BACKUP_DIR", self._orig_bak)

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

    def test_bad_encoding_raises_not_crashes(self):
        """A-P2-1：editor.json 为**非法 UTF-8**（用户用别的编码编辑过）时，须抛
        TreeError(editorReadFailed) 优雅报错 —— **不得**漏 UnicodeDecodeError 冒泡裸崩。"""
        self.editor.parent.mkdir(parents=True, exist_ok=True)
        self.editor.write_bytes('{"root": {"name": "测试"}}'.encode("gbk"))
        with self.assertRaises(TreeError) as ctx:
            routes.load_editor()
        self.assertEqual(ctx.exception.code, "editorReadFailed")

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


class EditorBackupTests(unittest.TestCase):
    """V0.0.26：编辑态**轮转备份**（保存前把上一版复制进 `data/.bak/`，保留最近 N 份）。

    `save_editor` 是原子替换（`os.replace`）—— 替换即覆盖上一版，而 `load_editor`
    的损坏保护挡不住「合法但错误」的覆盖。本类锁死备份的四件事：
    ① 只在**有上一版**时才备；② 备的是**上一版**内容（不是新版）；③ 上限裁掉最旧的；
    ④ **备份失败不阻断保存**。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_editorbak_")
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        self.editor = self.data / "editor.json"
        self.bak = self.data / ".bak"
        self._of = config.EDITOR_FILE
        self._ob = config.EDITOR_BACKUP_DIR
        self._ok = config.EDITOR_BACKUP_KEEP
        config.EDITOR_FILE = self.editor
        config.EDITOR_BACKUP_DIR = self.bak
        config.EDITOR_BACKUP_KEEP = 5
        self.addCleanup(setattr, config, "EDITOR_FILE", self._of)
        self.addCleanup(setattr, config, "EDITOR_BACKUP_DIR", self._ob)
        self.addCleanup(setattr, config, "EDITOR_BACKUP_KEEP", self._ok)

    def _doc(self, name):
        return {"schemaVersion": 1, "root": {
            "type": "dir", "id": "d1", "name": name, "children": [
                {"type": "file", "id": "f1", "name": "a.md", "content": "hi"},
            ]}}

    def _root_name(self, path):
        return json.loads(path.read_text(encoding="utf-8"))["root"]["name"]

    def _bak_files(self):
        return sorted(self.bak.glob("editor-*.json"))

    # ---------- 基本语义 ----------

    def test_first_save_creates_no_backup(self):
        res = routes.save_editor({"doc": self._doc("根1")})
        self.assertTrue(res["ok"])
        self.assertIn("backup", res, "响应必须带 backup 字段（契约 schema.json）")
        self.assertIsNone(res["backup"]["file"], "此前无文档，不应产生备份")
        self.assertFalse(self.bak.exists(), "无上一版时不应建 .bak 目录")

    def test_backup_holds_previous_version_not_new(self):
        routes.save_editor({"doc": self._doc("第一版")})
        res = routes.save_editor({"doc": self._doc("第二版")})
        self.assertTrue(res["backup"]["ok"])
        files = self._bak_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(self._root_name(files[0]), "第一版",
                         "备份必须是**上一版**（顺序颠倒就备成了新版）")
        self.assertEqual(self._root_name(self.editor), "第二版")

    def test_backup_is_byte_exact_copy(self):
        routes.save_editor({"doc": self._doc("v1")})
        before = self.editor.read_bytes()
        routes.save_editor({"doc": self._doc("v2")})
        self.assertEqual(self._bak_files()[0].read_bytes(), before,
                         "备份必须是上一版的**逐字节**副本")

    def test_rejected_save_leaves_no_backup(self):
        """备份发生在**校验 + 体积检查之后** —— 被拒的保存不得留下备份。"""
        routes.save_editor({"doc": self._doc("v1")})
        bad = {"root": {"type": "dir", "id": "d1", "name": "根", "children": [
            {"type": "file", "id": "dup", "name": "a", "content": ""},
            {"type": "file", "id": "dup", "name": "b", "content": ""},
        ]}}
        with self.assertRaises(TreeError):
            routes.save_editor({"doc": bad})
        self.assertEqual(self._bak_files(), [], "非法文档被拒时不应产生备份")

    # ---------- 轮转上限 ----------

    def test_keep_limit_prunes_oldest(self):
        config.EDITOR_BACKUP_KEEP = 3
        for i in range(1, 7):
            routes.save_editor({"doc": self._doc("根%d" % i)})
        files = self._bak_files()
        self.assertEqual(len(files), 3, "保留份数必须被裁到上限")
        self.assertEqual([self._root_name(p) for p in files], ["根3", "根4", "根5"],
                         "留下的必须是**最近**三版；裁错方向会留下最旧的")

    def test_keep_one(self):
        config.EDITOR_BACKUP_KEEP = 1
        for i in range(1, 5):
            routes.save_editor({"doc": self._doc("根%d" % i)})
        files = self._bak_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(self._root_name(files[0]), "根3")

    def test_pruned_backups_go_to_trash_not_deleted(self):
        """超限旧备份必须**移入** `.bak/.trash/`（软删除）。

        项目总原则「只复制不删除」是硬不变量 —— `verify.py` 7q 守卫禁止 `routes.py`
        出现 `unlink`/`remove`；轮转淘汰走 `templates/.trash/` 同一体例。
        """
        config.EDITOR_BACKUP_KEEP = 1
        for i in range(1, 5):
            routes.save_editor({"doc": self._doc("根%d" % i)})
        trashed = sorted((self.bak / ".trash").glob("*/editor-*.json"))
        self.assertEqual([self._root_name(p) for p in trashed], ["根1", "根2"],
                         "被淘汰的两版应完整保存在 .trash/ 下，而非被真删")
        self.assertEqual([self._root_name(p) for p in self._bak_files()], ["根3"])

    def test_prune_reports_moved_count(self):
        config.EDITOR_BACKUP_KEEP = 2
        for i in range(1, 5):
            routes.save_editor({"doc": self._doc("根%d" % i)})
        # 第 4 次保存时 .bak/ 将有 3 份 → 淘汰 1 份
        res = routes.save_editor({"doc": self._doc("根5")})
        self.assertGreaterEqual(res["backup"]["pruned"], 1)

    # ---------- 命名与排序（锁死本轮修掉的排序缺陷）----------

    def test_name_order_matches_chronology(self):
        """定宽名（含微秒）+ `_NNN` 后缀 ⇒ 名字序 == 时间序。

        反例（旧实现）：后缀用 `-NNN` 时 ASCII `-`(0x2D) < `.`(0x2E)，
        `editor-X-2.json` 会排到 `editor-X.json` **之前** —— 名字序反了，
        「保留最近 N 份」割掉的就是**最新**那份。
        """
        names = [
            "editor-20261010-233000-000001.json",
            "editor-20261010-233000-000002.json",
            "editor-20261010-233000-000002_002.json",
            "editor-20261010-233001-000000.json",
            "editor-20261010-233001-000000_002.json",
        ]
        self.assertEqual(sorted(names), names)

    def test_same_microsecond_collision_does_not_overwrite(self):
        self.data.mkdir(parents=True, exist_ok=True)
        self.editor.write_text("{}", encoding="utf-8")
        frozen = datetime(2026, 10, 10, 23, 30, 0)   # %f == 000000

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        with mock.patch.object(routes, "datetime", _FrozenDatetime):
            names = [routes._backup_editor(self.editor)["file"] for _ in range(3)]
        self.assertEqual(names, ["editor-20261010-233000-000000.json",
                                 "editor-20261010-233000-000000_002.json",
                                 "editor-20261010-233000-000000_003.json"])
        self.assertEqual(sorted(p.name for p in self._bak_files()), names,
                         "同微秒内多次备份：既不互相覆盖，名字序也仍是创建序")

    def test_prune_never_drops_the_newest(self):
        """回归：真实缺陷 —— 被裁掉的名字若被**后一次**备份复用，它会按名字序排到
        前面，于是「保留最近 N 份」把刚写的**最新**那份裁掉（实测：最新备份刚写就被删）。
        微秒时间戳使名字不再复用；本用例用递增微秒复现该序列并锁死这条不变量。
        """
        config.EDITOR_BACKUP_KEEP = 2
        counter = [0]

        class _SeqDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                counter[0] += 1
                return datetime(2026, 10, 10, 23, 30, 0, counter[0])

        self.data.mkdir(parents=True, exist_ok=True)
        self.editor.write_text("{}", encoding="utf-8")
        with mock.patch.object(routes, "datetime", _SeqDatetime):
            for _ in range(6):
                newest = routes._backup_editor(self.editor)["file"]
                files = [p.name for p in self._bak_files()]
                self.assertIn(newest, files, "刚写的备份不得被同一次裁剪删掉")
                self.assertLessEqual(len(files), 2, "裁剪必须收敛到上限")

    # ---------- 失败不阻断保存 ----------

    def test_backup_failure_does_not_block_save(self):
        blocker = self.data / "blocker"
        self.data.mkdir(parents=True, exist_ok=True)
        blocker.write_text("x", encoding="utf-8")
        routes.save_editor({"doc": self._doc("根1")})     # 先造出「上一版」
        config.EDITOR_BACKUP_DIR = blocker / "sub"        # 父路径是文件 → mkdir 必失败
        res = routes.save_editor({"doc": self._doc("根2")})
        self.assertTrue(res["ok"], "备份失败**不得**阻断保存（主契约是「存得下」）")
        self.assertFalse(res["backup"]["ok"])
        self.assertIn("reason", res["backup"], "失败须回报原因，不得静默")
        self.assertEqual(self._root_name(self.editor), "根2", "文档仍须落盘")

    def test_backup_keeps_editor_json_lf(self):
        routes.save_editor({"doc": self._doc("v1")})
        routes.save_editor({"doc": self._doc("v2")})
        self.assertNotIn(b"\r", self._bak_files()[0].read_bytes(), "备份须保持 LF")


class TemplateTests(unittest.TestCase):
    """V0.0.11 模板库接口。

    `templates/` **不在版本交付清单内**，预览副本里没有它 —— 因此测试一律自建
    临时目录，靠替换 `config.templates_dir`（V0.0.35 起的**唯一**解析入口）隔离，
    不依赖主线真实模板。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_tpl_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self._bind_dir(self.tmp)

    def _bind_dir(self, path):
        """把运行态模板目录钉到 `path`（生产由 `config.templates_dir()` 解析）。"""
        patcher = mock.patch.object(config, "templates_dir", lambda: path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name, body):
        p = self.tmp / name
        p.write_text(body, encoding="utf-8")
        return p

    def test_missing_dir_is_unavailable_not_error(self):
        """目录不存在 → available=False + 空列表（预览副本的常态，不得报错）。"""
        self._bind_dir(self.tmp / "不存在")
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

    # ---------- V0.0.21 模板覆盖写 ----------

    def test_save_overwrite_moves_old_to_trash_then_writes(self):
        """overwrite=true：旧模板**先入回收站**（可找回），原位为新内容，返回 overwritten=true。"""
        routes.save_template({"name": "甲", "tree": {"old": {}}})
        raw_before = (self.tmp / "甲.json").read_bytes()
        res = routes.save_template({"name": "甲", "tree": {"new": {}}, "overwrite": True})
        self.assertTrue(res["ok"])
        self.assertIs(res["overwritten"], True)
        # 新内容生效
        doc = json.loads((self.tmp / "甲.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["tree"], {"new": {}})
        # 旧内容逐字节入回收站（延续「只复制不删除」）
        trash = self.tmp / config.TEMPLATE_TRASH_DIRNAME
        found = list(trash.rglob("甲.json"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].read_bytes(), raw_before)

    def test_save_overwrite_false_or_absent_still_refuses(self):
        """overwrite 缺失或显式 false → 行为与旧版一致：拒写且原文件原样保留。"""
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        for payload in ({"name": "甲", "tree": {"b": {}}},
                        {"name": "甲", "tree": {"b": {}}, "overwrite": False}):
            with self.assertRaises(TreeError) as ctx:
                routes.save_template(payload)
            self.assertEqual(ctx.exception.code, "templateExists")
        self.assertEqual(
            json.loads((self.tmp / "甲.json").read_text(encoding="utf-8"))["tree"], {"a": {}})

    def test_save_overwrite_requires_strict_true(self):
        """真值字符串 / 数字（"true"、1、"yes"…）**不得**开启覆盖 —— 必须严格 `is True`。"""
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        for truthy in ("true", 1, "1", "yes", []):
            with self.assertRaises(TreeError) as ctx:
                routes.save_template({"name": "甲", "tree": {"b": {}}, "overwrite": truthy})
            self.assertEqual(ctx.exception.code, "templateExists", repr(truthy))
        self.assertEqual(
            json.loads((self.tmp / "甲.json").read_text(encoding="utf-8"))["tree"], {"a": {}})

    def test_save_overwrite_on_absent_name_just_creates(self):
        """overwrite=true 但目标不存在 → 正常新建，overwritten=false，且不产生回收站目录。"""
        res = routes.save_template({"name": "新甲", "tree": {"a": {}}, "overwrite": True})
        self.assertTrue(res["ok"])
        self.assertIs(res["overwritten"], False)
        self.assertTrue((self.tmp / "新甲.json").is_file())
        self.assertFalse((self.tmp / config.TEMPLATE_TRASH_DIRNAME).exists())

    # ---------- V0.0.24 模板失败回滚（P3-11） ----------

    def test_save_overwrite_write_failure_restores_old(self):
        """覆盖时写新文件失败 → 回滚：把旧模板从回收站移回原位，原位置不得凭空消失。"""
        routes.save_template({"name": "甲", "tree": {"old": {}}})
        original = (self.tmp / "甲.json").read_bytes()
        real_replace = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:          # 第 2 次 = tmp→path 提交新文件，模拟写失败
                raise OSError("simulated write failure")
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=flaky):
            with self.assertRaises(TreeError) as ctx:
                routes.save_template({"name": "甲", "tree": {"new": {}}, "overwrite": True})
        self.assertEqual(ctx.exception.code, "templateWriteFailed")
        # 回滚后：原位置仍是旧内容（未因覆盖失败而消失）
        self.assertTrue((self.tmp / "甲.json").is_file())
        self.assertEqual((self.tmp / "甲.json").read_bytes(), original)

    def test_rename_old_to_trash_failure_rolls_back(self):
        """重命名时旧文件入回收站失败 → 回滚：新文件也移入回收站，避免新旧并存。"""
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        real_replace = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:          # 第 2 次 = 旧文件→回收站，模拟失败
                raise OSError("simulated trash failure")
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=flaky):
            with self.assertRaises(TreeError) as ctx:
                routes.rename_template("甲.json", {"name": "乙"})
        self.assertEqual(ctx.exception.code, "templateRenameFailed")
        # 回滚后：原位置仍是旧文件；新名位置不存在（避免新旧两份并存）
        self.assertTrue((self.tmp / "甲.json").is_file())
        self.assertFalse((self.tmp / "乙.json").exists())

    # ---------- V0.0.20 模板 CRUD（删除 / 重命名） ----------

    def test_delete_is_soft_into_trash(self):
        """删除 = 软删除：文件移入 templates/.trash/<时间戳>/，原位置消失、内容逐字节保留。"""
        routes.save_template({"name": "待删", "tree": {"a": {}}})
        raw_before = (self.tmp / "待删.json").read_bytes()
        res = routes.delete_template("待删.json")
        self.assertTrue(res["ok"])
        self.assertFalse((self.tmp / "待删.json").exists())
        # 回收站里能找到，且内容一致（没被真删）
        trash = self.tmp / config.TEMPLATE_TRASH_DIRNAME
        found = list(trash.rglob("待删.json"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].read_bytes(), raw_before)
        # 列表不再包含它，且 .trash 不被 glob 扫到（不递归）
        self.assertEqual(routes.list_templates()["items"], [])

    def test_delete_missing_is_not_found(self):
        with self.assertRaises(TreeError) as ctx:
            routes.delete_template("不存在.json")
        self.assertEqual(ctx.exception.code, "templateNotFound")

    def test_delete_rejects_traversal(self):
        for bad in ("../x.json", "sub/x.json", "", None, "x.txt"):
            with self.assertRaises(TreeError) as ctx:
                routes.delete_template(bad)
            self.assertEqual(ctx.exception.code, "templateNotFound", repr(bad))

    def test_rename_moves_file_and_updates_inner_name(self):
        """重命名必须**同时**改文件名与文件内 name —— 否则列表显示名与 URL 脱节。"""
        routes.save_template({"name": "旧名", "tree": {"a": {"b": {}}}})
        res = routes.rename_template("旧名.json", {"name": "新名"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["file"], "新名.json")
        self.assertFalse((self.tmp / "旧名.json").exists())
        self.assertTrue((self.tmp / "新名.json").is_file())
        doc = json.loads((self.tmp / "新名.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["name"], "新名")            # 文件内 name 同步
        self.assertEqual(doc["tree"], {"a": {"b": {}}})  # 树内容不变
        # 列表显示新名
        self.assertEqual([i["name"] for i in routes.list_templates()["items"]], ["新名"])
        # 旧文件进了回收站（保底，不真删）
        self.assertEqual(len(list((self.tmp / config.TEMPLATE_TRASH_DIRNAME).rglob("旧名.json"))), 1)

    def test_rename_strips_json_suffix_and_keeps_lf(self):
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        routes.rename_template("甲.json", {"name": "乙.json"})
        self.assertTrue((self.tmp / "乙.json").is_file())
        self.assertNotIn(b"\r", (self.tmp / "乙.json").read_bytes())

    def test_rename_refuses_existing_target(self):
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        routes.save_template({"name": "乙", "tree": {"b": {}}})
        with self.assertRaises(TreeError) as ctx:
            routes.rename_template("甲.json", {"name": "乙"})
        self.assertEqual(ctx.exception.code, "templateExists")
        # 两边都原样保留，没有被破坏
        self.assertEqual(json.loads((self.tmp / "甲.json").read_text(encoding="utf-8"))["tree"], {"a": {}})
        self.assertEqual(json.loads((self.tmp / "乙.json").read_text(encoding="utf-8"))["tree"], {"b": {}})

    def test_rename_same_name_is_noop(self):
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        res = routes.rename_template("甲.json", {"name": "甲"})
        self.assertTrue(res["ok"])
        self.assertTrue(res.get("unchanged"))
        self.assertTrue((self.tmp / "甲.json").is_file())

    def test_rename_rejects_bad_names(self):
        routes.save_template({"name": "甲", "tree": {"a": {}}})
        for bad in ("", "   ", "a/b", "../x", "x.txt", None, 123):
            with self.assertRaises(TreeError) as ctx:
                routes.rename_template("甲.json", {"name": bad})
            self.assertIn(ctx.exception.code,
                          ("templateNameEmpty", "templateNameInvalid"), repr(bad))
        self.assertTrue((self.tmp / "甲.json").is_file())

    def test_rename_missing_is_not_found(self):
        with self.assertRaises(TreeError) as ctx:
            routes.rename_template("无.json", {"name": "x"})
        self.assertEqual(ctx.exception.code, "templateNotFound")
        self.assertFalse((self.tmp / "甲.json").exists())


class TemplatesDirRouteTests(unittest.TestCase):
    """V0.0.35 模板目录绑定（`GET/PUT /api/templates-dir`）。

    绑定目录来自 env / settings 两处**外部状态**，故测试须同时隔离两者：
    `QM_SETTINGS` 指向临时文件、清掉 `QM_TEMPLATES_DIR`，绝不碰真机配置。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_bind_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.bind = self.tmp / "我的模板"
        self.settings = self.tmp / "settings.json"
        env = mock.patch.dict(os.environ, {"QM_SETTINGS": str(self.settings)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("QM_TEMPLATES_DIR", None)

    @staticmethod
    def _same(a, b) -> bool:
        return os.path.normcase(str(a)) == os.path.normcase(str(b))

    def test_default_dir_is_valid_not_blocked(self):
        """未绑定时运行态目录＝内置 `templates/`，必须**可用** ——
        不许把「不许绑到内置层」误当成「不许使用内置层」。"""
        res = routes.get_templates_dir()
        self.assertTrue(res["ok"])
        self.assertEqual(res["source"], "default")
        self.assertTrue(self._same(res["dir"], config.DEFAULT_TEMPLATES_DIR))
        self.assertTrue(res["valid"])
        self.assertEqual(res["reason"], "")
        self.assertIn("settingsFiles", res)

    def test_default_dir_lists_normally(self):
        """默认目录下 `list_templates` 照常可用（回归：曾被判非法 → 恒 available=False）。"""
        res = routes.list_templates()
        self.assertTrue(res["available"])
        self.assertEqual(res["reason"], "")

    def test_put_persists_and_becomes_effective(self):
        res = routes.set_templates_dir({"dir": str(self.bind)})
        self.assertTrue(res["ok"])
        self.assertTrue(res["applied"])
        self.assertTrue(self._same(res["effectiveDir"], self.bind))
        raw = self.settings.read_bytes()
        self.assertNotIn(b"\r", raw, "settings 须保持 LF（§编码基线）")
        doc = json.loads(raw.decode("utf-8"))
        self.assertTrue(self._same(doc["templatesDir"], self.bind))
        self.assertEqual(doc["schemaVersion"], config.SETTINGS_SCHEMA_VERSION)
        # 不缓存：改完即刻生效，且来源转为 settings
        self.assertTrue(self._same(config.templates_dir(), self.bind))
        self.assertEqual(config.templates_dir_source(), "settings")

    def test_put_rejects_empty(self):
        for bad in ("", "   ", None, 123):
            with self.assertRaises(TreeError) as ctx:
                routes.set_templates_dir({"dir": bad})
            self.assertEqual(ctx.exception.code, "templateDirBlocked", repr(bad))
        self.assertFalse(self.settings.exists(), "拒绑不得留下 settings")

    def test_put_rejects_self_project_and_ancestors(self):
        for bad in (str(config.PROJECT_DIR), str(config.PROJECT_DIR.parent)):
            with self.assertRaises(TreeError) as ctx:
                routes.set_templates_dir({"dir": bad})
            self.assertEqual(ctx.exception.code, "templateDirBlocked", bad)
        self.assertFalse(self.settings.exists())

    def test_put_rejects_builtin_templates_dir(self):
        with self.assertRaises(TreeError) as ctx:
            routes.set_templates_dir({"dir": str(config.DEFAULT_TEMPLATES_DIR)})
        self.assertEqual(ctx.exception.code, "templateDirBlocked")

    def test_put_rejects_system_subtree(self):
        root, _label = config.BLOCKED_SUBTREES[0]
        with self.assertRaises(TreeError) as ctx:
            routes.set_templates_dir({"dir": str(root / "qingman-bind-probe")})
        self.assertEqual(ctx.exception.code, "templateDirBlocked")

    def test_put_rejects_blocked_root_itself(self):
        root, _label = config.BLOCKED_ROOTS[0]
        with self.assertRaises(TreeError) as ctx:
            routes.set_templates_dir({"dir": str(root)})
        self.assertEqual(ctx.exception.code, "templateDirBlocked")

    def test_put_rejects_not_writable(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("x", encoding="utf-8")     # 文件占位 → 同名目录建不出来
        with self.assertRaises(TreeError) as ctx:
            routes.set_templates_dir({"dir": str(blocker / "sub")})
        self.assertEqual(ctx.exception.code, "templateDirNotWritable")
        self.assertFalse(self.settings.exists())

    def test_env_overrides_settings(self):
        """env 优先于 settings：PUT 照写盘，但 `applied=false` 如实回报。"""
        os.environ["QM_TEMPLATES_DIR"] = str(self.tmp / "envdir")
        res = routes.set_templates_dir({"dir": str(self.bind)})
        self.assertFalse(res["applied"])
        self.assertEqual(res["source"], "env")
        self.assertTrue(self._same(res["effectiveDir"], self.tmp / "envdir"))

    def test_illegal_binding_makes_list_unavailable(self):
        """env 强设非法目录（指向青蔓自身）→ 列表 available=False，且不去 glob 该位置。"""
        os.environ["QM_TEMPLATES_DIR"] = str(config.PROJECT_DIR)
        res = routes.list_templates()
        self.assertFalse(res["available"])
        self.assertEqual(res["items"], [])
        self.assertTrue(res["reason"])

    def test_write_paths_also_enforce_dir_guard(self):
        """env 可绕过 UI 直指受保护目录 —— 写路径必须**自己**再校验一次。"""
        os.environ["QM_TEMPLATES_DIR"] = str(config.PROJECT_DIR)
        with self.assertRaises(TreeError) as ctx:
            routes.save_template({"name": "甲", "tree": {"a": {}}})
        self.assertEqual(ctx.exception.code, "templateDirBlocked")


class TemplatesDirPickTests(unittest.TestCase):
    """V0.0.38 · 6E 原生目录选择框（`POST /api/templates-dir/pick`）。

    真弹窗会**阻塞到有人去点它**，自动化里绝不可触发 —— 故全部给 `_ask_directory`
    打桩，只测本层逻辑：env 关断 / 不可用降级 / 取消 / 选中四条分支 + 「选择不落盘」。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_pick_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = mock.patch.dict(os.environ, {"QM_SETTINGS": str(self.tmp / "settings.json")})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("QM_TEMPLATES_DIR", None)
        os.environ.pop(routes.NO_GUI_PICK_ENV, None)
        self.addCleanup(lambda: os.environ.pop(routes.NO_GUI_PICK_ENV, None))

    def test_disabled_by_env(self):
        os.environ[routes.NO_GUI_PICK_ENV] = "1"
        res = routes.pick_templates_dir()
        self.assertTrue(res["ok"])
        self.assertFalse(res["available"])
        self.assertEqual(res["reason"], "disabled")
        self.assertEqual(res["dir"], "")

    def test_unavailable_degrades(self):
        with mock.patch.object(routes, "_ask_directory",
                               side_effect=routes._PickUnavailable("no display")):
            res = routes.pick_templates_dir()
        self.assertTrue(res["ok"])
        self.assertFalse(res["available"])
        self.assertEqual(res["reason"], "unavailable")
        self.assertIn("no display", res["message"])
        self.assertEqual(res["dir"], "")

    def test_returns_chosen_dir(self):
        chosen = str(self.tmp / "模板库")
        with mock.patch.object(routes, "_ask_directory", return_value=chosen):
            res = routes.pick_templates_dir()
        self.assertTrue(res["available"])
        self.assertFalse(res["cancelled"])
        self.assertEqual(res["dir"], chosen)

    def test_cancelled_returns_empty(self):
        with mock.patch.object(routes, "_ask_directory", return_value=None):
            res = routes.pick_templates_dir()
        self.assertTrue(res["available"])
        self.assertTrue(res["cancelled"])
        self.assertEqual(res["dir"], "")

    def test_pick_does_not_touch_settings(self):
        """「选择」不得落盘 —— 只回报路径，绑定留给 `PUT /api/templates-dir`。"""
        with mock.patch.object(routes, "_ask_directory", return_value=str(self.tmp / "x")):
            routes.pick_templates_dir()
        self.assertFalse((self.tmp / "settings.json").exists())

    def test_list_items_carry_mtime_and_size(self):
        """轮询变化判据依赖的两个字段必须在每项上（V0.0.38 · 6E）。"""
        res = routes.list_templates()
        self.assertTrue(res["available"])
        self.assertTrue(res["items"], "默认内置目录应至少有一套模板")
        for item in res["items"]:
            self.assertIsInstance(item["mtime"], float)
            self.assertIsInstance(item["size"], int)
            self.assertGreaterEqual(item["size"], 0)


class TemplateExportTests(unittest.TestCase):
    """V0.0.38 · 6E 模板导出（`GET /api/templates-export/<name>`）。

    导出的语义是「盘上那份文件**原样**交回」—— 故断言**逐字节等于**盘上内容，
    这正是「导出 → 再导入」能成环的前提（若导出做了再序列化，两侧就会漂移）。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_export_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.dir = self.tmp / "lib"
        self.dir.mkdir()
        patcher = mock.patch.object(config, "templates_dir", lambda: self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name: str, text: str) -> str:
        (self.dir / name).write_text(text, encoding="utf-8", newline="\n")
        return text

    def test_json_export_is_byte_identical(self):
        text = '{\n  "name": "甲",\n  "tree": {"a": {}}\n}\n'
        self._write("甲.json", text)
        res = routes.export_template("甲.json")
        self.assertTrue(res["ok"])
        self.assertEqual(res["file"], "甲.json")
        self.assertEqual(res["source"], "json")
        self.assertEqual(res["text"], text)

    def test_md_export_is_byte_identical(self):
        text = "# 乙\n\n> 说明\n\n- 目录/\n"
        self._write("乙.md", text)
        res = routes.export_template("乙.md")
        self.assertEqual(res["source"], "md")
        self.assertEqual(res["text"], text)

    def test_export_rejects_path_traversal_and_bad_ext(self):
        for bad in ("../x.json", "a/b.json", "..\\x.json", "x.txt", ""):
            with self.assertRaises(TreeError) as ctx:
                routes.export_template(bad)
            self.assertEqual(ctx.exception.code, "templateNotFound", repr(bad))

    def test_export_missing_file(self):
        with self.assertRaises(TreeError) as ctx:
            routes.export_template("不存在.md")
        self.assertEqual(ctx.exception.code, "templateNotFound")


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


class LocaleListTests(unittest.TestCase):
    """V0.0.44 · 动态语言包：`/api/locales.js` 的枚举与注入脚本。

    设计要点（与 `OsLocaleTests` 同构）：清单必须**早于 module 脚本**同步注入，
    故产物是一段可解析的 JS 赋值而非异步接口。语言标签取自**文件名**（`LOCALE`
    与文件名一致由 verify 静态把关），`NAME` 只做**正则文本**读取 —— 服务端
    绝不 import 前端 ES Module。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_locales_")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        patcher = mock.patch.object(config, "LOCALES_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    # ---------- 真机目录 ----------

    def test_real_dir_lists_builtin_languages(self):
        """出厂目录须恰好枚举到 zh-CN / en-US，且名字是母语自描述名。"""
        with mock.patch.object(config, "LOCALES_DIR",
                               config.WEB_DIR / "locales"):
            got = routes.list_locales()
        by_code = {e["code"]: e["name"] for e in got}
        self.assertEqual(by_code.get("zh-CN"), "简体中文")
        self.assertEqual(by_code.get("en-US"), "English")
        # README.md 等非语言包文件不得混入
        self.assertEqual(set(by_code), {"zh-CN", "en-US"}, by_code)

    # ---------- 扫描与过滤 ----------

    def test_only_js_with_bcp47_name_is_taken(self):
        self._write("zh-CN.js", "export const LOCALE='zh-CN';\nexport const NAME='简体中文';\n")
        self._write("notes.txt", "xx")
        self._write("readme.md", "xx")
        self._write("x.js", "short name")        # 主语言 1 字母 → 不匹配
        self._write("bad name.js", "space")      # 含空格 → 不匹配
        self._write("..js", "dots")              # 空主标签 → 不匹配
        got = routes.list_locales()
        self.assertEqual([e["code"] for e in got], ["zh-CN"], got)

    def test_subtagged_tag_is_accepted(self):
        """带多级子标签的合法标签（zh-Hans-CN）应被接受。"""
        self._write("zh-Hans-CN.js", "export const NAME='简体中文（大陆）';\n")
        self.assertEqual([e["code"] for e in routes.list_locales()], ["zh-Hans-CN"])

    def test_sorted_by_filename(self):
        for tag in ("zh-CN", "en-US", "de-DE"):
            self._write(f"{tag}.js", f"export const NAME='{tag}';\n")
        self.assertEqual([e["code"] for e in routes.list_locales()],
                         ["de-DE", "en-US", "zh-CN"])

    def test_directory_that_looks_like_locale_is_skipped(self):
        """名字合法但是**目录**而非文件 → 跳过（只认文件）。"""
        (self.dir / "fr-FR.js").mkdir()
        self._write("en-US.js", "export const NAME='English';\n")
        self.assertEqual([e["code"] for e in routes.list_locales()], ["en-US"])

    # ---------- NAME 解析与降级 ----------

    def test_name_read_by_regex_without_executing_js(self):
        """名字从 `export const NAME = '…'` 里取；文件里夹带任意代码也不执行。"""
        self._write("fr-FR.js",
                    "throw new Error('never executed');\n"
                    "export const LOCALE = 'fr-FR';\n"
                    "export const NAME = \"Français\";\n")
        got = routes.list_locales()
        self.assertEqual(got, [{"code": "fr-FR", "name": "Français"}])

    def test_missing_name_falls_back_to_filename(self):
        """取不到 `NAME` 时回落文件名 —— 不让这门语言从清单里凭空消失。"""
        self._write("ja-JP.js", "export const LOCALE='ja-JP';\n")
        self.assertEqual(routes.list_locales(),
                         [{"code": "ja-JP", "name": "ja-JP"}])

    def test_undecodable_file_is_skipped(self):
        """非 UTF-8 字节 → 跳过该文件，不因单包损坏而拖垮整份清单。"""
        (self.dir / "ko-KR.js").write_bytes(b"export const NAME='\xff\xfe';\n")
        self._write("en-US.js", "export const NAME='English';\n")
        self.assertEqual([e["code"] for e in routes.list_locales()], ["en-US"])

    # ---------- 缺目录与注入脚本 ----------

    def test_missing_dir_returns_empty(self):
        with mock.patch.object(config, "LOCALES_DIR", self.dir / "nope"):
            self.assertEqual(routes.list_locales(), [])

    def test_script_shape_and_native_names_unescaped(self):
        """产物是可解析的 JS 赋值，且母语名**原样**（ensure_ascii=False）。"""
        self._write("zh-CN.js", "export const NAME='简体中文';\n")
        script = routes.locales_script()
        m = re.match(r'^window\.__QM_LOCALES__ = (.*);\n$', script)
        self.assertIsNotNone(m, repr(script))
        value = json.loads(m.group(1))
        self.assertEqual(value, [{"code": "zh-CN", "name": "简体中文"}])
        self.assertIn("简体中文", script, "母语名不得被转成 \\uXXXX")

    def test_script_empty_when_no_locales(self):
        with mock.patch.object(config, "LOCALES_DIR", self.dir / "nope"):
            self.assertEqual(routes.locales_script(), "window.__QM_LOCALES__ = [];\n")


class BackendDefenseBatchTests(unittest.TestCase):
    """src 审查第四档 · 后端防御批（V0.0.30 · A-P3-1~8）回归位。"""

    # ---------- A-P3-6 dryRun 严格布尔 ----------

    def test_dryrun_string_false_is_not_dry_run(self):
        """A-P3-6：字符串 `"false"` 不得被 `bool()` 当成 True 而误开演练。"""
        with tempfile.TemporaryDirectory(prefix="qm_dryrun_") as d:
            target = str(Path(d) / "out")
            r = routes.generate({"tree": SIMPLE_TREE, "target": target, "dryRun": "false"})
            self.assertFalse(r["dryRun"], "字符串 \"false\" 应判为非演练")
            self.assertTrue(Path(target).is_dir(), "非演练应真的落盘")

    def test_dryrun_true_writes_nothing(self):
        with tempfile.TemporaryDirectory(prefix="qm_dryrun_") as d:
            target = str(Path(d) / "out")
            r = routes.generate({"tree": SIMPLE_TREE, "target": target, "dryRun": True})
            self.assertTrue(r["dryRun"])
            self.assertFalse(Path(target).exists(), "dry_run 不得写盘")

    # ---------- A-P3-2 原子写唯一临时名 ----------

    def test_tmp_sibling_unique_same_dir(self):
        """A-P3-2：临时名两两不同，且与目标同目录（保 os.replace 同盘原子）。"""
        p = Path("D:/x/y/editor.json")
        a = routes._tmp_sibling(p)
        b = routes._tmp_sibling(p)
        self.assertNotEqual(a, b)
        self.assertEqual(a.parent, p.parent)
        self.assertTrue(a.name.startswith("editor.json."))
        self.assertTrue(a.name.endswith(".tmp"))

    # ---------- A-P3-3 模板回收站目录唯一化 ----------

    def test_template_trash_dir_unique_in_same_second(self):
        """A-P3-3：同一秒内二次调用必须拿到不同目录（否则会覆盖上次软删除的旧版）。"""
        with tempfile.TemporaryDirectory(prefix="qm_trash_") as d:
            with mock.patch.object(config, "templates_dir", lambda: Path(d)):
                first = routes._template_trash_dir()
                first.mkdir(parents=True)
                second = routes._template_trash_dir()
                self.assertNotEqual(first, second)
                self.assertEqual(second.parent, first.parent)

    # ---------- A-P3-4 真实桌面解析 ----------

    def test_desktop_dir_is_path(self):
        self.assertIsInstance(config.desktop_dir(), Path)

    # ---------- A-P3-1 subprocess 超时 → OSError ----------

    def test_write_lnk_timeout_becomes_oserror(self):
        """A-P3-1：PowerShell 超时必须转成 OSError，交上层降级，而非永久挂住线程。"""
        boom = routes.subprocess.TimeoutExpired("powershell", routes._PS_TIMEOUT_SEC)
        with mock.patch.object(routes.subprocess, "run", side_effect=boom):
            with tempfile.TemporaryDirectory(prefix="qm_lnk_") as d:
                with self.assertRaises(OSError):
                    routes._write_lnk(Path(d) / "x.lnk", "target", "workdir")

    # ---------- A-P3-7 chunked 请求体 ----------

    @staticmethod
    def _fake_handler(headers, body):
        # 桩对象挂上真实的 _read_body / _read_chunked_body（不启动服务即可驱动入口）
        h = type("H", (), {
            "_read_body": app.Handler._read_body,
            "_read_chunked_body": app.Handler._read_chunked_body,
        })()
        h.headers = headers
        h.rfile = io.BytesIO(body)
        return h

    def test_read_body_parses_chunked(self):
        """A-P3-7：走**真实入口** `_read_body`，带 chunked 头须正确拼接。

        旧实现只读 Content-Length → chunked 请求体被静默当空（返回 b""）。
        """
        h = self._fake_handler({"Transfer-Encoding": "chunked"},
                               b"5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n")
        self.assertEqual(app.Handler._read_body(h), b"hello world")

    def test_read_body_chunked_enforces_cap(self):
        """A-P3-7：分块读取期间也须受体积上限约束。"""
        over = config.MAX_BODY_BYTES + 1
        payload = b"a" * over
        raw = hex(over)[2:].encode() + b"\r\n" + payload + b"\r\n0\r\n\r\n"
        h = self._fake_handler({"Transfer-Encoding": "chunked"}, raw)
        with self.assertRaises(TreeError) as ctx:
            app.Handler._read_body(h)
        self.assertEqual(ctx.exception.code, "bodyTooLarge")


class HealthTests(unittest.TestCase):

    def test_health_shape(self):
        info = routes.health()
        self.assertTrue(info["ok"])
        self.assertEqual(info["app"], config.APP_NAME_EN)
        self.assertIn("version", info)
        json.dumps(info)  # 必须可序列化


class TemplateDualFormatTests(unittest.TestCase):
    """V0.0.36 · 6C：模板**双格式**（`.json` + `.md`）列表 / 读取 / 导入。

    隔离方式同 `TemplateTests`：自建临时目录 + `mock.patch.object(config,
    "templates_dir", …)`，不碰主线真实模板。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qm_tplfmt_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        patcher = mock.patch.object(config, "templates_dir", lambda: self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name, body):
        p = self.tmp / name
        p.write_text(body, encoding="utf-8", newline="\n")
        return p

    _MD = "# 我的模板\n> 一句描述\n- 素材/\n  - 原图/\n  - 说明.md\n"
    # ---- 列表 ----

    def test_list_includes_md_with_source(self):
        """列表同时扫 `*.json` 与 `*.md`，每项带 `source` 标注。"""
        self._write("a.json", json.dumps(
            {"name": "甲", "description": "", "tree": {"x": {}}}, ensure_ascii=False))
        self._write("b.md", self._MD)
        res = routes.list_templates()
        self.assertTrue(res["available"])
        by_file = {it["file"]: it for it in res["items"]}
        self.assertEqual(set(by_file), {"a.json", "b.md"})
        self.assertEqual(by_file["a.json"]["source"], "json")
        self.assertEqual(by_file["b.md"]["source"], "md")
        # md 项的名称来自其 `# 标题`，计数与 json 同一口径
        self.assertEqual(by_file["b.md"]["name"], "我的模板")
        self.assertEqual((by_file["b.md"]["dirs"], by_file["b.md"]["files"]), (2, 1))

    def test_corrupt_md_skipped_not_fatal(self):
        """坏 `.md` 只跳过该套，不影响其余（与坏 json 同体例）。"""
        self._write("ok.json", json.dumps({"name": "甲", "tree": {"x": {}}}, ensure_ascii=False))
        self._write("bad.md", "  - 缩进非法\n")   # 首行即带缩进的悬空项
        res = routes.list_templates()
        self.assertEqual([it["file"] for it in res["items"]], ["ok.json"])

    # ---- 读取 ----

    def test_load_md_dispatch(self):
        self._write("b.md", self._MD)
        res = routes.load_template("b.md")
        self.assertEqual(res["source"], "md")
        self.assertEqual(res["name"], "我的模板")
        self.assertEqual(res["description"], "一句描述")
        self.assertEqual(res["tree"], {"素材": {"原图": {}, "说明.md": ""}})
        self.assertEqual(res["stats"], {"dirs": 2, "files": 1})

    def test_load_json_still_reports_source_json(self):
        self._write("a.json", json.dumps(
            {"name": "甲", "tree": {"x": {}}}, ensure_ascii=False))
        res = routes.load_template("a.json")
        self.assertEqual(res["source"], "json")

    def test_load_json_without_tree_still_bad_json(self):
        """**回归位**：`.json` 缺 `tree` 仍是 `templateBadJson`（语义不得被双格式改造改变）。"""
        self._write("notree.json", json.dumps({"name": "甲"}, ensure_ascii=False))
        with self.assertRaises(TreeError) as ctx:
            routes.load_template("notree.json")
        self.assertEqual(ctx.exception.code, "templateBadJson")

    def test_load_unknown_ext_not_found(self):
        with self.assertRaises(TreeError) as ctx:
            routes.load_template("x.txt")
        self.assertEqual(ctx.exception.code, "templateNotFound")

    # ---- 导入 ----

    def test_import_md_normalizes_and_persists(self):
        """导入 `.md` → 归一 → **仍以 `.md` 落盘**，且列表可见。"""
        # 原始 md 有多余空行、缩进随手，导入后应被 render 规范化为确定性产物
        messy = "# 我的模板\n> 描述\n\n\n- 素材/\n  - 原图/\n\n- 说明.md\n"
        res = routes.import_template({"filename": "导入的.md", "content": messy})
        self.assertTrue(res["ok"])
        self.assertEqual(res["source"], "md")
        self.assertEqual(res["file"], "导入的.md")
        self.assertEqual(res["stats"], {"dirs": 2, "files": 1})
        self.assertFalse(res["overwritten"])
        # 落盘的是规范化后的 md（与 `render_md_template` 逐字节一致 → 导入/导出可成环）
        saved = (self.tmp / "导入的.md").read_text(encoding="utf-8")
        self.assertEqual(saved, "# 我的模板\n> 描述\n\n- 素材/\n  - 原图/\n- 说明.md\n")
        # 列表能看见它，且能再读回来
        self.assertIn("导入的.md", [it["file"] for it in routes.list_templates()["items"]])
        self.assertEqual(routes.load_template("导入的.md")["tree"],
                         {"素材": {"原图": {}}, "说明.md": ""})

    def test_import_json_persists_schema_version(self):
        res = routes.import_template({
            "filename": "t.json",
            "content": json.dumps({"name": "甲", "tree": {"x": {}}}, ensure_ascii=False),
        })
        self.assertEqual(res["source"], "json")
        doc = json.loads((self.tmp / "t.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["schemaVersion"], config.TEMPLATE_SCHEMA_VERSION)
        self.assertIn("updated", doc)

    def test_import_rejects_empty_content(self):
        for bad in ("", "   ", None, 123):
            with self.assertRaises(TreeError) as ctx:
                routes.import_template({"filename": "t.md", "content": bad})
            self.assertEqual(ctx.exception.code, "templateEmpty", repr(bad))

    def test_import_rejects_empty_tree(self):
        """内容可解析但**一个节点都没有** → `templateEmpty`（不落一个空模板）。"""
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({"filename": "t.md", "content": "# 空模板\n"})
        self.assertEqual(ctx.exception.code, "templateEmpty")

    def test_import_rejects_bad_markdown(self):
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({"filename": "t.md", "content": "- a/\n   - 跳级不可达/\n"})
        self.assertIn(ctx.exception.code, ("templateBadMarkdown",))

    def test_import_rejects_bad_json(self):
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({"filename": "t.json", "content": "{ not json"})
        self.assertEqual(ctx.exception.code, "templateBadJson")

    def test_import_validates_segments(self):
        """导入是质量闸门：非法段名（尾随点）拦下 —— 列表/读取路径不做此校验，导入做。"""
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({
                "filename": "t.json",
                "content": json.dumps({"name": "甲", "tree": {"bad.": {}}}, ensure_ascii=False),
            })
        self.assertEqual(ctx.exception.code, "segmentInvalid")

    def test_import_rejects_sibling_duplicate(self):
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({
                "filename": "t.json",
                "content": json.dumps({"name": "甲", "tree": {"A": {}, "a": {}}}, ensure_ascii=False),
            })
        self.assertEqual(ctx.exception.code, "templateSiblingDuplicated")

    def test_import_duplicate_filename_rejected(self):
        self._write("t.md", self._MD)
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({"filename": "t.md", "content": "# 新\n- x\n"})
        self.assertEqual(ctx.exception.code, "templateExists")

    def test_import_overwrite_moves_old_to_trash(self):
        self._write("t.md", self._MD)
        res = routes.import_template({
            "filename": "t.md", "content": "# 新\n- x\n", "overwrite": True})
        self.assertTrue(res["overwritten"])
        self.assertEqual(routes.load_template("t.md")["tree"], {"x": ""})
        trash = list((self.tmp / ".trash").rglob("t.md"))
        self.assertEqual(len(trash), 1)   # 旧版入回收站，可人工找回

    def test_import_rejects_invalid_filename(self):
        for bad in ("", "  ", "a.txt", "../x.md", "a/b.md"):
            with self.assertRaises(TreeError) as ctx:
                routes.import_template({"filename": bad, "content": self._MD})
            self.assertEqual(ctx.exception.code, "templateNameEmpty" if not bad.strip()
                             else "templateNameInvalid", repr(bad))

    def test_import_illegal_dir_guard_applies(self):
        """绑定目录非法（自绑项目自身）→ 拒绝（复用 6B 的写路径守卫）。"""
        patcher = mock.patch.object(config, "templates_dir", lambda: config.PROJECT_DIR)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(TreeError) as ctx:
            routes.import_template({"filename": "t.md", "content": self._MD})
        self.assertEqual(ctx.exception.code, "templateDirBlocked")

    # ---- 改名 / 删除：格式保持 ----

    def test_rename_md_keeps_md(self):
        self._write("old.md", self._MD)
        res = routes.rename_template("old.md", {"name": "新的"})
        self.assertEqual(res["file"], "新的.md")          # 仍是 .md，不转 json
        self.assertFalse((self.tmp / "old.md").exists())
        self.assertEqual(routes.load_template("新的.md")["name"], "新的")

    def test_rename_json_keeps_json(self):
        self._write("old.json", json.dumps(
            {"name": "甲", "tree": {"x": {}}}, ensure_ascii=False))
        res = routes.rename_template("old.json", {"name": "新的"})
        self.assertEqual(res["file"], "新的.json")

    def test_delete_md_soft(self):
        self._write("del.md", self._MD)
        res = routes.delete_template("del.md")
        self.assertFalse((self.tmp / "del.md").exists())
        self.assertTrue(Path(res["trashedTo"]).is_file())

    def test_json_name_hint_with_md_suffix_becomes_json(self):
        """`save_template` 带 `.md` 后缀 → 剥掉存为 `.json`（双格式上线后的友好化）。"""
        res = routes.save_template({"name": "甲.md", "tree": {"x": {}}})
        self.assertEqual(res["file"], "甲.json")


if __name__ == "__main__":
    unittest.main()
