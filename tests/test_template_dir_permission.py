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

/* 权限状态**可变**：granted → prompt 用来模拟「刷新后失权」。
   `calls.request` 统计 requestPermission 次数 —— 用它断言「列表不弹框」。 */
function makeDir(stateRef, files) {
  const denied = () => {
    const e = new Error('The request is not allowed by the user agent or the platform.');
    e.name = 'NotAllowedError';
    return e;
  };
  /* 真实浏览器：未授权时**读取本身**就抛 NotAllowedError（不是靠 queryPermission 拦） */
  const guard = () => (stateRef.value === 'granted' ? null : Promise.reject(denied()));
  return {
    name: '我的模板库', kind: 'directory',
    queryPermission: () => Promise.resolve(stateRef.value),
    requestPermission: () => {
      stateRef.calls.request += 1;
      /* 真实浏览器：无手势时直接回 'denied'，**不抛错** */
      if (!stateRef.gesture) { return Promise.resolve('denied'); }
      stateRef.value = 'granted';
      return Promise.resolve('granted');
    },
    values() {
      const blocked = guard();
      if (blocked) { return { next: () => blocked }; }
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

/* 每次「新建页面」都重建 window / localStorage，但 IndexedDB 的 kv 可跨页复用。
   `env.pickState` 决定**这一次点选**拿到的句柄绑在哪个权限状态上 —— 场景 E 要的正是
   「库里那份已失权、而这次点选拿到的是**另一个**已授权的新句柄」。 */
function newPage(stateRef, kv, files, env) {
  const MEM = new Map();
  const localStorage = {
    getItem: (k) => (MEM.has(k) ? MEM.get(k) : null),
    setItem: (k, v) => { MEM.set(k, String(v)); },
    removeItem: (k) => { MEM.delete(k); },
  };
  const noop = () => {};
  const doc = { readyState: 'complete', querySelector: () => null, addEventListener: noop };
  const dir = makeDir(stateRef, files);
  /* 点选拿到的句柄可以**不是**库里那份（同名）：场景 E —— 用户重选同一个文件夹，
     选择器返回的是**新**句柄，权限已授予。若实现把「同名」当成「同一个句柄」，
     新句柄会被丢弃，旧句柄的 403 就永远修不好。 */
  const pickDir = env && env.pickState
    ? makeDir({ value: env.pickState, gesture: true, calls: { request: 0 } }, files)
    : dir;
  const win = {
    location: { href: 'https://qingman.pages.dev/', origin: 'https://qingman.pages.dev' },
    localStorage, indexedDB: fakeIdb(kv),
    showDirectoryPicker: () => Promise.resolve(pickDir),
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
  const perm = { value: 'granted', gesture: true, calls: { request: 0 } };
  const files = FILES.map((f) => ({ ...f }));

  /* ---- A. 首次绑定 ---- */
  let call = newPage(perm, kv, files);
  const pick = await call('/api/templates-dir/pick', 'POST', {});
  const put = await call('/api/templates-dir', 'PUT', { dir: pick.body.dir, create: false });
  ok('首次绑定成功', put.body.applied === true, 'applied=' + put.body.applied);

  const l1 = await call('/api/templates', 'GET');
  ok('首次列表正常', l1.status === 200 && (l1.body.items || []).length === 1,
     'status=' + l1.status + ' items=' + (l1.body.items || []).length);

  /* 关键反向断言：刚绑定时列表**不该**再要一次授权（pick 已经给了） */
  ok('绑定时不多弹授权', perm.calls.request === 0, 'requestPermission 次数=' + perm.calls.request);

  /* ---- B. 刷新：权限退回 prompt，且**无手势** ---- */
  perm.value = 'prompt';
  perm.gesture = false;
  const before = perm.calls.request;
  call = newPage(perm, kv, files);        // 新页面，dirCache 为空，从 IndexedDB 取回句柄
  const l2 = await call('/api/templates', 'GET');
  ok('失权时如实 403（不假装成功）',
     l2.status === 403 && l2.body.code === 'demoNeedPermission',
     'status=' + l2.status + ' code=' + l2.body.code);

  /* **本轮核心回归位**：列表**一次都不能**调 requestPermission —— 它在 2.5s 轮询里
     反复触发，是用户报「多次弹出确认窗口」的直接原因；而且轮询无手势必然失败。 */
  ok('列表轮询不触发授权弹窗', perm.calls.request === before,
     '新增 requestPermission 次数=' + (perm.calls.request - before));

  /* ---- C. 重复轮询也不弹框（连查 3 次） ---- */
  const before3 = perm.calls.request;
  for (let i = 0; i < 3; i += 1) { await call('/api/templates', 'GET'); }
  ok('连续轮询仍不弹框', perm.calls.request === before3,
     '新增 requestPermission 次数=' + (perm.calls.request - before3));

  /* ---- D. 重新走一次「选择目录」→ 恢复 ---- */
  perm.gesture = true;
  perm.value = 'granted';                 // 用户在选择器里点了「允许」
  const pick2 = await call('/api/templates-dir/pick', 'POST', {});
  ok('重新授权 pick 可用',
     pick2.body.available === true && !!pick2.body.dir,
     'available=' + pick2.body.available + ' dir=' + pick2.body.dir);
  const l4 = await call('/api/templates', 'GET');
  ok('重新授权后列表恢复',
     l4.status === 200 && (l4.body.items || []).length === 1,
     'status=' + l4.status + ' items=' + (l4.body.items || []).length);

  /* ---- E. 真机最常踩的那条：**重选同一个文件夹** ----
     2026-10-21 用户实测「选择一个目录作为模板库后，模板文件没有载入」。
     真机时序：上次绑过 → 刷新页面 → 句柄回到 prompt（读取抛 NotAllowedError，403）→
     用户点「选择目录」选**同一个**文件夹 → picker 返回**同名的新句柄**（权限已授予）。
     缺陷：PUT 分支写着 `if (handle && wantDir === handle.name) return applied:true`，
     只比**名字**就认定「已经是这个目录」，于是把新句柄丢掉、继续用失权的旧句柄 ——
     403 永不恢复，重选多少次都一样。 */
  perm.value = 'prompt';                  // 库里那份失权
  perm.gesture = false;
  const staleCall = newPage(perm, kv, files, { pickState: 'granted' });
  const l5 = await staleCall('/api/templates', 'GET');
  ok('重选前如实 403', l5.status === 403 && l5.body.code === 'demoNeedPermission',
     'status=' + l5.status + ' code=' + l5.body.code);

  const pick3 = await staleCall('/api/templates-dir/pick', 'POST', {});
  const put3 = await staleCall('/api/templates-dir', 'PUT', { dir: pick3.body.dir, create: false });
  ok('重选同名目录应采纳新句柄', put3.body.applied === true,
     'applied=' + put3.body.applied + ' dir=' + put3.body.dir);

  const l6 = await staleCall('/api/templates', 'GET');
  ok('重选同名目录后列表恢复',
     l6.status === 200 && (l6.body.items || []).length === 1,
     'status=' + l6.status + ' items=' + (l6.body.items || []).length);

  /* ---- F. 列表条目要带 dirs / files ----
     真机实测：绑定目录后每个模板行显示「undefined 目录 · undefined 文件」——
     目录分支的列表项漏了这两个字段（本机版有）。这属于「列表没载入成功」的观感来源之一。 */
  ok('目录列表项带 dirs/files',
     (l6.body.items || []).every((it) => Number.isFinite(it.dirs) && Number.isFinite(it.files)),
     JSON.stringify((l6.body.items || []).map((it) => [it.dirs, it.files])));

  /* ---- G. 坏文件要进 `skipped`，不能混在可载入条目里 ----
     真机实测：一个 JSON 解析失败的文件照样列成模板（名字取文件名），点它才报错。
     本机版 V0.4.0 已改为回传 skipped 清单，在线版没跟上。 */
  const badFiles = files.concat([{ name: '坏文件.json', text: '{"tree": ' }]);
  const badCall = newPage({ value: 'granted', gesture: true, calls: { request: 0 } }, {}, badFiles);
  const badPick = await badCall('/api/templates-dir/pick', 'POST', {});
  await badCall('/api/templates-dir', 'PUT', { dir: badPick.body.dir, create: false });
  const l7 = await badCall('/api/templates', 'GET');
  ok('坏文件不进可载入列表',
     (l7.body.items || []).every((it) => it.file !== '坏文件.json'),
     JSON.stringify((l7.body.items || []).map((it) => it.file)));
  ok('坏文件进 skipped 清单',
     Array.isArray(l7.body.skipped) && l7.body.skipped.some((s) => s.file === '坏文件.json' && !!s.code),
     JSON.stringify(l7.body.skipped || null));

  /* ---- H. 一键重新授权（V0.4.5 新增端点 POST /api/templates-dir/grant） ----
     失权后用户不必重走文件夹选择器：点列表里那颗按钮 → 浏览器在手势里弹一次「允许」
     → 复用 IndexedDB 里那份句柄。断言：① 无手势时如实 403；② 有手势时 granted 且列表恢复。 */
  const gPerm = { value: 'prompt', gesture: false, calls: { request: 0 } };
  const gCall = newPage(gPerm, {}, files);
  await gCall('/api/templates-dir/pick', 'POST', {});
  await gCall('/api/templates-dir', 'PUT', { dir: '我的模板库', create: false });
  gPerm.value = 'prompt';
  const g1 = await gCall('/api/templates-dir/grant', 'POST', {});
  ok('无手势授权如实 403', g1.status === 403 && g1.body.code === 'demoNeedPermission',
     'status=' + g1.status + ' code=' + g1.body.code);

  gPerm.gesture = true;
  const g2 = await gCall('/api/templates-dir/grant', 'POST', {});
  ok('有手势授权成功', g2.status === 200 && g2.body.granted === true,
     'status=' + g2.status + ' granted=' + g2.body.granted);
  const g3 = await gCall('/api/templates', 'GET');
  const gItems = g3.body.items || [];
  ok('一键授权后列表恢复', g3.status === 200 && gItems.length === files.length,
     'status=' + g3.status + ' items=' + gItems.length);

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
        """基线：绑定成功后列表立即可用，且**不再多要一次授权**。"""
        self._ok("首次绑定成功")
        self._ok("首次列表正常")
        self._ok("绑定时不多弹授权")

    def test_expired_permission_reports_403(self):
        """失权时：必须**如实 403**，不能假装成功返回空列表。

        若为了「让界面好看」而在无权限时返回空 items + 200，
        用户会以为模板真的没了。
        """
        self._ok("失权时如实 403（不假装成功）")

    def test_list_never_requests_permission(self):
        """**本轮核心回归位**：列表请求一次都不能触发授权弹窗。

        2026-10-21 用户报「选择目录时多次弹出需要确认的窗口，操作繁琐」，
        根因是列表分支（每 2500ms 轮询）里调了 `requestPermission`：
          · 无手势时必然失败（浏览器回 denied，不抛错）⇒ 永远 403；
          · 有手势时则真的弹框 ⇒ 用户被反复打扰。
        故断言：绑定后、失权后、连续轮询后，`requestPermission` 调用次数都不增加。
        """
        self._ok("绑定时不多弹授权")
        self._ok("列表轮询不触发授权弹窗")
        self._ok("连续轮询仍不弹框")

    def test_reauth_restores_list(self):
        """用户重新走一次「选择目录」后，列表恢复。"""
        self._ok("重新授权 pick 可用")
        self._ok("重新授权后列表恢复")

    def test_repick_same_folder_restores_list(self):
        """**2026-10-21 用户实测缺陷的回归位**：重选**同一个**文件夹必须能恢复列表。

        真机时序：上次绑过 → 刷新 → 句柄失权（403）→ 点「选择目录」选同一个文件夹
        → picker 返回**同名的新句柄**。旧实现只比名字就短路返回 `applied:true`，
        新句柄被丢弃 ⇒ 永远 403、重选多少次都没用（这正是用户说的「改了多次仍不能载入」）。
        """
        self._ok("重选前如实 403")
        self._ok("重选同名目录应采纳新句柄")
        self._ok("重选同名目录后列表恢复")

    def test_list_items_carry_stats(self):
        """列表项必须带 `dirs` / `files` —— 否则界面显示「undefined 目录 · undefined 文件」。"""
        self._ok("目录列表项带 dirs/files")

    def test_broken_file_goes_to_skipped(self):
        """解析失败的模板文件**不进**可载入列表，而是进 `skipped` 清单（与本机版同口径）。"""
        self._ok("坏文件不进可载入列表")
        self._ok("坏文件进 skipped 清单")

    def test_grant_endpoint_requires_gesture(self):
        """一键重新授权：无手势时如实 403（浏览器不会弹框），有手势时成功并恢复列表。"""
        self._ok("无手势授权如实 403")
        self._ok("有手势授权成功")
        self._ok("一键授权后列表恢复")


if __name__ == "__main__":
    unittest.main()
