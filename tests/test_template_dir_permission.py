"""青蔓 QingMan · 在线版模板目录「权限过期」契约测试（`demo-backend.js` + `online-store.js`）。

**由来**：2026-10-21 用户报障「在线版模板载入异常」——实测现象是
**提示「已绑定模板目录：templates」，但模板列表一片空白**，控制台两条
`request failed: demoNeedPermission {status: 403}`。

**根因**：File System Access 的授权**不随句柄持久化**。`pickDir()` 当下拿到的读写权限
只在**当前页面会话**内有效；句柄存进 IndexedDB 后，刷新页面再 `queryPermission`
会退回 `prompt`。而 `GET /api/templates` 原先**只查不问**（`dirPermission` 是纯查询），
一旦状态非 `granted` 就恒返回 403 ⇒ 列表永远空白，且**没有任何提示**
（前端对轮询失败一律静默）。

**修复口径**（两条互补）：
  ① 后端：列表分支在权限不足时**先就地请求一次**（有手势则自愈，无手势仍回 403）；
  ② 前端：`demoNeedPermission` **不再静默**，改为显示说明 + 可点的「重新授权」按钮。

本模块锁住四件事：
  A. 首次绑定后列表正常；
  B. 刷新导致权限退回 prompt 且**无手势**时，仍如实 403（**不得假装成功返回空列表**）；
  C. 有手势时列表**能自愈**，不必让用户重新选目录；
  D. 重新走一次「选择目录」后列表恢复。

⚠ 替身要点：`queryPermission` 必须**可变**（模拟刷新后失权），
`requestPermission` 在无手势时回 `'denied'` 而**不抛错** —— 这是浏览器的真实行为。
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
_BACKEND_JS = _TOOLS / "web-demo" / "demo-backend.js"
_STORE_JS = _TOOLS / "web-demo" / "online-store.js"
_MD_JS = _TOOLS / "web-demo" / "md-template.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

const DIR = process.env.QM_DIR;

const FILES = [
  { name: 'P1_实拍.json',
    text: JSON.stringify({ name: '实拍短视频项目', tree: { 日志: {}, 项目管理: { 项目章程: {} } } }, null, 2) + '\n' },
];

/* 权限状态**可变**：granted → prompt 用来模拟「刷新后失权」 */
function makeDir(stateRef, files) {
  return {
    name: '我的模板库', kind: 'directory',
    queryPermission: () => Promise.resolve(stateRef.value),
    requestPermission: () => {
      /* 真实浏览器：无手势时直接回 'denied'，**不抛错** */
      if (!stateRef.gesture) { return Promise.resolve('denied'); }
      stateRef.value = 'granted';
      return Promise.resolve('granted');
    },
    values() {
      const arr = files.map((f) => ({
        kind: 'file', name: f.name,
        getFile: () => Promise.resolve({
          size: f.text.length, lastModified: 1700000000000,
          text: () => Promise.resolve(f.text),
        }),
      }));
      let i = 0;
      return { next: () => Promise.resolve(i < arr.length ? { done: false, value: arr[i++] } : { done: true }) };
    },
    getFileHandle(name, opt) {
      let hit = files.find((f) => f.name === name);
      if (!hit) {
        if (opt && opt.create) { hit = { name, text: '' }; files.push(hit); }
        else { const e = new Error('missing'); e.name = 'NotFoundError'; return Promise.reject(e); }
      }
      return Promise.resolve({
        name,
        getFile: () => Promise.resolve({
          size: hit.text.length, lastModified: 1700000000000,
          text: () => Promise.resolve(hit.text),
        }),
        createWritable: () => {
          let b = '';
          return Promise.resolve({
            write: (s) => { b += s; return Promise.resolve(); },
            close: () => { hit.text = b; return Promise.resolve(); },
          });
        },
      });
    },
  };
}

function fakeIdb(kv) {
  const db = {
    objectStoreNames: { contains: () => true },
    createObjectStore: () => {},
    transaction: () => {
      const tx = { oncomplete: null, onerror: null };
      tx.objectStore = () => ({
        put: (v, k) => { kv[k] = v; setTimeout(() => tx.oncomplete && tx.oncomplete(), 0); return {}; },
        get: (k) => { const r = { result: kv[k] }; setTimeout(() => tx.oncomplete && tx.oncomplete(), 0); return r; },
        delete: (k) => { delete kv[k]; setTimeout(() => tx.oncomplete && tx.oncomplete(), 0); return {}; },
      });
      return tx;
    },
  };
  return { open: () => {
    const req = { result: db };
    setTimeout(() => { if (req.onupgradeneeded) req.onupgradeneeded(); if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  } };
}

/* 每次「新建页面」都重建 window / localStorage，但 IndexedDB 的 kv 可跨页复用 */
function newPage(stateRef, kv, files) {
  const MEM = new Map();
  const localStorage = {
    getItem: (k) => (MEM.has(k) ? MEM.get(k) : null),
    setItem: (k, v) => { MEM.set(k, String(v)); },
    removeItem: (k) => { MEM.delete(k); },
  };
  const noop = () => {};
  const doc = { readyState: 'complete', querySelector: () => null, addEventListener: noop };
  const dir = makeDir(stateRef, files);
  const win = {
    location: { href: 'https://qingman.pages.dev/', origin: 'https://qingman.pages.dev' },
    localStorage, indexedDB: fakeIdb(kv),
    showDirectoryPicker: () => Promise.resolve(dir),
    fetch: () => Promise.resolve(new Response('{}', { status: 404 })),
    navigator: { language: 'zh-CN', storage: null },
    document: doc, addEventListener: noop,
    __QM_DEMO__: {
      version: 'V0.4.1',
      template: { file: 'P0_空白项目模板.json', name: '空白项目模板', description: '', tree: {} },
    },
  };
  const load = (file) => {
    const ctx = {
      window: win, document: doc, localStorage, indexedDB: win.indexedDB, navigator: win.navigator,
      Response, URL, JSON, Promise, setTimeout, console, atob, Blob: class {},
    };
    ctx.globalThis = ctx;
    vm.runInNewContext(fs.readFileSync(DIR + '/' + file, 'utf8'), ctx);
    Object.keys(ctx).forEach((k) => { if (k !== 'window' && k !== 'globalThis') win[k] = ctx[k]; });
  };
  /* 线上注入序：md → store → backend */
  load('md-template.js');
  load('online-store.js');
  load('demo-backend.js');

  return async (p, method, body) => {
    const res = await win.fetch(p, method
      ? { method, body: body ? JSON.stringify(body) : undefined }
      : { method: 'GET' });
    let b; try { b = await res.json(); } catch (e) { b = { parseError: String(e) }; }
    return { status: res.status, body: b };
  };
}

const out = [];
const ok = (name, pass, extra) => out.push({ name, pass: !!pass, extra: String(extra == null ? '' : extra) });

(async () => {
  const kv = {};
  const perm = { value: 'granted', gesture: true };
  const files = FILES.map((f) => ({ ...f }));

  /* ---- A. 首次绑定 ---- */
  let call = newPage(perm, kv, files);
  const pick = await call('/api/templates-dir/pick', 'POST', {});
  const put = await call('/api/templates-dir', 'PUT', { dir: pick.body.dir, create: false });
  ok('首次绑定成功', put.body.applied === true, 'applied=' + put.body.applied);

  const l1 = await call('/api/templates', 'GET');
  ok('首次列表正常', l1.status === 200 && (l1.body.items || []).length === 1,
     'status=' + l1.status + ' items=' + (l1.body.items || []).length);

  /* ---- B. 刷新：权限退回 prompt，且**无手势** ---- */
  perm.value = 'prompt';
  perm.gesture = false;
  call = newPage(perm, kv, files);        // 新页面，dirCache 为空，从 IndexedDB 取回句柄
  const l2 = await call('/api/templates', 'GET');
  ok('无手势时如实 403（不假装成功）',
     l2.status === 403 && l2.body.code === 'demoNeedPermission',
     'status=' + l2.status + ' code=' + l2.body.code);

  /* ---- C. 有手势时列表自愈 ---- */
  perm.value = 'prompt';
  perm.gesture = true;
  const l3 = await call('/api/templates', 'GET');
  ok('有手势时列表自愈',
     l3.status === 200 && (l3.body.items || []).length === 1,
     'status=' + l3.status + ' items=' + (l3.body.items || []).length);

  /* ---- D. 重新走一次「选择目录」 ---- */
  perm.value = 'prompt';
  perm.gesture = true;
  const pick2 = await call('/api/templates-dir/pick', 'POST', {});
  ok('重新授权 pick 可用',
     pick2.body.available === true && !!pick2.body.dir,
     'available=' + pick2.body.available + ' dir=' + pick2.body.dir);
  const l4 = await call('/api/templates', 'GET');
  ok('重新授权后列表恢复',
     l4.status === 200 && (l4.body.items || []).length === 1,
     'status=' + l4.status + ' items=' + (l4.body.items || []).length);

  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
})().catch((err) => {
  out.push({ name: '探针异常', pass: false, extra: String(err && (err.stack || err.message || err.name)) });
  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
});
"""


class TemplateDirPermissionTests(unittest.TestCase):
    """Node 驱动：锁住「权限不随句柄持久化」这一真实行为下的列表可用性。"""

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
            raise unittest.SkipTest("本机无 node —— 在线版权限契约测试跳过")
        for need in (_BACKEND_JS, _STORE_JS, _MD_JS):
            if not need.is_file():
                raise unittest.SkipTest(f"缺 {need}")

        tmp = tempfile.TemporaryDirectory(prefix="qm_perm_")
        cls.addClassCleanup(tmp.cleanup)
        work = Path(tmp.name)
        # 把三个脚本拷进同一目录，探针按文件名加载（与线上注入序一致）
        for src in (_MD_JS, _STORE_JS, _BACKEND_JS):
            shutil.copy2(src, work / src.name)
        harness = work / "probe.cjs"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")

        env = dict(os.environ, QM_DIR=str(work))
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

    def test_bind_then_list(self):
        """基线：绑定成功后列表立即可用。"""
        self._ok("首次绑定成功")
        self._ok("首次列表正常")

    def test_expired_permission_reports_403(self):
        """刷新后无手势：必须**如实 403**，不能假装成功返回空列表。

        这是本条最关键的反向约束 —— 若为了「让界面好看」而在无权限时返回
        空 items + 200，用户会以为模板真的没了。
        """
        self._ok("无手势时如实 403（不假装成功）")

    def test_gesture_self_heals(self):
        """有手势时后端就地请求授权，列表自愈，用户不必重选目录。"""
        self._ok("有手势时列表自愈")

    def test_reauth_restores_list(self):
        """用户点「重新授权」重走选择器后，列表恢复。"""
        self._ok("重新授权 pick 可用")
        self._ok("重新授权后列表恢复")


if __name__ == "__main__":
    unittest.main()
