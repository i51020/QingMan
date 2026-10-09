/**
 * 青蔓 QingMan · 后端调用封装
 * 所有网络请求集中在此，其余模块不直接使用 fetch。
 */

const BASE = window.location.origin;

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch (err) {
    throw new Error(`后端返回非 JSON（HTTP ${res.status}）`);
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
};
