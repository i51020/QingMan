/**
 * 青蔓 QingMan · 目录树视图
 * 只负责把数据模型渲染成 DOM 并回传交互事件，不改数据。
 * V0.0.19：节点拖拽移动（HTML5 DnD）+ 右键菜单（回调由 main.js 提供，逻辑同工具栏）。
 * V0.0.32：拖拽落点**预判**（C-P3-2）+ `dragleave` 不因划过子元素而摘高亮（C-P3-3）。
 */

import { isDir, isSelfOrDescendant } from '../modules/tree-model.js';
import { t } from '../i18n/index.js';

/**
 * 指针是否**真的离开了本行**（C-P3-3）。
 *
 * HTML5 DnD 的 `dragenter` / `dragleave` 是**逐元素**派发的：鼠标从行背景移到行内的
 * 子元素（`tree-toggle` / `tree-icon` / `tree-name`）时，本行同样会收到一条 `dragleave`。
 * 旧实现据此无条件摘掉 `is-drop-target` → 划过子元素时高亮闪烁。
 *
 * `relatedTarget` 就是「指针正进入的那个元素」，仍在本行内即视为没离开。
 * 个别实现不给 `relatedTarget`（为 `null`）→ 退回指针坐标判定
 * （`DragEvent` 继承 `MouseEvent`，坐标可用）。
 *
 * **导出以便单测**：本条判据承担「算不算离开」的判定职责，两种分支（有 / 无
 * `relatedTarget`）都要能独立验证；浏览器探针只能造出「有 relatedTarget」那一种。
 */
export function leftRow(row, event) {
  const related = event.relatedTarget;
  if (related) return !row.contains(related);
  const rect = row.getBoundingClientRect();
  return !(event.clientX >= rect.left && event.clientX <= rect.right
        && event.clientY >= rect.top && event.clientY <= rect.bottom);
}

export function createTreeView(container, { onSelect, onMove, onContext }) {
  /** 折叠状态只存在于视图层，不污染数据模型 */
  const collapsed = new Set();
  let currentRoot = null;
  /** 渲染时的选中 id 快照：拖拽/折叠等视图内重渲染时用它，避免闭包取旧值 */
  let currentSelectedId = null;
  /** 当前拖拽中的节点 id（dragover 时判定合法性用） */
  let draggingId = null;
  /** 当前拖拽中的**节点对象**：C-P3-2 预判「落点是否在被拖子树内」时用（见 dragover） */
  let draggingNode = null;

  function render(root, selectedId) {
    currentRoot = root;
    currentSelectedId = selectedId;
    /* C-P3-1：本函数是**全量重建**（编辑 / 折叠 / 选中任一操作都走到这里），
       清空容器会让滚动位置回到顶部。滚动条长在**父节点** `#treeWrap` 上
       （见 css/layout.css：`#treeWrap { overflow: auto }`），`container`（`#treeCanvas`）
       自身不滚动 —— 故在重建前后记录并还原滚动偏移，避免"改一下就跳回顶"。 */
    const scroller = container.parentElement || container;
    const keepTop = scroller.scrollTop;
    const keepLeft = scroller.scrollLeft;
    container.textContent = '';
    if (root) container.appendChild(buildRow(root, selectedId));
    scroller.scrollTop = keepTop;
    scroller.scrollLeft = keepLeft;
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
    /* V0.0.42：根节点名即「根文件夹名」，可为空 —— 空名渲染为「（不建根）」占位 */
    const isRootRow = !!currentRoot && node.id === currentRoot.id;
    if (isRootRow && !node.name) {
      name.textContent = t('tree.rootNoName');
      name.classList.add('is-placeholder');
    } else {
      name.textContent = node.name;
    }
    row.appendChild(name);

    row.addEventListener('click', () => onSelect(node.id));
    wrap.appendChild(row);

    /* ---------- 拖拽（V0.0.19）：根节点不可拖；目录可作落点 ---------- */
    row.addEventListener('dragstart', (event) => {
      draggingId = node.id;
      draggingNode = node;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/qm-node-id', node.id);
    });
    row.addEventListener('dragend', () => {
      draggingId = null;
      draggingNode = null;
      row.classList.remove('is-drop-target');
    });
    if (dir) {
      row.addEventListener('dragover', (event) => {
        /* C-P3-2：**预判**「拖进自身 / 自身子孙」。
           旧实现只挡了「自身」（仅比 id 是否相等），子孙落点照样
           `preventDefault()` 并亮起 `is-drop-target` —— 给出「可放下」的假暗示，
           直到 `drop` 才由模型层 `canMove` 判 `cycle` 报错。
           此处复用模型层的**同一权威** `isSelfOrDescendant`，不另立第二份防环规则
           （规则重复必然漂移，见《项目约定》§P2 第 28 项 A-P2-2 的同类裁决）。
           注：其余判定（同名冲突等）仍留给 drop 时的模型层，本项只收「自身 / 子孙」。 */
        if (!draggingNode || isSelfOrDescendant(draggingNode, node.id)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        row.classList.add('is-drop-target');
      });
      row.addEventListener('dragleave', (event) => {
        /* C-P3-3：划过行内子元素不算离开（判定见 leftRow） */
        if (leftRow(row, event)) row.classList.remove('is-drop-target');
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
