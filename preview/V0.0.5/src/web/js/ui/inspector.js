/**
 * 青蔓 QingMan · 属性面板
 * 只读展示当前选中节点信息，不做任何编辑（编辑入口在后续版本接入）。
 */

import { isDir, pathOf, depthOf, countTree } from '../modules/tree-model.js';
import { t } from '../i18n/index.js';

export function createInspector(refs) {
  return {
    render(root, selectedId) {
      if (!root || !selectedId) {
        clear();
        return;
      }
      const node = findAny(root, selectedId);
      if (!node) {
        clear();
        return;
      }
      const stats = isDir(node) ? countTree(node) : { dirs: 0, files: 0 };
      const depth = depthOf(root, selectedId);

      refs.name.textContent = node.name;
      refs.type.textContent = isDir(node) ? t('inspector.typeDir') : t('inspector.typeFile');
      refs.path.textContent = pathOf(root, selectedId) || node.name;
      refs.dirs.textContent = String(stats.dirs);
      refs.files.textContent = String(stats.files);
      refs.depth.textContent = depth >= 0 ? String(depth) : '—';
    },

    showResult(result) {
      refs.result.textContent = JSON.stringify(result, null, 2);
    },

    showError(err) {
      refs.result.textContent = t('inspector.genFailed',
        { code: err.code || 'error', message: err.message });
    },
  };

  function clear() {
    refs.name.textContent = '—';
    refs.type.textContent = '—';
    refs.path.textContent = '—';
    refs.dirs.textContent = '0';
    refs.files.textContent = '0';
    refs.depth.textContent = '—';
  }
}

function findAny(node, id) {
  if (!node) return null;
  if (node.id === id) return node;
  if (!isDir(node)) return null;
  for (const child of node.children) {
    const hit = findAny(child, id);
    if (hit) return hit;
  }
  return null;
}
