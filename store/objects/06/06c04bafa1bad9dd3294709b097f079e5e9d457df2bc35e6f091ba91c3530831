/**
 * 青蔓 QingMan · 应用入口
 * 负责装配：偏好 → 取词填充 → 状态仓库 → 视图 → 交互绑定 → 编辑态持久化 → 后端连通性自检。
 *
 * 本文件不直写任何用户可见文案 —— 一律经 `t(key)` 取自 i18n 取词表（§P0-3 L1）。
 */

import { createStore } from './core/store.js';
import { api } from './core/api.js';
import { localizeError, describeError } from './core/errors.js';
import {
  t, applyStatic, initPrefs, watchLocale,
  getGenBarState, setGenBarState,
} from './i18n/index.js';
import {
  createDir, createFile, findNode, findParent, addChild,
  renameNode, removeNode, moveNode, canMove, countTree, treePayload,
  hasSiblingName, reserveIds, assertUniqueIds,
  toDocumentNode, fromDocumentNode, resetIdRegistry, fromNestedTree,
  adoptTemplateNote, normalizeNote, isDir, pathOf,
} from './modules/tree-model.js';
import { createTreeView } from './ui/tree-view.js';
import { createInspector } from './ui/inspector.js';
import { createSkinPicker } from './ui/skin-picker.js';
import { createLangPicker } from './ui/lang-picker.js';
import { createContextMenu } from './ui/ctx-menu.js';
import { toast } from './ui/toast.js';
import { copyText } from './ui/inspector.js';
import { renderLaunchIcon, ensureLaunchIcon } from './ui/launch-icon.js';

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

/* ---------- 顶栏：语言 / 皮肤 / 支持 ---------- */

function initTopbar() {
  createLangPicker(el('langSelect'));

  createSkinPicker(el('skinSelect'));

  el('btnSupport').addEventListener('click', () => {
    // V0.0.18：支持拆为独立页（赞赏码），帮助页只留使用说明
    window.open('./support.html', '_blank', 'noopener');
  });
}

/* ---------- 撤销 / 重做（上限 50 步） ---------- */

const HISTORY_LIMIT = 50;
let undoStack = [];
let redoStack = [];
/** note 编辑会话（V0.0.20）：已为哪个节点入过撤销栈 —— 一次连续编辑只占一格历史，
 *  否则打一段字就会把 50 步上限全部吃掉（V0.0.17 遗留缺陷）。 */
let noteHistoryId = null;
/** 上一次渲染的选中节点：用于在切换选中时结束 note 编辑会话 */
let lastRenderedSelectedId = null;

function snapshotTree() {
  return toDocumentNode(store.get().root);
}

function updateUndoUI() {
  el('btnUndo').disabled = undoStack.length === 0;
  el('btnRedo').disabled = redoStack.length === 0;
}

function pushHistory() {
  undoStack.push(snapshotTree());
  if (undoStack.length > HISTORY_LIMIT) undoStack.shift();
  redoStack = [];
  updateUndoUI();
}

function restoreHistory(doc) {
  resetIdRegistry();
  reserveIds(doc);
  const root = fromDocumentNode(doc);
  let selectedId = store.get().selectedId;
  if (!findNode(root, selectedId)) selectedId = root.id;
  noteHistoryId = null;   // 历史已变，原编辑会话作废（否则撤销后继续打字不入栈）
  // 同步作废属性栏的编辑暂存：否则 note 输入框仍显示回退前的旧文本（V0.0.20）
  if (typeof inspector.resetEditing === 'function') inspector.resetEditing();
  store.set({ root, selectedId });
}

function undo() {
  if (!undoStack.length) {
    toast(t('toast.cannotUndo'), 'warn');
    return;
  }
  redoStack.push(snapshotTree());
  const doc = undoStack.pop();
  restoreHistory(doc);
  setStatus(t('status.undid'));
  markDirty();
}

function redo() {
  if (!redoStack.length) {
    toast(t('toast.cannotRedo'), 'warn');
    return;
  }
  undoStack.push(snapshotTree());
  const doc = redoStack.pop();
  restoreHistory(doc);
  setStatus(t('status.redid'));
  markDirty();
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
  // V0.0.19 拖拽：把 id 节点移到 targetDirId 下（模型层拦截非目录/成环/同名/根）
  onMove(id, targetDirId) {
    const root = store.get().root;
    const check = canMove(root, id, targetDirId);
    if (check !== true) {
      const keys = {
        notDir: 'toast.moveNotDir',
        cycle: 'toast.moveCycle',
        exists: 'toast.siblingExists',
        root: 'toast.moveRoot',
      };
      const node = findNode(root, id);
      toast(t(keys[check] || 'toast.moveNotDir', { name: node ? node.name : '' }), 'warn');
      return;
    }
    const node = findNode(root, id);
    const target = findNode(root, targetDirId);
    const name = node ? node.name : '';
    const to = target ? target.name : '';
    pushHistory();           // 先快照改动前状态，再落改动
    moveNode(root, id, targetDirId);
    treeView.expandAll();    // 目标目录展开，移进去立即可见
    store.set({ selectedId: id });
    setStatus(t('status.moved', { name, to }));
    markDirty();
  },
  // V0.0.19 右键：选中并弹菜单；菜单项与工具栏同一组动作函数
  onContext(id, x, y) {
    store.set({ selectedId: id });
    openTreeContextMenu(id, x, y);
  },
});

/* ---------- 右键菜单（V0.0.19）：动作与工具栏同函数，菜单只管收集与弹出 ---------- */

const ctxMenu = createContextMenu();

function openTreeContextMenu(id, x, y) {
  const root = store.get().root;
  const node = findNode(root, id);
  if (!node) return;
  const isRoot = id === root.id;
  ctxMenu.showAt(x, y, [
    { label: t('tree.addChild'), disabled: !isDir(node), action: () => doAddChild(id) },
    { label: t('tree.rename'), disabled: isRoot, action: () => doRename(id) },
    { label: t('tree.delete'), danger: true, disabled: isRoot, action: () => doDelete(id) },
    {
      label: t('tree.copyPath'),
      action: () => copyWithToast(pathOf(root, id) || node.name, 'toast.copied', 'toast.copyFailed'),
    },
  ]);
}

const inspector = createInspector({
  name: el('propName'),
  type: el('propType'),
  path: el('propPath'),
  dirs: el('propDirs'),
  files: el('propFiles'),
  depth: el('propDepth'),
  note: el('propNote'),
  result: el('genResult'),
  onNoteChange(id, value) {
    // note 编辑：与重命名同路入撤销栈，但**按编辑会话合并**（V0.0.20）——
    // 同一节点连续输入只在第一次入栈，失焦/切换节点/撤销后重新计一次。
    const node = findNode(store.get().root, id);
    if (!node) return;
    if (noteHistoryId !== id) {
      pushHistory();
      noteHistoryId = id;
    }
    node.note = normalizeNote(value);
    setStatus(t('status.noteUpdated', { name: node.name }));
    markDirty();
  },
});

function render() {
  const { root, selectedId } = store.get();
  // 选中节点切换即结束 note 编辑会话（V0.0.20）：换回来重编辑时重新计一格历史
  if (selectedId !== lastRenderedSelectedId) {
    noteHistoryId = null;
    lastRenderedSelectedId = selectedId;
  }
  treeView.render(root, selectedId);
  inspector.render(root, selectedId);
  const stats = countTree(root);
  el('statusCount').textContent = t('status.count', { dirs: stats.dirs, files: stats.files });
  renderSaveChip();
  updateUndoUI();
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
    toast(t('toast.saveFailed', { message: localizeError(err) }), 'error', 6000);
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
    toast(t('toast.restoreFailed', { message: localizeError(err) }), 'warn', 6000);
  }
}

/* ---------- 交互 ---------- */

function selectedId() {
  return store.get().selectedId;
}

/* 三个树操作提取为具名函数：工具栏按钮与右键菜单共用同一实现（V0.0.19）。
   id 缺省用当前选中，右键菜单显式传入被右键节点。 */

function doAddChild(id = selectedId()) {
  const root = store.get().root;
  const node = findNode(root, id);
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
  pushHistory();
  const child = createDir(trimmed);
  addChild(node, child);
  store.set({ selectedId: child.id });
  setStatus(t('status.addedDir', { name: trimmed }));
  markDirty();
}

function doRename(id = selectedId()) {
  const root = store.get().root;
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
  pushHistory();
  renameNode(root, id, trimmed);
  store.set({});
  setStatus(t('status.renamed', { name: trimmed }));
  markDirty();
}

function doDelete(id = selectedId()) {
  const root = store.get().root;
  if (id === root.id) {
    toast(t('toast.rootDeleteBlocked'), 'warn');
    return;
  }
  const node = findNode(root, id);
  if (!node) return;
  if (!window.confirm(t('tree.deleteConfirm', { name: node.name }))) return;
  pushHistory();
  const parent = findParent(root, id);
  removeNode(root, id);
  store.set({ selectedId: parent ? parent.id : root.id });
  setStatus(t('status.deleted', { name: node.name }));
  markDirty();
}

el('btnAddChild').addEventListener('click', () => doAddChild());
el('btnRename').addEventListener('click', () => doRename());
el('btnDelete').addEventListener('click', () => doDelete());

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
    setStatus(t(dryRun ? 'status.dryDone' : 'status.genDone', {
      dirs: result.createdDirs.length,
      files: result.createdFiles.length,
      existed: result.existed.length,
    }));
    toast(dryRun ? t('toast.dryDone') : t('toast.generatedTo', { root: result.root }), 'info');
  } catch (err) {
    inspector.showError(err);
    setStatus(t('status.genFailed', { message: localizeError(err) }));
    toast(describeError(err), 'error', 5000);
  } finally {
    btn.disabled = false;
  }
});

/* 帮助页在新标签打开：主界面内存里可能正握着一棵尚未落盘的目录树，
   同标签跳转会丢掉编辑态（见 docs/项目约定.md §P0-3）。 */
el('btnHelp').addEventListener('click', () => {
  window.open('./help.html', '_blank', 'noopener');
});

async function createShortcut() {
  if (!window.confirm(t('shortcut.confirm'))) return;
  try {
    // 皮肤联动图标（V0.0.15）：生成失败走 null → 后端沿用默认图标，不阻塞快捷方式
    let iconBase64 = null;
    const ico = await renderLaunchIcon();
    if (ico) {
      let binary = '';
      const CHUNK = 0x8000;
      for (let i = 0; i < ico.length; i += CHUNK) {
        binary += String.fromCharCode.apply(null, ico.subarray(i, i + CHUNK));
      }
      iconBase64 = btoa(binary);
    }
    const res = await api.createShortcut(iconBase64);
    if (res.fallback && res.data) {
      const a = document.createElement('a');
      a.href = 'data:application/octet-stream;base64,' + res.data;
      a.download = res.name || t('shortcut.fileName');
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast(t('shortcut.done') + t('shortcut.downloaded'), 'info');
    } else {
      toast(t('shortcut.done'), 'info');
    }
  } catch (err) {
    toast(t('shortcut.failed', { message: localizeError(err) }), 'error');
  }
}

el('btnLogo').addEventListener('click', createShortcut);

/* ---------- 属性栏：三粒度复制（V0.0.17） ---------- */

async function copyWithToast(text, okKey, failKey) {
  const ok = await copyText(text);
  toast(ok ? t(okKey) : t(failKey), ok ? 'info' : 'error');
}

el('btnCopyName').addEventListener('click', () => {
  const node = findNode(store.get().root, selectedId());
  if (node) copyWithToast(node.name, 'toast.copied', 'toast.copyFailed');
});

el('btnCopyPath').addEventListener('click', () => {
  const node = findNode(store.get().root, selectedId());
  if (node) copyWithToast(el('propPath').textContent, 'toast.copied', 'toast.copyFailed');
});

el('btnCopyNote').addEventListener('click', () => {
  const node = findNode(store.get().root, selectedId());
  if (!node) return;
  copyWithToast(normalizeNote(node.note), 'toast.copied', 'toast.copyFailed');
});

el('btnUndo').addEventListener('click', undo);
el('btnRedo').addEventListener('click', redo);

// note 说明框失焦 = 编辑会话结束（V0.0.20）：下次聚焦重新计一格历史
el('propNote').addEventListener('blur', () => {
  noteHistoryId = null;
});

/* Ctrl/Cmd + S 立即保存；Ctrl/Cmd + Z 撤销；Ctrl/Cmd + Y / Ctrl/Cmd + Shift + Z 重做；
   Delete 删除选中节点；F2 重命名选中节点。
   在输入框内时保留原生行为，不拦截（typing 守卫）。 */
document.addEventListener('keydown', (event) => {
  const tag = (event.target.tagName || '').toLowerCase();
  const typing = tag === 'input' || tag === 'textarea' || event.target.isContentEditable;

  if (event.key === 'Delete') {
    if (typing) return;
    event.preventDefault();
    doDelete();
    return;
  }
  if (event.key === 'F2') {
    if (typing) return;
    event.preventDefault();
    doRename();
    return;
  }

  const mod = event.ctrlKey || event.metaKey;
  if (!mod || event.altKey) return;
  const key = String(event.key).toLowerCase();

  if (key === 's') {
    event.preventDefault();
    saveNow();
    return;
  }
  if (typing) return;
  if (key === 'z') {
    event.preventDefault();
    event.shiftKey ? redo() : undo();
    return;
  }
  if (key === 'y') {
    event.preventDefault();
    redo();
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

/* ---------- 服务状态（V0.0.16：左栏自检收敛为顶栏服务状态三态） ---------- */

const SERVICE_CHIP_CLASS = {
  connecting: 'chip-ghost',
  ready: 'chip-ok',
  offline: 'chip-bad',
};

let serviceState = 'connecting';

/** 设置顶栏「服务状态」chip 的三态：connecting / ready / offline。 */
function setServiceState(state) {
  serviceState = state;
  const chip = el('chipBackend');
  if (!chip) return;
  chip.className = 'chip ' + (SERVICE_CHIP_CLASS[state] || '');
  chip.textContent = t('topbar.backend.' + state);
}

async function boot() {
  setServiceState('connecting');

  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true });
    setServiceState('ready');
    setStatus(t('status.readyWith', { nameZh: info.nameZh, app: info.app }));
  } catch (err) {
    setServiceState('offline');
    setStatus(t('status.backendOffHint'));
    toast(t('toast.backendOff', { message: localizeError(err) }), 'error', 6000);
    return;
  }

  // 后端可用才恢复/初始化文档；后端未连接时保持默认示例，不做任何写盘尝试
  await restoreDocument();

  // 模板库是只读素材，与文档恢复无依赖，放在最后且失败不影响主流程
  await loadTemplateList();
}

/* ---------- 模板库（V0.0.11） ---------- */

/* 错误本地化已迁至 ./core/errors.js（V0.0.12）：主界面与帮助页共用同一套 `err.<code>` 取词。 */

function renderTemplateState(text, kind) {
  const host = el('templateList');
  host.textContent = '';
  const li = document.createElement('li');
  li.className = 'tpl-empty' + (kind ? ' tpl-' + kind : '');
  li.textContent = text;
  host.appendChild(li);
}

async function loadTemplateList() {
  renderTemplateState(t('template.loading'));
  let res;
  try {
    res = await api.listTemplates();
  } catch (err) {
    renderTemplateState(localizeError(err) || t('template.unavailable'), 'warn');
    return;
  }
  const items = (res && res.items) || [];
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
    const stats = document.createElement('span');
    stats.className = 'tpl-stats';
    stats.textContent = t('template.stats', { dirs: item.dirs, files: item.files });
    btn.append(name, stats);
    btn.addEventListener('click', () => applyTemplate(item));

    // V0.0.20：模板 CRUD 补 U/D —— 重命名 / 删除（删除走服务端软删除入 .trash）
    const ops = document.createElement('span');
    ops.className = 'tpl-ops';
    const renameBtn = document.createElement('button');
    renameBtn.type = 'button';
    renameBtn.className = 'tpl-op';
    renameBtn.textContent = t('template.rename');
    renameBtn.title = t('template.renameTip');
    renameBtn.addEventListener('click', () => renameTemplateItem(item));
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'tpl-op is-danger';
    delBtn.textContent = t('template.delete');
    delBtn.title = t('template.deleteTip');
    delBtn.addEventListener('click', () => deleteTemplateItem(item));
    ops.append(renameBtn, delBtn);

    li.append(btn, ops);
    host.appendChild(li);
  }
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
    store.set({ root, selectedId: root.id });
    setStatus(t('template.loaded', { name: res.name || item.name })
      + (noteFrom ? t('template.noteAdopted', { file: noteFrom }) : ''));
    markDirty();
  } catch (err) {
    toast(t('template.loadFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

/**
 * 另存为模板（V0.0.13）：把正在编辑的树写进 templates/<name>.json。
 *
 * 服务端**拒绝覆盖同名模板**（templateExists）—— 改名留给用户在提示里重试，
 * 工具绝不替用户决定「旧的那套可以丢」。
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
    const res = await api.saveTemplate({ name: trimmed, tree: treePayload(root) });
    const saved = res.name || trimmed;
    setStatus(t('template.saved', { name: saved }));
    toast(t('template.saved', { name: saved }), 'info');
    await loadTemplateList();   // 新模板要立刻出现在列表里，否则用户以为没生效
  } catch (err) {
    toast(t('template.saveFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

el('btnSaveTemplate').addEventListener('click', saveAsTemplate);

/* 语言切换后刷新动态文案（静态文案由 applyStatic 在 setLocale 内处理） */
document.addEventListener('qmlocalechange', () => {
  renderSaveChip();
  renderGenBar();
  render();
  setServiceState(serviceState);   // 服务状态 chip 文案随语言刷新
});

/* 换肤后重传启动图标（V0.0.15）：事件由 applySkin 在样式表 onload 后派发，
   此时 getComputedStyle 读到的已是新皮肤配色。失败静默（launch-icon 内部处理）。 */
document.addEventListener('qmskinchange', () => {
  ensureLaunchIcon();
});

/* 启动顺序：先恢复偏好并填静态文案，再渲染动态内容 —— 否则 applyStatic 会覆盖状态栏等动态字段 */
initPrefs();
watchLocale();          // 另一页面（帮助页）改语言时，本页随之切换
applyStatic(document);
initTopbar();
initGenBar();
render();
boot();
