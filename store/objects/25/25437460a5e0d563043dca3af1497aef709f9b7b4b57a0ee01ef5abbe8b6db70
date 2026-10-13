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
  hasSiblingName, reserveIds, assertUniqueIds, validateSegment,
  toDocumentNode, fromDocumentNode, resetIdRegistry, fromNestedTree,
  adoptTemplateNote, normalizeNote, isDir, pathOf,
} from './modules/tree-model.js';
import { createTreeView } from './ui/tree-view.js';
import { createInspector, copyText } from './ui/inspector.js';
import { createSkinPicker } from './ui/skin-picker.js';
import { createLangMenu } from './ui/lang-picker.js';
import { createContextMenu } from './ui/ctx-menu.js';
import { createLayerManager, placeUnder } from './ui/layer.js';
import { createHelpDoc } from './ui/help-doc.js';
import { toast } from './ui/toast.js';
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

/* ---------- 顶栏：语言 / 皮肤 / 支持 / 帮助 / 服务（V0.0.40 · 手册 10.2 节 #6 / #7 / #9） ----------
   四项入口由「`<select>` + 新标签开页」改为「图标按钮 + 应用内弹层」：
   - 语言 / 皮肤 / 更多 → popover（贴按钮下沿，点外部自动收起）
   - 支持 / 帮助 / 服务 → modal（居中 + 遮罩 + 焦点陷阱）
   三条关闭路径（右上角 × / Esc / 点遮罩）统一由 ui/layer.js 接线，避免各写各的。 */

/** 弹层管理器：全应用共用一个 —— 弹层之间互斥打开，关闭时焦点归还各自的触发器。 */
let layers = null;
/** 帮助弹窗正文渲染器；服务状态变化时用它覆盖版本号 / 连接状态（见 setServiceState）。 */
let helpDoc = null;

/** 图标按钮 → 浮层：已开则关（点同一颗按钮收回），否则锚到按钮下沿再开。 */
function togglePopover(trigger, node, width) {
  if (layers.isOpenNode(node)) {
    layers.closeAll();
    return;
  }
  placeUnder(trigger, node, width);
  layers.open(node, trigger);
}

/**
 * 服务弹窗的「测试连接」：复用 boot() 同一支健康检查，结果**就地**显示。
 * 不走 toast —— toast 悬浮在遮罩之上，会盖住正要看的弹窗内容。
 */
async function testService() {
  const btn = el('btnSvcTest');
  const out = el('svcResult');
  if (!btn || !out) return;
  btn.disabled = true;
  out.textContent = t('svc.testing');
  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true });
    setServiceState('ready');
    out.textContent = t('svc.testOk', { version: info.version });
  } catch (err) {
    setServiceState('offline');
    out.textContent = t('svc.testFail', { message: localizeError(err) });
  } finally {
    btn.disabled = false;
  }
}

function initTopbar() {
  layers = createLayerManager();

  createLangMenu(el('popLang'));
  createSkinPicker(el('skinGrid'), {
    // 选定后收起浮层；焦点由 layer 的关闭逻辑归还给触发器（#btnSkin）。
    onPick: () => layers.closeAll(),
  });
  helpDoc = createHelpDoc(el('dlgHelpToc'), el('dlgHelpDoc'), {
    // 弹窗里的「支持」一行是按钮：切到支持弹窗，不再新标签开页（手册 10.2 节 #9）。
    onSupport: () => layers.open(el('dlgSupport'), el('btnSupport')),
  });

  // 浮层：语言 / 皮肤 / 更多。stopPropagation 防止本次点击立刻被「点外部关闭」逻辑收回。
  el('btnLang').addEventListener('click', (event) => {
    event.stopPropagation();
    togglePopover(el('btnLang'), el('popLang'), 148);
  });
  el('btnSkin').addEventListener('click', (event) => {
    event.stopPropagation();
    togglePopover(el('btnSkin'), el('popSkin'), 344);
  });
  el('btnMore').addEventListener('click', (event) => {
    event.stopPropagation();
    togglePopover(el('btnMore'), el('popMore'), 200);
  });

  // 模态：支持 / 帮助 / 服务。支持与帮助在「新标签开页」与「应用内弹窗」之间统一切到
  // **弹窗** —— 同标签跳转会丢掉内存里尚未落盘的目录树（见 docs/项目约定.md §P0-3）。
  el('btnSupport').addEventListener('click', () => layers.open(el('dlgSupport'), el('btnSupport')));
  el('btnHelp').addEventListener('click', () => layers.open(el('dlgHelp'), el('btnHelp')));
  el('chipBackend').addEventListener('click', () => layers.open(el('dlgService'), el('chipBackend')));

  // 「更多」浮层里的三个低频入口：窄窗折入后复用同一批弹窗。
  // 触发器一律回指 #btnMore —— 窄窗下 #btnSupport / #btnHelp 已 display:none，
  // 焦点若归还给隐藏元素会丢失，须有可见落点。
  el('moreService').addEventListener('click', () => layers.open(el('dlgService'), el('btnMore')));
  el('moreSupport').addEventListener('click', () => layers.open(el('dlgSupport'), el('btnMore')));
  el('moreHelp').addEventListener('click', () => layers.open(el('dlgHelp'), el('btnMore')));

  // 服务弹窗：地址取自 api.js 的同一基址（window.location.origin），测试按钮走后端健康检查。
  el('svcAddr').textContent = window.location.origin;
  el('btnSvcTest').addEventListener('click', testService);
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

// 偏好必须在默认示例**取词之前**恢复（V0.0.22）：defaultRoot() 用 t('sample.*') 取名，
// 若此时仍是出厂 zh-CN，英文环境的首屏示例会是中文名，且随后被 restoreDocument()
// 的 saveNow() 永久落盘 —— 语言探测结果形同虚设。initPrefs 只碰 localStorage 与
// document.head，module 脚本在文档解析后执行，此处调用安全。
initPrefs();
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
        missing: 'toast.moveMissing',
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
/** 是否已有一次保存在途（B-P3-2）。防抖到点与 Ctrl+S 可能同时触发 → 并发 PUT。 */
let saveInFlight = false;
/** 在途期间又发生了改动：等本次完成后合并再存一次。 */
let saveQueued = false;

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
  // B-P3-2：在途保护 —— 并发 PUT 会让两次保存的响应乱序（后到的旧结果覆盖新状态）。
  // 合并为「一次在途 + 一次排队」，排队在收尾时重新触发。
  if (saveInFlight) {
    saveQueued = true;
    return;
  }
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

  saveInFlight = true;
  store.set({ saveState: 'saving' });
  try {
    const res = await api.saveDoc(currentDocument());
    const at = String(res.savedAt || '').slice(11, 16);
    store.set({ saveState: 'saved', savedAt: at });
  } catch (err) {
    store.set({ saveState: 'error' });
    toast(t('toast.saveFailed', { message: localizeError(err) }), 'error', 6000);
  } finally {
    saveInFlight = false;
    // 在途期间的改动：此刻已无并发，安全地再存一次（markDirty 会重新起防抖）
    if (saveQueued) {
      saveQueued = false;
      markDirty();
    }
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
  const vseg = validateSegment(trimmed);
  if (!vseg.ok) {
    toast(t('err.' + vseg.code, { name: trimmed }), 'warn');
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
  const vseg = validateSegment(trimmed);
  if (!vseg.ok) {
    toast(t('err.' + vseg.code, { name: trimmed }), 'warn');
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

/* 帮助入口改为应用内弹窗（V0.0.40）：接线集中在 initTopbar()，
   理由同 §P0-3 —— 同标签跳转会丢掉内存里尚未落盘的目录树。 */

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

/* ---------- 服务状态（V0.0.16 起收敛为顶栏三态；V0.0.40 由只读 chip 升级为可点按钮） ---------- */

let serviceState = 'connecting';

/**
 * 同步「服务状态」的三处落点，各取所需：
 *   - 顶栏 #chipBackend：可点按钮（点开服务弹窗），离线加 .is-offline；
 *   - 更多浮层 #popMoreStatus：窄窗下顶栏状态文案被收进这里，须与顶栏一致；
 *   - 帮助弹窗：版本号与「后端」一行的实测值（离线时回落到本机记录值）。
 */
function setServiceState(state) {
  serviceState = state;

  const btn = el('chipBackend');
  if (btn) {
    btn.classList.toggle('is-offline', state === 'offline');
    const txt = btn.querySelector('.btn-txt');
    if (txt) txt.textContent = t('topbar.backend.' + state);
  }

  const moreText = el('popMoreStatus');
  if (moreText) {
    moreText.textContent = t('topbar.backend.' + state);
    const wrap = moreText.closest('.pop-more-status');
    if (wrap) wrap.classList.toggle('is-offline', state === 'offline');
  }

  if (helpDoc) {
    // 只有真连上才把实测版本号写进帮助弹窗；否则传空值，回落 versionFallback（本机记录值）。
    helpDoc.setStatus({
      version: state === 'ready' ? store.get().version : '',
      backendOk: state === 'ready',
    });
  }
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

  // 模板库是只读素材，与文档恢复无依赖，放在最后且失败不影响主流程。
  // 两个请求**并发**：串行会多花一个网络往返，无头冒烟的虚拟时间预算可能在
  // 列表渲染完成前就 dump DOM（`--virtual-time-budget` 不等未决 Promise）。
  await Promise.all([loadTemplatesDir(), loadTemplateList()]);
  startTemplatePolling();   // 仅在后端可用时起轮询：连不上就别空转发请求
}

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

/**
 * 「选择…」（生成栏·目标位置，V0.0.40 · 手册 10.2 节 #13）：**复用**模板目录的原生选择器
 * （`POST /api/templates-dir/pick`，V0.0.38 · 6E 提供），本机用不了则降级为**手动粘贴路径**
 * —— 与上方的「选择模板目录」同一套降级范式。
 *
 * 与「选择模板目录」的差别只在**落点**：选中后写进 `#inTarget` 并刷新摘要行，
 * **不落盘、不绑定** —— `target` 的规范化与安全边界（§P0-1）全在生成时由服务端
 * `check_target` 把关，前端这里只负责「把用户挑的路径填进输入框」。
 *
 * ⚠ 原生框是 `mustexist=True`：只能选**已存在**的目录。想指定一个尚不存在、交由
 * 生成器创建的路径，仍走键盘输入（输入框本就允许）。
 */
async function chooseTargetDir() {
  let res;
  try {
    res = await api.pickTemplatesDir();
  } catch (err) {
    res = { available: false };   // 端点异常按能力缺失处理，走同一降级路径
  }
  if (res.available && !res.cancelled && res.dir) {
    applyTargetDir(res.dir);
    return;
  }
  if (res.available && res.cancelled) return;   // 用户主动取消：静默
  const typed = window.prompt(t('gen.targetPastePrompt'), el('inTarget').value.trim());
  if (typed === null) return;
  const picked = typed.trim();
  if (picked) applyTargetDir(picked);
}

/** 把选中的目录写进「目标位置」输入框，并刷新折叠摘要行（否则收起态下看不到已选值）。 */
function applyTargetDir(dir) {
  el('inTarget').value = dir;
  renderGenBar();
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

    // V0.0.38 · 6E：改名 / 删除等操作**收进右键菜单**（去常驻按钮），与目录树共用 `ctx-menu`
    li.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      openTemplateContextMenu(item, event.clientX, event.clientY);
    });

    li.append(btn);
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
    store.set({ root, selectedId: root.id });
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
  if (!layers) return;
  el('newTplName').value = '';
  el('newTplDesc').value = '';
  await fillTemplateBaseOptions();
  // 焦点由 #newTplName 的 data-autofocus 交给 layer.js 处理 —— 不要在这里手动 focus，
  // layer.open() 会在 30ms 后按 [data-autofocus] 定焦，手动那次会被覆盖（白写）。
  layers.open(el('dlgNewTemplate'), el('btnNewTemplate'));
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
    if (layers) layers.closeAll();
    await loadTemplateList();   // 新模板要立刻出现在列表里，否则用户以为没生效
  } catch (err) {
    toast(t('template.saveFailed', { message: localizeError(err) }), 'error', 6000);
  }
}

el('btnNewTemplate').addEventListener('click', newTemplateFlow);
el('newTplConfirm').addEventListener('click', submitNewTemplate);
el('btnSaveTemplate').addEventListener('click', saveAsTemplate);
el('btnImportTemplate').addEventListener('click', importTemplateFlow);
el('btnPickDir').addEventListener('click', chooseTemplatesDir);
/* 目标位置「选择…」：与模板目录共用同一原生选择器（V0.0.40 · 手册 10.2 节 #13）。
   按钮位于 <label> 内，先阻止 label 把该次点击转发给输入框 —— 否则原生框弹出前
   输入框会被顺手聚焦，收起键盘态时视觉上像「没反应」。 */
el('btnPickTarget').addEventListener('click', (event) => {
  event.preventDefault();
  chooseTargetDir();
});
el('btnRefreshTpl').addEventListener('click', () => { loadTemplatesDir(); loadTemplateList(); });

/* 语言切换后刷新动态文案（静态文案由 applyStatic 在 setLocale 内处理） */
document.addEventListener('qmlocalechange', () => {
  renderSaveChip();
  renderGenBar();
  render();
  setServiceState(serviceState);   // 服务状态 chip 文案随语言刷新
  renderTemplatesDir(lastDirRes);  // 绑定行提示是动态文案，须随语言重渲染
  // 「新建模板」弹窗若开着：起点下拉的「空白」项是取词键，须重填（其余项是模板名，与语言无关）。
  // 用 isOpenNode（判**具体**那个层）而非 isOpen —— 后者只答「有没有层开着」。
  if (layers && layers.isOpenNode(el('dlgNewTemplate'))) fillTemplateBaseOptions();
});

/* 换肤后重传启动图标（V0.0.15）：事件由 applySkin 在样式表 onload 后派发，
   此时 getComputedStyle 读到的已是新皮肤配色。失败静默（launch-icon 内部处理）。 */
document.addEventListener('qmskinchange', () => {
  ensureLaunchIcon();
});

/* 启动顺序：偏好**已在模块顶部**恢复（须早于默认示例取词，见上方 defaultRoot 处注释）；
   此处补齐静态文案与动态内容 —— 否则 applyStatic 会覆盖状态栏等动态字段 */
watchLocale();          // 另一页面（帮助页）改语言时，本页随之切换
applyStatic(document);
initTopbar();
initGenBar();
render();
boot();
