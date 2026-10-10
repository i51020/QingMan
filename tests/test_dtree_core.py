"""青蔓 QingMan · dtree_core 单元测试（§P0-1 / §P0-2 T2–T3）。

零第三方依赖：仅标准库 unittest。
测试一律在临时目录内进行，**不触碰真实用户目录**（§P0-2 T6）。

运行：
    python -m unittest discover -s tests -v
    QM_SRC=<其它版本根>/src python -m unittest discover -s tests -v   # 落地前先测预览版
"""

from __future__ import annotations

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

from server import config, dtree_core  # noqa: E402
from server.dtree_core import TreeError  # noqa: E402


def code_of(raw) -> str | None:
    """调 check_target；放行返回 None，拒绝返回错误码。"""
    try:
        dtree_core.check_target(raw)
        return None
    except TreeError as exc:
        return exc.code


class SegmentTests(unittest.TestCase):
    """validate_segment 边界（§P0-2 T3）。"""

    def test_accepts_normal_names(self):
        for name in ("素材", "docs", "a b", "说明.md", "层1.2"):
            self.assertEqual(dtree_core.validate_segment(name)[0], True, name)

    def test_rejects_non_string(self):
        self.assertEqual(dtree_core.validate_segment(None)[1], "segmentNotString")
        self.assertEqual(dtree_core.validate_segment(123)[1], "segmentNotString")

    def test_rejects_empty_and_blank(self):
        self.assertEqual(dtree_core.validate_segment("")[1], "segmentEmpty")
        self.assertEqual(dtree_core.validate_segment("   ")[1], "segmentEmpty")

    def test_rejects_dot_names(self):
        self.assertEqual(dtree_core.validate_segment(".")[1], "segmentDot")
        self.assertEqual(dtree_core.validate_segment("..")[1], "segmentDot")

    def test_rejects_too_long(self):
        self.assertEqual(dtree_core.validate_segment("x" * 121)[1], "segmentTooLong")
        self.assertTrue(dtree_core.validate_segment("x" * 120)[0])

    def test_rejects_illegal_chars(self):
        for name in ('a/b', "a\\b", "a:b", "a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"):
            self.assertEqual(dtree_core.validate_segment(name)[1], "segmentIllegalChar", name)

    def test_rejects_control_chars(self):
        self.assertEqual(dtree_core.validate_segment("a\tb")[1], "segmentIllegalChar")

    def test_rejects_windows_reserved(self):
        for name in ("CON", "con", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9",
                     "con.txt"):
            self.assertEqual(dtree_core.validate_segment(name)[1], "segmentReserved", name)


class CountTests(unittest.TestCase):

    def test_count_tree(self):
        tree = {"a": {"b": {}, "c": {"d": {}}}, "e.md": "", "f.txt": ""}
        self.assertEqual(dtree_core.count_tree(tree), (4, 2))

    def test_count_tree_non_dict(self):
        self.assertEqual(dtree_core.count_tree(["x"]), (0, 0))


class ValidateDocumentTests(unittest.TestCase):

    def _doc(self, **kw):
        base = {"type": "dir", "id": "d1", "name": "根", "children": []}
        base.update(kw)
        return base

    def test_ok(self):
        root = self._doc(children=[
            {"type": "dir", "id": "d2", "name": "子", "children": []},
            {"type": "file", "id": "f1", "name": "a.md", "content": "hi"},
        ])
        self.assertEqual(dtree_core.validate_document(root), {"dirs": 1, "files": 1})

    def test_root_must_be_dir(self):
        with self.assertRaises(TreeError) as ctx:
            dtree_core.validate_document({"type": "file", "id": "f", "name": "x"})
        self.assertEqual(ctx.exception.code, "editorRootNotDir")

    def test_duplicate_id(self):
        root = self._doc(children=[
            {"type": "file", "id": "dup", "name": "a", "content": ""},
            {"type": "file", "id": "dup", "name": "b", "content": ""},
        ])
        with self.assertRaises(TreeError) as ctx:
            dtree_core.validate_document(root)
        self.assertEqual(ctx.exception.code, "editorIdDuplicated")

    def test_sibling_duplicate_is_case_insensitive(self):
        root = self._doc(children=[
            {"type": "file", "id": "x", "name": "Readme", "content": ""},
            {"type": "file", "id": "y", "name": "readme", "content": ""},
        ])
        with self.assertRaises(TreeError) as ctx:
            dtree_core.validate_document(root)
        self.assertEqual(ctx.exception.code, "editorSiblingDuplicated")

    def test_too_many_nodes(self):
        children = [{"type": "file", "id": f"f{i}", "name": f"n{i}", "content": ""}
                    for i in range(config.MAX_EDITOR_NODES + 1)]
        with self.assertRaises(TreeError) as ctx:
            dtree_core.validate_document(self._doc(children=children))
        self.assertEqual(ctx.exception.code, "editorTooManyNodes")


class CheckTargetTests(unittest.TestCase):
    """§P0-1 R1–R5：落盘安全边界。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_target_")
        self.addCleanup(self.tmp.cleanup)

    # R1 路径规范化
    def test_r1_normalizes_dotdot(self):
        raw = str(Path(self.tmp.name) / "a" / ".." / "b")
        resolved = dtree_core.check_target(raw)
        self.assertEqual(resolved, (Path(self.tmp.name) / "b").resolve())
        self.assertNotIn("..", resolved.parts)

    def test_r1_target_missing(self):
        self.assertEqual(code_of(""), "targetMissing")
        self.assertEqual(code_of("   "), "targetMissing")
        self.assertEqual(code_of(None), "targetMissing")
        self.assertEqual(code_of(123), "targetMissing")

    # R2 盘根
    def test_r2_rejects_drive_root(self):
        self.assertEqual(code_of(Path.cwd().anchor), "targetTooShallow")

    # R3 系统目录（整棵子树）
    def test_r3_blocks_subtree(self):
        self.assertGreater(len(config.BLOCKED_SUBTREES), 0)
        for blocked, _label in config.BLOCKED_SUBTREES:
            self.assertEqual(code_of(str(blocked)), "targetBlocked", str(blocked))
            self.assertEqual(code_of(str(blocked / "sub")), "targetBlocked", str(blocked / "sub"))

    # R4 用户关键目录（仅根本身）
    def test_r4_blocks_root_allows_child(self):
        self.assertGreater(len(config.BLOCKED_ROOTS), 0)
        for blocked, _label in config.BLOCKED_ROOTS:
            self.assertEqual(code_of(str(blocked)), "targetBlocked", str(blocked))
        parent, _ = config.BLOCKED_ROOTS[0]
        self.assertIsNone(code_of(str(parent / "my-project")))

    # R5 项目自身及其上级
    def test_r5_rejects_project_and_ancestors(self):
        project = config.PROJECT_DIR_RESOLVED
        self.assertEqual(code_of(str(project)), "targetReserved")
        self.assertEqual(code_of(str(project.parent)), "targetReserved")

    def test_allows_normal_target(self):
        self.assertIsNone(code_of(str(Path(self.tmp.name) / "demo")))

    def test_allows_temp_dir_itself(self):
        # 临时目录若被误判为黑名单，测试将无法落盘 —— 这里显式锁定该前提
        self.assertIsNone(code_of(self.tmp.name))


class BuildTreeTests(unittest.TestCase):
    """§P0-1 R6–R8 与落盘行为。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_build_")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "out"

    def test_dry_run_writes_nothing(self):
        tree = {"a": {"b": {}}, "c.md": "hi"}
        result = dtree_core.build_tree(tree, self.base, dry_run=True)
        self.assertTrue(result["dryRun"])
        self.assertFalse(self.base.exists(), "dry_run 不得在磁盘上留下任何目录")
        self.assertEqual((result["plannedDirs"], result["plannedFiles"]), (2, 1))
        # 既有契约：dry_run 下 createdDirs/createdFiles 描述「将要新建」的清单（前端据此显示计划）
        self.assertEqual(len(result["createdDirs"]), 2)
        self.assertEqual(len(result["createdFiles"]), 1)
        self.assertEqual(result["existed"], [])

    def test_real_write_then_idempotent(self):
        tree = {"a": {"c.md": "hello"}, "b.txt": "world"}
        first = dtree_core.build_tree(tree, self.base, dry_run=False)
        self.assertEqual(len(first["createdDirs"]), 1)
        self.assertEqual(len(first["createdFiles"]), 2)
        self.assertEqual(first["existed"], [])
        self.assertTrue((self.base / "a" / "c.md").is_file())

        second = dtree_core.build_tree(tree, self.base, dry_run=False)
        self.assertEqual(second["createdDirs"], [], "重复生成不得重复建目录")
        self.assertEqual(second["createdFiles"], [], "已存在文件必须跳过（R7）")
        self.assertEqual(len(second["existed"]), 3)

    def test_existing_content_not_overwritten(self):
        target = self.base / "keep.txt"
        self.base.mkdir(parents=True, exist_ok=True)
        target.write_text("原始内容", encoding="utf-8")
        dtree_core.build_tree({"keep.txt": "新内容"}, self.base, dry_run=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "原始内容", "R7：不得覆盖既有文件")

    def test_file_dir_conflict(self):
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "dup").write_text("我是文件", encoding="utf-8")
        with self.assertRaises(TreeError) as ctx:
            dtree_core.build_tree({"dup": {}}, self.base, dry_run=False)
        self.assertEqual(ctx.exception.code, "pathConflict")

    def test_dir_conflict_for_file_target(self):
        """P3-13：类型冲突必须**对称** —— 树要建文件、磁盘同名是目录，也要报错而非静默跳过。"""
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "dup").mkdir()          # 磁盘上是目录
        with self.assertRaises(TreeError) as ctx:
            dtree_core.build_tree({"dup": "内容"}, self.base, dry_run=False)
        self.assertEqual(ctx.exception.code, "pathConflictDir")
        # 既有目录不得被改写或删除（R8）
        self.assertTrue((self.base / "dup").is_dir())

    def test_never_deletes(self):
        self.base.mkdir(parents=True, exist_ok=True)
        bystander = self.base / "既有文件.md"
        bystander.write_text("别删我", encoding="utf-8")
        dtree_core.build_tree({"new": {"x.txt": "1"}}, self.base, dry_run=False)
        self.assertTrue(bystander.is_file(), "R8：生成过程绝不删除既有文件")

    def test_r6_rejects_oversize_plan(self):
        tree = {f"d{i}": {} for i in range(config.MAX_NODES + 1)}
        with self.assertRaises(TreeError) as ctx:
            dtree_core.build_tree(tree, self.base, dry_run=True)
        self.assertEqual(ctx.exception.code, "tooManyNodes")
        self.assertFalse(self.base.exists(), "超限必须在写盘前被拒")

    def test_r6_boundary_at_limit_passes(self):
        tree = {f"d{i}": {} for i in range(config.MAX_NODES)}
        result = dtree_core.build_tree(tree, self.base, dry_run=True)
        self.assertEqual(result["plannedDirs"], config.MAX_NODES)

    def test_generated_files_use_lf(self):
        dtree_core.build_tree({"note.md": "第一行\n第二行\n"}, self.base, dry_run=False)
        data = (self.base / "note.md").read_bytes()
        self.assertNotIn(b"\r", data, "生成文件必须为 LF（§编码基线）")
        self.assertEqual(data, "第一行\n第二行\n".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
