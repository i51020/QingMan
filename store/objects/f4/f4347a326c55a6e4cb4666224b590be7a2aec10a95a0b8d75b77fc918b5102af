/**
 * 青蔓 QingMan · 自绘悬停提示（V0.0.51@r4 · UI 改版九条第 7 条）
 *
 * 为什么自绘：浏览器原生 title 浮标约 1 秒才出现、强制单行、字号与配色不可控，
 * 而本项目按钮提示多为整句说明（最长一句 30+ 字），靠原生浮标根本读不完。
 *
 * 数据源仍是 title —— `data-i18n-title` 经 applyStatic 写入 title，本模块只读取取值、
 * 不改写取值，故取词机制、无障碍语义（aria-label 独立存在）、以及 verify.py 的
 * 「顶栏图标按钮须有 tooltip」守卫均不受影响。
 *
 * 抑制原生浮标的办法：悬停期间把 title **临时转移**到模块内的 WeakMap（DOM 不留痕迹），
 * 离开即回填 —— 若期间 title 已被 applyStatic 重设（正好在切语言），回填时让位给现值、
 * 不覆盖，故语言切换与提示不会互相踩。WeakMap 也让「摘除后如何再认领同一元素」有据可依。
 *
 * 单例浮层 + 事件委托：不逐按钮绑定，日后新增按钮自动获得提示。
 */

const SHOW_DELAY = 180;   // 出现延迟：过滤「鼠标划过一排按钮」时的连闪；移开则立即消失
const GAP = 8;            // 浮层与宿主之间的间距
const MARGIN = 6;         // 浮层与视口边缘的安全边距

let tip = null;
let host = null;
let pending = null;              // 已进入但仍在延迟窗口内的宿主（尚未显示）
let timer = 0;
let installed = false;
const stashed = new WeakMap();   // 宿主 → 被临时摘下的 title 文本

function ensureTip() {
  if (tip) return tip;
  tip = document.createElement('div');
  tip.className = 'qm-tip';
  tip.setAttribute('role', 'tooltip');
  document.body.appendChild(tip);
  return tip;
}

/** 读宿主的提示文本；title 可能已被本模块摘除，故先查缓存。 */
function textOf(node) {
  const raw = stashed.has(node) ? stashed.get(node) : node.getAttribute('title');
  return raw && raw.trim() ? raw.trim() : '';
}

/** 沿目标向上找最近的「有提示文本」的元素；已被摘除 title 的宿主用缓存认领。 */
function pick(node) {
  if (!node || !node.closest) return null;
  const hit = node.closest('[title]');
  if (hit && textOf(hit)) return hit;
  for (let n = node; n && n !== document.documentElement; n = n.parentElement) {
    if (stashed.has(n) && textOf(n)) return n;
  }
  return null;
}

/** 定位：默认贴宿主下方居中；下方空间不足则翻到上方，水平方向夹在视口内。 */
function place(node) {
  const r = node.getBoundingClientRect();
  const w = tip.offsetWidth;
  const h = tip.offsetHeight;
  let top = r.bottom + GAP;
  let below = true;
  if (top + h > window.innerHeight - MARGIN) {
    if (r.top - GAP - h >= MARGIN) { top = r.top - GAP - h; below = false; }
    else top = Math.max(MARGIN, window.innerHeight - MARGIN - h);
  }
  const half = w / 2;
  const minLeft = Math.min(half + MARGIN, window.innerWidth / 2);
  const maxLeft = Math.max(window.innerWidth - half - MARGIN, window.innerWidth / 2);
  let left = r.left + r.width / 2;
  left = Math.min(Math.max(left, minLeft), maxLeft);
  tip.style.left = Math.round(left) + 'px';
  tip.style.top = Math.round(top) + 'px';
  tip.classList.toggle('is-below', below);
}

function reveal(node) {
  const text = textOf(node);
  if (!text) return;
  clearTimeout(timer);
  timer = 0;
  pending = null;
  host = node;
  if (!stashed.has(node)) stashed.set(node, node.getAttribute('title') || text);
  node.removeAttribute('title');          // 抑制原生浮标（否则与自绘浮层同时出现）
  ensureTip();
  tip.textContent = text;
  tip.classList.add('is-on');
  place(node);
}

function dismiss() {
  clearTimeout(timer);
  timer = 0;
  pending = null;
  if (tip) tip.classList.remove('is-on');
  if (!host) return;
  const text = stashed.get(host);
  stashed.delete(host);
  // 让位给现值：期间若 applyStatic 已把新文案写回 title，则不回填旧文本
  if (text != null && !host.hasAttribute('title')) host.setAttribute('title', text);
  host = null;
}

/* ---------- 事件：一律委托到 document，零逐元素绑定 ---------- */

function onPointerOver(event) {
  const node = pick(event.target);
  if (!node) { dismiss(); return; }                 // 移到无提示处：收起并取消待显示
  if (node === host) return;                        // 已显示：保持
  if (node === pending) return;                     // 待显示且同一宿主：保持计时，别重来
  dismiss();
  pending = node;
  timer = setTimeout(() => reveal(node), SHOW_DELAY);
}

function onPointerOut(event) {
  const to = event.relatedTarget;
  // 锚点取「已显示宿主」或「待显示宿主」：在延迟窗口内离开同样要取消这一枪 ——
  // 否则浮层会在鼠标早已移开之后凭空冒出（行为探针 t3 抓到的正是这一条）。
  const anchor = host || pending;
  if (anchor && to && anchor.contains(to)) return;  // 仍在宿主体内（含其子元素）
  dismiss();
}

function onFocusIn(event) {
  const node = pick(event.target);
  if (!node || node === host) return;
  /* V0.2.3：**只有键盘可见焦点才提示**。
     旧实现对所有 focusin 立即 reveal —— 而弹层打开时会把焦点放到关闭按钮上（程序化 focus），
     于是"打开窗口就自己冒出一个『关闭』提示"，用户看到的是「提示提前显示」。
     `:focus-visible` 正好区分两者：Tab 到按钮为真（无障碍要保留），
     程序化 focus / 鼠标点击产生的 focus 为假（不该弹提示）。
     取不到该伪类（极老引擎）时按「不显示」处理 —— 宁可少提示，也不要乱提示。 */
  let visible = false;
  try { visible = node.matches(':focus-visible'); } catch (err) { visible = false; }
  if (!visible) return;
  dismiss();
  reveal(node);
}

function onKeyDown(event) {
  if (event.key === 'Escape' && host) dismiss();
}

/** 装配：须在 applyStatic 之后调用（title 值此时已由取词写入）。幂等。 */
export function installTooltips() {
  if (installed) return;
  installed = true;
  ensureTip();
  document.addEventListener('pointerover', onPointerOver, true);
  document.addEventListener('pointerout', onPointerOut, true);
  document.addEventListener('focusin', onFocusIn, true);
  document.addEventListener('focusout', () => dismiss(), true);
  document.addEventListener('pointerdown', () => dismiss(), true);   // 点击即收，免挡弹层
  document.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('scroll', () => dismiss(), true);          // 捕获：任意滚动容器
  window.addEventListener('resize', () => dismiss());
  window.addEventListener('blur', () => dismiss());
}
