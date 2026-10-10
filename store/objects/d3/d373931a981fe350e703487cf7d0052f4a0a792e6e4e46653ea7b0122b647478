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
  t, AUTO_LOCALE, SUPPORTED_LOCALES, getLocalePreference, setLocale,
} from '../i18n/index.js';

/** 选项标签键：`auto` → `lang.auto`；`zh-CN` → `lang.zhCN`。 */
function labelOf(value) {
  return value === AUTO_LOCALE ? 'lang.auto' : `lang.${value.replace('-', '')}`;
}

export function createLangPicker(selectEl) {
  if (!selectEl) return;

  const fill = () => {
    const saved = getLocalePreference();
    selectEl.textContent = '';
    for (const value of [AUTO_LOCALE, ...SUPPORTED_LOCALES]) {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = t(labelOf(value));
      selectEl.appendChild(opt);
    }
    selectEl.value = saved;
  };

  fill();
  selectEl.addEventListener('change', () => setLocale(selectEl.value));

  // 语言切换后，选项**自身**的文案也要跟着变 —— applyStatic() 只处理
  // `data-i18n`，管不到这里动态生成的 <option>。
  document.addEventListener('qmlocalechange', fill);
}
