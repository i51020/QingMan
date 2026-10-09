/**
 * 青蔓 QingMan · 事件总线
 * 极简发布/订阅，模块之间只通过事件通信，不互相直接引用。
 */

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
    if (set) set.delete(handler);
  }

  function emit(type, payload) {
    const set = listeners.get(type);
    if (!set) return;
    for (const handler of Array.from(set)) {
      try {
        handler(payload);
      } catch (err) {
        console.error(`[bus] 事件 ${type} 的处理函数抛错：`, err);
      }
    }
  }

  return { on, off, emit };
}
