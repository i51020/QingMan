/**
 * 青蔓 QingMan · 目录树右键菜单（V0.0.19）
 * 只管定位/开合/键盘导航，菜单项与动作由 main.js 每次打开时传入 —— 菜单本身零业务逻辑。
 * 文案走取词表（§P0-3），与工具栏按钮共用同一组键（tree.*）。
 *
 * V0.0.51 · 第 4 条修复「菜单关不掉」。旧实现的关闭时机只有四种 ——
 * `click`(捕获) / `Esc` / `resize` / `blur`，**漏掉的三类有一个共同点：都不产生 `click`**：
 *   ① **再按一次右键** —— 右键只发 `contextmenu`、**不发 `click`**，故在已打开的菜单上
 *      再按右键毫无反应（用户报的「关不掉」主因）；
 *   ② **滚动页面** —— 菜单是 `position: fixed`（见 `layout.css` 的 `.ctx-menu`），
 *      滚动不会让它跟随，只会悬在原地错位，必须关掉而不是留着；
 *   ③ **按下左键起拖** —— 树节点支持拖拽，而拖拽**不产生 `click`**，菜单同样会赖着不走。
 * 故补齐 `contextmenu` / `pointerdown`（均捕获）与 `scroll`（**必须捕获**：`scroll` 不冒泡，
 * 只有捕获阶段能收到内部滚动容器的滚动）。三类共用**同一判据**「目标不在菜单内则关」，
 * 与既有的点击判据合并为 `closeIfOutside` —— **关闭语义只有一个出口**。
 *
 * V0.2.2 修复「右键菜单关不掉」：JS 一直在设 `hidden = true`，但 CSS 的
 * `.ctx-menu { display: flex }` 压过了 UA 的 `[hidden]`，**视觉上从未消失**。
 * 根因在样式（已补 `.ctx-menu[hidden]`），本文件同时补三种符合直觉的关闭方式：
 *   ① **在菜单上再右键一次** —— 与 Windows 资源管理器一致（用户最常试的那一下）；
 *   ② **滚轮** —— 菜单是 `position: fixed`，滚动不会让它跟手，留着只会错位；
 *   ③ **焦点移出** —— 键盘 Tab 走开时菜单不该赖着（无障碍）。
 */

const el = (id) => document.getElementById(id);

export function createContextMenu() {
  const menu = el('ctxMenu');
  let open = false;

  function close() {
    if (!open) return;
    open = false;
    menu.hidden = true;
    document.removeEventListener('click', closeIfOutside, true);
    document.removeEventListener('contextmenu', closeIfOutside, true);
    document.removeEventListener('pointerdown', closeIfOutside, true);
    document.removeEventListener('scroll', close, true);
    document.removeEventListener('wheel', closeIfOutside, true);
    document.removeEventListener('focusin', closeIfOutside, true);
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', close);
    window.removeEventListener('blur', close);
  }

  function closeIfOutside(event) {
    if (!menu.contains(event.target)) close();
  }

  function onKey(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    const items = [...menu.querySelectorAll('button:not(:disabled)')];
    if (!items.length) return;
    event.preventDefault();
    const index = items.indexOf(document.activeElement);
    let next;
    if (event.key === 'ArrowDown') next = index < 0 ? 0 : (index + 1) % items.length;
    else next = index <= 0 ? items.length - 1 : index - 1;
    items[next].focus();
  }

  /**
   * @param {number} x y 视口坐标（contextmenu 的 clientX/Y）
   * @param {Array<{label:string, danger?:boolean, disabled?:boolean, action:Function}>} items
   */
  function showAt(x, y, items) {
    menu.textContent = '';
    for (const item of items) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('role', 'menuitem');
      btn.className = 'ctx-item' + (item.danger ? ' is-danger' : '');
      btn.textContent = item.label;
      btn.disabled = Boolean(item.disabled);
      btn.addEventListener('click', () => {
        close();
        if (typeof item.action === 'function' && !item.disabled) item.action();
      });
      menu.appendChild(btn);
    }

    menu.hidden = false;
    open = true;
    // 先临时展开量尺寸，再按视口边界翻转，防止贴边溢出
    menu.style.left = '0px';
    menu.style.top = '0px';
    const rect = menu.getBoundingClientRect();
    const left = Math.min(x, window.innerWidth - rect.width - 8);
    const top = Math.min(y, window.innerHeight - rect.height - 8);
    menu.style.left = `${Math.max(8, left)}px`;
    menu.style.top = `${Math.max(8, top)}px`;

    document.addEventListener('click', closeIfOutside, true);
    document.addEventListener('contextmenu', closeIfOutside, true);
    document.addEventListener('pointerdown', closeIfOutside, true);
    document.addEventListener('scroll', close, true);
    /* V0.2.2：滚轮只关「在菜单外」的；焦点移到菜单外（Tab）也关。均捕获，
       因为两种事件都不保证冒泡到 document。 */
    document.addEventListener('wheel', closeIfOutside, true);
    document.addEventListener('focusin', closeIfOutside, true);
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', close);
    window.addEventListener('blur', close);
    const first = menu.querySelector('button:not(:disabled)');
    if (first) first.focus();
  }

  /* 常驻监听（只注册一次）：在菜单上再右键一次 = 关掉它。
     不放在 showAt 里，否则每开一次就叠一个监听。
     `preventDefault()` 是必须的 —— 否则浏览器原生菜单会同时弹出，看起来像「没反应」。 */
  menu.addEventListener('contextmenu', (event) => {
    event.preventDefault();
    close();
  });

  return { showAt, close, get isOpen() { return open; } };
}
