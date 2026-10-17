/* 青蔓 QingMan · 在线版存储层（只由 tools/build_static_site.py 注入产物）
 *
 * 浏览器里没有"磁盘"，但有三样东西可以顶上来，各管一段：
 *
 *   localStorage          草稿与在线模板（小、同步、够用）           —— 原有
 *   IndexedDB             存 **FileSystemDirectoryHandle**（句柄可结构化克隆）
 *                         ⇒ 「绑定过的本地模板目录」下次打开还记得
 *   OPFS（navigator.storage.getDirectory）
 *                         浏览器私有文件系统 ⇒ 历史版本快照，可多份轮转
 *
 * 这三者都按 **origin 隔离**：换域名 = 换 origin = 数据看不见。所以「导出备份」
 * 不是锦上添花，是唯一的数据搬迁手段。
 *
 * 为什么句柄要进 IndexedDB：`showDirectoryPicker()` 返回的 handle 不能序列化成
 * 字符串，但可以直接存 IDB；重新打开页面后 `queryPermission()` 若为 granted 就能
 * 直接用，为 prompt 则必须再点一次按钮（浏览器要求用户手势）。
 */
(function (root) {
  'use strict';

  var KEYS = { doc: 'qm.demo.editor', templates: 'qm.demo.templates' };
  var DB_NAME = 'qm-demo';
  var DB_STORE = 'kv';
  var DIR_KEY = 'templatesDir';
  var TARGET_KEY = 'targetDir';   /* 生成目标目录 —— 与模板库**分键存放**，互不影响 */
  var KEEP = 5;                 // 历史版本保留份数（与本地版 EDITOR_BACKUP_KEEP 同值）
  var TPL_EXT = /\.(json|md)$/i;

  /* ---------- localStorage 小工具 ---------- */

  function readLs(key, fallback) {
    try {
      var raw = root.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (err) { return fallback; }
  }
  function writeLs(key, value) {
    try { root.localStorage.setItem(key, JSON.stringify(value)); return true; }
    catch (err) { return false; }
  }

  /* ---------- IndexedDB（只存一个句柄） ---------- */

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!root.indexedDB) { reject(new Error('no-idb')); return; }
      var req = root.indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(DB_STORE)) { req.result.createObjectStore(DB_STORE); }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error || new Error('idb-open-failed')); };
    });
  }

  function idbRun(mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(DB_STORE, mode);
        var req = fn(tx.objectStore(DB_STORE));
        tx.oncomplete = function () { resolve(req ? req.result : undefined); };
        tx.onerror = function () { reject(tx.error || new Error('idb-tx-failed')); };
      });
    });
  }

  var dirCache = null;

  function getDir() {
    if (dirCache) { return Promise.resolve(dirCache); }
    return idbRun('readonly', function (store) { return store.get(DIR_KEY); })
      .then(function (handle) { dirCache = handle || null; return dirCache; })
      .catch(function () { return null; });
  }

  /* 「选择」与「绑定」必须是两步 —— 与本机版语义一致（routes.pick_templates_dir 的
     docstring 明确写着"不落盘、不绑定"，绑定由前端另发 PUT 完成）。

     教训（2026-10-17 用户报告"选完目标位置后模板目录变了"）：这里原先在 pick 成功时
     就 `store.put(handle, DIR_KEY)`，把两步合成了一步。而「目标位置 · 选择…」复用的
     正是同一个端点（main.js chooseTargetDir → POST /api/templates-dir/pick），它拿到
     路径只填进输入框、**从不发 PUT** —— 于是用户的模板库被悄悄改绑到目标文件夹。
     现在 pick 只把句柄放进 pendingDir，等 PUT 确认时由 commitDir 才落库。 */

  var pendingDir = null;

  function pickDir() {
    /* ⚠ 必须**同步**发起：picker 依赖用户激活窗口，先 await 别的东西再弹会被拒绝 */
    if (typeof root.showDirectoryPicker !== 'function') {
      return Promise.reject({ code: 'demoFsUnsupported' });
    }
    var picking;
    try {
      picking = root.showDirectoryPicker({ mode: 'read', id: 'qm-templates' });
    } catch (err) {
      return Promise.reject({ code: 'demoFsUnsupported' });
    }
    return picking.then(function (handle) {
      pendingDir = handle;   /* 只暂存，不落库 */
      return handle;
    });
  }

  /** 前端发送 `PUT /api/templates-dir` 确认绑定后，才把待定句柄写进 IndexedDB。
   *  `name` 必须与刚选中的目录同名（手填的任意路径认不出来，也没法换成句柄）。 */
  function commitDir(name) {
    if (!pendingDir || !name || pendingDir.name !== name) return Promise.resolve(false);
    var handle = pendingDir;
    pendingDir = null;
    dirCache = handle;
    return idbRun('readwrite', function (store) { return store.put(handle, DIR_KEY); })
      .then(function () { return true; })
      /* 存不下（隐私模式配额 / 旧内核）不影响本次会话：dirCache 已生效，刷新后才丢 */
      .catch(function () { return true; });
  }

  function dirPermission(handle) {
    if (!handle || typeof handle.queryPermission !== 'function') { return Promise.resolve('denied'); }
    return handle.queryPermission({ mode: 'read' }).catch(function () { return 'denied'; });
  }

  /* ---------- 生成目标位置（与模板库**分键**，互不影响） ----------
   *
   * 本机版的目标位置是一个**绝对路径字符串**：可手输、可点选，生成时服务端按它写盘。
   * 浏览器两件都做不到（不披露路径、不能按路径写），能还原的是**语义**：
   * 「点一次选个文件夹 → 记下来 → 生成时直接写进去」，不必每次重新弹框。
   *
   * ⚠ 判据必须**同步**：`showDirectoryPicker()` 要在用户激活窗口内发起，先 await 再弹
   *   会被 NotAllowedError 拒绝。所以 peekTarget() 读的是**页面载入时预热的内存缓存**。
   */

  var targetCache = null;
  var targetState = '';        /* '' | granted | prompt | denied */

  /** 页面载入时预热：读回上次记住的目标目录，并查询它的**读写**权限。 */
  function preloadTarget() {
    return idbRun('readonly', function (store) { return store.get(TARGET_KEY); })
      .then(function (handle) {
        targetCache = handle || null;
        if (!handle) { targetState = ''; return null; }
        return targetPermission(handle).then(function (state) {
          targetState = state || '';
          return handle;
        });
      })
      .catch(function () { targetCache = null; targetState = ''; return null; });
  }

  /** 同步判据：已记住、且写权限已在手 —— 有值就直接写，不弹框。 */
  function peekTarget() {
    return targetState === 'granted' ? targetCache : null;
  }

  /** 记住目标目录（点选或首次生成后调用）。存不下也不影响本次会话。 */
  function rememberTarget(handle) {
    targetCache = handle || null;
    targetState = handle ? 'granted' : '';
    if (!handle) { return Promise.resolve(false); }
    return idbRun('readwrite', function (store) { return store.put(handle, TARGET_KEY); })
      .then(function () { return true; })
      .catch(function () { return true; });
  }

  /** 「目标位置 · 选择…」：弹一次读写授权框，并记成下次的默认目标。 */
  function pickTarget() {
    if (typeof root.showDirectoryPicker !== 'function') {
      return Promise.reject({ code: 'demoFsUnsupported' });
    }
    var picking;
    try {
      picking = root.showDirectoryPicker({ mode: 'readwrite', id: 'qm-target' });
    } catch (err) {
      return Promise.reject({ code: 'demoFsUnsupported' });
    }
    return picking.then(function (handle) {
      return rememberTarget(handle).then(function () { return handle; });
    });
  }

  function targetPermission(handle) {
    if (!handle || typeof handle.queryPermission !== 'function') { return Promise.resolve('denied'); }
    return handle.queryPermission({ mode: 'readwrite' }).catch(function () { return 'denied'; });
  }

  /* ---------- 从目录读模板 ---------- */

  function entriesOf(dirHandle) {
    var out = [];
    var it = dirHandle.values();
    function step() {
      return it.next().then(function (res) {
        if (res.done) { return out; }
        out.push(res.value);
        return step();
      });
    }
    return step();
  }

  function parseTemplateText(text, file) {
    if (/\.md$/i.test(file)) { return root.QMDemoMd.parse(text); }
    return JSON.parse(text);
  }

  function readDirTemplates(dirHandle) {
    return entriesOf(dirHandle).then(function (entries) {
      var picked = entries.filter(function (h) {
        return h.kind === 'file' && TPL_EXT.test(h.name);
      });
      return Promise.all(picked.map(function (h) {
        /* 名字取**句柄**的 `h.name`，不取 `File.name` —— 两者恒等，但少一层隐含依赖：
           任何实现（含测试替身）只要能列出条目，就该能读。 */
        return h.getFile().then(function (file) {
          return file.text().then(function (text) {
            var doc = null;
            try { doc = parseTemplateText(text, h.name); } catch (err) { doc = null; }
            return {
              file: h.name,
              name: (doc && doc.name) || h.name.replace(/\.[^.]+$/, ''),
              description: (doc && doc.description) || '',
              size: file.size,
              mtime: file.lastModified / 1000,
              source: /\.md$/i.test(h.name) ? 'md' : 'json',
              broken: !doc,
            };
          });
        });
      }));
    });
  }

  function readDirTemplate(dirHandle, file) {
    return dirHandle.getFileHandle(file).then(function (fh) {
      return fh.getFile().then(function (f) {
        return f.text().then(function (text) {
          var doc = parseTemplateText(text, file);
          return {
            file: file,
            name: doc.name || file.replace(/\.[^.]+$/, ''),
            description: doc.description || '',
            tree: doc.tree || {},
            source: /\.md$/i.test(file) ? 'md' : 'json',
          };
        });
      });
    });
  }

  /* ---------- OPFS 历史版本 ---------- */

  function opfsBackupDir() {
    if (!root.navigator || !navigator.storage || !navigator.storage.getDirectory) {
      return Promise.reject(new Error('no-opfs'));
    }
    return navigator.storage.getDirectory().then(function (dir) {
      return dir.getDirectoryHandle('backups', { create: true });
    });
  }

  function stampName() {
    var d = new Date();
    var p = function (n, w) { return String(n).padStart(w || 2, '0'); };
    return 'editor-' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate())
      + '-' + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds())
      + '-' + p(d.getMilliseconds(), 3) + '.json';
  }

  function writeFileIn(dir, name, text) {
    return dir.getFileHandle(name, { create: true }).then(function (fh) {
      return fh.createWritable().then(function (w) {
        return w.write(text).then(function () { return w.close(); });
      });
    });
  }

  function readTextIn(dir, name) {
    return dir.getFileHandle(name).then(function (fh) {
      return fh.getFile().then(function (file) { return file.text(); });
    });
  }

  function pruneBackups(dir) {
    return entriesOf(dir).then(function (entries) {
      var names = entries.filter(function (h) { return h.kind === 'file' && /^editor-.*\.json$/.test(h.name); })
        .map(function (h) { return h.name; })
        .sort();                      // 时间戳定长 → 字典序即时间序
      var drop = names.slice(0, Math.max(0, names.length - KEEP));
      return Promise.all(drop.map(function (n) {
        return dir.removeEntry(n).catch(function () { /* 单份删失败不影响其它 */ });
      }));
    });
  }

  function snapshot(prevDoc) {
    /* 与本地版同义：**写新版之前**先把上一版留档；没有上一版就不产生空档案 */
    if (!prevDoc || !prevDoc.root) { return Promise.resolve(''); }
    return opfsBackupDir().then(function (dir) {
      var name = stampName();
      var body = JSON.stringify(prevDoc, null, 2) + '\n';
      return writeFileIn(dir, name, body)
        .then(function () { return pruneBackups(dir); })
        .then(function () { return name; });
    }).catch(function () { return ''; });
  }

  function listBackups() {
    return opfsBackupDir().then(function (dir) {
      return entriesOf(dir).then(function (entries) {
        var files = entries.filter(function (h) { return h.kind === 'file' && /^editor-.*\.json$/.test(h.name); })
          .map(function (h) { return h.name; })
          .sort()
          .reverse();                 // 新 → 旧
        return Promise.all(files.map(function (name) {
          return dir.getFileHandle(name).then(function (fh) {
            return fh.getFile().then(function (file) {
              return file.text().then(function (text) {
                var doc = null;
                try { doc = JSON.parse(text); } catch (err) { doc = null; }
                return {
                  id: name,
                  name: name,
                  savedAt: (doc && doc.savedAt) || '',
                  rootName: (doc && doc.root && doc.root.name) || '',
                  bytes: file.size,
                  archived: false,
                  broken: !doc || !doc.root,
                };
              });
            });
          }).catch(function () {
            return { id: name, name: name, savedAt: '', rootName: '', bytes: 0,
                     archived: false, broken: true };
          });
        }));
      });
    }).catch(function () { return []; });
  }

  function readBackup(id) {
    if (!/^editor-[0-9-]+\.json$/.test(String(id || ''))) {
      return Promise.reject({ code: 'editorBackupNotFound' });
    }
    return opfsBackupDir()
      .then(function (dir) { return readTextIn(dir, id); })
      .then(function (text) {
        var doc = JSON.parse(text);
        if (!doc || !doc.root) { throw { code: 'editorBackupCorrupt' }; }
        return doc;
      });
  }

  /* ---------- 备份 / 恢复 / 清空 ---------- */

  function exportAll() {
    var payload = {
      schema: 'qm-demo-backup/1',
      exportedAt: new Date().toISOString(),
      editor: readLs(KEYS.doc, null),
      templates: readLs(KEYS.templates, {}),
    };
    var d = new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    return {
      file: 'qingman-backup-' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate())
        + '-' + p(d.getHours()) + p(d.getMinutes()) + '.json',
      text: JSON.stringify(payload, null, 2) + '\n',
    };
  }

  function importAll(text) {
    var payload;
    try { payload = JSON.parse(text); } catch (err) { throw { code: 'badJson' }; }
    if (!payload || payload.schema !== 'qm-demo-backup/1') { throw { code: 'demoBackupSchema' }; }
    var stats = { editor: false, templates: 0 };
    if (payload.editor && payload.editor.root) {
      writeLs(KEYS.doc, payload.editor);
      stats.editor = true;
    }
    if (payload.templates && typeof payload.templates === 'object') {
      var merged = readLs(KEYS.templates, {});
      Object.keys(payload.templates).forEach(function (name) {
        merged[name] = payload.templates[name];
        stats.templates += 1;
      });
      writeLs(KEYS.templates, merged);
    }
    return stats;
  }

  function clearAll() {
    var removed = [];
    [KEYS.doc, KEYS.templates].forEach(function (key) {
      try { root.localStorage.removeItem(key); removed.push(key); } catch (err) { /* 忽略 */ }
    });
    /* 目标位置**一并忘记**：共用电脑时，上一个人选过的文件夹不该被下一个人无声写入。
       （模板目录句柄刻意保留 —— 那个只读，不构成写入风险。） */
    targetCache = null;
    targetState = '';
    idbRun('readwrite', function (store) { return store.delete(TARGET_KEY); })
      .catch(function () { /* 删不掉不影响清空结果 */ });
    return removed;
  }

  root.QMDemoStore = {
    KEYS: KEYS,
    readLs: readLs,
    writeLs: writeLs,
    getDir: getDir,
    pickDir: pickDir,
    commitDir: commitDir,
    dirPermission: dirPermission,
    preloadTarget: preloadTarget,
    peekTarget: peekTarget,
    rememberTarget: rememberTarget,
    pickTarget: pickTarget,
    targetPermission: targetPermission,
    readDirTemplates: readDirTemplates,
    readDirTemplate: readDirTemplate,
    snapshot: snapshot,
    listBackups: listBackups,
    readBackup: readBackup,
    exportAll: exportAll,
    importAll: importAll,
    clearAll: clearAll,
  };
})(typeof window !== 'undefined' ? window : globalThis);
