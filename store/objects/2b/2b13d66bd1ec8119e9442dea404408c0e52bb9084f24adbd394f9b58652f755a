/**
 * 青蔓 QingMan · 支持页（V0.0.18 从帮助页拆出）
 *
 * 与帮助页同壳（tokens/base/help.css + 品牌区 + 语言下拉 + 版本 chip），
 * 正文只有赞赏支持一块。任何面向用户的文案都不写在这里 —— 全部来自 i18n 取词表。
 */

import { t, applyStatic, initPrefs, watchLocale } from './i18n/index.js';
import { createLangPicker } from './ui/lang-picker.js';
import { api } from './core/api.js';

const el = (id) => document.getElementById(id);

/** 动态字段的当前值。version 为 null 表示尚未拿到后端实测值。 */
const state = { version: null, backendOk: false };

function applyShell() {
  applyStatic(document);
  document.title = t('support.docTitle');
  const back = el('btnBack');
  if (back) back.title = t('help.backTip');
}

function buildSupport() {
  const box = document.createElement('div');
  box.className = 'help-support';

  const figure = document.createElement('figure');
  figure.className = 'help-qr';
  const img = document.createElement('img');
  img.src = './assets/sponsor-wechat.png';
  img.alt = t('help.support.qrAlt');
  const figcaption = document.createElement('figcaption');
  figcaption.textContent = t('help.support.wechat');
  figure.append(img, figcaption);

  const thanks = document.createElement('p');
  thanks.className = 'help-thanks';
  thanks.textContent = t('help.support.thanks');

  box.append(figure, thanks);
  return box;
}

function renderContent() {
  const host = el('supportContent');
  if (!host) return;
  host.textContent = '';
  host.appendChild(buildSupport());
}

function paint() {
  const version = state.version || t('help.versionFallback');
  const chip = el('helpChipVersion');
  if (chip) chip.textContent = version;
}

document.addEventListener('qmlocalechange', () => {
  applyShell();
  renderContent();
  paint();
});

async function boot() {
  initPrefs();
  watchLocale();
  createLangPicker(el('helpLangSelect'));
  applyShell();
  renderContent();
  paint();

  try {
    const info = await api.health();
    state.version = info.version;
    state.backendOk = true;
  } catch (err) {
    state.version = null;
    state.backendOk = false;
  }
  paint();
}

boot();
