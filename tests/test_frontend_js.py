"""青蔓 QingMan · 前端核心 Node 驱动测试（src 审查第四档 · 批 4B / 4C / 4D）。

`modules/tree-model.js`、`core/*.js` 与 `ui/tree-view.js`（顶层只 import + 函数声明）
均**无顶层 DOM 依赖**，可在 Node 中直接作 ESM 导入。本模块把一段断言脚本写成临时 `.mjs`，
交给托管 `node` 执行，读回 `RESULT <json>` 逐项判定。

覆盖批 4B：B-P3-1（网络失败归一）/ B-P3-3（renameNode 自校验）/ B-P3-4（toPlainTree
重名告警）/ B-P3-5（查询族深树不爆栈）/ B-P3-6（bus.off 后不再触发）。
覆盖批 4C：C-P3-3（`leftRow`「算不算离开」判定，含 relatedTarget 为 null 的坐标兜底）。
覆盖 V0.0.43 · F 组：`modules/selection.js` 的选择集合语义（净化 / 多选门槛 /
最外层祖先去重 / 批量移动预检）。
覆盖批 4D：4D-1（`toDocumentNode` 深链不爆栈）/ 4D-2（`fromDocumentNode` 深链不爆栈
+ 往返结构保真），20000 层 = `MAX_EDITOR_NODES`，旧递归版在此必 `RangeError`。
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
  /* V0.0.42：根节点名 = 「根文件夹名」—— 放开改名；允许置空（= 不建根）；
     但**非法字符仍拒**（自校验不因放开而失效）；非根节点空名仍拒。 */
  ok('B-P3-3/root-renamable', tm.renameNode(root, root.id, 'zz') === true && root.name === 'zz');
  ok('B-P3-3/root-blank-is-noroot', tm.renameNode(root, root.id, '') === true && root.name === '');
  ok('B-P3-3/root-illegal-still-rejected', tm.renameNode(root, root.id, 'a/b') === false && root.name === '');
  ok('B-P3-3/nonroot-blank-still-rejected', tm.renameNode(root, b.id, '') === false && b.name === 'c.txt');
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

/* ---------- 批 4D 序列化族深链不爆栈（20000 == MAX_EDITOR_NODES；旧递归版必 RangeError） ---------- */
{
  const root = tm.createDir('r');
  let cur = root;
  for (let i = 0; i < 20000; i++) {
    const d = tm.createDir('d' + i);
    tm.addChild(cur, d);
    cur = d;
  }
  /* 最深处是**无子目录的空 dir**（使下潜计数恰为 20000）；文件另挂根下，用于往返内容断言 */
  tm.addChild(root, tm.createFile('leaf.txt', 'x'));

  let doc = null; let docErr = '';
  try { doc = tm.toDocumentNode(root); } catch (e) { docErr = String((e && e.message) || e); }
  ok('4D-1/toDocumentNode', docErr === '' && !!doc && doc.type === 'dir', docErr);
  /* 深度用迭代下潜点算（不可 JSON.stringify —— 它自身也会在深链上爆栈） */
  let d1 = doc; let depth1 = 0;
  while (d1 && d1.type === 'dir' && d1.children && d1.children.length) { d1 = d1.children[0]; depth1 += 1; }
  ok('4D-1/depth', depth1 === 20000, depth1);

  let back = null; let backErr = '';
  try { back = tm.fromDocumentNode(doc); } catch (e) { backErr = String((e && e.message) || e); }
  ok('4D-2/fromDocumentNode', backErr === '' && !!back && back.type === 'dir', backErr);
  let d2 = back; let depth2 = 0;
  while (d2 && d2.type === 'dir' && d2.children && d2.children.length) { d2 = d2.children[0]; depth2 += 1; }
  ok('4D-2/depth', depth2 === 20000, depth2);
  ok('4D-2/leaf', !!back && back.children[1] && back.children[1].name === 'leaf.txt'
    && back.children[1].content === 'x',
    back && back.children[1] ? back.children[1].name : 'null');
}

/* ---------- 批 4D 报错顺序保真（前序：更深子树里的非法节点先被抛出） ---------- */
{
  /* 深层非法（缺 name）+ 浅层兄弟也非法（缺 name）。原实现前序下潜，故先抛深层路径。
     迭代版以「帧 + 游标」复刻同一顺序；若改成先把同层子节点全过一遍即会改变结果。 */
  const raw = {
    type: 'dir', name: 'r', children: [
      { type: 'dir', name: 'a', children: [{ type: 'file' }] },
      { type: 'file' },
    ],
  };
  let msg = '';
  try { tm.fromDocumentNode(raw); } catch (e) { msg = String((e && e.message) || e); }
  ok('4D-2/errorOrder', msg.indexOf('$.children[0].children[0]') >= 0, msg);
}

/* ---------- 批 4D 往返保真（小树：name / note / content / 源顺序） ---------- */
{
  const root = tm.createDir('r');
  root.note = 'root-note';
  const a = tm.createDir('a');
  a.note = 'a-note';
  tm.addChild(root, a);
  tm.addChild(a, tm.createFile('f.txt', 'hello'));
  tm.addChild(root, tm.createFile('z.txt', 'last'));
  const doc = tm.toDocumentNode(root);
  const back = tm.fromDocumentNode(doc);
  ok('4D-2/roundtrip',
    back.name === 'r' && back.note === 'root-note'
    && back.children.length === 2
    && back.children[0].name === 'a' && back.children[0].note === 'a-note'
    && back.children[0].children[0].name === 'f.txt'
    && back.children[0].children[0].content === 'hello'
    && back.children[1].name === 'z.txt' && back.children[1].content === 'last',
    back.children.length);
}

/* ---------- V0.0.43 · F 组：选择集合语义（modules/selection.js，纯函数） ----------
   本组最重的不变式是 outermostIds ——「父子同选只作用于最外层祖先」。
   注意「删掉的行数」在这条规则上**不具判别力**（逐个删时子节点已随父消失，
   第二次 removeNode 返回 false，最终行数相同），故必须在纯函数层直接钉住。 */
{
  const sel = await import(SRC + '/modules/selection.js');
  /* 选择语义用一棵专用小树：r → a → a1 → a11 ；r → b */
  const sr = tm.createDir('r');
  const sa = tm.createDir('a'); tm.addChild(sr, sa);
  const sa1 = tm.createDir('a1'); tm.addChild(sa, sa1);
  const sa11 = tm.createDir('a11'); tm.addChild(sa1, sa11);
  const sb = tm.createDir('b'); tm.addChild(sr, sb);

  ok('F/liveIds-dropsRoot', sel.liveIds(sr, [sr.id, sa.id]).join() === sa.id);
  ok('F/liveIds-dropsGhost', sel.liveIds(sr, [sa.id, 'nope']).join() === sa.id);
  ok('F/multiSel-needsTwo',
    sel.multiSel(sr, [sa.id]).length === 0 && sel.multiSel(sr, [sa.id, sb.id]).length === 2);
  ok('F/outermost-childFirst', sel.outermostIds(sr, [sa1.id, sa.id]).join() === sa.id);
  ok('F/outermost-parentFirst', sel.outermostIds(sr, [sa.id, sa1.id]).join() === sa.id);
  ok('F/outermost-deepGrandchild',
    sel.outermostIds(sr, [sa11.id, sa.id, sa1.id]).join() === sa.id);
  ok('F/outermost-siblingsKept',
    sel.outermostIds(sr, [sa.id, sb.id]).join() === [sa.id, sb.id].join());
  ok('F/outermost-empty', sel.outermostIds(sr, []).length === 0);
  const all = sel.allNodeIds(sr);
  ok('F/allNodeIds-excludesRoot', all.indexOf(sr.id) < 0 && all.length === 4, all.length);

  /* canBatchMove：每个案子单独建树，避免相互干扰 */
  const mr = tm.createDir('r');
  const ma = tm.createDir('a'); tm.addChild(mr, ma);
  const ma1 = tm.createDir('a1'); tm.addChild(ma, ma1);
  const mb = tm.createDir('b'); tm.addChild(mr, mb);
  const mf = tm.createFile('f.txt', 'x'); tm.addChild(mr, mf);
  ok('F/canBatchMove-cycle', sel.canBatchMove(mr, [ma.id], ma1.id).code === 'cycle');
  ok('F/canBatchMove-notDir', sel.canBatchMove(mr, [mb.id], mf.id).code === 'notDir');
  ok('F/canBatchMove-missing', sel.canBatchMove(mr, ['nope'], mb.id).code === 'missing');
  const mx = tm.createDir('a'); tm.addChild(mb, mx);   /* 目标下已有一个同名 'a' */
  ok('F/canBatchMove-exists', sel.canBatchMove(mr, [ma.id], mb.id).code === 'exists');
  /* 同名者本身就是「已在目标下、又要移到目标下」的那一个 → 排除后不算冲突 */
  ok('F/canBatchMove-sameParentNoConflict', sel.canBatchMove(mr, [mx.id], mb.id).ok === true);
  ok('F/canBatchMove-ok', sel.canBatchMove(mr, [ma1.id], mb.id).ok === true);
}

/* ---------- V0.0.44 · 动态语言包（i18n/index.js） ----------
   `i18n/index.js` 顶层只 import 纯数据（语言包 + skins），DOM / localStorage 访问全在
   函数体内 —— 可作 ESM 直接导入。这里把「清单合成 / 母语名 / BCP 47 降级 / 非法形态收口」
   四条**纯逻辑**固化为回归网；运行时渲染由 `browser_smoke` 覆盖。 */
{
  const i18n = await import(SRC + '/i18n/index.js');
  const win = globalThis.window;

  /* 无注入清单时：可用语言 = 出厂内置两语，顺序稳定 */
  delete win.__QM_LOCALES__;
  ok('i18n/supported-builtin',
     i18n.supportedLocales().join(',') === 'zh-CN,en-US',
     i18n.supportedLocales().join(','));

  /* 母语自描述名；未知语言回落代码本身（不让它凭空消失） */
  ok('i18n/name-zh', i18n.localeName('zh-CN') === '简体中文', i18n.localeName('zh-CN'));
  ok('i18n/name-en', i18n.localeName('en-US') === 'English', i18n.localeName('en-US'));
  ok('i18n/name-fallback', i18n.localeName('xx-YY') === 'xx-YY', i18n.localeName('xx-YY'));

  /* 注入清单：排在内置之前；形态非法（含路径穿越面）的项被白名单过滤；与内置重复不重列 */
  win.__QM_LOCALES__ = [
    { code: 'fr-FR', name: 'Français' },
    { code: '../evil', name: 'x' },
    { code: 'zh-CN', name: '简体中文' },
  ];
  ok('i18n/supported-injected',
     i18n.supportedLocales().join(',') === 'fr-FR,zh-CN,en-US',
     i18n.supportedLocales().join(','));
  ok('i18n/name-injected', i18n.localeName('fr-FR') === 'Français', i18n.localeName('fr-FR'));
  ok('i18n/match-injected', i18n.matchLocale('fr-CA') === 'fr-FR', i18n.matchLocale('fr-CA'));
  delete win.__QM_LOCALES__;

  /* BCP 47 降级链：逐级剥离子标签 → 主语言回退；大小写 / 下划线兼容 */
  ok('i18n/match-exact', i18n.matchLocale('en-US') === 'en-US', i18n.matchLocale('en-US'));
  ok('i18n/match-strip', i18n.matchLocale('zh-Hant-TW') === 'zh-CN', i18n.matchLocale('zh-Hant-TW'));
  ok('i18n/match-primary', i18n.matchLocale('EN_gb') === 'en-US', i18n.matchLocale('EN_gb'));
  ok('i18n/match-none', i18n.matchLocale('de-DE') === null, i18n.matchLocale('de-DE'));
  ok('i18n/match-empty', i18n.matchLocale('') === null, i18n.matchLocale(''));

  /* loadLocale：内置立即 true；形态非法立即 false；清单有但文件缺失 → 降级 false 不抛 */
  ok('i18n/load-builtin', (await i18n.loadLocale('zh-CN')) === true);
  ok('i18n/load-bad-shape', (await i18n.loadLocale('../x')) === false);
  ok('i18n/load-missing', (await i18n.loadLocale('de-DE')) === false);

  /* 帮助分节与当前语言同源（默认 zh-CN）：非空数组 */
  ok('i18n/help-nonempty',
     Array.isArray(i18n.getHelpSections()) && i18n.getHelpSections().length > 0,
     i18n.getHelpSections().length);
}

/* ---------- V0.3.3 模板排序口径（modules/tpl-order.js） ---------- */
{
  const order = await import(SRC + '/modules/tpl-order.js');
  const mk = (file, name) => ({ file, name });
  const seq = (rows) => rows.map((r) => r.file).join(',');
  const NAME = order.SORT_NAME;
  const EVENT = order.SORT_EVENT;
  const ev = (fresh, usage) => ({ mode: EVENT, usage: usage || {}, fresh: fresh || {} });

  /* ① `SORT_NAME`：纯名称序 —— 新建段与使用记录**一起让位**。
        这是「首次进入 / 点刷新」的唯一口径，少让任何一个都会破坏基线。 */
  ok('TPL/name-mode',
     seq(order.sortTemplates([mk('b.json', 'B'), mk('a.json', 'A')],
       { mode: NAME, usage: { 'b.json': { last: 9e12, count: 99 } },
         fresh: { created: ['b.json'] } })) === 'a.json,b.json',
     seq(order.sortTemplates([mk('b.json', 'B'), mk('a.json', 'A')],
       { mode: NAME, usage: { 'b.json': { last: 9e12, count: 99 } },
         fresh: { created: ['b.json'] } })));

  /* ② ① 新建压过一切：名字排在最后也照样置顶 */
  ok('TPL/new-first',
     seq(order.sortTemplates([mk('z.json', 'Z'), mk('a.json', 'A')],
       ev({ created: ['z.json'] }))) === 'z.json,a.json',
     seq(order.sortTemplates([mk('z.json', 'Z'), mk('a.json', 'A')],
       ev({ created: ['z.json'] }))));

  /* ③ 段序 新建 > 单个导入 > 批量导入 > 其余（名字的字母序不得干扰段序） */
  ok('TPL/seg-order',
     seq(order.sortTemplates(
       [mk('a.json', 'A'), mk('b.json', 'B'), mk('c.json', 'C'), mk('d.json', 'D')],
       ev({ created: ['c.json'], single: ['b.json'], batch: ['a.json'] })))
       === 'c.json,b.json,a.json,d.json',
     seq(order.sortTemplates(
       [mk('a.json', 'A'), mk('b.json', 'B'), mk('c.json', 'C'), mk('d.json', 'D')],
       ev({ created: ['c.json'], single: ['b.json'], batch: ['a.json'] }))));

  /* ④ 同一段内按名称 —— 这就是「同时载入的多个模板按名称」。
        **只对 ③（批量导入 / 外部新增）成立**：那一批是同一个动作推进来的，批内无先后。 */
  ok('TPL/batch-by-name',
     seq(order.sortTemplates([mk('3.json', 'c'), mk('1.json', 'a'), mk('2.json', 'b')],
       ev({ batch: ['3.json', '1.json', '2.json'] }))) === '1.json,2.json,3.json',
     seq(order.sortTemplates([mk('3.json', 'c'), mk('1.json', 'a'), mk('2.json', 'b')],
       ev({ batch: ['3.json', '1.json', '2.json'] }))));

  /* ④b V0.3.8 **① 段内按操作先后、后建的在前**（旧实现按名称 → 用户报「新建的没排前面」）。
        实测样本：依次新建 甲 → 乙 → 辛，旧口径输出 `乙,甲,辛`（中文按 UTF-16 码位，
        最新建的「辛」垫底）；新口径应为 `辛,乙,甲`。
        注意这条**不依赖名称序**：即使名称升序与操作序一致也判得出（见 ④c）。 */
  ok('TPL/created-latest-first',
     seq(order.sortTemplates(
       [mk('jia.json', '甲'), mk('yi.json', '乙'), mk('xin.json', '辛')],
       ev({ created: ['jia.json', 'yi.json', 'xin.json'] })))
       === 'xin.json,yi.json,jia.json',
     seq(order.sortTemplates(
       [mk('jia.json', '甲'), mk('yi.json', '乙'), mk('xin.json', '辛')],
       ev({ created: ['jia.json', 'yi.json', 'xin.json'] }))));

  /* ④c 反向对照：操作序与名称升序**故意相反**（先建 A 再建 Z）——
        按名称排会得到 `a,z`，按操作先后应为 `z,a`。这一条才是判据本身。 */
  ok('TPL/created-defies-name',
     seq(order.sortTemplates([mk('a.json', 'A'), mk('z.json', 'Z')],
       ev({ created: ['a.json', 'z.json'] }))) === 'z.json,a.json',
     seq(order.sortTemplates([mk('a.json', 'A'), mk('z.json', 'Z')],
       ev({ created: ['a.json', 'z.json'] }))));

  /* ④d ② 段同理：两次独立单选导入，后导入的在前 */
  ok('TPL/single-latest-first',
     seq(order.sortTemplates([mk('a.json', 'A'), mk('z.json', 'Z')],
       ev({ single: ['a.json', 'z.json'] }))) === 'z.json,a.json',
     seq(order.sortTemplates([mk('a.json', 'A'), mk('z.json', 'Z')],
       ev({ single: ['a.json', 'z.json'] }))));

  /* ⑤ **用过即出队**：仍在新建段里的模板，只要次数 ≥ 1 就退出，改按最近使用排。
        漏掉这条，新建的模板会永远压顶，④⑤ 再也轮不到。 */
  ok('TPL/used-leaves',
     seq(order.sortTemplates([mk('fresh.json', '新建的'), mk('a.json', 'A')],
       ev({ created: ['fresh.json'] },
          { 'fresh.json': { last: 1, count: 1 }, 'a.json': { last: 2, count: 1 } })))
       === 'a.json,fresh.json',
     seq(order.sortTemplates([mk('fresh.json', '新建的'), mk('a.json', 'A')],
       ev({ created: ['fresh.json'] },
          { 'fresh.json': { last: 1, count: 1 }, 'a.json': { last: 2, count: 1 } }))));

  /* ⑥ 其余段：最近使用在前 */
  ok('TPL/rest-recent',
     seq(order.sortTemplates([mk('old.json', '同名'), mk('new.json', '同名')],
       ev({}, { 'old.json': { last: 100, count: 5 }, 'new.json': { last: 200, count: 1 } })))
       === 'new.json,old.json',
     seq(order.sortTemplates([mk('old.json', '同名'), mk('new.json', '同名')],
       ev({}, { 'old.json': { last: 100, count: 5 }, 'new.json': { last: 200, count: 1 } }))));

  /* ⑦ 其余段：最近使用打平 → 次数多的在前 */
  ok('TPL/rest-count',
     seq(order.sortTemplates([mk('rare.json', '同名'), mk('often.json', '同名')],
       ev({}, { 'rare.json': { last: 100, count: 1 }, 'often.json': { last: 100, count: 9 } })))
       === 'often.json,rare.json',
     seq(order.sortTemplates([mk('rare.json', '同名'), mk('often.json', '同名')],
       ev({}, { 'rare.json': { last: 100, count: 1 }, 'often.json': { last: 100, count: 9 } }))));

  /* ⑧ 全打平 → 名称 → 文件名（大小写不敏感） */
  ok('TPL/tie-name-file',
     seq(order.sortTemplates([mk('B.json', '同名'), mk('a.json', '同名')], ev({})))
       === 'a.json,B.json',
     seq(order.sortTemplates([mk('B.json', '同名'), mk('a.json', '同名')], ev({}))));

  /* ⑨ 记录是脏的（null / 字符串 / 对象）不抛错，按「无记录」处理 */
  let dirtyOk = true;
  try {
    dirtyOk = seq(order.sortTemplates([mk('b.json', '一样'), mk('a.json', '一样')],
      ev({}, { 'a.json': null, 'b.json': { last: 'oops', count: {} } }))) === 'a.json,b.json';
  } catch (err) {
    dirtyOk = false;
  }
  ok('TPL/dirty-usage', dirtyOk, String(dirtyOk));

  /* ⑩ `fresh` 整个缺失 / 非数组 → 退化为全名称序，不抛 */
  ok('TPL/no-fresh',
     seq(order.sortTemplates([mk('b.json', 'B'), mk('a.json', 'A')], { mode: EVENT }))
       === 'a.json,b.json',
     seq(order.sortTemplates([mk('b.json', 'B'), mk('a.json', 'A')], { mode: EVENT })));

  /* ⑪ 不改入参、返回新数组 */
  const srcRows = [mk('b.json', 'B'), mk('a.json', 'A')];
  const sortedRows = order.sortTemplates(srcRows, ev({}));
  ok('TPL/no-mutate',
     seq(srcRows) === 'b.json,a.json' && sortedRows !== srcRows,
     seq(srcRows));

  /* ⑫ 非数组入参退化为空数组，不抛 */
  ok('TPL/empty', Array.isArray(order.sortTemplates(null)) && order.sortTemplates(null).length === 0);

  /* ⑬ V0.3.4 首次进入 / 刚点刷新：**只登记 known、不建 ③ 段**。
        旧实现把整库存量写进 batch，靠 mode 暂时掩盖；一旦 mode 切 EVENT，
        存量就冒充「本次批量导入」，把用过的模板压到后面（回归位见 ⑯）。 */
  const fs1 = order.planExternal(
    { mode: NAME, created: [], single: [], batch: [], known: [] },
    ['a.json', 'b.json']);
  ok('TPL/ext-first-sight',
     fs1.firstSight === true && fs1.session.mode === NAME
       && fs1.session.batch.length === 0
       && fs1.session.known.join(',') === 'a.json,b.json',
     JSON.stringify(fs1.session));

  /* ⑭ 之后才出现的外部新增：进 ③ 段，并把 mode 切到 EVENT */
  const fs2 = order.planExternal(
    { mode: NAME, created: [], single: [], batch: [], known: ['a.json'] },
    ['a.json', 'c.json']);
  ok('TPL/ext-later',
     fs2.firstSight === false && fs2.session.mode === EVENT
       && fs2.session.batch.join(',') === 'c.json',
     JSON.stringify(fs2.session));

  /* ⑮ 导入分段：一次 1 个 → ②（single）；一次多个 → ③（batch）。
        判据是**选了几个**，不是「成功几个」—— 选 5 个、4 个同名跳过仍是批量导入。 */
  ok('IMP/bucket',
     order.importBucket(1) === 'single' && order.importBucket(3) === 'batch'
       && order.importBucket(0) === 'single',
     `${order.importBucket(1)}/${order.importBucket(3)}`);

  /* ⑯ 用户实测现象的回归位：首次进入（6 套）→ 载入 C → **C 必须排第一**。
        旧行为实测为 a,b,d,e,f,c（用过的垫底）。 */
  const boot = order.planExternal(
    { mode: NAME, created: [], single: [], batch: [], known: [] },
    ['A.json', 'B.json', 'C.json', 'D.json', 'E.json', 'F.json']).session;
  const six = ['A', 'B', 'C', 'D', 'E', 'F'].map((ch) => mk(ch + '.json', ch));
  const afterUse = { mode: EVENT, usage: { 'C.json': { last: 1, count: 1 } }, fresh: boot };
  ok('TPL/used-first-after-boot',
     seq(order.sortTemplates(six, afterUse)) === 'C.json,A.json,B.json,D.json,E.json,F.json',
     seq(order.sortTemplates(six, afterUse)));
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
        # V0.0.42：B-P3-3/root 反转为 root-renamable / root-blank-is-noroot /
        #          root-illegal-still-rejected / nonroot-blank-still-rejected
        for n in ("B-P3-3/illegal", "B-P3-3/dup", "B-P3-3/ok",
                  "B-P3-3/root-renamable", "B-P3-3/root-blank-is-noroot",
                  "B-P3-3/root-illegal-still-rejected", "B-P3-3/nonroot-blank-still-rejected"):
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

    def test_4d_deep_serialization(self):
        """批 4D · 序列化族深链（20000 = MAX_EDITOR_NODES）不爆栈；旧递归版必 RangeError。"""
        for n in ("4D-1/toDocumentNode", "4D-1/depth",
                  "4D-2/fromDocumentNode", "4D-2/depth", "4D-2/leaf"):
            self._ok(n)

    def test_4d_error_order_and_roundtrip(self):
        """批 4D · 前序报错顺序保真（更深子树的错先抛）+ 小树往返保真。"""
        for n in ("4D-2/errorOrder", "4D-2/roundtrip"):
            self._ok(n)

    def test_v043_selection_semantics(self):
        """V0.0.43 · F 组：选择集合语义（净化 / 多选门槛 / 最外层祖先去重 / 批量移动预检）。

        `outermostIds` 是本组唯一「行为上不可从结果反推」的规则 —— 见 HARNESS 里的注释。
        """
        for n in ("F/liveIds-dropsRoot", "F/liveIds-dropsGhost", "F/multiSel-needsTwo",
                  "F/outermost-childFirst", "F/outermost-parentFirst",
                  "F/outermost-deepGrandchild", "F/outermost-siblingsKept", "F/outermost-empty",
                  "F/allNodeIds-excludesRoot",
                  "F/canBatchMove-cycle", "F/canBatchMove-notDir", "F/canBatchMove-missing",
                  "F/canBatchMove-exists", "F/canBatchMove-sameParentNoConflict",
                  "F/canBatchMove-ok"):
            self._ok(n)

    def test_v033_template_order(self):
        """V0.3.3 · 模板排序六段：新建 → 单个导入 → 批量导入 → 最近使用 → 次数 → 名称。

        这是**用户可见行为**，两条最容易被后人「顺手改掉」，故逐条钉住：
        ① `SORT_NAME` 模式必须**同时**忽略新建段与使用记录 —— 少让任何一个，
           「点刷新回到名称序」就不干净；
        ② 段 ①②③ 只收「未使用过」的模板（`count > 0` 即出队）—— 少了这条，
           新建的会永远压顶，④⑤ 再也轮不到，等于把六段退化成一节。
        """
        for n in ("TPL/name-mode", "TPL/new-first", "TPL/seg-order", "TPL/batch-by-name",
                  "TPL/created-latest-first", "TPL/created-defies-name",
                  "TPL/single-latest-first",
                  "TPL/used-leaves", "TPL/rest-recent", "TPL/rest-count",
                  "TPL/tie-name-file", "TPL/dirty-usage", "TPL/no-fresh",
                  "TPL/no-mutate", "TPL/empty", "TPL/ext-first-sight", "TPL/ext-later",
                  "IMP/bucket", "TPL/used-first-after-boot"):
            self._ok(n)

    def test_v044_dynamic_locales(self):
        """V0.0.44 · 动态语言包：清单合成 / 母语名 / BCP 47 降级 / 非法形态收口。

        这四条都是**纯逻辑**（不依赖 DOM 渲染），却决定「新增语言包能否被发现、
        能不能被正确匹配、坏包是否拖垮清单」—— 故固化为回归网，而非只靠静态守卫。
        """
        for n in ("i18n/supported-builtin", "i18n/name-zh", "i18n/name-en",
                  "i18n/name-fallback", "i18n/supported-injected", "i18n/name-injected",
                  "i18n/match-injected", "i18n/match-exact", "i18n/match-strip",
                  "i18n/match-primary", "i18n/match-none", "i18n/match-empty",
                  "i18n/load-builtin", "i18n/load-bad-shape", "i18n/load-missing",
                  "i18n/help-nonempty"):
            self._ok(n)


if __name__ == "__main__":
    unittest.main()
