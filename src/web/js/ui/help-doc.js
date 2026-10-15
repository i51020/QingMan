/**
 * 青蔓 QingMan · 帮助弹窗正文（V0.0.40）
 *
 * 应用内帮助弹窗（`#dlgHelp`）的正文与目录渲染器。
 * 数据源与帮助页**同一份**（`i18n/index.js` 的 `getHelpSections()` → 当前语言包）—— 版式不同，
 * 但只要分节清单是同一个数组，两处内容就不可能漂移（这是本模块存在的唯一理由）。
 *
 * 版式差异（与 help.js 的页面版）：
 *   - 页面：分节是**卡片**（.help-section），导航在独立窄栏；
 *   - 弹窗：分节是**扁平分节**（.help-sec），目录与正文左右两栏（.help-2col）。
 *   - 「支持」一行在页面是**新标签链接**，在弹窗是**按钮**（切到支持弹窗，不再开页）。
 *
 * 文案一律经 `t(key)`（§P0-3 L1）。
 */

import { t, getHelpSections } from '../i18n/index.js';

/**
 * @param {HTMLElement} tocEl 目录容器（`.help-toc`）
 * @param {HTMLElement} docEl 正文容器（`.help-doc`）
 * @param {{onSupport?: Function}} [opts] onSupport 由「支持」一行按钮触发
 */
export function createHelpDoc(tocEl, docEl, opts = {}) {
  if (!tocEl || !docEl) return null;

  /** 动态字段：version / tplDir 为空表示尚未拿到后端实测值。 */
  const state = { version: '', backendOk: false, tplDir: '', tplDirBuiltin: false };

  function buildList(section) {
    const list = document.createElement(section.kind === 'ol' ? 'ol' : 'ul');
    for (const key of section.items) {
      const li = document.createElement('li');
      li.textContent = t(key);
      list.appendChild(li);
    }
    return list;
  }

  /** 「模板库位置」一行的文案：未读到 → 说明句；读到 → 实测目录（内置层加后缀）。 */
  function tplDirText() {
    if (!state.tplDir) return t('about.tplDirUnknown');
    return state.tplDir + (state.tplDirBuiltin ? t('about.tplDirBuiltin') : '');
  }

  function buildAbout(section) {
    const table = document.createElement('table');
    table.className = 'help-table';
    const version = state.version || t('help.versionFallback');
    const rows = [
      { label: 'about.app', value: `${t('app.nameZh')} ${t('app.nameEn')}` },
      { label: 'about.version', value: state.backendOk ? version : `${version} ${t('help.versionStale')}` },
      { label: 'about.backend', value: state.backendOk ? t('about.backendOn') : t('about.backendOff') },
      // V0.0.51@r6：模板库位置（后端实测值，随绑定变化）—— 与帮助页版同一取词键。
      { label: 'about.tplDir', value: tplDirText() },
      { label: 'help.support.title', action: true },
    ];
    for (const row of rows) {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.textContent = t(row.label);
      const td = document.createElement('td');
      if (row.action) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-ghost btn-mini';
        btn.textContent = t('help.support.goto');
        btn.addEventListener('click', () => {
          if (typeof opts.onSupport === 'function') opts.onSupport(btn);
        });
        td.appendChild(btn);
      } else {
        td.textContent = row.value;
      }
      tr.append(th, td);
      table.appendChild(tr);
    }
    if (!section.note) return table;
    const wrap = document.createElement('div');
    wrap.className = 'help-about';
    wrap.appendChild(table);
    const note = document.createElement('p');
    note.className = 'help-about-note';
    note.textContent = t(section.note);
    wrap.appendChild(note);
    return wrap;
  }

  /**
   * 快捷键表（kind: 'kbd'）：左列键帽、右列说明，逐行对齐。
   *
   * 数据约定与帮助页 `help.js` 的 buildKbd **完全一致**（同一份 helpSections，
   * 两处版式不同但结构同源）：
   *   - 说明文案 = `t(item)`；键位文案 = `t(item + '.keys')`；
   *   - 键位串内 `|` 分隔**等价**键位（渲染为多个键帽，以 help.kbd.or 相连）；
   *     `/` 表示同一按键的平台差异（Ctrl 或 Cmd），原样留在同一个键帽里。
   */
  function buildKbd(section) {
    const table = document.createElement('table');
    table.className = 'help-kbd';
    for (const item of section.items) {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      const keys = t(item + '.keys').split('|').map((s) => s.trim()).filter(Boolean);
      keys.forEach((key, i) => {
        if (i) {
          const or = document.createElement('span');
          or.className = 'help-kbd-or';
          or.textContent = t('help.kbd.or');
          th.appendChild(or);
        }
        const kbd = document.createElement('kbd');
        kbd.textContent = key;
        th.appendChild(kbd);
      });
      const td = document.createElement('td');
      td.textContent = t(item);
      tr.append(th, td);
      table.appendChild(tr);
    }
    const wrap = document.createElement('div');
    wrap.className = 'help-kbd-wrap';
    wrap.appendChild(table);
    if (section.note) {
      const note = document.createElement('p');
      note.className = 'help-kbd-note';
      note.textContent = t(section.note);
      wrap.appendChild(note);
    }
    return wrap;
  }

  function buildSection(section) {
    const wrap = document.createElement('section');
    wrap.className = 'help-sec';
    wrap.id = `dlg-h-${section.id}`;
    const title = document.createElement('h4');
    title.textContent = t(section.title);
    wrap.appendChild(title);
    let body;
    if (section.kind === 'about') body = buildAbout(section);
    else if (section.kind === 'kbd') body = buildKbd(section);
    else body = buildList(section);
    wrap.appendChild(body);
    return wrap;
  }

  /** 幂等：语言切换会再次调用，先清空再重建（同 help.js / support.js 的既有约定）。 */
  function render() {
    docEl.textContent = '';
    tocEl.textContent = '';
    for (const section of getHelpSections()) {
      docEl.appendChild(buildSection(section));
      const link = document.createElement('a');
      link.href = `#dlg-h-${section.id}`;
      link.textContent = t(section.title);
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const target = docEl.querySelector(`#dlg-h-${section.id}`);
        if (target) target.scrollIntoView({ block: 'start' });
      });
      tocEl.appendChild(link);
    }
  }

  /** 后端实测值回来后覆盖（版本号 / 连接状态）。 */
  function setStatus(next) {
    state.version = (next && next.version) || '';
    state.backendOk = Boolean(next && next.backendOk);
    state.tplDir = (next && next.tplDir) || '';
    state.tplDirBuiltin = Boolean(next && next.tplDirBuiltin);
    render();
  }

  render();
  document.addEventListener('qmlocalechange', render);
  return { render, setStatus };
}
