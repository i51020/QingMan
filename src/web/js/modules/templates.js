/**
 * 青蔓 QingMan · 模板库（V0.0.48 自 main.js 整体迁出 · 行为零变更）
 *
 * 与 V0.0.43 拆出 modules/selection.js 同因：解 `verify` 7f 的**单文件 64K** 上限。
 * 迁入函数体**保留原顶层缩进** —— 纯搬迁，故可逐字节比对。文案一律经 `t(key)`（§P0-3 L1）。
 * 边界：生成参数区的「目标位置 · 选择…」不属模板库，仍在 main.js。
 */

import { api } from '../core/api.js';
import { localizeError } from '../core/errors.js';
import { t } from '../i18n/index.js';
import { toast } from '../ui/toast.js';
import { fromNestedTree, adoptTemplateNote, treePayload } from './tree-model.js';

/** 与 main.js 同款取元素助手（各自持有 1 行，不为一个 1 行函数再拆模块）。 */
const el = (id) => document.getElementById(id);

/**
 * @param {object} ctx 由 main.js 装配：`el` / `t` / `ctxMenu` / `store` /
 *   `getLayers`（**getter** —— `layers` 迟至 `initTopbar()` 才赋值）/
 *   `pushHistory`（载入模板是一次可撤销的编辑）/ `setStatus` / `markDirty`。
 */
export function createTemplates({ ctxMenu, store, getLayers, pushHistory, setStatus, markDirty }) {

/* ---------- 模板库（V0.0.11） ---------- */

/* 错误本地化已迁至 ./core/errors.js（V0.0.12）：主界面与帮助页共用同一套 `err.<code>` 取词。 */

/* ---------- 模板目录绑定（V0.0.38 · 6E） ---------- */

/** 最近一次 `GET /api/templates-dir` 的响应；切换语言时用它重渲染动态文案（不再请求）。 */
let lastDirRes = null;

/**
 * 渲染绑定行：路径 + 状态提示。
 *
 * `source === 'default'` 表示**没绑外部目录**（用内置层）—— 这不是错误，
 * 但要说明白，否则用户会奇怪「为什么我放在别处的模板看不见」。
 * `valid === false`（自绑 / 系统区 / 不存在）才是真异常，展示后端给的原因。
 */
function renderTemplatesDir(res) {
  lastDirRes = res;
  const pathEl = el('tplDirPath');
  const hintEl = el('tplDirHint');
  const dir = (res && res.dir) || '';
  pathEl.textContent = dir || t('template.dirUnknown');
  pathEl.title = dir;

  let hint = '';
  if (res && res.source === 'default') hint = t('template.dirHintDefault');
  else if (res && res.valid === false) hint = t('template.dirHintInvalid', { reason: res.reason || '' });
  hintEl.textContent = hint;
  hintEl.hidden = !hint;

  // V0.0.51@r6：绑定变化后，帮助页「模板库位置」一行也要跟着变 —— 本模块是唯一
  // 知道运行态目录的地方，故在此派发事件（与 qmlocalechange / qmskinchange 同风格）。
  document.dispatchEvent(new CustomEvent('qmtpldirchange', { detail: res }));
}

async function loadTemplatesDir() {
  try {
    renderTemplatesDir(await api.templatesDir());
  } catch (err) {
    // 只读查询失败不该拖垮主流程：路径显示「未读取」，不弹提示
    renderTemplatesDir(null);
  }
}

/** 绑定目录 → 成功后刷新路径行与列表；被 env 遮蔽时如实提示（settings 已写但未生效）。 */
async function bindTemplatesDir(dir) {
  try {
    const res = await api.setTemplatesDir(dir);
    if (res.applied === false) {
      toast(t('template.dirEnvShadow', { dir: res.effectiveDir || '' }), 'warn', 6000);
    } else {
      toast(t('template.dirBound', { dir: res.dir || dir }), 'ok');
    }
    await loadTemplatesDir();
    await loadTemplateList();
  } catch (err) {
    toast(t('template.dirBindFailed', { message: localizeError(err) }), 'warn', 6000);
  }
}

/**
 * 「选择…」：优先原生目录框；本机用不了（缺 tkinter / 无 GUI / env 关断）则降级为
 * **手动粘贴路径**（设计文档《模板系统重设计_方案原型_20261011.md》第六节）。
 * 选中后只把路径交给 `bindTemplatesDir` —— 「选择」与「绑定」两步分离。
 */
async function chooseTemplatesDir() {
  let res;
  try {
    res = await api.pickTemplatesDir();
  } catch (err) {
    res = { available: false };   // 端点异常按能力缺失处理，走同一降级路径
  }
  if (res.available && !res.cancelled && res.dir) {
    await bindTemplatesDir(res.dir);
    return;
  }
  if (res.available && res.cancelled) return;   // 用户主动取消：静默
  const typed = window.prompt(t('template.dirPastePrompt'), el('tplDirPath').textContent || '');
  if (typed === null) return;
  const picked = typed.trim();
  if (picked) await bindTemplatesDir(picked);
}

function renderTemplateState(text, kind) {
  const host = el('templateList');
  host.textContent = '';
  const li = document.createElement('li');
  li.className = 'tpl-empty' + (kind ? ' tpl-' + kind : '');
  li.textContent = text;
  host.appendChild(li);
}

/* ---------- 模板列表轮询（V0.0.38 · 6E · MVP 2500ms） ---------- */

/**
 * 轮询间隔（毫秒）。设计文档第六节裁决：MVP 用**定时轮询**（零依赖；`watchdog` + SSE
 * 等增强留后续）。2500ms 是「外部改动能被及时察觉」与「不做无谓请求」的折中。
 */
const TPL_POLL_MS = 2500;

/** 最近一次渲染的签名；轮询据此判断「要不要重建 DOM」。 */
let tplSignature = '';
let tplPollTimer = null;

/** 模板列表渲染签名（V0.0.38 · 6E）：`available` + 每条 `file + mtime + size`。 */
function templateSignature(res) {
  const items = (res && res.items) || [];
  const avail = res && res.available === false ? '0' : '1';
  return avail + '\n' + items.map((i) => `${i.file}|${i.mtime}|${i.size}`).join('\n');
}

/**
 * 读取并渲染模板列表。
 *
 * `force`（默认）＝用户动作触发（启动 / 刷新 / 增删改后），无条件重建；
 * `force=false` ＝轮询触发，**签名没变就完全不碰 DOM** —— 否则每 2.5s 重建一次列表，
 * 正在浏览的用户会看到滚动位置被重置、hover 态丢失（设计文档第六节「避免抖动」）。
 * 轮询失败**静默**：保留上一次渲染，不把界面打成「不可用」（不然网络抖一次就闪一下红字）。
 */
async function loadTemplateList({ force = true } = {}) {
  if (force) renderTemplateState(t('template.loading'));
  let res;
  try {
    res = await api.listTemplates();
  } catch (err) {
    if (!force) return;   // 轮询失败：保留现状，不打扰
    renderTemplateState(localizeError(err) || t('template.unavailable'), 'warn');
    return;
  }
  const items = (res && res.items) || [];
  const sig = templateSignature(res);
  if (!force && sig === tplSignature) return;
  tplSignature = sig;

  // available=false：templates/ 不在版本清单内，预览副本中本就没有它 —— 不可用而非报错
  if (!res || res.available === false) {
    renderTemplateState(t('template.unavailable'), 'warn');
    return;
  }
  if (!items.length) {
    renderTemplateState(t('template.empty'));
    return;
  }

  const host = el('templateList');
  host.textContent = '';
  // 「内置 / 用户」按**当前绑定层**判（V0.0.38 · 6E）：还绑在内置层 → 内置；
  // 绑了外部目录 → 用户。列表整体同层，故徽标文案只需算一次。
  const layerKey = (!lastDirRes || lastDirRes.source === 'default')
    ? 'template.layerBuiltin' : 'template.layerUser';
  for (const item of items) {
    const li = document.createElement('li');
    li.className = 'tpl-row';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tpl-item';
    btn.title = item.description || item.name;
    const name = document.createElement('span');
    name.className = 'tpl-name';
    name.textContent = item.name;
    const meta = document.createElement('span');
    meta.className = 'tpl-meta';
    const badge = document.createElement('span');
    badge.className = 'tpl-badge';
    badge.textContent = t(layerKey);
    const stats = document.createElement('span');
    stats.className = 'tpl-stats';
    stats.textContent = t('template.stats', { dirs: item.dirs, files: item.files });
    meta.append(badge, stats);
    btn.append(name, meta);
    btn.addEventListener('click', () => applyTemplate(item));

    // V0.0.51@r11：行尾**常驻 ⋮**（恢复可发现性）。两条硬约束：
    //   ① **动作来源仍唯一** —— 点击只是把 `openTemplateContextMenu` 以按钮坐标为锚再调一次，
    //      **不另造菜单、不复制菜单项**；与右键共用同一个 `ctx-menu` 与同一份定位夹取。
    //      （设计稿 `prototype.html`「行尾 ⋮：打开既有 #ctxMenu …… 不另造一套」即此意。）
    //   ② **样式零新增** —— `.tpl-more` 的复位规则 `soft.css` 早已写好，此前因无消费者
    //      沦为死码；本按钮即其**唯一消费者**，故它是「复活」而非「新写」。基础态（占位 /
    //      半透明常驻 / 点亮）在 `layout.css` 的 `.tpl-row` 节。
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'btn btn-ghost btn-mini btn-ic tpl-more';
    more.title = t('template.moreTip');
    more.setAttribute('aria-label', t('template.more'));
    more.setAttribute('aria-haspopup', 'true');
    const moreIc = document.createElement('span');
    moreIc.className = 'ic ic-more';
    moreIc.setAttribute('aria-hidden', 'true');
    more.append(moreIc);
    more.addEventListener('click', () => {
      // 锚在按钮下沿左缘（视口坐标，同 `contextmenu` 的 clientX/Y 口径）——
      // 贴底时由 `ctx-menu` 自行向上翻转，此处不重复做边界判断。
      const box = more.getBoundingClientRect();
      openTemplateContextMenu(item, box.left, box.bottom);
    });

    // V0.0.38 · 6E：改名 / 删除等操作**收进右键菜单**（去常驻按钮），与目录树共用 `ctx-menu`
    li.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      openTemplateContextMenu(item, event.clientX, event.clientY);
    });

    li.append(btn, more);
    host.appendChild(li);
  }
}

/**
 * 模板行右键菜单（V0.0.38 · 6E）：载入 / 重命名 / 复制 / 导出 / 删除。
 * 与工具栏、目录树菜单同宗 —— `ctx-menu` 只管定位与开合，动作全在这里。
 */
function openTemplateContextMenu(item, x, y) {
  ctxMenu.showAt(x, y, [
    { label: t('template.load'), action: () => applyTemplate(item) },
    { label: t('template.rename'), action: () => renameTemplateItem(item) },
    { label: t('template.duplicate'), action: () => duplicateTemplateItem(item) },
    { label: t('template.export'), action: () => exportTemplateItem(item) },
    { label: t('template.delete'), danger: true, action: () => deleteTemplateItem(item) },
  ]);
}

/**
 * 复制模板为副本（V0.0.38 · 6E）。
 *
 * 【推断】设计文档只写「复制」。此处取「生成一份同内容、可编辑的新模板」——
 * 与「导出（下载到本地）」互补：前者留在库里继续用，后者带出工具外。
 * 落盘走 `saveTemplate`（目标恒为规范 `.json`），与「另存为」同一条路径。
 */
async function duplicateTemplateItem(item) {
  const input = window.prompt(t('template.duplicatePrompt'),
    t('template.copySuffix', { name: item.name }));
  if (input === null) return;
  const next = input.trim();
  if (!next || next === item.name) return;
  try {
    const res = await api.loadTemplate(item.file);
    await api.saveTemplate({ name: next, tree: res.tree });
    toast(t('template.duplicated', { name: next }), 'ok');
    await loadTemplateList();
  } catch (err) {
    toast(localizeError(err) || t('template.opFailed'), 'warn', 6000);
  }
}

/**
 * 导出模板（V0.0.38 · 6E）：取后端给的**原文**，按原扩展名触发下载。
 * 不在前端二次序列化 —— 后端那份才是真源，故「导出 → 再导入」与原件一致。
 */
async function exportTemplateItem(item) {
  try {
    const res = await api.exportTemplate(item.file);
    downloadText(res.file || item.file, res.text || '');
    toast(t('template.exported', { name: item.name }), 'ok');
  } catch (err) {
    toast(t('template.exportFailed', { message: localizeError(err) }), 'warn', 6000);
  }
}

/** 触发浏览器下载（纯前端、零依赖）。 */
function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // 立刻回收会让部分浏览器拿不到数据，延后一拍再撤销
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * 导入模板（V0.0.38 · 6E 接线）：浏览器原生文件选择 → 读文本 → 后端校验后落盘。
 *
 * 这里用 `<input type="file">` 而非后端对话框：读的是**文件内容**，浏览器本就能胜任；
 * 只有「目录选择」才必须走后端（浏览器拿不到绝对路径，见 `chooseTemplatesDir`）。
 */
function importTemplateFlow() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json,.md,application/json,text/markdown';
  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    let text;
    try {
      text = await file.text();
    } catch (err) {
      toast(t('template.importFailed', { message: localizeError(err) }), 'warn', 6000);
      return;
    }
    await submitImport(file.name, text);
  });
  input.click();
}

/** 提交导入；同名时询问是否覆盖（覆盖后旧模板由后端移入 `.trash/`，可找回）。 */
async function submitImport(filename, text) {
  try {
    await api.importTemplate({ filename, content: text });
  } catch (err) {
    if (!err || err.code !== 'templateExists') {
      toast(t('template.importFailed', { message: localizeError(err) }), 'warn', 6000);
      return;
    }
    if (!window.confirm(t('template.importOverwriteConfirm', { name: filename }))) return;
    try {
      await api.importTemplate({ filename, content: text, overwrite: true });
    } catch (err2) {
      toast(t('template.importFailed', { message: localizeError(err2) }), 'warn', 6000);
      return;
    }
  }
  toast(t('template.imported', { name: filename }), 'ok');
  await loadTemplateList();
}

/** 开/停轮询定时器（幂等：重复开不会叠出多个 interval）。 */
function setTemplatePolling(on) {
  if (on && !tplPollTimer) {
    tplPollTimer = window.setInterval(() => loadTemplateList({ force: false }), TPL_POLL_MS);
  } else if (!on && tplPollTimer) {
    window.clearInterval(tplPollTimer);
    tplPollTimer = null;
  }
}

/**
 * 起轮询：2.5s 静默对一次表；页面隐藏时暂停、回到前台先立即对一次不等下一个周期。
 *
 * 用 `visibilitychange` 而非无条件空转 —— 用户切走时本页既没人看，也没必要持续发请求。
 */
function startTemplatePolling() {
  setTemplatePolling(true);
  document.addEventListener('visibilitychange', () => {
    const hidden = document.visibilityState === 'hidden';
    setTemplatePolling(!hidden);
    if (!hidden) loadTemplateList({ force: false });
  });
}

/** 重命名模板（V0.0.20）：改文件名 + 文件内 name，服务端拒绝重名。 */
async function renameTemplateItem(item) {
  const input = window.prompt(t('template.renamePrompt', { name: item.name }), item.name);
  if (input === null) return;
  const next = input.trim();
  if (!next || next === item.name) return;
  try {
    await api.renameTemplate(item.file, next);
    toast(t('template.renamed', { name: next }), 'ok');
    await loadTemplateList();
  } catch (err) {
    toast(localizeError(err) || t('template.opFailed'), 'warn', 6000);
  }
}

/** 删除模板（V0.0.20）：二次确认 → 服务端软删除入 templates/.trash/。 */
async function deleteTemplateItem(item) {
  if (!window.confirm(t('template.deleteConfirm', { name: item.name }))) return;
  try {
    await api.deleteTemplate(item.file);
    toast(t('template.deleted', { name: item.name }), 'ok');
    await loadTemplateList();
  } catch (err) {
    toast(localizeError(err) || t('template.opFailed'), 'warn', 6000);
  }
}

async function applyTemplate(item) {
  if (!window.confirm(t('template.loadConfirm', { name: item.name }))) return;
  try {
    const res = await api.loadTemplate(item.file);
    pushHistory();                       // 载入可撤销：与新建/重命名/删除同一套历史栈
    // 模板是「嵌套字典」格式（目录=对象、文件=内容），与编辑态文档不同 —— 走 fromNestedTree 转换，
    // id 由前端按既有规则补发。根节点名取模板的 name。
    const root = fromNestedTree(res.tree, res.name || item.name);
    // 模板说明提炼（V0.0.17）：根 note 为空时取「说明文档.md」（兜底首个 *.md）填入 ——
    // 独立副本：原 .md 文件保留不动，编辑 note 不回写
    const noteFrom = adoptTemplateNote(root);
    store.set({ root, selectedId: root.id, selectedIds: [] });
    setStatus(t('template.loaded', { name: res.name || item.name })
      + (noteFrom ? t('template.noteAdopted', { file: noteFrom }) : ''));
    markDirty();
  } catch (err) {
    toast(t('template.loadFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

/**
 * 另存为模板（V0.0.13；覆盖分支 V0.0.21）：把正在编辑的树写进 templates/<name>.json。
 *
 * 服务端**默认拒绝覆盖同名模板**（templateExists）—— 改名留给用户在提示里重试。
 * 若用户愿意覆盖，第二次请求带 `overwrite: true`，**旧模板由后端移入回收站**
 * （`templates/.trash/`，可人工找回）而非静默丢弃：工具不替用户决定「旧的那套可以丢」，
 * 但把「丢」的决定权明确交回用户（二次确认）。
 */
async function saveAsTemplate() {
  const { root } = store.get();
  const name = window.prompt(t('template.savePrompt'), root.name || '');
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    toast(t('template.nameEmpty'), 'warn');
    return;
  }
  try {
    let res;
    try {
      res = await api.saveTemplate({ name: trimmed, tree: treePayload(root) });
    } catch (err) {
      // 同名：默认拒写。用户显式确认「覆盖」后重发（旧模板入回收站，可找回）。
      if (!err || err.code !== 'templateExists') throw err;
      if (!window.confirm(t('template.overwriteConfirm', { name: trimmed }))) return;
      res = await api.saveTemplate({ name: trimmed, tree: treePayload(root), overwrite: true });
    }
    const saved = res.name || trimmed;
    const key = res.overwritten ? 'template.overwritten' : 'template.saved';
    setStatus(t(key, { name: saved }));
    toast(t(key, { name: saved }), 'info');
    await loadTemplateList();   // 新模板要立刻出现在列表里，否则用户以为没生效
  } catch (err) {
    toast(t('template.saveFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

/**
 * 新建模板（V0.0.41 · 手册 9.2 节 #7 / 10.2 节 #4）：**从零**创建一套模板写进模板库。
 *
 * 与「另存为」的分工：另存为把**正在编辑的树**存成模板；本入口不依赖编辑态，
 * 只取「名称 + 说明 + 起点」，起点即骨架（空白 / 库中任一模板）。
 *
 * 起点选项**取当前模板库**而非写死内置文件名：模板库可被绑定到外部目录
 * （`PUT /api/templates-dir`），写死名字在换库后必然失效。
 *
 * **落盘后不自动载入编辑器** —— 载入会丢掉内存里那棵尚未落盘的树（《项目约定》§P0-3）。
 * 要编辑新模板，在列表里点它即可；那条路径本就有未保存确认。
 */
async function newTemplateFlow() {
  if (!getLayers()) return;
  el('newTplName').value = '';
  el('newTplDesc').value = '';
  await fillTemplateBaseOptions();
  // 焦点由 #newTplName 的 data-autofocus 交给 layer.js 处理 —— 不要在这里手动 focus，
  // layer.open() 会在 30ms 后按 [data-autofocus] 定焦，手动那次会被覆盖（白写）。
  getLayers().open(el('dlgNewTemplate'), el('btnNewTemplate'));
}

/**
 * 填「起点」下拉：空白恒为首项，其后是当前模板库中的每一套。
 * 列表拉取失败**不阻塞**新建 —— 仍可用空白起点（否则列表一挂就建不了模板）。
 */
async function fillTemplateBaseOptions() {
  const sel = el('newTplBase');
  const keep = sel.value;
  sel.textContent = '';
  const blank = document.createElement('option');
  blank.value = '';
  blank.textContent = t('template.newBaseBlank');
  sel.appendChild(blank);
  try {
    const res = await api.listTemplates();
    for (const item of (res && res.items) || []) {
      const opt = document.createElement('option');
      opt.value = item.file;
      opt.textContent = item.name;
      sel.appendChild(opt);
    }
  } catch (_) { /* 起点可退化为「空白」 */ }
  // 语言切换会重建选项，尽量保住用户已选的那一项
  sel.value = keep && Array.prototype.some.call(sel.options, (o) => o.value === keep) ? keep : '';
}

/** 提交「新建模板」：按起点取骨架 → 落盘；同名默认拒写，用户确认后方可覆盖。 */
async function submitNewTemplate() {
  const nameEl = el('newTplName');
  const trimmed = nameEl.value.trim();
  if (!trimmed) {
    toast(t('template.nameEmpty'), 'warn');
    nameEl.focus();
    return;
  }
  const base = el('newTplBase').value;
  const description = el('newTplDesc').value.trim();
  try {
    let tree = {};
    if (base) {
      const src = await api.loadTemplate(base);   // 起点＝既有模板：取其 tree 当骨架
      tree = (src && src.tree) || {};
    }
    let res;
    try {
      res = await api.saveTemplate({ name: trimmed, description, tree });
    } catch (err) {
      // 与「另存为」同一套同名取舍：默认拒写，显式确认后才覆盖（旧模板入回收站）
      if (!err || err.code !== 'templateExists') throw err;
      if (!window.confirm(t('template.overwriteConfirm', { name: trimmed }))) return;
      res = await api.saveTemplate({ name: trimmed, description, tree, overwrite: true });
    }
    const saved = res.name || trimmed;
    const key = res.overwritten ? 'template.overwritten' : 'template.saved';
    setStatus(t(key, { name: saved }));
    toast(t(key, { name: saved }), 'info');
    const lv = getLayers();
    if (lv) lv.closeAll();
    await loadTemplateList();   // 新模板要立刻出现在列表里，否则用户以为没生效
  } catch (err) {
    toast(t('template.saveFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

  /* 按钮接线（原在 main.js 末尾；处理函数只在点击时执行，故绑定时机等价） */
  el('btnNewTemplate').addEventListener('click', newTemplateFlow);
  el('newTplConfirm').addEventListener('click', submitNewTemplate);
  el('btnSaveTemplate').addEventListener('click', saveAsTemplate);
  el('btnImportTemplate').addEventListener('click', importTemplateFlow);
  el('btnPickDir').addEventListener('click', chooseTemplatesDir);
  el('btnRefreshTpl').addEventListener('click', () => { loadTemplatesDir(); loadTemplateList(); });

  /* 语言切换后刷新本模块的动态文案（静态文案由 applyStatic 在 setLocale 内处理） */
  document.addEventListener('qmlocalechange', () => {
    renderTemplatesDir(lastDirRes);  // 绑定行提示是动态文案，须随语言重渲染
    // 起点下拉的「空白」项是取词键须重填；判**具体**那个层用 isOpenNode（isOpen 只答「有没有」）。
    const lv = getLayers();
    if (lv && lv.isOpenNode(el('dlgNewTemplate'))) fillTemplateBaseOptions();
  });

  return { loadTemplatesDir, loadTemplateList, startTemplatePolling };
}
