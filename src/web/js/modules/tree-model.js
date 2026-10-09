/**
 * 青蔓 QingMan · 目录树数据模型
 * 纯数据操作，不碰 DOM、不碰网络。
 *
 * 内存节点结构：{ id, type:'dir'|'file', name, children:[], content? }
 */

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

export function findNode(root, id) {
  if (!root) return null;
  if (root.id === id) return root;
  if (!isDir(root)) return null;
  for (const child of root.children) {
    const hit = findNode(child, id);
    if (hit) return hit;
  }
  return null;
}

export function findParent(root, id) {
  if (!root || !isDir(root)) return null;
  for (const child of root.children) {
    if (child.id === id) return root;
    const hit = findParent(child, id);
    if (hit) return hit;
  }
  return null;
}

export function addChild(parent, node) {
  if (!isDir(parent)) return false;
  parent.children.push(node);
  return true;
}

export function renameNode(root, id, name) {
  const node = findNode(root, id);
  if (!node || root.id === id) return false;
  node.name = name;
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

export function pathOf(root, id) {
  if (!root) return '';
  if (root.id === id) return root.name;
  if (!isDir(root)) return '';
  for (const child of root.children) {
    const sub = pathOf(child, id);
    if (sub) return `${root.name} / ${sub}`;
  }
  return '';
}

export function depthOf(root, id, depth = 0) {
  if (!root) return -1;
  if (root.id === id) return depth;
  if (!isDir(root)) return -1;
  for (const child of root.children) {
    const hit = depthOf(child, id, depth + 1);
    if (hit >= 0) return hit;
  }
  return -1;
}

/* ---------- 文档序列化（编辑态持久化，见 docs/项目约定.md §P0-7） ---------- */

/** 内存节点 → 可持久化节点（保留 id，只留数据字段，剔除折叠态等视图信息）。 */
export function toDocumentNode(node) {
  if (isDir(node)) {
    return {
      id: node.id,
      type: 'dir',
      name: node.name,
      children: node.children.map(toDocumentNode),
    };
  }
  return { id: node.id, type: 'file', name: node.name, content: node.content || '' };
}

/**
 * 可持久化节点 → 内存节点。结构非法即抛 Error，错误消息标明出错路径。
 *
 * 宽容处：id 缺失或非字符串时补发新 id（兼容早期文档）。
 * 恢复后仍须调用 reserveIds()，把补发之外的既有 id 一并登记。
 */
export function fromDocumentNode(raw, path = '$') {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error(`文档节点非法（${path}）：应为对象`);
  }
  if (raw.type !== 'dir' && raw.type !== 'file') {
    throw new Error(`文档节点非法（${path}）：type 必须为 dir 或 file`);
  }
  if (typeof raw.name !== 'string' || !raw.name) {
    throw new Error(`文档节点非法（${path}）：name 必须为非空字符串`);
  }
  const id = (typeof raw.id === 'string' && raw.id) ? raw.id : uid(raw.type === 'dir' ? 'd' : 'f');

  if (raw.type === 'dir') {
    const children = raw.children === undefined ? [] : raw.children;
    if (!Array.isArray(children)) {
      throw new Error(`文档节点非法（${path}.children）：应为数组`);
    }
    return {
      id,
      type: 'dir',
      name: raw.name,
      children: children.map((child, i) => fromDocumentNode(child, `${path}.children[${i}]`)),
    };
  }
  return {
    id,
    type: 'file',
    name: raw.name,
    content: typeof raw.content === 'string' ? raw.content : '',
  };
}

/* ---------- 落盘载荷（供 /api/generate 使用） ---------- */

/** 内存节点 → 后端/模板使用的纯对象结构：目录为 {}，文件为字符串内容。 */
export function toPlainTree(node) {
  if (!isDir(node)) {
    return { [node.name]: node.content || '' };
  }
  const out = {};
  if (node.children.length === 0) return out;
  for (const child of node.children) {
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
