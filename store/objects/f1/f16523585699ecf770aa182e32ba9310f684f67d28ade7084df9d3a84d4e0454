/**
 * 青蔓 QingMan · 应用入口
 * 负责装配：偏好 → 取词填充 → 状态仓库 → 视图 → 交互绑定 → 编辑态持久化 → 后端连通性自检。
 *
 * 本文件不直写任何用户可见文案 —— 一律经 `t(key)` 取自 i18n 取词表（§P0-3 L1）。
 */

import { createStore } from './core/store.js';
import { api } from './core/api.js';
import { t, applyStatic, initPrefs, getGenBarState, setGenBarState } from './i18n/index.js';
import {
  createDir, createFile, findNode, findParent, addChild,
  renameNode, removeNode, countTree, treePayload,
  hasSiblingName, reserveIds, assertUniqueIds,
  toDocumentNode, fromDocumentNode, resetIdRegistry,
} from './modules/tree-model.js';
import { createTreeView } from './ui/tree-view.js';
import { createInspector } from './ui/inspector.js';
import { toast } from './ui/toast.js';

const el = (id) => document.getElementById(id);

/** 自动保存的防抖窗口（毫秒）：停手这么久之后才写盘，避免连击时反复落盘 */
const AUTOSAVE_DELAY = 800;

/** 编辑态文档结构版本，与 src/shared/schema.json 的 editorDocument.schemaVersion 一致 */
const DOC_SCHEMA_VERSION = 1;

/* ---------- 生成参数区：折叠 ---------- */

/** 折叠标记，与目录树的展开/折叠符同款（见 ui/tree-view.js） */
const CARET_OPEN = '\u25BC';
const CARET_CLOSED = '\u25B6';

/**
 * 启动时定一次折叠态。无记录则默认展开 —— 目标位置目前不跨会话保存，
 * 故首次启动总是展开，与帮助页的引导顺序（先填目标位置）一致。
 */
function initGenBar() {
  if (!getGenBarState()) setGenBarState('open');
  renderGenBar();
}

/** 摘要行文案：目标位置（未填时明说）· 根名（有才显示）· 演练或写盘 */
function genSummaryText() {
  const target = el('inTarget').value.trim();
  const rootName = el('inRoot').value.trim();
  const parts = [target ? t('gen.summaryTarget', { target }) : t('gen.summaryEmpty')];
  if (rootName) parts.push(t('gen.summaryRoot', { root: rootName }));
  parts.push(t(el('inDryRun').checked ? 'gen.summaryDryRun' : 'gen.summaryWrite'));
  return parts.join(t('gen.summarySep'));
}

function renderGenBar() {
  const collapsed = getGenBarState() === 'closed';
  const head = el('btnGenToggle');
  el('genBar').classList.toggle('is-collapsed', collapsed);
  head.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  head.setAttribute('title', t(collapsed ? 'gen.toggleExpand' : 'gen.toggleCollapse'));
  el('genCaret').textContent = collapsed ? CARET_CLOSED : CARET_OPEN;
  el('genSummary').textContent = genSummaryText();
}

function setGenBarCollapsed(next) {
  setGenBarState(next ? 'closed' : 'open');
  renderGenBar();
}

/* ---------- 初值：尚无持久化文档时使用的默认示例 ---------- */

function defaultRoot() {
  resetIdRegistry();
  const root = createDir(t('sample.root'));
  addChild(root, createDir(t('sample.materials')));
  addChild(root, createDir(t('sample.output')));
  addChild(root, createFile(t('sample.readme'), t('sample.readmeContent')));
  const sample = findNode(root, root.children[0].id);
  addChild(sample, createDir(t('sample.raw')));
  addChild(sample, createDir(t('sample.tidied')));
  return root;
}

const rootNode = defaultRoot();

const store = createStore({
  root: rootNode,
  selectedId: rootNode.id,
  version: '—',
  connected: false,
  saveState: 'idle',   // idle | pending | saving | saved | error
  savedAt: '',
});

/* ---------- 视图 ---------- */

const treeView = createTreeView(el('treeCanvas'), {
  onSelect(id) {
    store.set({ selectedId: id });
  },
});

const inspector = createInspector({
  name: el('propName'),
  type: el('propType'),
  path: el('propPath'),
  dirs: el('propDirs'),
  files: el('propFiles'),
  depth: el('propDepth'),
  result: el('genResult'),
});

function render() {
  const { root, selectedId } = store.get();
  treeView.render(root, selectedId);
  inspector.render(root, selectedId);
  const stats = countTree(root);
  el('statusCount').textContent = t('status.count', { dirs: stats.dirs, files: stats.files });
  renderSaveChip();
}

store.subscribe(render);

/* ---------- 保存状态指示（复用现有 chip 变体，不新造视觉语言） ---------- */

const SAVE_CHIP_CLASS = {
  idle: 'chip-ghost',
  pending: 'chip-ghost',
  saving: '',
  saved: 'chip-ok',
  error: 'chip-bad',
};

const SAVE_CHIP_KEY = {
  idle: 'topbar.save.idle',
  pending: 'topbar.save.pending',
  saving: 'topbar.save.saving',
  error: 'topbar.save.error',
};

function renderSaveChip() {
  const { saveState, savedAt } = store.get();
  const chip = el('chipSave');
  if (!chip) return;
  chip.className = `chip ${SAVE_CHIP_CLASS[saveState] || ''}`.trim();
  const key = SAVE_CHIP_KEY[saveState];
  chip.textContent = saveState === 'saved'
    ? (savedAt ? t('topbar.save.savedAt', { at: savedAt }) : t('topbar.save.saved'))
    : (key ? t(key) : '');
}

/* ---------- 编辑态持久化（见 docs/项目约定.md §P0-7） ---------- */

let saveTimer = null;

/** 重复 id 列表 → 便于阅读的短串（分隔符同样走取词，避免直写全角标点）。 */
function idList(ids) {
  return ids.slice(0, 3).join(t('list.separator'));
}

function currentDocument() {
  return {
    schemaVersion: DOC_SCHEMA_VERSION,
    root: toDocumentNode(store.get().root),
  };
}

/** 标脏：重启防抖计时器，编辑安静下来后自动写盘。 */
function markDirty() {
  if (saveTimer) clearTimeout(saveTimer);
  store.set({ saveState: 'pending' });
  saveTimer = setTimeout(() => {
    saveTimer = null;
    saveNow();
  }, AUTOSAVE_DELAY);
}

/** 立即写盘。防抖到点与 Ctrl+S 都走这里。 */
async function saveNow() {
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }

  // 落盘前自检：重复 id 属内部缺陷，宁可拒存也不写坏文档（服务端另有一道校验）
  const duplicated = assertUniqueIds(store.get().root);
  if (duplicated.length) {
    store.set({ saveState: 'error' });
    toast(t('toast.dupIdBlocked', { ids: idList(duplicated) }), 'error', 8000);
    return;
  }

  store.set({ saveState: 'saving' });
  try {
    const res = await api.saveDoc(currentDocument());
    const at = String(res.savedAt || '').slice(11, 16);
    store.set({ saveState: 'saved', savedAt: at });
  } catch (err) {
    store.set({ saveState: 'error' });
    toast(t('toast.saveFailed', { message: err.message }), 'error', 6000);
  }
}

/** 从后端恢复文档；尚无文档时把默认示例落盘一次，使持久化状态从一开始就一致。 */
async function restoreDocument() {
  try {
    const res = await api.loadDoc();
    if (res.doc && res.doc.root) {
      // 顺序不可颠倒：先登记文档里的既有 id，再转换 —— 否则补发的新 id 可能撞上它们
      reserveIds(res.doc.root);
      const root = fromDocumentNode(res.doc.root);
      const duplicated = assertUniqueIds(root);
      if (duplicated.length) {
        toast(t('toast.docDupId', { ids: idList(duplicated) }), 'warn', 8000);
      }
      const at = String(res.doc.savedAt || '').slice(11, 16);
      store.set({ root, selectedId: root.id, saveState: 'saved', savedAt: at });
      setStatus(at ? t('status.restoredAt', { at }) : t('status.restored'));
      return;
    }
    saveNow();
  } catch (err) {
    toast(t('toast.restoreFailed', { message: err.message }), 'warn', 6000);
  }
}

/* ---------- 交互 ---------- */

function selectedId() {
  return store.get().selectedId;
}

el('btnAddChild').addEventListener('click', () => {
  const root = store.get().root;
  const node = findNode(root, selectedId());
  if (!node || node.type !== 'dir') {
    toast(t('toast.selectDirFirst'), 'warn');
    return;
  }
  const name = window.prompt(t('tree.newDirPrompt'), t('tree.newDirDefault'));
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    toast(t('toast.nameEmpty'), 'warn');
    return;
  }
  if (hasSiblingName(node, trimmed)) {
    toast(t('toast.siblingExists', { name: trimmed }), 'warn');
    return;
  }
  const child = createDir(trimmed);
  addChild(node, child);
  store.set({ selectedId: child.id });
  setStatus(t('status.addedDir', { name: trimmed }));
  markDirty();
});

el('btnRename').addEventListener('click', () => {
  const root = store.get().root;
  const id = selectedId();
  if (id === root.id) {
    toast(t('toast.rootRenameBlocked'), 'warn');
    return;
  }
  const node = findNode(root, id);
  if (!node) return;
  const name = window.prompt(t('tree.renamePrompt'), node.name);
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    toast(t('toast.nameEmpty'), 'warn');
    return;
  }
  if (trimmed === node.name) return;
  const parent = findParent(root, id);
  if (hasSiblingName(parent, trimmed, id)) {
    toast(t('toast.siblingExists', { name: trimmed }), 'warn');
    return;
  }
  renameNode(root, id, trimmed);
  store.set({});
  setStatus(t('status.renamed', { name: trimmed }));
  markDirty();
});

el('btnDelete').addEventListener('click', () => {
  const root = store.get().root;
  const id = selectedId();
  if (id === root.id) {
    toast(t('toast.rootDeleteBlocked'), 'warn');
    return;
  }
  const node = findNode(root, id);
  if (!node) return;
  if (!window.confirm(t('tree.deleteConfirm', { name: node.name }))) return;
  const parent = findParent(root, id);
  removeNode(root, id);
  store.set({ selectedId: parent ? parent.id : root.id });
  setStatus(t('status.deleted', { name: node.name }));
  markDirty();
});

el('btnExpandAll').addEventListener('click', () => {
  treeView.expandAll();
  render();
});

el('btnCollapseAll').addEventListener('click', () => {
  treeView.collapseAll(store.get().root);
  render();
});

el('btnGenToggle').addEventListener('click', () => {
  setGenBarCollapsed(getGenBarState() !== 'closed');
});

/* 参数一变就刷新摘要行，使折叠态下也能一眼看清当前设定 */
for (const id of ['inRoot', 'inTarget']) {
  el(id).addEventListener('input', renderGenBar);
}
el('inDryRun').addEventListener('change', renderGenBar);

el('btnGenerate').addEventListener('click', async () => {
  const { root } = store.get();
  const target = el('inTarget').value.trim();
  const rootName = el('inRoot').value.trim();
  const dryRun = el('inDryRun').checked;

  if (!target) {
    setGenBarCollapsed(false);   // 目标位置为空时参数区必须可见，否则用户看不到该填哪里
    toast(t('toast.targetRequired'), 'warn');
    el('inTarget').focus();
    return;
  }

  const btn = el('btnGenerate');
  btn.disabled = true;
  setStatus(t(dryRun ? 'status.dryRunning' : 'status.writing'));

  try {
    const result = await api.generate(treePayload(root), { target, root: rootName, dryRun });
    inspector.showResult(result);
    markCheck('write', !dryRun);
    setStatus(t(dryRun ? 'status.dryDone' : 'status.genDone', {
      dirs: result.createdDirs.length,
      files: result.createdFiles.length,
      existed: result.existed.length,
    }));
    toast(dryRun ? t('toast.dryDone') : t('toast.generatedTo', { root: result.root }), 'info');
  } catch (err) {
    inspector.showError(err);
    setStatus(t('status.genFailed', { message: err.message }));
    toast(err.message, 'error', 5000);
  } finally {
    btn.disabled = false;
  }
});

/* 帮助页在新标签打开：主界面内存里可能正握着一棵尚未落盘的目录树，
   同标签跳转会丢掉编辑态（见 docs/项目约定.md §P0-3）。 */
el('btnHelp').addEventListener('click', () => {
  window.open('./help.html', '_blank', 'noopener');
});

/* Ctrl/Cmd + S：跳过防抖立即写盘 */
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === 's') {
    event.preventDefault();
    saveNow();
  }
});

/* 防抖窗口内关页会丢最后一次改动，提醒一下 */
window.addEventListener('beforeunload', (event) => {
  const state = store.get().saveState;
  if (state === 'pending' || state === 'saving') {
    event.preventDefault();
    event.returnValue = '';
  }
});

function setStatus(text) {
  el('statusText').textContent = text;
}

/* ---------- 自检 ---------- */

function markCheck(key, ok) {
  const item = document.querySelector(`#checklist li[data-check="${key}"]`);
  if (!item) return;
  item.classList.toggle('is-ok', !!ok);
  item.classList.remove('is-bad');
}

function failCheck(key) {
  const item = document.querySelector(`#checklist li[data-check="${key}"]`);
  if (!item) return;
  item.classList.remove('is-ok');
  item.classList.add('is-bad');
}

async function boot() {
  markCheck('modules', true);
  markCheck('model', !!store.get().root);

  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true });
    el('chipBackend').textContent = t('topbar.backendOn');
    el('chipBackend').classList.remove('chip-ghost');
    el('chipBackend').classList.add('chip-ok');
    markCheck('backend', true);
    setStatus(t('status.readyWith', { nameZh: info.nameZh, app: info.app }));
  } catch (err) {
    failCheck('backend');
    failCheck('write');
    el('chipBackend').textContent = t('topbar.backendOff');
    el('chipBackend').classList.add('chip-bad');
    setStatus(t('status.backendOffHint'));
    toast(t('toast.backendOff', { message: err.message }), 'error', 6000);
    return;
  }

  // 后端可用才恢复/初始化文档；后端未连接时保持默认示例，不做任何写盘尝试
  await restoreDocument();
}

/* 启动顺序：先恢复偏好并填静态文案，再渲染动态内容 —— 否则 applyStatic 会覆盖状态栏等动态字段 */
initPrefs();
applyStatic(document);
initGenBar();
render();
markCheck('modules', true);
markCheck('model', true);
boot();
