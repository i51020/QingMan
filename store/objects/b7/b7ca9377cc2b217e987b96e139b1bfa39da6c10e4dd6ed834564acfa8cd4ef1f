/**
 * 青蔓 QingMan · 模板库（V0.0.48 自 main.js 整体迁出 · 行为零变更）
 *
 * 与 V0.0.43 拆出 modules/selection.js 同因：解 `verify` 7f 的**单文件 64K** 上限。
 * 迁入函数体**保留原顶层缩进** —— 纯搬迁，故可逐字节比对。文案一律经 `t(key)`（§P0-3 L1）。
 * 边界：生成参数区的「目标位置 · 选择…」不属模板库，仍在 main.js。
 */

import { api } from '../core/api.js';
import { localizeError } from '../core/errors.js';
import { readPref, writePref, t, TPL_USAGE_KEY } from '../i18n/index.js';
import { toast } from '../ui/toast.js';
import { fromNestedTree, adoptTemplateNote, treePayload } from './tree-model.js';
import { sortTemplates, SORT_NAME, SORT_EVENT, importBucket, planExternal } from './tpl-order.js';

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

/* ---------- 模板使用记录（V0.3.2） ---------- */

/**
 * 使用记录：`{ [文件名]: { last: 毫秒戳, count: 次数 } }`。
 *
 * **只存文件名，不存显示名** —— 改名后旧记录自然失效。这是有意的取舍：宁可丢掉
 * 一条记录（退回按显示名排），也不让「改过名的模板」顶着别人的使用次数排到前面。
 *
 * 排序口径本身**不在这里**（见 `./tpl-order.js`）：本模块只负责「记一次」与
 * 「读出来」，模块顶层 import 了 `core/api.js`（读 `window.location.origin`），
 * 在 Node 里导不进来 —— 拆开才能让排序口径被单测钉住。
 */
const TPL_USAGE_MAX = 200;   // 最多记 200 套，防止 localStorage 无限增长

/** 读使用记录。手改坏 / 隐私模式下取不到 —— 一律当「没有记录」，不让列表挂掉。 */
function readUsage() {
  try {
    const raw = readPref(TPL_USAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (err) {
    return {};
  }
}

function writeUsage(map) {
  try {
    writePref(TPL_USAGE_KEY, JSON.stringify(map));
  } catch (err) {
    /* 存不下就只在本次会话内生效：排序降级为纯显示名序，不影响任何功能 */
  }
}

/**
 * 记一次「用了这套模板」。
 *
 * **只在 `applyTemplate` 里调用** —— 载入编辑器才叫「用」。复制（`duplicateTemplateItem`）
 * 与「新建时以某套为起点」（`submitNewTemplate`）都会读模板，但那是取材、不是使用；
 * 若一并计入，常用模板会被「复制副本」这类一次性动作带偏。
 */
function bumpUsage(file) {
  if (!file) return;
  const map = readUsage();
  const prev = map[file] && typeof map[file] === 'object' ? map[file] : {};
  const count = Number(prev.count);
  map[file] = { last: Date.now(), count: (Number.isFinite(count) ? count : 0) + 1 };
  const files = Object.keys(map);
  if (files.length > TPL_USAGE_MAX) {
    // 超限只淘汰**最久没用**的那些（按 last 降序保留前 N 条）
    files.sort((a, b) => (Number(map[b].last) || 0) - (Number(map[a].last) || 0));
    for (const key of files.slice(TPL_USAGE_MAX)) delete map[key];
  }
  writeUsage(map);
}

/* ---------- 排序会话（V0.3.3 · 六段规则的事件源） ---------- */

/**
 * 六个排序段的会话状态。**存 `sessionStorage`，不是 `localStorage`** —— 两个理由：
 *
 *   ① **F5 不动排序**：按 F5 只是想刷新载入状态，不该把刚导入的那批打散。
 *      `sessionStorage` 与标签页同生命周期，重载后仍在；
 *   ② **关掉标签页即归零**：下次打开回到「首次进入」—— 现有模板全部收进 ③ 段、
 *      段内按名称，正是「首次载入按名称排序」。若存 `localStorage`，这份状态会跨天
 *      残留，用户半年后打开还看到上次的分段结果，反而更怪。
 *
 * 键名**故意不带 `qm.` 前缀，也不进 `i18n` 的偏好键清单**：
 *   ① 偏好键是**跨会话**的用户选择（语言 / 皮肤 / 使用记录），这份是**一次会话内**的临时
 *      排序上下文，语义不同；`verify` 7ai 只收 `localStorage` 的 `qm.*` 声明，故不涉及「三方一致」；
 *   ② 带点的名字会被 `verify` 的**取词键闭包**当成 i18n 键（`qm.tplSortSession` 实测报
 *      「取词表缺少 1 个键」）—— 无点形态从一开始就避开这条判据。
 */
const SORT_SESSION_KEY = 'qmTplSortSession';

/** 当前会话的排序上下文；`null` = 还没读过。 */
let sortSession = null;

function blankSession() {
  // 初始即**名称基线**：首次进入（sessionStorage 空）与点刷新走同一条路径，
  // 都是「整批模板按名称」。`SORT_EVENT` 只由真实操作（新建 / 导入 / 载入）打开。
  return { mode: SORT_NAME, created: [], single: [], batch: [], known: [] };
}

/** 读会话状态（脏值兜底：手改 / 旧结构一律退化为初始态，**绝不抛**）。 */
function loadSortSession() {
  if (sortSession) return sortSession;
  try {
    const raw = window.sessionStorage.getItem(SORT_SESSION_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === 'object') {
      sortSession = {
        mode: parsed.mode === SORT_NAME ? SORT_NAME : SORT_EVENT,
        created: Array.isArray(parsed.created) ? parsed.created : [],
        single: Array.isArray(parsed.single) ? parsed.single : [],
        batch: Array.isArray(parsed.batch) ? parsed.batch : [],
        known: Array.isArray(parsed.known) ? parsed.known : [],
      };
      return sortSession;
    }
  } catch (err) {
    /* 隐私模式 / 配额满 / JSON 坏：落到下面的初始态，排序退化为名称序 */
  }
  sortSession = blankSession();
  return sortSession;
}

function saveSortSession() {
  try {
    window.sessionStorage.setItem(SORT_SESSION_KEY, JSON.stringify(sortSession));
  } catch (err) {
    /* 存不下就只在本次页面内存里生效：F5 后回到名称序，不影响任何功能 */
  }
}

/**
 * 把文件记进某个新段，并同步推入 `known`。
 *
 * **必须同步 `known`**：否则紧接着的 `loadTemplateList` 做 diff 时，这个刚由前端
 * 造出来的文件会被当成「外部新增」—— 于是「新建」被降级成「③ 批量导入」，
 * 优先级悄悄掉一档（这类错误在界面上完全看不出来，只能靠单测钉住）。
 */
function markFresh(bucket, files) {
  const s = loadSortSession();
  let touched = false;
  for (const f of files || []) {
    if (!f) continue;
    if (s[bucket].indexOf(f) < 0) { s[bucket].push(f); touched = true; }
    if (s.known.indexOf(f) < 0) { s.known.push(f); touched = true; }
  }
  if (!touched) return;
  // 真的产出了新模板才离开「纯名称」基线 —— 空调用不该打破刷新后的基线
  s.mode = SORT_EVENT;
  saveSortSession();
}

/** ① 本次新建（新建 / 另存为 / 复制，都算「应用内产生的新模板」）。 */
function markCreated(file) { markFresh('created', [file]); }

/**
 * ② 单个导入 / ③ 批量导入（V0.3.4 起按「本次选了几个文件」分段）。
 *
 * 判据来自 `importBucket`（纯函数、可单测）：**一次选 1 个 → ②**，**一次选多个 → ③**。
 * 连续多次单选都落进 ② 段，段内一律按名称 —— 用户要的「连续操作等同同批」自动成立，
 * 不需要额外记「上一步是不是导入」。
 */
function markImported(files, count) {
  const n = count === undefined ? (files || []).length : count;
  markFresh(importBucket(n), files);
}

/**
 * ③ 本次批量导入 / 外部新增（轮询发现的名字）。
 *
 * 全部状态转移交给 `planExternal`（`./tpl-order.js` 的纯函数）——**首次进入只登记
 * `known`、不建段**。旧实现（V0.3.3）把整库存量写进 ③ 段，只靠 `mode=SORT_NAME`
 * 暂时掩盖；`mode` 一旦切到 `SORT_EVENT`（载入 / 新建 / 导入），存量立刻冒充
 * 「本次批量导入」，把真正用过的模板全部压到后面。回归位见 `test_v033` 的
 * `TPL/ext-first-sight`。
 */
function markExternal(files) {
  const s = loadSortSession();
  const plan = planExternal(s, files);
  s.mode = plan.session.mode;
  s.created = plan.session.created;
  s.single = plan.session.single;
  s.batch = plan.session.batch;
  s.known = plan.session.known;
  saveSortSession();
}

/**
 * 载入一套模板 ⇒ 它「被使用过」了，退出 ①②③ 新段（`freshRank` 见 count > 0 即出队），
 * 改按 ④⑤ 排。故模式必须切到 EVENT —— 点刷新后的名称基线到此为止。
 */
function markUsed() {
  const s = loadSortSession();
  if (s.mode === SORT_EVENT) return;
  s.mode = SORT_EVENT;
  saveSortSession();
}

/**
 * 点「刷新」：回到纯名称基线。
 *
 * 三个新段与 `known` **全部清空** —— 于是下一次列表加载会把现有模板整批收进 ③ 段；
 * 而 `mode` 停在 `SORT_NAME` 时排序根本不看这些段，直接按名称。
 * 这个基线**保持到下一次真正产出新模板**（新建 / 导入），载入模板不会打破它：
 * 否则「点刷新回到名称序」就只维持到用户点第一个模板为止，等于没生效。
 */
function resetSortSession() {
  sortSession = blankSession();
  sortSession.mode = SORT_NAME;
  saveSortSession();
}

/** 排序上下文 —— 三处调用点（左侧列表 / 起点下拉 / 载入后重排）共用一份口径。 */
function sortCtx() {
  const s = loadSortSession();
  return { mode: s.mode, usage: readUsage(), fresh: s };
}

/* ---------- 模板目录绑定（V0.0.38 · 6E） ---------- */

/** 最近一次 `GET /api/templates-dir` 的响应；切换语言时用它重渲染动态文案（不再请求）。 */
let lastDirRes = null;

/** 当前**生效**的模板目录（服务端回报值）。V0.3.5：输入框改为可编辑后，它是
 *  「脏值判断」与「Esc 还原」的基线 —— 没有它就无法区分「用户改了」与「渲染回填」。 */
let dirBase = '';

/** 绑定请求序号（V0.3.5）：失焦提交可能连发两次，用序号作废旧响应。 */
let dirBindSeq = 0;

/**
 * 绑定请求的串行队列（V0.3.7）。
 *
 * 序号只能作废**界面**上的旧响应，管不了**服务端落盘顺序**：连改两次时若两个 PUT
 * 并发到达，谁先落盘由网络/线程调度决定 —— 最终 settings 里可能是**先点的那次**，
 * 而界面显示的是后点的那次，两边不一致且无法自愈。排队后「最后一次提交」必定最后
 * 落盘，序号再负责让中间那次的提示不打扰用户。
 */
let dirBindChain = Promise.resolve();

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
  /* V0.3.5：控件是 <input>，路径走 `value`（原 <code> 用 textContent）。
     占位符沿用 `dirUnknown`（「（未读取）」）—— 读不到目录时框内是空值，
     正好由它说明状态，不必新增取词键。
     V0.3.7：**用户正在编辑时不回填**。`loadTemplatesDir()` 会在绑定成功、语言切换等
     时机被调，若无条件写 `value`，正好把敲了一半的路径冲掉（V0.3.5 引入可编辑输入框
     后新出现的覆盖源）。基线 `dirBase` 照常推进，Esc / 失焦的语义不受影响。 */
  const editing = document.activeElement === pathEl
    && (pathEl.value || '').trim() !== dirBase;
  if (!editing) {
    pathEl.value = dir;
    pathEl.title = dir;
  }
  pathEl.placeholder = t('template.dirUnknown');
  dirBase = dir;

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

/** 绑定目录 → 成功后刷新路径行与列表；被 env 遮蔽时如实提示（settings 已写但未生效）。
 *
 *  ⚠ V0.3.5 `create: false`：服务端默认会 `mkdir` 目标目录，好让「先绑定后放模板」
 *  这种用法成立。但手输通道上线后，打错一个字的代价是**凭空多一个空目录 + 模板
 *  列表被清空**，用户只看到一句「已绑定」。故两条通道统一要求目录**已存在**：
 *  不存在就报错，由 `catch` 把输入框退回原值。
 */
async function bindTemplatesDir(dir) {
  /* V0.3.5：失焦提交让「连着改两次」变得容易（A 失焦 → 输入 B → 再失焦），而两次
     PUT 的返回顺序没有保证。用序号作废旧响应 —— 只作废**提示与回退**，刷新照旧，
     否则旧请求的 toast / 回退会盖掉新请求的结果。
     V0.3.7 追加**串行队列**：序号管界面，队列管落盘顺序（见 `dirBindChain` 注释）。 */
  const seq = ++dirBindSeq;
  const run = () => bindTemplatesDirNow(dir, seq);
  dirBindChain = dirBindChain.then(run, run);
  return dirBindChain;
}

async function bindTemplatesDirNow(dir, seq) {
  try {
    const res = await api.setTemplatesDir(dir, { create: false });
    if (seq === dirBindSeq) {
      if (res.applied === false) {
        toast(t('template.dirEnvShadow', { dir: res.effectiveDir || '' }), 'warn', 6000);
      } else {
        toast(t('template.dirBound', { dir: res.dir || dir }), 'ok');
      }
    }
    await loadTemplatesDir();
    await loadTemplateList();
  } catch (err) {
    if (seq !== dirBindSeq) return;   // 已有更新的绑定在途：本次错误不再打扰用户
    toast(t('template.dirBindFailed', { message: localizeError(err) }), 'warn', 6000);
    /* V0.3.5：绑定失败时把输入框退回「当前生效值」。否则框里留着一条非法路径，
       看上去像已经切过去了 —— 而列表显示的其实还是旧目录。
       V0.3.7：**焦点还在框里就不回退**（Enter 提交这条路上，用户正要接着改错字；
       强行回填等于把刚敲的内容抹掉，比保留一条非法路径更难用）。 */
    const input = el('tplDirPath');
    if (document.activeElement !== input) input.value = dirBase;
  }
}

/**
 * 提交输入框里的路径（V0.3.5）。
 *
 * 只在「非空且确实改过」时才发请求：失焦会频繁触发，若每次都打一次
 * `templates-dir` 写接口，用户点一下别处就等于重绑一次目录（还会弹 toast）。
 */
function commitDirInput() {
  const input = el('tplDirPath');
  const typed = (input.value || '').trim();
  if (!typed || typed === dirBase) {
    input.value = dirBase;   // 空值 / 未改动：回到生效值，不发请求
    return;
  }
  bindTemplatesDir(typed);
}

/** 路径输入框的两条键盘出口：Enter 提交、Esc 放弃本次编辑。 */
function initDirInput() {
  const input = el('tplDirPath');
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      commitDirInput();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      input.value = dirBase;
      input.blur();
    }
  });
  input.addEventListener('blur', commitDirInput);
}

/**
 * 「选择…」：优先原生目录框；用不了则把焦点交回**输入框**（V0.3.5 之前的降级是
 * `window.prompt`，现由常驻输入框承担同一条通道）。选中后只把路径交给
 * `bindTemplatesDir` —— 「选择」与「绑定」两步分离。
 *
 * V0.3.7：降级**分四路**，不再一律「打不开」。此前「服务没连上」「被 env 关断」
 * 「本机没有可用对话框」在界面上是同一句话，用户既不知道该启动服务、也不知道
 * 缺什么组件 —— 而这三种情况的处置方式完全不同。
 */
async function chooseTemplatesDir() {
  let res;
  try {
    res = await api.pickTemplatesDir();
  } catch (err) {
    // 网络层失败：根本没连上本机服务（线上版 / 服务未启动）。原生框无从谈起。
    toast(t('template.dirPickerOffline'), 'warn', 8000);
    focusDirInput();
    return;
  }
  if (res.available && !res.cancelled && res.dir) {
    await bindTemplatesDir(res.dir);
    return;
  }
  if (res.available && res.cancelled) return;   // 用户主动取消：静默
  if (res.reason === 'disabled') {
    toast(t('template.dirPickerDisabled'), 'info', 8000);
    focusDirInput();
    return;
  }
  /* 能力缺失 → 说明**具体原因**，并把焦点送到输入框，用户当场就能手输 + 回车。
     比弹 prompt 少一次转场，也不会出现「prompt 文本无法换行/无法粘贴多段」的问题。 */
  const why = String(res.message || '').trim();
  toast(t('template.dirPastePrompt', {
    reason: why || t('template.dirReasonUnknown'),
  }), 'info', 8000);
  focusDirInput();
}

/** 把焦点与选择范围交给路径输入框（降级通道的唯一入口）。 */
function focusDirInput() {
  const input = el('tplDirPath');
  if (!input) return;
  input.focus();
  input.select();
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
  // 签名**只取后端原序**（`file|mtime|size`）。刻意**不并入**排序结果：排序含使用
  // 记录，若进签名，载入一套模板就会让下一次轮询判定「变了」→ 重建 DOM，
  // 正在浏览的用户会看到滚动位置被重置（与 V0.0.38 · 6E 的防抖动取舍同源）。
  const sig = templateSignature(res);
  if (!force && sig === tplSignature) return;
  tplSignature = sig;

  // 外部新增（V0.3.3）：本次列表里出现、上一轮没见过的文件 ⇒ 归入 ③ 段。
  // 基准是 sessionStorage 里的 `known` —— 于是 F5 后不会把已有模板误判成新增，
  // 而点刷新时 `known` 被清空 ⇒ 现有模板整批收进 ③ 段（段内按名称）。
  const sess = loadSortSession();
  const freshFiles = items
    .filter((it) => it && it.file && sess.known.indexOf(it.file) < 0)
    .map((it) => it.file);
  if (freshFiles.length) markExternal(freshFiles);
  // 基准始终推到最新：删掉 / 改名的旧名字不能永远占着 `known`，否则同名文件下次
  // 出现时会被当成「已见过」而悄悄漏掉一次置顶
  sess.known = items.map((it) => it.file);
  saveSortSession();

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
  // 顺序：六段规则（V0.3.3，口径见 ./tpl-order.js）
  for (const item of sortTemplates(items, sortCtx())) {
    const li = document.createElement('li');
    li.className = 'tpl-row';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tpl-item';
    btn.title = item.description || item.name;
    const name = document.createElement('span');
    name.className = 'tpl-name';
    name.textContent = item.name;
    /* V0.3.6：模板包是 `.json` + `.md` **双格式并存**，同源两套的显示名一模一样，
     * 列表里会出现两条看不出差别的条目 —— 用户无法判断该删/该载哪一条。
     * 故把**文件格式**摆到名称右侧（仅此一处能区分）。取扩展名而非写死格式：
     * 未来若支持别的后缀，这里自动跟上。无扩展名（理论上不会）则不渲染徽标。
     * 注：`prototype_20261014.html:1254` 的 `.tpl-badge` 本就是 json/md 语义；
     * 现实现把它用作「内置/用户」层标签，两者都要，故格式另起 `.tpl-fmt`。 */
    const extMatch = /\.([A-Za-z0-9]+)$/.exec(String(item.file || ''));
    const nameRow = document.createElement('span');
    nameRow.className = 'tpl-name-row';
    nameRow.append(name);
    if (extMatch) {
      const fmt = document.createElement('span');
      fmt.className = 'tpl-fmt';
      fmt.textContent = `.${extMatch[1].toLowerCase()}`;
      fmt.title = item.file;            // 悬停给全文件名，含重名时的完整依据
      nameRow.append(fmt);
    }
    const meta = document.createElement('span');
    meta.className = 'tpl-meta';
    const badge = document.createElement('span');
    badge.className = 'tpl-badge';
    badge.textContent = t(layerKey);
    const stats = document.createElement('span');
    stats.className = 'tpl-stats';
    stats.textContent = t('template.stats', { dirs: item.dirs, files: item.files });
    meta.append(badge, stats);
    btn.append(nameRow, meta);
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
    /* V0.2.0：导出分两种格式（模板默认存 `.json`，`.md` 便于人读/进版本库）。 */
    { label: t('template.exportJson'), action: () => exportTemplateItem(item, 'json') },
    { label: t('template.exportMd'), action: () => exportTemplateItem(item, 'md') },
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
    const made = await api.saveTemplate({ name: next, tree: res.tree });
    markCreated(made && made.file);   // 复制也是「应用内产生的新模板」，与新建同段置顶
    toast(t('template.duplicated', { name: next }), 'ok');
    await loadTemplateList();
  } catch (err) {
    toast(localizeError(err) || t('template.opFailed'), 'warn', 6000);
  }
}

/**
 * 导出模板（V0.0.38 · 6E；V0.2.0 起可选格式）：取后端给的文本，按响应的 `file`
 * 触发下载。**转换也由后端做**（`?format=`），前端不二次序列化 —— 否则两侧迟早漂移。
 */
async function exportTemplateItem(item, fmt) {
  try {
    const res = await api.exportTemplate(item.file, fmt);
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
  /* V0.3.4：一次可选多套。此前仅 `files[0]`（连 `multiple` 都没有），17 套模板
     要开 17 次选择框 —— 这是「批量」诉求里最便宜、收益最高的一处。 */
  input.multiple = true;
  input.accept = '.json,.md,application/json,text/markdown';
  input.addEventListener('change', async () => {
    const files = Array.prototype.slice.call(input.files || []);
    if (!files.length) return;
    if (files.length === 1) {
      const file = files[0];
      let text;
      try {
        text = await file.text();
      } catch (err) {
        toast(t('template.importFailed', { message: localizeError(err) }), 'warn', 6000);
        return;
      }
      await submitImport(file.name, text);
      return;
    }
    await importFiles(files);
  });
  input.click();
}

/**
 * 批量导入（V0.3.4）：串行落盘，**同名默认不覆盖**，全部跑完后一次性询问。
 *
 * 为什么不逐个弹确认：选 10 套里有 6 套同名，逐个 `confirm` 就是 6 次打断；而且
 * 「要不要覆盖」是一个**批量决定**，一次问清才符合直觉。跳过的那些不算失败 ——
 * 汇总里单独报，用户才知道「没导入」是因为同名，不是坏了。
 *
 * 串行而非并发：后端每个请求都要落盘 + 可能进回收站，并发只会让错误顺序不可读，
 * 也拿不到「第几个失败」的确定结果；模板只有几 KB，串行的等待可以忽略。
 */
async function importFiles(files) {
  const ok = [];
  const conflict = [];
  const failed = [];
  for (const file of files) {
    let text;
    try {
      text = await file.text();
    } catch (err) {
      failed.push(file.name);
      continue;
    }
    try {
      const res = await api.importTemplate({ filename: file.name, content: text });
      ok.push((res && res.file) || file.name);
    } catch (err) {
      if (err && err.code === 'templateExists') conflict.push({ file, text });
      else failed.push(file.name);
    }
  }

  let skipped = 0;
  if (conflict.length) {
    if (window.confirm(t('template.importBatchOverwriteConfirm', { n: conflict.length }))) {
      for (const row of conflict) {
        try {
          const res = await api.importTemplate({
            filename: row.file.name, content: row.text, overwrite: true,
          });
          ok.push((res && res.file) || row.file.name);
        } catch (err) {
          failed.push(row.file.name);
        }
      }
    } else {
      skipped = conflict.length;
    }
  }

  // 段归属按**本次选中数**判（选 5 个、4 个跳过，仍是「一次批量导入」）
  if (ok.length) markImported(ok, files.length);
  toast(t('template.importBatchResult', {
    ok: ok.length, skip: skipped, fail: failed.length,
  }), failed.length ? 'warn' : 'ok', 6000);
  if (ok.length) await loadTemplateList();
}

/** 提交导入；同名时询问是否覆盖（覆盖后旧模板由后端移入 `.trash/`，可找回）。 */
async function submitImport(filename, text) {
  let saved = filename;
  try {
    const res = await api.importTemplate({ filename, content: text });
    saved = (res && res.file) || filename;
  } catch (err) {
    if (!err || err.code !== 'templateExists') {
      toast(t('template.importFailed', { message: localizeError(err) }), 'warn', 6000);
      return;
    }
    if (!window.confirm(t('template.importOverwriteConfirm', { name: filename }))) return;
    try {
      const res2 = await api.importTemplate({ filename, content: text, overwrite: true });
      saved = (res2 && res2.file) || filename;
    } catch (err2) {
      toast(t('template.importFailed', { message: localizeError(err2) }), 'warn', 6000);
      return;
    }
  }
  // ② 本次单个导入。**连续多次导入自动并入同一批** —— 段内一律按名称排，
  // 所以「连续操作等同同批」不需要额外判「上一步是不是导入」，结果本就一致。
  markImported([saved]);
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
  /* V0.3.6：改名同样按**文件**生效，同名两份要能分辨，故一并带上文件名。 */
  const input = window.prompt(t('template.renamePrompt', { name: item.name, file: item.file }), item.name);
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
  /* V0.3.6：确认框必须带**文件名**。同名 `.json` / `.md` 的显示名完全相同，
   * 只说「确认删除模板「X」」时用户根本不知道删的是哪一份 —— 这正是要修的坑。 */
  if (!window.confirm(t('template.deleteConfirm', { name: item.name, file: item.file }))) return;
  try {
    await api.deleteTemplate(item.file);
    toast(t('template.deleted', { name: item.name, file: item.file }), 'ok');
    await loadTemplateList();
  } catch (err) {
    toast(localizeError(err) || t('template.opFailed'), 'warn', 6000);
  }
}

async function applyTemplate(item) {
  /* V0.3.6：同上 —— 载入的是**某一份文件**，同名两套内容可能不同，须先分清。 */
  if (!window.confirm(t('template.loadConfirm', { name: item.name, file: item.file }))) return;
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
    bumpUsage(item.file);   // 载入成功才算「用过一次」
    // 用过即退出 ①②③ 新段（`tpl-order` 的 `freshRank` 见 count > 0 就出队），改按
    // ④ 最近使用 / ⑤ 频率 排。**必须主动重排**：轮询签名只看 `file|mtime|size`，
    // 载入不改这三者 ⇒ 不会自己触发重渲染；少了这一句，用户点完模板就看不到顺序变化。
    // 重排会重建 DOM，故前后暂存父容器的滚动位置，免得列表跳回顶部。
    const scroller = el('templateList') ? el('templateList').parentElement : null;
    const keepScroll = scroller ? scroller.scrollTop : 0;
    markUsed();
    await loadTemplateList();
    if (scroller) scroller.scrollTop = keepScroll;
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
    markCreated(res.file);   // 另存为同样产出新模板 ⇒ 与「新建」同段
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
    // 与左侧列表同一口径（V0.3.3）：下拉里看到的次序不该和列表里不一样
    for (const item of sortTemplates((res && res.items) || [], sortCtx())) {
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
    markCreated(res.file);   // ① 本次新建：置于列表最前（须早于 loadTemplateList，见 markFresh）
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
  el('btnRefreshTpl').addEventListener('click', () => {
    resetSortSession();   // 刷新 = 回到纯名称基线（V0.3.3，六段规则全部让位）
    loadTemplatesDir();
    loadTemplateList();
  });

  /* V0.3.5：路径输入框的双通道另一半（Enter / Esc / 失焦提交）。
     ⚠ 两个按钮各自吃掉 `mousedown` 的默认行为：不让点击把它们抢焦点过去，
     否则敲了一半的路径会先触发 blur 提交、紧接着按钮又发起一次绑定 ——
     同一次点击打两个写请求，还会连弹两条 toast。 */
  initDirInput();
  for (const id of ['btnPickDir', 'btnRefreshTpl']) {
    el(id).addEventListener('mousedown', (event) => event.preventDefault());
  }

  /* 语言切换后刷新本模块的动态文案（静态文案由 applyStatic 在 setLocale 内处理） */
  document.addEventListener('qmlocalechange', () => {
    renderTemplatesDir(lastDirRes);  // 绑定行提示是动态文案，须随语言重渲染
    // 起点下拉的「空白」项是取词键须重填；判**具体**那个层用 isOpenNode（isOpen 只答「有没有」）。
    const lv = getLayers();
    if (lv && lv.isOpenNode(el('dlgNewTemplate'))) fillTemplateBaseOptions();
  });

  return { loadTemplatesDir, loadTemplateList, startTemplatePolling };
}
