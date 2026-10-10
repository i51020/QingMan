/**
 * 青蔓 QingMan · 后端错误本地化
 *
 * 后端 `_fail()` 返回的是结构化三件套 `{ ok, code, message, detail }`，
 * 其中 `message` 是**已按中文渲染好的整句**，`detail` 才是参数字典。
 * 本模块只认 `code` + `detail`，用取词表的 `err.<code>` 重新成句 —— 因此
 * 界面语言切换后，错误消息随之切换，后端无需感知语言。
 *
 * 未登记的错误码**回退后端原文**，与既有行为一致（存量行为不破坏）。
 * 由 tools/verify.py 的「错误码本地化闭包」守卫保证 `err.<code>` 的覆盖度。
 *
 * 文案一律经取词表（§P0-3 L1），本文件不直写任何用户可见文案。
 */

import { t, has } from '../i18n/index.js';

/**
 * 后端错误 → 当前语言的文案。
 * @param {Error} err `api.js` 抛出的错误，带 `code` 与 `detail`
 * @returns {string} 本地化文案；未登记的码回退 `err.message`
 */
export function localizeError(err) {
  const code = err && err.code ? err.code : '';
  if (code) {
    const key = 'err.' + code;
    if (has(key)) return t(key, (err && err.detail) || {});
  }
  return err && err.message ? err.message : '';
}

/**
 * 错误码徽标文本（技术排查用的稳定标识）。
 * 无码时返回空串 —— 调用方据此决定是否拼接，避免出现空的「错误码：」。
 * @returns {string}
 */
export function errorCode(err) {
  const code = err && err.code ? err.code : '';
  return code ? t('err.codeLabel', { code }) : '';
}

/**
 * 本地化文案 + 错误码徽标。用于**直接向用户展示错误**的场景；
 * 已包在外层包装文案里的场景（如「保存失败：…」）请用 `localizeError()`，
 * 否则会出现「保存失败：目录名含非法字符：a/b · 错误码：x」这类套娃。
 * @returns {string}
 */
export function describeError(err) {
  const text = localizeError(err);
  const badge = errorCode(err);
  if (!text) return badge;
  return badge ? text + ' · ' + badge : text;
}
