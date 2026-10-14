/**
 * 青蔓 QingMan · 属性面板
 * 只读展示当前选中节点信息（名称/类型/路径/深度/统计）；
 * note 说明可编辑（V0.0.17，纯文本 —— 工具不解析/渲染 Markdown）；
 * 名称 / 路径 / 说明 三粒度一键复制。
 *
 * 编辑流：输入 → onNoteChange（调用方入撤销栈 + markDirty）→ 重渲染。
 */

import {
  isDir, pathOf, depthOf, countTree, normalizeNote, findParent, toPlainTree,
} from '../modules/tree-model.js';
import { localizeError } from '../core/errors.js';
import { t } from '../i18n/index.js';

export function createInspector(refs) {
  /** 正在渲染的节点 id。渲染自身触发 input 事件时用它抑制回环。 */
  let renderingId = null;
  /** 当前选中节点 id。必须在 input 监听器**之前**声明 —— 监听器引用它（P3-8）。 */
  let currentId = null;
  /** 编辑中的 note 暂存：node 引用随 store 重渲染可能变化，以 id + 内容判定。 */
  let editing = { id: null, value: '' };

  refs.note.addEventListener('input', () => {
    if (renderingId !== null && refs.note.value === editing.value) return;
    editing = { id: currentId, value: refs.note.value };
    if (typeof refs.onNoteChange === 'function') {
      refs.onNoteChange(currentId, refs.note.value);
    }
  });

  return {
    render(root, selectedId, ids) {
      if (!root) {
        clear();
        return;
      }
      /* V0.0.43 · F × H：多选（≥2）时没有「那个节点」可描述，切到聚合口径。 */
      if (Array.isArray(ids) && ids.length >= 2) {
        renderMulti(root, ids);
        return;
      }
      if (!selectedId) {
        clear();
        return;
      }
      const node = findAny(root, selectedId);
      if (!node) {
        clear();
        return;
      }
      currentId = selectedId;
      const stats = isDir(node) ? countTree(node) : { dirs: 0, files: 0 };
      const depth = depthOf(root, selectedId);
      const note = normalizeNote(node.note);

      refs.name.textContent = node.name;
      refs.type.textContent = isDir(node) ? t('inspector.typeDir') : t('inspector.typeFile');
      refs.path.textContent = pathOf(root, selectedId) || node.name;
      refs.dirs.textContent = String(stats.dirs);
      refs.files.textContent = String(stats.files);
      refs.depth.textContent = depth >= 0 ? String(depth) : '—';
      /* 从聚合态切回来时必须还原占位提示（聚合态把它改成了「多选时不可编辑说明」） */
      refs.note.placeholder = t('inspector.notePlaceholder');

      // Render note: skip overwrite while the user is editing this very node
      // (avoids clobbering the caret mid-typing on store-driven re-renders).
      renderingId = selectedId;
      if (refs.note.value !== note && editing.id !== selectedId) {
        refs.note.value = note;
      }
      if (editing.id !== selectedId) editing = { id: selectedId, value: note };
      refs.note.disabled = false;
      renderingId = null;
    },

    showResult(result) {
      refs.result.textContent = JSON.stringify(result, null, 2);
    },

    /**
     * 「源码」视图内容（V0.0.43 · H 组）：把选中节点的**子树**序列化成与落盘同构的纯对象。
     *
     * 复用 `toPlainTree` —— 与 `/api/generate` 的 payload **同源**，因此这一栏显示的
     * 就是「按生成时这个节点会写成什么」，可用于生成前当场核验（H 组选该方案的理由）。
     * 多选时按「完整路径 → 子树」合并成一份对象，键即路径，读起来就是一张映射表。
     *
     * 视图归属：源码面板属于检视器自身，故渲染留在这里而不是 main.js ——
     * 主入口只管「何时重渲染」，不管「面板里写什么」。
     */
    renderSource(root, ids) {
      const host = refs.source;
      if (!host) return;
      if (!ids.length) {
        host.textContent = t('inspector.sourceEmpty');
        return;
      }
      if (ids.length === 1) {
        const node = findAny(root, ids[0]);
        host.textContent = node
          ? JSON.stringify(toPlainTree(node), null, 2)
          : t('inspector.sourceEmpty');
        return;
      }
      const merged = {};
      for (const id of ids) {
        const node = findAny(root, id);
        if (node) merged[pathOf(root, id) || node.name] = toPlainTree(node);
      }
      host.textContent = JSON.stringify(merged, null, 2);
    },

    showError(err) {
      refs.result.textContent = t('inspector.genFailed',
        { code: err.code || 'error', message: localizeError(err) });
    },

    /**
     * 作废「正在编辑」暂存（V0.0.20）。
     * render 为防打断光标会跳过覆盖 textarea —— 撤销/重做恢复了模型值后，
     * 必须显式清掉暂存，否则界面仍显示回退前的旧文本（模型与 UI 脱节）。
     */
    resetEditing() {
      editing = { id: null, value: '' };
    },
  };

  /**
   * 多选聚合态（V0.0.43 · F × H，需求草案 5.1 节）。
   *
   * 多选后若面板仍显示「最后点击的那个节点」，语义是错的 —— 改报**集合口径**：
   * 计数取各项合计、路径取公共父目录（跨父则明说「多个位置」）、深度无从定义故留 `—`、
   * note 无单一可编辑对象故**禁用**。选中集合本身的详表在「源码」视图（合并 JSON）。
   */
  function renderMulti(root, ids) {
    currentId = null;
    editing = { id: null, value: '' };
    let dirs = 0;
    let files = 0;
    for (const id of ids) {
      const node = findAny(root, id);
      if (!node) continue;
      if (isDir(node)) {
        const sub = countTree(node);
        dirs += sub.dirs;
        files += sub.files;
      } else {
        files += 1;
      }
    }
    refs.name.textContent = t('inspector.multiTitle', { n: ids.length });
    refs.type.textContent = t('inspector.multiType');
    refs.path.textContent = commonParentLabel(root, ids) || t('inspector.multiParents');
    refs.dirs.textContent = String(dirs);
    refs.files.textContent = String(files);
    refs.depth.textContent = '—';
    refs.note.value = '';
    refs.note.placeholder = t('inspector.multiNoteDisabled');
    refs.note.disabled = true;
  }

  /** 全部选中项的**公共父目录**标签；跨父返回空串（调用方据此显示「多个位置」）。 */
  function commonParentLabel(root, ids) {
    let shared = null;
    for (const id of ids) {
      const parent = findParent(root, id);
      if (!parent) return '';
      if (shared === null) shared = parent;
      else if (shared.id !== parent.id) return '';
    }
    if (!shared) return '';
    if (shared.id === root.id) return root.name || t('tree.rootNoName');
    return pathOf(root, shared.id) || shared.name;
  }

  function clear() {
    currentId = null;
    editing = { id: null, value: '' };
    refs.name.textContent = '—';
    refs.type.textContent = '—';
    refs.path.textContent = '—';
    refs.dirs.textContent = '0';
    refs.files.textContent = '0';
    refs.depth.textContent = '—';
    refs.note.value = '';
    refs.note.placeholder = t('inspector.notePlaceholder');
    refs.note.disabled = true;
  }
}

/** 复制文本到剪贴板：优先 Clipboard API（127.0.0.1 属安全上下文），失败降级 execCommand。 */
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (err2) {
      ok = false;
    }
    ta.remove();
    return ok;
  }
}

/** 按 id 找节点。显式栈（B-P3-5）：深树不撞引擎调用栈上限，语义同旧递归版。 */
function findAny(node, id) {
  if (!node) return null;
  const stack = [node];
  while (stack.length) {
    const n = stack.pop();
    if (n.id === id) return n;
    if (isDir(n)) for (const child of n.children) stack.push(child);
  }
  return null;
}
