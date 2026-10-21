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
  var MD = window.QMDemoMd || null;
  var STORE = window.QMDemoStore || null;
  var P0 = DEMO.template || { file: 'P0_空白项目模板.json', name: '空白项目模板', description: '', tree: {} };

  var ZH = (navigator.language || 'zh').toLowerCase().indexOf('zh') === 0;
  var TEXT = {
    zh: {
      nameZh: '青蔓',
      dataDir: '浏览器本地存储（编辑草稿；生成时可直接写入你选择的文件夹）',
      tplPath: '在线版模板库（存浏览器）',
      noDisk: '在线版需要你授权选择保存位置后才能写入磁盘。若浏览器不支持（请用 Edge / Chrome），可在本机运行 start.bat。',
      noPermission: '没有拿到写入授权，未创建任何文件。',
      cancelled: '已取消选择保存位置，未创建任何文件。',
      noExport: '在线版不支持该操作，请在本机运行 start.bat。',
      noRestore: '在线版没有历史版本记录。',
      badJson: '请求内容不是合法 JSON。',
      tplExists: '模板库里已有同名模板。',
      pickHint: '（未选：点「选择…」，或生成时再选）',
      pickHintTitle: '浏览器不披露绝对路径，所以这里只显示文件夹名。点「选择…」选中的文件夹会被记住，生成时直接写进去；没选就在生成时再问一次。',
      targetTitle: '已记住这个文件夹：下次生成直接写到这里。要换位置再点「选择…」。',
      treeMissing: '目录树为空，没有可生成的内容。',
      tooMany: '节点太多（上限 500），请精简后再生成。',
      fsUnsupported: '当前浏览器不支持直接写入文件夹（请用 Edge / Chrome）。可以改用本机 start.bat。',
      usePwa: '在线版没有桌面快捷方式 —— 浏览器菜单里选「安装此应用 / 安装青蔓」，就会在桌面与开始菜单得到图标（还能离线使用）。',
      needPermission: '模板目录的读取权限已失效（浏览器在重启后常要求重新确认）。请点「选择目录」再授权一次。',
      dirMissing: '绑定的模板目录已不存在（可能被删除、改名或移动）。请点「选择目录」重新指定，或用「刷新」重试。',
      tplNeedWrite: '模板目录没有写入授权，模板没保存。请点「选择目录」再授权一次，并在弹框里允许修改。',
      tplWriteFail: '写入模板目录失败：{msg}',
      tplNameInvalid: '这个模板名不能当文件名（含 / \\ : * ? " < > | ，或以 .. 开头），请换一个。',
    },
    en: {
      nameZh: 'QingMan',
      dataDir: 'Browser local storage (drafts; generation writes to a folder you pick)',
      tplPath: 'Online template library (browser storage)',
      noDisk: 'The online version needs your permission to pick a folder before writing. If your browser is unsupported (use Edge / Chrome), run start.bat locally.',
      noPermission: 'Write permission was not granted; nothing was created.',
      cancelled: 'Folder selection cancelled; nothing was created.',
      noExport: 'This action is unavailable online. Run start.bat locally.',
      noRestore: 'The online version keeps no version history.',
      badJson: 'Request body is not valid JSON.',
      tplExists: 'A template with that name already exists.',
      pickHint: '(none yet — click Choose, or pick at generate time)',
      pickHintTitle: 'Browsers never reveal absolute paths, so only the folder name is shown. A folder picked with "Choose" is remembered and used directly on generate; otherwise you are asked at generate time.',
      targetTitle: 'This folder is remembered: the next generate writes here directly. Click "Choose" to change it.',
      treeMissing: 'The tree is empty; nothing to generate.',
      tooMany: 'Too many nodes (500 max). Trim the tree and retry.',
      fsUnsupported: 'This browser cannot write to folders directly (use Edge / Chrome), or run start.bat locally.',
      usePwa: 'The online version has no desktop shortcut — use your browser menu "Install app" to get an icon on the desktop and Start menu (it also works offline).',
      needPermission: 'Read access to the template folder expired (browsers usually re-ask after a restart). Click "Choose folder" and grant it again.',
      dirMissing: 'The bound template folder no longer exists (deleted, renamed or moved). Click "Choose folder" to pick it again, or press Refresh to retry.',
      tplNeedWrite: 'The template folder has no write permission, so nothing was saved. Click "Choose folder" again and allow editing.',
      tplWriteFail: 'Failed to write into the template folder: {msg}',
      tplNameInvalid: 'That name cannot be used as a file name (it contains / \\ : * ? " < > | or starts with ..). Pick another.',
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
    /* 内置示例恒居首（它不是用户文件）；其余与**目录分支同口径**排序。
       排序规则只写在 `online-store.byFile` 一处，此处调用、不复制 —— 两条分支顺序
       若各写一套，迟早又会不一致。 */
    if (items.length > 1 && STORE && typeof STORE.sortByFile === 'function') {
      return [items[0]].concat(STORE.sortByFile(items.slice(1)));
    }
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
  function fail(code, message, status, detail) {
    var body = { ok: false, code: code, message: message || tr('noExport') };
    /* **必须带 detail**：前端 `localizeError()` 只认 `code` + `detail`，用取词表的
       `err.<code>` 重新成句。缺 `detail` 时占位符不会被替换，用户会看到字面量
       「模板不存在：{name}」—— 2026-10-21 用户报障里那句正是这么来的。 */
    if (detail) { body.detail = detail; }
    return new Response(JSON.stringify(body), {
      status: status || 400, headers: { 'Content-Type': 'application/json' },
    });
  }
  /* base64 ICO → 浏览器下载（在线版没有快捷方式可挂，只能把文件交给用户） */
  function downloadIco(base64) {
    try {
      var bin = atob(base64);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i += 1) { bytes[i] = bin.charCodeAt(i); }
      var url = URL.createObjectURL(new Blob([bytes], { type: 'image/x-icon' }));
      var a = document.createElement('a');
      a.href = url;
      a.download = 'qingman-launch.ico';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 0);
    } catch (err) { /* 下载失败不阻断请求 */ }
  }

  function bodyOf(init) {
    try { return JSON.parse((init && init.body) || '{}'); }
    catch (err) { return null; }
  }

  /* ---------- 生成目录：真的写到用户磁盘 ----------
   *
   * 关键点：线上版不是「演示」，而是**换了一条写盘通道**。
   * 本地版由 Python 写 `target` 路径；线上没有 Python，改用浏览器的 File System Access API，
   * 由用户当场授权一个文件夹，然后**逐个创建真实目录与文件**。
   * 差别只有两点：位置由用户点选（不是输入框）、需要 Edge/Chrome。
   *
   * ⚠ 调用顺序不可改：`showDirectoryPicker()` 必须在**用户激活窗口内同步发起**。
   *   先 await 任何东西再弹，浏览器会以 NotAllowedError 直接拒绝 —— 这是本 API 最常见的坑。
   */

  function writeTree(dirHandle, node, prefix, createdDirs, createdFiles) {
    return Object.keys(node).reduce(function (chain, key) {
      return chain.then(function () {
        var value = node[key];
        var path = prefix ? prefix + '/' + key : key;
        if (value && typeof value === 'object') {
          return dirHandle.getDirectoryHandle(key, { create: true }).then(function (sub) {
            createdDirs.push(path);
            return writeTree(sub, value, path, createdDirs, createdFiles);
          });
        }
        return dirHandle.getFileHandle(key, { create: true })
          .then(function (fh) { return fh.createWritable(); })
          .then(function (w) {
            return w.write(String(value === null || value === undefined ? '' : value))
              .then(function () { return w.close(); });
          })
          .then(function () { createdFiles.push(path); });
      });
    }, Promise.resolve());
  }

  function generate(init) {
    var payload = bodyOf(init);
    if (!payload) return Promise.resolve(fail('badJson', tr('badJson')));
    var tree = payload.tree;
    if (!tree || typeof tree !== 'object' || !Object.keys(tree).length) {
      return Promise.resolve(fail('treeMissing', tr('treeMissing')));
    }
    var stats = countTree(tree);
    if (stats.dirs + stats.files > 500) {
      return Promise.resolve(fail('tooManyNodes', tr('tooMany'), 400, {
        dirs: stats.dirs, files: stats.files, total: stats.dirs + stats.files, limit: 500,
      }));
    }
    var rootName = String(payload.root || '').trim();

    /* 演练：只回清单，不碰磁盘 —— 与本地版语义一致（主界面按 createdDirs 等算数量） */
    if (payload.dryRun) {
      var plan = { dirs: [], files: [] };
      (function walk(node, prefix) {
        Object.keys(node).forEach(function (key) {
          var path = prefix ? prefix + '/' + key : key;
          if (node[key] && typeof node[key] === 'object') {
            plan.dirs.push(path);
            walk(node[key], path);
          } else {
            plan.files.push(path);
          }
        });
      })(tree, rootName);
      return Promise.resolve(ok({
        root: rootName, dryRun: true, createdDirs: plan.dirs, createdFiles: plan.files,
        existed: [], stats: stats,
      }));
    }

    if (typeof window.showDirectoryPicker !== 'function') {
      return Promise.resolve(fail('demoFsUnsupported', tr('fsUnsupported')));
    }

    /* 目标位置已「选过并记住」就直接写，不再弹框 —— 这是与本机版对齐的那一半语义
       （输入框里的值 = 生成落点）。判据必须**同步**：showDirectoryPicker 要在用户激活
       窗口内发起，中间不能夹 await（见 writeTree 上方的注释）。 */
    var remembered = (STORE && STORE.peekTarget) ? STORE.peekTarget() : null;
    var picker;
    if (remembered) {
      picker = Promise.resolve(remembered);
    } else {
      try {
        picker = window.showDirectoryPicker({ mode: 'readwrite', id: 'qingman' });
      } catch (err) {
        return Promise.resolve(fail('demoFsUnsupported', tr('fsUnsupported')));
      }
    }

    return picker.then(function (parent) {
      /* 这次是「现选」的：记成默认目标，并把文件夹名回填到输入框 —— 与本机版
         「生成后输入框仍留着那个路径」的观感一致（浏览器只给名字，给不了路径）。 */
      if (!remembered) {
        if (STORE && STORE.rememberTarget) { STORE.rememberTarget(parent); }
        syncTargetInput(parent.name);
      }
      var base = rootName
        ? parent.getDirectoryHandle(rootName, { create: true })
        : Promise.resolve(parent);
      return base.then(function (dir) {
        var createdDirs = [];
        var createdFiles = [];
        return writeTree(dir, tree, rootName, createdDirs, createdFiles).then(function () {
          return ok({
            root: rootName, createdDirs: createdDirs, createdFiles: createdFiles,
            existed: [], stats: stats,
          });
        });
      });
    }).catch(function (err) {
      var name = (err && err.name) || '';
      if (name === 'AbortError') return fail('demoCancelled', tr('cancelled'));
      if (name === 'NotAllowedError' || name === 'SecurityError') {
        return fail('demoNoPermission', tr('noPermission'));
      }
      return fail('ioError', (err && err.message) || tr('noDisk'), 500, { message: (err && err.message) || tr('noDisk') });
    });
  }

  /* 读一套模板的**源文本**（导出专用）：绑了真实目录就先读目录原文，
     没有目录 / 未授权 / 目录里没有该文件，才回落到浏览器内存储。

     **2026-10-21 修复**：此前导出走 `templateDoc()`，只读 `localStorage` 与内置 P0，
     **完全不知道已绑定的目录**；而列表（`GET /api/templates`）在绑定后只读目录。
     于是「列表里有、导出却 404 templateNotFound」—— 绑定真实模板目录后导出必失败。
     导出必须与列表**同源**，否则两条路径迟早各说各话。 */
  function localTemplateText(file) {
    if (file === P0.file) {
      return JSON.stringify({
        schemaVersion: 1, name: P0.name, description: P0.description || '', tree: P0.tree || {},
      }, null, 2) + '\n';
    }
    var tpl = userTemplates()[file];
    if (!tpl) { return null; }
    return JSON.stringify({
      schemaVersion: 1, name: tpl.name, description: tpl.description || '', tree: tpl.tree || {},
    }, null, 2) + '\n';
  }

  function readTemplateSource(file) {
    var fallback = function () {
      var text = localTemplateText(file);
      return text === null ? null : { text: text, source: 'json' };
    };
    if (!STORE || typeof STORE.readDirTemplateText !== 'function') {
      return Promise.resolve(fallback());
    }
    return STORE.getDir().then(function (handle) {
      if (!handle) { return fallback(); }
      return STORE.dirPermission(handle).then(function (state) {
        if (state !== 'granted') { return fallback(); }
        /* 原文直读：不传 format 时后端语义是**原样交回**，再序列化就不再是原件 */
        return STORE.readDirTemplateText(handle, file).then(function (text) {
          return { text: text, source: /\.md$/i.test(file) ? 'md' : 'json' };
        }).catch(function () { return fallback(); });
      });
    }).catch(function () { return fallback(); });
  }

  /** 导出：原样（缺省 / 同格式）或等价转换（`?format=json|md`）。
   *  转换口径对齐 `src/server/templates.py::export_template` —— 转换前后都校验，
   *  坏模板不借导出洗白。 */
  function exportTemplate(expName, want) {
    if (!expName) {
      return Promise.resolve(fail('templateNotFound', tr('noExport'), 404, { name: '' }));
    }
    return readTemplateSource(expName).then(function (src) {
      if (!src) {
        return fail('templateNotFound', tr('noExport'), 404, { name: expName });
      }
      var source = src.source;
      var text = src.text;
      var stem = stemOf(expName);
      if (!want || want === source || (want !== 'json' && want !== 'md')) {
        return ok({ file: expName, name: stem, source: source, text: text });
      }
      if (!MD) { return fail('demoReadonly', tr('noExport')); }
      if (want === 'md') {
        var doc;
        try { doc = JSON.parse(text); } catch (err) { return fail('templateBadJson', tr('noExport'), 400, { name: expName }); }
        if (!doc || typeof doc !== 'object') { return fail('templateBadJson', tr('noExport'), 400, { name: expName }); }
        var badJson = validateTree(doc.tree, true);
        if (badJson) { return fail(badJson, tr('noExport')); }
        try { text = MD.render(doc); } catch (err) { return fail('templateBadJson', tr('noExport'), 400, { name: expName }); }
        return ok({ file: stem + '.md', name: stem, source: 'md', text: text });
      }
      var mdDoc;
      try { mdDoc = MD.parse(text); } catch (err) {
        return fail((err && err.code) || 'templateBadMarkdown', tr('noExport'));
      }
      var badMd = validateTree(mdDoc && mdDoc.tree, true);
      if (badMd) { return fail(badMd, tr('noExport')); }
      return ok({
        file: stem + '.json', name: stem, source: 'json',
        text: JSON.stringify(mdDoc, null, 2) + '\n',
      });
    });
  }

  function extOf(name) {
    var m = /\.[^.\/]+$/.exec(name);
    return m ? m[0].slice(1).toLowerCase() : '';
  }
  function stemOf(name) { return name.replace(/\.[^.]+$/, ''); }

  /* 结构校验：根为空即拒绝；**空目录合法**（`{}` 是真空目录，不是空树） */
  function validateTree(tree, isRoot) {
    if (!tree || typeof tree !== 'object' || Array.isArray(tree)) return 'templateTreeMissing';
    var keys = Object.keys(tree);
    if (isRoot && !keys.length) return 'templateEmpty';
    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];
      if (!String(key).trim()) return 'segmentEmpty';
      if (/[\\/:*?"<>|]/.test(key)) return 'segmentIllegalChar';
      var value = tree[key];
      if (value && typeof value === 'object') {
        var bad = validateTree(value, false);
        if (bad) return bad;
      }
    }
    return '';
  }

  /* ---------- 各端点 ---------- */


  /* 未绑定目录时的回落：内置空白模板 + 浏览器里在线新增的那几套 */
  function templateFromLocal(rawName) {
    if (rawName === P0.file) {
      var tree = P0.tree || {};
      return ok({
        file: P0.file, name: P0.name, description: P0.description || '',
        tree: tree, stats: countTree(tree), source: 'json', schemaVersion: 1,
      });
    }
    var got = userTemplates()[rawName];
    if (!got) { return fail('templateNotFound', tr('noExport'), 404, { name: rawName }); }
    return ok({
      file: rawName, name: got.name, description: got.description || '',
      tree: got.tree || {}, stats: countTree(got.tree || {}), source: 'json',
    });
  }

  /* ---------- 写模板：绑了目录就必须落盘（读写同源） ----------
   *
   * 2026-10-17 修：此前**写**操作（新建 / 改名 / 删除 / 导入）恒写 `localStorage`，
   * 而列表在绑定目录后只读目录 —— 于是「新建模板看不见」。读写必须同源：
   * 绑了真实目录就以目录为准，没绑才用浏览器内存储。
   */

  /* 文件名净化：这个名字会**真的写到用户磁盘上**，必须挡路径穿越与非法字符。
     与本机版 `templates.py` 的 `TEMPLATE_FILE` 同一取舍：只认「名字 + .json/.md」；
     不合规就**拒绝**而不是悄悄改名 —— 悄悄改名会让用户以为存上了、其实名字被换掉。 */
  var ILLEGAL_FILE = /[\\/:*?"<>|\u0000-\u001f]/;

  function safeTemplateFile(raw) {
    var file = String(raw || '').trim();
    if (!file) return '';
    if (!/\.[^.]+$/.test(file)) file += '.json';
    if (!/\.(json|md)$/i.test(file)) return '';       /* 别把 .exe 之类写进模板库 */
    if (file.length > 120) return '';
    if (ILLEGAL_FILE.test(file)) return '';
    if (file.indexOf('..') === 0) return '';
    if (/\s$/.test(stemOf(file))) return '';          /* Windows 不接受文件名结尾空格 */
    return file;
  }

  /** 当前模板库的写目标：绑了真实目录 → `{dir}`；没绑 → `{local:true}`；无写权限 → `{needPermission}`。 */
  function templateSink() {
    if (!STORE) return Promise.resolve({ local: true });
    return STORE.getDir().then(function (handle) {
      if (!handle) return { local: true };
      return STORE.dirPermission(handle, 'readwrite').then(function (state) {
        if (state === 'granted') return { dir: handle, name: handle.name };
        /* 2026-10-18：权限不在手时先**就地升级**再放弃。
           `requestPermission` 需要用户手势，而这条请求本就由「新建模板」对话框的
           确认点击发起，transient activation 窗口（约 5s）通常还在 —— 升级成功
           浏览器会弹一次「允许修改」，用户点允许即可继续写，正是错误提示里
           描述的那个框，只是不必再手动重走「选择目录」。
           升级失败（无手势 / 用户拒绝 / 旧浏览器无此方法）才回 needPermission，
           提示口径与修复前一致：重新选择目录并授权。 */
        if (typeof STORE.requestDirPermission !== 'function') {
          return { needPermission: true, name: handle.name };
        }
        return STORE.requestDirPermission(handle, 'readwrite').then(function (next) {
          if (next === 'granted') return { dir: handle, name: handle.name };
          return { needPermission: true, name: handle.name };
        });
      });
    });
  }

  /** 读一套模板的文档（目录优先、浏览器内兜底）。找不到回 `null`。 */
  function readTemplateDoc(file) {
    if (!STORE) return Promise.resolve(null);
    return STORE.getDir().then(function (handle) {
      if (!handle) return null;
      return STORE.dirPermission(handle).then(function (state) {
        if (state !== 'granted') return null;
        return STORE.readDirTemplate(handle, file).catch(function () { return null; });
      });
    });
  }

  /** 按文件扩展名序列化：`.md` 走 md 文法渲染，其余写 JSON（与本机版「保持原格式」一致）。 */
  function serializeTemplateDoc(file, doc) {
    var body = { name: doc.name, description: doc.description || '', tree: doc.tree || {} };
    if (/\.md$/i.test(file) && MD) { return MD.render(body); }
    return JSON.stringify(body, null, 2) + '\n';
  }

  /** 把一套模板写进当前模板库（目录 or localStorage）。 */
  function saveTemplateDoc(file, doc, overwrite) {
    return templateSink().then(function (sink) {
      if (sink.needPermission) return fail('demoNeedPermission', tr('tplNeedWrite'), 403);
      if (sink.local) {
        var map = userTemplates();
        if (map[file] && !overwrite) return fail('templateExists', tr('tplExists'), 400, { name: file });
        map[file] = doc;
        writeJson(LS_TPL, map);
        return ok({ file: file, name: doc.name, sink: 'local' });
      }
      return STORE.dirFileExists(sink.dir, file).then(function (exists) {
        if (exists && !overwrite) return fail('templateExists', tr('tplExists'), 400, { name: file });
        /* 落盘时**不写 mtime** —— 真实文件自带 lastModified，多一个字段只是噪音 */
        var text = serializeTemplateDoc(file, doc);
        return STORE.writeDirFile(sink.dir, file, text).then(function () {
          return ok({ file: file, name: doc.name, sink: 'dir', dir: sink.name });
        }).catch(function (err) {
          if (err && (err.name === 'NotAllowedError' || err.name === 'SecurityError')) {
            return fail('demoNoPermission', tr('tplNeedWrite'), 403);
          }
          return fail('ioError', tr('tplWriteFail').replace('{msg}', (err && err.message) || ''), 500, { message: (err && err.message) || '' });
        });
      });
    });
  }

  /** 从当前模板库删一套模板。 */
  function removeTemplateDoc(file) {
    return templateSink().then(function (sink) {
      if (sink.needPermission) return fail('demoNeedPermission', tr('tplNeedWrite'), 403);
      if (sink.local) {
        var map = userTemplates();
        if (!map[file]) return fail('templateNotFound', tr('noExport'), 404, { name: file });
        delete map[file];
        writeJson(LS_TPL, map);
        return ok({ file: file, sink: 'local' });
      }
      return STORE.dirFileExists(sink.dir, file).then(function (exists) {
        if (!exists) return fail('templateNotFound', tr('noExport'), 404, { name: file });
        return STORE.removeDirEntry(sink.dir, file).then(function () {
          return ok({ file: file, sink: 'dir', dir: sink.name });
        }).catch(function (err) {
          return fail('ioError', tr('tplWriteFail').replace('{msg}', (err && err.message) || ''), 500, { message: (err && err.message) || '' });
        });
      });
    });
  }

  /** 改名 = 读旧 + 写新 + 删旧（同一文件名时只覆盖写）。
   *
   * 两条语义**对齐本机版 `rename_template`**：
   * ① 同时改文件名与文件内 `name`（只改一个，会出现"点了 A 却载入 B"）；
   * ② **保持原格式**：`.md` 进则 `.md` 出，不把用户的 md 偷偷转成 json。 */
  function renameTemplateDoc(from, toRaw, displayName) {
    var stem = stemOf(String(toRaw || '').trim());
    var ext = extOf(from) === 'md' ? '.md' : '.json';
    var to = safeTemplateFile(stem + ext);
    if (!to) return Promise.resolve(fail('templateNameInvalid', tr('tplNameInvalid'), 400, { name: String(toRaw || '') }));
    return readTemplateDoc(from).then(function (doc) {
      if (!doc) return fail('templateNotFound', tr('noExport'), 404, { name: from });
      var next = {
        name: displayName || doc.name,
        description: doc.description || '',
        tree: doc.tree || {},
        mtime: Date.now(),
      };
      return saveTemplateDoc(to, next, from === to).then(function (res) {
        if (!res || res.status >= 400 || from === to) return res;
        return removeTemplateDoc(from).then(function () { return res; });
      });
    });
  }

  function handle(path, method, init, search) {
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
      var nextDoc = { schemaVersion: 1, savedAt: savedAt, root: payload.doc.root };
      var prevDoc = readJson(LS_DOC, null);
      /* 与本地版同序：**先留上一版，再替换当前版**。颠倒就备份成了新内容。 */
      var commit = function (backupName) {
        var persisted = writeJson(LS_DOC, nextDoc);
        return ok({
          path: 'localStorage://' + LS_DOC, savedAt: savedAt,
          bytes: JSON.stringify(nextDoc).length,
          stats: countTree(payload.doc.root.children ? {} : {}),
          backup: { ok: !!backupName, file: backupName || '', skipped: !backupName },
          persisted: persisted,
        });
      };
      if (STORE && prevDoc) {
        return STORE.snapshot(prevDoc).then(commit, function () { return commit(''); });
      }
      return commit('');
    }

    /* 历史版本：存在 OPFS（浏览器私有文件系统）里，保留最近 5 份 */
    if (path === '/api/editor-backups' && method === 'GET') {
      if (!STORE) return ok({ dir: tr('dataDir'), keep: 0, backups: [] });
      return STORE.listBackups().then(function (backups) {
        return ok({ dir: tr('dataDir'), keep: 5, backups: backups });
      });
    }
    if (path === '/api/editor-restore' && method === 'POST') {
      var restorePayload = bodyOf(init) || {};
      if (!STORE) return fail('demoReadonly', tr('noRestore'));
      return STORE.readBackup(restorePayload.id).then(function (doc) {
        var now = new Date().toISOString().slice(0, 19);
        writeJson(LS_DOC, { schemaVersion: 1, savedAt: now, root: doc.root });
        return ok({
          restored: {
            id: restorePayload.id, name: restorePayload.id,
            rootName: (doc.root && doc.root.name) || '',
          },
        });
      }).catch(function (err) {
        /* 两个码都带占位符（`{name}` / `{id}`）：不传 detail 会原样露给用户 */
        var code = (err && err.code) || 'editorBackupCorrupt';
        return fail(code, tr('noRestore'), 404, { name: restorePayload.id, id: restorePayload.id });
      });
    }

    /* 模板库：内置空白模板 + 用户在线新增（都存在 localStorage） */
    if (path === '/api/templates' && method === 'GET') {
      if (!STORE) {
        return ok({ available: true, items: templateList(), path: 'localStorage://' + LS_TPL, reason: '' });
      }
      return STORE.getDir().then(function (handle) {
        if (!handle) { return { bound: false }; }
        /* **2026-10-21 修（第二版）**：这里原先查 `read`，而 `pickDir()` 绑定授的是
           `readwrite`。File System Access 的权限**按 mode 分别记录**，两处口径不一致
           就会出现「刚绑定成功、紧接着列表就 403」的怪象（用户实测反复
           `demoNeedPermission`，重选目录也没用）。

           统一为 **`readwrite`** —— 与绑定、与写入侧 `templateSink()` 完全同口径：
             · 已授权 readwrite ⇒ 查 readwrite 得 granted（列表正常）
             · 权限过期（prompt）⇒ 有手势则弹一次授权自愈；无手势则如实 403 */
        return STORE.dirPermission(handle, 'readwrite').then(function (state) {
          if (state === 'granted') {
            return STORE.readDirTemplates(handle).then(function (items) {
              return { bound: true, items: items, name: handle.name };
            });
          }
          /* 权限不在手：先**就地请求**一次。列表请求多由"打开页面/点刷新"触发，
             若此刻仍有 transient activation，浏览器会弹一次「允许查看/修改」，点了即恢复；
             无手势则 `requestPermission` 直接回 denied（浏览器不抛错），仍回 403。 */
          if (typeof STORE.requestDirPermission !== 'function') {
            return { bound: true, needPermission: true, name: handle.name };
          }
          return STORE.requestDirPermission(handle, 'readwrite')
            .then(function (next) {
              if (next !== 'granted') {
                return { bound: true, needPermission: true, name: handle.name };
              }
              return STORE.readDirTemplates(handle).then(function (items) {
                return { bound: true, items: items, name: handle.name, reGranted: true };
              });
            });
        });
      }).catch(function (err) {
        /* **2026-10-21 补**：绑定的文件夹**被删除 / 改名 / 移动**时，句柄仍在 IndexedDB，
           但底层读不到，抛 File System 的 `NotFoundError`。此前它**没人接**，一路冒泡到
           `api.js` 的 `catch`，被归成 `networkError`，界面显示「无法连接后端服务，请确认
           服务仍在运行」—— **归因完全错误**：在线版根本没有网络请求，服务从来不在。

           现就地识别，给出准确错误码；其它异常仍按原样上抛，不掩盖真问题。 */
        if (err && err.name === 'NotFoundError') {
          return fail('demoDirMissing', tr('dirMissing'), 404);
        }
        throw err;
      }).then(function (res) {
        if (res && res.bound && res.needPermission) {
          return fail('demoNeedPermission', tr('needPermission'), 403);
        }
        if (res && res.bound) {
          return ok({ available: true, items: res.items, path: res.name, reason: '', source: 'bound' });
        }
        return ok({ available: true, items: templateList(), path: 'localStorage://' + LS_TPL, reason: '' });
      });
    }
    if (path === '/api/templates' && method === 'POST') {
      var tplPayload = bodyOf(init);
      if (!tplPayload) return fail('badJson', tr('badJson'));
      var fileName = safeTemplateFile(tplPayload.name);
      if (!fileName) return fail('templateNameInvalid', tr('tplNameInvalid'), 400, { name: String(tplPayload.name || '') });
      return saveTemplateDoc(fileName, {
        name: String(tplPayload.name || '').trim().replace(/\.[^.]+$/, '') || stemOf(fileName),
        description: tplPayload.description || '',
        tree: tplPayload.tree || {},
        mtime: Date.now(),
      }, !!tplPayload.overwrite);
    }
    if (path.indexOf('/api/templates/') === 0 && path !== '/api/templates/import') {
      var rawName = decodeURIComponent(path.slice('/api/templates/'.length));
      if (method === 'GET') {
        return readTemplateDoc(rawName).then(function (fromDir) {
          if (!fromDir) { return templateFromLocal(rawName); }
          return ok({
            file: fromDir.file, name: fromDir.name, description: fromDir.description,
            tree: fromDir.tree, stats: countTree(fromDir.tree), source: fromDir.source,
          });
        });
      }
      if (method === 'DELETE') {
        /* 内置示例是页面自带的，不在任何目录里 —— 删不掉（沿用既有取舍） */
        if (rawName === P0.file) return fail('templateNotFound', tr('noExport'), 404, { name: rawName });
        return removeTemplateDoc(rawName);
      }
      if (method === 'POST') {
        var renamePayload = bodyOf(init) || {};
        var nextName = String(renamePayload.name || '').trim();
        if (!nextName) return fail('templateNameEmpty', tr('tplNameInvalid'));
        return renameTemplateDoc(rawName, nextName, nextName);
      }
    }

    /* 绑定目录：点选得到**真实句柄**并记住；手动粘贴的路径无法解析，只能点选 */
    if (path === '/api/templates-dir' && method === 'GET') {
      if (!STORE) return ok({ dir: tr('tplPath'), source: 'demo', available: true, reason: '' });
      return STORE.getDir().then(function (handle) {
        if (!handle) return ok({ dir: tr('tplPath'), source: 'demo', available: true, reason: '' });
        /* 与列表用**同一 mode**（readwrite）判 available —— 否则会出现
           「绑定行说可用、列表却 403」的口径分裂（2026-10-21 实测踩到）。 */
        return STORE.dirPermission(handle, 'readwrite').then(function (state) {
          return ok({
            dir: handle.name, source: 'bound',
            available: state === 'granted',
            reason: state === 'granted' ? '' : 'needPermission',
          });
        });
      });
    }
    if (path === '/api/templates-dir' && method === 'PUT') {
      var dirPayload = bodyOf(init) || {};
      if (!STORE) return ok({ applied: false, dir: tr('tplPath'), reason: 'demo' });
      var wantDir = String(dirPayload.dir || '');
      return STORE.getDir().then(function (handle) {
        if (handle && wantDir === handle.name) {
          return ok({ applied: true, dir: handle.name, source: 'bound' });
        }
        /* 只有「刚点选过、且名字对得上」的待定句柄才允许落库 —— 手填任意路径一律不认，
           因为浏览器解析不了路径、也换不出句柄。这是 pick 与 bind 两步分离的另一半：
           pick 不写库，PUT 才写（否则「选择目标位置」会改掉模板库，见 online-store.pickDir）。 */
        return STORE.commitDir(wantDir).then(function (committed) {
          if (committed) return ok({ applied: true, dir: wantDir, source: 'bound' });
          return ok({
            applied: false,
            dir: handle ? handle.name : tr('tplPath'),
            reason: 'demoPickOnly',
          });
        });
      });
    }
    if (path === '/api/templates-dir/pick') {
      if (!STORE) return ok({ available: false, reason: 'demo' });
      /* 同一个端点被两个按钮共用（「模板目录 · 选择…」与「目标位置 · 选择…」），
         而这两个动作的落点完全不同：前者是只读素材库（要 PUT 确认才绑定），
         后者是写入目标（记住后生成时直接用）。用途由注入层在点击时打标识别 ——
         src/web 不改，也就不会因为多一个入参而影响本机版。 */
      var wantTarget = pickingTarget;
      pickingTarget = false;
      if (wantTarget) {
        return STORE.pickTarget().then(function (handle) {
          /* 主界面会用回执里的 dir 填输入框；title 只能我们自己补（它不认识这个语义）。
             放到下一轮任务里改，避免和主界面写 value 抢同一帧。 */
          setTimeout(function () { syncTargetInput(handle.name); }, 0);
          return ok({ available: true, cancelled: false, dir: handle.name, target: true });
        }).catch(function (err) {
          if (err && err.name === 'AbortError') return ok({ available: true, cancelled: true });
          return ok({ available: false, reason: 'demo' });
        });
      }
      return STORE.pickDir().then(function (handle) {
        return ok({ available: true, cancelled: false, dir: handle.name });
      }).catch(function (err) {
        if (err && err.name === 'AbortError') return ok({ available: true, cancelled: true });
        return ok({ available: false, reason: 'demo' });
      });
    }
    if (path === '/api/open-dir') return ok({ available: false, reason: 'demo' });

    /* 图标：浏览器没有 .lnk 可挂，就把生成的 ICO 直接交给用户下载 */
    if (path === '/api/launch-icon' && method === 'POST') {
      var iconPayload = bodyOf(init) || {};
      if (iconPayload.icon) {
        downloadIco(iconPayload.icon);
        return ok({ exported: true, skipped: true });
      }
      return ok({ skipped: true });
    }

    /* 全量备份 / 恢复 / 清空（换浏览器、换域名的唯一退路） */
    if (path === '/api/demo-backup' && method === 'GET') {
      if (!STORE) return fail('demoUnsupported', tr('noExport'));
      return ok(STORE.exportAll());
    }
    if (path === '/api/demo-import' && method === 'POST') {
      var importPayload = bodyOf(init);
      if (!importPayload || typeof importPayload.content !== 'string') {
        return fail('badJson', tr('badJson'));
      }
      if (!STORE) return fail('demoUnsupported', tr('noExport'));
      try {
        return ok({ stats: STORE.importAll(importPayload.content) });
      } catch (err) {
        return fail((err && err.code) || 'badJson', tr('noExport'));
      }
    }
    if (path === '/api/demo-clear' && method === 'POST') {
      if (!STORE) return fail('demoUnsupported', tr('noExport'));
      return ok({ removed: STORE.clearAll() });
    }

    /* 生成目录：走浏览器写盘通道（真写，不是模拟） */
    if (path === '/api/generate' && method === 'POST') return generate(init);

    /* 快捷方式 / 导入导出：浏览器做不到，明确说明而不是假装成功 */
    if (path === '/api/shortcut') return fail('demoUsePwa', tr('usePwa'));
    /* 导出：把模板原文（或等价转换后的文本）交回前端 —— 前端本来就按响应的 `file`
       触发 Blob 下载，故浏览器侧无需任何改动。
       2026-10-21：读取**与列表同源**（目录优先），此前只读 localStorage，绑定目录后必 404。 */
    if (path.indexOf('/api/templates-export/') === 0 && method === 'GET') {
      var expName = decodeURIComponent(path.slice('/api/templates-export/'.length));
      var want = String((search && search.get('format')) || '').trim().toLowerCase();
      return exportTemplate(expName, want);
    }

    /* 导入：收原文 → 解析（.md 走移植的同一份文法）→ 校验 → 存为规范 .json */
    if (path === '/api/templates/import' && method === 'POST') {
      var imp = bodyOf(init);
      if (!imp) return fail('badJson', tr('badJson'));
      var impName = String(imp.filename || '').trim();
      if (!impName) return fail('templateNameEmpty', tr('noExport'));
      var impText = imp.content;
      if (typeof impText !== 'string' || !impText.trim()) return fail('templateEmpty', tr('noExport'));
      var impExt = extOf(impName);
      var impDoc;
      try {
        if (impExt === 'md') {
          if (!MD) return fail('demoReadonly', tr('noExport'));
          impDoc = MD.parse(impText);
        } else {
          impDoc = JSON.parse(impText);
        }
      } catch (err) {
        return fail((err && err.code) || 'templateBadMarkdown', tr('noExport'));
      }
      if (!impDoc || typeof impDoc !== 'object') return fail('templateBadJson', tr('noExport'), 400, { name: impName });
      var treeBad = validateTree(impDoc.tree, true);
      if (treeBad) return fail(treeBad, tr('noExport'));
      var storeName = safeTemplateFile(stemOf(impName) + '.json');
      if (!storeName) return fail('templateNameInvalid', tr('tplNameInvalid'), 400, { name: impName });
      var docName = impDoc.name || stemOf(impName);
      return saveTemplateDoc(storeName, {
        name: docName, description: impDoc.description || '',
        tree: impDoc.tree, mtime: Date.now(),
      }, !!imp.overwrite).then(function (res) {
        if (res && res.status >= 400) return res;
        return ok({ file: storeName, name: docName, source: 'json' });
      });
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
    var parsed = null;
    var path;
    try {
      parsed = new URL(url, window.location.href);
      path = parsed.pathname;
    } catch (err) {
      parsed = null;
      path = '';
    }
    /* `/api/env.js` 与 `/api/locales.js` 看着像接口，其实是**静态文件**
       （页面用 <script src> 同步取语言，脚本标签本就不经过 fetch）。
       但程序里若用 fetch 取它们，也必须落到真实文件上 —— 否则会被下面的兜底判成
       demoUnsupported，把「语言清单」这条链打断。 */
    if (path === '/api/env.js' || path === '/api/locales.js') return nativeFetch(input, init);
    if (path.indexOf('/api/') !== 0) return nativeFetch(input, init);
    var method = String(
      (init && init.method) || (input && input.method) || 'GET'
    ).toUpperCase();
    var hit = handle(path, method, init, parsed ? parsed.searchParams : null);
    if (hit) return Promise.resolve(hit);
    return nativeFetch(input, init);
  };

  /* 在线版不读「目标位置」输入框：真正的保存位置由生成时的目录选择器决定。
     但主界面会因 target 为空而拦下生成（本地版的合理校验），故这里预置一句说明文字，
     并置为只读 —— 让校验通过，同时不伪装成一个真实路径。 */
  function targetInput() { return document.querySelector('#inTarget'); }

  function markTargetInput() {
    var input = targetInput();
    if (!input || input.dataset.qmDemo === '1') { return; }
    input.dataset.qmDemo = '1';
    input.readOnly = true;
    if (!input.value) { input.value = tr('pickHint'); }
    input.title = tr('pickHintTitle');
  }

  /** 目标目录确定后回填**文件夹名**（浏览器只给名字，给不了绝对路径）。 */
  function syncTargetInput(name) {
    var input = targetInput();
    if (!input || !name) { return; }
    input.value = name;
    input.title = tr('targetTitle');
  }

  /* 「目标位置 · 选择…」与「模板目录 · 选择目录」共用同一个端点，靠**点击意图**区分。
     捕获阶段先于按钮自身的 click 处理器执行，而 chooseTargetDir() 会在同一个任务里
     立刻发出 POST /api/templates-dir/pick —— 请求到达时标记必然已置位。 */
  var pickingTarget = false;

  function bindTargetIntent() {
    document.addEventListener('click', function (event) {
      var node = event.target;
      var btn = (node && node.closest) ? node.closest('#btnPickTarget') : null;
      if (!btn) { return; }
      pickingTarget = true;
      /* 兜底复位：万一这次点击没走到 pick（被别的监听器拦掉），标记不该永久粘住 */
      setTimeout(function () { pickingTarget = false; }, 2000);
    }, true);
  }

  function bootTarget() {
    markTargetInput();
    bindTargetIntent();
    /* 预热：把上次记住的目标目录连同它的**读写**权限读进内存，
       好让 generate 能**同步**判断「要不要弹框」（弹框必须在用户激活窗口内发起）。 */
    if (!STORE || typeof STORE.preloadTarget !== 'function') { return; }
    STORE.preloadTarget().then(function () {
      var handle = STORE.peekTarget();
      if (handle) { syncTargetInput(handle.name); }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootTarget);
  } else {
    bootTarget();
  }

  window.__QM_DEMO_ACTIVE__ = true;
})();
