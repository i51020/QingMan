"""在线版「按树生成」的重名契约测试（`tools/web-demo/demo-backend.js`）。

**由来（2026-10-26 用户诉求）**：「检查网页版、本地版重名判定，原则是不要误删、污染同名目录。」

审计发现在线版与本机版口径不一致 —— 在线版 `writeTree` 对文件一律
`getFileHandle(create:true)` + `createWritable()`，于是**同名既有文件会被直接覆盖**
（内容被悄悄改掉），且仍被计入 `createdFiles`（谎报新建）。

本模块把三条不变量钉死（与本机版 `dtree_core.build_tree` 同口径）：

  A. 同名**目录**已存在 → 复用，计入 `existed`；
  B. 同名**文件**已存在 → 跳过、**绝不覆盖**，计入 `existed`；
  C. 同名但类型相反 → 明确 409（`pathConflict` / `pathConflictDir`），不静默跳过；
  D. 同层仅大小写不同 → 409 `treeSiblingDuplicated`，且**磁盘一字未动**（预检先于写盘）。
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
_BACKEND = _TOOLS / "web-demo" / "demo-backend.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const backendSrc = fs.readFileSync(process.env.QM_BACKEND_JS, 'utf8');

const out = [];
const ok = (name, pass, extra) => out.push({ name, pass: !!pass, extra: String(extra == null ? '' : extra) });

/* ---------- 假文件系统（只实现本用例用到的三种语义） ---------- */
function newRoot() { return { type: 'dir', children: {} }; }

function fileHandle(node, name) {
  return {
    kind: 'file', name,
    createWritable: () => Promise.resolve({
      write: (s) => { node.children[name].content = String(s); return Promise.resolve(); },
      close: () => Promise.resolve(),
    }),
  };
}

function dirHandle(node, name) {
  return {
    kind: 'directory', name,
    getFileHandle: (n, opt) => {
      const e = node.children[n];
      if (e) {
        if (e.type === 'dir') { const x = new Error('mismatch'); x.name = 'TypeMismatchError'; return Promise.reject(x); }
        return Promise.resolve(fileHandle(node, n));
      }
      if (opt && opt.create) {
        node.children[n] = { type: 'file', content: '' };
        return Promise.resolve(fileHandle(node, n));
      }
      const x = new Error('missing'); x.name = 'NotFoundError'; return Promise.reject(x);
    },
    getDirectoryHandle: (n, opt) => {
      const e = node.children[n];
      if (e) {
        if (e.type === 'file') { const x = new Error('mismatch'); x.name = 'TypeMismatchError'; return Promise.reject(x); }
        return Promise.resolve(dirHandle(e, n));
      }
      if (opt && opt.create) {
        node.children[n] = { type: 'dir', children: {} };
        return Promise.resolve(dirHandle(node.children[n], n));
      }
      const x = new Error('missing'); x.name = 'NotFoundError'; return Promise.reject(x);
    },
  };
}

function makeEnv(root) {
  const noop = () => {};
  const doc = { readyState: 'complete', querySelector: () => null, getElementById: () => null, addEventListener: noop };
  const win = {
    location: { href: 'https://example.test/', origin: 'https://example.test' },
    localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    navigator: { language: 'zh-CN' },
    document: doc,
    addEventListener: noop,
    fetch: () => Promise.resolve(new Response('{}', { status: 404 })),
    /* 真实浏览器里必然存在；`generate` 会先检查它的存在性，再走「已记住目标」的快路。
       故这里给一个桩（用例都走快路，不会被真正调用）。 */
    showDirectoryPicker: () => Promise.resolve(dirHandle(root, 'target')),
    __QM_DEMO__: { version: 'V0.4.7', template: { file: 'P0.json', name: 'P0', description: '', tree: {} } },
    QMDemoStore: {
      peekTarget: () => dirHandle(root, 'target'),
      rememberTarget: () => Promise.resolve(true),
      peekDir: () => null,
    },
  };
  const ctx = {
    window: win, document: doc, navigator: win.navigator, localStorage: win.localStorage,
    Response, URL, JSON, Promise, setTimeout, console, atob, Blob: class {},
  };
  ctx.globalThis = ctx;
  vm.runInNewContext(backendSrc, ctx);
  return win;
}

async function call(win, body) {
  const res = await win.fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  let payload = null;
  try { payload = await res.json(); } catch (e) { payload = { parseError: String(e) }; }
  return { status: res.status, payload };
}

(async () => {
  /* A. 全新目录：正常创建，existed 为空 */
  {
    const root = newRoot();
    const win = makeEnv(root);
    const r = await call(win, { tree: { 素材: { 'a.txt': '1' } }, root: '项目', dryRun: false });
    ok('A 新建成功', r.status === 200 && r.payload.ok === true, 'status=' + r.status);
    ok('A existed 为空', Array.isArray(r.payload.existed) && r.payload.existed.length === 0,
       JSON.stringify(r.payload.existed));
    const p = root.children['项目'] || { children: {} };
    ok('A 文件内容正确', !!p.children['素材'] && p.children['素材'].children['a.txt'].content === '1',
       JSON.stringify(p.children['素材'] || null));
  }

  /* B. 同名文件已存在：**不得覆盖**，计入 existed，不报 createdFiles */
  {
    const root = newRoot();
    root.children['项目'] = { type: 'dir', children: {
      '素材': { type: 'dir', children: { 'a.txt': { type: 'file', content: '原始内容' } } },
    } };
    const win = makeEnv(root);
    const r = await call(win, { tree: { 素材: { 'a.txt': '覆盖尝试', 'b.txt': '新' } }, root: '项目', dryRun: false });
    ok('B 生成成功', r.status === 200 && r.payload.ok === true, 'status=' + r.status);
    const kept = root.children['项目'].children['素材'].children['a.txt'].content;
    ok('B 既有文件未被覆盖', kept === '原始内容', 'content=' + kept);
    ok('B 既有项计入 existed', r.payload.existed.some((x) => x.endsWith('a.txt')),
       JSON.stringify(r.payload.existed));
    ok('B 未被谎报为新建', !r.payload.createdFiles.some((x) => x.endsWith('a.txt')),
       JSON.stringify(r.payload.createdFiles));
    ok('B 只新建缺的那个', r.payload.createdFiles.some((x) => x.endsWith('b.txt')),
       JSON.stringify(r.payload.createdFiles));
  }

  /* C. 树要目录、磁盘是文件 → 409 pathConflict */
  {
    const root = newRoot();
    root.children['项目'] = { type: 'dir', children: { '素材': { type: 'file', content: 'x' } } };
    const win = makeEnv(root);
    const r = await call(win, { tree: { 素材: {} }, root: '项目', dryRun: false });
    ok('C 文件占名时拒绝建目录', r.status === 409 && r.payload.code === 'pathConflict',
       'status=' + r.status + ' code=' + r.payload.code);
  }

  /* D. 树要文件、磁盘是目录 → 409 pathConflictDir（与本机版对称） */
  {
    const root = newRoot();
    root.children['项目'] = { type: 'dir', children: { '素材': { type: 'dir', children: {} } } };
    const win = makeEnv(root);
    const r = await call(win, { tree: { 素材: '内容' }, root: '项目', dryRun: false });
    ok('D 目录占名时拒绝建文件', r.status === 409 && r.payload.code === 'pathConflictDir',
       'status=' + r.status + ' code=' + r.payload.code);
  }

  /* E. 同层仅大小写不同 → 409，且磁盘一字未动 */
  {
    const root = newRoot();
    const win = makeEnv(root);
    const r = await call(win, { tree: { A: { 'x.txt': '1' }, a: { 'y.txt': '2' } }, root: '项目', dryRun: false });
    ok('E 大小写重复被拒', r.status === 409 && r.payload.code === 'treeSiblingDuplicated',
       'status=' + r.status + ' code=' + r.payload.code);
    ok('E 拒绝时不留半棵树', !root.children['项目'], JSON.stringify(Object.keys(root.children)));
  }

  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
})().catch((err) => {
  out.push({ name: '探针异常', pass: false, extra: String(err && (err.stack || err.message)) });
  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
});
"""


class OnlineGenerateCollisionTests(unittest.TestCase):
    """Node 驱动：在线版写盘必须与本机版同口径（不覆盖、不误删、类型冲突报错）。"""

    results: dict = {}
    err: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        import shutil
        import sys

        if str(_TOOLS) not in sys.path:
            sys.path.insert(0, str(_TOOLS))
        import verify  # noqa: E402

        node = verify.find_node()
        if node is None:
            raise unittest.SkipTest("本机无 node —— 在线版生成契约测试跳过")
        if not _BACKEND.is_file():
            raise unittest.SkipTest(f"缺 {_BACKEND}")

        tmp = tempfile.TemporaryDirectory(prefix="qm_ongen_")
        cls.addClassCleanup(tmp.cleanup)
        work = Path(tmp.name)
        shutil.copy2(_BACKEND, work / "demo-backend.js")
        harness = work / "probe.cjs"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")

        env = dict(os.environ, QM_BACKEND_JS=str(work / "demo-backend.js"))
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True,
                              env=env, timeout=120)
        cls.err = proc.stderr[-800:]
        for line in proc.stdout.splitlines():
            if line.startswith("RESULT "):
                for item in json.loads(line[len("RESULT "):]):
                    cls.results[item["name"]] = item

    def _ok(self, name: str) -> None:
        self.assertIn(name, self.results, f"探针未产出 {name}；stderr={self.err}")
        item = self.results[name]
        self.assertTrue(item["pass"], f"{name} 不成立（extra={item['extra']}）")

    def test_new_tree_creates(self):
        self._ok("A 新建成功")
        self._ok("A existed 为空")
        self._ok("A 文件内容正确")

    def test_existing_file_is_never_overwritten(self):
        """**本轮核心**：同名文件已存在时不得覆盖内容，也不得谎报为新建。"""
        self._ok("B 生成成功")
        self._ok("B 既有文件未被覆盖")
        self._ok("B 既有项计入 existed")
        self._ok("B 未被谎报为新建")
        self._ok("B 只新建缺的那个")

    def test_type_conflicts_are_explicit(self):
        self._ok("C 文件占名时拒绝建目录")
        self._ok("D 目录占名时拒绝建文件")

    def test_case_only_siblings_rejected_atomically(self):
        self._ok("E 大小写重复被拒")
        self._ok("E 拒绝时不留半棵树")


if __name__ == "__main__":
    unittest.main()
