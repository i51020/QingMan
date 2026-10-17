/* 青蔓 QingMan · DOM 级对比度探针（由 tools/dom_probe.py 注入构建产物执行）。
 *
 * **为什么要它**：`tools/contrast_audit.py` 只算「设计令牌 A vs 令牌 B」。真实 DOM 上
 * 若某处写死了颜色、或把文字压在了错的变量上，词表看不见 —— 2026-10-17 的 s06
 * 「悬停行次要文字 4.35」就是这么漏出去的。
 *
 * **测什么**：8 个场景（主界面 + 5 个弹窗 + 2 个浮层）× 18 套主题。每个场景用真实
 * 触发器**点开**（不是强行改 CSS，否则内容没渲染、测了个空壳），然后只量该层内部
 * 的节点；主界面量全页。逐条按 WCAG 2.1 算「字色 vs 实际背景」。
 *
 * **怎么把结果送出来**：不靠 `--dump-dom`（它在 load 时就截快照，等不到异步渲染），
 * 而是 `fetch('/__qaE?<payload>')` 打回本地 http.server，由 dom_probe.py 从日志读。
 * `window.__QM_THEMES` 由 dom_probe.py 从 tokens.css + skins/*.css 现算后写在本文件前。
 */
(function () {
  /* 场景：name 用于报告；trigger 是要点的按钮 id；layer 是弹层 id（量它的内部）。 */
  var SCENARIOS = [
    { name: 'main', trigger: null, layer: null },
    { name: 'popSkin', trigger: 'btnSkin', layer: 'popSkin' },
    { name: 'popMore', trigger: 'btnMore', layer: 'popMore' },
    { name: 'popLang', trigger: 'btnLang', layer: 'popLang' },
    { name: 'dlgNewTemplate', trigger: 'btnNewTemplate', layer: 'dlgNewTemplate' },
    { name: 'dlgService', trigger: 'chipBackend', layer: 'dlgService' },
    { name: 'dlgBackups', trigger: 'btnBackups', layer: 'dlgBackups' },
    { name: 'dlgSupport', trigger: 'btnSupport', layer: 'dlgSupport' }
  ];
  /* 别的页面（help / support）没有这些触发器，只测整页。由 dom_probe.py 用 ?scen= 指定。 */
  (function () {
    var m = /[?&]scen=([^&]+)/.exec(location.search || '');
    if (!m) return;
    var want = decodeURIComponent(m[1]).split(',');
    SCENARIOS = SCENARIOS.filter(function (s) { return want.indexOf(s.name) >= 0; });
  })();

  function report(s) { try { fetch('/__qaE?' + encodeURIComponent(s)); } catch (e) {} }
  function srgb(c) { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function lum(p) { return 0.2126 * srgb(p[0]) + 0.7152 * srgb(p[1]) + 0.0722 * srgb(p[2]); }
  function parse(s) {
    var m = /rgba?\(([^)]+)\)/.exec(s || ''); if (!m) return null;
    var p = m[1].split(',').map(parseFloat);
    return { rgb: [p[0], p[1], p[2]], a: p.length > 3 ? p[3] : 1 };
  }
  function ratio(f, b) { var a = lum(f), c = lum(b); var h = Math.max(a, c), l = Math.min(a, c); return (h + 0.05) / (l + 0.05); }
  /* 往上找第一个「不透明」背景；半透明（rgba）就继续往上叠，实在找不到按白底算。 */
  function bgOf(el) {
    var n = el;
    while (n && n.nodeType === 1) {
      var c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a >= 0.95) return c.rgb;
      n = n.parentElement;
    }
    return [255, 255, 255];
  }
  /* 只取元素自己的文本节点，避免把子元素的字重复算到父元素头上。 */
  function ownText(el) {
    var t = '';
    for (var i = 0; i < el.childNodes.length; i += 1) {
      if (el.childNodes[i].nodeType === 3) t += el.childNodes[i].nodeValue;
    }
    return t.trim();
  }
  function measure(root) {
    var out = [];
    var all = (root || document.body).querySelectorAll('*');
    for (var i = 0; i < all.length; i += 1) {
      var el = all[i], st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      if (!el.offsetParent && st.position !== 'fixed') continue;   // 不可见（含折叠区、别层残留）
      var text = ownText(el); if (!text) continue;
      var fg = parse(st.color); if (!fg) continue;
      if (parseFloat(st.opacity || '1') < 0.9) continue;            // 故意做淡的元素，按设计意图放过
      var size = parseFloat(st.fontSize), weight = parseInt(st.fontWeight, 10) || 400;
      var large = size >= 24 || (size >= 18.66 && weight >= 700);
      var bg = bgOf(el), r = ratio(fg.rgb, bg);
      out.push({ t: text.slice(0, 14), c: (el.className || '').toString().slice(0, 22),
                 ratio: r, pass: r >= (large ? 3 : 4.5), fg: st.color, bg: 'rgb(' + bg.join(',') + ')' });
    }
    return out;
  }

  function esc() {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    var scrim = document.getElementById('scrim');
    if (scrim && !scrim.hidden) scrim.click();
  }
  function openLayer(sc) {
    esc();                                   // 先关掉上一个，避免叠层互相污染
    if (!sc.trigger) return null;
    var btn = document.getElementById(sc.trigger);
    if (btn) { btn.click(); }
    var node = sc.layer ? document.getElementById(sc.layer) : null;
    if (node && node.hidden) {               // 触发器没起到作用（或按钮不可用）就强行展开
      node.hidden = false;
      node.classList.add('is-open');
    }
    return node && !node.hidden ? node : null;
  }

  /* 等页面「安静下来」：DOM 节点数连续 4 次不变再开测，避免量到半渲染的空壳。 */
  function settle(done) {
    var last = -1, stable = 0, t0 = Date.now();
    (function tick() {
      var n = document.querySelectorAll('body *').length;
      if (n === last) { stable += 1; } else { stable = 0; last = n; }
      if ((stable >= 4 && Date.now() - t0 > 1200) || Date.now() - t0 > 12000) { done(); return; }
      setTimeout(tick, 200);
    })();
  }

  window.addEventListener('load', function () {
    /* **必须先把过渡与动画掐掉**：`.btn` 有 `transition: background .12s, color .12s`，
       每换一套主题、字色与底色都在 120ms 里爬向新值。若在爬的过程中量，就会量到
       「半路混合色」—— 2026-10-17 首轮八场景实测里「创建」按钮报 2.85 / 3.22 / 4.30
       三条假 FAIL 全是这么来的（实测算出的混合比例 α≈0.68，两边朝同一底色靠）。
       要审计的是**终态**配色，不是动画帧，所以这里直接把过渡关死。 */
    var kill = document.createElement('style');
    kill.textContent = '*,*::before,*::after{transition:none!important;animation:none!important}';
    document.head.appendChild(kill);
    setTimeout(function () {
      settle(function () {
        var out = [], s = 0;
        function nextScenario() {
          if (s >= SCENARIOS.length) { report('SUMMARY ' + JSON.stringify(out)); report('DONE'); return; }
          var sc = SCENARIOS[s];
          var layer = openLayer(sc);
          setTimeout(function () {
            var root = layer || (sc.layer ? null : document.body);
            if (!root) {                        // 层没打开 —— 如实记 0，别假装测过
              out.push({ scenario: sc.name, theme: '—', n: 0, bad: 0, worst: ['（层未打开，未测）'] });
              s += 1; nextScenario(); return;
            }
            var i = 0;
            function nextTheme() {
              if (i >= window.__QM_THEMES.length) { s += 1; nextScenario(); return; }
              var th = window.__QM_THEMES[i];
              Object.keys(th.vars).forEach(function (k) {
                document.documentElement.style.setProperty('--qm-' + k, th.vars[k]);
              });
              setTimeout(function () {
                var rows = measure(root);
                var bad = rows.filter(function (r) { return !r.pass; })
                              .sort(function (a, b) { return a.ratio - b.ratio; });
                out.push({ scenario: sc.name, theme: th.name, n: rows.length, bad: bad.length,
                           worst: bad.slice(0, 3).map(function (r) {
                             return r.t + ' | ' + r.ratio.toFixed(2) + ' | ' + r.fg + ' on ' + r.bg;
                           }) });
                i += 1; nextTheme();
              }, 90);
            }
            nextTheme();
          }, 700);
        }
        nextScenario();
      });
    }, 400);
  });
})();
