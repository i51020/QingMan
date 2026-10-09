/**
 * 青蔓 QingMan · 取词与偏好运行时（§P0-3 L1–L3 · L6）
 *
 * 单一取词入口：**所有面向用户可见的文案都必须经 `t(key)` 取得**，
 * UI 模块一律不得直写文案（由 `tools/verify.py` 的静态检查把关）。
 *
 * 语言与皮肤分别持久化在 localStorage 的 `qm.lang` / `qm.skin`（§P0-3 L6）。
 * 本模块的 DOM / localStorage 访问全部发生在函数内部 —— 顶层导入是安全的，
 * 因此纯逻辑模块（如 modules/tree-model.js）也可以取词。
 */

import { dict as zhCN } from './zh-CN.js';

/** 语言代码 → 字典。日后新增 `en-US.js` 并在此登记即可切换（§P0-3 L3）。 */
const DICTIONARIES = { 'zh-CN': zhCN };

export const DEFAULT_LOCALE = 'zh-CN';
export const LOCALE_KEY = 'qm.lang';
export const SKIN_KEY = 'qm.skin';

let locale = DEFAULT_LOCALE;
let dict = DICTIONARIES[locale];

/* ---------- 偏好存取 ---------- */

/** localStorage 在隐私模式 / 沙箱 iframe 下可能抛错，一律降级为「本会话内生效」。 */
function readPref(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (err) {
    return null;
  }
}

function writePref(key, value) {
  try {
    if (value === null || value === undefined || value === '') {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, String(value));
    }
  } catch (err) {
    /* 存储不可用：偏好只在本次会话内有效，不阻断任何功能 */
  }
}

/* ---------- 取词 ---------- */

export function getLocale() {
  return locale;
}

/** 切换语言。未登记的语种返回 false，不做任何改动。 */
export function setLocale(next) {
  if (!DICTIONARIES[next]) return false;
  locale = next;
  dict = DICTIONARIES[next];
  writePref(LOCALE_KEY, next);
  if (typeof document !== 'undefined') document.documentElement.lang = next;
  return true;
}

/** 该键是否已有译文。 */
export function has(key) {
  return Object.prototype.hasOwnProperty.call(dict, key);
}

/**
 * 取词。支持 `{name}` 占位替换（缺失的占位原样保留）。
 * 未命中的键**回显键名并告警** —— 便于一眼看出漏翻，而不是渲染成空白。
 */
export function t(key, vars) {
  const value = dict[key];
  if (value === undefined) {
    console.warn('[i18n] missing key:', key, '(', locale, ')');
    return String(key);
  }
  if (!vars) return value;
  return value.replace(/\{(\w+)\}/g, (whole, name) =>
    (Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : whole));
}

/** 静态文案填充：`data-i18n` 填文本，另三个变体填对应属性。 */
export function applyStatic(root) {
  const scope = root || (typeof document !== 'undefined' ? document : null);
  if (!scope) return;
  for (const node of scope.querySelectorAll('[data-i18n]')) {
    node.textContent = t(node.getAttribute('data-i18n'));
  }
  const ATTRS = {
    'data-i18n-title': 'title',
    'data-i18n-placeholder': 'placeholder',
    'data-i18n-aria-label': 'aria-label',
  };
  for (const attr of Object.keys(ATTRS)) {
    for (const node of scope.querySelectorAll('[' + attr + ']')) {
      node.setAttribute(ATTRS[attr], t(node.getAttribute(attr)));
    }
  }
}

/* ---------- 皮肤（§P0-3 L5 · L6，机制预留） ---------- */

export function getSkin() {
  return readPref(SKIN_KEY) || '';
}

export function setSkin(name) {
  writePref(SKIN_KEY, name || '');
  applySkin();
}

/**
 * 装载皮肤样式表。
 *
 * 皮肤 = 一组 `--qm-*` 变量覆盖，文件放在 `src/web/css/skins/<name>.css`（§P0-3 L5）。
 * 组件 CSS **不得感知皮肤**（不写 `.skin-x .btn` 这类选择器），因此只需覆盖变量即可换肤。
 * 未选择皮肤时不注入任何样式表 —— 行为与不使用皮肤完全一致。
 */
export function applySkin() {
  if (typeof document === 'undefined') return;
  const name = getSkin();
  const existing = document.getElementById('skinLink');
  if (!name) {
    if (existing) existing.remove();
    return;
  }
  const link = existing || document.createElement('link');
  link.id = 'skinLink';
  link.rel = 'stylesheet';
  link.href = './css/skins/' + name + '.css';
  if (!existing) document.head.appendChild(link);
}

/** 启动时恢复已保存的语言与皮肤。**必须在填充任何文案之前调用**。 */
export function initPrefs() {
  const saved = readPref(LOCALE_KEY);
  if (saved && DICTIONARIES[saved]) {
    locale = saved;
    dict = DICTIONARIES[saved];
  }
  if (typeof document !== 'undefined') document.documentElement.lang = locale;
  applySkin();
  return locale;
}
