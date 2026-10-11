/**
 * 青蔓 QingMan · 轻提示
 * V0.0.32：加**同时显示数量上限**（C-P3-4）。
 */

const host = () => document.getElementById('toastHost');

/**
 * 同时最多保留的提示条数（C-P3-4）。
 *
 * 旧实现无上限：连续操作出错时（生成失败 + 保存失败 + 多条 warn 前后脚出现）
 * 提示条会一直往上堆，遮住右栏甚至整个窗口。超限时淘汰**最旧**的一条 ——
 * 保留最新信息（用户刚做的事最相关），且与「轮转备份保留最近 N 份」同向。
 */
const MAX_TOASTS = 4;

export function toast(message, type = 'info', timeout = 3200) {
  const box = host();
  if (!box) return;

  const item = document.createElement('div');
  item.className = 'toast' + (type === 'error' ? ' is-error' : type === 'warn' ? ' is-warn' : '');
  item.textContent = message;
  box.appendChild(item);

  /* 逐个淘汰最旧的，直到不超过上限（`querySelectorAll` 是静态列表，索引稳定）。 */
  const items = box.querySelectorAll('.toast');
  for (let i = 0; i < items.length - MAX_TOASTS; i += 1) items[i].remove();

  window.setTimeout(() => {
    item.remove();
  }, timeout);
}
