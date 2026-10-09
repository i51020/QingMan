/**
 * 青蔓 QingMan · 应用入口
 * 负责装配：状态仓库 → 视图 → 交互绑定 → 编辑态持久化 → 后端连通性自检。
 */

import { createStore } from './core/store.js';
import { api } from './core/api.js';
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

/* ---------- 初值：尚无持久化文档时使用的默认示例 ---------- */

function defaultRoot() {
  resetIdRegistry();
  const root = createDir('青蔓示例项目');
  addChild(root, createDir('素材'));
  addChild(root, createDir('产出'));
  addChild(root, createFile('说明.md', '# 说明\n\n本目录骨架由青蔓 QingMan 生成。\n'));
  const sample = findNode(root, root.children[0].id);
  addChild(sample, createDir('原始素材'));
  addChild(sample, createDir('已整理'));
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
  el('statusCount').textContent = `目录 ${stats.dirs} · 文件 ${stats.files}`;
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

function renderSaveChip() {
  const { saveState, savedAt } = store.get();
  const chip = el('chipSave');
  if (!chip) return;
  chip.className = `chip ${SAVE_CHIP_CLASS[saveState] || ''}`.trim();
  const labels = {
    idle: '未保存',
    pending: '未保存',
    saving: '保存中…',
    saved: savedAt ? `已保存 ${savedAt}` : '已保存',
    error: '保存失败',
  };
  chip.textContent = labels[saveState] || '';
}

/* ---------- 编辑态持久化（见 docs/项目约定.md §P0-7） ---------- */

let saveTimer = null;

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
    toast(`检测到重复 id（${duplicated.slice(0, 3).join('、')}），已阻止保存`, 'error', 8000);
    return;
  }

  store.set({ saveState: 'saving' });
  try {
    const res = await api.saveDoc(currentDocument());
    const at = String(res.savedAt || '').slice(11, 16);
    store.set({ saveState: 'saved', savedAt: at });
  } catch (err) {
    store.set({ saveState: 'error' });
    toast(`保存失败：${err.message}`, 'error', 6000);
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
        toast(`文档存在重复 id：${duplicated.slice(0, 3).join('、')}`, 'warn', 8000);
      }
      const at = String(res.doc.savedAt || '').slice(11, 16);
      store.set({ root, selectedId: root.id, saveState: 'saved', savedAt: at });
      setStatus(at ? `已恢复上次编辑内容（${at}）` : '已恢复上次编辑内容');
      return;
    }
    saveNow();
  } catch (err) {
    toast(`读取上次编辑内容失败：${err.message}`, 'warn', 6000);
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
    toast('请先选中一个目录节点', 'warn');
    return;
  }
  const name = window.prompt('新目录名称', '新建目录');
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    toast('名称不能为空', 'warn');
    return;
  }
  if (hasSiblingName(node, trimmed)) {
    toast(`「${trimmed}」已存在于该目录下`, 'warn');
    return;
  }
  const child = createDir(trimmed);
  addChild(node, child);
  store.set({ selectedId: child.id });
  setStatus(`已新建目录「${trimmed}」`);
  markDirty();
});

el('btnRename').addEventListener('click', () => {
  const root = store.get().root;
  const id = selectedId();
  if (id === root.id) {
    toast('根节点名称由「根文件夹名」决定，不在此处重命名', 'warn');
    return;
  }
  const node = findNode(root, id);
  if (!node) return;
  const name = window.prompt('重命名', node.name);
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    toast('名称不能为空', 'warn');
    return;
  }
  if (trimmed === node.name) return;
  const parent = findParent(root, id);
  if (hasSiblingName(parent, trimmed, id)) {
    toast(`「${trimmed}」已存在于该目录下`, 'warn');
    return;
  }
  renameNode(root, id, trimmed);
  store.set({});
  setStatus(`已重命名为「${trimmed}」`);
  markDirty();
});

el('btnDelete').addEventListener('click', () => {
  const root = store.get().root;
  const id = selectedId();
  if (id === root.id) {
    toast('根节点不可删除', 'warn');
    return;
  }
  const node = findNode(root, id);
  if (!node) return;
  if (!window.confirm(`确认删除「${node.name}」及其全部子节点？`)) return;
  const parent = findParent(root, id);
  removeNode(root, id);
  store.set({ selectedId: parent ? parent.id : root.id });
  setStatus(`已删除「${node.name}」`);
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

el('btnGenerate').addEventListener('click', async () => {
  const { root } = store.get();
  const target = el('inTarget').value.trim();
  const rootName = el('inRoot').value.trim();
  const dryRun = el('inDryRun').checked;

  if (!target) {
    toast('请先填写目标位置', 'warn');
    el('inTarget').focus();
    return;
  }

  const btn = el('btnGenerate');
  btn.disabled = true;
  setStatus(dryRun ? '演练中…' : '正在写入磁盘…');

  try {
    const result = await api.generate(treePayload(root), { target, root: rootName, dryRun });
    inspector.showResult(result);
    markCheck('write', !dryRun);
    setStatus(
      `${dryRun ? '演练完成' : '生成完成'}：目录 ${result.createdDirs.length} · 文件 ${result.createdFiles.length} · 已存在 ${result.existed.length}`
    );
    toast(dryRun ? '演练完成，未写入磁盘' : `已生成到 ${result.root}`, 'info');
  } catch (err) {
    inspector.showError(err);
    setStatus(`生成失败：${err.message}`);
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
    el('chipBackend').textContent = '后端已连接';
    el('chipBackend').classList.remove('chip-ghost');
    el('chipBackend').classList.add('chip-ok');
    markCheck('backend', true);
    setStatus(`就绪 · ${info.nameZh} ${info.app}`);
  } catch (err) {
    failCheck('backend');
    failCheck('write');
    el('chipBackend').textContent = '后端未连接';
    el('chipBackend').classList.add('chip-bad');
    setStatus('后端未连接，请通过 start.bat 启动');
    toast(`后端未连接：${err.message}`, 'error', 6000);
    return;
  }

  // 后端可用才恢复/初始化文档；后端未连接时保持默认示例，不做任何写盘尝试
  await restoreDocument();
}

render();
markCheck('modules', true);
markCheck('model', true);
boot();
