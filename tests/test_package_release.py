"""青蔓 · 发布包构建工具的单测（V0.1.0）。

覆盖四件**会静默出错**的事：
  ① 白名单/黑名单 —— 把 `data/`、`store/`、`tests/` 打进包（用户拿到你的草稿与历史）；
  ② 运行时裁剪 —— 把 `Lib/test`（33 MB）带出去，或误删 `Lib/os.py`（启动即崩）；
  ③ 确定性 —— 同一输入两次构建字节不同，发布包无法复算；
  ④ 清单 —— 文件的 sha256 与磁盘不符，接收者无从校验。

不构建真实发布包（40 MB 级、依赖本机 Python 安装），只测纯逻辑。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
if str(_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_ROOT / "tools"))

import package_release as pr  # noqa: E402


class ProjectFilesTests(unittest.TestCase):
    """白名单只列该带的；黑名单挡住开发期资产。"""

    def test_includes_user_facing_files(self):
        rels = {rel for _src, rel in pr.iter_project_files()}
        for must in ("VERSION", "start.bat", "README_使用说明.md",
                     "src/server/app.py", "templates-pack/模板库来源说明.md"):
            self.assertIn(must, rels, f"发布包缺少 {must}")

    def test_excludes_dev_assets(self):
        rels = {rel for _src, rel in pr.iter_project_files()}
        for banned in ("data", "store", "versions", "docs", "tests", "tools", "legacy", "preview"):
            self.assertFalse(any(r == banned or r.startswith(banned + "/") for r in rels),
                             f"发布包不应包含 {banned}/")
        self.assertFalse(any("__pycache__" in r or r.endswith(".pyc") for r in rels))

    def test_sorted_and_deduped(self):
        rels = [rel for _src, rel in pr.iter_project_files()]
        self.assertEqual(rels, sorted(rels))
        self.assertEqual(len(rels), len(set(rels)))


class RuntimeTrimTests(unittest.TestCase):
    """运行时只留能跑的东西：`Lib/test` 不带、`Lib/os.py` 必须带。"""

    def _fake_runtime(self, base: Path) -> Path:
        runtime = base / "runtime"
        keep = ["python.exe", "python314.dll", "DLLs/_tkinter.pyd",
                "Lib/os.py", "Lib/tkinter/__init__.py", "tcl/tk90t.dll"]
        drop = ["Lib/test/test_os.py", "Lib/site-packages/requests.py",
                "Lib/idlelib/idle.py", "Lib/ensurepip/__init__.py",
                "Doc/readme.txt", "include/Python.h", "libs/python314.lib",
                "Scripts/pip.exe", "Lib/__pycache__/os.cpython-314.pyc"]
        for rel in keep + drop:
            path = runtime / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
        return runtime

    def test_keeps_interpreter_and_stdlib(self):
        with tempfile.TemporaryDirectory(prefix="qm_rt_") as d:
            runtime = self._fake_runtime(Path(d))
            rels = {rel for _src, rel in pr.iter_runtime_files(runtime)}
            for must in ("runtime/python.exe", "runtime/python314.dll",
                         "runtime/DLLs/_tkinter.pyd", "runtime/Lib/os.py",
                         "runtime/Lib/tkinter/__init__.py", "runtime/tcl/tk90t.dll"):
                self.assertIn(must, rels)

    def test_drops_docs_tests_and_third_party(self):
        with tempfile.TemporaryDirectory(prefix="qm_rt_") as d:
            runtime = self._fake_runtime(Path(d))
            rels = {rel for _src, rel in pr.iter_runtime_files(runtime)}
            for banned in ("runtime/Lib/test/test_os.py", "runtime/Lib/site-packages/requests.py",
                           "runtime/Lib/idlelib/idle.py", "runtime/Lib/ensurepip/__init__.py",
                           "runtime/Doc/readme.txt", "runtime/include/Python.h",
                           "runtime/libs/python314.lib", "runtime/Scripts/pip.exe"):
                self.assertNotIn(banned, rels)


class ManifestAndZipTests(unittest.TestCase):
    """清单可校验 + 打包确定性（同输入 → 同一 sha256）。"""

    def _stage(self, base: Path, payload: dict) -> tuple[Path, dict]:
        staging = base / "stage"
        srcs = []
        for name, data in payload.items():
            p = base / "src" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            srcs.append((p, name))
        manifest = pr.build_staging(staging, srcs, None)
        pr.write_manifest(staging, manifest)
        return staging, manifest

    def test_manifest_matches_disk(self):
        with tempfile.TemporaryDirectory(prefix="qm_man_") as d:
            staging, manifest = self._stage(Path(d), {"a.txt": b"hello", "sub/b.txt": b"world"})
            self.assertEqual(manifest["fileCount"], 2)
            self.assertEqual(manifest["totalBytes"], 10)
            for rel, meta in manifest["files"].items():
                data = (staging / rel).read_bytes()
                self.assertEqual(meta["size"], len(data))
                self.assertEqual(meta["sha256"], hashlib.sha256(data).hexdigest())
            on_disk = json.loads((staging / "发布包清单.json").read_text(encoding="utf-8"))
            self.assertEqual(on_disk["version"], pr.VERSION)

    def test_zip_is_deterministic(self):
        digests = []
        for _ in range(2):
            with tempfile.TemporaryDirectory(prefix="qm_zip_") as d:
                staging, _man = self._stage(Path(d), {"x/y.txt": b"same", "z.txt": b"bytes"})
                out = Path(d) / "out.zip"
                pr.build_zip(staging, out)
                digests.append(hashlib.sha256(out.read_bytes()).hexdigest())
                with zipfile.ZipFile(out) as zf:
                    names = zf.namelist()
                self.assertTrue(all(n.startswith(pr.PKG_DIRNAME + "/") for n in names))
                self.assertEqual(names, sorted(names), "zip 条目未排序")
        self.assertEqual(digests[0], digests[1], "同输入两次构建不一致")


class RuntimeDetectTests(unittest.TestCase):
    def test_rejects_non_python_dir(self):
        with tempfile.TemporaryDirectory(prefix="qm_detect_") as d:
            with self.assertRaises(SystemExit):
                pr.detect_runtime_dir(d)


if __name__ == "__main__":
    unittest.main()
