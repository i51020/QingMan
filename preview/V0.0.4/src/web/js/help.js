/**
 * 青蔓 QingMan · 帮助页
 *
 * 本文件只做三件事：① 用取词表填充静态占位；② 按分节结构渲染正文；③ 取后端实测版本。
 * 任何面向用户的文案都不写在这里 —— 全部来自 `i18n/zh-CN.js`（见 docs/项目约定.md §P0-3）。
 */

import { dict, helpSections, LOCALE } from './i18n/zh-CN.js';
import { api } from './core/api.js';

const el = (id) => document.getElementById(id);

/** 取词。未命中的键直接回显键名并告警，便于一眼看出漏翻。 */
function t(key) {
  const value = dict[key];
  if (value === undefined) {
    console.warn('[i18n] missing key:', key, '(', LOCALE, ')');
    return key;
  }
  return value;
}

/** 动态字段的当前值。version 为 null 表示尚未拿到后端实测值。 */
const state = { version: null, backendOk: false };

/* ---------- 静态占位 ---------- */

function applyStatic() {
  document.documentElement.lang = LOCALE;
  document.title = t('help.docTitle');
  for (const node of document.querySelectorAll('[data-i18n]')) {
    node.textContent = t(node.getAttribute('data-i18n'));
  }
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
  ];

  for (const row of rows) {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = t(row.label);
    const td = document.createElement('td');
    td.textContent = row.value;
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

function buildSection(section) {
  const wrap = document.createElement('section');
  wrap.className = 'help-section';
  wrap.id = 'sec-' + section.id;

  const title = document.createElement('h2');
  title.className = 'help-section-title';
  title.textContent = t(section.title);
  wrap.appendChild(title);

  wrap.appendChild(section.kind === 'about' ? buildAbout() : buildList(section));
  return wrap;
}

function renderSections() {
  const host = el('helpSections');
  const nav = el('helpNavList');
  if (!host || !nav) return;

  for (const section of helpSections) {
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

/* ---------- 启动 ---------- */

async function boot() {
  applyStatic();
  renderSections();
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
