/* 青蔓 QingMan · 在线版数据面板（只由 tools/build_static_site.py 注入产物）
 *
 * 在线版的数据全在浏览器里，所以需要三个本地版不必有的出口：
 *   导出备份 / 导入备份 —— 换浏览器、换域名（origin 变了数据就看不见）时的唯一搬法
 *   清空本机数据       —— 共用电脑时把上一个人的草稿与模板清掉
 *   导出启动图标       —— 在线版没有 .lnk 可挂，只能把生成的 ICO 交给用户
 *
 * 为什么挂在「服务设置」里：那是用户找"数据在哪"的地方（弹窗里本来就有数据目录一行），
 * 不必新造入口，也不动顶部工具栏的布局。
 */
(function (root) {
  'use strict';

  var TEXT = {
    zh: {
      title: '在线版数据',
      hint: '草稿与模板都存在这个浏览器里。换浏览器或换域名后看不见，请先导出备份。',
      exportBackup: '导出备份',
      importBackup: '导入备份',
      clear: '清空本机数据',
      exportIcon: '导出启动图标',
      confirmClear: '将清空本浏览器里的草稿与在线模板（已绑定的模板目录不受影响）。确定吗？',
      clearDone: '已清空，页面将重新载入。',
      clearFail: '清空失败：{msg}',
      importDone: '导入完成：草稿已恢复，模板合并 {n} 套。页面将重新载入。',
      importFail: '导入失败：{msg}',
      exportFail: '导出失败：{msg}',
      iconDone: '已导出启动图标（qingman-launch.ico）',
      iconFail: '图标导出失败：{msg}',
      install: '安装到桌面',
      installOk: '已在浏览器里弹出安装确认。装好后桌面与开始菜单会出现「青蔓」图标，可离线打开。',
      installUsed: '已经装过了（当前就在应用窗口里），桌面图标无需重复创建。',
      installManual: '这个浏览器没给出安装入口。可用地址栏右侧的安装图标，或菜单 → 应用 → 安装此站点。',
    },
    en: {
      title: 'Online data',
      hint: 'Drafts and templates live in this browser. Switching browsers or domains hides them — export a backup first.',
      exportBackup: 'Export backup',
      importBackup: 'Import backup',
      clear: 'Clear local data',
      exportIcon: 'Export app icon',
      confirmClear: 'This clears drafts and online templates in this browser (a bound template folder is untouched). Continue?',
      clearDone: 'Cleared. The page will reload.',
      clearFail: 'Clear failed: {msg}',
      importDone: 'Imported: draft restored, {n} template(s) merged. The page will reload.',
      importFail: 'Import failed: {msg}',
      exportFail: 'Export failed: {msg}',
      iconDone: 'App icon exported (qingman-launch.ico)',
      iconFail: 'Icon export failed: {msg}',
      install: 'Install to desktop',
      installOk: 'The browser asked you to confirm. Once installed you get a QingMan icon on the desktop and Start menu, and it works offline.',
      installUsed: 'Already installed (you are in the app window), no extra desktop icon needed.',
      installManual: 'This browser exposed no install prompt. Use the install icon in the address bar, or menu > Apps > Install this site.',
    },
  };

  function isZh() {
    var lang = document.documentElement.lang || navigator.language || 'zh';
    return String(lang).toLowerCase().indexOf('zh') === 0;
  }
  function tr(key, vars) {
    var text = (isZh() ? TEXT.zh : TEXT.en)[key] || key;
    return vars ? text.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] != null ? vars[k] : m; }) : text;
  }

  /* ---------- 小工具 ---------- */

  function download(file, text, type) {
    var blob = new Blob([text], { type: type || 'application/json;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = file;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  function downloadBytes(file, bytes, type) {
    var url = URL.createObjectURL(new Blob([bytes], { type: type }));
    var a = document.createElement('a');
    a.href = url;
    a.download = file;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  function call(path, options) {
    return fetch(path, options || {}).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || body.ok === false) {
          var error = new Error(body.message || ('HTTP ' + res.status));
          error.code = body.code;
          throw error;
        }
        return body;
      });
    });
  }

  function note(host, text) {
    var line = host.querySelector('.qm-data-note');
    if (line) { line.textContent = text; }
  }

  /* ---------- 面板 ---------- */

  var STYLE = [
    '.qm-data{margin-top:12px;padding-top:10px;border-top:1px dashed var(--qm-line,#d8dbe0)}',
    '.qm-data-hd{font-weight:600;font-size:13px;margin-bottom:4px}',
    '.qm-data-hint{margin:0 0 8px;font-size:12px;line-height:1.6;color:var(--qm-ink-3,#7b838d)}',
    '.qm-data-acts{display:flex;gap:8px;flex-wrap:wrap}',
    '.qm-data-note{margin:6px 0 0;font-size:12px;color:var(--qm-ink-2,#4a5058);min-height:1em}',
    '.qm-data [hidden]{display:none!important}',
  ].join('\n');

  function buildPanel() {
    var wrap = document.createElement('div');
    wrap.className = 'qm-data';
    wrap.innerHTML = [
      '<div class="qm-data-hd"><span class="qm-zh">' + TEXT.zh.title + '</span><span class="qm-en">' + TEXT.en.title + '</span></div>',
      '<p class="qm-data-hint"><span class="qm-zh">' + TEXT.zh.hint + '</span><span class="qm-en">' + TEXT.en.hint + '</span></p>',
      '<div class="qm-data-acts">',
      '  <button type="button" class="btn btn-ghost btn-mini" data-act="export"><span class="qm-zh">' + TEXT.zh.exportBackup + '</span><span class="qm-en">' + TEXT.en.exportBackup + '</span></button>',
      '  <button type="button" class="btn btn-ghost btn-mini" data-act="import"><span class="qm-zh">' + TEXT.zh.importBackup + '</span><span class="qm-en">' + TEXT.en.importBackup + '</span></button>',
      '  <button type="button" class="btn btn-ghost btn-mini" data-act="clear"><span class="qm-zh">' + TEXT.zh.clear + '</span><span class="qm-en">' + TEXT.en.clear + '</span></button>',
      '  <button type="button" class="btn btn-ghost btn-mini" data-act="icon"><span class="qm-zh">' + TEXT.zh.exportIcon + '</span><span class="qm-en">' + TEXT.en.exportIcon + '</span></button>',
      '  <button type="button" class="btn btn-ghost btn-mini" data-act="install"><span class="qm-zh">' + TEXT.zh.install + '</span><span class="qm-en">' + TEXT.en.install + '</span></button>',
      '</div>',
      '<p class="qm-data-note"></p>',
    ].join('\n');

    var style = document.createElement('style');
    style.textContent = STYLE;
    wrap.appendChild(style);

    wrap.addEventListener('click', function (event) {
      var btn = event.target.closest('[data-act]');
      if (!btn) { return; }
      var act = btn.getAttribute('data-act');
      if (act === 'export') { return doExport(wrap); }
      if (act === 'import') { return doImport(wrap); }
      if (act === 'clear') { return doClear(wrap); }
      if (act === 'icon') { return doIcon(wrap); }
      if (act === 'install') { return doInstall(wrap); }
    });
    return wrap;
  }

  function doExport(host) {
    call('/api/demo-backup').then(function (res) {
      download(res.file, res.text);
      note(host, res.file);
    }).catch(function (err) { note(host, tr('exportFail', { msg: err.message })); });
  }

  function doImport(host) {
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) { return; }
      file.text().then(function (text) {
        return call('/api/demo-import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-QingMan': '1' },
          body: JSON.stringify({ content: text }),
        });
      }).then(function (res) {
        note(host, tr('importDone', { n: (res.stats && res.stats.templates) || 0 }));
        setTimeout(function () { location.reload(); }, 900);
      }).catch(function (err) { note(host, tr('importFail', { msg: err.message })); });
    });
    input.click();
  }

  function doClear(host) {
    if (!window.confirm(tr('confirmClear'))) { return; }
    call('/api/demo-clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-QingMan': '1' },
      body: '{}',
    }).then(function () {
      note(host, tr('clearDone'));
      setTimeout(function () { location.reload(); }, 700);
    }).catch(function (err) { note(host, tr('clearFail', { msg: err.message })); });
  }

  function doIcon(host) {
    /* 复用 src 里那套「按当前皮肤画图标」的实现，避免两处各画一个 */
    import('./ui/launch-icon.js').then(function (mod) {
      return mod.renderLaunchIcon();
    }).then(function (ico) {
      if (!ico || !ico.length) { throw new Error('no-icon'); }
      downloadBytes('qingman-launch.ico', ico, 'image/x-icon');
      note(host, tr('iconDone'));
    }).catch(function (err) { note(host, tr('iconFail', { msg: err.message || err })); });
  }

  /* ---------- 安装到桌面（在线版唯一能得到的"真快捷方式"） ----------
   *
   * 网页写不了 .lnk（不知道路径、也没有本机程序可指向），但浏览器**自己**可以：
   * 站点有 manifest + service worker 时，`beforeinstallprompt` 会被触发，调用
   * `prompt()` 就由浏览器在桌面 / 开始菜单建一个真正的快捷方式 —— 指向已安装的应用，
   * 还能离线打开。这是"生成快捷方式"在浏览器里的等价物。
   *
   * ⚠ 事件可能在挂载前就触发，所以在**模块初始化**时就开始捕获，而不是等面板建好。 */

  var deferredPrompt = null;

  root.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();   /* 不接管的话 Chrome 会自己弹迷你条，位置不可控 */
    deferredPrompt = event;
  });

  function standalone() {
    try {
      return !!(root.matchMedia && root.matchMedia('(display-mode: standalone)').matches);
    } catch (err) { return false; }
  }

  function doInstall(host) {
    if (deferredPrompt) {
      var event = deferredPrompt;
      deferredPrompt = null;   /* 同一个 event 只能 prompt 一次 */
      event.prompt();
      note(host, tr('installOk'));
      return;
    }
    note(host, standalone() ? tr('installUsed') : tr('installManual'));
  }

  /* ---------- 挂载 ---------- */

  function mount() {
    if (document.getElementById('qmDataPanel')) { return; }
    var actions = document.querySelector('#dlgService .svc-adv-actions');
    var host = actions ? actions.parentNode : null;
    if (!host) { return; }
    var panel = buildPanel();
    panel.id = 'qmDataPanel';
    host.appendChild(panel);

    function syncLang() {
      var zh = isZh();
      panel.querySelectorAll('.qm-zh').forEach(function (el) { el.hidden = !zh; });
      panel.querySelectorAll('.qm-en').forEach(function (el) { el.hidden = zh; });
    }
    syncLang();
    document.addEventListener('qmlocalechange', syncLang);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})(typeof window !== 'undefined' ? window : globalThis);
