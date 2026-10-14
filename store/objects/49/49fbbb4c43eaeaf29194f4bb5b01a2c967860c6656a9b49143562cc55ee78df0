/**
 * 青蔓 QingMan · 语言下拉
 *
 * 三档：**跟随系统 / 简体中文 / English**。
 * 「跟随系统」必须是**显式可见的一档** —— 若只在「没设过」时隐式跟随，
 * 用户手动选过一次之后就再也回不到自动跟随了。
 *
 * 主界面与帮助页是两个独立页面，各自调用本模块即可获得一致行为。
 * 文案一律经取词表（§P0-3 L1）。
 */

import {
  t, AUTO_LOCALE, supportedLocales, localeName, getLocalePreference, setLocale,
} from '../i18n/index.js';

/**
 * 选项标签：`auto` 是取词键（要翻译）；其余取语言包**自带的自描述名**（母语写法，不翻译）。
 * 上一版把标签写成 `lang.<code>` 硬编码两语，新增语言包里没有对应键 → 只能回显键名。
 */
function labelOf(value) {
  return value === AUTO_LOCALE ? t('lang.auto') : localeName(value);
}

export function createLangPicker(selectEl) {
  if (!selectEl) return;

  const fill = () => {
    const saved = getLocalePreference();
    selectEl.textContent = '';
    for (const value of [AUTO_LOCALE, ...supportedLocales()]) {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = labelOf(value);
      selectEl.appendChild(opt);
    }
    selectEl.value = saved;
  };

  fill();
  selectEl.addEventListener('change', () => { void setLocale(selectEl.value); });

  // 语言切换后，选项**自身**的文案也要跟着变 —— applyStatic() 只处理
  // `data-i18n`，管不到这里动态生成的 <option>。
  document.addEventListener('qmlocalechange', fill);
}

/**
 * 顶栏语言浮层（V0.0.40）—— 与上面的 `<select>` 版本**同源同档**，
 * 只是渲染成 `#popLang` 里的 `menu-item`（`role="menuitemradio"`）。
 *
 * 为什么保留两份：帮助页 / 支持页仍是独立页面、仍用 `<select>`；
 * 主界面按设计稿改为图标按钮 + 浮层。两者共用 `supportedLocales()` 与
 * `setLocale`，故不会出现「两个入口能选的档不一致」。
 *
 * 「跟随系统」同样是**显式可见的一档**（与 select 版一致）。
 */
export function createLangMenu(menuEl) {
  if (!menuEl) return null;

  const options = () => [AUTO_LOCALE, ...supportedLocales()];
  const items = new Map();

  function sync() {
    const saved = getLocalePreference();
    for (const [value, node] of items) {
      node.setAttribute('aria-checked', value === saved ? 'true' : 'false');
    }
  }

  function build() {
    menuEl.textContent = '';
    items.clear();
    for (const value of options()) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'menu-item';
      btn.setAttribute('role', 'menuitemradio');
      btn.dataset.locale = value;
      const check = document.createElement('span');
      check.className = 'ic ic-sm ic-check';
      check.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.textContent = labelOf(value);
      btn.append(check, text);
      // 切换会经 `qmlocalechange` 触发 build() 重建菜单（选中态随之复位）；
      // 加载失败则不重建，选中态保持原样 —— 正是失败时应有的表现。
      btn.addEventListener('click', () => { void setLocale(value); });
      menuEl.appendChild(btn);
      items.set(value, btn);
    }
    sync();
  }

  build();
  // 文案是取词键（lang.auto / lang.zhCN / lang.enUS）→ 换语言须重建。
  // 与 select 版同构；重建同时完成 aria-checked 复位。
  document.addEventListener('qmlocalechange', build);

  return { sync };
}

