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

  /** 读取当前绑定的模板目录与元信息（V0.0.38 · 6E）。**只读**。 */
  templatesDir() {
    return request('/api/templates-dir', { method: 'GET' });
  },

  /**
   * 绑定模板目录（V0.0.38 · 6E）。服务端会拒自绑 / 拒系统区 / 实测可写后才落盘；
   * 被 `QM_TEMPLATES_DIR` 环境变量覆盖时返回 `applied=false`，调用方据此提示。
   */
  setTemplatesDir(dir) {
    return request('/api/templates-dir', {
      method: 'PUT',
      body: JSON.stringify({ dir }),
    });
  },

  /**
   * 弹原生目录选择框并**只回报所选路径**（V0.0.38 · 6E），不落盘、不绑定。
   * `available=false` = 本机用不了原生框（缺 tkinter / 无 GUI / env 关断）→ 调用方
   * 降级为「手动粘贴路径」；`cancelled=true` = 用户取消。
   */
  pickTemplatesDir() {
    return request('/api/templates-dir/pick', { method: 'POST', body: '{}' });
  },

  /**
   * 请求系统打开青蔓自己的某个目录（V0.0.51@r7 · 服务设置）。
   * `target` 只接受枚举标识 `'project' | 'data' | 'templates'` —— 后端查表定位，
   * **不接收任意路径**（白名单是结构性的，路径穿越无从谈起）。
   * 响应 `available=false` 时按 `reason` 区分：`disabled`（env 关断）/
   * `missing`（目录尚未创建）/ `unavailable`（系统打不开）—— 三种都由调用方就地说明。
   */
  openDir(target) {
    return request('/api/open-dir', {
      method: 'POST',
      body: JSON.stringify({ target }),
    });
  },

  /**
   * 导入一套模板（后端 V0.0.36 · 6C，前端接线 V0.0.38 · 6E）：上传 `.json` / `.md`
   * 内容，服务端按扩展名分派解析 + `validate_template` 全量校验后落盘；
   * `overwrite` 为真时同名旧模板先移入 `templates/.trash/`。
   */
  importTemplate(payload) {
    return request('/api/templates/import', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * 导出模板**原文**（V0.0.38 · 6E）：返回盘上那份文件的文本（`text`）与原文件名
   * （`file`）。由调用方按扩展名触发下载 —— 内容不在前端二次序列化，
   * 后端那份才是真源，故「导出 → 再导入」与原件一致。
   */
  exportTemplate(name) {
    return request('/api/templates-export/' + encodeURIComponent(name), { method: 'GET' });
  },

  /**
   * 列出可恢复的历史版本（V0.0.51@r9）。**只读**。
   * 返回 `{ dir, keep, backups: [{ id, name, archived, bytes, savedAt, rootName, broken }] }`，
   * 按新→旧排序。`id` 是相对 `data/.bak/` 的路径，**同时是恢复请求的标识**；
   * `archived=true` 表示已轮转进 `.bak/.trash/`（软删除件，同样可恢复）；
   * `broken=true` 表示文件读不出（仍列出，让用户知道它存在，但恢复会被挡下）。
   */
  listEditorBackups() {
    return request('/api/editor-backups', { method: 'GET' });
  },

  /**
   * 把某个历史版本恢复为当前版本（V0.0.51@r9）。**是写操作**。
   * `id` 须来自 `listEditorBackups()` 的枚举结果（后端按白名单比对，不接任意路径）。
   * 成功返回带 `restored: { id, name, rootName }`；旧当前版已先自动进 `.bak/`，
   * 故**恢复本身也可回退**。
   */
  restoreEditor(id) {
    return request('/api/editor-restore', {
      method: 'POST',
      body: JSON.stringify({ id }),
    });
  },
};
