"""青蔓 QingMan · store 单元测试（§P0-2 T2）。

重点：`manifest_digest` 把**路径**纳入运算 —— 改名必须能被检出。
以及同版本多修订（§P0-6）的追加语义。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import store  # noqa: E402


class ManifestDigestTests(unittest.TestCase):

    def test_detects_rename(self):
        a = {"src/x.py": "sha256:aaa", "src/y.py": "sha256:bbb"}
        b = {"src/x.py": "sha256:aaa", "src/z.py": "sha256:bbb"}   # y → z（内容同）
        self.assertNotEqual(store.manifest_digest(a), store.manifest_digest(b),
                            "改名必须改变清单指纹")

    def test_detects_content_change(self):
        a = {"src/x.py": "sha256:aaa"}
        b = {"src/x.py": "sha256:ccc"}
        self.assertNotEqual(store.manifest_digest(a), store.manifest_digest(b))

    def test_detects_path_move(self):
        a = {"src/a/x.py": "sha256:aaa"}
        b = {"src/b/x.py": "sha256:aaa"}
        self.assertNotEqual(store.manifest_digest(a), store.manifest_digest(b))

    def test_order_independent(self):
        a = {"a": "1", "b": "2", "c": "3"}
        b = {"c": "3", "b": "2", "a": "1"}
        self.assertEqual(store.manifest_digest(a), store.manifest_digest(b))

    def test_stable(self):
        m = {"src/x.py": "sha256:aaa"}
        self.assertEqual(store.manifest_digest(m), store.manifest_digest(dict(m)))

    def test_empty(self):
        self.assertEqual(len(store.manifest_digest({})), 64)


class RefParsingTests(unittest.TestCase):

    def test_manifest_filename(self):
        self.assertEqual(store.manifest_filename(1), "MANIFEST.json")
        self.assertEqual(store.manifest_filename(2), "MANIFEST-r2.json")
        with self.assertRaises(ValueError):
            store.manifest_filename(0)

    def test_revision_of(self):
        self.assertEqual(store.revision_of("MANIFEST.json"), 1)
        self.assertEqual(store.revision_of("MANIFEST-r7.json"), 7)
        self.assertIsNone(store.revision_of("SNAPSHOT.json"))
        self.assertIsNone(store.revision_of("MANIFEST-r.json"))

    def test_parse_ref(self):
        self.assertEqual(store.parse_ref("V0.0.1"), ("V0.0.1", None))
        self.assertEqual(store.parse_ref("V0.0.1@r2"), ("V0.0.1", 2))
        self.assertEqual(store.parse_ref("V0.0.1@2"), ("V0.0.1", 2))
        self.assertEqual(store.parse_ref(" V0.0.1@R3 "), ("V0.0.1", 3))
        for bad in ("V0.0.1@r0", "V0.0.1@rx", "V0.0.1@"):
            with self.assertRaises(ValueError, msg=bad):
                store.parse_ref(bad)


class ShaTests(unittest.TestCase):

    def test_sha256_and_blob_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "a.txt"
            f.write_bytes(b"hello")
            digest = store.sha256_of(f)
            self.assertEqual(len(digest), 64)
            self.assertEqual(store.blob_path(root, digest),
                             root / "store" / "objects" / digest[:2] / digest)


class CommitIntegrationTests(unittest.TestCase):
    """建一个最小项目，跑真实的 commit → 追加修订流程。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_store_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
        (self.root / "start.bat").write_text("@echo off\r\n", encoding="utf-8")
        (self.root / "VERSION").write_text("V0.0.1\n", encoding="utf-8", newline="\n")

    def _manifest(self, rev=1):
        return json.loads(
            (self.root / "versions" / "V0.0.1" / store.manifest_filename(rev))
            .read_text(encoding="utf-8"))

    def test_commit_creates_manifest_and_blobs(self):
        self.assertEqual(store.do_commit(self.root, self.root, "首次", ""), 0)
        meta = self._manifest()
        self.assertEqual(meta["version"], "V0.0.1")
        self.assertEqual(meta["revision"], 1)
        self.assertEqual(meta["fileCount"], 3)
        self.assertEqual(set(meta["files"]), {"VERSION", "start.bat", "src/a.py"})
        for rel in meta["files"]:
            digest = meta["files"][rel].split(":", 1)[-1]
            self.assertTrue(store.blob_path(self.root, digest).is_file(), rel)
        self.assertIsNone(meta["parent"])

    def test_identical_commit_is_skipped(self):
        store.do_commit(self.root, self.root, "首次", "")
        store.do_commit(self.root, self.root, "一模一样", "")
        self.assertFalse((self.root / "versions" / "V0.0.1" / "MANIFEST-r2.json").exists(),
                         "内容未变时不得追加修订")

    def test_same_version_appends_revision(self):
        store.do_commit(self.root, self.root, "首次", "")
        (self.root / "src" / "a.py").write_text("print('b')\n", encoding="utf-8")
        store.do_commit(self.root, self.root, "第二次", "")
        meta = self._manifest(2)
        self.assertEqual(meta["revision"], 2)
        self.assertEqual(meta["parentManifest"], "MANIFEST.json")
        self.assertEqual(store.latest_revision(self.root, "V0.0.1"), 2)

    def test_base_manifest_never_overwritten(self):
        store.do_commit(self.root, self.root, "首次", "")
        before = (self.root / "versions" / "V0.0.1" / "MANIFEST.json").read_bytes()
        (self.root / "src" / "a.py").write_text("print('c')\n", encoding="utf-8")
        store.do_commit(self.root, self.root, "第二次", "")
        after = (self.root / "versions" / "V0.0.1" / "MANIFEST.json").read_bytes()
        self.assertEqual(before, after, "r1 基线清单绝不覆盖（§P0-6）")

    def test_list_versions_and_fsck(self):
        store.do_commit(self.root, self.root, "首次", "")
        self.assertEqual(store.list_versions(self.root), ["V0.0.1"])
        self.assertEqual(store.do_fsck(self.root), 0)


class FingerprintDiffTests(unittest.TestCase):
    """§P2-9：指纹比对单点（handoff 与 verify 复用同一实现）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_fp_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("A\n", encoding="utf-8")

    def _h(self, rel):
        return "sha256:" + store.sha256_of(self.root / rel)

    def test_clean_returns_three_empty_lists(self):
        recorded = {"src/a.py": self._h("src/a.py")}
        self.assertEqual(store.fingerprint_diff(self.root, recorded), ([], [], []))

    def test_detects_changed_added_missing(self):
        recorded = {
            "src/a.py": "sha256:" + "0" * 64,        # 内容不符 → 改动
            "src/gone.py": "sha256:" + "1" * 64,     # 盘上不存在 → 缺失
        }
        (self.root / "src" / "new.py").write_text("N\n", encoding="utf-8")   # 未记录 → 新增
        changed, added, missing = store.fingerprint_diff(self.root, recorded)
        self.assertEqual(changed, ["src/a.py"])
        self.assertEqual(added, ["src/new.py"])
        self.assertEqual(missing, ["src/gone.py"])

    def test_lists_are_sorted(self):
        recorded = {"src/z.py": "sha256:" + "0" * 64, "src/a.py": "sha256:" + "0" * 64}
        for name in ("src/z.py", "src/a.py"):
            (self.root / name).write_text("x\n", encoding="utf-8")
        changed, _added, _missing = store.fingerprint_diff(self.root, recorded)
        self.assertEqual(changed, sorted(changed))


class IsWithinTests(unittest.TestCase):
    """§P2-8 的路径包含判定（对齐 config.is_within 语义）。"""

    def test_equal_below_outside(self):
        base = Path("/a/b")
        self.assertTrue(store.is_within(base, base))
        self.assertTrue(store.is_within(Path("/a/b/c/d"), base))
        self.assertFalse(store.is_within(Path("/a"), base))
        self.assertFalse(store.is_within(Path("/a/bc"), base))


class FromValidationTests(unittest.TestCase):
    """§P2-8：--from 指向 root 之内的子目录必须被拦下（清单相对路径会错位）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_from_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("A\n", encoding="utf-8")
        (self.root / "VERSION").write_text("V0.0.1\n", encoding="utf-8", newline="\n")
        # 一个「同构子目录」：root/preview/V0.0.1/src/...
        sub = self.root / "preview" / "V0.0.1" / "src"
        sub.mkdir(parents=True)
        (sub / "a.py").write_text("B\n", encoding="utf-8")

    def _run(self, *extra):
        return subprocess.run(
            [sys.executable, "-B", str(_TOOLS / "store.py"), "commit",
             "--root", str(self.root), *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_from_inside_root_is_rejected(self):
        proc = self._run("--from", str(self.root / "preview" / "V0.0.1"))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("不得指向", proc.stdout)
        self.assertFalse((self.root / "versions").exists(), "被拦下时不得写清单")

    def test_from_equal_root_is_ok(self):
        proc = self._run("--from", str(self.root))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((self.root / "versions" / "V0.0.1" / "MANIFEST.json").is_file())


class CheckoutTrashTests(unittest.TestCase):
    """§P2-5：同秒两次 checkout 不得让后一次的回收副本覆盖前一次。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qm_trash_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("A\n", encoding="utf-8")
        (self.root / "VERSION").write_text("V0.0.1\n", encoding="utf-8", newline="\n")
        store.do_commit(self.root, self.root, "首次", "")

    def test_same_second_checkouts_keep_both_trash_copies(self):
        # 关键：**同一路径**两次被回收（第一次回收后用户又建了同名文件）——
        # 若回收目录名撞车，后一次的副本会覆盖前一次，前一次内容永久丢失（§P2-5）。
        (self.root / "src" / "extra.py").write_text("A\n", encoding="utf-8")
        store.do_checkout(self.root, "V0.0.1", False)
        (self.root / "src" / "extra.py").write_text("B\n", encoding="utf-8")
        store.do_checkout(self.root, "V0.0.1", False)
        trash = self.root / "store" / ".trash"
        contents = {p.read_text(encoding="utf-8")
                    for d in trash.iterdir() if d.is_dir()
                    for p in d.rglob("extra.py") if p.is_file()}
        self.assertEqual(contents, {"A\n", "B\n"},
                         "两次回收副本都须留存，不得互相覆盖")


if __name__ == "__main__":
    unittest.main()
