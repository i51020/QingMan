/**
 * 青蔓 QingMan · 目录树数据模型
 * 纯数据操作，不碰 DOM、不碰网络。
 *
 * 内存节点结构：{ id, type:'dir'|'file', name, children:[], content?, note? }
 *
 * note（V0.0.17）：节点说明，纯文本编辑态元数据 —— 随文档持久化，
 * 但**不参与** /api/generate 落盘（`toPlainTree` 只取 name/content）。
 * 工具不解析、不渲染、不校验 Markdown 语法（.md 边界裁定）。
 *
 * 说明：本模块会取词（§P0-3 L1）—— 抛出的错误消息面向用户，统一来自取词表。
 * 取词模块不在顶层触碰 DOM / localStorage，故此处导入不会破坏「纯数据」定位。
 */

import { t } from '../i18n/index.js';

/** 规范化 note：非字符串一律归空串（老文档缺失 / 脏数据容忍）。 */
export function normalizeNote(value) {
  return typeof value === 'string' ? value : '';
}

/* ---------- id 分配：唯一性靠判定，不靠概率 ---------- */

/** 已派发的 id 集合。跨会话恢复文档后由 reserveIds() 补登。 */
const usedIds = new Set();
let counter = 0;

/**
 * 派发一个全局唯一 id。
 *
 * 形态：`<前缀><时间基36><计数36>`，前缀固定 `d` = 目录 / `f` = 文件。
 * 生成后立即登记进 usedIds；撞号则推进计数重试 —— 唯一性由集合判定保证，
 * 不依赖「同一毫秒不会撞」这类概率假设。
 */
export function uid(prefix = 'n') {
  let id = '';
  do {
    counter += 1;
    id = `${prefix}${Date.now().toString(36)}${counter.toString(36)}`;
  } while (usedIds.has(id));
  usedIds.add(id);
  return id;
}

/**
 * 把一棵树（或任意含 id / children 的对象）里的全部 id 登记进 usedIds。
 *
 * **从持久化文档恢复后必须调用**，否则新派发的 id 可能与文档里的既有 id 撞号。
 * 返回新登记的 id 数量。
 */
export function reserveIds(node) {
  let added = 0;
  const walk = (n) => {
    if (!n || typeof n !== 'object') return;
    if (typeof n.id === 'string' && n.id && !usedIds.has(n.id)) {
      usedIds.add(n.id);
      added += 1;
    }
    if (Array.isArray(n.children)) n.children.forEach(walk);
  };
  walk(node);
  return added;
}

/** 返回全树中重复出现的 id（空数组 = 每个 id 唯一）。供校验与测试断言。 */
export function assertUniqueIds(node) {
  const seen = new Set();
  const dup = new Set();
  const walk = (n) => {
    if (!n || typeof n !== 'object') return;
    if (typeof n.id === 'string' && n.id) {
      if (seen.has(n.id)) dup.add(n.id);
      else seen.add(n.id);
    }
    if (Array.isArray(n.children)) n.children.forEach(walk);
  };
  walk(node);
  return [...dup];
}

/** 清空 id 登记表。仅供「新建空白文档」与测试使用，常规编辑流程不得调用。 */
export function resetIdRegistry() {
  counter = 0;
  usedIds.clear();
}

/* ---------- 节点构造与查询 ---------- */

export function isDir(node) {
  return !!node && node.type === 'dir';
}

export function createDir(name) {
  return { id: uid('d'), type: 'dir', name, children: [] };
}

export function createFile(name, content = '') {
  return { id: uid('f'), type: 'file', name, content };
}

/**
 * 查询族一律用**显式栈**而非递归（B-P3-5）。
 *
 * 树深由用户输入决定（`MAX_EDITOR_NODES` = 20000，深链可逼近该值）；递归实现会在
 * 深树上撞 JS 引擎调用栈上限抛 `RangeError: Maximum call stack size exceeded`。
 * 显式栈把栈搬到堆，深度不再受引擎限制。**语义与旧递归实现一致**（id 全局唯一，
 * 遍历顺序不影响命中结果）。
 */
export function findNode(root, id) {
  if (!root) return null;
  const stack = [root];
  while (stack.length) {
    const node = stack.pop();
    if (node.id === id) return node;
    if (isDir(node)) for (const child of node.children) stack.push(child);
  }
  return null;
}

export function findParent(root, id) {
  if (!root || !isDir(root)) return null;
  const stack = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!isDir(node)) continue;
    for (const child of node.children) {
      if (child.id === id) return node;
      stack.push(child);
    }
  }
  return null;
}

export function addChild(parent, node) {
  if (!isDir(parent)) return false;
  parent.children.push(node);
  return true;
}

/**
 * 节点是否在 target 的子树内（含相等）。
 * 拖拽防环用：把目录移进它自己的子孙里会形成环，必须拦截。
 * 显式栈实现（B-P3-5），语义同旧递归版（含 `!node → true` 的历史行为）。
 */
export function isSelfOrDescendant(node, id) {
  if (!node || node.id === id) return true;
  if (!isDir(node)) return false;
  const stack = [...node.children];
  while (stack.length) {
    const n = stack.pop();
    if (n.id === id) return true;
    if (isDir(n)) for (const c of n.children) stack.push(c);
  }
  return false;
}

/**
 * 移动合法性检查（不改数据）。让调用方能在**入撤销栈之前**判定，
 * 保证 pushHistory 快照的是改动前的状态。
 * @returns {true | 'missing' | 'notDir' | 'cycle' | 'exists' | 'root'}
 */
export function canMove(root, id, targetDirId) {
  if (!root || id === root.id) return 'root';
  const node = findNode(root, id);
  if (!node) return 'missing';
  const target = findNode(root, targetDirId);
  if (!target || !isDir(target)) return 'notDir';
  if (isSelfOrDescendant(node, targetDirId)) return 'cycle';
  if (hasSiblingName(target, node.name, id)) return 'exists';
  if (!findParent(root, id)) return 'root';
  return true;
}

/**
 * 把 id 节点移动到 targetDir 下（V0.0.19 拖拽）。
 * 拦截四类非法移动：目标不是目录 / 移入自身或子孙（防环）/ 目标目录已有同名 / 根节点不可移动。
 * 纯数据操作，撤销栈由调用方管理（与重命名/删除同路）。
 * @returns {true | 'missing' | 'notDir' | 'cycle' | 'exists' | 'root'}
 */
export function moveNode(root, id, targetDirId) {
  const check = canMove(root, id, targetDirId);
  if (check !== true) return check;
  const node = findNode(root, id);
  const target = findNode(root, targetDirId);
  removeNode(root, id);
  addChild(target, node);
  return true;
}

/**
 * 重命名节点。**自校验**（B-P3-3）：名字非法或同层重名一律拒改并返回 `false`。
 *
 * 此前只查「节点存在 / 非根」，重名与合法性完全依赖调用方 —— 新增调用点极易漏检，
 * 留下「UI 显示成功、落盘被服务端拒」的不一致。此处复用同模块的 `validateSegment`
 * 与 `hasSiblingName`，把不变式收在被改的模型里（函数声明提升，前向引用无碍）。
 */
export function renameNode(root, id, name) {
  const node = findNode(root, id);
  if (!node) return false;
  /* V0.0.42：根节点名 = 「根文件夹名」——允许改名，且允许置空（空名 = 不建根）。
     非根节点保持原自校验（B-P3-3）：非法字符 / 空 / 同级重名一律拒。 */
  if (root.id === id) {
    if (name !== '' && !validateSegment(name).ok) return false;
    node.name = name;
    return true;
  }
  if (!validateSegment(name).ok) return false;
  if (hasSiblingName(findParent(root, id), name, id)) return false;
  node.name = name;
  return true;
}

/**
 * 清空节点内容（V0.1.0 · 根节点「删除」的语义）。
 *
 * 树必须有根 —— 所以根的「删除」不是摘除节点，而是**清空它的全部子节点**。
 * **根的名字一并重置为空**（空名 = 不建根，V0.0.42 起的合法状态）：只清子节点、
 * 留着旧根名，与随之出现的空态提示自相矛盾（用户裁定，记录见任务进度 V0.3.11）。
 * 非根目录清空**不动名** —— 目录还在，名字是它的身份。
 * 与 `removeNode` 分开而不是重载：两者对撤销栈都是"一次操作"，但语义完全不同，
 * 合成一个函数会让调用方靠 `id === root.id` 猜行为（正是 B-P3-3 那类不一致的来源）。
 */
export function clearNode(root, id) {
  const node = findNode(root, id);
  if (!node || !isDir(node)) return false;
  node.children = [];
  if (root.id === id) node.name = '';
  return true;
}

export function removeNode(root, id) {
  const parent = findParent(root, id);
  if (!parent) return false;
  const index = parent.children.findIndex((child) => child.id === id);
  if (index < 0) return false;
  parent.children.splice(index, 1);
  return true;
}

/**
 * 同层是否已有同名节点。
 *
 * 比较**大小写不敏感** —— 落盘目标多为 Windows 文件系统，`A` 与 `a` 会互相覆盖。
 * 重命名时用 exceptId 排除自身。空名不算冲突（由调用方另行拦截）。
 */
export function hasSiblingName(parent, name, exceptId = null) {
  if (!isDir(parent)) return false;
  const key = String(name || '').trim().toLowerCase();
  if (!key) return false;
  return parent.children.some(
    (child) => child.id !== exceptId && String(child.name || '').trim().toLowerCase() === key,
  );
}

/* ---------- 名字合法性（前端轻校验 + 服务端权威，B-P2-1 修正） ---------- */

/** Windows 文件名非法字符 —— 用户可即时理解的语法级字符（\ / : * ? " < > |）。 */
const ILLEGAL_CHARS = new Set(['/', '\\', ':', '*', '?', '"', '<', '>', '|']);

/** 单段名长度上限 —— 与后端 `validate_segment` 的 120 一致。 */
const MAX_SEGMENT_LENGTH = 120;

/**
 * 前端**轻校验**（即时语法级）：仅拦截用户立刻能理解的非法字符 / 空 / 过长 / "." / ".."。
 *
 * **完整业务规则（Windows 保留名、尾随空白 / 点等）由服务端 `dtree_core.validate_segment`
 * 作为唯一权威裁决** —— 前端不镜像这些业务规则，避免「前端 / 后端双份规则」漂移
 * （评审文档裁决：采纳「前端轻校验 + 服务端权威」，撤销早期「前端镜像后端」方案）。
 *
 * 返回 `{ ok, code }`：`code` 为错误码（如 `segmentIllegalChar`），调用方用
 * `t('err.' + code, { name })` 本地化成句，与后端错误码共用同一套取词文案。
 */
export function validateSegment(name) {
  if (typeof name !== 'string') return { ok: false, code: 'segmentNotString' };
  const s = name.trim();
  if (!s) return { ok: false, code: 'segmentEmpty' };
  if (s === '.' || s === '..') return { ok: false, code: 'segmentDot' };
  if (s.length > MAX_SEGMENT_LENGTH) return { ok: false, code: 'segmentTooLong' };
  for (const ch of s) {
    if (ILLEGAL_CHARS.has(ch) || ch.codePointAt(0) < 32) {
      return { ok: false, code: 'segmentIllegalChar' };
    }
  }
  return { ok: true, code: '' };
}

/* ---------- 统计与路径 ---------- */

export function countTree(node) {
  let dirs = 0;
  let files = 0;
  if (!isDir(node)) return { dirs, files };
  for (const child of node.children) {
    if (isDir(child)) {
      dirs += 1;
      const sub = countTree(child);
      dirs += sub.dirs;
      files += sub.files;
    } else {
      files += 1;
    }
  }
  return { dirs, files };
}

/**
 * 路径（`A / B / C`）。显式栈 + **父指针映射**（B-P3-5）。
 *
 * 不用「栈里带全路径字符串」的做法：那对线性深链是 O(深度²) 的字符串构建
 * （20000 层会吃掉上 GB 中间串）。先一遍 DFS 建 `child → parent` 映射并定位目标，
 * 再从目标回溯到根拼名字 —— **O(n) 时间 / O(n) 空间**，输出格式与旧递归版一致。
 */
export function pathOf(root, id) {
  if (!root) return '';
  if (root.id === id) return root.name;
  const parent = new Map();
  const stack = [root];
  let target = null;
  while (!target && stack.length) {
    const node = stack.pop();
    if (!isDir(node)) continue;
    for (const child of node.children) {
      parent.set(child, node);
      if (child.id === id) {
        target = child;
        break;
      }
      stack.push(child);
    }
  }
  if (!target) return '';
  const names = [];
  for (let cur = target; cur && cur !== root; cur = parent.get(cur)) names.push(cur.name);
  names.push(root.name);
  return names.reverse().join(' / ');
}

/** 深度（根 = 0）。显式栈（B-P3-5），保留第三参以兼容既有调用。 */
export function depthOf(root, id, depth = 0) {
  if (!root) return -1;
  const stack = [[root, depth]];
  while (stack.length) {
    const [node, d] = stack.pop();
    if (node.id === id) return d;
    if (!isDir(node)) continue;
    for (const child of node.children) stack.push([child, d + 1]);
  }
  return -1;
}

/* ---------- 文档序列化（编辑态持久化，见 docs/项目约定.md §P0-7） ---------- */

/**
 * 内存节点 → 可持久化节点（保留 id，只留数据字段，剔除折叠态等视图信息）。
 *
 * 4D-1：改为**显式栈迭代**（原为按 children 递归下潜，与 B-P3-5 同类缺陷 ——
 * 深链在 MAX_EDITOR_NODES（20000）下递归版会 RangeError）。语义不变：
 * 目录 children 保持源顺序，文件保留 content 原样。
 */
export function toDocumentNode(node) {
  const build = (n) => (isDir(n)
    ? { id: n.id, type: 'dir', name: n.name, note: normalizeNote(n.note), children: [] }
    : {
      id: n.id, type: 'file', name: n.name,
      note: normalizeNote(n.note), content: n.content || '',
    });
  const outRoot = build(node);
  if (!isDir(node)) return outRoot;
  const stack = [[node, outRoot]];
  while (stack.length) {
    const [src, out] = stack.pop();
    for (const child of src.children) {
      const childOut = build(child);
      out.children.push(childOut);
      if (isDir(child)) stack.push([child, childOut]);
    }
  }
  return outRoot;
}

/**
 * 可持久化节点 → 内存节点。结构非法即抛 Error，错误消息标明出错路径。
 *
 * 宽容处：id 缺失或非字符串时补发新 id（兼容早期文档）。
 * 恢复后仍须调用 reserveIds()，把补发之外的既有 id 一并登记。
 *
 * 4D-2：改为**显式栈迭代**。关键 —— 用「帧 + 游标」模拟原递归的**前序**下潜：
 * 建好 child[i] 后立即深入其子树，回来再取 child[i+1]。这样「多个节点同时非法时
 * 先抛哪一个」的错误顺序与原实现逐字一致（若改成一次性先把同层子节点全过一遍，
 * 就会改变该顺序）。宽容与校验语义均保持不变。
 */
export function fromDocumentNode(raw, path = '$') {
  const build = (r, p) => {
    if (!r || typeof r !== 'object' || Array.isArray(r)) {
      throw new Error(t('doc.nodeNotObject', { path: p }));
    }
    if (r.type !== 'dir' && r.type !== 'file') {
      throw new Error(t('doc.nodeBadType', { path: p }));
    }
    if (typeof r.name !== 'string' || !r.name) {
      throw new Error(t('doc.nodeBadName', { path: p }));
    }
    const id = (typeof r.id === 'string' && r.id) ? r.id : uid(r.type === 'dir' ? 'd' : 'f');
    if (r.type === 'dir') {
      const children = r.children === undefined ? [] : r.children;
      if (!Array.isArray(children)) {
        throw new Error(t('doc.nodeBadChildren', { path: p }));
      }
      return { id, type: 'dir', name: r.name, note: normalizeNote(r.note), children: [] };
    }
    return {
      id, type: 'file', name: r.name,
      note: normalizeNote(r.note),
      content: typeof r.content === 'string' ? r.content : '',
    };
  };
  const kidsOf = (r) => (r.children === undefined ? [] : r.children);

  const root = build(raw, path);
  if (root.type !== 'dir') return root;

  const stack = [{ src: raw, out: root, base: path, kids: kidsOf(raw), i: 0 }];
  while (stack.length) {
    const frame = stack[stack.length - 1];
    if (frame.i >= frame.kids.length) {
      stack.pop();
      continue;
    }
    const idx = frame.i;
    frame.i += 1;
    const childPath = `${frame.base}.children[${idx}]`;
    const child = build(frame.kids[idx], childPath);
    frame.out.children.push(child);
    if (child.type === 'dir') {
      stack.push({ src: frame.kids[idx], out: child, base: childPath,
        kids: kidsOf(frame.kids[idx]), i: 0 });
    }
  }
  return root;
}

/* ---------- 落盘载荷（供 /api/generate 使用） ---------- */

/**
 * 内存节点 → 后端/模板使用的纯对象结构：目录为 {}，文件为字符串内容。
 *
 * B-P3-4：对象字面量下**同层重名会「后者覆盖前者」**（静默丢一个节点）。
 * 正常流程已由 `validateSegment` / 服务端 `editorSiblingDuplicated` 拦住，不会到达；
 * 此处加**告警**把「本不该发生」的情形暴露出来（不抛错 —— 落盘契约不能因此中断）。
 */
export function toPlainTree(node) {
  if (!isDir(node)) {
    return { [node.name]: node.content || '' };
  }
  const out = {};
  if (node.children.length === 0) return out;
  for (const child of node.children) {
    if (Object.prototype.hasOwnProperty.call(out, child.name)) {
      console.warn('[QingMan] toPlainTree: duplicate sibling name overwritten:', child.name);
    }
    if (isDir(child)) {
      out[child.name] = toPlainTree(child);
    } else {
      out[child.name] = child.content || '';
    }
  }
  return out;
}

/** 把整棵根节点转成可提交的树对象（不含根自身名称）。 */
export function treePayload(root) {
  return isDir(root) ? toPlainTree(root) : {};
}

/* ---------- 模板载入（V0.0.11） ---------- */

/**
 * 模板的**嵌套字典**结构 → 内存节点树。
 *
 * 模板格式与编辑态文档格式**不同**：模板里「目录 = 对象、文件 = 内容字符串」，
 * 且没有 id / type 字段（`toPlainTree` 的输出即此形态）。因此载入模板必须走本函数，
 * 由前端按既有规则补发 id —— 后端不发明第二套 id 规则。
 *
 * @param {Object} nested 模板的 tree 字段
 * @param {string} rootName 根节点名称（取模板的 name）
 * @returns 目录节点（id 已由 createDir/createFile 分配）
 */
export function fromNestedTree(nested, rootName = '') {
  const root = createDir(rootName || 'root');
  const build = (node, parent) => {
    if (!node || typeof node !== 'object' || Array.isArray(node)) return;
    for (const [name, value] of Object.entries(node)) {
      // 对象 → 目录；其余（字符串 / 数字 / null）→ 文件，内容取其字符串形式
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        const dir = createDir(name);
        addChild(parent, dir);
        build(value, dir);
      } else {
        addChild(parent, createFile(name, value === null || value === undefined ? '' : String(value)));
      }
    }
  };
  build(nested, root);
  return root;
}

/* ---------- 模板说明提炼（V0.0.17） ---------- */

/**
 * 从根节点直接子层提炼模板说明 → 填入根 note（裁定：独立副本，不回写）。
 *
 * 查找顺序：**`说明文档.md`**（约定名，16/17 套模板含它）→ 兜底**首个 `*.md`**。
 * 命中即取其 content 填根 `note`（原 .md 文件**保留不动**，编辑 note 不回写）；
 * 根已有 note 时不覆盖 —— 模板说明只填「空白」。找不到返回 null。
 *
 * 纯函数（只改 node.note 字段，不碰 DOM），便于单测。
 */
export function adoptTemplateNote(root) {
  if (!isDir(root) || normalizeNote(root.note)) return null;
  const doc = root.children.find((c) => !isDir(c) && c.name === '说明文档.md')
    || root.children.find((c) => !isDir(c) && c.name.toLowerCase().endsWith('.md'));
  if (!doc) return null;
  root.note = doc.content || '';
  return doc.name;
}
