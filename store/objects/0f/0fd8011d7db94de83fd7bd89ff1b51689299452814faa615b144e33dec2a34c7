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
  getInspMode, setInspMode,
} from './i18n/index.js';
import {
  createDir, createFile, findNode, findParent, addChild,
  renameNode, removeNode, clearNode, moveNode, canMove, countTree, treePayload,
  hasSiblingName, reserveIds, assertUniqueIds, validateSegment,
  toDocumentNode, fromDocumentNode, resetIdRegistry,
  normalizeNote, isDir, pathOf,
} from './modules/tree-model.js';
import { createTreeView } from './ui/tree-view.js';
import { createInspector, copyText } from './ui/inspector.js';
import {
  liveIds, multiSel, allNodeIds, outermostIds, canBatchMove,
} from './modules/selection.js';
import { createSkinPicker } from './ui/skin-picker.js';
import { createLangMenu } from './ui/lang-picker.js';
import { createTemplates } from './modules/templates.js';
import { createContextMenu } from './ui/ctx-menu.js';
import { createLayerManager, placeUnder } from './ui/layer.js';
import { createBackups } from './ui/backups.js';
import { createHelpDoc } from './ui/help-doc.js';
import { toast } from './ui/toast.js';
import { installTooltips } from './ui/tooltip.js';
import { renderLaunchIcon, ensureLaunchIcon } from './ui/launch-icon.js';

const el = (id) => document.getElementById(id);

/** 自动保存的防抖窗口（毫秒）：停手这么久之后才写盘，避免连击时反复落盘 */
const AUTOSAVE_DELAY = 800;

/** 编辑态文档结构版本，与 src/shared/schema.json 的 editorDocument.schemaVersion 一致 */
const DOC_SCHEMA_VERSION = 1;

/* ---------- 生成参数区：常驻状态行（V0.0.51@r9 撤销折叠） ----------

   摘要行原先是「折叠开关」的把手：参数区折叠后只留它，折叠态还写进偏好 `qm.genBar`
   **永久记住**。问题是用户随手一收，此后每次打开「目标位置」整行（含「选择目录」图标
   按钮）都不见了，看上去像功能消失；而参数区只占一行，省下的高度远不值这个风险。
   故折叠整个撤销（偏好键 `qm.genBar` 一并退场，见 i18n/index.js），摘要行只留**核验**
   这一个用途：生成前把「会建到哪 · 建成什么名字 · 演练还是写盘」用一句话说清。 */

/** 摘要行文案：目标位置（未填时明说）· 根名或「不建根」· 演练或写盘 */
function genSummaryText() {
  const target = el('inTarget').value.trim();
  /* V0.0.42：根名真源 = 树编辑区的根节点名（不再有独立输入框） */
  const { root } = store.get();
  const rootName = root && root.name ? root.name.trim() : '';
  const parts = [target ? t('gen.summaryTarget', { target }) : t('gen.summaryEmpty')];
  parts.push(rootName ? t('gen.summaryRoot', { root: rootName }) : t('gen.summaryNoRoot'));
  parts.push(t(el('inDryRun').checked ? 'gen.summaryDryRun' : 'gen.summaryWrite'));
  return parts.join(t('gen.summarySep'));
}

function renderGenBar() {
  el('genSummary').textContent = genSummaryText();
}

/* ---------- 检视器双模式：属性 ⇄ 源码（V0.0.43 · H 组） ----------
   模式存偏好（qm.inspMode），走 i18n/index.js 的带降级读写路径 —— 那里是对外承诺的
   单一偏好访问点，别处不得直访 localStorage。 */

let inspMode = getInspMode();

/** 把模式落到 DOM：换面板 + 分段控件选中态。纯视图动作，不碰 store。 */
function applyInspMode() {
  const src = inspMode === 'src';
  el('inspPropPane').hidden = src;
  el('inspSrcPane').hidden = !src;
  el('btnInspProp').setAttribute('aria-selected', String(!src));
  el('btnInspSrc').setAttribute('aria-selected', String(src));
  el('btnInspProp').classList.toggle('is-on', !src);
  el('btnInspSrc').classList.toggle('is-on', src);
}

function setInspModeUI(mode) {
  inspMode = mode === 'src' ? 'src' : 'prop';
  setInspMode(inspMode);
  applyInspMode();
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
/** 历史版本弹窗（V0.0.51@r9）：列表渲染 + 恢复请求。恢复成功后由 onRestored 装回编辑器。 */
let backups = null;

/** 图标按钮 → 浮层：已开则关（点同一颗按钮收回），否则锚到按钮下沿再开。 */
function togglePopover(trigger, node, width) {
  if (layers.isOpenNode(node)) {
    layers.closeAll();
    return;
  }
  placeUnder(trigger, node, width);
  layers.open(node, trigger);
}

/** 清空「重新检测 / 打开目录」的结果行（弹窗每次打开时调，免得上一次的反馈残留到下回）。 */
function resetSvcResult() {
  const out = el('svcResult');
  if (out) {
    out.hidden = true;
    out.textContent = '';
  }
}

/**
 * 把服务状态与实测信息刷进弹窗的**常驻字段**。
 *
 * 这正是「测完即忘」的修法：状态取自 `serviceState`（`boot()` 时已探测过），版本 /
 * 数据目录取自 `store`（boot 或「重新检测」成功时写入）—— 故**打开弹窗即可见**
 * （V0.0.51@r7 之前是先显示「尚未测试」，非点一下不可）；且与顶栏 chip 同源，
 * 不会一个说就绪、另一个说未测。
 *
 * 刻意**不碰** `#svcResult`：那是「本次操作」的即时反馈，由各操作自行填。
 */
function syncServiceDialog() {
  // 地址取自 api.js 的同一基址（同源 → 就是本服务的 origin）。
  const addr = el('svcAddr');
  if (addr) addr.textContent = window.location.origin;

  const st = el('svcStatus');
  if (st) {
    st.textContent = t('svc.state.' + serviceState);
    // 与顶栏 #chipBackend / 更多浮层同惯例：离线转危险色（JS 加类）。
    st.classList.toggle('is-offline', serviceState === 'offline');
  }

  const ver = el('svcVersion');
  if (ver) ver.textContent = store.get().version || t('svc.unknown');

  const dir = el('svcDataDir');
  if (dir) dir.textContent = store.get().dataDir || t('svc.unknown');
}

/**
 * 服务弹窗的「重新检测」：复用 boot() 同一支健康检查，结果**就地**显示。
 * 不走 toast —— toast 悬浮在遮罩之上，会盖住正要看的弹窗内容。
 */
async function testService() {
  const btn = el('btnSvcTest');
  const out = el('svcResult');
  if (!btn || !out) return;
  btn.disabled = true;
  out.hidden = false;
  out.textContent = t('svc.testing');
  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true, dataDir: info.dataDir || '' });
    setServiceState('ready');       // 内含 syncServiceDialog()，常驻字段随之刷新
    out.textContent = t('svc.testOk');
  } catch (err) {
    setServiceState('offline');
    out.textContent = t('svc.testFail', { message: localizeError(err) });
  } finally {
    btn.disabled = false;
  }
}

/**
 * **服务状态的自动复查**（V0.0.51@r8）：补上「无轮询」留下的缺口 —— 状态不该靠
 * 用户点按钮去问，而应**自己更新**。
 *
 * 触发点两处（都是用户即将看状态的时刻）：① 打开服务弹窗；② 页面重新可见
 * （切回标签页 / 从最小化恢复）。**不做定时轮询** —— 空转发请求没有收益。
 *
 * 与 `testService()`（手动「重新检测」）的分工：本函数**不碰 `#svcResult`**，
 * 那是「本次操作」的就地反馈，只有用户点了按钮才该出现；这里只把**常驻字段**
 * 与顶栏 chip 刷成实测值，用户开窗时看到的就是真值，无需先点一下。
 *
 * `serviceDown` 只在**从「连不上」翻回「连上」**时提示刷新 —— 首次加载成功不该弹。
 * 提示用语是「请刷新页面」而非自动载入：`boot()` 失败时保留的是出厂示例树，
 * 自动恢复文档会**覆盖用户此刻屏幕上的内容**，属越权动作（与手动「重新检测」
 * 保持同一语义：只改状态，不动文档）。
 */
const RECHECK_MIN_MS = 5000;      // 最短复查间隔：连点弹窗 / 快速切窗不连打请求
let recheckAt = 0;
let rechecking = false;
let serviceDown = false;

async function recheckService() {
  if (rechecking) return;                       // 单飞：上一次还没回来就跳过
  const now = Date.now();
  if (now - recheckAt < RECHECK_MIN_MS) return;
  recheckAt = now;
  rechecking = true;
  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true, dataDir: info.dataDir || '' });
    setServiceState('ready');
    if (serviceDown) {
      serviceDown = false;
      toast(t('toast.serviceBack'), 'info', 6000);
    }
  } catch (err) {
    serviceDown = true;
    setServiceState('offline');
  } finally {
    rechecking = false;
  }
}

/**
 * 服务弹窗的「打开目录」：请后端让系统打开青蔓自己的某个目录（V0.0.51@r7）。
 * 就地反馈，且**按 reason 给出可执行的下一步** —— 「目录尚不存在」与「系统打不开」
 * 是两种不同处境（前者等一会儿就有、后者得手动去），笼统一句「失败」帮不上忙。
 */
async function openServiceDir(target) {
  const out = el('svcResult');
  if (!out) return;
  out.hidden = false;
  try {
    const res = await api.openDir(target);
    if (res.available) out.textContent = t('svc.openOk', { dir: res.dir });
    else if (res.reason === 'disabled') out.textContent = t('svc.openDisabled', { dir: res.dir });
    else if (res.reason === 'missing') out.textContent = t('svc.openMissing', { dir: res.dir });
    else out.textContent = t('svc.openUnavailable', { dir: res.dir });
  } catch (err) {
    out.textContent = t('svc.testFail', { message: localizeError(err) });
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
  el('chipBackend').addEventListener('click', () => {
    resetSvcResult();
    recheckService();   // 开窗即探一次：让常驻字段是「刚才的实测值」，而非上次遗留
    layers.open(el('dlgService'), el('chipBackend'));
  });

  // 「更多」浮层里的三个低频入口：窄窗折入后复用同一批弹窗。
  // 触发器一律回指 #btnMore —— 窄窗下 #btnSupport / #btnHelp 已 display:none，
  // 焦点若归还给隐藏元素会丢失，须有可见落点。
  el('moreService').addEventListener('click', () => {
    resetSvcResult();
    recheckService();   // 同上：窄窗下这里才是真正的入口
    layers.open(el('dlgService'), el('btnMore'));
  });
  el('moreSupport').addEventListener('click', () => layers.open(el('dlgSupport'), el('btnMore')));
  el('moreHelp').addEventListener('click', () => layers.open(el('dlgHelp'), el('btnMore')));

  // 服务弹窗（V0.0.51@r7）：常驻字段（状态 / 地址 / 版本 / 数据目录）统一由
  // syncServiceDialog 填；「重新检测」走后端健康检查；两颗「打开目录」请后端调系统打开。
  // V0.0.51@r8：第一颗的靶子由「项目目录」换成**模板库目录** —— 项目根下混着
  // `src/` / `tests/` / `tools/` / `.git` 等用户不该碰的东西，而模板库才是用户
  // 真正会动手放文件的地方（`templates` 本就在后端白名单内，后端零改动）。
  el('btnSvcTest').addEventListener('click', testService);
  el('btnOpenTpl').addEventListener('click', () => openServiceDir('templates'));
  el('btnOpenData').addEventListener('click', () => openServiceDir('data'));

  // 历史版本（V0.0.51@r9）：备份取回的出口。此前 `.bak/` 只进不出 —— 后端每次保存前
  // 都在留档，界面上却没有任何入口能取回。恢复成功后**就地**重载文档（含入撤销栈）。
  // 快照必须先于重载（同 :462 的既有语义：先拍改动前状态，再落改动），否则撤销栈里
  // 存的会是**恢复之后**的状态，Ctrl+Z 就撤不动。
  backups = createBackups({
    onRestored: async () => { pushHistory(); await restoreDocument(); },
  });
  el('btnBackups').addEventListener('click', () => {
    layers.open(el('dlgBackups'), el('btnBackups'));
    backups.open();
  });
  syncServiceDialog();
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

/**
 * 视图组「展开 / 折叠」单按钮的外观同步（V0.0.51@r3 · 第 6 条）。
 *
 * 图标与提示跟随**这一下会做什么**（而不是当前是什么状态）：
 * 树里还有收起的层级 → 显示「全部展开」；已全展开 → 显示「全部折叠」。
 * 这个方向和点击时的实际动作取自**同一个** `foldStats()` 判据 —— 见上方点击处注释。
 *
 * 全树没有「带子节点的目录」时置灰：此时点它不发生任何可见变化，留着可点等于
 * 给用户一个「程序没反应」的假象（与 `btnUndo / btnRedo` 的空栈置灰同一口径）。
 */
function updateToggleAllUI() {
  const { root } = store.get();
  const stats = treeView.foldStats(root);
  const willExpand = stats.collapsed > 0;
  const btn = el('btnToggleAll');
  btn.disabled = stats.expandable === 0;
  const ic = btn.querySelector('.ic');
  if (willExpand) ic.className = 'ic ic-expand-all';
  else ic.className = 'ic ic-collapse-all';
  btn.setAttribute('aria-label', t(willExpand ? 'tree.expandAll' : 'tree.collapseAll'));
  btn.setAttribute('title', t(willExpand ? 'tree.expandAllTip' : 'tree.collapseAllTip'));
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
  // V0.0.43 · F 组：撤销/重做后集合可能指向已不存在的节点 —— 一并清掉，回到单选
  store.set({ root, selectedId, selectedIds: [] });
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
  /* V0.0.42：根节点名即「根文件夹名」—— 默认置空 = 默认不建根（保持旧默认行为）。
     改名入口在树区：选中根节点 → 工具栏/右键「重命名」；清空即回到「不建根」。 */
  const root = createDir('');
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
  /* V0.0.43 · F 组：多选集合。**仅在多选（≥2）时非空** —— 单选仍只认 selectedId，
     以保持 tree-view / inspector / 键盘操作既有调用点不变。纯内存，不落盘
     （schema.json 的 editorDocument 契约里没有选中态）。 */
  selectedIds: [],
  version: '',
  connected: false,
  /* V0.0.51@r7：数据目录实测值（服务弹窗展示）。由 boot() / 「重新检测」写入 ——
     与 version 同策：离线时保留最后一次实测值，不刻意清空。 */
  dataDir: '',
  saveState: 'idle',   // idle | pending | saving | saved | error
  savedAt: '',
});

/* ---------- 视图 ---------- */

const treeView = createTreeView(el('treeCanvas'), {
  // V0.0.43 · F 组：事件一并传入，修饰键语义在选择模型里裁决（见 selectNode）
  onSelect(id, event) {
    selectNode(id, event);
  },
  // V0.0.19 拖拽：把 id 节点移到 targetDirId 下（模型层拦截非目录/成环/同名/根）
  // V0.0.43 · F 组：拖动**多选集合内**的节点 → 整组移动（需求草案 2.4 节 #2）
  onMove(id, targetDirId) {
    const root = store.get().root;
    const set = multiSelNow();
    if (set.length >= 2 && set.includes(id)) {
      batchMove(root, set, targetDirId);
      return;
    }
    const check = canMove(root, id, targetDirId);
    if (check !== true) {
      const node = findNode(root, id);
      toast(t(MOVE_ERR_KEY[check] || 'toast.moveNotDir', { name: node ? node.name : '' }), 'warn');
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
    openTreeContextMenu(id, x, y);
  },
  /* V0.0.51@r3 · 第 6 条：点**节点自带的三角**折叠 / 展开，走的是视图层的**内部重渲染**
     （tree-view.js 的 toggle 处理器直接调自己的 render，不经 main.js 的 render()）；
     视图组那颗切换按钮的图标与提示若只在本文件的 render() 里同步，就会停在上一次的状态 ——
     出现「点下去其实是展开、图标却画着折叠」的自相矛盾（**实测抓到**：见本轮行为探针 s3）。
     故视图层每完成一次内部重渲染即回调此处，与主渲染共用同一个同步函数。 */
  onFold() {
    updateToggleAllUI();
  },
});

/** 移动失败的取词键（单节点移动与整组移动共用同一套原因码）。 */
const MOVE_ERR_KEY = {
  missing: 'toast.moveMissing',
  notDir: 'toast.moveNotDir',
  cycle: 'toast.moveCycle',
  exists: 'toast.siblingExists',
  root: 'toast.moveRoot',
};

/* ---------- 多选（V0.0.43 · F 组） ----------
   选择模型：`selectedId` 恒为「锚点 / 主选中」，`selectedIds` 仅在多选（≥2）时承载
   集合 —— 保留 selectedId 使 tree-view / inspector / 键盘的既有调用点无需改动。
   集合的语义运算（净化 / 去重 / 批量移动预检）在 modules/selection.js（纯函数、可单测），
   本节只管「读 store」与「写 store」。 */

/** store 里的多选**原始值**（未净化）。 */
function multiIds() {
  const ids = store.get().selectedIds;
  return Array.isArray(ids) ? ids : [];
}

/** 当前**生效**的多选集合（已净化、且 ≥2 项才成立）—— 通往 modules/selection.js 的唯一入口。 */
function multiSelNow() {
  return multiSel(store.get().root, multiIds());
}

/**
 * 选择归约：修饰键 → 离散多选 / 范围选择 / 单选。
 *
 * - `Ctrl`/`Cmd` + 单击 → 切换该项的选中态（离散多选）
 * - `Shift` + 单击     → 从锚点到当前节点的**连续一段**（取当前可视行序，
 *                        折叠的子树不计入 —— 需求草案 2.6 节裁定）
 * - 单击（无修饰）      → 清空多选，回到单选
 */
function selectNode(id, event) {
  const root = store.get().root;
  const mod = !!(event && (event.ctrlKey || event.metaKey));
  const shift = !!(event && event.shiftKey);

  if (shift) {
    const visible = treeView.visibleIds();
    const anchor = store.get().selectedId;
    const to = visible.indexOf(id);
    if (to < 0) return;
    let from = visible.indexOf(anchor);
    if (from < 0) from = to;
    const ids = visible.slice(Math.min(from, to), Math.max(from, to) + 1);
    applySelection(ids, anchor);
    return;
  }

  if (mod) {
    if (id === root.id) return;   // 根不可多选
    const base = multiSelNow().length ? multiSelNow() : (store.get().selectedId ? [store.get().selectedId] : []);
    const next = base.filter((x) => x !== root.id);
    const at = next.indexOf(id);
    if (at >= 0) next.splice(at, 1);
    else next.push(id);
    applySelection(next, id);
    return;
  }

  store.set({ selectedIds: [], selectedId: id });
}

/** 把候选集合收口进 store：≥2 进多选态，否则塌回单选（锚点优先保留）。 */
function applySelection(ids, anchor) {
  const root = store.get().root;
  const uniq = [...new Set(ids)].filter((x) => x !== root.id);
  if (uniq.length >= 2) {
    const keep = anchor && uniq.includes(anchor) ? anchor : uniq[uniq.length - 1];
    store.set({ selectedIds: uniq, selectedId: keep });
    return;
  }
  store.set({ selectedIds: [], selectedId: uniq[0] || anchor || root.id });
}

/* ---------- 右键菜单（V0.0.19）：动作与工具栏同函数，菜单只管收集与弹出 ---------- */

const ctxMenu = createContextMenu();

/**
 * 树节点右键菜单（V0.0.19；多选语义 V0.0.43 · F 组）。
 *
 * 集合语义（需求草案 2.4 节 #3）：右键的节点**在**多选集合内 → 菜单作用于**整个集合**；
 * **不在**集合内 → 作用于该节点，并清空多选（否则「右键别的节点」会留下一个
 * 用户看不见的旧集合，下一次批量操作会误伤它）。
 */
function openTreeContextMenu(id, x, y) {
  const root = store.get().root;
  const node = findNode(root, id);
  if (!node) return;
  const set = multiSelNow();
  const inSet = set.includes(id);
  if (!inSet && multiIds().length) store.set({ selectedIds: [] });
  const scope = inSet ? set : [id];
  const isRoot = id === root.id;

  if (scope.length >= 2) {
    ctxMenu.showAt(x, y, [
      { label: t('tree.batchDelete'), danger: true, action: () => batchDelete(scope) },
      { label: t('tree.batchCopy'), action: () => batchCopy(scope) },
      { label: t('tree.batchClear'), action: () => store.set({ selectedIds: [] }) },
    ]);
    return;
  }

  ctxMenu.showAt(x, y, [
    { label: t('tree.addChild'), disabled: !isDir(node), action: () => doAddChild(id) },
    /* V0.1.0：根节点也支持重命名 / 删除。删除根＝**清空内容**（树必须有根），
       确认文案明确写「内容清空、根名保留」，避免用户以为整个文档没了。 */
    { label: t('tree.rename'), action: () => doRename(id) },
    { label: isRoot ? t('tree.clearRoot') : t('tree.delete'), danger: true,
      action: () => doDelete(id) },
    {
      label: t('tree.copyPath'),
      action: () => copyWithToast(pathOf(root, id) || node.name, 'toast.copied', 'toast.copyFailed'),
    },
  ]);
}

/* ---------- 批量操作（V0.0.43 · F 组） ---------- */

/**
 * 批量删除。
 *
 * 只作用于**最外层祖先**，故对话框里报的是**实际将被摘除的顶层项数**，
 * 可能与「已选 N 项」不等（父子同选时子被父覆盖）—— 报真实数才不至于误导。
 * 删除整体**可撤销**：撤销栈是快照式的，一次批量操作只占一格历史。
 */
function batchDelete(ids) {
  const root = store.get().root;
  const targets = outermostIds(root, liveIds(root, ids));
  if (!targets.length) return;
  if (targets.includes(root.id)) {
    toast(t('tree.batchDeleteRoot'), 'warn');
    return;
  }
  if (!window.confirm(t('tree.batchDeleteConfirm', { n: targets.length }))) return;
  pushHistory();
  const anchor = findParent(root, targets[0]);
  for (const id of targets) removeNode(root, id);
  store.set({ selectedIds: [], selectedId: anchor ? anchor.id : root.id });
  setStatus(t('status.batchDeleted', { n: targets.length }));
  markDirty();
}

/** 批量复制路径（只读操作，不入撤销栈）：一行一条，便于直接贴进资源管理器。 */
function batchCopy(ids) {
  const root = store.get().root;
  const targets = outermostIds(root, liveIds(root, ids));
  const text = targets.map((id) => pathOf(root, id)).filter(Boolean).join('\n');
  if (!text) return;
  copyWithToast(text, 'toast.batchCopied', 'toast.copyFailed', { n: targets.length });
}

/**
 * 整组移动（拖动多选集合内任一项时触发）。
 *
 * 预检 `canBatchMove` 来自 modules/selection.js（纯函数、可单测）——
 * 必须在 pushHistory **之前**跑完，快照才是改动前的状态。id 跨移动稳定，
 * 故移动后集合保持选中，用户可接着操作。
 */
function batchMove(root, ids, targetDirId) {
  const check = canBatchMove(root, ids, targetDirId);
  if (!check.ok) {
    toast(t(MOVE_ERR_KEY[check.code] || 'toast.moveNotDir', { name: check.name }), 'warn');
    return;
  }
  const target = findNode(root, targetDirId);
  pushHistory();
  for (const id of ids) moveNode(root, id, targetDirId);
  treeView.expandAll();
  store.set({ selectedIds: ids });
  setStatus(t('status.batchMoved', { n: ids.length, to: target ? target.name : '' }));
  markDirty();
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
  source: el('inspSource'),
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

  /* 多选集合可能因撤销 / 载入模板 / 恢复文档而指向已不存在的节点 → 先收敛。
     收敛会再触发一次 render（store 同步派发），故这里直接返回，避免半渲染。 */
  const raw = multiIds();
  const live = liveIds(root, raw);
  if (live.length !== raw.length || (live.length > 0 && live.length < 2)) {
    store.set({ selectedIds: live.length >= 2 ? live : [] });
    return;
  }

  // 选中节点切换即结束 note 编辑会话（V0.0.20）：换回来重编辑时重新计一格历史
  if (selectedId !== lastRenderedSelectedId) {
    noteHistoryId = null;
    lastRenderedSelectedId = selectedId;
  }
  treeView.render(root, selectedId, live);
  inspector.render(root, selectedId, live);
  inspector.renderSource(root, live.length >= 2 ? live : (selectedId ? [selectedId] : []));
  applyInspMode();
  renderBatchBar(live);
  updateSelectionUI(live);
  const stats = countTree(root);
  el('statusCount').textContent = t('status.count', { dirs: stats.dirs, files: stats.files });
  renderSaveChip();
  updateUndoUI();
  updateToggleAllUI();
}

/** 批量条：多选 ≥2 项才出现（横幅式常驻说明「已选几项 + 怎么移动」）。 */
function renderBatchBar(ids) {
  const bar = el('batchBar');
  const many = ids.length >= 2;
  bar.hidden = !many;
  if (many) el('batchInfo').textContent = t('tree.batchInfo', { n: ids.length });
}

/**
 * 多选时把「只对单个节点成立」的按钮禁用并写明原因（需求草案 5.2 节）。
 *
 * 「加子节点」与「重命名」都要一个**唯一**的作用对象，多选下语义不明；
 * 而「删除」在集合语义下有确定含义（见右键菜单与批量条），故只有这两颗被禁。
 * 用 title 说明原因 —— 光禁用不给理由是常见的可用性缺陷。
 */
function updateSelectionUI(ids) {
  const many = ids.length >= 2;
  const add = el('btnAddChild');
  const ren = el('btnRename');
  add.disabled = many;
  ren.disabled = many;
  add.title = many ? t('tree.addMultiBlocked') : '';
  ren.title = many ? t('tree.renameMultiBlocked') : '';
}

store.subscribe(render);

/* ---------- 保存状态指示（复用现有 chip 变体，不新造视觉语言；V0.0.53：改纯图标） ---------- */

const SAVE_CHIP_CLASS = {
  idle: 'chip-ghost',
  pending: 'chip-ghost',
  saving: '',
  saved: 'chip-ok',
  error: 'chip-bad',
};

/* 四态图标（V0.0.53）。全部取自**既有图标册** —— 本批零新增形状（§P0-3 L8 要求
   图标「定义 ↔ 使用」双向配对，凭空加一枚没人用的形状会当场被守卫 7aj 判红）。
   `idle` 与 `pending` 共用 `ic-save`：两者原本也都写作「未保存」，若连它也强行区分，
   就得为「无改动」再引入一枚形状，而该态在产品里几乎不可见（启动后立刻转 saved）。 */
const SAVE_CHIP_ICON = {
  idle: 'ic-save',
  pending: 'ic-save',
  saving: 'ic-refresh',   // 配 .is-spinning 转起来
  saved: 'ic-check',
  error: 'ic-close',
};

/* 四态文案（V0.0.53：**不再上屏**，改作 `aria-label` —— 视线看不见，屏幕阅读器仍读得到）。 */
const SAVE_CHIP_KEY = {
  idle: 'topbar.save.idle',
  pending: 'topbar.save.pending',
  saving: 'topbar.save.saving',
  error: 'topbar.save.error',
};

/**
 * 保存状态 chip：**只产出一枚图标** + 一句给无障碍的名字（文字不再上屏）。
 *
 * ⚠ 本函数是 `#chipSave` 内容的**唯一**产出方 ⇒ index.html 上**不得**挂 `data-i18n`，
 *   否则 applyStatic 会在每次切语言时用文本节点覆盖掉这里产出的图标。
 * ⚠ 语言切换后**必须**重跑（`qmlocalechange` 已接好），否则 `aria-label` 会停在
 *   上一种语言 —— 与 `setServiceState()` 同一个坑。
 */
function renderSaveChip() {
  const { saveState, savedAt } = store.get();
  const chip = el('chipSave');
  if (!chip) return;
  chip.className = `chip ${SAVE_CHIP_CLASS[saveState] || ''}`.trim();
  const name = saveState === 'saved'
    ? (savedAt ? t('topbar.save.savedAt', { at: savedAt }) : t('topbar.save.saved'))
    : (SAVE_CHIP_KEY[saveState] ? t(SAVE_CHIP_KEY[saveState]) : '');
  chip.setAttribute('aria-label', name);
  const icon = document.createElement('span');
  icon.className = `ic ic-sm ${SAVE_CHIP_ICON[saveState] || 'ic-save'}`
    + (saveState === 'saving' ? ' is-spinning' : '');
  icon.setAttribute('aria-hidden', 'true');
  chip.replaceChildren(icon);
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
      store.set({ root, selectedId: root.id, selectedIds: [], saveState: 'saved', savedAt: at });
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
  if (multiSelNow().length >= 2) {
    toast(t('tree.addMultiBlocked'), 'warn');
    return;
  }
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
  if (multiSelNow().length >= 2) {
    toast(t('tree.renameMultiBlocked'), 'warn');
    return;
  }
  const isRootNode = id === root.id;
  const node = findNode(root, id);
  if (!node) return;
  const name = window.prompt(t('tree.renamePrompt'), node.name);
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    /* V0.0.42：根节点名即「根文件夹名」—— 允许空名 = 不建根；非根节点仍拒空 */
    if (!isRootNode) {
      toast(t('toast.nameEmpty'), 'warn');
      return;
    }
    pushHistory();
    renameNode(root, id, '');
    store.set({});
    renderGenBar();
    setStatus(t('status.renamed', { name: t('tree.rootNoName') }));
    markDirty();
    return;
  }
  const vseg = validateSegment(trimmed);
  if (!vseg.ok) {
    toast(t('err.' + vseg.code, { name: trimmed }), 'warn');
    return;
  }
  if (trimmed === node.name) return;
  const parent = findParent(root, id);
  if (parent && hasSiblingName(parent, trimmed, id)) {
    toast(t('toast.siblingExists', { name: trimmed }), 'warn');
    return;
  }
  pushHistory();
  renameNode(root, id, trimmed);
  store.set({});
  if (isRootNode) renderGenBar();   // 根名变了 → 摘要行要跟着变
  setStatus(t('status.renamed', { name: trimmed }));
  markDirty();
}

function doDelete(id = selectedId()) {
  const root = store.get().root;
  /* V0.0.43 · F 组：多选时「删除」作用于整个集合（工具栏 / Delete 键 / 右键菜单三处共用） */
  const set = multiSelNow();
  if (set.length >= 2 && set.includes(id)) {
    batchDelete(set);
    return;
  }
  const node = findNode(root, id);
  if (id === root.id) {
    /* 根「删除」＝清空内容（V0.1.0）。仍走 pushHistory ⇒ 可撤销；
       根名保留，因为落盘时必须有一个根文件夹名。 */
    if (!window.confirm(t('tree.clearRootConfirm', { name: node ? node.name : '' }))) return;
    pushHistory();
    clearNode(root, id);
    store.set({ selectedId: root.id });
    renderGenBar();
    setStatus(t('status.clearedRoot'));
    markDirty();
    return;
  }
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

/* V0.0.51@r3 · 第 6 条：展开 / 折叠合为**一颗**切换按钮。
   方向按**当前真实折叠态**定：树里还有收起的目录 → 全部展开，已全展开 → 全部折叠。
   判据与图标同步共用 `treeView.foldStats()` 的同一个数，**只有一处真相** —— 若两处各判
   各的，迟早出现「图标显示折叠、点下去却展开」这类自相矛盾。 */
el('btnToggleAll').addEventListener('click', () => {
  const { root } = store.get();
  if (treeView.foldStats(root).collapsed > 0) treeView.expandAll();
  else treeView.collapseAll(root);
  render();
});

/* 参数一变就刷新摘要行 —— 它是生成前的核验句（目标位置 · 根名 · 演练/写盘）。
   V0.0.42：根名不再有独立输入框（真源是树区根节点名，改名后由 doRename 直接刷新摘要）。 */
el('inTarget').addEventListener('input', renderGenBar);
el('inDryRun').addEventListener('change', renderGenBar);

el('btnGenerate').addEventListener('click', async () => {
  const { root } = store.get();
  const target = el('inTarget').value.trim();
  /* V0.0.42：根名 = 树区根节点名；空 = 不建根（后端 base 直接落 target） */
  const rootName = (root.name || '').trim();
  const dryRun = el('inDryRun').checked;

  if (!target) {
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

async function copyWithToast(text, okKey, failKey, vars) {
  const ok = await copyText(text);
  toast(ok ? t(okKey, vars) : t(failKey), ok ? 'info' : 'error');
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

/* 检视器模式切换（V0.0.43 · H 组）：只切面板 + 存偏好，不动数据、不入撤销栈。 */
el('btnInspProp').addEventListener('click', () => setInspModeUI('prop'));
el('btnInspSrc').addEventListener('click', () => setInspModeUI('src'));

/* 批量条（V0.0.43 · F 组）：三颗按钮各自再取一次当前集合 —— 不用闭包里的旧值，
   因为面板可能在两次点击之间被别处（右键菜单 / Esc）改动过。 */
el('btnBatchDelete').addEventListener('click', () => batchDelete(multiSelNow()));
el('btnBatchCopy').addEventListener('click', () => batchCopy(multiSelNow()));
el('btnBatchClear').addEventListener('click', () => store.set({ selectedIds: [] }));

/* 点树区空白处取消多选（帮助页写明的路径之一）。点在行上时不处理 ——
   行的 click 会冒泡到此处，由 closest 判掉。 */
el('treeWrap').addEventListener('click', (event) => {
  if (event.target.closest('.tree-row')) return;
  if (multiIds().length) store.set({ selectedIds: [] });
});

// note 说明框失焦 = 编辑会话结束（V0.0.20）：下次聚焦重新计一格历史
el('propNote').addEventListener('blur', () => {
  noteHistoryId = null;
});

/* Ctrl/Cmd + S 立即保存；Ctrl/Cmd + Z 撤销；Ctrl/Cmd + Y / Ctrl/Cmd + Shift + Z 重做；
   Delete 删除选中节点；F2 重命名选中节点。
   V0.0.43 · F 组新增：Esc 取消多选；Ctrl/Cmd + A 选中除根以外的全部节点。
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
  /* Esc：取消多选。弹层开着时**让给弹层** —— layer.js 有自己的 Esc 监听，
     此处若也处理，会出现「关掉弹窗的同时把树区多选一并清掉」的连坐。 */
  if (event.key === 'Escape') {
    if (typing) return;
    if (layers && layers.isOpen()) return;
    if (!multiIds().length) return;
    event.preventDefault();
    store.set({ selectedIds: [] });
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
  if (key === 'a') {
    /* 全选「根之下」全部节点（需求草案 2.2 节）—— 含折叠在里面的，语义是「整棵树」 */
    const all = allNodeIds(store.get().root);
    if (!all.length) return;
    event.preventDefault();
    applySelection(all, all[0]);
    return;
  }
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

/* 帮助弹窗「模板库位置」一行的运行态快照（V0.0.51@r6）。由 ./modules/templates.js
   派发的 qmtpldirchange 更新 —— setServiceState 只管服务状态，不耦合模板模块。 */
const helpDirState = { tplDir: '', tplDirBuiltin: false };

/**
 * 把「服务状态 + 模板库位置」一并推给帮助弹窗。
 * 调用点：服务状态变（setServiceState）/ 语言变 / 模板目录变（qmtpldirchange）。
 * 未连后端时一律传空值 —— 帮助页回落到「未连接后端」说明句，而不是展示陈旧路径。
 */
function pushHelpStatus() {
  if (!helpDoc) return;
  const ready = serviceState === 'ready';
  helpDoc.setStatus({
    version: ready ? store.get().version : '',
    backendOk: ready,
    tplDir: ready ? helpDirState.tplDir : '',
    tplDirBuiltin: ready && helpDirState.tplDirBuiltin,
  });
}

/**
 * 同步「服务状态」的三处落点，各取所需：
 *   - 顶栏 #chipBackend：可点按钮（点开服务弹窗），离线加 .is-offline；
 *   - 更多浮层 #popMoreStatus：窄窗下顶栏状态文案被收进这里，须与顶栏一致；
 *   - 帮助弹窗：版本号 /「后端」/「模板库位置」三行的实测值（离线时回落本机记录值）。
 */
function setServiceState(state) {
  serviceState = state;

  const btn = el('chipBackend');
  if (btn) {
    // V0.0.53：按钮压成圆圈后**不再显示文字**，可见状态信号只剩「圆点颜色 + 下三角」；
    // 故 `.btn-txt` 的写入退场，改为把状态**合成进 `aria-label`**（状态词 + 默认名）。
    // 文字内容并没有丢：它仍在「更多 ⋮」浮层 #popMoreStatus 与服务弹窗里。
    btn.classList.toggle('is-offline', state === 'offline');
    btn.setAttribute('aria-label',
      `${t('topbar.backend.' + state)}${t('list.separator')}${t('topbar.backendTip')}`);
  }

  const moreText = el('popMoreStatus');
  if (moreText) {
    moreText.textContent = t('topbar.backend.' + state);
    const wrap = moreText.closest('.pop-more-status');
    if (wrap) wrap.classList.toggle('is-offline', state === 'offline');
  }

  // 帮助弹窗的三行实测值（版本 / 后端 / 模板库位置）在此统一同步。
  pushHelpStatus();

  // 服务弹窗的常驻字段同源同步：状态一变，顶栏与弹窗同时变（不会各说各话）。
  syncServiceDialog();
}

async function boot() {
  setServiceState('connecting');

  try {
    const info = await api.health();
    store.set({ version: info.version, connected: true, dataDir: info.dataDir || '' });
    setServiceState('ready');
    setStatus(t('status.readyWith', { nameZh: info.nameZh, app: info.app }));
  } catch (err) {
    serviceDown = true;   // 记下「起手就是断的」：日后复查翻回连上时提示刷新（见 recheckService）
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
  await Promise.all([templates.loadTemplatesDir(), templates.loadTemplateList()]);
  templates.startTemplatePolling();   // 仅在后端可用时起轮询：连不上就别空转发请求
}

/* ---------- 模板库（V0.0.11） ---------- */

/* 错误本地化已迁至 ./core/errors.js（V0.0.12）：主界面与帮助页共用同一套 `err.<code>` 取词。 */

/* V0.0.48：模板库主体（目录绑定 / 列表与轮询 / 行操作 / 另存为·新建）已整体迁至
   ./modules/templates.js —— 解单文件 64K 上限，手法与理由同 V0.0.43 拆 selection.js。
   本文件只留：① 装配（见下方 `createTemplates`）；② 生成参数区的「目标位置 · 选择…」。 */

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
  /* V0.3.5：原生框不可用时把焦点交给旁边的输入框（它一直存在，本就可手输）。
     原先弹 `window.prompt` —— 等于让用户在输入框之外再打一遍同一件事，
     多一道转场，且 prompt 里粘贴长路径无法回看。 */
  const input = el('inTarget');
  toast(t('gen.targetPastePrompt'), 'info', 6000);
  input.focus();
  input.select();
}

/** 把选中的目录写进「目标位置」输入框，并刷新折叠摘要行（否则收起态下看不到已选值）。 */
function applyTargetDir(dir) {
  el('inTarget').value = dir;
  renderGenBar();
}

/* ---------- 模板库装配（V0.0.48） ---------- */

/* `getLayers` 传 **getter** 而非值：`layers` 迟至 `initTopbar()` 才被赋值，而本行早于它执行 ——
   传值会固化 `null`，模板弹窗就再也打不开了。`el`/`t`/`api`/`toast` 由模块自行 import。 */
const templates = createTemplates({
  el, t, ctxMenu, store, getLayers: () => layers, pushHistory, setStatus, markDirty,
});

/* 目标位置「选择…」：与模板目录共用同一原生选择器（V0.0.40 · 手册 10.2 节 #13）。
   按钮位于 <label> 内，先阻止 label 把该次点击转发给输入框 —— 否则原生框弹出前
   输入框会被顺手聚焦，收起键盘态时视觉上像「没反应」。 */
el('btnPickTarget').addEventListener('click', (event) => {
  event.preventDefault();
  chooseTargetDir();
});

/* 语言切换后刷新动态文案（静态文案由 applyStatic 在 setLocale 内处理） */
document.addEventListener('qmlocalechange', () => {
  renderSaveChip();
  renderGenBar();
  render();
  setServiceState(serviceState);   // 服务状态 chip 文案随语言刷新
  if (backups) backups.render();   // 历史版本列表的时间 / 大小 / 徽标随语言刷新
  // 模板库的两处动态文案（绑定行提示 / 「新建模板」起点下拉）由 ./modules/templates.js
  // 自注册同一事件刷新 —— 搬走的是监听体，不是行为。
});

/* 换肤后重传启动图标（V0.0.15）：事件由 applySkin 在样式表 onload 后派发，
   此时 getComputedStyle 读到的已是新皮肤配色。失败静默（launch-icon 内部处理）。 */
document.addEventListener('qmskinchange', () => {
  ensureLaunchIcon();
});

/* 页面重新可见（切回标签页 / 从最小化恢复）时自动复查服务状态（V0.0.51@r8）。
   选 `visibilitychange` 而非 `focus`：切换窗口时 `focus` 会在「地址栏获得焦点」
   这类无关场景反复触发，而 `visibilitychange` 只在**页面整体可见性**变化时来一次。
   两条触发路径（开窗 / 变可见）都汇入 recheckService —— 间隔与单飞守卫在那里。 */
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') recheckService();
});

/* 模板目录变化（绑定 / 刷新 / 语言切换重渲染）后，同步帮助弹窗的「模板库位置」一行。
   事件由 ./modules/templates.js 派发 —— 它是唯一知道运行态目录的地方。 */
document.addEventListener('qmtpldirchange', (event) => {
  const res = event.detail;
  helpDirState.tplDir = (res && res.dir) || '';
  helpDirState.tplDirBuiltin = Boolean(res && res.source === 'default');
  pushHelpStatus();
});

/* 启动顺序：偏好**已在模块顶部**恢复（须早于默认示例取词，见上方 defaultRoot 处注释）；
   此处补齐静态文案与动态内容 —— 否则 applyStatic 会覆盖状态栏等动态字段 */
watchLocale();          // 另一页面（帮助页）改语言时，本页随之切换
applyStatic(document);
installTooltips();      // V0.0.51@r4 · 自绘悬停提示：须在 applyStatic 之后（title 值此刻已写入）
initTopbar();
renderGenBar();         // 参数区常显：只需把核验句填上，无需再定折叠态
render();
boot();
