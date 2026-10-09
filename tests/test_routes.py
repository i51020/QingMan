"""青蔓 QingMan · routes 单元测试（§P0-1 / §P0-2 T2）。

覆盖：参数校验、落盘安全边界的错误码透出、编辑态读写往返与拒写分支。
全部在临时目录内进行，不触碰主线 `data/`。
"""

from __future__ import annotations

import json
import os
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


class HealthTests(unittest.TestCase):

    def test_health_shape(self):
        info = routes.health()
        self.assertTrue(info["ok"])
        self.assertEqual(info["app"], config.APP_NAME_EN)
        self.assertIn("version", info)
        json.dumps(info)  # 必须可序列化


if __name__ == "__main__":
    unittest.main()
