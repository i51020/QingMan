/**
 * 青蔓 QingMan · 状态仓库
 * 单一状态源。所有读取走 get()，所有写入走 set()，订阅走 subscribe()。
 */

import { createBus } from './bus.js';

export function createStore(initialState) {
  const bus = createBus();
  let state = { ...initialState };

  return {
    bus,

    get() {
      return state;
    },

    set(patch) {
      state = { ...state, ...patch };
      bus.emit('change', state);
      return state;
    },

    subscribe(handler) {
      return bus.on('change', handler);
    },
  };
}
