/**
 * 青蔓 QingMan · 皮肤选择器
 *
 * 皮肤注册表来自 `i18n/skins.js`，显示顺序按背景色明度（亮 → 暗）实时排序，
 * 不硬编码顺序（§P0-3 L5）。
 */

import { getSkin, setSkin, t } from '../i18n/index.js';
import { SKINS, DEFAULT_SKIN_CID } from '../i18n/skins.js';

function luma(hex) {
  const s = hex.replace('#', '');
  const r = parseInt(s.slice(0, 2), 16) / 255;
  const g = parseInt(s.slice(2, 4), 16) / 255;
  const b = parseInt(s.slice(4, 6), 16) / 255;
  const gamma = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * gamma(r) + 0.7152 * gamma(g) + 0.0722 * gamma(b);
}

export function createSkinPicker(selectEl) {
  const sorted = [...SKINS].sort((a, b) => luma(b.swatch[0]) - luma(a.swatch[0]));

  const none = document.createElement('option');
  none.value = '';
  none.textContent = t('skin.default');
  selectEl.appendChild(none);

  for (const skin of sorted) {
    const opt = document.createElement('option');
    opt.value = skin.file;
    opt.textContent = t(skin.label);
    selectEl.appendChild(opt);
  }

  const saved = getSkin();
  selectEl.value = saved || SKINS.find(s => s.cid === DEFAULT_SKIN_CID)?.file || '';

  selectEl.addEventListener('change', () => {
    setSkin(selectEl.value);
  });
}
