/**
 * 青蔓 QingMan · 轻提示
 */

const host = () => document.getElementById('toastHost');

export function toast(message, type = 'info', timeout = 3200) {
  const box = host();
  if (!box) return;

  const item = document.createElement('div');
  item.className = 'toast' + (type === 'error' ? ' is-error' : type === 'warn' ? ' is-warn' : '');
  item.textContent = message;
  box.appendChild(item);

  window.setTimeout(() => {
    item.remove();
  }, timeout);
}
