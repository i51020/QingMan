/**
 * 青蔓 QingMan · 后端调用封装
 * 所有网络请求集中在此，其余模块不直接使用 fetch。
 * 文案一律经取词表（§P0-3 L1），本文件不直写任何用户可见文案。
 */

import { t } from '../i18n/index.js';

const BASE = window.location.origin;

/**
 * 默认请求头。
 * `X-QingMan` 是服务端的写操作防护头（见 docs/项目约定.md N1）：
 * 跨站页面无法在不触发 CORS 预检的前提下携带自定义头，而本服务不响应预检，
 * 因此该头可阻断跨站盲发 POST。同源请求携带自定义头不触发预检，正常可用。
 */
const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'X-QingMan': '1',
};

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { ...DEFAULT_HEADERS, ...(options.headers || {}) },
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch (err) {
    throw new Error(t('api.nonJson', { status: res.status }));
  }

  if (!res.ok || payload.ok === false) {
    const detail = payload && payload.message ? payload.message : `HTTP ${res.status}`;
    const error = new Error(detail);
    error.code = payload && payload.code ? payload.code : 'httpError';
    error.detail = payload && payload.detail ? payload.detail : {};
    throw error;
  }
  return payload;
}

export const api = {
  health() {
    return request('/api/health', { method: 'GET' });
  },

  generate(tree, { target, root, dryRun }) {
    return request('/api/generate', {
      method: 'POST',
      body: JSON.stringify({ tree, target, root, dryRun }),
    });
  },

  /** 读取编辑态文档。doc 为 null 表示尚无文档，调用方回落到默认示例。 */
  loadDoc() {
    return request('/api/editor', { method: 'GET' });
  },

  /** 保存编辑态文档。服务端会重新校验结构，非法内容拒写。 */
  saveDoc(doc) {
    return request('/api/editor', {
      method: 'PUT',
      body: JSON.stringify({ doc }),
    });
  },

  /**
   * 创建桌面快捷方式。
   * 成功直写桌面 → { ok: true, path };
   * 桌面不可写 → { ok: true, fallback: true, name, data(base64) }，由调用方触发下载。
   */
  createShortcut() {
    return request('/api/shortcut', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },
};
