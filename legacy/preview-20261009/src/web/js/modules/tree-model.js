/**
 * 青蔓 QingMan · 目录树数据模型
 * 纯数据操作，不碰 DOM、不碰网络。
 * 内存节点结构：{ id, type:'dir'|'file', name, children:[], content? }
 */

let counter = 0;

export function uid(prefix = 'n') {
  counter += 1;
  return `${prefix}${Date.now().toString(36)}${counter.toString(36)}`;
}

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
