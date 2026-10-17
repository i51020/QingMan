"""青蔓 QingMan · 在线版存储层的两步契约测试（`tools/web-demo/online-store.js`）。

**由来**：2026-10-17 用户报告「目录树工作区选择目标位置后，模板目录路径变了」。

根因是 `pickDir()` 在 `showDirectoryPicker` 成功后**立刻** `store.put(handle, 'templatesDir')`
—— 把本机版刻意分开的「选择」与「绑定」两步合成了一步。而主界面的「目标位置 · 选择…」
复用的正是同一个端点（`POST /api/templates-dir/pick`），它拿到路径只填进输入框、
**从不发 `PUT /api/templates-dir`** —— 于是模板库被悄悄改绑到目标文件夹。

契约（与本机版 `routes.pick_templates_dir` 的 docstring 一致）：
  * `pickDir()`  只暂存句柄，**不落库**；
  * `commitDir(name)` 在前端发 `PUT` 确认、且**名字对得上**时才写 IndexedDB。

本模块用 Node + 假 IndexedDB 锁住这条契约：若有人把 `pickDir` 改回"选完即落库"，
本测试立刻红。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
_TOOLS = _ROOT / "tools"
_STORE_JS = _TOOLS / "web-demo" / "online-store.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.env.QM_STORE_JS, 'utf8');

const results = [];
const ok = (name, pass, extra = '') => results.push({ name, pass: !!pass, extra: String(extra) });

/* ---- 假 IndexedDB：只够 openDb / idbRun 用（一个 kv 表） ---- */
function fakeIdb() {
  const data = Object.create(null);
  const db = {
    objectStoreNames: { contains: () => true },
    createObjectStore: () => {},
    transaction: () => {
      const tx = { oncomplete: null, onerror: null };
      tx.objectStore = () => ({
        put: (value, key) => {
          data[key] = value;
          const req = {};
          setTimeout(() => { if (tx.oncomplete) tx.oncomplete(); }, 0);
          return req;
        },
        get: (key) => {
          const req = { result: data[key] };
          setTimeout(() => { if (tx.oncomplete) tx.oncomplete(); }, 0);
          return req;
        },
      });
      return tx;
    },
  };
  return {
    open: () => {
      const req = { result: db };
      setTimeout(() => {
        if (req.onupgradeneeded) req.onupgradeneeded();
        if (req.onsuccess) req.onsuccess();
      }, 0);
      return req;
    },
  };
}

function fakeLocalStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => { data.set(k, String(v)); },
    removeItem: (k) => { data.delete(k); },
  };
}

const handles = { tpl: { name: '旧模板目录' }, tgt: { name: '目标文件夹' } };
let nextHandle = null;
const win = {
  indexedDB: fakeIdb(),
  localStorage: fakeLocalStorage(),
  showDirectoryPicker: () => Promise.resolve(nextHandle),
};
vm.runInNewContext(src, { window: win, console, setTimeout, Promise, JSON });
const STORE = win.QMDemoStore;

(async () => {
  ok('导出可用', !!STORE && typeof STORE.pickDir === 'function'
     && typeof STORE.commitDir === 'function' && typeof STORE.getDir === 'function');

  /* ① 选择：只回报，不落库 */
  nextHandle = handles.tpl;
  const picked = await STORE.pickDir();
  ok('pick 回报所选目录', picked && picked.name === '旧模板目录', picked && picked.name);
  ok('pick 不落库', (await STORE.getDir()) == null);

  /* ② 名字对不上（手填路径）：拒绝，且待定句柄仍留着 */
  ok('名字不符不落库', (await STORE.commitDir('D:/随便/写的')) === false);
  ok('拒绝后仍未落库', (await STORE.getDir()) == null);

  /* ③ 前端发 PUT 确认同名的目录：这才落库 */
  ok('确认后落库', (await STORE.commitDir('旧模板目录')) === true);
  const bound = await STORE.getDir();
  ok('落库确为模板目录', !!bound && bound.name === '旧模板目录', bound && bound.name);

  /* ④ 回归点：再走一次「选择」（= 目标位置流程）不得改动已绑定的模板目录 */
  nextHandle = handles.tgt;
  const target = await STORE.pickDir();
  ok('目标位置也能拿到目录名', target && target.name === '目标文件夹', target && target.name);
  const after = await STORE.getDir();
  ok('选目标位置不改模板库', !!after && after.name === '旧模板目录', after && after.name);

  /* ⑤ 真要在模板库弹窗里绑定这个目录（会发 PUT），仍然可以 */
  ok('另一个目录也可按名绑定', (await STORE.commitDir('目标文件夹')) === true);
  const rebound = await STORE.getDir();
  ok('改绑后为新的目录', !!rebound && rebound.name === '目标文件夹', rebound && rebound.name);

  process.stdout.write('RESULT ' + JSON.stringify(results) + '\n');
})().catch((err) => {
  ok('异常', false, err && (err.message || err.name));
  process.stdout.write('RESULT ' + JSON.stringify(results) + '\n');
});
"""


class OnlineStoreTests(unittest.TestCase):
    """Node 驱动：锁住「选择 / 绑定」两步契约。"""

    results: dict = {}
    err: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        import sys

        if str(_TOOLS) not in sys.path:
            sys.path.insert(0, str(_TOOLS))
        import verify  # noqa: E402  （tools/ 已入 sys.path）

        node = verify.find_node()
        if node is None:
            raise unittest.SkipTest("本机无 node —— 在线版存储层测试跳过")
        if not _STORE_JS.is_file():
            raise unittest.SkipTest(f"缺 {_STORE_JS}")

        tmp = tempfile.TemporaryDirectory(prefix="qm_store_")
        cls.addClassCleanup(tmp.cleanup)
        harness = Path(tmp.name) / "probe.cjs"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        env = dict(os.environ, QM_STORE_JS=str(_STORE_JS))
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

    def test_exports_available(self):
        self._ok("导出可用")

    def test_pick_does_not_persist(self):
        self._ok("pick 回报所选目录")
        self._ok("pick 不落库")

    def test_commit_requires_matching_name(self):
        self._ok("名字不符不落库")
        self._ok("拒绝后仍未落库")
        self._ok("确认后落库")
        self._ok("落库确为模板目录")

    def test_target_pick_keeps_templates_dir(self):
        """用户报告的那个 bug：选目标位置后模板目录不得变化。"""
        self._ok("目标位置也能拿到目录名")
        self._ok("选目标位置不改模板库")

    def test_rebind_still_works(self):
        self._ok("另一个目录也可按名绑定")
        self._ok("改绑后为新的目录")


if __name__ == "__main__":
    unittest.main()
