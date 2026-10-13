/**
 * 青蔓 QingMan · 皮肤选择器（V0.0.40 改版：下拉 → 色块网格浮层）
 *
 * 皮肤注册表来自 `i18n/skins.js`，显示顺序按背景色明度（亮 → 暗）实时排序，
 * 不硬编码顺序（§P0-3 L5）。
 *
 * V0.0.40 改动（设计稿提案第 8 节）：原 `<select id="skinSelect">` 退场，改为
 * `#popSkin` 里的三列色块卡片网格 —— **卡片本身就是配色缩影**（底色/面板色/强调色
 * 按 44 : 32 : 24 的用色权重铺一条三色带），比「一行皮肤名」可辨得多。
 *
 * ⚠ 排序仍是本模块唯一的「数据契约」：`tools/browser_smoke.py` 会抓取
 *   `#skinGrid` 内 `.sw-card` 的 `data-file` 顺序，与 Python 侧按同一亮度公式
 *   **独立复算**的期望序列逐项比对（《项目手册》十三.4 的绑定守卫由下拉迁移到网格）。
 */

import { getSkin, setSkin, t } from '../i18n/index.js';
import { SKINS } from '../i18n/skins.js';

function luma(hex) {
  const s = hex.replace('#', '');
  const r = parseInt(s.slice(0, 2), 16) / 255;
  const g = parseInt(s.slice(2, 4), 16) / 255;
  const b = parseInt(s.slice(4, 6), 16) / 255;
  const gamma = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * gamma(r) + 0.7152 * gamma(g) + 0.0722 * gamma(b);
}

/**
 * @param {HTMLElement} gridEl 色块网格容器（`#skinGrid`）
 * @param {{onPick?: Function}} [opts] onPick 在选定一款后调用（用于关闭浮层、归还焦点）
 */
export function createSkinPicker(gridEl, opts = {}) {
  if (!gridEl) return null;

  const sorted = [...SKINS].sort((a, b) => luma(b.swatch[0]) - luma(a.swatch[0]));
  const cards = new Map();

  function sync() {
    const current = getSkin();
    for (const [file, card] of cards) {
      card.setAttribute('aria-pressed', file === current ? 'true' : 'false');
    }
  }

  function build() {
    gridEl.textContent = '';
    cards.clear();
    for (const skin of sorted) {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'sw-card';
      card.dataset.file = skin.file;
      card.setAttribute('role', 'option');
      card.title = t(skin.label);

      const strip = document.createElement('span');
      strip.className = 'sw';
      for (const color of skin.swatch) {
        const chip = document.createElement('i');
        // 三色取自注册表（数据，不是样式），故此处允许直接写 inline background
        chip.style.background = color;
        strip.appendChild(chip);
      }

      const name = document.createElement('span');
      name.className = 'nm';
      name.textContent = t(skin.label);

      card.append(strip, name);
      card.addEventListener('click', () => {
        setSkin(skin.file);
        sync();
        if (typeof opts.onPick === 'function') opts.onPick(skin.file);
      });
      gridEl.appendChild(card);
      cards.set(skin.file, card);
    }
    sync();
  }

  build();
  // 皮肤名是取词键（skin.N）→ 换语言须重建（与旧版同构，C-P2-1）。
  document.addEventListener('qmlocalechange', build);
  // 皮肤文件 onload 后广播 —— 内存态切换（非 setSkin）也能同步选中角标。
  document.addEventListener('qmskinchange', sync);

  return { sync };
}
