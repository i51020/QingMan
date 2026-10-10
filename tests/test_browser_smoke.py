"""青蔓 QingMan · browser_smoke 纯函数单元测试（§P0-2 T2 / 审查报告 §P1-4）。

背景：`tools/browser_smoke.py` 的 7 个判定函数（`as_int` / `parse_metrics` /
`console_lines` / `find_browser` / `verify_metrics` 等）是全部页面级断言的**判定逻辑本体**，
但此前**零单测** —— `verify.py` 只做静态 token 锚定（防被削成空壳），
**不验证判定逻辑本身是否正确**。本文件把「一次性反向验证」变成**常态回归网**。

重点（复刻上一轮反向验证的逻辑，但固化为单测）：
  * 喂「正常指标」→ 7 项全 PASS；
  * 喂「P1-1 回归指标（分节 7 → 14 → 21）」→ **恰好**「帮助页·分节渲染幂等」一项 FAIL；
  * 喂「P1-2 回归指标（示例含中文名 6 个）」→ **恰好**「主界面·默认示例随语言」一项 FAIL。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import browser_smoke as bs  # noqa: E402

VERSION = "V0.0.25"

# 一份「一切正常」的探针指标 —— 与真机实测形态一致
NORMAL = {
    "htmlLang": "en-US",
    "idxRows": "6",
    "idxCjk": "0",
    "idxSkin": "1",
    "tplRows": "17",
    "secBefore": "7", "secEn": "7", "secZh": "7",
    "navBefore": "7", "navZh": "7",
    "langEn": "en-US", "langZh": "zh-CN",
    "chip": VERSION, "stale": "0",
    "qr": "1", "thanks": "1",
}

FAIL = "帮助页·分节渲染幂等"
FAIL_LANG = "主界面·默认示例随语言"


def run_metrics(metrics: dict, expected_version: str = VERSION,
                expect_templates: bool = True) -> list[tuple[bool, str, str]]:
    """跑一遍 `verify_metrics` 并取回它产生的判定结果（清掉全局累积，保证独立）。"""
    bs.RESULTS.clear()
    bs.verify_metrics(metrics, expected_version, expect_templates)
    return list(bs.RESULTS)


def failed_names(results) -> list[str]:
    return [name for ok, name, _note in results if not ok]


class AsIntTests(unittest.TestCase):

    def test_parses_plain_and_padded(self):
        self.assertEqual(bs.as_int("5"), 5)
        self.assertEqual(bs.as_int(" 42 "), 42)

    def test_default_on_garbage(self):
        self.assertEqual(bs.as_int("x"), -1)
        self.assertEqual(bs.as_int(None), -1)
        self.assertEqual(bs.as_int("3.5"), -1)          # 非整数 → 不静默截断
        self.assertEqual(bs.as_int("x", 0), 0)          # 默认值可指定

    def test_negative_and_zero(self):
        self.assertEqual(bs.as_int("0"), 0)
        self.assertEqual(bs.as_int("-3"), -3)


class ParseMetricsTests(unittest.TestCase):

    def test_container_anchored(self):
        stdout = '<html><div id="out">RESULT a=1 | b=two</div></html>'
        self.assertEqual(bs.parse_metrics(stdout), {"a": "1", "b": "two"})

    def test_fallback_when_no_container(self):
        # 无容器时退回宽松匹配（旧版浏览器 / 结构变动的兜底路径）
        self.assertEqual(bs.parse_metrics("junk RESULT a=1 | b=2\n"), {"a": "1", "b": "2"})

    def test_probe_source_literal_not_mistaken_for_result(self):
        """探针源码里也有 `'RESULT '` 字面量 —— 不能被当成结果行（否则整项假通过）。"""
        source = "var line = 'RESULT ' + parts.join('|');\n"
        self.assertIsNone(bs.parse_metrics(source))

    def test_no_result_returns_none(self):
        self.assertIsNone(bs.parse_metrics("<html>nothing here</html>"))

    def test_parts_without_equals_are_dropped(self):
        # 只有 `k=v` 才入表；落单的片段不产生键
        self.assertEqual(bs.parse_metrics('<div id="out">RESULT a=1 | lonely</div>'),
                         {"a": "1"})


class ConsoleLinesTests(unittest.TestCase):

    ORIGIN = "http://127.0.0.1:8799"

    def _line(self, text: str, source: str | None = None) -> str:
        origin = source or self.ORIGIN
        return f'[1234:1010:1.1:INFO:CONSOLE(1)] "{text}", source: {origin}/_probe_ui.html (8799)'

    def test_keeps_own_origin_console(self):
        line = self._line("Uncaught Error: boom")
        self.assertEqual(bs.console_lines(line, self.ORIGIN), [line])

    def test_drops_browser_extension_noise(self):
        noise = ('[1:1:1.1:INFO:CONSOLE(1)] "whatever", source: '
                 'chrome-extension://abcdefg/protocol_launch.js (1)')
        self.assertEqual(bs.console_lines(noise, self.ORIGIN), [])

    def test_drops_devtools_noise(self):
        noise = '[1:1:1.1:ERROR:CONSOLE(1)] "x", source: devtools://devtools/bundled/x.js'
        self.assertEqual(bs.console_lines(noise, self.ORIGIN), [])

    def test_drops_other_origin(self):
        other = self._line("Uncaught Error: other", source="http://127.0.0.1:9999")
        self.assertEqual(bs.console_lines(other, self.ORIGIN), [])

    def test_drops_non_console_lines(self):
        self.assertEqual(bs.console_lines("[1:1:1.1:VERBOSE1:foo] bar", self.ORIGIN), [])

    def test_empty_origin_keeps_all_but_extension(self):
        keep = self._line("Uncaught", source="http://localhost:1")
        noise = '[1:1:1.1:INFO:CONSOLE(1)] "x", source: chrome-extension://a/b.js'
        self.assertEqual(bs.console_lines(keep + "\n" + noise, ""), [keep])


class FindBrowserTests(unittest.TestCase):

    def test_explicit_existing_path_wins(self):
        self.assertEqual(bs.find_browser(sys.executable), str(sys.executable))

    def test_env_var_used_when_no_explicit(self):
        old = os.environ.get("QM_BROWSER")
        os.environ["QM_BROWSER"] = sys.executable
        try:
            self.assertEqual(bs.find_browser(None), str(sys.executable))
        finally:
            if old is None:
                os.environ.pop("QM_BROWSER", None)
            else:
                os.environ["QM_BROWSER"] = old

    def test_missing_explicit_path_not_returned(self):
        missing = "Z:/definitely/not/here/quark.exe"
        self.assertNotEqual(bs.find_browser(missing), missing)


class VerifyMetricsTests(unittest.TestCase):

    def test_normal_all_pass(self):
        results = run_metrics(NORMAL)
        self.assertEqual(failed_names(results), [], "正常指标不应有任何失败项")
        self.assertEqual(len(results), 7, "verify_metrics 应产生 7 项判定")

    def test_p1_1_regression_fails_exactly_section_idempotence(self):
        """P1-1 回归：帮助页切语言累积分节（7 → 14 → 21）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, secEn="14", secZh="21")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL])

    def test_p1_2_regression_fails_exactly_default_sample_language(self):
        """P1-2 回归：默认示例未随语言（含中文名 6 个）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, idxCjk="6")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_LANG])

    def test_nav_accumulation_also_fails_section_idempotence(self):
        metrics = dict(NORMAL, navZh="14")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL])

    def test_stale_version_chip_fails(self):
        for bad in (dict(NORMAL, chip="V0.0.24"), dict(NORMAL, stale="1"),
                    dict(NORMAL, chip="")):
            with self.subTest(metrics=bad):
                self.assertEqual(failed_names(run_metrics(bad)),
                                 ["帮助页·版本徽标 = VERSION（后端可达）"])

    def test_unexpected_language_fails_switch_check(self):
        metrics = dict(NORMAL, langZh="en-US")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["帮助页·语言切换联动 html lang"])

    def test_support_page_regression_fails(self):
        metrics = dict(NORMAL, qr="0")
        self.assertEqual(failed_names(run_metrics(metrics)), ["支持页·拆页后完好"])

    def test_templates_check_skipped_when_not_expected(self):
        results = run_metrics(NORMAL, expect_templates=False)
        self.assertEqual(len(results), 6, "不期望模板时不应产生模板判定项")
        self.assertNotIn("主界面·模板库已接入", [n for _o, n, _x in results])

    def test_low_row_count_fails(self):
        metrics = dict(NORMAL, idxRows="1")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_LANG])


if __name__ == "__main__":
    unittest.main()
