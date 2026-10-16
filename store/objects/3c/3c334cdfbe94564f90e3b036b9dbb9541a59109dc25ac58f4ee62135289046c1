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

export function createTreeView(container, { onSelect, onMove, onContext, onFold }) {
  /** 折叠状态只存在于视图层，不污染数据模型 */
  const collapsed = new Set();
  let currentRoot = null;
  /** 渲染时的选中 id 快照：拖拽/折叠等视图内重渲染时用它，避免闭包取旧值 */
  let currentSelectedId = null;
  /** 渲染时的**多选集合**快照（V0.0.43 · F 组）：同上，供视图内重渲染复用 */
  let currentSelectedIds = [];
  /** 当前拖拽中的节点 id（dragover 时判定合法性用） */
  let draggingId = null;
  /** 当前拖拽中的**节点对象**：C-P3-2 预判「落点是否在被拖子树内」时用（见 dragover） */
  let draggingNode = null;

  function render(root, selectedId, selectedIds) {
    currentRoot = root;
    currentSelectedId = selectedId;
    currentSelectedIds = Array.isArray(selectedIds) ? selectedIds : [];
    /* C-P3-1：本函数是**全量重建**（编辑 / 折叠 / 选中任一操作都走到这里），
       清空容器会让滚动位置回到顶部。滚动条长在**父节点** `#treeWrap` 上
       （见 css/layout.css：`#treeWrap { overflow: auto }`），`container`（`#treeCanvas`）
       自身不滚动 —— 故在重建前后记录并还原滚动偏移，避免"改一下就跳回顶"。 */
    const scroller = container.parentElement || container;
    const keepTop = scroller.scrollTop;
    const keepLeft = scroller.scrollLeft;
    container.textContent = '';
    if (root) container.appendChild(buildRow(root, selectedId, currentSelectedIds));
    scroller.scrollTop = keepTop;
    scroller.scrollLeft = keepLeft;
  }

  function buildRow(node, selectedId, selectedIds) {
    const wrap = document.createElement('div');
    wrap.className = 'tree-node';

    const dir = isDir(node);
    const hasChildren = dir && node.children.length > 0;
    const isCollapsed = collapsed.has(node.id);

    const row = document.createElement('div');
    const isSelected = node.id === selectedId;
    const isMulti = selectedIds.includes(node.id);
    row.className = 'tree-row' + (isSelected ? ' is-selected' : '') + (isMulti ? ' is-multi' : '');
    row.dataset.id = node.id;
    row.setAttribute('role', 'treeitem');
    /* aria-selected 是 role="treeitem" 的选择语义；单选与多选都算「选中」 */
    row.setAttribute('aria-selected', isSelected || isMulti ? 'true' : 'false');
    row.draggable = node.id !== (currentRoot && currentRoot.id);

    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle' + (hasChildren ? '' : ' is-leaf');
    toggle.textContent = hasChildren ? (isCollapsed ? '\u25B6' : '\u25BC') : '\u2022';
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!hasChildren) return;
      if (collapsed.has(node.id)) collapsed.delete(node.id);
      else collapsed.add(node.id);
      render(currentRoot, currentSelectedId, currentSelectedIds);
      /* V0.0.51@r3 · 第 6 条：这条路径的重渲染只发生在视图层内部，外部无从得知折叠态变了。
         通知一声，让「展开 / 折叠」切换按钮的图标与提示跟上（回调是可选参数，不传即静默）。 */
      if (typeof onFold === 'function') onFold();
    });
    row.appendChild(toggle);

    const icon = document.createElement('span');
    /* V0.0.52：树行图标由 emoji（📁 / 📄）归一为 `.ic` mask —— 与全项目图标同一套
       （§P0-3 L8）。emoji 是**彩色字形**、不吃 `color`，换肤时树行图标不随配色；
       mask 走 `.ic` 基类的 `background-color: currentColor`，16 款皮肤自动跟随。
       尺寸用**既有**修饰符 `.ic-sm`（14px），不新造尺寸词汇。
       ⚠ 两个形状名**各写成一条独立字面量**，不要合并为三元表达式：
         `verify` 7aj ① 是从「类名声明形态」的**字面量**里抽「定义 ↔ 使用」配对的，
         写成 `classList.add(dir ? 'ic-folder' : 'ic-file')` 会让两枚形状都抽不到，
         于是当场误报「base.css 定义了 .ic-folder 但无人使用」（本批预防性记此坑）。 */
    icon.className = 'ic ic-sm tree-icon';
    if (dir) icon.classList.add('ic-folder');
    else icon.classList.add('ic-file');
    icon.setAttribute('aria-hidden', 'true');
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

    /* V0.0.43 · F 组：把事件一并回传 —— 调用方据 ctrl/meta/shift 修饰键决定
       「离散多选 / 范围选择 / 单选」。视图层不自己解释修饰键（那属于选择模型）。 */
    row.addEventListener('click', (event) => onSelect(node.id, event));
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
        box.appendChild(buildRow(child, selectedId, selectedIds));
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

  /**
   * 折叠态统计（V0.0.51@r3 · 第 6 条「展开 / 折叠」合一按钮的唯一判据）。
   *
   * - `expandable` ＝ 全树**带子节点的目录**数（折叠动作作用的对象）；
   * - `collapsed`  ＝ 其中**当前处于折叠态**的个数。
   *
   * 两个数都**现算**（折叠集合 ∩ 现存目录），而不是直接读 `collapsed.size`：
   * 折叠集合是视图层私有 `Set`，删掉一个折叠着的节点后它的 id 仍留在集合里 ——
   * 直接读 size 会让按钮在树已全部展开时仍显示「还有收起的」，且再也回不到
   * 「全部折叠」（点了也清不掉的幽灵计数）。故此处以**模型为准**反过来筛集合。
   */
  function foldStats(root) {
    let expandable = 0;
    let folded = 0;
    walkDirs(root, (node) => {
      if (node.children.length === 0) return;
      expandable += 1;
      if (collapsed.has(node.id)) folded += 1;
    });
    return { expandable, collapsed: folded };
  }

  /**
   * 当前**可视行**的 id 序列（V0.0.43 · F 组）。
   *
   * Shift 范围选择要「从锚点到当前节点」——折叠的子树不在序列里，语义即
   * 「只计看得见的行」（需求草案 2.6 节的裁定）。直接读 DOM 而非遍历模型，
   * 是因为「哪一行可见」正是渲染的产物，模型侧无从得知折叠态（视图层私有）。
   */
  function visibleIds() {
    return Array.prototype.map.call(
      container.querySelectorAll('.tree-row'), (row) => row.dataset.id);
  }

  return { render, expandAll, collapseAll, foldStats, visibleIds };
}
