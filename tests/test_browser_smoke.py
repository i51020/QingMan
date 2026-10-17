"""青蔓 QingMan · browser_smoke 纯函数单元测试（§P0-2 T2 / 审查报告 §P1-4）。

背景：`tools/browser_smoke.py` 的 7 个判定函数（`as_int` / `parse_metrics` /
`console_lines` / `find_browser` / `verify_metrics` 等）是全部页面级断言的**判定逻辑本体**，
但此前**零单测** —— `verify.py` 只做静态 token 锚定（防被削成空壳），
**不验证判定逻辑本身是否正确**。本文件把「一次性反向验证」变成**常态回归网**。

重点（复刻上一轮反向验证的逻辑，但固化为单测）：
  * 喂「正常指标」→ 28 项全 PASS（V0.0.38 起含 6E 的绑定 UI / 右键菜单 / 轮询实证；
    V0.0.40 起含目标位置「选择…」按钮的就位与取词刷新；
    V0.0.41 起含模板「新建」按钮 + 弹窗开合/起点填充的运行时实证；
    V0.0.42 起含根名方案 C 的两条；
    V0.0.43 起含 UI 定版差集 G（工具栏三分组）/ H（检视器属性⇄源码）/ F（多选手势 + 批量删除只作用于最外层祖先）四条）；
  * 喂「P1-1 回归指标（分节 7 → 14 → 21）」→ **恰好**「帮助页·分节渲染幂等」一项 FAIL；
  * 喂「P1-2 回归指标（示例含中文名 6 个）」→ **恰好**「主界面·默认示例随语言」一项 FAIL；
  * 喂「C-P3-5 回归指标（非法皮肤名被直接采用）」/「D-P3-2 回归指标（顶栏图标色仍是旧灰）」→ 各恰好一项 FAIL；
  * V0.0.32 三项（C-P3-2 子孙落点误收 / C-P3-3 划过子元素误摘 / C-P3-4 提示条无上限）→ 各恰好一项 FAIL；
  * V0.0.43 四项（G 按钮离组 / H 源码栏非 JSON / F 手势断链 / F 父子同选去重失效）→ 各恰好一项 FAIL。

NORMAL 里的 V0.0.43 各值取**真机实测原值**（`tools/browser_smoke.py` 一次真实运行），
非手填 —— 以免基线自身与页面行为悄悄漂移；改探针须同步回此处。
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
    "skinEn": "Paper", "skinZh": "纸张",
    "tplRows": "1",
    "secBefore": "7", "secEn": "7", "secZh": "7",
    "navBefore": "7", "navZh": "7",
    "langEn": "en-US", "langZh": "zh-CN",
    "chip": VERSION, "stale": "0",
    "qr": "1", "thanks": "1",
    # V0.0.29 新增：C-P3-5（非法皮肤回落）/ D-P3-2（箭头随 --qm-text-dim）/ C-P3-1（重建后滚动保持）
    "badSkinHref": "./css/skins/s06-moonlight-pengray.css",
    "arrowColor": "rgb(79, 84, 90)", "dimColor": "rgb(79, 84, 90)",
    "scrollBefore": "40", "scrollAfter": "40", "reRendered": "1",
    # V0.0.32 新增：C-P3-2（拖拽落点预判）/ C-P3-3（划子元素不摘高亮）/ C-P3-4（提示条上限）
    #   上限值须与 src/web/js/ui/toast.js 的 MAX_TOASTS 一致（verify_metrics 会从源码读，此处对齐）
    "dragSelf": "1", "dragDesc": "1", "dragOk": "1",
    "dlChild": "1", "dlOut": "1",
    "toastN": str(bs.toast_cap()),
    # V0.0.38 新增：6E（绑定 UI / 右键菜单项 / 轮询实证）
    "tplDirRow": "1", "tplDirPath": "D:/x/templates", "tplDirBtns": "3",
    # V0.2.0：导出拆成两项 ⇒ 6 项（夹具必须与 browser_smoke 的判据同步，否则基线整体失真）
    "tplMenuN": "6",
    "tplMenu": "Load/Rename/Duplicate/Export as .json/Export as .md/Delete",
    # V0.0.51@r11 新增：模板行 ⋮ 常驻入口 —— 7aj⑤b 的**运行期**对照。
    #   静态判据（verify 7aj⑤b）只能证「产出方源码里有这三样标记 + 调用点 ≥2 + 不另造菜单」，
    #   证不了「点了它**真的**开同一个 #ctxMenu」—— 只有本探针走真实监听器能证。
    "tplMoreThere": "1", "tplMoreN": "6",
    "tplMoreMenu": "Load/Rename/Duplicate/Export as .json/Export as .md/Delete",
    # V0.2.2：关得掉（hidden 与计算样式双判据）
    "ctxClosed": "1", "ctxDisplay": "none",
    # V0.2.3：程序化聚焦不得弹出提示
    "tipOnFocus": "0",
    "pollBefore": "1", "pollAfter": "2",
    # V0.0.39 新增：皮肤 swatch 绑定（网格按 swatch[0] 背景明度亮 → 暗排序）
    #   期望序列由 tools/browser_smoke.py 的 expected_skin_order() 独立复算，
    #   与 src/web/js/ui/skin-picker.js 的 luma() 同公式（改皮肤背景色须同步此处基线）。
    "skinOrder": bs.expected_skin_order(),
    "skinCount": "16",
    # V0.0.40 新增：目标位置「选择…」按钮（手册 10.2 节 #13）—— 证「在位 + 文案随语言刷新」。
    #   V0.0.50 · I 组：该按钮已去文字改纯线性图标，取词证据改从**可访问名 + tooltip**
    #   采集（`aria-label | title`），故基线形态随之变化 —— 断言强度不变（非空 + 随语言变）。
    #   文案取自 i18n 的 gen.targetPick / gen.targetPickTip；改文案须同步此处基线。
    "pickTargetBtn": "1",
    "pickTargetEn": "Choose... ／ Choose an existing folder as the target path (system folder picker)",
    "pickTargetZh": "选择… ／ 选择一个已存在的目录作为目标位置（本机原生目录选择框）",
    # V0.0.41 新增：模板编辑区「新建模板」（手册 9.2 节 #7 / 10.2 节 #4）。
    #   文案取自 i18n 的 template.new / template.newTip（同上，V0.0.50 起走 aria-label | title）；
    #   起点首项是 template.newBaseBlank（探针读时语言已复位 en-US，故基线为英文文案）。
    #   改文案须同步此处基线。
    "tplNewBtn": "1", "tplNewDlg": "1",
    "tplNewEn": "New ／ Create a template from scratch (blank or any template in the library as a starting point)",
    "tplNewZh": "新建 ／ 从零创建一套模板（可选空白或库中任一模板作起点）",
    "tplNewOpen": "1", "tplNewBaseN": "2", "tplNewBaseText": "Blank (root only)",
    "tplNewClosing": "0", "tplNewClosed": "1",
    # V0.0.42 新增：根名方案 C（手册 10.2 节 #12）—— 根节点名即「根文件夹名」。
    #   探针与 i18n 解耦（只比对「含/不含」受控根名 'QmRootX'），故摘要基线用哑值占位。
    "rootProbe": "1",
    "rootSumBefore": "", "rootSumAfter": "Target X · Root QmRootX · Dry run",
    "rootSumBlank": "Target X · No root folder · Dry run",
    "rootNameBefore": "", "rootNameAfter": "QmRootX", "rootNameBlank": "(no root folder)",
    # V0.0.43 新增：UI 定版差集 G / H / F 三条（真机实测原值）。
    #   G：工具栏分组 —— 锚点是 8 颗按钮的**归属序列**（见 bs.EXPECT_GROUP_MAP），
    #      只数分组个数会被空壳 div 骗过，故同时钉「组数 / 带标签数 / 归属序列」。
    #      V0.0.50 · I 组：「另存为模板」移入操作带独立成组 → 3 组变 4 组。
    #      V0.0.51@r3：视图组两颗（全部展开 / 全部折叠）合为单颗切换 → 9 颗变 8 颗。
    "gGroups": "4", "gLabels": "4", "gMap": bs.EXPECT_GROUP_MAP,
    #   H：检视器「属性 ⇄ 源码」—— hJson + hHasChild 是强证据（源码栏须为可解析 JSON
    #      且真的含子节点名，证走的是 toPlainTree 序列化而非随手拼串）；hBack=2 证能复位。
    "hSeg": "2", "hPropHidden": "1", "hSrcShown": "1", "hJson": "1", "hHasChild": "1",
    "hBack": "2", "hPref": "src",
    #   F：多选批量。fAll 与 fVisible 联动（全选除根 = 可见行数 - 1）；fDedupSet 证父子同选
    #      在视图层确实标了 2 行「多选」。
    "fBar0": "0", "fMulti": "2", "fBarOn": "1", "fInfo": "1", "fAgg": "1",
    "fBarOff": "1", "fMultiOff": "0", "fShift": "3", "fVisible": "6", "fAll": "5",
    "fAllBar": "1", "fBarOff2": "1", "fDedupSet": "2",
    #   fConfirmMsg 是**取词**后的整句（随语言变化），判定只用 first_int 抽其中数字；
    #   基线取真机英文原句，但改文案不会影响判定 —— 关键量是首个数字（= 最外层祖先数）。
    "fConfirmMsg": "Delete the 1 selected nodes and all their children? (undoable)",
    "fDropN": "3", "fBefore": "6", "fAfter": "3", "fCancelKept": "1", "fBarClear": "1",
    # V0.0.45 新增：Soft 转基础层（三页 <html> 不再挂 data-soft）—— 「柔光层被加载并**生效**」
    #   的运行时证据。判定 = 侧栏影与**同页参照**（探针临时元素施加 `var(--qm-raise),
    #   var(--qm-card-edge)`）**逐字符相等**且含 inset。基线取真机实测原值（默认皮肤 S06），
    #   两者天然相等；改 soft 对 #sidebar 的表达式须同步此处。
    "softShadow": "rgba(255, 255, 255, 0.55) -3px -3px 6px 0px, rgba(99, 99, 98, 0.15) 3px 3px 6px 0px, rgba(255, 255, 255, 0.62) 0.5px 0.5px 1px 0px inset",
    "softRef": "rgba(255, 255, 255, 0.55) -3px -3px 6px 0px, rgba(99, 99, 98, 0.15) 3px 3px 6px 0px, rgba(255, 255, 255, 0.62) 0.5px 0.5px 1px 0px inset",
    # V0.0.52 新增：树行图标归一（emoji 📁/📄 → `.ic` mask）。
    #   取值是 `tree-view.js` 组装出的**真实类名字符串**（`className` 一个整串 +
    #   `classList.add` 追加的形状），故基线写全串而非子串匹配。
    #   treeIconTxtLen = 0 是「彩色字形真的撤了」的证据 —— 与类名互补缺一不可。
    "treeIconCls": "ic ic-sm tree-icon ic-folder", "treeIconTxtLen": "0",
}

FAIL = "帮助页·分节渲染幂等"
FAIL_LANG = "主界面·默认示例随语言"
FAIL_DRAG = "主界面·拖拽预判自身子树（C-P3-2）"
FAIL_DL = "主界面·拖拽高亮不因划过子元素闪烁（C-P3-3）"
FAIL_TOAST = "主界面·提示条数量上限（C-P3-4）"
# V0.0.37（6D）：模板判定项由「模板库已接入（≥1）」收紧为「内置模板仅 P0（恰好 1）」
TPL_CHECK = "主界面·内置模板仅 P0（V0.0.37）"
# V0.0.40（手册 10.2 节 #13）：目标位置「选择…」按钮的判定名
FAIL_PICK = "主界面·目标位置「选择…」按钮就位且随语言刷新（V0.0.40）"
# V0.0.41（手册 9.2 节 #7 / 10.2 节 #4）：「新建模板」按钮 / 弹窗的两条判定名
FAIL_TPLNEW = "主界面·模板「新建」按钮就位且随语言刷新（V0.0.41）"
FAIL_TPLDLG = "主界面·「新建模板」弹窗可开、起点已填充、可关（V0.0.41）"
# V0.0.42（手册 10.2 节 #12）：根名方案 C 的两条判定名
FAIL_ROOTRENAME = "主界面·根名即树根：改名后摘要与树区同步（V0.0.42）"
FAIL_ROOTBLANK = "主界面·根名即树根：清空即不建根（V0.0.42）"
# V0.0.43（UI 定版差集 G / H / F）：四条判定名
FAIL_GROUP3 = "主界面·工具栏语义分组：按钮各归其组（V0.0.43 · G）"
FAIL_INSPMODE = "主界面·检视器属性⇄源码：可切换且源码为同源 JSON（V0.0.43 · H）"
FAIL_BATCHGEST = "主界面·多选手势与批量条（Ctrl/Shift/Esc/Ctrl+A）（V0.0.43 · F）"
FAIL_BATCHDEL = "主界面·批量删除只作用于最外层祖先（V0.0.43 · F）"
# V0.0.51@r11：模板行 ⋮ 常驻入口的判定名（⋮ 由 JS 动态创建 ⇒ 7aj⑤ 的静态扫描扫不到）
FAIL_TPLMORE = "主界面·模板行 ⋮ 常驻入口（V0.0.51@r11）"
# V0.0.52：树行图标由 emoji 归一为 `.ic` mask 的判定名
FAIL_TREEICON = "主界面·树行图标走 mask（V0.0.52）"


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

    def test_no_container_returns_none(self):
        # §P2-12：已去掉宽松兜底 —— 取不到锚定容器即判「未取到结果」（宁可 FAIL，不捞源码字面量）
        self.assertIsNone(bs.parse_metrics("junk RESULT a=1 | b=2\n"))

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
        self.assertEqual(len(results), 32,
                         "verify_metrics 应产生 32 项判定"
                         "（24 + V0.0.43 的 G/H/F 四条 + V0.0.51@r11 的 ⋮ 一条"
                         " + V0.2.2 的「右键菜单可关闭」一条 + V0.2.3 的「提示不抢焦点」一条）")

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
        self.assertEqual(len(results), 24, "不期望模板时不应产生模板判定项（V0.0.41 / V0.0.42 / V0.0.43 的项与模板库无关，仍在）")
        self.assertNotIn(TPL_CHECK, [n for _o, n, _x in results])

    def test_v042_root_rename_not_propagated_fails_exactly(self):
        """V0.0.42 回归：改名未贯通到摘要（摘要保持原样）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, rootSumAfter=NORMAL["rootSumBefore"])
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_ROOTRENAME])

    def test_v042_root_blank_not_back_to_noroot_fails_exactly(self):
        """V0.0.42 回归：清空后仍显示旧根名（未回到「不建根」）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, rootSumBlank="Target X · Root QmRootX · Dry run",
                       rootNameBlank="QmRootX")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_ROOTBLANK])

    def test_6d_business_templates_in_builtin_fails_exactly(self):
        """6D 契约：内置只允许 P0。业务模板被放回 templates/（17 行）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, tplRows="17")
        self.assertEqual(failed_names(run_metrics(metrics)), [TPL_CHECK])

    def test_low_row_count_fails(self):
        metrics = dict(NORMAL, idxRows="1")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_LANG])

    def test_c1_skin_picker_i18n_regression_fails_exactly(self):
        """C-P2-1 回归：换语言后皮肤网格未重建（文案前后一致）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, skinZh="Paper")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·皮肤网格随语言刷新"])

    def test_c3_5_illegal_skin_adopted_fails_exactly(self):
        """C-P3-5 回归：非法皮肤名被直接采用（href 指向不存在的 .css）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, badSkinHref="./css/skins/not-a-real-skin.css")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·非法皮肤回落出厂默认（C-P3-5）"])

    def test_d3_2_arrow_stale_color_fails_exactly(self):
        """D-P3-2 回归：顶栏图标色未随皮肤变量（仍是旧版烘死的 #6d7278）→ 恰好那项 FAIL。

        V0.0.40 起落点由「下拉箭头伪元素」迁移为「图标按钮 #btnLang 的 color」。
        """
        metrics = dict(NORMAL, arrowColor="rgb(109, 114, 120)")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·顶栏图标随 --qm-text-dim（D-P3-2）"])

    def test_c3_1_scroll_reset_fails_exactly(self):
        """C-P3-1 回归：重建后滚动位置回顶（scrollTop 40 → 0）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, scrollAfter="0")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·重建后滚动位置保持（C-P3-1）"])

    def test_skin_order_regression_fails_exactly(self):
        """V0.0.39 回归：网格顺序与按 swatch[0] 明度复算的期望序列不符 → 恰好那项 FAIL。

        这是 §十三.4「swatch 与 CSS 无绑定」的**页面层**回归位：swatch 在页面上唯一
        可见的效果就是排序，把顺序锁死即等于把 swatch 数据锁死。V0.0.40 起落点由
        下拉 options 迁移为 `#skinGrid` 的 `.sw-card[data-file]` 顺序。
        """
        wrong = ",".join(reversed(NORMAL["skinOrder"].split(",")))
        metrics = dict(NORMAL, skinOrder=wrong)
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·皮肤网格按背景明度排序（V0.0.39）"])

    def test_skin_count_regression_fails_exactly(self):
        """V0.0.39 回归：皮肤少注册一款（如漏掉 swatch 字段被过滤）→ 恰好那项 FAIL。"""
        parts = NORMAL["skinOrder"].split(",")
        metrics = dict(NORMAL, skinOrder=",".join(parts[:-1]), skinCount=str(len(parts) - 1))
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·皮肤网格按背景明度排序（V0.0.39）"])

    def test_c3_1_no_rebuild_is_not_vacuous_pass(self):
        """C-P3-1：未真正重建（reRendered=0）时，即使 scrollTop 相等也不得判定通过。"""
        metrics = dict(NORMAL, reRendered="0")
        self.assertEqual(failed_names(run_metrics(metrics)),
                         ["主界面·重建后滚动位置保持（C-P3-1）"])

    def test_c3_2_descendant_drop_misadvertised_fails_exactly(self):
        """C-P3-2 回归：子孙落点仍给「可放下」假暗示（dragDesc=0）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, dragDesc="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_DRAG])

    def test_c3_2_over_rejection_fails_exactly(self):
        """C-P3-2：合法落点被误拒（dragOk=0）也要 FAIL —— 防「一律拒绝」式假修复。"""
        metrics = dict(NORMAL, dragOk="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_DRAG])

    def test_c3_2_missing_metrics_fail_explicitly(self):
        """C-P3-2：探针找不到落点（-1）时须明确 FAIL，不静默略过。"""
        metrics = dict(NORMAL, dragSelf="-1", dragDesc="-1", dragOk="-1")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_DRAG])

    def test_c3_3_child_span_strips_highlight_fails_exactly(self):
        """C-P3-3 回归：划过行内子元素即摘高亮（dlChild=0）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, dlChild="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_DL])

    def test_c3_3_never_stripping_fails_exactly(self):
        """C-P3-3：真离开却不摘高亮（dlOut=0）也要 FAIL —— 防「干脆永不摘」式假修复。"""
        metrics = dict(NORMAL, dlOut="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_DL])

    def test_c3_4_unbounded_toasts_fail_exactly(self):
        """C-P3-4 回归：提示条无上限堆积（实存 40 条 > 上限）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, toastN="40")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TOAST])

    def test_toast_cap_read_from_source(self):
        """C-P3-4：上限须从 `toast.js` 读（单一事实源），而非硬编码在判定里。"""
        self.assertGreater(bs.toast_cap(), 0)
        self.assertEqual(NORMAL["toastN"], str(bs.toast_cap()))

    def test_v0040_target_pick_button_missing_fails_exactly(self):
        """V0.0.40 回归：目标位置「选择…」按钮缺失（如误删 `#btnPickTarget`）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, pickTargetBtn="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_PICK])

    def test_v0040_target_pick_text_frozen_fails_exactly(self):
        """V0.0.40 回归：按钮文案未随语言刷新 → 恰好那项 FAIL（说明未走 i18n 取词）。
        V0.0.50：负控改为「zh := 本基线的 en 值」，不再钉死某个英文字面量 ——
        后者与产品文案耦合，文案一改（I 组去文字即为一例）负控就会**静默退化成正控**。"""
        metrics = dict(NORMAL, pickTargetZh=NORMAL["pickTargetEn"])
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_PICK])

    def test_v0041_new_template_button_missing_fails_exactly(self):
        """V0.0.41 回归：模板「新建」按钮缺失（如误删 `#btnNewTemplate`）→ 恰好那项 FAIL。"""
        metrics = dict(NORMAL, tplNewBtn="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TPLNEW])

    def test_v0041_new_template_text_frozen_fails_exactly(self):
        """V0.0.41 回归：按钮文案未随语言刷新 → 恰好那项 FAIL（说明未走 i18n 取词）。
        V0.0.50：同 pickTarget —— 负控改用本基线的 en 值，避免与产品文案耦合。"""
        metrics = dict(NORMAL, tplNewZh=NORMAL["tplNewEn"])
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TPLNEW])

    def test_v0041_new_template_dialog_regression_fails_exactly(self):
        """V0.0.41 回归：弹窗没开 / 起点下拉为空 / 关不掉 —— 三种各恰好那项 FAIL。

        这条断言是本轮**唯一**的运行时交互实证（其余只证「元素在位 + 取词」）：
        它同时覆盖 `newTemplateFlow` 的 async 流程（await 列表 → open）与 `[data-close]` 接线。
        """
        for bad in (dict(NORMAL, tplNewOpen="0"),
                    dict(NORMAL, tplNewBaseN="0"),
                    dict(NORMAL, tplNewBaseText=""),
                    dict(NORMAL, tplNewClosing="1"),
                    dict(NORMAL, tplNewClosed="0")):
            with self.subTest(metrics=bad):
                self.assertEqual(failed_names(run_metrics(bad)), [FAIL_TPLDLG])

    # ---- V0.0.43 · UI 定版差集 G / H / F 的反向验证 ----

    def test_v043_group_map_off_fails_exactly(self):
        """G 回归：某颗按钮被移出原分组（归属序列变了）→ 恰好 G 一项 FAIL。"""
        metrics = dict(NORMAL, gMap="00000122")     # 「一键生成」被划入保存组（未独立成组）
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_GROUP3])

    def test_v043_group_count_or_label_off_fails_exactly(self):
        """G 回归：只剩两组 / 某组丢了 aria-label（读屏还原成一长串按钮）→ 恰好 G 一项 FAIL。"""
        for bad in (dict(NORMAL, gGroups="2"), dict(NORMAL, gLabels="2")):
            with self.subTest(metrics=bad):
                self.assertEqual(failed_names(run_metrics(bad)), [FAIL_GROUP3])

    def test_v043_inspector_source_not_json_fails_exactly(self):
        """H 回归：源码栏不是可解析 JSON（退化成随手拼的字符串）→ 恰好 H 一项 FAIL。"""
        metrics = dict(NORMAL, hJson="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_INSPMODE])

    def test_v043_inspector_source_lacks_child_fails_exactly(self):
        """H 回归：源码栏是 JSON 但不含实际子节点名（序列化未贯通）→ 恰好 H 一项 FAIL。"""
        metrics = dict(NORMAL, hHasChild="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_INSPMODE])

    def test_v043_inspector_not_switched_back_fails_exactly(self):
        """H 回归：切到源码后切不回属性面板（分段控件单向）→ 恰好 H 一项 FAIL。"""
        metrics = dict(NORMAL, hBack="1")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_INSPMODE])

    def test_v043_batch_gesture_break_fails_exactly(self):
        """F 回归：Shift 范围选择只选中 2 行（未按可视序取连续段）→ 恰好 F 手势一项 FAIL。"""
        metrics = dict(NORMAL, fShift="2")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHGEST])

    def test_v043_batch_all_include_root_fails_exactly(self):
        """F：Ctrl+A 若把根也选进去（fAll 不再等于可见行数 - 1）→ 恰好 F 手势一项 FAIL。"""
        metrics = dict(NORMAL, fAll=NORMAL["fVisible"])     # 6 != 6-1
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHGEST])

    def test_v043_batch_esc_not_clearing_fails_exactly(self):
        """F 回归：Esc 未取消多选（集合残留 / 批量条不收）→ 恰好 F 手势一项 FAIL。"""
        metrics = dict(NORMAL, fMultiOff="2")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHGEST])

    def test_v043_batch_dedup_line_count_is_not_the_criterion(self):
        """为何判据是「对话框报的顶层项数」而非「实删行数」——本用例把这点钉死。

        逐个删除时，子节点在父被摘走后已随之消失，第二次 `removeNode` 自然返回 false，
        最终行数**恰好与只删父相同**（故 `fBefore - fAfter == fDropN` 恒成立，不具判别力）。
        本用例的指标里行数口径**完全自洽**（6 - 3 == 3），只有对话框报 2 项 ——
        仍须**恰好**在批量删除一项 FAIL，证明判定用的确是对话框口径。
        """
        metrics = dict(NORMAL, fConfirmMsg="Delete the 2 selected nodes? (undoable)")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHDEL])

    def test_v043_batch_dedup_reports_two_fails_exactly(self):
        """F 回归：父子同选时对话框报 2 项（未去重）→ 恰好批量删除一项 FAIL。"""
        metrics = dict(NORMAL, fConfirmMsg="Delete the 2 selected nodes and all their children? (undoable)")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHDEL])

    def test_v043_batch_cancel_must_leave_tree_untouched(self):
        """F 回归：取消路径没生效（树被动了 / 批量条未收）→ 各恰好批量删除一项 FAIL。"""
        for bad in (dict(NORMAL, fCancelKept="0"), dict(NORMAL, fBarClear="0")):
            with self.subTest(metrics=bad):
                self.assertEqual(failed_names(run_metrics(bad)), [FAIL_BATCHDEL])

    def test_v043_batch_over_deletion_fails_exactly(self):
        """F 回归：删多了（实删行数 ≠ 父行子树行数）→ 恰好批量删除一项 FAIL。"""
        metrics = dict(NORMAL, fAfter="0")      # 6 - 0 = 6 != 3
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_BATCHDEL])

    def test_v043_probe_metrics_present(self):
        """V0.0.43：探针须真的写出这 29 个新指标键（否则判定读到空值会静默 FAIL）。

        与 `verify.py` 的静态 token 锚定互补：那里保证「探针源码里有这些赋值」，
        这里保证「基线把每一个都当成了判定输入」—— 少一个就是判据缺口。
        """
        need = ("gGroups", "gLabels", "gMap",
                "hSeg", "hPropHidden", "hSrcShown", "hJson", "hHasChild", "hBack", "hPref",
                "fBar0", "fMulti", "fBarOn", "fInfo", "fAgg", "fBarOff", "fMultiOff",
                "fShift", "fVisible", "fAll", "fAllBar", "fBarOff2", "fDedupSet",
                "fConfirmMsg", "fDropN", "fBefore", "fAfter", "fCancelKept", "fBarClear")
        for key in need:
            self.assertIn(key, NORMAL, f"基线缺少 V0.0.43 指标 {key}")

    def test_v045_probe_metrics_present(self):
        """V0.0.45：探针须真的写出 2 个柔光层指标键（否则「柔光层生效」判定读到空值会静默 FAIL）。

        与 `verify.py` 的 7d-6 静态锚定互补：那里保证「三页无 data-soft / soft.css 无前缀与
        形态字面量 / 两处实测补丁在位」，这里保证「基线把这两个**运行时**量都当成了判定输入」——
        静态守卫证不了「这份 CSS 真的被加载且特异性足以作用到 #sidebar」，只有它能。
        """
        for key in ("softShadow", "softRef"):
            self.assertIn(key, NORMAL, f"基线缺少 V0.0.45 指标 {key}")

    def test_v0051r11_more_entry_missing_fails_exactly(self):
        """V0.0.51@r11：模板行 ⋮ 缺失 → 恰好那项 FAIL。

        这是 7aj⑤b 的**运行期**对照 —— 静态判据管「源码里有没有」，它管「点了有没有用」。
        """
        metrics = dict(NORMAL, tplMoreThere="0")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TPLMORE])

    def test_v0051r11_more_menu_rewired_fails_exactly(self):
        """V0.0.51@r11：⋮ 绕开同一菜单（点开后项数不是 5）→ 恰好那项 FAIL。

        「复用同一菜单、不另造一套」是本批采纳「丙-1」的核心不变量；静态侧由
        `ctxMenu.showAt` 恰 1 处把关（verify 7aj⑤b），运行期由本条把关。
        """
        metrics = dict(NORMAL, tplMoreN="3")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TPLMORE])

    def test_v0051r11_probe_metrics_present(self):
        """V0.0.51@r11：探针须真的写出 3 个 ⋮ 指标键（否则判定读到空值会**静默 FAIL**）。

        与 `verify.py` 的 7aj⑤b 静态判据互补：那里保证「产出方源码里有标记与接线」，
        这里保证「基线把这 3 个运行时量都当成了判定输入」—— 少一个就是判据缺口。
        """
        for key in ("tplMoreThere", "tplMoreN", "tplMoreMenu"):
            self.assertIn(key, NORMAL, f"基线缺少 V0.0.51@r11 指标 {key}")


class TreeIconMaskTests(unittest.TestCase):
    """V0.0.52：树行图标归一（emoji → `.ic` mask）的判定必须**两个条件都查**。

    只查类名 → 「字形没删干净、只是又挂了个 mask 类」照样判过（旧实现删除不彻底）；
    只查文字长度 → 「把 emoji 换成了一串空白」也判过。两条各来一个反例。
    """

    def test_baseline_ok(self):
        self.assertEqual(failed_names(run_metrics(NORMAL)), [])

    def test_flags_missing_mask_class(self):
        """类名没挂形状（或仍是旧的裸 `tree-icon`）→ 恰该项 FAIL。"""
        metrics = dict(NORMAL, treeIconCls="tree-icon")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TREEICON])

    def test_flags_leftover_glyph(self):
        """mask 类挂上了、但彩色字形**没删干净** → 仍须 FAIL（类名查不出这一条）。"""
        metrics = dict(NORMAL, treeIconTxtLen="1")
        self.assertEqual(failed_names(run_metrics(metrics)), [FAIL_TREEICON])

    def test_v0052_probe_metrics_present(self):
        """探针须真的写出这 2 个指标键，否则判定读到空值会**静默 FAIL**（判据缺口）。"""
        for key in ("treeIconCls", "treeIconTxtLen"):
            self.assertIn(key, NORMAL, f"基线缺少 V0.0.52 指标 {key}")


class FirstIntTests(unittest.TestCase):
    """V0.0.43 · F：`first_int` 是批量删除判定的**解耦层**（只抽数字，不比对整句）。"""

    def test_extracts_leading_number(self):
        self.assertEqual(
            bs.first_int("Delete the 1 selected nodes and all their children? (undoable)"), 1)
        self.assertEqual(bs.first_int("确认删除选中的 1 个节点及其全部子节点？（可用撤销恢复）"), 1)

    def test_default_when_no_digit(self):
        self.assertEqual(bs.first_int("no digits here", default=-1), -1)
        self.assertEqual(bs.first_int(""), -1)
        self.assertEqual(bs.first_int(None), -1)

    def test_returns_first_of_several(self):
        self.assertEqual(bs.first_int("3 of 7 items"), 3)


class SandboxBaseTests(unittest.TestCase):
    """§P2-10：沙盒父目录不再硬编码绝对盘符路径。"""

    def test_env_var_wins(self):
        old = os.environ.get("QM_SANDBOX")
        os.environ["QM_SANDBOX"] = "X:/my/sandbox"
        try:
            self.assertEqual(bs.sandbox_base(), Path("X:/my/sandbox"))
        finally:
            if old is None:
                os.environ.pop("QM_SANDBOX", None)
            else:
                os.environ["QM_SANDBOX"] = old

    def test_default_follows_project_root(self):
        old = os.environ.pop("QM_SANDBOX", None)
        try:
            self.assertEqual(bs.sandbox_base(), bs.PROJECT_ROOT.parent.parent / "_sandbox")
        finally:
            if old is not None:
                os.environ["QM_SANDBOX"] = old


class BrowserDrivableTests(unittest.TestCase):
    """§P2-11：不可驱动 / 不存在的前置探测须返回「不可驱动 + 原因」。"""

    def test_missing_exe_is_not_drivable(self):
        ok, why = bs.browser_drivable("Z:/definitely/not/here/quark.exe", timeout=5)
        self.assertFalse(ok)
        self.assertTrue(why)


class ProbeSelfReportTests(unittest.TestCase):
    """§P2-13：正面控制必须真的写在探针页里，否则「日志通道可用」永远 FAIL。"""

    def test_probe_emits_self_report_line(self):
        self.assertIn(bs.SELF_REPORT, bs.PROBE_HTML)


if __name__ == "__main__":
    unittest.main()
