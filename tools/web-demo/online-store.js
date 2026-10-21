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
      /* 2026-10-18 修：模式 `'read'` → `'readwrite'`。
         读写同源（fe94be1）之后，绑定的目录**既是素材库也是写落地** ——
         新建 / 改名 / 删除 / 导入全都落在这里。而 File System Access 的权限
         **按 mode 记录**：只读授权永远满足不了 `templateSink` 的 readwrite
         查询，表现为「新建模板必败」，且错误提示里的「在弹框里允许修改」
         无从触发（再选一次还是只读）—— 是一条死路。
         反方向成立：readwrite 授权**隐含** read，列表的只读查询照常 granted。 */
      picking = root.showDirectoryPicker({ mode: 'readwrite', id: 'qm-templates' });
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

  /** 目录权限查询。`mode` 默认 `'read'`（模板库只读进来用），写盘前要传 `'readwrite'`。 */
  function dirPermission(handle, mode) {
    if (!handle || typeof handle.queryPermission !== 'function') { return Promise.resolve('denied'); }
    return handle.queryPermission({ mode: mode || 'read' }).catch(function () { return 'denied'; });
  }

  /** 目录权限**升级**：把只读授权换成读写（2026-10-18 加，配合 `pickDir` 模式修正）。
   *
   *  `requestPermission` 会**消耗 transient activation**（用户手势），无手势时浏览器
   *  直接回 `'denied'` 而不抛错 —— 所以这里把一切异常都收成 `'denied'`，让调用方
   *  统一回退到「请重新选择目录」的提示，**不能把升级成功当成必然**。
   *
   * 用途：修复前（`mode: 'read'` 时代）绑定的老目录只有只读授权，写操作当场弹一次
   * 「允许修改」即可自愈，不必逼用户重新走一遍「选择目录 + 确认绑定」。 */
  function requestDirPermission(handle, mode) {
    if (!handle || typeof handle.requestPermission !== 'function') {
      return Promise.resolve('denied');
    }
    return handle.requestPermission({ mode: mode || 'readwrite' })
      .catch(function () { return 'denied'; });
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
    return dirPermission(handle, 'readwrite');
  }

  /* ---------- 写目录（模板库绑到真实文件夹后，写操作必须真的落盘） ----------
   *
   * 2026-10-17 修：此前只实现了「从目录读」，写操作（新建 / 改名 / 删除 / 导入）仍
   * 一律写 `localStorage`，而列表在绑定目录后只读目录 —— 于是「新建模板看不见」。
   * 读写必须同源：绑了目录就以目录为准，没绑才用浏览器内存储。
   */

  /** 目录里是否已有这个文件（`getFileHandle` 不带 create，缺失会抛 NotFoundError）。 */
  function dirFileExists(dirHandle, file) {
    if (!dirHandle || typeof dirHandle.getFileHandle !== 'function') { return Promise.resolve(false); }
    return dirHandle.getFileHandle(file)
      .then(function () { return true; })
      .catch(function () { return false; });
  }

  /** 把一段文本写成目录里的文件（覆盖写）。 */
  function writeDirFile(dirHandle, file, text) {
    return dirHandle.getFileHandle(file, { create: true }).then(function (fh) {
      return fh.createWritable().then(function (writable) {
        return writable.write(text).then(function () { return writable.close(); });
      });
    });
  }

  /** 删目录里的一个文件；本来就没有也算成功（幂等，避免"已删过"变成报错）。 */
  function removeDirEntry(dirHandle, file) {
    if (!dirHandle || typeof dirHandle.removeEntry !== 'function') {
      return Promise.reject({ code: 'demoFsUnsupported' });
    }
    return dirHandle.removeEntry(file).catch(function (err) {
      if (err && err.name === 'NotFoundError') { return true; }
      throw err;
    });
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

  /**
   * 模板列表的**唯一**排序口径：按文件名（小写优先比较，再比原名）。
   *
   * 为什么必须显式排：`FileSystemDirectoryHandle.values()` 的枚举顺序**由文件系统决定、
   * 没有任何稳定性承诺** —— Windows 目录索引、OneDrive/同步盘、以及新建/删除/改名之后
   * 都可能改序；`Object.keys()` 同理（插入序，删一条再建就变）。不排就等于把
   * 「底层怎么摆」直接暴露成「用户看到的顺序」，于是每次载入/每次轮询都可能重排。
   *
   * 为什么用文件名而不是模板里的 `name`：**与本机版同口径**
   * （`src/server/templates.py` 的 `sorted(..., key=lambda q: (q.name.lower(), q.name))`）。
   * 两版顺序一致，用户换形态打开时看到的列表才是同一个。
   *
   * 附带好处：前端轮询的签名是 `file|mtime|size` **按序拼接**，顺序一乱签名就变，
   * 会每 2.5s 重建一次 DOM（列表跳动、hover/滚动丢失）。排序稳定后签名也稳定。
   */
  function byFile(a, b) {
    var x = String(a.file || '').toLowerCase();
    var y = String(b.file || '').toLowerCase();
    if (x !== y) { return x < y ? -1 : 1; }
    var ax = String(a.file || '');
    var bx = String(b.file || '');
    return ax < bx ? -1 : (ax > bx ? 1 : 0);
  }

  function sortByFile(items) {
    return items.slice().sort(byFile);
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
      })).then(sortByFile);   /* 顺序由 byFile 显式规定，不交给文件系统 */
    });
  }

  /** 读目录里模板文件的**原文**（导出用：不传 format 时要原样交回，不能再序列化）。
   *
   * 2026-10-21 补：此前只暴露 `readDirTemplate`（解析后的文档），导出端因此拿不到
   * 原文，只好回落到浏览器内存储 —— 于是「列表读目录、导出读 localStorage」，
   * 绑定真实目录后导出必然 404。
   */
  function readDirTemplateText(dirHandle, file) {
    return dirHandle.getFileHandle(file).then(function (fh) {
      return fh.getFile().then(function (f) { return f.text(); });
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
    requestDirPermission: requestDirPermission,
    preloadTarget: preloadTarget,
    peekTarget: peekTarget,
    rememberTarget: rememberTarget,
    pickTarget: pickTarget,
    targetPermission: targetPermission,
    readDirTemplates: readDirTemplates,
    readDirTemplate: readDirTemplate,
    readDirTemplateText: readDirTemplateText,
    dirFileExists: dirFileExists,
    writeDirFile: writeDirFile,
    removeDirEntry: removeDirEntry,
    sortByFile: sortByFile,
    snapshot: snapshot,
    listBackups: listBackups,
    readBackup: readBackup,
    exportAll: exportAll,
    importAll: importAll,
    clearAll: clearAll,
  };
})(typeof window !== 'undefined' ? window : globalThis);
