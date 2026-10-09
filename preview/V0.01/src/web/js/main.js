/**
 * 青蔓 QingMan · 应用入口
 * 负责装配：状态仓库 → 视图 → 交互绑定 → 后端连通性自检。
 */

import { createStore } from './core/store.js';
import { api } from './core/api.js';
import {
  createDir, createFile, findNode, findParent, addChild,
  renameNode, removeNode, countTree, treePayload,
} from './modules/tree-model.js';
import { createTreeView } from './ui/tree-view.js';
import { createInspector } from './ui/inspector.js';
import { toast } from './ui/toast.js';

const el = (id) => document.getElementById(id);

/* ---------- 初始数据 ---------- */

const rootNode = createDir('青蔓示例项目');
addChild(rootNode, createDir('素材'));
addChild(rootNode, createDir('产出'));
addChild(rootNode, createFile('说明.md', '# 说明\n\n本目录骨架由青蔓 QingMan 生成。\n'));

const sample = findNode(rootNode, rootNode.children[0].id);
addChild(sample, createDir('原始素材'));
addChild(sample, createDir('已整理'));

const store = createStore({
  root: rootNode,
  selectedId: rootNode.id,
  version: '—',
  connected: false,
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
}

store.subscribe(render);

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
  const child = createDir(trimmed);
  addChild(node, child);
  store.set({ selectedId: child.id });
  setStatus(`已新建目录「${trimmed}」`);
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
  renameNode(root, id, trimmed);
  store.set({});
  setStatus(`已重命名为「${trimmed}」`);
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
    el('chipVersion').textContent = info.version;
    el('chipBackend').textContent = `后端已连接 ${info.version}`;
    el('chipBackend').classList.remove('chip-ghost');
    el('chipBackend').classList.add('chip-ok');
    markCheck('backend', true);
    setStatus(`就绪 · ${info.nameZh} ${info.app} ${info.version}`);
  } catch (err) {
    failCheck('backend');
    failCheck('write');
    el('chipBackend').textContent = '后端未连接';
    el('chipBackend').classList.add('chip-bad');
    setStatus('后端未连接，请通过 start.bat 启动');
    toast(`后端未连接：${err.message}`, 'error', 6000);
  }
}

render();
markCheck('modules', true);
markCheck('model', true);
boot();
