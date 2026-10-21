"""青蔓 QingMan · 在线版**导出**链路契约测试（`tools/web-demo/demo-backend.js`）。

**由来**：2026-10-21 用户报障「在线版 https://qingman.pages.dev 的导出功能异常」。
实测根因：**列表与导出不同源**。

  * `GET /api/templates` 在绑定真实目录后**只读目录**；
  * 而导出 `GET /api/templates-export/<name>` 走 `templateDoc()`，**只读 `localStorage`
    与内置 P0**，完全不知道已绑定的目录 —— 于是「列表里看得见、一导出就 404
    `templateNotFound`」。

修复口径：导出改用 `readTemplateSource()`，**目录优先、浏览器内兜底**，与列表同源；
且不传 `format` 时必须**原样交回原文**（导出 → 再导入要与原件一致，不能被再序列化）。

本模块锁住五件事：
  ① 已绑定目录能导出 `.json` / `.md`，且**逐字节等于目录里的原文**；
  ② 未绑定目录时仍能导出浏览器内模板与内置空白模板（回归位：别为了修 A 弄坏 B）；
  ③ `?format=` 双向转换可用，且转出的内容能被解析回来；
  ④ 目标不存在仍是 404，不得因放宽读取面而变成「假成功」；
  ⑤ 备份导出（服务设置面板那条）不受影响。

⚠ 探针的加载顺序必须是**线上真实注入序**：`md-template.js` → `online-store.js`
→ `demo-backend.js`。顺序错了，`MD` 会是 null，转换分支测不出来（会误报 demoReadonly）。
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
_MD_JS = _TOOLS / "web-demo" / "md-template.js"
_LOCALE_JS = _ROOT / "locales" / "zh-CN.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

const backendPath = process.env.QM_BACKEND_JS;
const mdPath = process.env.QM_MD_JS;
const localePath = process.env.QM_LOCALE_JS;

/* 取词表：从**真实语言包**抓 `err.*` 文案（正则取字典项，不执行整个模块）。
   错误文案断言必须基于真实文案 —— 自造一份就等于只测自己的假设。 */
function loadDict(file) {
  const txt = fs.readFileSync(file, 'utf8');
  const dict = {};
  const re = /'([^']+)':\s*'((?:[^'\\]|\\.)*)'/g;
  let m;
  while ((m = re.exec(txt))) {
    dict[m[1]] = m[2].replace(/\\'/g, "'").replace(/\\\\/g, '\\');
  }
  return dict;
}

/* 假模板目录：一个 .json、一个 .md。原文刻意带缩进与中文，用来验「逐字节原样交回」。 */
const FILES = [
  { name: '目录里的甲.json',
    text: JSON.stringify({ name: '目录里的甲', description: '在磁盘上', tree: { A: {} } }, null, 2) + '\n' },
  { name: '目录里的乙.md', text: '# 目录里的乙\n\n- 甲/\n- b.txt\n' },
];

function fakeDir(files) {
  return {
    name: '我的模板库',
    kind: 'directory',
    queryPermission: () => Promise.resolve('granted'),
    requestPermission: () => Promise.resolve('granted'),
    values() {
      const arr = files.map((f) => ({
        kind: 'file',
        name: f.name,
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
        /* `create:true` 要能新建 —— 否则「新建模板」这条回归位跑不起来，
           会把替身的缺陷误报成产品的 500。 */
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
          let buf = '';
          return Promise.resolve({
            write: (s) => { buf += s; return Promise.resolve(); },
            close: () => { hit.text = buf; return Promise.resolve(); },
          });
        },
      });
    },
  };
}

/* 每档测试都用**全新环境**：localStorage 与目录句柄不串味 */
function makeEnv(bound) {
  const MEM = new Map();
  if (!bound) {
    MEM.set('qm.demo.templates', JSON.stringify({
      '本地模板丙.json': { name: '本地模板丙', description: '在浏览器里', tree: { C: {} }, mtime: 1 },
    }));
  }
  const localStorage = {
    getItem: (k) => (MEM.has(k) ? MEM.get(k) : null),
    setItem: (k, v) => { MEM.set(k, String(v)); },
    removeItem: (k) => { MEM.delete(k); },
  };
  const dir = bound ? fakeDir(FILES) : null;
  const store = {
    getDir: () => Promise.resolve(dir),
    dirPermission: () => Promise.resolve('granted'),
    requestDirPermission: () => Promise.resolve('granted'),
    readDirTemplates: () => Promise.resolve(bound ? FILES.map((f) => ({
      file: f.name, name: f.name.replace(/\.[^.]+$/, ''), description: '',
      dirs: 0, files: 1,
      size: f.text.length, mtime: 0, source: /\.md$/.test(f.name) ? 'md' : 'json',
    })) : []),
    /* V0.4.5：列表改走 `scanDirTemplates`（返回 items + skipped）；
       导出测试只关心「列表能读到目录」，故给同形替身即可。 */
    scanDirTemplates: () => Promise.resolve({
      items: bound ? FILES.map((f) => ({
        file: f.name, name: f.name.replace(/\.[^.]+$/, ''), description: '',
        dirs: 0, files: 1,
        size: f.text.length, mtime: 0, source: /\.md$/.test(f.name) ? 'md' : 'json',
      })) : [],
      skipped: [],
    }),
    /* 本替身没有「刚点选、待确认」的句柄：PUT 走原来的同名短路即可 */
    hasPendingDir: () => false,
    readDirTemplateText: (h, file) => {
      const hit = FILES.find((f) => f.name === file);
      if (!hit || !bound) { const e = new Error('missing'); e.name = 'NotFoundError'; return Promise.reject(e); }
      return Promise.resolve(hit.text);
    },
    readDirTemplate: (h, file) => {
      const hit = FILES.find((f) => f.name === file);
      if (!hit || !bound) return Promise.reject(new Error('missing'));
      const doc = /\.md$/.test(file)
        ? { name: '目录里的乙', description: '', tree: { 甲: {}, 'b.txt': '' } }
        : JSON.parse(hit.text);
      return Promise.resolve({
        file, name: doc.name, description: doc.description || '',
        tree: doc.tree || {}, source: /\.md$/.test(file) ? 'md' : 'json',
      });
    },
    peekTarget: () => null,
    preloadTarget: () => Promise.resolve(false),
    sortByFile: (items) => items.slice(),
    /* 写模板这条链的替身：错误文案断言要走到「新建 / 同名冲突」分支，
       缺这两个原语会抛 TypeError，被误当成产品缺陷。 */
    dirFileExists: (h, file) => Promise.resolve(bound && FILES.some((f) => f.name === file)),
    writeDirFile: (h, file, text) => {
      const hit = FILES.find((f) => f.name === file);
      if (hit) { hit.text = text; } else { FILES.push({ name: file, text }); }
      return Promise.resolve();
    },
    exportAll: () => ({
      file: 'qingman-backup-20261021-1102.json',
      text: JSON.stringify({ schema: 'qm-demo-backup/1', editor: null, templates: {} }, null, 2) + '\n',
    }),
  };

  const noop = () => {};
  const doc = { readyState: 'complete', querySelector: () => null, addEventListener: noop };
  const win = {
    location: { href: 'https://qingman.pages.dev/', origin: 'https://qingman.pages.dev' },
    localStorage,
    fetch: () => Promise.resolve(new Response('{}', { status: 404 })),
    navigator: { language: 'zh-CN' },
    document: doc,
    addEventListener: noop,
    __QM_DEMO__: {
      version: 'V0.3.12',
      template: { file: 'P0_空白项目模板.json', name: '空白项目模板', description: '', tree: {} },
    },
  };
  const ctx = {
    window: win, document: doc, localStorage, navigator: win.navigator,
    Response, URL, JSON, Promise, setTimeout, console, atob, Blob: class {},
  };
  ctx.globalThis = ctx;

  /* **加载顺序 = 线上注入序**（构建器写进页面的先后）：
     md-template.js → online-store.js → demo-backend.js。
     `demo-backend.js` 在**载入那一刻**就抓 `window.QMDemoMd` / `window.QMDemoStore`，
     所以这两个必须在它之前就位。 */
  vm.runInNewContext(fs.readFileSync(mdPath, 'utf8'), ctx);
  win.QMDemoStore = store;
  win.__QM_TEST_DICT__ = localePath ? loadDict(localePath) : {};
  vm.runInNewContext(fs.readFileSync(backendPath, 'utf8'), ctx);

  return {
    win,
    call: async (path, method, body) => {
      const res = await win.fetch(path, method && method !== 'GET'
        ? { method, body: JSON.stringify(body || {}), headers: { 'Content-Type': 'application/json' } }
        : { method: 'GET' });
      let payload = null;
      try { payload = await res.json(); } catch (e) { payload = { parseError: String(e) }; }
      return { status: res.status, payload };
    },
  };
}

const out = [];
const ok = (name, pass, extra) => out.push({ name, pass: !!pass, extra: String(extra == null ? '' : extra) });

(async () => {
  /* ---------- A. 未绑定目录（浏览器内模板）—— 回归位 ---------- */
  {
    const { call } = makeEnv(false);
    const r = await call('/api/templates-export/' + encodeURIComponent('本地模板丙.json'), 'GET');
    ok('未绑定·导出浏览器内模板', r.status === 200 && r.payload.ok === true,
       'status=' + r.status + ' code=' + r.payload.code);

    const p0 = await call('/api/templates-export/' + encodeURIComponent('P0_空白项目模板.json'), 'GET');
    ok('未绑定·导出内置空白模板', p0.status === 200 && p0.payload.ok === true,
       'status=' + p0.status + ' code=' + p0.payload.code);

    const md = await call('/api/templates-export/' + encodeURIComponent('本地模板丙.json') + '?format=md', 'GET');
    ok('未绑定·json→md 转换', md.status === 200 && /\.md$/.test(md.payload.file || ''),
       'status=' + md.status + ' file=' + md.payload.file);

    const none = await call('/api/templates-export/' + encodeURIComponent('不存在.json'), 'GET');
    ok('未绑定·不存在的模板 404', none.status === 404,
       'status=' + none.status + ' code=' + none.payload.code);
  }

  /* ---------- B. 已绑定真实目录 —— 本次报障的主场景 ---------- */
  {
    const { call } = makeEnv(true);

    const list = await call('/api/templates', 'GET');
    const files = (list.payload.items || []).map((x) => x.file);
    ok('已绑定·列表读目录', files.indexOf('目录里的甲.json') >= 0, files.join(','));

    const j = await call('/api/templates-export/' + encodeURIComponent('目录里的甲.json'), 'GET');
    ok('已绑定·导出 json 模板', j.status === 200 && j.payload.ok === true,
       'status=' + j.status + ' code=' + j.payload.code);
    ok('已绑定·json 原样交回', j.status === 200 && (j.payload.text || '') === FILES[0].text,
       'byte-equal=' + ((j.payload.text || '') === FILES[0].text));

    const m = await call('/api/templates-export/' + encodeURIComponent('目录里的乙.md'), 'GET');
    ok('已绑定·导出 md 模板原样', m.status === 200 && (m.payload.text || '') === FILES[1].text,
       'status=' + m.status + ' byte-equal=' + ((m.payload.text || '') === FILES[1].text));

    const c1 = await call('/api/templates-export/' + encodeURIComponent('目录里的甲.json') + '?format=md', 'GET');
    ok('已绑定·json→md 转换', c1.status === 200 && c1.payload.source === 'md'
       && c1.payload.file === '目录里的甲.md',
       'status=' + c1.status + ' file=' + c1.payload.file);

    const c2 = await call('/api/templates-export/' + encodeURIComponent('目录里的乙.md') + '?format=json', 'GET');
    ok('已绑定·md→json 转换', c2.status === 200 && c2.payload.source === 'json'
       && /\.json$/.test(c2.payload.file || ''),
       'status=' + c2.status + ' file=' + c2.payload.file);

    let back = false;
    try {
      const parsed = JSON.parse(c2.payload.text || '');
      back = !!parsed.tree && Object.keys(parsed.tree).indexOf('甲') >= 0;
    } catch (e) { back = false; }
    ok('已绑定·转出的 json 可解析', back, (c2.payload.text || '').slice(0, 60));

    const miss = await call('/api/templates-export/' + encodeURIComponent('没有这个.json'), 'GET');
    ok('已绑定·目录里没有仍 404', miss.status === 404,
       'status=' + miss.status + ' code=' + miss.payload.code);
  }

  /* ---------- C. 备份导出（服务设置面板）—— 别被同一次改动带坏 ---------- */
  {
    const { call } = makeEnv(true);
    const bak = await call('/api/demo-backup', 'GET');
    ok('备份导出可用', bak.status === 200 && bak.payload.ok === true && !!bak.payload.text,
       'status=' + bak.status);
    ok('备份文件名合规', /^qingman-backup-\d{8}-\d{4}\.json$/.test(bak.payload.file || ''),
       bak.payload.file);
  }

  /* ---------- D. 错误文案占位符必须被填满（2026-10-21 用户报障「模板不存在：{name}」） ----------
   * 前端 `localizeError()` 只认 `code` + `detail`，用取词表 `err.<code>` 重新成句；
   * `fail()` 不带 `detail` 时占位符不会被替换，用户会看到字面量 `{name}`。
   * 这里按**前端真实逻辑**渲染，断言最终文案里不得出现 `{`。 */
  {
    const { call, win } = makeEnv(true);

    /* 取词表来自真实语言包（zh-CN.js），不另造文案 */
    const dict = win.__QM_TEST_DICT__ || {};
    const render = (body) => {
      const key = 'err.' + body.code;
      let text = dict[key];
      if (text === undefined) return body.message || '';
      if (body.detail) {
        text = text.replace(/\{(\w+)\}/g, (whole, name) =>
          (Object.prototype.hasOwnProperty.call(body.detail, name) ? String(body.detail[name]) : whole));
      }
      return text;
    };

    const miss = await call('/api/templates-export/' + encodeURIComponent('根本没有这个.json'), 'GET');
    ok('报错·导出缺失带 detail', !!miss.payload.detail, JSON.stringify(miss.payload.detail));
    ok('报错·导出缺失文案填满占位符', render(miss.payload).indexOf('{') < 0, render(miss.payload));

    const bad = await call('/api/templates', 'POST', { name: '../evil', tree: { A: {} } });
    ok('报错·非法名带 detail', !!bad.payload.detail, JSON.stringify(bad.payload.detail));
    ok('报错·非法名文案填满占位符', render(bad.payload).indexOf('{') < 0, render(bad.payload));

    const dup1 = await call('/api/templates', 'POST', { name: '重复名', tree: { X: {} } });
    ok('报错·首次新建成功', dup1.status === 200, 'status=' + dup1.status);
    const dup2 = await call('/api/templates', 'POST', { name: '重复名', tree: { X: {} } });
    ok('报错·同名冲突带 detail', !!dup2.payload.detail, JSON.stringify(dup2.payload.detail));
    ok('报错·同名冲突文案填满占位符', render(dup2.payload).indexOf('{') < 0, render(dup2.payload));

    const big = {};
    for (let i = 0; i < 520; i += 1) { big['f' + i] = ''; }
    const over = await call('/api/generate', 'POST', { tree: big });
    ok('报错·规模超限带 detail', !!over.payload.detail, JSON.stringify(over.payload.detail));
    ok('报错·规模超限文案填满占位符', render(over.payload).indexOf('{') < 0, render(over.payload));
  }

  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
})().catch((err) => {
  out.push({ name: '探针异常', pass: false, extra: String(err && (err.stack || err.message || err.name)) });
  process.stdout.write('RESULT ' + JSON.stringify(out) + '\n');
});
"""


class DemoExportTests(unittest.TestCase):
    """Node 驱动：锁住在线版导出链路的「与列表同源」契约。"""

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
            raise unittest.SkipTest("本机无 node —— 在线版导出契约测试跳过")
        for need in (_BACKEND_JS, _MD_JS):
            if not need.is_file():
                raise unittest.SkipTest(f"缺 {need}")

        tmp = tempfile.TemporaryDirectory(prefix="qm_export_")
        cls.addClassCleanup(tmp.cleanup)
        harness = Path(tmp.name) / "probe.cjs"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        env = dict(os.environ, QM_BACKEND_JS=str(_BACKEND_JS), QM_MD_JS=str(_MD_JS),
                   QM_LOCALE_JS=str(_LOCALE_JS))
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

    def test_export_from_bound_dir(self):
        """本次报障主场景：绑定真实模板目录后，导出必须能读到目录里的模板。"""
        self._ok("已绑定·列表读目录")
        self._ok("已绑定·导出 json 模板")
        self._ok("已绑定·导出 md 模板原样")

    def test_export_returns_original_text(self):
        """不传 format = 原样交回（导出→再导入须与原件一致，不能被再序列化）。"""
        self._ok("已绑定·json 原样交回")
        self._ok("已绑定·导出 md 模板原样")

    def test_export_format_conversion(self):
        """`?format=` 双向转换可用，且转出的 json 能被解析回来。"""
        self._ok("已绑定·json→md 转换")
        self._ok("已绑定·md→json 转换")
        self._ok("已绑定·转出的 json 可解析")

    def test_export_missing_still_404(self):
        """放宽读取面后，目标不存在仍须 404 —— 不得变成「假成功」。"""
        self._ok("已绑定·目录里没有仍 404")
        self._ok("未绑定·不存在的模板 404")

    def test_export_unbound_regression(self):
        """回归位：未绑定目录时，浏览器内模板与内置空白模板照常可导出。"""
        self._ok("未绑定·导出浏览器内模板")
        self._ok("未绑定·导出内置空白模板")
        self._ok("未绑定·json→md 转换")

    def test_backup_export_unaffected(self):
        """备份导出（服务设置面板）与本条改动无关，必须仍然可用。"""
        self._ok("备份导出可用")
        self._ok("备份文件名合规")

    def test_error_messages_fill_placeholders(self):
        """错误响应必须带 `detail`，否则用户会看到字面量 `{name}`。

        由来：2026-10-21 用户报障原话是「导出失败：模板不存在：{name}」—— 占位符
        没被替换。根因不在导出逻辑，而在 `fail()` 从不传 `detail`，而前端
        `localizeError()` 依 `code` + `detail` 重新成句。这类缺陷对读 payload 的
        探针不可见（`message` 字段本身是渲染好的整句），只有按前端逻辑渲染才现形。
        """
        self._ok("报错·导出缺失带 detail")
        self._ok("报错·导出缺失文案填满占位符")
        self._ok("报错·非法名带 detail")
        self._ok("报错·非法名文案填满占位符")
        self._ok("报错·首次新建成功")
        self._ok("报错·同名冲突带 detail")
        self._ok("报错·同名冲突文案填满占位符")
        self._ok("报错·规模超限带 detail")
        self._ok("报错·规模超限文案填满占位符")


if __name__ == "__main__":
    unittest.main()
