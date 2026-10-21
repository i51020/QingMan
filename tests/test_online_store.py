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
本测试立刻红。另覆盖**目标位置的独立存储**：`targetDir` 与 `templatesDir` 分键，
两个方向都不得互相影响（选目标不动模板库、改绑模板库不动目标）。

第四条契约（2026-10-17 追加）：**读写必须同源**。绑定真实目录后，新建 / 改名 / 删除的落点
必须是那个目录，不能仍写 `localStorage` —— 否则列表读目录、写操作写浏览器，模板"存了却看不见"。

第三条契约（2026-10-17 追加）：**列表顺序必须由代码规定，不得沿用文件系统枚举序**。
`FileSystemDirectoryHandle.values()` 不承诺稳定（Windows 目录索引 / 同步盘 / 增删改名都会变），
前端轮询的签名又是 `file|mtime|size` 按序拼接 —— 顺序一抖，签名就"变了"，列表每 2.5s 重建。
故 `readDirTemplates` 结果统一过 `byFile`（按文件名小写、再比原名，与本机版同口径）。
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
        delete: (key) => {
          delete data[key];
          const req = {};
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
let pickOpts = null;   /* 捕获 showDirectoryPicker 入参：授权模式必须看得见、断言得了 */
const win = {
  indexedDB: fakeIdb(),
  localStorage: fakeLocalStorage(),
  showDirectoryPicker: (opts) => { pickOpts = opts || null; return Promise.resolve(nextHandle); },
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

  /* ⑥ 目标位置与模板库**分键**：选目标不动模板库 */
  /* 目标句柄要带 queryPermission：真实 FileSystemDirectoryHandle 一定有，
     预热时靠它判断"写权限是否还在手"（权限为 prompt 就该重弹，别硬写）。 */
  nextHandle = { name: '生成目标', queryPermission: () => Promise.resolve('granted') };
  const tg = await STORE.pickTarget();
  ok('pickTarget 返回目标目录', tg && tg.name === '生成目标', tg && tg.name);
  ok('peekTarget 同步可见', !!STORE.peekTarget() && STORE.peekTarget().name === '生成目标');
  const tplAfter = await STORE.getDir();
  ok('选目标位置不动模板库', !!tplAfter && tplAfter.name === '目标文件夹', tplAfter && tplAfter.name);

  /* ⑦ 反向：改绑模板库不动目标 */
  nextHandle = { name: '新模板库' };
  await STORE.pickDir();
  await STORE.commitDir('新模板库');
  ok('绑模板目录不动目标', !!STORE.peekTarget() && STORE.peekTarget().name === '生成目标');

  /* ⑧ 预热：重开页面后仍能认出目标（权限 granted 的前提） */
  ok('preload 后仍可见目标', (await STORE.preloadTarget()) && !!STORE.peekTarget());

  /* ⑨ 清空本机数据：忘记目标，但保留模板库句柄 */
  STORE.clearAll();
  ok('清空忘记目标位置', STORE.peekTarget() == null);
  const tplKeep = await STORE.getDir();
  ok('清空保留模板库', !!tplKeep && tplKeep.name === '新模板库', tplKeep && tplKeep.name);

  /* ⑩ 模板列表顺序：枚举顺序不得泄漏到结果（用户报告「模板排序总是变化」） */
  function fakeDir(files) {
    return {
      name: '乱序库',
      values: function () {
        const arr = files.map(function (f) {
          return {
            kind: 'file',
            name: f.name,
            getFile: function () {
              return Promise.resolve({
                size: f.text.length,
                lastModified: 1700000000000,
                text: function () { return Promise.resolve(f.text); },
              });
            },
          };
        });
        let i = 0;
        return {
          next: function () {
            return Promise.resolve(i < arr.length ? { done: false, value: arr[i++] } : { done: true });
          },
        };
      },
    };
  }
  const files = (names) => names.map((n) => ({
    name: n,
    text: /\.json$/.test(n) ? '{"name":"' + n + '","tree":{"X":{}}}' : '# 标题\n',
  }));

  const orderA = (await STORE.readDirTemplates(fakeDir(files(['b.json', 'A.md', 'c.json', 'a.json']))))
    .map((x) => x.file);
  /* `'a.json' < 'A.md'`：小写化后 j(106) < m(109)；仅大小写不同时再比原名 */
  const want = ['a.json', 'A.md', 'b.json', 'c.json'];
  ok('乱序枚举也按文件名排', JSON.stringify(orderA) === JSON.stringify(want), orderA.join(','));

  const orderB = (await STORE.readDirTemplates(fakeDir(files(['c.json', 'a.json', 'b.json', 'A.md']))))
    .map((x) => x.file);
  ok('枚举顺序变了结果不变', JSON.stringify(orderA) === JSON.stringify(orderB), orderB.join(','));

  const caseOrder = (await STORE.readDirTemplates(fakeDir(files(['a.json', 'A.json']))))
    .map((x) => x.file);
  ok('仅大小写不同按原名定序', JSON.stringify(caseOrder) === JSON.stringify(['A.json', 'a.json']),
     caseOrder.join(','));

  const once = STORE.sortByFile(orderA.map((f) => ({ file: f }))).map((x) => x.file);
  ok('排序幂等', JSON.stringify(STORE.sortByFile(once.map((f) => ({ file: f }))).map((x) => x.file))
     === JSON.stringify(once), once.join(','));

  /* ⑪ 写目录：读写同源的地基（dirFileExists / writeDirFile / removeDirEntry） */
  function fakeWriteDir(disk) {
    return {
      name: '可写库',
      queryPermission: function () { return Promise.resolve('granted'); },
      getFileHandle: function (f, opt) {
        if (!(f in disk) && !(opt && opt.create)) {
          var miss = new Error('missing'); miss.name = 'NotFoundError';
          return Promise.reject(miss);
        }
        if (!(f in disk)) { disk[f] = ''; }
        return Promise.resolve({
          name: f,
          createWritable: function () {
            var buf = '';
            return Promise.resolve({
              write: function (s) { buf += String(s); return Promise.resolve(); },
              close: function () { disk[f] = buf; return Promise.resolve(); },
            });
          },
        });
      },
      removeEntry: function (f) {
        if (!(f in disk)) {
          var miss2 = new Error('missing'); miss2.name = 'NotFoundError';
          return Promise.reject(miss2);
        }
        delete disk[f];
        return Promise.resolve();
      },
    };
  }

  const disk = {};
  const wdir = fakeWriteDir(disk);
  ok('写前目录里没有', (await STORE.dirFileExists(wdir, '新模板.json')) === false);
  await STORE.writeDirFile(wdir, '新模板.json', '{"tree":{"甲":{}}}');
  ok('写后目录里有', (await STORE.dirFileExists(wdir, '新模板.json')) === true);
  ok('正文确实落盘', disk['新模板.json'] === '{"tree":{"甲":{}}}', disk['新模板.json']);
  await STORE.removeDirEntry(wdir, '新模板.json');
  ok('删后目录里没有', (await STORE.dirFileExists(wdir, '新模板.json')) === false);
  ok('删不存在不报错', (await STORE.removeDirEntry(wdir, '根本没有.json')) === true);

  /* ⑫ 绑定授权必须是**读写**（2026-10-18 报障「新建模板恒败」的根因）。
     读写同源（fe94be1）之后，模板目录既是素材库也是写落地；File System Access
     的权限按 mode 记录，只读授权满足不了 templateSink 的 readwrite 查询，
     且「再授权一次」走的还是只读 pick —— 死路。
     反方向安全：readwrite 授权隐含 read，列表的只读查询照常 granted。 */
  nextHandle = { name: '读写目录' };
  await STORE.pickDir();
  ok('pickDir 请求读写授权', !!pickOpts && pickOpts.mode === 'readwrite',
     pickOpts && pickOpts.mode);

  /* ⑬ 权限自愈：只读授权的老目录当场升级；一切失败（无方法 / 抛错 / 空句柄）
     一律回落 'denied'，由调用方回退到「重新选择目录」提示，绝不把成功当必然。 */
  ok('导出含权限升级', typeof STORE.requestDirPermission === 'function');
  const roHandle = {
    name: '旧只读库',
    queryPermission: function () { return Promise.resolve('prompt'); },
    requestPermission: function () { return Promise.resolve('granted'); },
  };
  ok('升级后拿到读写', (await STORE.requestDirPermission(roHandle, 'readwrite')) === 'granted');
  const noReq = { name: '无方法库', queryPermission: function () { return Promise.resolve('prompt'); } };
  ok('无 requestPermission 回落 denied',
     (await STORE.requestDirPermission(noReq, 'readwrite')) === 'denied');
  const thrower = {
    name: '会抛错的库',
    queryPermission: function () { return Promise.resolve('prompt'); },
    requestPermission: function () { return Promise.reject(new Error('no-gesture')); },
  };
  ok('requestPermission 抛错也回落 denied',
     (await STORE.requestDirPermission(thrower, 'readwrite')) === 'denied');
  ok('空句柄回落 denied', (await STORE.requestDirPermission(null, 'readwrite')) === 'denied');

  /* ⑭ pickDir **不得**再做任何权限动作（2026-10-21 回退位）。
     一度在这里加过「再查一次、必要时再请求一次」，实测帮倒忙：
       · picker 成功返回时权限本就已授予，再请求会**多弹一个确认框**（用户报「操作繁琐」）；
       · 该调用通常已无手势，浏览器可能记成 denied，反而把刚拿到的授权弄坏。
     故断言：pickDir 只返回句柄，**不查、不求**。 */
  let pickQueryCalled = 0;
  let pickRequestCalled = 0;
  nextHandle = {
    name: '不该多问的库',
    queryPermission: function () { pickQueryCalled += 1; return Promise.resolve('prompt'); },
    requestPermission: function () { pickRequestCalled += 1; return Promise.resolve('granted'); },
  };
  const straight = await STORE.pickDir();
  ok('pickDir 不多弹授权', pickRequestCalled === 0, 'requestPermission 次数=' + pickRequestCalled);
  ok('pickDir 不额外查权限', pickQueryCalled === 0, 'queryPermission 次数=' + pickQueryCalled);
  ok('pickDir 仍返回句柄', !!straight && straight.name === '不该多问的库', straight && straight.name);

  /* 没有权限 API 的句柄也不能把 pickDir 弄崩（旧内核 / 测试替身） */
  nextHandle = { name: '无权限API库' };
  const bare = await STORE.pickDir();
  ok('无权限 API 不阻断 pickDir', !!bare && bare.name === '无权限API库', bare && bare.name);

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

    def test_target_key_is_independent(self):
        self._ok("pickTarget 返回目标目录")
        self._ok("peekTarget 同步可见")
        self._ok("选目标位置不动模板库")
        self._ok("绑模板目录不动目标")

    def test_target_survives_reload_but_not_clear(self):
        self._ok("preload 后仍可见目标")
        self._ok("清空忘记目标位置")
        self._ok("清空保留模板库")

    def test_template_order_is_explicit(self):
        """用户报告「模板排序总是变化」：顺序必须由代码规定，不跟文件系统走。"""
        self._ok("乱序枚举也按文件名排")
        self._ok("枚举顺序变了结果不变")
        self._ok("仅大小写不同按原名定序")
        self._ok("排序幂等")

    def test_dir_write_primitives(self):
        """读写同源的地基：目录能判断存在、能写、能删，且删不存在的算成功。"""
        self._ok("写前目录里没有")
        self._ok("写后目录里有")
        self._ok("正文确实落盘")
        self._ok("删后目录里没有")
        self._ok("删不存在不报错")

    def test_rebind_still_works(self):
        self._ok("另一个目录也可按名绑定")
        self._ok("改绑后为新的目录")

    def test_pick_requests_readwrite(self):
        """绑定授权必须是读写：只读授权下写操作必败（2026-10-18 报障的根因）。"""
        self._ok("pickDir 请求读写授权")

    def test_request_dir_permission(self):
        """权限自愈：升级成功照常写；一切失败回落 denied，由调用方兜底提示。"""
        self._ok("导出含权限升级")
        self._ok("升级后拿到读写")
        self._ok("无 requestPermission 回落 denied")
        self._ok("requestPermission 抛错也回落 denied")
        self._ok("空句柄回落 denied")

    def test_pick_dir_does_not_ask_permission(self):
        """`pickDir` 只返回句柄，**不查也不求**权限（2026-10-21 回退）。

        用户报「选择目录时多次弹出需要确认的窗口，操作繁琐」—— picker 成功返回时
        权限本就已授予，再请求一次纯属多余，且无手势时可能把状态记成 denied。
        """
        self._ok("pickDir 不多弹授权")
        self._ok("pickDir 不额外查权限")
        self._ok("pickDir 仍返回句柄")
        self._ok("无权限 API 不阻断 pickDir")


if __name__ == "__main__":
    unittest.main()
