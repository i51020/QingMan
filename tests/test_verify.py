"""青蔓 QingMan · verify 工具层判定单元测试（§P0-2 T2 / §P2 第 19、20 项）。

覆盖 `tools/verify.py` 里**承担判定职责**的纯函数 —— 按 §P2 第 19 项的裁定：
「凡承担判定职责的工具函数，必须有单元测试」。当前覆盖「托管 node 取最新」这一组
（§P2 第 20 项 / 审查报告 §P2-2：旧实现硬编码 `versions/22.22.2-6/node.exe`，
托管运行时一升级即失效）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import verify  # noqa: E402


def rmtree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


class NodeVersionKeyTests(unittest.TestCase):

    def test_parses_digits(self):
        self.assertEqual(verify.node_version_key("22.22.2-6"), (22, 22, 2, 6))
        self.assertEqual(verify.node_version_key("24.21.0"), (24, 21, 0))

    def test_ordered_by_number_not_lexicographically(self):
        # 字典序会把 "9" 排在 "24" 之后 —— 必须按数字比较
        self.assertGreater(verify.node_version_key("24.21.0"),
                           verify.node_version_key("9.11.2"))

    def test_non_numeric_yields_empty(self):
        self.assertEqual(verify.node_version_key("current"), ())
        self.assertEqual(verify.node_version_key(".locks"), ())


class RawColorHitsTests(unittest.TestCase):
    """D-P2-1：「组件 CSS 无裸色值」判据须覆盖 rgb()/rgba()/hsl()/hsla()，不能只认 #hex。"""

    def test_detects_hex(self):
        self.assertIn("#1e2732", verify.raw_color_hits("color: #1e2732;"))

    def test_detects_rgb_and_rgba(self):
        self.assertTrue(verify.raw_color_hits("box-shadow: inset 1px 1px 3px rgba(0, 0, 0, .25);"))
        self.assertTrue(verify.raw_color_hits("background: rgb(1 2 3);"))

    def test_detects_hsl(self):
        self.assertTrue(verify.raw_color_hits("color: hsl(120 50% 50%);"))

    def test_ignores_var_reference(self):
        self.assertEqual(
            verify.raw_color_hits("color: var(--qm-text); box-shadow: var(--qm-inset);"), [])


class RawFontSizeHitsTests(unittest.TestCase):
    """§P0-3 L4「禁止裸尺寸」的**字号档**：判据须**白名单式** —— 取值必须以 `var(--qm-` 打头。

    只否掉 px 会让 `1rem` / `inherit` 溜过去（"不是 px"≠"走了 token"）。
    """

    def test_detects_px_literal(self):
        self.assertIn("font-size:12px", verify.raw_font_size_hits(".a { font-size: 12px; }"))

    def test_detects_non_px_literal(self):
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: 1rem; }"))
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: inherit; }"))

    def test_detects_without_trailing_semicolon(self):
        self.assertTrue(verify.raw_font_size_hits(".a { font-size: 13px }"))

    def test_ignores_token_reference(self):
        self.assertEqual(
            verify.raw_font_size_hits(".a { font-size: var(--qm-fs-md); }"), [])
        self.assertEqual(
            verify.raw_font_size_hits(".a{font-size:var(--qm-fs-3xl)}"), [])

    def test_ignores_other_size_properties(self):
        # 本条**只管字号**：间距 / 圆角的裸值不在判据内（已知缺口，见 §P2 第 44 项）
        self.assertEqual(
            verify.raw_font_size_hits(".a { padding: 6px 10px; border-radius: 4px; }"), [])


class SkinTopLevelViolationsTests(unittest.TestCase):
    """§P0-3 L5 / §P2 第 45 项：皮肤文件**顶层只许 `:root` + `--qm-*` 声明**。

    判据同样是**白名单式** —— 选择器须恰为 `:root`、声明名须以 `--qm-` 打头。
    发现路径：7c-1 反向验证的**负向对照 N6** —— 往皮肤写
    `.rev-probe { font-size: var(--qm-fs-md); }` 竟**零新增红项**，证明
    「用 `var()` 去写组件样式」无人看守。
    """

    def test_accepts_canonical_skin(self):
        self.assertEqual(verify.skin_toplevel_violations(
            ":root { --qm-bg: #fff; --qm-text: #111; }"), [])

    def test_accepts_last_declaration_without_semicolon(self):
        self.assertEqual(verify.skin_toplevel_violations(":root { --qm-bg: #fff }"), [])

    def test_flags_component_selector(self):
        # 这正是 N6 注入的形态：合法 :root 之后跟一段组件样式
        hits = verify.skin_toplevel_violations(
            ":root { --qm-bg: #fff; }\n.rev-probe { font-size: var(--qm-fs-md); }")
        self.assertTrue(hits)
        self.assertTrue(any(h.startswith("选择器:") for h in hits))

    def test_flags_non_variable_declaration(self):
        hits = verify.skin_toplevel_violations(":root { color: var(--qm-text); }")
        self.assertTrue(any(h.startswith("非变量声明:") for h in hits))

    def test_flags_selector_not_exactly_root(self):
        self.assertTrue(verify.skin_toplevel_violations("html { --qm-bg: #fff; }"))
        self.assertTrue(verify.skin_toplevel_violations(":root, html { --qm-bg: #fff; }"))
        self.assertTrue(verify.skin_toplevel_violations(
            "[data-qm-skin=dark] { --qm-bg: #000; }"))
        self.assertTrue(verify.skin_toplevel_violations(
            ".skin-dark .btn { --qm-bg: #000; }"))

    def test_flags_at_rule_and_nesting(self):
        self.assertTrue(verify.skin_toplevel_violations(
            "@media (prefers-color-scheme: dark) { :root { --qm-bg: #000; } }"))

    def test_flags_toplevel_declaration_outside_block(self):
        self.assertTrue(verify.skin_toplevel_violations("--qm-bg: #fff;"))

    def test_multiple_violations_are_all_reported(self):
        hits = verify.skin_toplevel_violations(
            ":root { --qm-bg: #fff; color: red; }\n.b { --qm-text: #000; }")
        # 恰 2 处：① `:root` 块里混了一条非变量声明；② 第二块选择器不是 `:root`。
        # （第二块里的 `--qm-text` 本身合法 —— 判据只否选择器，不否变量名；变量名是否越界归 7d-1。）
        self.assertEqual(len(hits), 2)


class TemplateRowMoreViolationsTests(unittest.TestCase):
    """V0.0.51@r11：模板行 ⋮ 常驻入口的接线判据（挂在 7aj 的 ⑤b 上）。

    **判据为何存在**：7aj ⑤ 只扫 `src/web/index.html` 的**静态**标记，而 ⋮ 由
    `modules/templates.js` **动态创建** ⇒ 静态扫描天然扫不到，等于给「JS 造出来的图标
    按钮」开了一条无守卫通道。故改判**产出方源码**，并把「⋮ 与右键同源」一并机器化。

    这里逐条钉住四个子判据，防「判据自己悄悄失效」—— 同 `skin_toplevel_violations`
    的做法（§三.85：自查类的判据物须与被查对象不同一处）。
    """

    # 合规样例：定义 1 处 + 调用 2 处（右键 / ⋮），showAt 恰 1 处，三样标记齐备
    GOOD_JS = (
        "function openTemplateContextMenu(item, x, y) {\n"
        "  ctxMenu.showAt(x, y, []);\n"
        "}\n"
        "li.addEventListener('contextmenu',"
        " (e) => openTemplateContextMenu(item, e.clientX, e.clientY));\n"
        "more.addEventListener('click', () => {\n"
        "  const box = more.getBoundingClientRect();\n"
        "  openTemplateContextMenu(item, box.left, box.bottom);\n"
        "});\n"
        "more.className = 'btn btn-ghost btn-mini btn-ic tpl-more';\n"
        "moreIc.className = 'ic ic-more';\n"
        "more.setAttribute('aria-label', t('template.more'));\n"
        "more.title = t('template.moreTip');\n"
    )
    GOOD_LAYOUT = ".tpl-row .tpl-more { opacity: .45; }\n"
    GOOD_SOFT = "html .tpl-row .tpl-more { background: transparent; }\n"

    def _run(self, js=None, layout=None, soft=None):
        return verify.template_row_more_violations(
            self.GOOD_JS if js is None else js,
            self.GOOD_LAYOUT if layout is None else layout,
            self.GOOD_SOFT if soft is None else soft)

    def test_accepts_canonical_wiring(self):
        self.assertEqual(self._run(), [])

    def test_flags_missing_marker(self):
        hits = self._run(js=self.GOOD_JS.replace("tpl-more", "tpl-x"))
        self.assertTrue(any("类名" in h for h in hits), hits)

    def test_flags_missing_icon(self):
        hits = self._run(js=self.GOOD_JS.replace("ic-more", "ic-x"))
        self.assertTrue(any("图标" in h for h in hits), hits)

    def test_flags_missing_accessible_name(self):
        # 只删 `aria-label` 那句，**保留** tooltip —— 这正是引号锚定要挡的情形：
        # `template.more` 是 `template.moreTip` 的子串，裸查会放它过去。
        hits = self._run(js=self.GOOD_JS.replace(
            "more.setAttribute('aria-label', t('template.more'));\n", ""))
        self.assertTrue(any("可访问名" in h for h in hits), hits)

    def test_flags_tooltip_only(self):
        # 极端情形：整份 JS 里只剩 `template.moreTip`，没有任何 `'template.more'`
        hits = self._run(js=self.GOOD_JS.replace(
            "more.setAttribute('aria-label', t('template.more'));\n", ""))
        self.assertEqual(sum(1 for h in hits if "可访问名" in h), 1, hits)

    def test_flags_single_call_site(self):
        # 抽掉 ⋮ 那处调用 ⇒ 只剩右键盘路 ⇒ 判「⋮ 可能绕开了同一份菜单」
        hits = self._run(js=self.GOOD_JS.replace(
            "  openTemplateContextMenu(item, box.left, box.bottom);\n", ""))
        self.assertTrue(any("调用点" in h for h in hits), hits)

    def test_flags_second_menu(self):
        # 给 ⋮ 另造一套菜单 ⇒ `ctxMenu.showAt` 变 2 处
        hits = self._run(js=self.GOOD_JS + "ctxMenu.showAt(1, 2, []);\n")
        self.assertTrue(any("showAt" in h for h in hits), hits)

    def test_flags_missing_css_pairing(self):
        self.assertTrue(any("layout.css" in h for h in self._run(layout="")))
        self.assertTrue(any("soft.css" in h for h in self._run(soft="")))

    def test_definition_line_is_not_counted_as_call(self):
        # 负向对照：定义行本身含 `openTemplateContextMenu(`。若判据不减去这 1 处基准，
        # 「只有 1 个调用点」也会算成 2 ⇒ 漏报。此例只有右键盘路 ⇒ 必须命中。
        only_ctxmenu = (
            "function openTemplateContextMenu(item, x, y) {\n"
            "  ctxMenu.showAt(x, y, []);\n"
            "}\n"
            "li.oncontextmenu = () => openTemplateContextMenu(item, 1, 2);\n"
            "more.className = 'tpl-more';\n"
            "ic.className = 'ic-more';\n"
            "more.setAttribute('aria-label', t('template.more'));\n")
        hits = self._run(js=only_ctxmenu)
        self.assertTrue(any("调用点" in h for h in hits), hits)


class LocaleDictKeysTests(unittest.TestCase):
    """V0.0.51@r12：取词表「键集合」的唯一口径 `locale_dict_keys()`（7b-2 / 7b-3 共用）。

    **判据为何存在**：旧 7b-3「中英取词键对齐」用带 `^...$` 锚点且未加 `re.M` 的整串
    正则去匹配多行字典 ⇒ 两侧**永远各得 0 个键**，本项自设立起**恒 PASS**（一条不可能
    失败的守卫）；旧 7b-2 则拿「任何带点的引号串」当键，把**值** `V0.0.51` 也算了进去。
    故这里把新口径钉死：**按键位取、先剥注释、值不参与**。
    """

    # 一屏真实形态：正常条目 + 值里带点号的条目 + 注释里的「键」 + 正文里的点号串
    SAMPLE = (
        "/*\n"
        " * LOCALE        语言标签（必须与文件名一致）\n"
        " * 例：'sidebar.title' 曾在此处被提及\n"
        " */\n"
        "export default {\n"
        "  'sidebar.title': '模板工作区',\n"
        "  'help.versionFallback': 'V0.0.51',\n"
        "  'shortcut.fileName': 'QingMan.lnk',\n"
        "  'sample.readme': 'README.md',\n"
        "  'template.stats': '{dirs} 目录 · {files} 文件',\n"
        "};\n"
    )

    def test_takes_keys_not_values(self):
        """`'help.versionFallback': 'V0.0.51'` 只能产出**键**；值 `V0.0.51` 不得被当成键。

        这正是旧判据的幻影键（取词表因此虚记 442 键，实为 441）。
        """
        keys = verify.locale_dict_keys(self.SAMPLE)
        self.assertIn("help.versionFallback", keys)
        self.assertNotIn("V0.0.51", keys)

    def test_ignores_dotted_value_strings(self):
        """值是 `QingMan.lnk` / `README.md` 这类带点串时，同样不得被当成键。

        旧判据里这两个幻影键会让 en 侧凭空多出 2 个键。
        """
        keys = verify.locale_dict_keys(self.SAMPLE)
        self.assertNotIn("QingMan.lnk", keys)
        self.assertNotIn("README.md", keys)

    def test_ignores_commented_out_entries(self):
        """注释里出现的 `'sidebar.title'` 不算条目 —— 否则「注释里提一句」就能骗过闭包。"""
        text = self.SAMPLE.replace("  'sidebar.title': '模板工作区',\n", "")
        keys = verify.locale_dict_keys(text)
        self.assertNotIn("sidebar.title", keys)
        self.assertIn("shortcut.fileName", keys)   # 别处的真条目仍在

    def test_collects_all_keys_across_lines(self):
        """多行字典要**逐行全收**（旧判据正是死在「整串才匹配」上，收到 0 个）。"""
        keys = verify.locale_dict_keys(self.SAMPLE)
        self.assertEqual(
            keys,
            {"sidebar.title", "help.versionFallback", "shortcut.fileName",
             "sample.readme", "template.stats"})

    def test_empty_text_yields_empty_set(self):
        self.assertEqual(verify.locale_dict_keys(""), set())

    def test_matches_real_locale_file(self):
        """与**盘上真实取词表**对齐：条目数、真键在、幻影键不在。"""
        zh = (Path(verify.PROJECT_ROOT) / "src/web/locales/zh-CN.js").read_text(encoding="utf-8")
        keys = verify.locale_dict_keys(zh)
        self.assertIn("sidebar.title", keys)
        self.assertIn("help.quickStart.3", keys)
        self.assertNotIn("V0.0.51", keys)
        self.assertNotIn("sidebar.noteLine1", keys)   # V0.0.51@r12 已删（解说句归帮助页）
        # 条目数按盘上派生，不写死：两侧同源时才谈得上「中英键集一致」
        en = (Path(verify.PROJECT_ROOT) / "src/web/locales/en-US.js").read_text(encoding="utf-8")
        self.assertEqual(keys, verify.locale_dict_keys(en))


class IterManagedNodesTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="qm_verify_nodes_"))

    def tearDown(self):
        rmtree(self.root)

    def _mk(self, name: str, *, with_exe: bool = True) -> None:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        if with_exe:
            (d / "node.exe").write_bytes(b"stub")

    def test_picks_newest_first(self):
        for name in ("22.22.2-6", "24.21.0", "23.11.1"):
            self._mk(name)
        got = [p.parent.name for p in verify.iter_managed_nodes(self.root)]
        self.assertEqual(got, ["24.21.0", "23.11.1", "22.22.2-6"])

    def test_ignores_dirs_without_node_exe(self):
        self._mk("24.21.0")
        self._mk("current", with_exe=False)
        (self.root / ".locks").mkdir()
        got = [p.parent.name for p in verify.iter_managed_nodes(self.root)]
        self.assertEqual(got, ["24.21.0"])

    def test_missing_base_returns_empty(self):
        self.assertEqual(verify.iter_managed_nodes(self.root / "nope"), [])

    def test_empty_base_returns_empty(self):
        self.assertEqual(verify.iter_managed_nodes(self.root), [])


class FindNodeTests(unittest.TestCase):

    def test_returns_existing_node_or_none(self):
        node = verify.find_node()
        if node is None:
            self.skipTest("本机无 node —— find_node 返回 None 属正确降级")
        self.assertTrue(Path(node).is_file(), f"find_node 返回了不存在的路径：{node}")


class ArgParsingTests(unittest.TestCase):
    """§P2-16：多余位置参数须报错，不得静默忽略。"""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(_TOOLS / "verify.py"), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_extra_positional_arg_rejected(self):
        proc = self._run("root1", "root2")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("多余的参数", proc.stdout)

    def test_single_arg_not_flagged_as_extra(self):
        # 只传一个根目录（不存在）→ 应走「目录不存在」，绝非「多余的参数」
        proc = self._run(str(_TOOLS / "nonexistent_root_xyz"))
        self.assertNotIn("多余的参数", proc.stdout)


if __name__ == "__main__":
    unittest.main()
