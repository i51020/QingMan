/**
 * 青蔓 QingMan · 帮助页
 *
 * 本文件只做三件事：① 用取词表填充静态占位；② 按分节结构渲染正文；③ 取后端实测版本。
 * 任何面向用户的文案都不写在这里 —— 全部来自 `i18n/*.js`（见 docs/项目约定.md §P0-3）。
 */

import { helpSections as helpSectionsZh } from './i18n/zh-CN.js';
import { helpSections as helpSectionsEn } from './i18n/en-US.js';
import { t, applyStatic, initPrefs, getLocale, watchLocale } from './i18n/index.js';
import { createLangPicker } from './ui/lang-picker.js';
import { api } from './core/api.js';

const el = (id) => document.getElementById(id);

function currentHelpSections() {
  return getLocale() === 'en-US' ? helpSectionsEn : helpSectionsZh;
}

/** 动态字段的当前值。version 为 null 表示尚未拿到后端实测值。 */
const state = { version: null, backendOk: false };

/* ---------- 静态占位 ---------- */

function applyShell() {
  applyStatic(document);
  document.title = t('help.docTitle');
  const back = el('btnBack');
  if (back) back.title = t('help.backTip');
}

/* ---------- 正文渲染 ---------- */

function buildList(section) {
  const tag = section.kind === 'ol' ? 'ol' : 'ul';
  const list = document.createElement(tag);
  list.className = section.kind === 'note' ? 'help-list help-note' : 'help-list';
  for (const key of section.items) {
    const li = document.createElement('li');
    li.textContent = t(key);
    list.appendChild(li);
  }
  return list;
}

function buildAbout() {
  const table = document.createElement('table');
  table.className = 'help-table';

  const rows = [
    { label: 'about.app', value: t('app.nameZh') + ' ' + t('app.nameEn') },
    { label: 'about.version', value: '', cellId: 'aboutVersion' },
    { label: 'about.backend', value: '', cellId: 'aboutBackend' },
    { label: 'about.docs', value: t('about.docsValue') },
    { label: 'help.support.title', value: '', link: { href: './support.html', text: t('help.support.goto'), tip: t('help.support.gotoTip') } },
  ];

  for (const row of rows) {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = t(row.label);
    const td = document.createElement('td');
    if (row.link) {
      const a = document.createElement('a');
      a.href = row.link.href;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = row.link.text;
      a.title = row.link.tip;
      td.appendChild(a);
    } else {
      td.textContent = row.value;
    }
    if (row.cellId) td.id = row.cellId;
    tr.append(th, td);
    table.appendChild(tr);
  }

  const note = document.createElement('p');
  note.className = 'help-foot-note';
  note.textContent = t('about.note');

  const box = document.createElement('div');
  box.append(table, note);
  return box;
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

function buildSection(section) {
  const wrap = document.createElement('section');
  wrap.className = 'help-section';
  wrap.id = 'sec-' + section.id;

  const title = document.createElement('h2');
  title.className = 'help-section-title';
  title.textContent = t(section.title);
  wrap.appendChild(title);

  let body;
  if (section.kind === 'about') body = buildAbout();
  else if (section.kind === 'support') body = buildSupport();
  else body = buildList(section);
  wrap.appendChild(body);
  return wrap;
}

function renderSections() {
  const host = el('helpSections');
  const nav = el('helpNavList');
  if (!host || !nav) return;

  for (const section of currentHelpSections()) {
    host.appendChild(buildSection(section));

    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = '#sec-' + section.id;
    a.textContent = t(section.title);
    li.appendChild(a);
    nav.appendChild(li);
  }
}

/* ---------- 动态字段 ---------- */

function paint() {
  const version = state.version || t('help.versionFallback');

  const chip = el('helpChipVersion');
  if (chip) chip.textContent = version;

  const cell = el('aboutVersion');
  if (cell) {
    cell.textContent = state.backendOk ? version : version + ' ' + t('help.versionStale');
    cell.classList.toggle('help-stale', !state.backendOk);
  }

  const backend = el('aboutBackend');
  if (backend) backend.textContent = state.backendOk ? t('about.backendOn') : t('about.backendOff');
}

function scrollToHash() {
  const hash = window.location.hash.replace('#', '');
  if (!hash) return;
  const target = document.getElementById('sec-' + hash) || document.getElementById(hash);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- 启动 ---------- */

/* 语言切换后重渲染：正文按语种取自不同数组（helpSectionsZh / helpSectionsEn），
 * 静态壳（标题、返回按钮提示）由 applyShell 处理。 */
document.addEventListener('qmlocalechange', () => {
  applyShell();
  renderSections();
  paint();
});

async function boot() {
  initPrefs();                   // 先恢复语言/皮肤偏好，再填文案
  watchLocale();                 // 主界面改语言时，已打开的帮助页随之切换
  createLangPicker(el('helpLangSelect'));
  applyShell();
  renderSections();
  scrollToHash();
  paint();                       // 先渲染本机记录值，避免等后端时留空

  try {
    const info = await api.health();
    state.version = info.version;
    state.backendOk = true;
  } catch (err) {
    state.version = null;
    state.backendOk = false;
  }
  paint();                       // 后端实测值回来后覆盖
}

boot();
