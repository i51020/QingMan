/* 青蔓 QingMan · 浏览器内演示后端（只由 tools/build_static_site.py 注入静态产物）
 *
 * 为什么需要它：线上演示没有 Python 后端。若 `/api/*` 全部 404，界面只能显示
 * 「后端未连接」—— 访客会以为站点坏了，而实际上这是「本地工具被搬到云上」的必然落差。
 * 这里用**同一套 HTTP 契约**在浏览器里实现一个只读 / 内存版后端：
 *
 *   能做：读健康状况、读写编辑态（localStorage）、内置空白模板、模板增删改（内存）
 *   不能做：任何磁盘写入 —— 浏览器没有这个能力，也不该有。相关动作一律给出明确说明。
 *
 * 约束：本文件**不在 `src/` 内**，与生产代码完全隔离；
 * 文案在这里自带中英两份，不依赖语言包（它在语言包加载完成前就要能用）。
 */
(function () {
  'use strict';

  var LS_DOC = 'qm.demo.editor';
  var LS_TPL = 'qm.demo.templates';
  var DEMO = window.__QM_DEMO__ || {};
  var VERSION = DEMO.version || 'V0.3.0';
  var P0 = DEMO.template || { file: 'P0_空白项目模板.json', name: '空白项目模板', description: '', tree: {} };

  var ZH = (navigator.language || 'zh').toLowerCase().indexOf('zh') === 0;
  var TEXT = {
    zh: {
      nameZh: '青蔓',
      dataDir: '浏览器本地存储（在线演示，不写磁盘）',
      tplPath: '在线演示模板库（不写磁盘）',
      noDisk: '在线演示版无法把目录写入你的磁盘。请在本机运行 start.bat 使用完整功能。',
      noExport: '在线演示版不支持该操作，请在本机运行 start.bat。',
      noRestore: '在线演示版没有历史版本记录。',
      badJson: '请求内容不是合法 JSON。',
      tplExists: '模板库里已有同名模板。',
    },
    en: {
      nameZh: 'QingMan',
      dataDir: 'Browser local storage (online demo, no disk access)',
      tplPath: 'Demo template library (no disk access)',
      noDisk: 'The online demo cannot write folders to your disk. Run start.bat locally for full features.',
      noExport: 'This action is unavailable in the online demo. Run start.bat locally.',
      noRestore: 'The online demo keeps no version history.',
      badJson: 'Request body is not valid JSON.',
      tplExists: 'A template with that name already exists.',
    },
  };
  function tr(key) { return (ZH ? TEXT.zh : TEXT.en)[key] || key; }

  /* ---------- 存储 ---------- */

  function readJson(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (err) {
      return fallback;
    }
  }
  function writeJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (err) {
      return false;   // 隐私模式 / 配额满：演示版降级为「不持久」
    }
  }

  function userTemplates() { return readJson(LS_TPL, {}); }

  function templateList() {
    var map = userTemplates();
    var items = [{
      file: P0.file, name: P0.name, description: P0.description || '',
      size: JSON.stringify(P0.tree || {}).length, mtime: 0, source: 'json',
    }];
    Object.keys(map).forEach(function (file) {
      var tpl = map[file] || {};
      items.push({
        file: file, name: tpl.name || file.replace(/\.[^.]+$/, ''),
        description: tpl.description || '',
        size: JSON.stringify(tpl.tree || {}).length, mtime: tpl.mtime || 0, source: 'json',
      });
    });
    return items;
  }

  function countTree(tree) {
    var dirs = 0; var files = 0;
    (function walk(node) {
      Object.keys(node || {}).forEach(function (key) {
        var value = node[key];
        if (value && typeof value === 'object') { dirs += 1; walk(value); }
        else { files += 1; }
      });
    })(tree);
    return { dirs: dirs, files: files };
  }

  /* ---------- 响应构造（与后端 _json/_fail 同形） ---------- */

  function ok(body) {
    return new Response(JSON.stringify(Object.assign({ ok: true }, body)), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }
  function fail(code, message, status) {
    return new Response(JSON.stringify({ ok: false, code: code, message: message || tr('noExport') }), {
      status: status || 400, headers: { 'Content-Type': 'application/json' },
    });
  }
  function bodyOf(init) {
    try { return JSON.parse((init && init.body) || '{}'); }
    catch (err) { return null; }
  }

  /* ---------- 各端点 ---------- */

  function handle(path, method, init) {
    /* 健康检查：让界面进入「已连接」，并把数据位置如实说成浏览器存储 */
    if (path === '/api/health' && method === 'GET') {
      return ok({
        app: 'QingMan', nameZh: tr('nameZh'), version: VERSION,
        dataDir: tr('dataDir'), osLocale: navigator.language || 'zh-CN',
      });
    }

    /* 编辑态：真实可持久（刷新不丢），只是落在 localStorage 而非磁盘 */
    if (path === '/api/editor' && method === 'GET') {
      return ok({ doc: readJson(LS_DOC, null), path: 'localStorage://' + LS_DOC });
    }
    if (path === '/api/editor' && method === 'PUT') {
      var payload = bodyOf(init);
      if (!payload) return fail('badJson', tr('badJson'));
      if (!payload.doc || !payload.doc.root) return fail('editorRootMissing', tr('noDisk'));
      var savedAt = new Date().toISOString().slice(0, 19);
      var persisted = writeJson(LS_DOC, {
        schemaVersion: 1, savedAt: savedAt, root: payload.doc.root,
      });
      return ok({
        path: 'localStorage://' + LS_DOC, savedAt: savedAt,
        bytes: JSON.stringify(payload.doc).length,
        stats: countTree(payload.doc.root.children ? {} : {}),
        backup: { ok: persisted, skipped: true },
        persisted: persisted,
      });
    }

    /* 历史版本：演示版不保留，如实返回空列表（不是错误） */
    if (path === '/api/editor-backups' && method === 'GET') {
      return ok({ dir: tr('dataDir'), keep: 0, backups: [] });
    }
    if (path === '/api/editor-restore') return fail('demoReadonly', tr('noRestore'));

    /* 模板库：内置空白模板 + 用户在线新增（都存在 localStorage） */
    if (path === '/api/templates' && method === 'GET') {
      return ok({
        available: true, items: templateList(),
        path: 'localStorage://' + LS_TPL, reason: '',
      });
    }
    if (path === '/api/templates' && method === 'POST') {
      var tplPayload = bodyOf(init);
      if (!tplPayload) return fail('badJson', tr('badJson'));
      var fileName = String(tplPayload.name || '').trim();
      if (!fileName) return fail('templateNameInvalid', tr('noExport'));
      if (!/\.[^.]+$/.test(fileName)) fileName += '.json';
      var map = userTemplates();
      if (map[fileName] && !tplPayload.overwrite) {
        return fail('templateExists', tr('tplExists'));
      }
      map[fileName] = {
        name: tplPayload.name, description: tplPayload.description || '',
        tree: tplPayload.tree || {}, mtime: Date.now(),
      };
      writeJson(LS_TPL, map);
      return ok({ file: fileName, name: tplPayload.name });
    }
    if (path.indexOf('/api/templates/') === 0 && path !== '/api/templates/import') {
      var rawName = decodeURIComponent(path.slice('/api/templates/'.length));
      if (method === 'GET') {
        if (rawName === P0.file) {
          var tree = P0.tree || {};
          return ok({
            file: P0.file, name: P0.name, description: P0.description || '',
            tree: tree, stats: countTree(tree), source: 'json', schemaVersion: 1,
          });
        }
        var got = userTemplates()[rawName];
        if (!got) return fail('templateNotFound', tr('noExport'), 404);
        return ok({
          file: rawName, name: got.name, description: got.description || '',
          tree: got.tree || {}, stats: countTree(got.tree || {}), source: 'json',
        });
      }
      if (method === 'DELETE') {
        var delMap = userTemplates();
        if (rawName === P0.file || !delMap[rawName]) return fail('templateNotFound', tr('noExport'), 404);
        delete delMap[rawName];
        writeJson(LS_TPL, delMap);
        return ok({ file: rawName });
      }
      if (method === 'POST') {
        var renamePayload = bodyOf(init) || {};
        var nextName = String(renamePayload.name || '').trim();
        var rmap = userTemplates();
        if (!rmap[rawName] || !nextName) return fail('templateNotFound', tr('noExport'), 404);
        if (!/\.[^.]+$/.test(nextName)) nextName += '.json';
        if (rmap[nextName]) return fail('templateExists', tr('tplExists'));
        rmap[nextName] = rmap[rawName];
        delete rmap[rawName];
        writeJson(LS_TPL, rmap);
        return ok({ file: nextName });
      }
    }

    /* 绑定目录 / 原生选择框 / 打开目录：演示版没有文件系统，静默降级 */
    if (path === '/api/templates-dir' && method === 'GET') {
      return ok({ dir: tr('tplPath'), source: 'demo', available: true, reason: '' });
    }
    if (path === '/api/templates-dir' && method === 'PUT') {
      return ok({ applied: false, dir: tr('tplPath'), reason: 'demo' });
    }
    if (path === '/api/templates-dir/pick' || path === '/api/open-dir') {
      return ok({ available: false, reason: 'demo' });
    }
    if (path === '/api/launch-icon') return ok({ skipped: true });

    /* 写盘 / 快捷方式 / 导入导出：明确说「演示版做不到」，而不是假装成功 */
    if (path === '/api/generate') return fail('demoNoDisk', tr('noDisk'));
    if (path === '/api/shortcut') return fail('demoNoDisk', tr('noDisk'));
    if (path === '/api/templates/import' || path.indexOf('/api/templates-export/') === 0) {
      return fail('demoReadonly', tr('noExport'));
    }

    /* 其余 /api/* 一律挡住：绝不因为漏配而真的打到静态托管的 404 页面上 */
    if (path.indexOf('/api/') === 0) return fail('demoUnsupported', tr('noExport'));
    return null;
  }

  /* ---------- 拦截 fetch（api.js 是唯一出口，故只需拦这一处） ---------- */

  var nativeFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!nativeFetch) return;

  window.fetch = function (input, init) {
    var url;
    try {
      url = typeof input === 'string' ? input : (input && input.url) || '';
    } catch (err) {
      url = '';
    }
    var path;
    try {
      path = new URL(url, window.location.href).pathname;
    } catch (err) {
      path = '';
    }
    if (path.indexOf('/api/') !== 0) return nativeFetch(input, init);
    var method = String(
      (init && init.method) || (input && input.method) || 'GET'
    ).toUpperCase();
    var hit = handle(path, method, init);
    if (hit) return Promise.resolve(hit);
    return nativeFetch(input, init);
  };

  window.__QM_DEMO_ACTIVE__ = true;
})();
