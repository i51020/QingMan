/**
 * 青蔓 QingMan · 目录树视图
 * 只负责把数据模型渲染成 DOM 并回传交互事件，不改数据。
 * V0.0.19：节点拖拽移动（HTML5 DnD）+ 右键菜单（回调由 main.js 提供，逻辑同工具栏）。
 */

import { isDir } from '../modules/tree-model.js';

export function createTreeView(container, { onSelect, onMove, onContext }) {
  /** 折叠状态只存在于视图层，不污染数据模型 */
  const collapsed = new Set();
  let currentRoot = null;
  /** 渲染时的选中 id 快照：拖拽/折叠等视图内重渲染时用它，避免闭包取旧值 */
  let currentSelectedId = null;
  /** 当前拖拽中的节点 id（dragover 时判定合法性用） */
  let draggingId = null;

  function render(root, selectedId) {
    currentRoot = root;
    currentSelectedId = selectedId;
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
    row.draggable = node.id !== (currentRoot && currentRoot.id);

    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle' + (hasChildren ? '' : ' is-leaf');
    toggle.textContent = hasChildren ? (isCollapsed ? '\u25B6' : '\u25BC') : '\u2022';
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!hasChildren) return;
      if (collapsed.has(node.id)) collapsed.delete(node.id);
      else collapsed.add(node.id);
      render(currentRoot, currentSelectedId);
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

    /* ---------- 拖拽（V0.0.19）：根节点不可拖；目录可作落点 ---------- */
    row.addEventListener('dragstart', (event) => {
      draggingId = node.id;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/qm-node-id', node.id);
    });
    row.addEventListener('dragend', () => {
      draggingId = null;
      row.classList.remove('is-drop-target');
    });
    if (dir) {
      row.addEventListener('dragover', (event) => {
        // 自拖自（含拖进自己的子孙）一律不给放下提示；合法性细判在 drop 时由模型层拦截
        if (draggingId && draggingId !== node.id) {
          event.preventDefault();
          event.dataTransfer.dropEffect = 'move';
          row.classList.add('is-drop-target');
        }
      });
      row.addEventListener('dragleave', () => {
        row.classList.remove('is-drop-target');
      });
      row.addEventListener('drop', (event) => {
        event.preventDefault();
        row.classList.remove('is-drop-target');
        const id = draggingId || event.dataTransfer.getData('text/qm-node-id');
        draggingId = null;
        if (id && id !== node.id && typeof onMove === 'function') {
          onMove(id, node.id);
        }
      });
    }

    /* ---------- 右键菜单（V0.0.19）：选中并弹菜单，菜单项逻辑同工具栏 ---------- */
    row.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      if (typeof onContext === 'function') {
        onContext(node.id, event.clientX, event.clientY);
      }
    });

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
