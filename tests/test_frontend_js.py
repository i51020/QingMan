"""青蔓 QingMan · 前端核心 Node 驱动测试（src 审查第四档 · 批 4B / 4C）。

`modules/tree-model.js`、`core/*.js` 与 `ui/tree-view.js`（顶层只 import + 函数声明）
均**无顶层 DOM 依赖**，可在 Node 中直接作 ESM 导入。本模块把一段断言脚本写成临时 `.mjs`，
交给托管 `node` 执行，读回 `RESULT <json>` 逐项判定。

覆盖批 4B：B-P3-1（网络失败归一）/ B-P3-3（renameNode 自校验）/ B-P3-4（toPlainTree
重名告警）/ B-P3-5（查询族深树不爆栈）/ B-P3-6（bus.off 后不再触发）。
覆盖批 4C：C-P3-3（`leftRow`「算不算离开」判定，含 relatedTarget 为 null 的坐标兜底）。
B-P3-2（saveNow 在途保护）与 C-P3-2/C-P3-4（拖拽落点、提示条上限）依赖真实页面，
由 `tools/browser_smoke.py` + 静态守卫覆盖。
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
_ROOT = _HERE.parents[1]
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _ROOT / "src")
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

HARNESS = r"""
const SRC = process.env.QM_JS_SRC;
const results = [];
const ok = (name, pass, extra = '') => results.push({ name, pass: !!pass, extra: String(extra) });

const tm = await import(SRC + '/modules/tree-model.js');

/* ---------- B-P3-5 深树不爆栈（20000 == MAX_EDITOR_NODES 上限；旧递归版在此必 RangeError） ---------- */
{
  const root = tm.createDir('r');
  let cur = root;
  for (let i = 0; i < 20000; i++) {
    const d = tm.createDir('d' + i);
    tm.addChild(cur, d);
    cur = d;
  }
  const target = cur;
  ok('B-P3-5/findNode', tm.findNode(root, target.id) === target);
  ok('B-P3-5/pathOf', tm.pathOf(root, target.id).split(' / ').length === 20001);
  ok('B-P3-5/depthOf', tm.depthOf(root, target.id) === 20000);
  ok('B-P3-5/isSelfOrDescendant', tm.isSelfOrDescendant(root, target.id) === true);
  ok('B-P3-5/findParent', tm.findParent(root, target.id) !== null);
}

/* ---------- B-P3-3 renameNode 自校验 ---------- */
{
  const root = tm.createDir('r');
  const a = tm.createDir('a');
  tm.addChild(root, a);
  const b = tm.createFile('b.txt', 'x');
  tm.addChild(root, b);
  ok('B-P3-3/illegal', tm.renameNode(root, b.id, 'a/b') === false && b.name === 'b.txt');
  ok('B-P3-3/dup', tm.renameNode(root, b.id, 'a') === false && b.name === 'b.txt');
  ok('B-P3-3/ok', tm.renameNode(root, b.id, 'c.txt') === true && b.name === 'c.txt');
  ok('B-P3-3/root', tm.renameNode(root, root.id, 'zz') === false);
}

/* ---------- B-P3-4 toPlainTree 同层重名告警 ---------- */
{
  const root = tm.createDir('r');
  tm.addChild(root, tm.createFile('dup', '1'));
  tm.addChild(root, tm.createFile('dup', '2'));
  const warns = [];
  const orig = console.warn;
  console.warn = (...a) => warns.push(a.join(' '));
  let out;
  try { out = tm.toPlainTree(root); } finally { console.warn = orig; }
  ok('B-P3-4/warn', warns.some((w) => w.indexOf('toPlainTree') >= 0), warns.length);
  ok('B-P3-4/lastWins', out['dup'] === '2');

  const clean = tm.createDir('c');
  tm.addChild(clean, tm.createFile('x', '1'));
  const w2 = [];
  console.warn = (...a) => w2.push(a.join(' '));
  try { tm.toPlainTree(clean); } finally { console.warn = orig; }
  ok('B-P3-4/noFalseWarn', w2.length === 0);
}

/* ---------- B-P3-6 bus.off 后不再触发 ---------- */
{
  const busMod = await import(SRC + '/core/bus.js');
  const bus = busMod.createBus();
  let n = 0;
  const un = bus.on('evt', () => { n += 1; });
  bus.emit('evt');
  un();
  bus.emit('evt');
  ok('B-P3-6/offStops', n === 1, n);
}

/* ---------- B-P3-1 网络层失败归一 ---------- */
{
  globalThis.window = { location: { origin: 'http://127.0.0.1:0' } };
  globalThis.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
  const apiMod = await import(SRC + '/core/api.js');
  let code = null;
  try { await apiMod.api.health(); } catch (e) { code = e.code || null; }
  ok('B-P3-1/networkError', code === 'networkError', code);
}

/* ---------- C-P3-3「指针是否真离开本行」（批 4C） ----------
   `ui/tree-view.js` 顶层只有 import 与函数声明（DOM 访问都在函数体内），可作 ESM 导入。
   `leftRow` 是本项判定的**本体**，两种分支都要覆盖：浏览器探针只能造出
   「有 relatedTarget」那一种，`relatedTarget` 为 null 的坐标兜底分支只能在此验证。 */
{
  const tv = await import(SRC + '/ui/tree-view.js');
  const fakeRow = {
    contains: (el) => Boolean(el) && el.inRow === true,
    getBoundingClientRect: () => ({ left: 10, top: 20, right: 110, bottom: 40 }),
  };
  ok('C-P3-3/relatedInside',
    tv.leftRow(fakeRow, { relatedTarget: { inRow: true } }) === false);
  ok('C-P3-3/relatedOutside',
    tv.leftRow(fakeRow, { relatedTarget: { inRow: false } }) === true);
  ok('C-P3-3/nullInside',
    tv.leftRow(fakeRow, { relatedTarget: null, clientX: 60, clientY: 30 }) === false);
  ok('C-P3-3/nullOutside',
    tv.leftRow(fakeRow, { relatedTarget: null, clientX: 5, clientY: 30 }) === true);
  /* 边界取**闭区间**：正落在边框上仍算「行内」 */
  ok('C-P3-3/nullEdge',
    tv.leftRow(fakeRow, { relatedTarget: null, clientX: 10, clientY: 40 }) === false);
}

process.stdout.write('RESULT ' + JSON.stringify(results) + '\n');
"""


class FrontendJsTests(unittest.TestCase):
    """一次性 Node 驱动，断言脚本的各条结果逐项校验。"""

    results: dict = {}
    err: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        import verify  # noqa: E402  （tools/ 已入 sys.path）

        node = verify.find_node()
        if node is None:
            raise unittest.SkipTest("本机无 node —— 前端 JS 驱动测试跳过")
        tmp = tempfile.TemporaryDirectory(prefix="qm_fejs_")
        cls.addClassCleanup(tmp.cleanup)
        harness = Path(tmp.name) / "probe.mjs"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        env = dict(os.environ, QM_JS_SRC=(_SRC / "web/js").as_uri())
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True,
                              env=env, timeout=120)
        cls.err = proc.stderr[-800:]
        out = {}
        for line in proc.stdout.splitlines():
            if line.startswith("RESULT "):
                for item in json.loads(line[len("RESULT "):]):
                    out[item["name"]] = item
        cls.results = out

    def _ok(self, name: str) -> None:
        self.assertIn(name, self.results, f"探针未产出 {name}；stderr={self.err}")
        item = self.results[name]
        self.assertTrue(item["pass"], f"{name} 不成立（extra={item['extra']}）")

    def test_b3_5_deep_tree_queries(self):
        for n in ("B-P3-5/findNode", "B-P3-5/pathOf",
                  "B-P3-5/depthOf", "B-P3-5/isSelfOrDescendant", "B-P3-5/findParent"):
            self._ok(n)

    def test_b3_3_rename_self_guard(self):
        for n in ("B-P3-3/illegal", "B-P3-3/dup", "B-P3-3/ok", "B-P3-3/root"):
            self._ok(n)

    def test_b3_4_plain_tree_duplicate_warn(self):
        for n in ("B-P3-4/warn", "B-P3-4/lastWins", "B-P3-4/noFalseWarn"):
            self._ok(n)

    def test_b3_6_bus_off(self):
        self._ok("B-P3-6/offStops")

    def test_b3_1_network_error_normalized(self):
        self._ok("B-P3-1/networkError")

    def test_c3_3_left_row_judgement(self):
        """批 4C · C-P3-3：`dragleave` 的「算不算离开」判定，含 relatedTarget 为 null 的兜底分支。"""
        for n in ("C-P3-3/relatedInside", "C-P3-3/relatedOutside",
                  "C-P3-3/nullInside", "C-P3-3/nullOutside", "C-P3-3/nullEdge"):
            self._ok(n)


if __name__ == "__main__":
    unittest.main()
