"""青蔓 · 接续包与交付门禁的单测（V0.1.0）。

这两支工具治的都是「流程会漏」而不是「代码会错」，因此单测要钉住的是**两条纪律**：
  ① 接续包**只能带交接必需品** —— 带进 `store/`（整个版本库）或 `data/`（你的草稿）
     既臃肿又越界；漏掉 `docs/项目约定.md` 则接手者不知道规矩。
  ② 门禁的「预算」与「文档断言提示」不能自己乱：预算按字节求和（不是磁盘块），
     断言扫描**必须跳过历史快照**（否则每次运行都在喊狼来了，最后没人看）。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
for path in (_ROOT / "tools",):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gate  # noqa: E402
import handoff_pack as hp  # noqa: E402


class HandoffPackTests(unittest.TestCase):
    def test_包含交接必需品(self):
        rels = {rel for _src, rel in hp.iter_handoff_files()}
        for must in ("VERSION", "manifest.json", "docs/项目约定.md",
                     "docs/任务进度.md", "docs/错误笔记.md", "src/server/app.py"):
            self.assertIn(must, rels, f"接续包缺 {must}")

    def test_不带版本库与用户数据(self):
        rels = {rel for _src, rel in hp.iter_handoff_files()}
        for banned in ("store", "versions", "data", "dist", "runtime"):
            self.assertFalse(any(r == banned or r.startswith(banned + "/") for r in rels),
                             f"接续包不应包含 {banned}/")

    def test_构建后可自检且确定性(self):
        with tempfile.TemporaryDirectory(prefix="qm_hoff_") as d:
            stamp = "2026-10-17T16:00:00+08:00"      # 固定构建时间 → 才谈得上「逐字节一致」
            out1 = hp.build(Path(d), stamp)
            out2 = hp.build(Path(d).parent / f"again_{Path(d).name}", stamp)
            self.assertEqual(hp.verify(out1), 0)
            self.assertEqual(out1.read_bytes(), out2.read_bytes(), "同输入两次构建不一致")
            with zipfile.ZipFile(out1) as zf:
                names = zf.namelist()
            self.assertTrue(all(n.startswith(hp.PREFIX + "/") for n in names))
            self.assertIn(f"{hp.PREFIX}/发布包清单.json", names)


class GateTests(unittest.TestCase):
    def test_预算按字节求和并给出余量(self):
        with tempfile.TemporaryDirectory(prefix="qm_gate_") as d:
            root = Path(d)
            (root / "src" / "a").mkdir(parents=True)
            (root / "src" / "a" / "x.py").write_bytes(b"x" * 100)
            (root / "src" / "big.py").write_bytes(b"y" * 300)
            rows = dict(gate.budget(root, src_limit=1000, file_limit=500))
            self.assertIn("400", rows["src/ 合计"])
            self.assertIn("余 600", rows["src/ 合计"])
            self.assertIn("big.py", rows["单文件最大"])
            self.assertIn("余 200", rows["单文件最大"])

    def test_断言扫描跳过历史快照(self):
        with tempfile.TemporaryDirectory(prefix="qm_gate_") as d:
            docs = Path(d) / "docs"
            docs.mkdir()
            (docs / "项目手册.md").write_text("基础（截至 V0.0.10 实测）\n", encoding="utf-8")
            (docs / "任务进度.md").write_text("V0.0.10 实测 · 历史条目\n", encoding="utf-8")
            (docs / "验收基线_V0.0.10_20260101.md").write_text("V0.0.10 实测\n", encoding="utf-8")
            hits = gate.doc_claims(Path(d), "V9.9.9")
            self.assertEqual(len(hits), 1, hits)
            self.assertIn("项目手册.md", hits[0])

    def test_当前版本不提示(self):
        with tempfile.TemporaryDirectory(prefix="qm_gate_") as d:
            docs = Path(d) / "docs"
            docs.mkdir()
            (docs / "项目手册.md").write_text("V1.2.3 实测 119 项\n", encoding="utf-8")
            self.assertEqual(gate.doc_claims(Path(d), "V1.2.3"), [])


if __name__ == "__main__":
    unittest.main()
