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
                     "docs/任务进度.md", "docs/错误笔记.md", "src/server/app.py",
                     # V0.3.0：语言包已迁出 src/ —— 交接包漏了它，接手者拿到的是没有文案的程序
                     "locales/zh-CN.js", "locales/en-US.js"):
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


class FullPackTests(unittest.TestCase):
    """`--full` 完整开发包（V0.3.0 实测后新增）。

    存在的理由：接续包实测**跑不了四件套**（无 `tools/` `tests/`）、**没有回退点**
    （无 `store/` `versions/`），于是「改完能验证、改坏能回退」两条都断。
    `--full` 就是把这个缺口补上 —— 单测钉住「该有的必须有、不该带的必须不带」。
    """

    def test_带齐开发与回退所需(self):
        rels = {rel for _src, rel in hp.iter_full_files()}
        for must in ("tools/gate.py", "tools/verify.py", "tests/test_routes.py",
                     "templates/P0_空白项目模板.json", "templates-pack/pack.manifest.json",
                     "src/server/app.py", "locales/zh-CN.js", ".git/HEAD"):
            self.assertIn(must, rels, f"完整开发包缺 {must}")
        self.assertTrue(any(r.startswith("store/objects/") for r in rels), "缺 store/objects/")
        self.assertTrue(any(r.startswith("versions/") and r.endswith("MANIFEST.json") for r in rels),
                        "缺 versions/*/MANIFEST.json")

    def test_不带用户数据与可再生产物(self):
        rels = {rel for _src, rel in hp.iter_full_files()}
        for banned in ("data", "dist", "__pycache__", ".trash"):
            self.assertFalse(any(r == banned or r.startswith(banned + "/") or f"/{banned}/" in r
                                 for r in rels), f"完整开发包不应包含 {banned}")

    def test_可省掉git(self):
        rels = {rel for _src, rel in hp.iter_full_files(with_git=False)}
        self.assertFalse(any(r.startswith(".git/") for r in rels), "--no-git 仍带了 .git/")
        self.assertIn("tools/gate.py", rels, "省 .git 不该连带丢工具")

    def test_自检能抓缺件与越界(self):
        def make_zip(path: Path, extra: "list[str]", drop: str = "") -> None:
            base = ["VERSION", "manifest.json", "发布包清单.json",
                    "src/server/app.py", "locales/zh-CN.js", "locales/en-US.js",
                    "tools/gate.py", "tools/verify.py", "tools/package_release.py",
                    "tests/test_routes.py", "templates/P0_空白项目模板.json",
                    "templates-pack/pack.manifest.json",
                    "store/objects/00/abc", "versions/V0.3.0/MANIFEST.json", ".git/HEAD"]
            with zipfile.ZipFile(path, "w") as zf:
                for name in [n for n in base if n != drop] + extra:
                    zf.writestr(f"{hp.FULL_PREFIX}/{name}", b"x")

        with tempfile.TemporaryDirectory(prefix="qm_full_") as d:
            ok = Path(d) / "ok.zip"
            make_zip(ok, [])
            self.assertEqual(hp.verify(ok, full=True), 0, "该过的没过")

            # 反向验证①：抽掉 tools/ → 必须判红（这正是接续包的真实状态）
            no_tools = Path(d) / "no_tools.zip"
            make_zip(no_tools, [], drop="tools/gate.py")
            self.assertEqual(hp.verify(no_tools, full=True), 1, "缺 tools/ 竟未判红")

            # 反向验证②：带上 data/ → 必须判红（用户草稿不得外发）
            dirty = Path(d) / "dirty.zip"
            make_zip(dirty, ["data/editor.json"])
            self.assertEqual(hp.verify(dirty, full=True), 1, "带了 data/ 竟未判红")


class BudgetAlertTests(unittest.TestCase):
    """预算预警分级（V0.2.3 起）：余量 <5% 预警、<2% 临界。

    存在的理由：只在「越线」时报错，等于永远在最后一刻才发现 ——
    本仓真经历过「余 1,081 B 时被迫现场压注释」。分级让"还能不能再加一个功能"提前有答案。
    """

    def test_levels(self):
        self.assertEqual(gate.budget_alert(50_000, 655_360), "ok")
        self.assertEqual(gate.budget_alert(20_000, 655_360), "warn")    # 3.05%
        self.assertEqual(gate.budget_alert(8_634, 655_360), "crit")     # 1.32%

    def test_boundaries(self):
        self.assertEqual(gate.budget_alert(int(655_360 * 0.05), 655_360), "ok")   # 恰好 5% 不算预警
        self.assertEqual(gate.budget_alert(int(655_360 * 0.019), 655_360), "crit")

    def test_zero_limit_is_safe(self):
        self.assertEqual(gate.budget_alert(100, 0), "ok")


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
