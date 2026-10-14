"""青蔓 QingMan · 无头浏览器冒烟（§P0-2 T7，V0.0.25；V0.0.29 扩 C-P3-5 / D-P3-2 / C-P3-1）。

把「**页面跑起来才现形**」的那一类缺陷固化为常驻脚本。与相邻两件工具的分工：

  * `tools/verify.py` —— 静态交付校验（语法 / 结构 / 指纹 / 守卫），不跑页面；
  * `tools/smoke.py`  —— HTTP 层端到端（接口语义，不需要浏览器）；
  * 本脚本            —— **运行时页面层**：真实浏览器加载真实页面，验证渲染与交互。

背景（全项目审查 `docs/审查报告_架构与逻辑_20261010.md`）：P1-1（帮助页每次切语言
成倍追加分节）与 P1-2（首屏默认示例不随语言且被永久落盘）两处缺陷**实测确认时
三项门禁（verify / unittest / smoke）全绿** —— 它们只在页面真正跑起来时才现形。
本脚本把它们变成常态守卫，而不是靠一次性的临时探针。

校验项：
  1. 探针完成（浏览器确实跑到最后一步并写出结果行）
  2. 页面载入无未捕获异常 / 无漏翻 / 无请求失败（扫浏览器控制台日志）
  3. 主界面·默认示例随语言（英文偏好下节点名必须为英文，无中文）
  4. 主界面·皮肤样式表已装载、模板库已接入（首屏两条异步链跑通）
  5. 帮助页·分节渲染幂等（切换语言后分节/导航计数不得累积；P1-1 回归位）
  6. 帮助页·语言切换联动 `<html lang>`
  7. 帮助页·版本徽标 = `VERSION` 且后端可达（`help-stale` 已摘除）
  8. 支持页·V0.0.18 拆页后仍完好
  9. 主界面·非法皮肤偏好回落出厂默认（C-P3-5 回归位，V0.0.29）
 10. 主界面·下拉箭头颜色随 `--qm-text-dim`（D-P3-2 回归位，V0.0.29）
 11. 主界面·目录树全量重建后保持滚动位置（C-P3-1 回归位，V0.0.29）

用法：
    python tools/browser_smoke.py [--keep] [--browser PATH] [--sandbox DIR]
                                  [--port N] [--budget MS]

退出码：0 全部通过（**未检测到浏览器则跳过并返回 0**）；1 存在失败项。

约定（§P0-2 T6）：
  * 全程在沙盒内进行 —— 复制 `src/`（与 `VERSION`、`templates/`）到沙盒后再起服务。
    原因：`config.DATA_DIR` 恒为 `<项目根>/data`，直接跑真实 `src/` 时首屏默认示例会
    经 `saveNow()` 写进**真实** `data/editor.json`。
  * 探针页写在**沙盒副本**的静态目录里，随沙盒一并清除，不落入主线。
  * 浏览器用户数据目录也落在沙盒内，localStorage 不污染本机浏览器配置。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

RESULTS: list[tuple[bool, str, str]] = []

# 控制台日志里**致命**的 token：命中即判定页面行为异常。
# `Uncaught`      —— 未捕获异常（脚本抛错 / 模块加载失败）；
# `[i18n] missing key` —— 漏翻（取词表缺键，界面会直接显示键名）；
# `[QingMan] request failed` —— 前端请求失败（接口或接线出错）。
# 注：`[QingMan] launch icon upload skipped` / `logo.svg unavailable` 属「尽力而为」的
# 装饰性动作，在无头环境下本就可能失败，**不计入失败**，仅在备注里提示。
FATAL_CONSOLE = ("Uncaught", "[i18n] missing key", "[QingMan] request failed")

# 探针启动时自报的一条日志 —— 用作「控制台日志通道可用」的**正面控制**（§P2-13）：
# 收得到它，才证明 `--enable-logging=stderr` 确实在投递；否则「无未捕获异常」的 PASS 不可信。
SELF_REPORT = "[qm-smoke] probe-boot"

BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

PROBE_NAME = "_probe_ui.html"

# 探针页：同源 iframe 驱动**真实页面**（不复制页面骨架，测的就是线上那份）。
# 全程事件驱动（iframe onload + setTimeout 轮询），不用 Promise 链 ——
# 无头浏览器的 `--virtual-time-budget` 不等待未决 Promise（经验教训）。
PROBE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>QingMan browser smoke probe</title>
</head>
<body>
<div id="out">START</div>
<script>
var out = document.getElementById('out');
console.log('[qm-smoke] probe-boot');   /* 正面控制：证明控制台日志通道确实在投递（§P2-13） */
var m = {};
var CJK = /[\\u4e00-\\u9fff]/;

function names(doc) {
  var list = doc.querySelectorAll('.tree-name');
  var arr = [];
  for (var i = 0; i < list.length; i += 1) { arr.push(list[i].textContent); }
  return arr;
}

function frame(url, probe, done) {
  var f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;left:-9999px;top:0;width:1100px;height:820px;border:0';
  f.onload = function () {
    var n = 240;
    (function tick() {
      var doc = f.contentDocument;
      var ok = false;
      try { ok = Boolean(doc) && Boolean(probe(doc)); } catch (e) { ok = false; }
      if (ok) { return done(doc); }
      if (n <= 0) { return done(doc); }
      n -= 1;
      setTimeout(tick, 25);
    }());
  };
  f.src = url;
  document.body.appendChild(f);
}

/* 阶段 1：英文偏好下的首屏默认示例（P1-2 回归位）+ 皮肤白名单 / 箭头随皮肤（C-P3-5 / D-P3-2）。
   先写偏好再建 iframe —— localStorage 与 iframe 同源共享，页面启动即读到。
   皮肤特意写入一个**非法**名：修复后页面须回落出厂默认（与"未选过"等价），
   故选这一档即可同时覆盖 C-P3-5（非法回落）与 D-P3-2（箭头色随 --qm-text-dim）。 */
try { localStorage.setItem('qm.lang', 'en-US'); } catch (e) {}
try { localStorage.setItem('qm.skin', 'not-a-real-skin'); } catch (e) {}

frame('./index.html', function (doc) {
  return doc.querySelectorAll('.tree-row').length > 0
    && doc.querySelectorAll('#templateList li').length > 0;
}, function (doc) {
  try {
    m.htmlLang = doc ? doc.documentElement.lang : '';
    m.idxRows = doc ? doc.querySelectorAll('.tree-row').length : -1;
    m.idxCjk = names(doc).filter(function (s) { return CJK.test(s); }).length;
    m.idxSkin = doc && doc.getElementById('skinLink') ? 1 : 0;
    m.tplRows = doc ? doc.querySelectorAll('#templateList li.tpl-row').length : -1;
    /* C-P3-5 / D-P3-2（V0.0.29；V0.0.40 迁移）：偏好已写入**非法**皮肤名 ——
       ① skinLink.href 不得指向该非法名，须回落出厂默认（否则装载失败 → 落裸色）；
       ② 顶栏配色随皮肤变量：下拉（.topbar-select）已退场，改钉图标按钮 #btnLang 的 color
          —— .icon-btn 的 color 取自 --qm-text-dim，须等于探针实色，且非旧版烘死的
          #6d7278 = rgb(109, 114, 120)（图标是 currentColor mask，故 color 即图标色）。 */
    var skinLink = doc ? doc.getElementById('skinLink') : null;
    m.badSkinHref = skinLink ? (skinLink.getAttribute('href') || '') : '';
    var win = doc ? doc.defaultView : null;
    var iconBtn = doc ? doc.getElementById('btnLang') : null;
    if (win && iconBtn) {
      var probeEl = doc.createElement('i');
      probeEl.style.color = 'var(--qm-text-dim)';
      doc.body.appendChild(probeEl);
      m.dimColor = win.getComputedStyle(probeEl).color;
      probeEl.parentNode.removeChild(probeEl);
      m.arrowColor = win.getComputedStyle(iconBtn).color;
    }
    /* C-P3-1（V0.0.29）：全量重建不得把目录树滚动位置弹回顶部。
       默认示例较短、正常高度下不滚动，故用内联 max-height 把滚动容器压到 60px 逼出滚动；
       记下 scrollTop → 点一个行（store.set → 同步 render 全量重建）→ 重建后 scrollTop 须保持。
       另校验"确实重建了"（首行节点被替换），避免重建未发生时的假通过。 */
    var tw = doc ? doc.getElementById('treeWrap') : null;
    var rows = doc ? doc.querySelectorAll('.tree-row') : null;
    if (tw && rows && rows.length > 1) {
      tw.style.maxHeight = '60px';
      tw.scrollTop = 40;
      m.scrollBefore = tw.scrollTop;
      var firstRow = rows[0];
      rows[1].dispatchEvent(new MouseEvent('click', { bubbles: true }));
      m.scrollAfter = tw.scrollTop;
      m.reRendered = (doc.querySelector('.tree-row') !== firstRow) ? 1 : 0;
    }
    /* C-P2-1 回归位：皮肤名是取词键（skin.N）→ 换语言须重建网格卡片。
       V0.0.40：下拉退场，走「点 #popLang 的 menu-item → setLocale → qmlocalechange →
       skin-picker.build()」这条**真实用户路径**（menu-item 的 click 监听器与手动点击同源）。 */
    var langMenu = doc ? doc.getElementById('popLang') : null;
    var skinGrid = doc ? doc.getElementById('skinGrid') : null;
    m.hasSkinGrid = skinGrid ? 1 : 0;
    var firstSkinName = function () {
      var nm = skinGrid ? skinGrid.querySelector('.sw-card .nm') : null;
      return nm ? nm.textContent : '';
    };
    /* V0.0.40 · 手册 10.2 节 #13：目标位置「选择…」按钮 —— 只采集「在位」与「取词文案」，
       不伪造点击（真点会弹原生目录框，自动化环境不可控）。 */
    var pickBtn = doc ? doc.getElementById('btnPickTarget') : null;
    var pickBtnText = function () { return pickBtn ? (pickBtn.textContent || '').trim() : ''; };
    m.pickTargetBtn = pickBtn ? 1 : 0;
    /* V0.0.41 · 手册 9.2 节 #7 / 10.2 节 #4：模板编辑区「新建模板」按钮 —— 与上面同理，
       这里只采集「在位」与「取词文案」（弹窗开合放在阶段 1 末尾实测，见下）。 */
    var newBtnEl = doc ? doc.getElementById('btnNewTemplate') : null;
    var newBtnText = function () { return newBtnEl ? (newBtnEl.textContent || '').trim() : ''; };
    m.tplNewBtn = newBtnEl ? 1 : 0;
    var pickLocale = function (value) {
      var items = langMenu ? langMenu.querySelectorAll('.menu-item') : [];
      for (var li = 0; li < items.length; li += 1) {
        if (items[li].getAttribute('data-locale') === value) {
          items[li].dispatchEvent(new MouseEvent('click', { bubbles: true }));
          return true;
        }
      }
      return false;
    };
    if (langMenu && skinGrid && skinGrid.children.length) {
      m.skinEn = firstSkinName();
      m.pickTargetEn = pickBtnText();
      m.tplNewEn = newBtnText();
      pickLocale('zh-CN');
      m.skinZh = firstSkinName();
      m.pickTargetZh = pickBtnText();
      m.tplNewZh = newBtnText();
      pickLocale('en-US');   /* 复位，避免影响阶段 2 的初始语言 */
    }
    /* V0.0.39 / 十三.4：swatch 在页面上的**唯一可见效果**就是网格卡片的**排列顺序**
       （skin-picker 按 swatch[0] 背景明度亮 → 暗排序）；把它整条抓出来，
       与 Python 侧按同一公式复算的期望序列逐项比对。 */
    if (skinGrid) {
      var cards = skinGrid.querySelectorAll('.sw-card');
      var order = [];
      for (var oi = 0; oi < cards.length; oi += 1) { order.push(cards[oi].getAttribute('data-file')); }
      m.skinOrder = order.join(',');
      m.skinCount = order.length;
    }
    /* C-P3-2 / C-P3-3（V0.0.32）：拖拽落点**预判**「自身 / 自身子孙」+ 高亮不因划子元素闪烁。
       合成 DragEvent 走**真实监听器**（dataTransfer 用 new DataTransfer()），不做静态断言。
       目录行用图标码点判定（📁 U+1F4C1）—— 走 codePointAt 而非字面量，
       避开多层转义（同 §P2-18 把 `\\u4e00` 换成 `CJK` 标识符的教训）。 */
    if (doc && win && typeof win.DragEvent === 'function') {
      var allRows = doc.querySelectorAll('.tree-row');
      var isDirRow = function (r) {
        var ic = r.querySelector('.tree-icon');
        return !!ic && ic.textContent.codePointAt(0) === 0x1F4C1;
      };
      var rowDepth = function (r) {
        var d = 0, p = r.parentNode;
        while (p && p !== doc) {
          if (p.classList && p.classList.contains('tree-children')) { d += 1; }
          p = p.parentNode;
        }
        return d;
      };
      /* A = 被拖节点：**非根**、且有目录子孙的目录行（默认示例里是 materials）；
         C = 非法落点（A 的目录子孙）；D = 合法落点（不在 A 子树内、也非根的另一目录行）。 */
      var A = null, C = null, D = null, i, j;
      for (i = 0; i < allRows.length; i += 1) {
        if (!isDirRow(allRows[i]) || rowDepth(allRows[i]) < 1) { continue; }
        var inner = allRows[i].parentNode.querySelectorAll('.tree-row');
        var cand = null;
        for (j = 1; j < inner.length; j += 1) {
          if (isDirRow(inner[j])) { cand = inner[j]; break; }
        }
        if (cand) { A = allRows[i]; C = cand; break; }
      }
      if (A) {
        for (i = 0; i < allRows.length; i += 1) {
          if (!isDirRow(allRows[i]) || rowDepth(allRows[i]) < 1) { continue; }
          if (!A.parentNode.contains(allRows[i])) { D = allRows[i]; break; }
        }
      }
      if (A && C && D) {
        var dt = new win.DataTransfer();
        var fire = function (el, type, init) {
          var o = { bubbles: true, cancelable: true, dataTransfer: dt };
          for (var k in (init || {})) { o[k] = init[k]; }
          var ev = new win.DragEvent(type, o);
          el.dispatchEvent(ev);
          return ev;
        };
        fire(A, 'dragstart');
        m.dragSelf = fire(A, 'dragover').defaultPrevented ? 0 : 1;
        var eDesc = fire(C, 'dragover');
        m.dragDesc = (eDesc.defaultPrevented || C.classList.contains('is-drop-target')) ? 0 : 1;
        var eOk = fire(D, 'dragover');
        m.dragOk = (eOk.defaultPrevented && D.classList.contains('is-drop-target')) ? 1 : 0;
        fire(D, 'dragleave', { relatedTarget: D.querySelector('.tree-name') });
        m.dlChild = D.classList.contains('is-drop-target') ? 1 : 0;
        fire(D, 'dragleave', { relatedTarget: doc.body, clientX: 0, clientY: 0 });
        m.dlOut = D.classList.contains('is-drop-target') ? 0 : 1;
        fire(A, 'dragend');
      } else {
        /* 默认示例形态变了 → 明示找不到落点，让三项判定明确 FAIL，不静默略过 */
        m.dragSelf = -1; m.dragDesc = -1; m.dragOk = -1; m.dlChild = -1; m.dlOut = -1;
      }
    }
    /* C-P3-4（V0.0.32）：连续 40 次「目标位置为空」的生成 → 提示条须被上限截住。
       走真实按钮监听器（`btnGenerate` 在目标为空时 toast 后即早退，不改数据）。 */
    var gen = doc ? doc.getElementById('btnGenerate') : null;
    if (gen) {
      for (var g = 0; g < 40; g += 1) {
        gen.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      }
      m.toastN = doc.querySelectorAll('#toastHost .toast').length;
    }
    /* 6E：模板目录绑定行 + 三个入口按钮必须在位（绑定 UI 的骨架） */
    m.tplDirRow = doc ? doc.querySelectorAll('#tplDirRow').length : -1;
    m.tplDirPath = (doc && doc.getElementById('tplDirPath'))
      ? doc.getElementById('tplDirPath').textContent : '';
    m.tplDirBtns = doc
      ? doc.querySelectorAll('#btnPickDir, #btnRefreshTpl, #btnImportTemplate').length : -1;
    /* 6E：模板行右键菜单项齐备 —— 在行上派发 contextmenu，读 #ctxMenu 的按钮数 / 文案。
       走真实监听器（li 上的 contextmenu → openTemplateContextMenu → ctx-menu.showAt），
       不做静态断言。 */
    var tplFirstRow = doc ? doc.querySelector('#templateList li.tpl-row') : null;
    if (tplFirstRow && win) {
      tplFirstRow.dispatchEvent(new win.MouseEvent('contextmenu', {
        bubbles: true, cancelable: true, clientX: 40, clientY: 40,
      }));
      var menu = doc.getElementById('ctxMenu');
      var mbtns = menu ? menu.querySelectorAll('button') : [];
      m.tplMenuN = mbtns.length;
      var labels = [];
      for (var bi = 0; bi < mbtns.length; bi += 1) { labels.push(mbtns[bi].textContent); }
      m.tplMenu = labels.join('/');
      doc.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));   /* 关掉菜单 */
    }
  } catch (e) { m.err1 = String(e && e.message ? e.message : e); }
  /* V0.0.42 · 手册 10.2 节 #12「根文件夹名与第一个目录逻辑重设计」—— 方案 C：
     根节点名**即**「根文件夹名」。走真实用户路径（选中根行 → 工具栏「重命名」），
     window.prompt 临时替换为受控返回值；断言点只看「摘要 / 树区是否随根名变」，
     不比对具体文案 → 与 i18n 解耦。 */
  var sumEl = doc ? doc.getElementById('genSummary') : null;
  var rootRowEl = doc ? doc.querySelector('.tree-row') : null;
  var btnRenameEl = doc ? doc.getElementById('btnRename') : null;
  m.rootProbe = (sumEl && rootRowEl && btnRenameEl && win) ? 1 : 0;
  if (m.rootProbe === 1) {
    var realPrompt = win.prompt;
    var fireOn = function (el, type) {
      el.dispatchEvent(new win.MouseEvent(type, { bubbles: true }));
    };
    try {
      m.rootSumBefore = sumEl.textContent || '';
      m.rootNameBefore = names(doc)[0] || '';
      win.prompt = function () { return 'QmRootX'; };   /* ① 根名 → QmRootX */
      fireOn(rootRowEl, 'click');
      fireOn(btnRenameEl, 'click');
      m.rootSumAfter = sumEl.textContent || '';
      m.rootNameAfter = names(doc)[0] || '';
      win.prompt = function () { return ''; };          /* ② 清空 → 不建根 */
      fireOn(btnRenameEl, 'click');
      m.rootSumBlank = sumEl.textContent || '';
      m.rootNameBlank = names(doc)[0] || '';
    } catch (e) {
      m.rootErr = String(e && e.message ? e.message : e);
    } finally {
      win.prompt = realPrompt;
    }
  }
  /* V0.0.43 · UI 定版差集 G 组：工具栏三分组（编辑 / 视图 / 输出）。
     判定锚点是「每颗按钮落在第几个分组里」—— 只数分组个数会被三个空壳 div 骗过，
     故把 8 颗按钮逐个回溯到所属 .tb-group，期望序列 00000112
     （撤销/重做/加子/改名/删除 属编辑，展开/折叠 属视图，生成 属输出）。 */
  var tbEl = doc ? doc.getElementById('toolbar') : null;
  if (tbEl && win) {
    var groups = tbEl.querySelectorAll('.tb-group');
    m.gGroups = groups.length;
    var labN = 0;
    for (var gi = 0; gi < groups.length; gi += 1) {
      if ((groups[gi].getAttribute('aria-label') || '').trim()) { labN += 1; }
    }
    m.gLabels = labN;
    var gIds = ['btnUndo', 'btnRedo', 'btnAddChild', 'btnRename', 'btnDelete',
                'btnExpandAll', 'btnCollapseAll', 'btnGenerate'];
    var gCode = '';
    for (var ga = 0; ga < gIds.length; ga += 1) {
      var gb = doc.getElementById(gIds[ga]);
      var gAt = -1;
      for (var gj = 0; gb && gj < groups.length; gj += 1) {
        if (groups[gj].contains(gb)) { gAt = gj; break; }
      }
      gCode += String(gAt);
    }
    m.gMap = gCode;
  }
  /* V0.0.43 · UI 定版差集 H 组：检视器「属性 ⇄ 源码」。
     走真实按钮（#btnInspSrc / #btnInspProp）。四件事一起证：分段控件两档齐备、
     切过去面板真的换、源码栏是**可解析的 JSON 且含实际子节点名**（证走的是
     toPlainTree 序列化，而不是随手拼的字符串）、切回来复原。 */
  var segEl = doc ? doc.getElementById('inspMode') : null;
  var srcPane = doc ? doc.getElementById('inspSrcPane') : null;
  var propPane = doc ? doc.getElementById('inspPropPane') : null;
  var srcHost = doc ? doc.getElementById('inspSource') : null;
  var hSrcBtn = doc ? doc.getElementById('btnInspSrc') : null;
  var hPropBtn = doc ? doc.getElementById('btnInspProp') : null;
  m.hSeg = segEl ? segEl.querySelectorAll('.seg-btn').length : -1;
  if (segEl && srcPane && propPane && srcHost && hSrcBtn && hPropBtn && win) {
    hSrcBtn.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
    m.hPropHidden = propPane.hidden ? 1 : 0;      /* 期望 1 */
    m.hSrcShown = srcPane.hidden ? 0 : 1;         /* 期望 1 */
    var srcObj = null;
    try { srcObj = JSON.parse((srcHost.textContent || '').trim()); } catch (e) { srcObj = null; }
    m.hJson = (srcObj && typeof srcObj === 'object' && !Array.isArray(srcObj)) ? 1 : 0;
    var firstChildName = doc.querySelector('.tree-children .tree-row .tree-name');
    m.hHasChild = (m.hJson === 1 && firstChildName
      && Object.prototype.hasOwnProperty.call(srcObj, firstChildName.textContent)) ? 1 : 0;
    try { m.hPref = win.localStorage.getItem('qm.inspMode') || ''; } catch (e) { m.hPref = '?'; }
    hPropBtn.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
    m.hBack = (propPane.hidden ? 0 : 1) + (srcPane.hidden ? 1 : 0);   /* 期望 2 */
  }
  /* V0.0.43 · UI 定版差集 F 组：多选批量。
     全部走真实用户路径（Ctrl+单击 / Shift+单击 / Esc / Ctrl+A / 批量条按钮 / window.confirm），
     不直接改 store。注意：每次交互都会触发**全量重建**，旧行元素随即失效 ——
     故每一拍都重新查询，只以「行下标」为稳定标识。 */
  var fBar = doc ? doc.getElementById('batchBar') : null;
  var fInfo = doc ? doc.getElementById('batchInfo') : null;
  var fRowsFn = function () { return doc ? doc.querySelectorAll('.tree-row') : []; };
  var fClick = function (node, ev) {
    if (node) { node.dispatchEvent(new win.MouseEvent('click', ev || { bubbles: true })); }
  };
  var fEsc = function () {
    doc.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  };
  m.fBar0 = fBar ? (fBar.hidden ? 0 : 1) : -1;    /* 初始：无多选 → 不得显示，期望 0 */
  if (fBar && fInfo && win) {
    /* ① 离散多选：Ctrl+单击两行（根行不可多选，故从下标 1 起） */
    fClick(fRowsFn()[1], { bubbles: true, ctrlKey: true });
    fClick(fRowsFn()[2], { bubbles: true, ctrlKey: true });
    m.fMulti = doc.querySelectorAll('.tree-row.is-multi').length;       /* 期望 2 */
    m.fBarOn = fBar.hidden ? 0 : 1;                                     /* 期望 1 */
    m.fInfo = (fInfo.textContent || '').trim() ? 1 : 0;
    m.fAgg = doc.getElementById('propNote').disabled ? 1 : 0;           /* 聚合态禁用 note */
    fEsc();
    m.fBarOff = fBar.hidden ? 1 : 0;                                    /* 期望 1 */
    m.fMultiOff = doc.querySelectorAll('.tree-row.is-multi').length;     /* 期望 0 */
    /* ② Shift 范围选择：单击起点 → Shift+单击终点 → 取**可视序**连续一段 */
    fClick(fRowsFn()[1]);
    fClick(fRowsFn()[3], { bubbles: true, shiftKey: true });
    m.fShift = doc.querySelectorAll('.tree-row.is-multi').length;        /* 期望 3 */
    fEsc();
    /* ③ Ctrl+A：全选「根之下」全部节点（树此时全展开，故 = 可见行数 - 1） */
    m.fVisible = fRowsFn().length;
    doc.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'a', ctrlKey: true, bubbles: true }));
    m.fAll = doc.querySelectorAll('.tree-row.is-multi').length;
    m.fAllBar = fBar.hidden ? 0 : 1;
    fClick(doc.getElementById('btnBatchClear'));
    m.fBarOff2 = fBar.hidden ? 1 : 0;
    /* ④ 批量删除须**只作用于最外层祖先**（需求草案 2.4 节 #1）。
       取「有子孙的第一行」+「它的第一个子孙」造父子同选，并记下父行子树的**行数**：
       实现正确时删掉的行数应恰等于该值（子被父覆盖），而非「父 + 子各删一次」。
       先跑一次取消路径（confirm=false）证「取消即不动树」，再跑确认路径。 */
    var pIdx = -1;
    var rs = fRowsFn();
    for (var fi = 1; fi < rs.length; fi += 1) {
      if (rs[fi].parentNode.querySelectorAll('.tree-row').length > 1) { pIdx = fi; break; }
    }
    var realConfirm = win.confirm;
    if (pIdx >= 0) {
      m.fDropN = fRowsFn()[pIdx].parentNode.querySelectorAll('.tree-row').length;
      fClick(fRowsFn()[0]);                                   /* 先回到单选，避免残留集合参与 */
      fClick(fRowsFn()[pIdx], { bubbles: true, ctrlKey: true });
      fClick(fRowsFn()[pIdx].parentNode.querySelectorAll('.tree-row')[1], { bubbles: true, ctrlKey: true });
      m.fDedupSet = doc.querySelectorAll('.tree-row.is-multi').length;   /* 期望 2（父 + 子） */
      m.fBefore = fRowsFn().length;
      var delBtn = doc.getElementById('btnBatchDelete');
      try {
        win.confirm = function (msg) {                       /* 取消路径：树不得变动 */
          m.fConfirmMsg = String(msg == null ? '' : msg);    /* 文案里带「实际将摘除的项数」 */
          return false;
        };
        fClick(delBtn);
        m.fCancelKept = fRowsFn().length === m.fBefore ? 1 : 0;
        win.confirm = function () { return true; };          /* 确认路径：按最外层祖先删 */
        fClick(delBtn);
        m.fAfter = fRowsFn().length;
        m.fBarClear = fBar.hidden ? 1 : 0;
      } catch (e) {
        m.fErr = String(e && e.message ? e.message : e);
      } finally {
        win.confirm = realConfirm;
      }
    } else {
      m.fDropN = -1; m.fDedupSet = -1; m.fBefore = -1; m.fAfter = -1;
      m.fCancelKept = -1; m.fBarClear = -1;
    }
  }
  /* V0.0.41 · 手册 9.2 节 #7 / 10.2 节 #4：「新建模板」弹窗**实测**（不是静态断言）。
     走真实路径：点 #btnNewTemplate → newTemplateFlow() 是 async（先 await /api/templates
     填起点下拉，再 layers.open），故点完等一拍再读。读完**立刻**用 [data-close] 关窗 ——
     弹窗开着会给 #app 置 inert，阶段 2 要驱动页面其余部分。 */
  var newBtn = doc ? doc.getElementById('btnNewTemplate') : null;
  var newDlg = doc ? doc.getElementById('dlgNewTemplate') : null;
  m.tplNewDlg = newDlg ? 1 : 0;
  if (newBtn && newDlg && win) {
    newBtn.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
    setTimeout(function () {
      try {
        m.tplNewOpen = newDlg.hidden ? 0 : 1;
        var sel = doc.getElementById('newTplBase');
        m.tplNewBaseN = sel ? sel.options.length : -1;
        m.tplNewBaseText = sel && sel.options.length ? sel.options[0].textContent : '';
        var closer = newDlg.querySelector('[data-close]');
        if (closer) { closer.dispatchEvent(new win.MouseEvent('click', { bubbles: true })); }
        /* layer.js 的 hide() 先**同步**摘 .is-open，再等 170ms 动画后才置 hidden。
           故分两拍读：同步态证明「点了就立刻响应」，延时态证明「真的 display:none 了」。 */
        m.tplNewClosing = newDlg.classList.contains('is-open') ? 1 : 0;
        setTimeout(function () {
          m.tplNewClosed = newDlg.hidden ? 1 : 0;
          pollProbe(doc);
        }, 260);
      } catch (e) {
        m.errNew = String(e && e.message ? e.message : e);
        pollProbe(doc);
      }
    }, 260);
  } else {
    pollProbe(doc);
  }
});

/* 6E 轮询**实证**：向模板库导入一套 → 等 ≥1 个轮询周期（虚拟时间会把 2.5s 定时器快进）
   → 列表须**自动**变成 2 行。这才证明轮询真的在干活，而不仅仅是「没把界面弄坏」。 */
function pollProbe(doc) {
  var list = doc ? doc.getElementById('templateList') : null;
  var win = doc ? doc.defaultView : null;
  if (!list || !win || typeof win.fetch !== 'function') {
    m.pollBefore = -1;
    return phase2();
  }
  m.pollBefore = list.querySelectorAll('li.tpl-row').length;
  win.fetch('/api/templates/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-QingMan': '1' },
    body: JSON.stringify({ filename: '探针轮询.md', content: '# 探针轮询\\n- 甲/\\n' }),
  }).then(function () {
    setTimeout(function () {
      m.pollAfter = list.querySelectorAll('li.tpl-row').length;
      phase2();
    }, 2600);
  }).catch(function (e) {
    m.pollErr = String(e && e.message ? e.message : e);
    phase2();
  });
}

/* 阶段 2：帮助页分节幂等（P1-1 回归位）+ 语言切换 + 版本徽标。
   探针只等「后端实测值已回来」（help-stale 摘除），随后用页面自己的语言下拉驱动切换 ——
   走的是真实用户路径（select change → setLocale → qmlocalechange → renderSections）。 */
function phase2() {
  frame('./help.html', function (doc) {
    var cell = doc.getElementById('aboutVersion');
    return doc.querySelectorAll('.help-section').length > 0
      && Boolean(cell) && !cell.classList.contains('help-stale');
  }, function (doc) {
    try {
      m.secBefore = doc.querySelectorAll('.help-section').length;
      m.navBefore = doc.querySelectorAll('#helpNavList li').length;
      var chip = doc.getElementById('helpChipVersion');
      m.chip = chip ? chip.textContent : '';
      var cell = doc.getElementById('aboutVersion');
      m.stale = cell ? (cell.classList.contains('help-stale') ? 1 : 0) : -1;
      var sel = doc.getElementById('helpLangSelect');
      m.hasSelect = sel ? 1 : 0;
      if (sel) {
        sel.value = 'en-US';
        sel.dispatchEvent(new Event('change'));
        m.secEn = doc.querySelectorAll('.help-section').length;
        m.langEn = doc.documentElement.lang;
        sel.value = 'zh-CN';
        sel.dispatchEvent(new Event('change'));
        m.secZh = doc.querySelectorAll('.help-section').length;
        m.navZh = doc.querySelectorAll('#helpNavList li').length;
        m.langZh = doc.documentElement.lang;
      }
    } catch (e) { m.err2 = String(e && e.message ? e.message : e); }
    phase3();
  });
}

/* 阶段 3：支持页（V0.0.18 从帮助页拆出，应保持完好） */
function phase3() {
  frame('./support.html', function (doc) {
    return doc.querySelectorAll('.help-qr').length > 0;
  }, function (doc) {
    try {
      m.qr = doc.querySelectorAll('.help-qr').length;
      m.thanks = doc.querySelectorAll('.help-thanks').length;
    } catch (e) { m.err3 = String(e && e.message ? e.message : e); }
    var parts = [];
    for (var k in m) {
      if (Object.prototype.hasOwnProperty.call(m, k)) { parts.push(k + '=' + m[k]); }
    }
    out.textContent = 'RESULT ' + parts.join(' | ');
  });
}
</script>
</body>
</html>
"""


def check(ok: bool, name: str, note: str = "") -> None:
    RESULTS.append((bool(ok), name, note))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_browser(explicit: str | None) -> str | None:
    """按 `--browser` → 环境变量 `QM_BROWSER` → 常见安装路径 → PATH 的顺序探测。"""
    for candidate in (explicit, os.environ.get("QM_BROWSER")):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    for name in ("msedge", "msedge.exe", "chrome", "chrome.exe", "chromium", "chromium.exe"):
        hit = shutil.which(name)
        if hit:
            return hit
    return None


def browser_drivable(path: str, timeout: float = 25.0) -> tuple[bool, str]:
    """前置探测：该可执行文件能否被**无头驱动**（`--dump-dom` 是否产出 DOM）。

    像夸克这类「启动器语义」的 exe，命令行契约不转发 —— `--headless=new --dump-dom`
    会静默退出、stdout 为空。那属于**环境不支持**，应显式跳过，而非判成
    「探针完成 FAIL」（把环境问题误读成页面缺陷，§P2-11）。
    """
    with tempfile.TemporaryDirectory(prefix="qm_browser_probe_") as prof:
        try:
            proc = subprocess.run(
                [path, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
                 f"--user-data-dir={prof}", "--dump-dom", "about:blank"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"无法启动：{exc}"
    if not (proc.stdout or "").strip():
        return False, "headless `--dump-dom` 无任何输出（疑似启动器语义 / 非 Chromium）"
    return True, ""


def sandbox_base() -> Path:
    """`--keep` / `--sandbox` 缺省时的沙盒父目录（§P2-10：不再硬编码绝对盘符路径）。

    环境变量 `QM_SANDBOX` 优先；否则取**项目根的上两级**下的 `_sandbox/`
    —— 与历史约定 `D:/Data/WorkBuddy/_sandbox` 等价，但随项目位置自动跟随。
    """
    env = os.environ.get("QM_SANDBOX", "").strip()
    return Path(env) if env else (PROJECT_ROOT.parent.parent / "_sandbox")


def wait_health(port: int, seconds: float) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.3)
    return False


def as_int(value, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def first_int(text: str, default: int = -1) -> int:
    """取字符串里第一段数字。

    用途：批量删除的确认文案是**取词**结果（`tree.batchDeleteConfirm`），随语言变化；
    但其中「实际将摘除的顶层项数」是唯一随实现而异的量。故只抽数字、不比对整句 ——
    与 i18n 解耦（改文案不会误伤本判定）。
    """
    m = re.search(r"\d+", text or "")
    return int(m.group(0)) if m else default


def expected_skin_order() -> str:
    """按 `skins.js` 的 `swatch[0]`（背景色）明度**亮 → 暗**复算期望的网格顺序。

    与 `src/web/js/ui/skin-picker.js` 的 `luma()` 用**同一公式**（WCAG 相对亮度）。
    此处**独立复算**，不调用页面函数 —— 调页面函数等于「拿页面证明它自己」
    （同 §P2-8 清单 digest「不调用工具函数」的道理）。
    """
    reg = SRC_DIR / "web/js/i18n/skins.js"
    if not reg.is_file():
        return ""
    entries = re.findall(
        r"file:\s*'([^']+)',\s*label:\s*'[^']+',\s*swatch:\s*\[\s*'([^']+)'",
        reg.read_text(encoding="utf-8"))

    def _luma(hexv: str) -> float:
        s = hexv.strip().lstrip("#")
        r, g, b = (int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))

        def _ch(c: float) -> float:
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * _ch(r) + 0.7152 * _ch(g) + 0.0722 * _ch(b)

    ordered = sorted(entries, key=lambda e: _luma(e[1]), reverse=True)
    return ",".join(f for f, _ in ordered)


def parse_metrics(stdout: str) -> dict[str, str] | None:
    """从 `--dump-dom` 的输出里取探针写下的 `RESULT k=v | k=v` 行。

    锚定到探针的输出容器 —— 脚本源码里也有 `'RESULT '` 这个字面量，
    宽松匹配会连源码一起命中（实测：会把 `RESULT ' + parts.join(...)` 捞进来）。
    §P2-12：**已去掉宽松兜底分支** —— 只认 `<div id="out">RESULT …</div>`；
    取不到锚定的结果行即返回 None（宁可 FAIL，也不捞源码字面量假通过）。
    """
    match = re.search(r'<div id="out">RESULT ([^<]*)</div>', stdout)
    if not match:
        return None
    metrics: dict[str, str] = {}
    for part in match.group(1).split("|"):
        key, sep, value = part.strip().partition("=")
        if sep:
            metrics[key.strip()] = value.strip()
    return metrics or None


def console_lines(stderr: str, origin: str) -> list[str]:
    """浏览器控制台日志中**属于本项目页面**的那几行。

    必须过滤两类噪声，否则「无未捕获异常」这一项会被污染：
      * `chrome-extension://` / `devtools://` —— 浏览器自身扩展的日志
        （实测：本机 Edge 的 ProtocolLaunch 扩展每次都会打一条）；
      * 非本服务 origin 的来源 —— 只认 `<origin>/...`，即探针页与其同源 iframe。
    """
    picked = []
    for line in stderr.splitlines():
        if "INFO:CONSOLE" not in line and "ERROR:CONSOLE" not in line:
            continue
        if "chrome-extension://" in line or "devtools://" in line:
            continue
        if origin and f"source: {origin}" not in line:
            continue
        picked.append(line)
    return picked


def run_browser(browser: str, url: str, profile: Path, budget: int, timeout: float):
    args = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--enable-logging=stderr",          # 让未捕获异常 / 漏翻告警可见（本脚本的核心抓手）
        f"--user-data-dir={profile}",
        f"--virtual-time-budget={budget}",
        "--dump-dom",
        url,
    ]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return proc.stdout or "", proc.stderr or "", proc.returncode


def toast_cap() -> int:
    """从 `src/web/js/ui/toast.js` 读「同时显示提示条」上限（C-P3-4，V0.0.32）。

    刻意**不把上限硬编码在判定里**：`toast.js` 是唯一事实源，改上限只需改源码一处，
    页面级断言自动跟随，不会出现「源码改了、断言还在按旧数判」的漂移。
    读不到常量（文件缺失 / 被改名）返回 -1 → 判定 FAIL，不静默放行。
    """
    path = SRC_DIR / "web" / "js" / "ui" / "toast.js"
    if not path.is_file():
        return -1
    match = re.search(r"const\s+MAX_TOASTS\s*=\s*(\d+)", path.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else -1


# V0.0.43 · G 组：工具栏 8 颗按钮所属分组的期望序列（5 编辑 / 2 视图 / 1 输出）。
#   顺序 = btnUndo, btnRedo, btnAddChild, btnRename, btnDelete, btnExpandAll,
#   btnCollapseAll, btnGenerate —— 改分组即须同步此处。
EXPECT_GROUP_MAP = "00000112"

def verify_metrics(metrics: dict[str, str], expected_version: str, expect_templates: bool) -> None:
    console_free = metrics.get("htmlLang") == "en-US"
    rows = as_int(metrics.get("idxRows"))
    cjk = as_int(metrics.get("idxCjk"))
    check(console_free and rows >= 5 and cjk == 0,
          "主界面·默认示例随语言",
          f"lang={metrics.get('htmlLang')} 节点 {rows} 行 / 含中文名 {cjk} 个"
          + ("" if cjk == 0 else "（P1-2 回归：示例未随语言）"))

    check(as_int(metrics.get("idxSkin")) == 1, "主界面·皮肤样式表已装载",
          f"skinLink={'有' if as_int(metrics.get('idxSkin')) == 1 else '无'}")

    skin_en = metrics.get("skinEn", "")
    skin_zh = metrics.get("skinZh", "")
    skin_i18n_ok = bool(skin_en and skin_zh and skin_en != skin_zh
                        and re.search(r"[\u4e00-\u9fff]", skin_zh or ""))
    check(skin_i18n_ok, "主界面·皮肤网格随语言刷新",
          f"en={skin_en!r} → zh={skin_zh!r}"
          + ("" if skin_i18n_ok else "（C-P2-1 回归：换语言后皮肤名未重建）"))

    # V0.0.39 / 十三.4：swatch 在页面上的**唯一可见效果** = 网格卡片的排列顺序（按 swatch[0]
    # 背景明度亮 → 暗）。期望序列由 Python 侧按同一公式独立复算（见 expected_skin_order）。
    # 它同时锁住三件事：15 款全在册 · swatch 数据正确 · 排序逻辑未被改坏。
    skin_order = metrics.get("skinOrder", "")
    exp_order = expected_skin_order()
    order_ok = bool(skin_order) and skin_order == exp_order
    if order_ok:
        parts = skin_order.split(",")
        order_note = f"{len(parts)} 款 · 首 {parts[0]} · 末 {parts[-1]}"
    else:
        order_note = f"实得={skin_order or '(空)'} 期望={exp_order or '(空)'}"
    check(order_ok, "主界面·皮肤网格按背景明度排序（V0.0.39）", order_note)

    # V0.0.40 · 手册 10.2 节 #13：目标位置「选择…」按钮。不伪造点击（真点会弹原生目录框，
    # 自动化环境不可控），改证「按钮在位 + 文案随语言刷新」—— 后者即证明该按钮走 i18n
    # 取词（键闭包成立）且 applyStatic 覆盖到它（data-i18n / data-i18n-title 均被替换）。
    pick_en = metrics.get("pickTargetEn", "")
    pick_zh = metrics.get("pickTargetZh", "")
    pick_ok = (as_int(metrics.get("pickTargetBtn")) == 1 and bool(pick_en) and bool(pick_zh)
               and pick_en != pick_zh)
    check(pick_ok, "主界面·目标位置「选择…」按钮就位且随语言刷新（V0.0.40）",
          f"en={pick_en!r} → zh={pick_zh!r}"
          + ("" if pick_ok else "（按钮缺失或未走取词）"))

    # V0.0.41 · 手册 9.2 节 #7 / 10.2 节 #4：模板编辑区「新建模板」。
    # 两个层次：① 按钮在位且文案随语言刷新（同 pickTarget 的取词闭包证明）；
    # ② 弹窗**实测**：点按钮 → 真开 → 起点下拉非空 → 关得掉。②比①强得多 ——
    # 它证明 newTemplateFlow 的 async 流程（await 列表 → open）与 [data-close] 接线
    # 都真的在页面上跑通了，而不只是「元素存在」。
    tplnew_en = metrics.get("tplNewEn", "")
    tplnew_zh = metrics.get("tplNewZh", "")
    tplnew_ok = (as_int(metrics.get("tplNewBtn")) == 1 and as_int(metrics.get("tplNewDlg")) == 1
                 and bool(tplnew_en) and bool(tplnew_zh) and tplnew_en != tplnew_zh)
    check(tplnew_ok, "主界面·模板「新建」按钮就位且随语言刷新（V0.0.41）",
          f"en={tplnew_en!r} → zh={tplnew_zh!r}"
          + ("" if tplnew_ok else "（按钮/弹窗缺失或未走取词）"))

    open_ok = as_int(metrics.get("tplNewOpen")) == 1
    base_n = as_int(metrics.get("tplNewBaseN"))
    base_text = metrics.get("tplNewBaseText", "")
    # 关闭分两拍：closing = 点后 .is-open 已同步摘除；closed = 170ms 动画后真的 display:none
    close_ok = (as_int(metrics.get("tplNewClosing")) == 0
                and as_int(metrics.get("tplNewClosed")) == 1)
    dlg_ok = open_ok and base_n >= 1 and bool(base_text) and close_ok
    check(dlg_ok, "主界面·「新建模板」弹窗可开、起点已填充、可关（V0.0.41）",
          f"open={metrics.get('tplNewOpen')} 起点 {base_n} 项 首项={base_text!r} "
          f"closing={metrics.get('tplNewClosing')} closed={metrics.get('tplNewClosed')}"
          + ("" if dlg_ok else "（弹窗未开 / 起点为空 / 关不掉）"))

    # V0.0.42 · 手册 10.2 节 #12：根名方案 C —— 根节点名**即**「根文件夹名」。
    # 探针走真实路径（选中根行 → 工具栏「重命名」，window.prompt 被替换为受控值 'QmRootX' / ''），
    # 断言点与 i18n 解耦：只看「摘要 / 树区根名是否随根名变」，不比对具体文案。
    root_probe = as_int(metrics.get("rootProbe"))
    sum_before = metrics.get("rootSumBefore", "")
    sum_after = metrics.get("rootSumAfter", "")
    sum_blank = metrics.get("rootSumBlank", "")
    name_after = metrics.get("rootNameAfter", "")
    name_blank = metrics.get("rootNameBlank", "")
    rename_ok = (root_probe == 1 and "QmRootX" not in sum_before
                 and "QmRootX" in sum_after and name_after == "QmRootX")
    check(rename_ok, "主界面·根名即树根：改名后摘要与树区同步（V0.0.42）",
          f"摘要 before={sum_before!r} → after={sum_after!r} / 树区根名={name_after!r}"
          + ("" if rename_ok else "（改名未贯通到摘要或树区）"))

    blank_ok = (root_probe == 1 and "QmRootX" not in sum_blank
                and bool(name_blank) and name_blank != "QmRootX")
    check(blank_ok, "主界面·根名即树根：清空即不建根（V0.0.42）",
          f"摘要={sum_blank!r} / 树区根名={name_blank!r}"
          + ("" if blank_ok else "（清空后未回到「不建根」）"))

    # V0.0.43 · UI 定版差集 G 组：工具栏三分组。
    # 锚点是**每颗按钮的归属**（序列 00000112）而非分组个数 —— 后者会被三个空壳容器骗过；
    # 三组各有 aria-label 才说明分组对读屏也可辨（原先读作一长串按钮）。
    g_map = metrics.get("gMap", "")
    g_ok = (as_int(metrics.get("gGroups")) == 3 and as_int(metrics.get("gLabels")) == 3
            and g_map == EXPECT_GROUP_MAP)
    check(g_ok, "主界面·工具栏三分组：按钮各归其组（V0.0.43 · G）",
          f"组数={metrics.get('gGroups')} 带标签={metrics.get('gLabels')} 归属={g_map or '(空)'}"
          + ("" if g_ok else f"（期望 {EXPECT_GROUP_MAP} = 5 编辑 / 2 视图 / 1 输出）"))

    # V0.0.43 · UI 定版差集 H 组：检视器「属性 ⇄ 源码」。
    # 最强的一条是 hJson + hHasChild：源码栏必须是**可解析的 JSON 且真的含子节点名** ——
    # 这才证明它走的是 toPlainTree 序列化（与 /api/generate 的 payload 同源），
    # 而不是随手拼出来的一段文本。切回属性面板同理（hBack=2）。
    h_ok = (as_int(metrics.get("hSeg")) == 2
            and as_int(metrics.get("hPropHidden")) == 1
            and as_int(metrics.get("hSrcShown")) == 1
            and as_int(metrics.get("hJson")) == 1
            and as_int(metrics.get("hHasChild")) == 1
            and as_int(metrics.get("hBack")) == 2)
    check(h_ok, "主界面·检视器属性⇄源码：可切换且源码为同源 JSON（V0.0.43 · H）",
          f"分段 {metrics.get('hSeg')} 档 / 属性面板隐={metrics.get('hPropHidden')} "
          f"/ JSON={metrics.get('hJson')} 含子节点={metrics.get('hHasChild')} "
          f"/ 复位={metrics.get('hBack')} / 偏好={metrics.get('hPref')!r}"
          + ("" if h_ok else "（未切换 / 源码非 JSON / 未复位）"))

    # V0.0.43 · UI 定版差集 F 组：多选批量。
    # 分五段实证：① 离散多选开条 + 聚合态禁 note；② Esc 与 Shift 范围选择；
    # ③ Ctrl+A 全选除根；④ 批量删除**只作用于最外层祖先**（父子同选 → 只删父）；
    # ⑤ 取消路径不动树。④ 是本组最重的一条 —— 它是「父子同选去重」唯一的运行时证据。
    f_gest = (as_int(metrics.get("fBar0")) == 0
              and as_int(metrics.get("fMulti")) == 2
              and as_int(metrics.get("fBarOn")) == 1
              and as_int(metrics.get("fInfo")) == 1
              and as_int(metrics.get("fAgg")) == 1
              and as_int(metrics.get("fBarOff")) == 1
              and as_int(metrics.get("fMultiOff")) == 0
              and as_int(metrics.get("fShift")) == 3
              and as_int(metrics.get("fAll")) == as_int(metrics.get("fVisible")) - 1
              and as_int(metrics.get("fAllBar")) == 1
              and as_int(metrics.get("fBarOff2")) == 1)
    check(f_gest, "主界面·多选手势与批量条（Ctrl/Shift/Esc/Ctrl+A）（V0.0.43 · F）",
          f"初始条={metrics.get('fBar0')} Ctrl多选={metrics.get('fMulti')} 条={metrics.get('fBarOn')} "
          f"Esc后={metrics.get('fMultiOff')}/{metrics.get('fBarOff')} Shift={metrics.get('fShift')} "
          f"CtrlA={metrics.get('fAll')}/{metrics.get('fVisible')} 清空后={metrics.get('fBarOff2')}"
          + ("" if f_gest else "（手势未生效 / 批量条未联动）"))

    # 关键判别量是 fConfirmN：父子同选时对话框必须报**1**（最外层祖先数），而非 2。
    # 注意「删掉的行数」**不是**判别量 —— 逐个删除时子节点在父被摘走后已随之消失，
    # 第二次 removeNode 自然返回 false，最终行数恰好相同（假通过）。故此处只认对话框口径。
    f_n = first_int(metrics.get("fConfirmMsg", ""))
    f_del = (as_int(metrics.get("fDedupSet")) == 2
             and f_n == 1
             and as_int(metrics.get("fDropN")) >= 2
             and as_int(metrics.get("fBefore")) - as_int(metrics.get("fAfter"))
                 == as_int(metrics.get("fDropN"))
             and as_int(metrics.get("fCancelKept")) == 1
             and as_int(metrics.get("fBarClear")) == 1)
    check(f_del, "主界面·批量删除只作用于最外层祖先（V0.0.43 · F）",
          f"父子同选={metrics.get('fDedupSet')} 对话框报 {f_n} 项 / 父子树 {metrics.get('fDropN')} 行 / "
          f"实删 {as_int(metrics.get('fBefore')) - as_int(metrics.get('fAfter'))} 行 / "
          f"取消不动树={metrics.get('fCancelKept')} 条已收={metrics.get('fBarClear')}"
          + ("" if f_del else "（对话框报的项数≠最外层祖先数，或取消未生效）"))

    # C-P3-5（V0.0.29）：非法皮肤偏好须回落出厂默认 —— 若被直接采用，会去加载不存在的
    # `./css/skins/not-a-real-skin.css`（装载失败 → 落 tokens.css 裸色，与选择器显示不符）。
    bad_href = metrics.get("badSkinHref", "")
    fallback_ok = bool(bad_href) and bad_href.endswith(".css") and "not-a-real-skin" not in bad_href
    check(fallback_ok, "主界面·非法皮肤回落出厂默认（C-P3-5）",
          f"href={bad_href or '(空)'}"
          + ("" if fallback_ok else "（C-P3-5 回归：非法皮肤名被直接采用）"))

    # D-P3-2（V0.0.29；V0.0.40 迁移）：顶栏配色须取自 --qm-text-dim（随皮肤），而非旧版烘死的
    # #6d7278 = rgb(109, 114, 120)。下拉已退场，改钉图标按钮 #btnLang 的 color（currentColor mask）。
    arrow = metrics.get("arrowColor", "")
    dim = metrics.get("dimColor", "")
    arrow_ok = bool(arrow) and bool(dim) and arrow == dim and arrow != "rgb(109, 114, 120)"
    check(arrow_ok, "主界面·顶栏图标随 --qm-text-dim（D-P3-2）",
          f"图标 {arrow or '(空)'} vs --qm-text-dim {dim or '(空)'}"
          + ("" if arrow_ok else "（D-P3-2 回归：图标色未随皮肤变量）"))

    # C-P3-1（V0.0.29）：目录树全量重建后须保持滚动位置（否则每次编辑都跳回顶部）。
    # 须同时满足「确实重建了」（reRendered=1），否则重建未发生时的相等是假通过。
    sb = as_int(metrics.get("scrollBefore"), -1)
    sa = as_int(metrics.get("scrollAfter"), -2)
    rebuilt = as_int(metrics.get("reRendered"), 0)
    scroll_ok = sb > 0 and sa == sb and rebuilt == 1
    check(scroll_ok, "主界面·重建后滚动位置保持（C-P3-1）",
          f"scrollTop {sb} → {sa}，重建 {'是' if rebuilt == 1 else '否'}"
          + ("" if scroll_ok else "（C-P3-1 回归：重建后滚动位置丢失）"))

    # C-P3-2（V0.0.32）：`dragover` 须**预判**「拖进自身 / 自身子孙」。
    # 逼出缺陷：旧实现只挡「自身」，子孙落点照样亮 `is-drop-target` → 给「可放下」假暗示，
    # 直到 `drop` 才由模型层 `canMove` 判 `cycle` 报错。三项同时成立才算过 ——
    # 只断言「子孙被拒」会被「一律拒绝」式假修复骗过，故合法落点必须**真的被接受**。
    d_self = as_int(metrics.get("dragSelf"), -1)
    d_desc = as_int(metrics.get("dragDesc"), -1)
    d_ok = as_int(metrics.get("dragOk"), -1)
    drag_ok = d_self == 1 and d_desc == 1 and d_ok == 1
    check(drag_ok, "主界面·拖拽预判自身子树（C-P3-2）",
          f"自身落点{'拒' if d_self == 1 else '误收'} / "
          f"子孙落点{'拒' if d_desc == 1 else '误收'} / "
          f"无关目录{'收' if d_ok == 1 else '误拒'}"
          + ("" if drag_ok else "（C-P3-2 回归：子树内落点仍给「可放下」假暗示）"))

    # C-P3-3（V0.0.32）：`dragleave` 的 `relatedTarget` 仍在本行内（划过 toggle / icon / name）
    # 时不得摘高亮；真离开时必须摘掉。**两向都断言**，否则「干脆永不摘」也能骗过单向断言。
    dl_child = as_int(metrics.get("dlChild"), -1)
    dl_out = as_int(metrics.get("dlOut"), -1)
    dl_ok = dl_child == 1 and dl_out == 1
    check(dl_ok, "主界面·拖拽高亮不因划过子元素闪烁（C-P3-3）",
          f"划过子元素{'保持' if dl_child == 1 else '被误摘'} / "
          f"真离开{'已摘' if dl_out == 1 else '未摘'}"
          + ("" if dl_ok else "（C-P3-3 回归：高亮在子元素间闪烁）"))

    # C-P3-4（V0.0.32）：提示条**同时显示**数量不得超上限。
    # 上限从源码读（单一事实源）：改上限只需改 `toast.js` 一处，此断言自动跟随。
    cap = toast_cap()
    toast_n = as_int(metrics.get("toastN"), -1)
    toast_ok = cap > 0 and toast_n == cap
    check(toast_ok, "主界面·提示条数量上限（C-P3-4）",
          f"上限 {cap if cap > 0 else '未读到'} 条，40 次提示后实存 {toast_n} 条"
          + ("" if toast_ok else "（C-P3-4 回归：提示条无上限堆积）"))

    if expect_templates:
        tpl = as_int(metrics.get("tplRows"))
        # V0.0.37（6D）：交付形态改为「内置仅 P0 + 独立模板包」，故断言由「≥1」收紧为
        # **恰好 1** —— 否则业务模板被放回 templates/ 也照样通过，「工具不带业务模板」失守。
        check(tpl == 1, "主界面·内置模板仅 P0（V0.0.37）",
              f"模板行 {tpl} 条（应恰好 1；业务模板归 templates-pack/）")

        # V0.0.38 · 6E：绑定行骨架 —— 行本身 + 路径文本 + 三个入口按钮（选择/刷新/导入）
        dir_row = as_int(metrics.get("tplDirRow"), -1)
        dir_path = metrics.get("tplDirPath", "")
        dir_btns = as_int(metrics.get("tplDirBtns"), -1)
        bind_ok = dir_row == 1 and bool(dir_path) and dir_btns == 3
        check(bind_ok, "主界面·模板目录绑定 UI（V0.0.38）",
              f"行 {dir_row} / 路径 {dir_path!r} / 入口按钮 {dir_btns} 个（应 3）"
              + ("" if bind_ok else "（6E 回归：绑定行或入口按钮缺失）"))

        # V0.0.38 · 6E：模板行右键菜单项齐备（载入 / 重命名 / 复制 / 导出 / 删除 = 5 项）。
        # 断言项数**加**文案，避免「挂了 5 个空壳按钮」也被判过。
        menu_n = as_int(metrics.get("tplMenuN"), -1)
        menu_text = metrics.get("tplMenu", "")
        menu_ok = menu_n == 5 and "Export" in menu_text
        check(menu_ok, "主界面·模板行右键菜单项齐备（V0.0.38）",
              f"{menu_n} 项：{menu_text or '(空)'}"
              + ("" if menu_ok else "（6E 回归：菜单项缺失或未挂到模板行）"))

        # V0.0.38 · 6E：轮询**实证** —— 导入一套后等 ≥1 个周期，列表须自动 1 → 2。
        # 只断言「界面没坏」是不够的：轮询被整个摘掉时该断言同样成立。
        poll_before = as_int(metrics.get("pollBefore"), -1)
        poll_after = as_int(metrics.get("pollAfter"), -2)
        poll_ok = poll_before == 1 and poll_after == 2
        check(poll_ok, "主界面·模板列表轮询生效（V0.0.38）",
              f"导入后 {poll_before} → {poll_after} 行（应 1 → 2）"
              + (f"；异常 {metrics.get('pollErr')}" if metrics.get("pollErr") else "")
              + ("" if poll_ok else "（6E 回归：轮询未生效或未刷新列表）"))

    sec_before = as_int(metrics.get("secBefore"), 0)
    sec_en = as_int(metrics.get("secEn"), 0)
    sec_zh = as_int(metrics.get("secZh"), 0)
    nav_before = as_int(metrics.get("navBefore"), 0)
    nav_zh = as_int(metrics.get("navZh"), 0)
    stable = (sec_before > 0 and sec_before == sec_en == sec_zh and nav_before == nav_zh)
    check(stable, "帮助页·分节渲染幂等",
          f"分节 {sec_before} → {sec_en} → {sec_zh}" + (f"（导航 {nav_before}/{nav_zh}）")
          + ("" if stable else "，计数不一致 —— 语言切换在累积（P1-1 回归）"))

    check(metrics.get("langEn") == "en-US" and metrics.get("langZh") == "zh-CN",
          "帮助页·语言切换联动 html lang",
          f"en-US → {metrics.get('langEn')} / zh-CN → {metrics.get('langZh')}")

    chip = metrics.get("chip", "")
    stale = as_int(metrics.get("stale"), -1)
    check(chip == expected_version and stale == 0,
          "帮助页·版本徽标 = VERSION（后端可达）",
          f"徽标 {chip or '(空)'} vs VERSION {expected_version}；"
          f"后端标注 {'陈旧' if stale != 0 else '正常'}")

    qr = as_int(metrics.get("qr"), 0)
    thanks = as_int(metrics.get("thanks"), 0)
    check(qr == 1 and thanks == 1, "支持页·拆页后完好",
          f".help-qr={qr} .help-thanks={thanks}")


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 无头浏览器冒烟")
    parser.add_argument("--browser", default=None, help="浏览器可执行文件路径（缺省自动探测 Edge/Chrome）")
    parser.add_argument("--port", type=int, default=0, help="0 = 自动挑一个空闲端口")
    parser.add_argument("--sandbox", default=None, help="沙盒目录（缺省用系统临时目录）")
    parser.add_argument("--keep", action="store_true", help="保留沙盒（默认测完即清）")
    parser.add_argument("--budget", type=int, default=20000, help="浏览器虚拟时间预算（毫秒）")
    parser.add_argument("--timeout", type=float, default=120.0, help="浏览器进程超时（秒）")
    parser.add_argument("--ready-timeout", type=float, default=15.0, help="等待服务就绪（秒）")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    if not browser:
        check(True, "浏览器探测", "未检测到 Edge/Chrome —— 已跳过页面级冒烟（本次未验证）")
        print("[冒烟·页面] 未检测到 Chromium 系浏览器（可用 --browser 指定路径后重跑）")
        width = max(len(name) for _ok, name, _note in RESULTS) + 2
        for ok, name, note in RESULTS:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        print("[冒烟·页面] 共 1 项 · 失败 0 项（跳过 1）")
        return 0

    # 前置探测（§P2-11）：`--browser` 指向不可无头驱动的 exe（如夸克启动器）时**跳过**，
    # 而不是让它走到「探针完成 FAIL」—— 那会把「环境不支持」误判成「页面有缺陷」。
    drivable, why = browser_drivable(browser)
    if not drivable:
        check(True, "浏览器可驱动性", f"已跳过页面级冒烟：{why}")
        print(f"[冒烟·页面] 浏览器不可无头驱动：{browser}")
        print(f"[冒烟·页面] 原因：{why}（属环境不支持，非页面缺陷；可用 --browser 换一个）")
        width = max(len(name) for _ok, name, _note in RESULTS) + 2
        for ok, name, note in RESULTS:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        print("[冒烟·页面] 共 1 项 · 失败 0 项（跳过 1）")
        return 0

    if not (SRC_DIR / "server").is_dir():
        print(f"[失败] 未找到服务端：{SRC_DIR / 'server'}")
        return 1

    if args.sandbox:
        sandbox = Path(args.sandbox).resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    elif args.keep:
        sandbox = sandbox_base() / f"qingman_browser_{time.strftime('%Y%m%d')}"
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        sandbox = Path(tempfile.mkdtemp(prefix="qm_browser_"))
        cleanup = True

    version_file = PROJECT_ROOT / "VERSION"
    expected_version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
    templates_dir = PROJECT_ROOT / "templates"

    print(f"[冒烟·页面] 浏览器：{browser}")
    print(f"[冒烟·页面] 沙盒：{sandbox}")

    sandbox_src = sandbox / "src"

    # 复用同一沙盒时，先清掉**本脚本自己**上次留下的产物（只看这几个已知名字，
    # 不动沙盒里其它内容）。`data/` 必须清：残留的 editor.json 会被
    # `restoreDocument()` 复原，于是走不到「默认构建」这条路径，
    # 「默认示例随语言」一项就会假通过。
    stale = [name for name in ("src", "templates", "VERSION", "data", "browser-profile")
             if (sandbox / name).exists()]
    if stale:
        print(f"[冒烟·页面] 复用沙盒，清理上次产物：{', '.join(stale)}")
        for name in stale:
            target = sandbox / name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink()

    shutil.copytree(SRC_DIR, sandbox_src)
    if version_file.is_file():
        shutil.copy2(version_file, sandbox / "VERSION")
    if templates_dir.is_dir():
        shutil.copytree(templates_dir, sandbox / "templates")
    (sandbox_src / "web" / PROBE_NAME).write_text(PROBE_HTML, encoding="utf-8", newline="\n")

    port = args.port or free_port()
    env = dict(os.environ, QM_PORT=str(port), QM_OPEN_BROWSER="0", PYTHONDONTWRITEBYTECODE="1")
    if templates_dir.is_dir():
        # 6D：显式绑定到**沙盒内**的内置目录 —— ① env 优先级高于 settings（`config.templates_dir()`
        # 的解析链为 env > settings > 默认），避免本机 %APPDATA%/QingMan/settings.json 里
        # 既有绑定把「内置模板数」污染成不可复现的值；② 断言「只内置 P0」因此具备确定性。
        env["QM_TEMPLATES_DIR"] = str(sandbox / "templates")
    # 服务端输出**必须持续排空**：`ThreadingHTTPServer` 每请求写一行访问日志，若走
    # PIPE 而全程无人读取，Windows 管道缓冲（约 4KB）一满，服务线程即刻阻塞在写日志上
    # → 不再响应任何请求 → 浏览器探针一路挂到超时（表现为「浏览器运行 120s 内未返回」，
    # 且探针连自报都发不出）。V0.0.43 只多出 3 个静态请求的日志量，就刚好越过这个临界
    # ——故改为落盘到沙盒日志文件：既排空管道，又留下排障线索（`--keep` 时保留）。
    server_log = (sandbox / "server.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "server"], cwd=str(sandbox_src), env=env,
        stdout=server_log, stderr=subprocess.STDOUT,
    )

    stderr = ""
    try:
        if not wait_health(port, args.ready_timeout):
            check(False, "服务启动", f"{args.ready_timeout}s 内未就绪")
        else:
            origin = f"http://127.0.0.1:{port}"
            url = f"{origin}/{PROBE_NAME}"
            timed_out = False
            try:
                stdout, stderr, code = run_browser(
                    browser, url, sandbox / "browser-profile", args.budget, args.timeout)
            except subprocess.TimeoutExpired:
                stdout, stderr, code = "", "", -1
                timed_out = True
                check(False, "浏览器运行", f"{args.timeout}s 内未返回")

            if timed_out:
                stderr = ""
            console = console_lines(stderr, origin)
            # 正面控制（§P2-13）：先证「日志通道在投递」，再谈「无未捕获异常」。
            alive = any(SELF_REPORT in line for line in console)
            check(alive, "控制台日志通道可用（正面控制）",
                  "已收到探针自报，日志通道正常" if alive else
                  "未收到探针自报 —— `--enable-logging` 通道可能失效，「无未捕获异常」判定不可信")
            fatal = [line for line in console if any(tok in line for tok in FATAL_CONSOLE)]
            noisy = [line for line in console
                     if SELF_REPORT not in line and not any(tok in line for tok in FATAL_CONSOLE)]
            check(not fatal, "页面载入无未捕获异常 / 无漏翻",
                  ("；".join(line.split("]", 1)[-1].strip()[:110] for line in fatal[:3])
                   if fatal else
                   f"本项目页面控制台 {len(console)} 条消息，无致命项"
                   + (f"（容忍 {len(noisy)} 条装饰性告警）" if noisy else "")))

            metrics = parse_metrics(stdout)
            check(metrics is not None, "探针完成",
                  "已取到页面指标" if metrics else f"未取到结果行（退出码 {code}）")
            if metrics:
                for key in ("err1", "err2", "err3"):
                    if key in metrics:
                        check(False, "探针脚本自身异常", f"{key}={metrics[key]}")
                verify_metrics(metrics, expected_version, templates_dir.is_dir())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log.close()
        if cleanup:
            shutil.rmtree(sandbox, ignore_errors=True)

    width = max(len(name) for _ok, name, _note in RESULTS) + 2
    failed = 0
    print("-" * 78)
    for ok, name, note in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        if not ok:
            failed += 1
    print("-" * 78)
    print(f"[冒烟·页面] 共 {len(RESULTS)} 项 · 失败 {failed} 项")
    print(f"[冒烟·页面] 结论：{'全部通过' if not failed else '不通过'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
