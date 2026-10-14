/**
 * 青蔓 QingMan · 选择集合的语义运算（V0.0.43 · UI 定版差集 F 组）
 *
 * 纯函数：只吃 `(root, ids)`，不碰 store、不碰 DOM、不碰网络 —— 故可独立单测。
 * 选择**状态**仍住在 store（`selectedId` 锚点 + `selectedIds` 集合），这里只负责
 * 「集合怎么算」：净化、判定、去重、批量移动预检。
 *
 * 之所以独立成模块：主入口 main.js 已逼近单文件体积上限（§P2 第 4 项 64K），
 * 而这几条规则彼此内聚、与主流程零耦合 —— 拆出来既解体积，也让规则可单测。
 *
 * 边界约定（需求草案 `docs/UI定版差集_需求草案_20261014.md`）：
 *   - **根节点永不参与多选**（不可删、不可移），但**可以**被单选（改名入口在那儿）；
 *   - 多选集合 **≥2 项才成立**，不剩一项时按业界标准塌回单选；
 *   - 父子同选时**只保留最外层祖先**（2.4 节 #1）。
 */

import { findNode, findParent, isDir, isSelfOrDescendant } from './tree-model.js';

/**
 * 剔除已失效 / 根节点的 id。
 *
 * 撤销、载入模板、恢复文档都会把树换成另一棵 —— 原集合可能指向已不存在的节点。
 * 每次渲染前必须过一遍，否则「已选 3 项」里混着幽灵，批量删除会算错数量。
 */
export function liveIds(root, ids) {
  if (!root || !Array.isArray(ids)) return [];
  return ids.filter((id) => id !== root.id && !!findNode(root, id));
}

/** 当前**生效**的多选集合：已净化且 ≥2 项才成立，否则空数组（= 无多选）。 */
export function multiSel(root, ids) {
  const live = liveIds(root, ids);
  return live.length >= 2 ? live : [];
}

/** 全树 id（不含根）。Ctrl+A 用；显式栈，深树不撞调用栈（同 tree-model 的约定）。 */
export function allNodeIds(root) {
  const out = [];
  const stack = isDir(root) ? [...root.children] : [];
  while (stack.length) {
    const node = stack.pop();
    out.push(node.id);
    if (isDir(node)) for (const child of node.children) stack.push(child);
  }
  return out;
}

/**
 * 只保留「最外层祖先」。
 *
 * 父子同选时子被父**覆盖** —— 若逐个执行删除/移动，子会被操作两次
 * （父先被摘走，子已随之离开树），且「选中 N 项」与实际数量对不上。
 */
export function outermostIds(root, ids) {
  const set = new Set(ids);
  return ids.filter((id) => {
    for (let p = findParent(root, id); p; p = findParent(root, p.id)) {
      if (set.has(p.id)) return false;
    }
    return true;
  });
}

/**
 * 批量移动的预检（须在入撤销栈**之前**跑完，快照才是改动前的状态）。
 *
 * 三类整体拒绝：目标不是目录 / 目标落在任一被移动节点的子树内（成环）/
 * 目标处已有同名 —— 判同名时排除「本次也要移走的那些」，否则自己与自己判冲突。
 * 与单节点移动共用同一套原因码，取词不另起一套。
 *
 * @returns {{ok: true} | {ok: false, code: string, name: string}}
 */
export function canBatchMove(root, ids, targetDirId) {
  const target = findNode(root, targetDirId);
  if (!target || !isDir(target)) return { ok: false, code: 'notDir', name: '' };
  for (const id of ids) {
    const node = findNode(root, id);
    if (!node) return { ok: false, code: 'missing', name: '' };
    if (isSelfOrDescendant(node, targetDirId)) return { ok: false, code: 'cycle', name: node.name };
  }
  const moving = new Set(ids);
  const names = new Set();
  for (const child of target.children) {
    if (!moving.has(child.id)) names.add(String(child.name || '').trim().toLowerCase());
  }
  for (const id of ids) {
    const node = findNode(root, id);
    const key = String(node.name || '').trim().toLowerCase();
    if (names.has(key)) return { ok: false, code: 'exists', name: node.name };
    names.add(key);
  }
  return { ok: true };
}
