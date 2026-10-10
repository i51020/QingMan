/**
 * 青蔓 QingMan · 皮肤联动启动图标（V0.0.15）
 *
 * 桌面快捷方式图标的配色**跟随当前皮肤**：
 *   - 色值单一事实源 = tokens.css / skins/*.css 的 --qm-* 变量（getComputedStyle 实取），
 *     本模块不镜像任何调色板 —— 换肤后重绘即得新配色，皮肤与图标永不失同步。
 *   - 字形 = logo.svg 的 path（Path2D 上色）；底板 = --qm-surface；
 *     字形色 = --qm-accent，对比度 < 3:1（非文本门槛）时回退 --qm-text。
 *   - 产物 = 16/32/48/256 四档 PNG-in-ICO，POST /api/launch-icon 落盘 data/qm-launch.ico。
 *
 * 纯逻辑（buildIco / parseLogoSvg / contrastRatio）不碰 DOM/canvas，
 * 便于 Node 侧用同一份代码做往返验证。
 */

import { api } from '../core/api.js';

/** ICO 收录的边长档位（Windows 桌面常用 + 256 大图）。 */
const ICON_SIZES = [16, 32, 48, 256];

/** 底板圆角半径比例（相对边长）；与顶栏 logo 的视觉气质一致。 */
const PLATE_RADIUS_RATIO = 0.18;

/** 字形对底板的留白比例（每边）。 */
const GLYPH_MARGIN_RATIO = 0.16;

/** 对比度门槛（WCAG 非文本元素 3:1）：字形色对底板不达标时回退正文色。 */
const CONTRAST_FLOOR = 3.0;

/* ---------- 纯逻辑：色值与对比度 ---------- */

/** 解析 #rgb / #rrggbb / #rrggbbaa → [r,g,b]（0-255）；不认识返回 null。 */
export function parseHexColor(text) {
  const s = String(text || '').trim();
  const m = /^#([0-9a-fA-F]{3,8})$/.exec(s);
  if (!m) return null;
  const hex = m[1];
  if (hex.length === 3 || hex.length === 4) {
    return [0, 1, 2].map((i) => parseInt(hex[i] + hex[i], 16));
  }
  if (hex.length === 6 || hex.length === 8) {
    return [0, 1, 2].map((i) => parseInt(hex.slice(i * 2, i * 2 + 2), 16));
  }
  return null;
}

/** 相对亮度（WCAG 定义）。输入 [r,g,b]。 */
export function relativeLuminance(rgb) {
  const chan = rgb.map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
}

/** 对比度（1..21）。任一输入非法返回 0（调用方按「不达标」处理）。 */
export function contrastRatio(a, b) {
  if (!a || !b) return 0;
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const hi = Math.max(la, lb);
  const lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * 从 svg 文本里取第一个 <path> 的 d 与整个 svg 的 viewBox。
 * 返回 { d, viewBox: [x, y, w, h] }；解析失败返回 null。
 */
export function parseLogoSvg(svgText) {
  const dMatch = /<path[^>]*\sd="([^"]+)"/.exec(String(svgText || ''));
  if (!dMatch) return null;
  const vbMatch = /viewBox="([^"]+)"/.exec(String(svgText || ''));
  if (!vbMatch) return null;
  const parts = vbMatch[1].trim().split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n)) || parts[2] <= 0 || parts[3] <= 0) {
    return null;
  }
  return { d: dMatch[1], viewBox: parts };
}

/* ---------- 纯逻辑：PNG-in-ICO 组包 ---------- */

/**
 * 把若干 PNG 组成一个 ICO 文件字节流（PNG-in-ICO，Vista+ 支持）。
 * 入参为 [{ size, bytes }]；size 是该帧的边长（256 在目录项里编码为 0）。
 * 返回 Uint8Array。纯数据操作，无 DOM 依赖。
 */
export function buildIco(frames) {
  const entries = frames.map((f) => ({ size: f.size, bytes: new Uint8Array(f.bytes) }));
  const count = entries.length;
  let offset = 6 + 16 * count;
  const total = offset + entries.reduce((sum, e) => sum + e.bytes.length, 0);
  const out = new Uint8Array(total);
  const view = new DataView(out.buffer);
  view.setUint16(0, 0, true);        // reserved
  view.setUint16(2, 1, true);        // type = icon
  view.setUint16(4, count, true);    // 目录项数
  let head = 6;
  let body = offset;
  for (const entry of entries) {
    view.setUint8(head, entry.size === 256 ? 0 : entry.size);   // 256 编码为 0
    view.setUint8(head + 1, 0);               // 高度同宽（正方形档位）
    view.setUint8(head + 2, 0);               // 色彩数（PNG 不适用）
    view.setUint8(head + 3, 0);               // 保留
    view.setUint16(head + 4, 1, true);        // color planes
    view.setUint16(head + 6, 32, true);       // bits per pixel
    view.setUint32(head + 8, entry.bytes.length, true);
    view.setUint32(head + 12, body, true);
    out.set(entry.bytes, body);
    head += 16;
    body += entry.bytes.length;
  }
  return out;
}

/* ---------- DOM/canvas 侧 ---------- */

/** 读 --qm-accent / --qm-surface / --qm-text 的当前计算值（16/32 位 #hex）。 */
function readSkinColors() {
  const style = getComputedStyle(document.documentElement);
  const pick = (name) => parseHexColor(style.getPropertyValue(name));
  return { accent: pick('--qm-accent'), surface: pick('--qm-surface'), text: pick('--qm-text') };
}

/** 字形色：accent 对 surface 不足 3:1 时回退 text（守卫只兜底，皮肤正常时 accent 已达标）。 */
export function glyphColorFor({ accent, surface, text }) {
  if (accent && contrastRatio(accent, surface) >= CONTRAST_FLOOR) return accent;
  return text || accent;
}

let logoCache = null;

/** 取 logo 资产的 { d, viewBox }（带缓存；失败返回 null，调用方放弃主题化）。 */
async function loadLogo() {
  if (logoCache !== null) return logoCache;
  try {
    const res = await fetch('./assets/logo.svg', { cache: 'no-cache' });
    if (!res.ok) throw new Error(String(res.status));
    logoCache = parseLogoSvg(await res.text());
  } catch (err) {
    console.warn('[QingMan] logo.svg unavailable, themed icon skipped:', err);
    logoCache = null;
  }
  return logoCache;
}

/** 画一档尺寸的 PNG Blob（roundRect 兜底手绘，兼容旧实现）。 */
function drawFrame(ctx, size, logo, colors) {
  ctx.clearRect(0, 0, size, size);
  const r = size * PLATE_RADIUS_RATIO;
  ctx.fillStyle = `rgb(${colors.surface.join(',')})`;
  if (typeof ctx.roundRect === 'function') {
    ctx.beginPath();
    ctx.roundRect(0, 0, size, size, r);
    ctx.fill();
  } else {
    ctx.beginPath();
    ctx.moveTo(r, 0);
    ctx.arcTo(size, 0, size, size, r);
    ctx.arcTo(size, size, 0, size, r);
    ctx.arcTo(0, size, 0, 0, r);
    ctx.arcTo(0, 0, size, 0, r);
    ctx.closePath();
    ctx.fill();
  }

  const glyph = glyphColorFor(colors);
  const margin = size * GLYPH_MARGIN_RATIO;
  const box = size - margin * 2;
  const [vx, vy, vw, vh] = logo.viewBox;
  const scale = Math.min(box / vw, box / vh);
  const dw = vw * scale;
  const dh = vh * scale;
  const dx = margin + (box - dw) / 2;
  const dy = margin + (box - dh) / 2;
  ctx.save();
  ctx.translate(dx, dy);
  ctx.scale(scale, scale);
  ctx.translate(-vx, -vy);
  const path = new Path2D(logo.d);
  ctx.fillStyle = `rgb(${glyph.join(',')})`;
  ctx.fill(path);
  ctx.restore();
}

/** 生成当前皮肤配色的 ICO（Uint8Array）。任一环节失败返回 null（调用方走默认图标）。 */
export async function renderLaunchIcon() {
  const logo = await loadLogo();
  if (!logo) return null;
  const colors = readSkinColors();
  if (!colors.surface) return null;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  const frames = [];
  for (const size of ICON_SIZES) {
    canvas.width = size;
    canvas.height = size;
    drawFrame(ctx, size, logo, colors);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) return null;
    frames.push({ size, bytes: new Uint8Array(await blob.arrayBuffer()) });
  }
  return buildIco(frames);
}

/** 当前皮肤是否与上次上传的一致（避免每次换语言等无关操作都重传图标）。 */
let lastUploadedKey = '';

/** 生成并上传启动图标（data/qm-launch.ico）。失败静默 —— 图标是尽力而为的装饰。 */
export async function ensureLaunchIcon() {
  try {
    const colors = readSkinColors();
    const key = [colors.accent, colors.surface, colors.text]
      .map((c) => (c || []).join(',')).join('|');
    if (!colors.surface || key === lastUploadedKey) return;
    const ico = await renderLaunchIcon();
    if (!ico) return;
    let binary = '';
    const CHUNK = 0x8000;
    for (let i = 0; i < ico.length; i += CHUNK) {
      binary += String.fromCharCode.apply(null, ico.subarray(i, i + CHUNK));
    }
    const base64 = btoa(binary);
    await api.saveLaunchIcon({ data: base64 });
    lastUploadedKey = key;
  } catch (err) {
    console.warn('[QingMan] launch icon upload skipped:', err && err.code);
  }
}
