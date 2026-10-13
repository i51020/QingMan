/**
 * 青蔓 QingMan · 弹层基元（V0.0.40）
 *
 * modal 与 popover 共用**一套**行为，只差三件事：遮罩、焦点焦点陷阱的落点、定位方式。
 *   - modal   ：居中 + 遮罩 + 焦点陷阱 + `#app` 置 inert（背景不可点）
 *   - popover ：贴触发器下沿 + 无遮罩 + 点外部关闭
 *
 * 为什么把开合收进一个模块：设计稿里「右上角 × / Esc / 点遮罩」三条关闭路径必须
 * 走**同一条**接线，否则很容易出现「× 能关、Esc 关不掉」这类各写各的偏差。
 * 本模块只做「开合 / 定位 / 焦点」，**不含任何业务**；弹层内容与动作由调用方提供。
 *
 * 文案不在本模块：aria-label 等一律走页面的 `data-i18n`（§P0-3 L1）。
 */

const el = (id) => document.getElementById(id);

/** 可聚焦元素；`[tabindex="-1"]` 与 disabled 一律排除。 */
function focusables(node) {
  return [...node.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), '
    + 'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((n) => n.offsetParent !== null || n === document.activeElement);
}

/**
 * 锚定定位：贴触发器下沿、与其右缘对齐，并夹在视口内。
 * 宽度由调用方给出（弹层尚未显示时量不到自身宽度，只能由调用方声明）。
 */
export function placeUnder(trigger, node, width) {
  const rect = trigger.getBoundingClientRect();
  node.style.top = `${rect.bottom + 6}px`;
  node.style.left = `${Math.max(8, rect.right - width)}px`;
}

export function createLayerManager() {
  const scrim = el('scrim');
  const app = el('app');
  const stack = [];
  let triggers = [];
  let lastFocus = null;

  const isPopover = (node) => node.classList.contains('popover');

  /* 强制重排后再挂 is-open —— 不依赖 rAF（无头 / 虚拟时间下不可靠）。
     同时用 __hideT 清掉未决的关闭定时器，避免「快速重开被上一次的关闭回调吃掉」。 */
  function show(node) {
    if (node.__hideT) { clearTimeout(node.__hideT); node.__hideT = 0; }
    node.hidden = false;
    void node.offsetWidth;
    node.classList.add('is-open');
  }

  function hide(node, delay) {
    node.classList.remove('is-open');
    if (node.__hideT) clearTimeout(node.__hideT);
    node.__hideT = setTimeout(() => { node.hidden = true; node.__hideT = 0; }, delay);
  }

  function markTriggers(next) {
    for (const node of triggers) {
      if (node.hasAttribute && node.hasAttribute('aria-expanded')) {
        node.setAttribute('aria-expanded', 'false');
      }
    }
    triggers = next ? [next] : [];
  }

  /** 打开弹层。触发器可缺省；缺省时焦点归还给打开前的活跃元素。 */
  function open(node, trigger) {
    if (!node) return;
    closeAll(true);
    lastFocus = trigger || document.activeElement;
    markTriggers(trigger);
    show(node);

    if (!isPopover(node)) {
      show(scrim);
      app.setAttribute('inert', '');
    }
    if (trigger && trigger.hasAttribute('aria-expanded')) {
      trigger.setAttribute('aria-expanded', 'true');
    }
    const first = node.querySelector('[data-autofocus]') || focusables(node)[0] || node;
    setTimeout(() => { try { first.focus(); } catch (err) { /* 焦点失败不阻断开合 */ } }, 30);
    stack.push(node);
  }

  /**
   * 关闭全部弹层。
   * @param {boolean} silent 为 true 时不归还焦点 —— 供「开另一个弹层前先清场」使用，
   *                         否则焦点会先跳回旧触发器再跳到新弹层，屏幕阅读器会读两次。
   */
  function closeAll(silent) {
    const returnFocus = silent !== true;
    for (const node of [...stack]) {
      hide(node, isPopover(node) ? 140 : 170);
    }
    stack.length = 0;
    hide(scrim, 170);
    app.removeAttribute('inert');
    markTriggers(null);
    if (returnFocus && lastFocus && lastFocus.focus) {
      try { lastFocus.focus(); } catch (err) { /* 焦点丢失不阻断关闭 */ }
    }
    lastFocus = null;
  }

  /** 焦点陷阱：只在最上层弹层内循环 Tab / Shift+Tab。 */
  function trapTab(event) {
    if (event.key !== 'Tab' || !stack.length) return;
    const top = stack[stack.length - 1];
    const list = focusables(top);
    if (!list.length) return;
    const first = list[0];
    const last = list[list.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  if (scrim) scrim.addEventListener('click', () => closeAll());

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && stack.length) {
      event.preventDefault();
      closeAll();
      return;
    }
    trapTab(event);
  });

  // 统一接线：任何 [data-close] 元素都关闭所属层（右上角 ×）。
  document.addEventListener('click', (event) => {
    const hit = event.target.closest ? event.target.closest('[data-close]') : null;
    if (hit) closeAll();
  });

  // popover 点外部关闭：触发器与弹层自身之外一律关闭。
  document.addEventListener('click', (event) => {
    const top = stack.length ? stack[stack.length - 1] : null;
    if (!top || !isPopover(top)) return;
    if (top.contains(event.target)) return;
    if (triggers.some((node) => node.contains(event.target))) return;
    closeAll();
  });

  return {
    open,
    closeAll,
    isOpen: () => stack.length > 0,
    isOpenNode: (node) => stack.includes(node) && !node.hidden,
  };
}
