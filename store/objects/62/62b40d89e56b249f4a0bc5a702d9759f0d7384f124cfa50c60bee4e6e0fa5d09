/**
 * 青蔓 QingMan · 历史版本（备份取回 · V0.0.51@r9）
 *
 * 后端**早就**每次保存前把当前版轮转留档（`data/.bak/`，见 `_backup_editor`），
 * 代码注释也写明动机「用户一次误操作 + 一次保存，上一版就永久消失」——
 * 但出口一直没做：没有端点、没有界面，用户只能自己开资源管理器、认出 17 位时间戳
 * 文件名、改名覆盖 `editor.json`。对零基础用户等于没有。本模块就是那个出口。
 *
 * 与 `modules/` 的分工：本模块只做「读列表 + 请求恢复 + 把结果交回调用方」，
 * **恢复成功后如何把内容装回编辑器由 main.js 决定**（它才持有 `store` / `pushHistory`）。
 *
 * 二次确认沿用模板库既有范式（`window.confirm` + 取词），不新造确认弹层。
 * 文案一律经 `t(key)`（§P0-3 L1），本文件不直写任何用户可见文案。
 */

import { api } from '../core/api.js';
import { localizeError } from '../core/errors.js';
import { t } from '../i18n/index.js';
import { toast } from './toast.js';

/** 与 main.js / templates.js 同款取元素助手（各自持有 1 行，不为一个 1 行函数再拆模块）。 */
const el = (id) => document.getElementById(id);

/** 字节 → 人类可读。单位串走取词表，不在此直写。 */
function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '';
  if (bytes < 1024) return t('backups.sizeB', { n: bytes });
  if (bytes < 1024 * 1024) return t('backups.sizeK', { n: Math.max(1, Math.round(bytes / 1024)) });
  return t('backups.sizeM', { n: (bytes / 1024 / 1024).toFixed(1) });
}

/**
 * 留档时间 → `2026-10-15 23:56`。
 * 优先用文档里的 `savedAt`（残缺时）再回落到**文件名里的戳** —— 后者恒在，
 * 故即便某份文件内容损坏、读不出 `savedAt`，时间列也总有值可显示。
 */
function formatStamp(savedAt, name) {
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/.exec(String(savedAt || ''));
  if (m) return `${m[1]} ${m[2]}`;
  const n = /editor-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/.exec(String(name || ''));
  return n ? `${n[1]}-${n[2]}-${n[3]} ${n[4]}:${n[5]}` : '';
}

/**
 * @param {object} ctx 由 main.js 装配：
 *   `onRestored` —— 恢复成功后的回调（把恢复出来的文档装回编辑器）。
 */
export function createBackups({ onRestored }) {
  /** 最近一次列表响应。切语言后据此**重渲染**动态文案，不重复请求。 */
  let last = null;

  /** 列表占位/提示行（空列表、读取中、读取失败三态共用）。 */
  function note(text) {
    const li = document.createElement('li');
    li.className = 'bak-empty';
    li.textContent = text;
    return li;
  }

  function row(item) {
    const li = document.createElement('li');
    li.className = 'bak-item' + (item.broken ? ' is-broken' : '');
    li.dataset.id = item.id;

    const meta = document.createElement('div');
    meta.className = 'bak-meta';
    const time = document.createElement('b');
    time.textContent = formatStamp(item.savedAt, item.name) || item.name;
    const root = document.createElement('span');
    root.textContent = item.rootName || t('backups.noRoot');
    meta.append(time, root);
    if (item.archived) {
      const tag = document.createElement('span');
      tag.className = 'bak-tag';
      tag.textContent = t('backups.archived');
      meta.append(tag);
    }

    const right = document.createElement('div');
    right.className = 'bak-right';
    const size = document.createElement('span');
    size.className = 'bak-size';
    size.textContent = item.broken ? t('backups.broken') : formatSize(item.bytes);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-mini';
    btn.textContent = t('backups.restore');
    /* 损坏件**仍列出** —— 用户得知道它存在；但不可恢复（后端也会以
       editorBackupCorrupt 单独挡下），故按钮置灰而非隐藏。 */
    btn.disabled = !!item.broken;
    btn.addEventListener('click', () => restore(item));

    right.append(size, btn);
    li.append(meta, right);
    return li;
  }

  function render() {
    const list = el('bakList');
    if (!list) return;
    list.replaceChildren();
    const items = (last && last.backups) || [];
    if (!items.length) {
      list.append(note(t('backups.empty')));
      return;
    }
    for (const item of items) list.append(row(item));
  }

  async function load() {
    const list = el('bakList');
    if (list) list.replaceChildren(note(t('backups.loading')));
    try {
      last = await api.listEditorBackups();
    } catch (err) {
      last = null;
      if (list) list.replaceChildren(note(t('backups.loadFail', { message: localizeError(err) })));
      return;
    }
    render();
  }

  async function restore(item) {
    const when = formatStamp(item.savedAt, item.name) || item.name;
    const root = item.rootName || t('backups.noRoot');
    const msg = `${t('backups.confirmTitle')}\n\n${t('backups.confirmBody', { time: when, root })}`;
    if (!window.confirm(msg)) return;
    try {
      const res = await api.restoreEditor(item.id);
      const info = (res && res.restored) || {};
      toast(t('backups.restored', { root: info.rootName || root }), 'info', 6000);
      await onRestored();                 // 装回编辑器（含历史入栈，可撤销）
    } catch (err) {
      toast(t('backups.restoreFail', { message: localizeError(err) }), 'warn', 8000);
    }
  }

  return {
    /** 打开弹窗前调用：拉取列表并渲染。 */
    open() { load(); },
    /** 语言切换后重渲染动态文案（时间/大小/徽标随语言变，路径与文件名不变）。 */
    render,
  };
}
