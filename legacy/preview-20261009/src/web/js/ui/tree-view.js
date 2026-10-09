/**
 * 青蔓 QingMan · 目录树视图
 * 只负责把数据模型渲染成 DOM 并回传交互事件，不改数据。
 */

import { isDir } from '../modules/tree-model.js';

export function createTreeView(container, { onSelect }) {
  /** 折叠状态只存在于视图层，不污染数据模型 */
  const collapsed = new Set();
  let currentRoot = null;

  function render(root, selectedId) {
    currentRoot = root;
    container.textContent = '';
    if (!root) return;
    container.appendChild(buildRow(root, selectedId));
  }

  function buildRow(node, selectedId) {
    const wrap = document.createElement('div');
    wrap.className = 'tree-node';

    const dir = isDir(node);
    const hasChildren = dir && node.children.length > 0;
    const isCollapsed = collapsed.has(node.id);

    const row = document.createElement('div');
    row.className = 'tree-row' + (node.id === selectedId ? ' is-selected' : '');
    row.dataset.id = node.id;
    row.setAttribute('role', 'treeitem');

    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle' + (hasChildren ? '' : ' is-leaf');
    toggle.textContent = hasChildren ? (isCollapsed ? '\u25B6' : '\u25BC') : '\u2022';
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!hasChildren) return;
      if (collapsed.has(node.id)) collapsed.delete(node.id);
      else collapsed.add(node.id);
      render(currentRoot, selectedId);
    });
    row.appendChild(toggle);

    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    icon.textContent = dir ? '\uD83D\uDCC1' : '\uD83D\uDCC4';
    row.appendChild(icon);

    const name = document.createElement('span');
    name.className = 'tree-name';
    name.textContent = node.name;
    row.appendChild(name);

    row.addEventListener('click', () => onSelect(node.id));
    wrap.appendChild(row);

    if (hasChildren) {
      const box = document.createElement('div');
      box.className = 'tree-children' + (isCollapsed ? ' is-collapsed' : '');
      for (const child of node.children) {
        box.appendChild(buildRow(child, selectedId));
      }
      wrap.appendChild(box);
    }
    return wrap;
  }

  function expandAll() {
    collapsed.clear();
  }

  function collapseAll(root) {
    collapsed.clear();
    walkDirs(root, (node) => {
      if (node.children.length > 0) collapsed.add(node.id);
    });
  }

  function walkDirs(node, visit) {
    if (!isDir(node)) return;
    visit(node);
    for (const child of node.children) walkDirs(child, visit);
  }

  return { render, expandAll, collapseAll };
}
