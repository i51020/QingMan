/**
 * 青蔓 QingMan · 皮肤注册表
 *
 * 单一数据源：皮肤 id / 文件名 / 名称取词键 / 色板预览。
 * 显示顺序**不写死** —— 由 ui/skin-picker.js 按背景明度（亮 → 暗）实时排序（§P0-3 L5）。
 * 色板仅用于选择器上的三色预览点；组件配色一律来自 skins/<file>.css 的变量覆盖。
 */

/** 默认皮肤：S06 月光序章·钢笔灰（中性、专业）。 */
export const DEFAULT_SKIN_CID = 6;

export const SKINS = [
  { cid: 1, file: 's01-cream-pink', label: 'skin.1', swatch: ['#f9f0f4', '#e32d6a', '#fff5f8'] },
  { cid: 2, file: 's02-offwhite-pine', label: 'skin.2', swatch: ['#f4f0e1', '#3e7a4c', '#faf6e9'] },
  { cid: 3, file: 's03-softdark-iceblue', label: 'skin.3', swatch: ['#1f2c42', '#50b5e0', '#313d51'] },
  { cid: 4, file: 's04-warmwhite-amber', label: 'skin.4', swatch: ['#fdf2e5', '#d3670a', '#fff7ee'] },
  { cid: 5, file: 's05-cream-warmwhite', label: 'skin.5', swatch: ['#faf0d4', '#b27e0d', '#fff8e5'] },
  { cid: 6, file: 's06-moonlight-pengray', label: 'skin.6', swatch: ['#f7f7f5', '#65696f', '#ffffff'] },
  { cid: 7, file: 's07-night-inkblue', label: 'skin.7', swatch: ['#162a46', '#d8d0c1', '#293b55'] },
  { cid: 8, file: 's08-winter-sun', label: 'skin.8', swatch: ['#cfdfef', '#0068ba', '#e4eef7'] },
  { cid: 9, file: 's09-first-snow', label: 'skin.9', swatch: ['#dfdff0', '#0068b8', '#eaecf8'] },
  { cid: 10, file: 's10-white-moonlight', label: 'skin.10', swatch: ['#d4f0f6', '#2c748e', '#e5f6fa'] },
  { cid: 11, file: 's11-vintage-paper', label: 'skin.11', swatch: ['#e8dcc8', '#8b6e54', '#f0e6d5'] },
  { cid: 12, file: 's12-moonrock', label: 'skin.12', swatch: ['#1a1a1a', '#a6a6a6', '#282828'] },
  { cid: 13, file: 's13-apple-silver-blue', label: 'skin.13', swatch: ['#e3e4e6', '#266cda', '#eff0f2'] },
  { cid: 14, file: 's14-blackgold-silentsea', label: 'skin.14', swatch: ['#202020', '#f0f0c0', '#2c2c2c'] },
  { cid: 15, file: 's15-cream-sunrise', label: 'skin.15', swatch: ['#f5edc8', '#483f36', '#fff9e3'] },
];
