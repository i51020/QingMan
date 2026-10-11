/**
 * 青蔓 QingMan · 事件总线
 * 极简发布/订阅，模块之间只通过事件通信，不互相直接引用。
 */

import { t } from '../i18n/index.js';

export function createBus() {
  /** @type {Map<string, Set<Function>>} */
  const listeners = new Map();

  function on(type, handler) {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type).add(handler);
    return () => off(type, handler);
  }

  function off(type, handler) {
    const set = listeners.get(type);
    if (!set) return;
    set.delete(handler);
    // B-P3-6：最后一个监听器移除后把空 Set 一并删掉 —— 否则 `listeners` 里会长期
    // 残留空集合（每注册过一种事件就多一条），属极轻微内存滞留。
    if (set.size === 0) listeners.delete(type);
  }

  function emit(type, payload) {
    const set = listeners.get(type);
    if (!set) return;
    for (const handler of Array.from(set)) {
      try {
        handler(payload);
      } catch (err) {
        console.error(t('bus.handlerError', { type }), err);
      }
    }
  }

  return { on, off, emit };
}
