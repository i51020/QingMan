/**
 * 青蔓 QingMan · 取词与偏好运行时（§P0-3 L1–L3 · L6）
 *
 * 单一取词入口：**所有面向用户可见的文案都必须经 `t(key)` 取得**，
 * UI 模块一律不得直写文案（由 `tools/verify.py` 的静态检查把关）。
 *
 * 语言包机制（V0.0.44）：出厂语言（zh-CN / en-US）**静态内置**以保证首屏同步取词；
 * 其余语言包放 `locales/<tag>.js`（V0.3.0 起在项目根，服务端经 `/locales/` 提供），由 `/api/locales.js` 枚举、
 * 前端经 `loadLocale()` 按需动态加载 —— **新增一门语言无需改动任何代码**。
 *
 * 五个偏好键持久化在 localStorage（**§P0-3 L6 为权威清单**，`tools/verify.py` 的 7ai 守卫
 * 绑死「实现 / 守卫 / 约定」三方一致）：
 * `qm.lang`（语言）/ `qm.skin`（皮肤）/ `qm.inspMode`（检视器模式，V0.0.43）/`qm.launchIcon`（皮肤联动启动图标，V0.0.15 —— 唯一消费者 `ui/launch-icon.js`）。
 * V0.0.51@r9：`qm.genBar`（生成栏折叠态）**退场** —— 折叠撤销，见本文件下方说明。
 * 本模块的 DOM / localStorage 访问全部发生在函数内部 —— 顶层导入是安全的，
 * 因此纯逻辑模块（如 modules/tree-model.js）也可以取词。
 *
 * 持久化单一访问点：`readPref` / `writePref` 对外导出，供其他模块（如皮肤联动图标）
 * 复用同一条带降级的读写路径，**不要在别处直访 `window.localStorage`**。
 */

/* V0.3.0：语言包已迁到项目根 `locales/`。此处用**相对路径**而非 `/locales/...`：
   绝对路径只有浏览器（同源服务）能解析，Node 侧单测会直接 ERR_MODULE_NOT_FOUND。
   四层上跳：i18n → js → web → src → 项目根。 */
import { dict as zhCN, helpSections as hsZh, NAME as nameZh } from '../../../../locales/zh-CN.js';
import { dict as enUS, helpSections as hsEn, NAME as nameEn } from '../../../../locales/en-US.js';
import { SKINS, DEFAULT_SKIN_CID } from './skins.js';

/**
 * 出厂语言包（**静态内置**）。
 *
 * 为什么内置而非全部动态：① 首屏**同步**可用 —— 模块脚本一执行完即能取词，无需
 * await，否则界面会先按空字典画一遍再跳变；② 后端不可用时（直接以 `file://` 打开
 * 页面）仍有一套完整语言可降级。其余语言按需从 `/locales/` **动态加载**。
 */
const BUILTIN_LOCALES = {
  'zh-CN': { name: nameZh, dict: zhCN, help: hsZh },
  'en-US': { name: nameEn, dict: enUS, help: hsEn },
};

/** 运行时语言注册表（内置 + 已动态加载）：`code → { name, dict, help }`。 */
const LOCALES = new Map(Object.entries(BUILTIN_LOCALES));

/** 语言代码形态白名单（BCP 47 粗判）。**代码会被拼进动态 import 的路径**，故必须过滤。 */
const LOCALE_SHAPE = /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/;

/** 后端注入的可用语言清单（`/api/locales.js` 同步注入，早于 module 脚本执行）。 */
function injectedLocales() {
  if (typeof window === 'undefined') return [];
  const raw = window.__QM_LOCALES__;
  if (!Array.isArray(raw)) return [];
  const out = [];
  for (const item of raw) {
    if (!item) continue;
    const code = String(item.code || '');
    if (!LOCALE_SHAPE.test(code)) continue;   // 清单来自文件系统，仍按白名单收口
    const name = typeof item.name === 'string' && item.name ? item.name : code;
    out.push({ code, name });
  }
  return out;
}

/**
 * 当前可用语言代码，顺序即语言选择器顺序（后端清单在前，未列入的内置语言补齐在后）。
 * **不导出为常量** —— 语言包可在运行时增删，快照式常量会与界面所见不一致。
 */
export function supportedLocales() {
  const seen = new Set();
  const out = [];
  for (const item of injectedLocales()) {
    if (!seen.has(item.code)) { seen.add(item.code); out.push(item.code); }
  }
  for (const code of LOCALES.keys()) {
    if (!seen.has(code)) { seen.add(code); out.push(code); }
  }
  return out;
}

/** 某语言的**自描述名**（母语写法）；未加载且无注入名时回落到代码本身。 */
export function localeName(code) {
  const entry = LOCALES.get(code);
  if (entry && entry.name) return entry.name;
  const hit = injectedLocales().find((x) => x.code === code);
  return hit ? hit.name : code;
}

const LOADING = new Map();

/**
 * 按需加载扩展语言包（`/locales/<code>.js`，动态 import）。**已加载则立即返回**。
 *
 * 失败（文件不存在 / 契约不符 / 代码形态非法）返回 `false`，调用方据此保持当前语言 ——
 * 语言包是**可增删的外部数据**，不能假定清单里的每一项都真能加载成功。
 */
export function loadLocale(code) {
  if (LOCALES.has(code)) return Promise.resolve(true);
  if (!LOCALE_SHAPE.test(String(code || ''))) return Promise.resolve(false);
  if (LOADING.has(code)) return LOADING.get(code);
  const url = new URL('../../../../locales/' + code + '.js', import.meta.url).href;
  const pending = import(url)
    .then((mod) => {
      if (!mod || typeof mod.dict !== 'object' || mod.dict === null) {
        console.warn('[i18n] locale pack has no dict:', code);
        return false;
      }
      LOCALES.set(code, {
        name: typeof mod.NAME === 'string' && mod.NAME ? mod.NAME : code,
        dict: mod.dict,
        help: Array.isArray(mod.helpSections) ? mod.helpSections : [],
      });
      return true;
    })
    .catch((err) => {
      console.warn('[i18n] cannot load locale pack:', code, err);
      return false;
    })
    .finally(() => { LOADING.delete(code); });
  LOADING.set(code, pending);
  return pending;
}

export const DEFAULT_LOCALE = 'zh-CN';
/** 「跟随系统」的偏好值。它不是语种，需经 `resolveLocale()` 解析成实际语种。 */
export const AUTO_LOCALE = 'auto';
export const LOCALE_KEY = 'qm.lang';
export const SKIN_KEY = 'qm.skin';
/** 检视器显示模式（V0.0.43 · H 组）：`'prop'` 属性 / `'src'` 源码。 */
export const INSP_KEY = 'qm.inspMode';
/** 上次已上传的启动图标配色指纹（P3-9）：持久化后，页面重载不再无条件重传图标。 */
export const ICON_KEY = 'qm.launchIcon';

let locale = DEFAULT_LOCALE;
let dict = BUILTIN_LOCALES[DEFAULT_LOCALE].dict;

/* ---------- 语种探测与匹配（BCP 47 降级） ---------- */

/**
 * 操作系统语言（V0.0.14）。
 *
 * 值由后端 `GET /api/env.js` **同步注入**（`<script src>` 早于 module 脚本执行），
 * 因此首屏即可拿到，不存在「先按浏览器语言画一遍再跳变」的闪烁。
 * 取不到（非 Windows / 脚本未加载）返回空串 —— 调用方据此回落到浏览器语言。
 */
function osLocale() {
  if (typeof window === 'undefined') return '';
  const value = window.__QM_OS_LOCALE__;
  return typeof value === 'string' ? value.trim() : '';
}

/**
 * 语种偏好列表，**OS 语言优先于浏览器语言**。
 *
 * 顺序即优先级：`window.__QM_OS_LOCALE__` → `navigator.languages`。
 * 浏览器语言可被单独改写（安装时选了英文、或用户在设置里调过），
 * 只有 OS 语言才是「跟随系统」的本意；浏览器语言退居其次，仅在取不到 OS 值时兜底。
 */
function systemLocales() {
  const list = [];
  const os = osLocale();
  if (os) list.push(os);
  if (typeof navigator !== 'undefined') {
    if (Array.isArray(navigator.languages) && navigator.languages.length) {
      return list.concat(navigator.languages.slice());
    }
    if (navigator.language) return list.concat([navigator.language]);
  }
  return list;
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
  const available = supportedLocales();
  for (let i = parts.length; i > 0; i -= 1) {
    const candidate = parts.slice(0, i).join('-');
    const hit = available.find((s) => s.toLowerCase() === candidate);
    if (hit) return hit;
  }
  const primary = parts[0];
  return available.find((s) => s.toLowerCase().split('-')[0] === primary) || null;
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
  if (pref && pref !== AUTO_LOCALE && LOCALES.has(pref)) return pref;
  return lookupLocale(systemLocales()) || DEFAULT_LOCALE;
}

/** 只改内存与 `<html lang>`，不写盘、不刷 DOM。 */
function applyLocale(next) {
  locale = next;
  const entry = LOCALES.get(next);
  dict = entry ? entry.dict : BUILTIN_LOCALES[DEFAULT_LOCALE].dict;
  if (typeof document !== 'undefined') document.documentElement.lang = next;
}

/* ---------- 偏好存取 ---------- */

/** localStorage 在隐私模式 / 沙箱 iframe 下可能抛错，一律降级为「本会话内生效」。 */
export function readPref(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (err) {
    return null;
  }
}

export function writePref(key, value) {
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
export async function setLocale(next) {
  if (next !== AUTO_LOCALE && !LOCALES.has(next)) {
    const ok = await loadLocale(next);   // 扩展语言按需加载；加载失败即保持当前语言
    if (!ok) return false;
  }
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
  if (saved === AUTO_LOCALE) return AUTO_LOCALE;
  // 只校验**形态**，不要求已加载 —— 用户选过的扩展语言可能本次还没加载，
  // 若在此判为非法，用户的选择会被悄悄改回「跟随系统」。
  return saved && LOCALE_SHAPE.test(saved) ? saved : AUTO_LOCALE;
}

/** 是否显式选过语言（用于区分「出厂默认」与「用户选的同一档」）。 */
export function hasLocalePref() {
  const saved = readPref(LOCALE_KEY);
  return Boolean(saved && (saved === AUTO_LOCALE || LOCALE_SHAPE.test(saved)));
}

/**
 * 跨页面同步：另一标签页改了 `qm.lang` 时，本页随之切换。
 * 主界面与帮助页是两个独立页面，共享 localStorage 但各自持有内存态，
 * 不监听 `storage` 就会出现「主界面切了语言、已打开的帮助页还是旧语言」。
 */
/**
 * 切到某偏好值：必要时先补载语言包，再应用并广播。
 *
 * **跨页同步（`watchLocale`）与启动补载（`initPrefs`）共用这一条路径** ——
 * 否则「另一标签页选了扩展语言」与「本页启动时偏好是扩展语言」会走出两种行为。
 */
function switchTo(pref) {
  const needLoad = pref && pref !== AUTO_LOCALE && !LOCALES.has(pref) && LOCALE_SHAPE.test(pref);
  const commit = () => {
    const resolved = resolveLocale(pref);
    if (resolved === locale) return;
    applyLocale(resolved);
    if (typeof document !== 'undefined') {
      applyStatic(document);
      document.dispatchEvent(new CustomEvent('qmlocalechange', { detail: { locale: resolved } }));
    }
  };
  if (needLoad) loadLocale(pref).then((ok) => { if (ok) commit(); });
  else commit();
}

export function watchLocale() {
  if (typeof window === 'undefined') return;
  window.addEventListener('storage', (event) => {
    if (event.key !== LOCALE_KEY) return;
    switchTo(event.newValue || AUTO_LOCALE);
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

/** 静态文案填充：`data-i18n` 填文本，另四个变体填对应属性。 */
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
    // V0.0.40：`alt` 是 <img> 的无障碍文本，不能省（支持弹窗的赞赏码）。
    // 注意：新增变体时须同步 `tools/verify.py` 7b-2 的采集正则，否则该键
    // 不会被「取词键闭包」校验覆盖，漏翻会静默溜过。
    'data-i18n-alt': 'alt',
  };
  for (const attr of Object.keys(ATTRS)) {
    for (const node of scope.querySelectorAll('[' + attr + ']')) {
      node.setAttribute(ATTRS[attr], t(node.getAttribute(attr)));
    }
  }
}

/* ---------- 帮助分节（V0.0.44 · 语言包统一来源） ---------- */

/**
 * 当前语言的帮助分节结构：帮助页（`help.js`）与帮助弹窗（`ui/help-doc.js`）**共用同一份**。
 *
 * 与 `t()` 同源 —— 都取自当前语言包，故「页面版」与「弹窗版」内容不可能漂移
 * （上一版是靠 `getLocale() === 'en-US' ? en : zh` 硬编码两语，新增语言即漏）。
 * 语言包未提供 `helpSections` 时返回空数组，调用方渲染空即可，不抛错。
 */
export function getHelpSections() {
  const entry = LOCALES.get(locale);
  return entry && Array.isArray(entry.help) ? entry.help : [];
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

/** 已登记皮肤文件名白名单（C-P3-5）：用于校验持久化偏好，非法值一律回落出厂默认。 */
const SKIN_FILES = new Set(SKINS.map((s) => s.file));

/**
 * 当前皮肤文件名。**恒返回非空**（无偏好或偏好非法时都给出厂默认）。
 *
 * C-P3-5：`localStorage` 可被手改、也可能残留旧版本/其它页写下的值；直接拿原值去拼
 * `./css/skins/<name>.css` 会 404 —— 皮肤样式表装载失败即落回 `tokens.css` 的裸色，
 * 与选择器上显示的皮肤名不符。故按注册表白名单校验，非法值回落出厂默认。
 */
export function getSkin() {
  const saved = readPref(SKIN_KEY);
  return SKIN_FILES.has(saved) ? saved : defaultSkinFile();
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
  const firstLoad = !existing;
  link.id = 'skinLink';
  link.rel = 'stylesheet';
  link.href = './css/skins/' + name + '.css';
  if (firstLoad) document.head.appendChild(link);

  // 皮肤样式表**加载完成**后才广播换肤（V0.0.15）：订阅方（如皮肤联动图标）
  // 需要读到新皮肤的 --qm-* 计算值 —— onload 之前 getComputedStyle 拿到的还是旧色。
  // 每次换肤都重建监听（href 赋值即触发重载）；内存态切换（非 setSkin）不重复广播。
  link.onload = () => {
    document.dispatchEvent(new CustomEvent('qmskinchange', { detail: { skin: name } }));
  };
}

/* ---------- 生成参数区：折叠已撤销（V0.0.51@r9） ----------

   这里原有 `getGenBarState()` / `setGenBarState()` 与偏好键 `qm.genBar`（§P0-3 L6）。
   撤销的理由见 `src/web/css/layout.css` 的 `#genBar` 注释：折叠态**持久化**意味着用户
   随手一收，此后每次打开「目标位置」整行连同「选择目录」按钮都不见了 —— 一个**永久
   消失的入口**，而参数区只占一行，省下的高度不值这个风险。
   故键与两个访问函数一并删除；摘要行退化为纯展示（`renderGenBar()` 只写文本），
   不再有状态可存。**仍可复用的教训**（曾是本键的关键约束）：折叠态若要在每次渲染时
   按业务条件动态推断，会与用户操作方向相反 —— 这属于「持久化 UI 状态」的通用陷阱。
*/

/* ---------- 检视器显示模式（V0.0.43 · H 组） ---------- */

/**
 * 检视器显示模式：`'prop'`（属性表）或 `'src'`（源码）。
 *
 * 与语言 / 皮肤 / 折叠态同一条带降级的读写路径 —— 该路径是本模块对外承诺的
 * **单一偏好访问点**（见文件头）。任何非法 / 缺失值一律回落 `'prop'`。
 */
export function getInspMode() {
  return readPref(INSP_KEY) === 'src' ? 'src' : 'prop';
}

/** 写检视器模式；非 `'src'` 一律落回 `'prop'`（把值域收在此处，调用方不必自校验）。 */
export function setInspMode(mode) {
  writePref(INSP_KEY, mode === 'src' ? 'src' : 'prop');
}

/** 启动时恢复已保存的语言与皮肤。**必须在填充任何文案之前调用**。 */
export function initPrefs() {
  const pref = getLocalePreference();
  applyLocale(resolveLocale(pref));
  applySkin();
  // 偏好指向**未内置**的扩展语言包时，首屏**不等它**（等会白屏）：先用默认画一遍，
  // 加载完成后经 switchTo 切过去。丢掉的只是一次重绘，换来的是首屏零阻塞。
  if (pref !== AUTO_LOCALE && !LOCALES.has(pref)) switchTo(pref);
  return locale;
}
