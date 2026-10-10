/**
 * 青蔓 QingMan · 目录树右键菜单（V0.0.19）
 * 只管定位/开合/键盘导航，菜单项与动作由 main.js 每次打开时传入 —— 菜单本身零业务逻辑。
 * 文案走取词表（§P0-3），与工具栏按钮共用同一组键（tree.*）。
 */

const el = (id) => document.getElementById(id);

export function createContextMenu() {
  const menu = el('ctxMenu');
  let open = false;

  function close() {
    if (!open) return;
    open = false;
    menu.hidden = true;
    document.removeEventListener('click', onDocClick, true);
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', close);
    window.removeEventListener('blur', close);
  }

  function onDocClick(event) {
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

    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', close);
    window.addEventListener('blur', close);
    const first = menu.querySelector('button:not(:disabled)');
    if (first) first.focus();
  }

  return { showAt, close, get isOpen() { return open; } };
}
