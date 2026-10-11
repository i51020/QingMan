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
  let res;
  try {
    res = await fetch(BASE + path, {
      ...options,
      headers: { ...DEFAULT_HEADERS, ...(options.headers || {}) },
    });
  } catch (cause) {
    // B-P3-1：网络层失败（服务未起 / 连接被拒 / DNS）会抛 **裸 `TypeError`**，它没有
    // `code` → `localizeError` 只能回落到浏览器原文（"Failed to fetch"，且是英文）。
    // 归一成带 `code` 的错误，走与 HTTP 错误同一条本地化通道。
    const error = new Error('networkError');
    error.code = 'networkError';
    error.detail = { path, message: String((cause && cause.message) || cause) };
    console.warn('[QingMan] network failed:', error.detail);
    throw error;
  }

  let payload = null;
  try {
    payload = await res.json();
  } catch (err) {
    throw new Error(t('api.nonJson', { status: res.status }));
  }

  if (!res.ok || payload.ok === false) {
    const fallback = `HTTP ${res.status}`;
    const error = new Error(payload && payload.message ? payload.message : fallback);
    error.code = payload && payload.code ? payload.code : 'httpError';
    // status 一并入 detail：本地化时 err.httpError 的 {status} 才有值可填
    error.detail = { ...(payload && payload.detail ? payload.detail : {}), status: res.status };
    // 控制台留痕：错误码是稳定标识，便于技术排查（界面上另有徽标）
    console.warn('[QingMan] request failed:', error.code, error.detail);
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
   * 成功直写桌面 → { ok: true, path }；icon=true 表示已写入皮肤联动图标。
   * 桌面不可写 → { ok: true, fallback: true, name, data(base64) }，由调用方触发下载。
   * icon 参数（base64 ICO）可选：由 launch-icon.js 按当前皮肤绘制。
   */
  createShortcut(icon) {
    return request('/api/shortcut', {
      method: 'POST',
      body: JSON.stringify(icon ? { icon } : {}),
    });
  },

  /** 上传皮肤联动启动图标（base64 ICO，V0.0.15），落盘 data/qm-launch.ico。 */
  saveLaunchIcon(payload) {
    return request('/api/launch-icon', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * 列出模板库。
   * `available=false` 表示 templates/ 不存在（预览副本中没有它），
   * 此时 items 为空 —— 调用方应显示「不可用」，而不是报网络错。
   */
  listTemplates() {
    return request('/api/templates', { method: 'GET' });
  },

  /** 读取单套模板的完整树。name 为模板文件名（含中文，需编码）。 */
  loadTemplate(name) {
    return request('/api/templates/' + encodeURIComponent(name), { method: 'GET' });
  },

  /**
   * 另存为模板：把当前目录树写进 templates/<name>.json（V0.0.13）。
   * 服务端**拒绝覆盖同名模板**（返回 templateExists），由调用方提示改名。
   */
  saveTemplate(payload) {
    return request('/api/templates', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * 重命名模板（V0.0.20）。name 为旧文件名（含中文，需编码）；
   * 服务端同时改文件名与文件内 name 字段，目标已存在返回 templateExists。
   */
  renameTemplate(name, nextName) {
    return request('/api/templates/' + encodeURIComponent(name), {
      method: 'POST',
      body: JSON.stringify({ name: nextName }),
    });
  },

  /** 删除模板（V0.0.20，服务端软删除入 templates/.trash/）。 */
  deleteTemplate(name) {
    return request('/api/templates/' + encodeURIComponent(name), { method: 'DELETE' });
  },
};
