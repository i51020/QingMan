/**
 * 青蔓 QingMan · 取词与偏好运行时（§P0-3 L1–L3 · L6）
 *
 * 单一取词入口：**所有面向用户可见的文案都必须经 `t(key)` 取得**，
 * UI 模块一律不得直写文案（由 `tools/verify.py` 的静态检查把关）。
 *
 * 语言 / 皮肤 / 界面折叠态分别持久化在 localStorage 的
 * `qm.lang` / `qm.skin` / `qm.genBar`（§P0-3 L6）。
 * 本模块的 DOM / localStorage 访问全部发生在函数内部 —— 顶层导入是安全的，
 * 因此纯逻辑模块（如 modules/tree-model.js）也可以取词。
 */

import { dict as zhCN } from './zh-CN.js';
import { dict as enUS } from './en-US.js';
import { SKINS, DEFAULT_SKIN_CID } from './skins.js';

/** 语言代码 → 字典。新增语种时在此登记（§P0-3 L3）。 */
const DICTIONARIES = { 'zh-CN': zhCN, 'en-US': enUS };

export const SUPPORTED_LOCALES = Object.freeze(Object.keys(DICTIONARIES));
export const DEFAULT_LOCALE = 'zh-CN';
/** 「跟随系统」的偏好值。它不是语种，需经 `resolveLocale()` 解析成实际语种。 */
export const AUTO_LOCALE = 'auto';
export const LOCALE_KEY = 'qm.lang';
export const SKIN_KEY = 'qm.skin';
export const GENBAR_KEY = 'qm.genBar';

let locale = DEFAULT_LOCALE;
let dict = DICTIONARIES[locale];

/* ---------- 语种探测与匹配（BCP 47 降级） ---------- */

/**
 * 系统/浏览器给出的语种偏好列表。
 * 浏览器语境下拿不到真正的 OS 语言，只能拿到浏览器语言偏好；
 * 而 Edge / Chrome 默认继承 OS 显示语言，故该列表在默认配置下即等于系统语言。
 */
function systemLocales() {
  if (typeof navigator === 'undefined') return [];
  if (Array.isArray(navigator.languages) && navigator.languages.length) {
    return navigator.languages.slice();
  }
  return navigator.language ? [navigator.language] : [];
}

/**
 * 单个语种标签的匹配。
 *
 * 采用 **BCP 47 降级链**，而非精确匹配 —— 精确匹配会让 `zh-Hant-TW` 落空后
 * 直接回退默认语种，导致繁体用户看到英文界面。
 *
 * 顺序：① 逐级剥离子标签做精确匹配（`zh-hant-tw` → `zh-hant` → `zh`）；
 * ② 仍不中则按 **主语言子标签** 匹配（`zh` → `zh-CN`，`en` → `en-US`）。
 *
 * @param {string} tag 任意语种标签，大小写与 `-`/`_` 分隔符均兼容
 * @returns {string|null} 命中的已登记语种；无命中返回 null
 */
export function matchLocale(tag) {
  const parts = String(tag || '').toLowerCase().split(/[-_]/).filter(Boolean);
  if (!parts.length) return null;
  for (let i = parts.length; i > 0; i -= 1) {
    const candidate = parts.slice(0, i).join('-');
    const hit = SUPPORTED_LOCALES.find((s) => s.toLowerCase() === candidate);
    if (hit) return hit;
  }
  const primary = parts[0];
  return SUPPORTED_LOCALES.find((s) => s.toLowerCase().split('-')[0] === primary) || null;
}

/** 在一串偏好里挑第一个能命中的语种；全不命中返回 null。 */
export function lookupLocale(preferred) {
  const list = Array.isArray(preferred) ? preferred : (preferred ? [preferred] : []);
  for (const tag of list) {
    const hit = matchLocale(tag);
    if (hit) return hit;
  }
  return null;
}

/**
 * 偏好值 → 实际语种。
 * 显式语种直接用；`auto`（或空）走系统探测；探测无命中落到 `DEFAULT_LOCALE`。
 */
export function resolveLocale(pref) {
  if (pref && pref !== AUTO_LOCALE && DICTIONARIES[pref]) return pref;
  return lookupLocale(systemLocales()) || DEFAULT_LOCALE;
}

/** 只改内存与 `<html lang>`，不写盘、不刷 DOM。 */
function applyLocale(next) {
  locale = next;
  dict = DICTIONARIES[next];
  if (typeof document !== 'undefined') document.documentElement.lang = next;
}

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

/**
 * 切换语言。可接受具体语种或 `AUTO_LOCALE`（跟随系统）。
 * 未登记的语种返回 false，不做任何改动；成功时刷新全部静态文案并广播事件。
 */
export function setLocale(next) {
  if (next !== AUTO_LOCALE && !DICTIONARIES[next]) return false;
  const resolved = resolveLocale(next);
  writePref(LOCALE_KEY, next);
  applyLocale(resolved);
  if (typeof document !== 'undefined') {
    applyStatic(document);
    document.dispatchEvent(new CustomEvent('qmlocalechange', { detail: { locale: resolved } }));
  }
  return true;
}

/** 用户显式选过的偏好值（可能是 `auto`）。未选过也返回 `auto` —— 即出厂默认就是跟随系统。 */
export function getLocalePreference() {
  const saved = readPref(LOCALE_KEY);
  return saved && (saved === AUTO_LOCALE || DICTIONARIES[saved]) ? saved : AUTO_LOCALE;
}

/** 是否显式选过语言（用于区分「出厂默认」与「用户选的同一档」）。 */
export function hasLocalePref() {
  const saved = readPref(LOCALE_KEY);
  return Boolean(saved && (saved === AUTO_LOCALE || DICTIONARIES[saved]));
}

/**
 * 跨页面同步：另一标签页改了 `qm.lang` 时，本页随之切换。
 * 主界面与帮助页是两个独立页面，共享 localStorage 但各自持有内存态，
 * 不监听 `storage` 就会出现「主界面切了语言、已打开的帮助页还是旧语言」。
 */
export function watchLocale() {
  if (typeof window === 'undefined') return;
  window.addEventListener('storage', (event) => {
    if (event.key !== LOCALE_KEY) return;
    const resolved = resolveLocale(event.newValue || AUTO_LOCALE);
    if (resolved === locale) return;
    applyLocale(resolved);
    if (typeof document !== 'undefined') {
      applyStatic(document);
      document.dispatchEvent(new CustomEvent('qmlocalechange', { detail: { locale: resolved } }));
    }
  });
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

/**
 * 出厂默认皮肤的文件名。
 *
 * 皮肤不可缺省 —— 未选过时**必须**落到默认皮肤（`DEFAULT_SKIN_CID`），
 * 否则用户看到的是 `tokens.css` 的裸色，与选择器上显示的皮肤名不一致。
 * 注册表缺失该项时回退为空串（不注入），由「皮肤注册表」守卫负责报错。
 */
function defaultSkinFile() {
  const hit = SKINS.find((s) => s.cid === DEFAULT_SKIN_CID);
  return hit ? hit.file : '';
}

/** 当前皮肤文件名。**恒返回非空**（无偏好时给出厂默认）。 */
export function getSkin() {
  const saved = readPref(SKIN_KEY);
  return saved || defaultSkinFile();
}

/** 是否显式选过皮肤（用于区分「出厂默认」与「用户选的同一款」）。 */
export function hasSkinPref() {
  return Boolean(readPref(SKIN_KEY));
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
 * 未选择皮肤时装载**出厂默认皮肤** —— 产品始终有一套完整配色，不存在"无皮肤"态。
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

/* ---------- 界面折叠态（§P0-3 L6） ---------- */

/**
 * 生成参数区的折叠态，取值 `'open'` / `'closed'`；未设置时返回空串。
 *
 * 该状态**只在启动时定一次**并落盘，之后完全由用户控制。不要在每次渲染时
 * 按"目标位置是否已填"动态推断 —— 那样用户输入目标位置的第一个字符就会
 * 触发展开区自动收起，恰好与帮助页的引导顺序（先填目标位置）相反。
 */
export function getGenBarState() {
  const saved = readPref(GENBAR_KEY);
  return saved === 'open' || saved === 'closed' ? saved : '';
}

/** 写折叠态；传入非法值时清除记录（下次启动重新按默认展开）。 */
export function setGenBarState(state) {
  writePref(GENBAR_KEY, state === 'open' || state === 'closed' ? state : '');
}

/** 启动时恢复已保存的语言与皮肤。**必须在填充任何文案之前调用**。 */
export function initPrefs() {
  applyLocale(resolveLocale(getLocalePreference()));
  applySkin();
  return locale;
}
