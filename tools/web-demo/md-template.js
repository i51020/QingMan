/* 青蔓 QingMan · 模板 `.md` 文法（JS 版，供在线版使用）
 *
 * 这是 `src/server/dtree_core.py` 里 `render_md_template` / `parse_md_template` 的**移植**。
 * 为什么要有第二份：在线版没有 Python，但「导入/导出 .md」是模板子系统的一半功能，
 * 不能因为换了运行环境就砍掉。
 *
 * 文法（与 Python 端逐字对应，改一边必须改另一边）：
 *   `# 名称`            —— 文档首个标题行 = 模板名（可选）
 *   `> 描述`            —— 紧随的引用块 = 描述（可选，可多行）
 *   `- 节点`            —— 每 2 空格一级；名尾 `/` 或前缀 📁 = 目录，否则文件
 *   `  ```md ... ``` `  —— 文件正文：围栏块再缩进一级；内容含连续反引号时围栏自动加长
 *
 * 一致性证据：构建期用 `tools/build_static_site.py` 的等价性自检（Python 渲染 → JS 解析
 * → 比较树）钉住，而不是靠"看起来一样"。
 */
(function (root) {
  'use strict';

  var DIR_MARK = '\uD83D\uDCC1';   // 📁
  var FENCE_MIN = 3;
  var ITEM_RE = /^( *)- +(.*)$/;

  function err(code, extra) {
    var e = new Error(code);
    e.code = code;
    if (extra) { e.detail = extra; }
    return e;
  }

  function fenceFor(content) {
    var longest = 0;
    var run = 0;
    for (var i = 0; i < content.length; i += 1) {
      if (content.charAt(i) === '`') {
        run += 1;
        if (run > longest) { longest = run; }
      } else {
        run = 0;
      }
    }
    var size = Math.max(FENCE_MIN, longest + 1);
    return new Array(size + 1).join('`');
  }

  function renderTree(node, depth, out) {
    var indent = new Array(depth + 1).join('  ');
    var bodyIndent = new Array(depth + 2).join('  ');
    Object.keys(node).forEach(function (name) {
      var value = node[name];
      if (value && typeof value === 'object') {
        out.push(indent + '- ' + name + '/');
        renderTree(value, depth + 1, out);
        return;
      }
      var content = typeof value === 'string' ? value : '';
      out.push(indent + '- ' + name);
      if (content) {
        var fence = fenceFor(content);
        out.push(bodyIndent + fence + 'md');
        content.split('\n').forEach(function (line) {
          // 空行不留缩进（与 Python 端同一规范化）
          out.push(line ? bodyIndent + line : '');
        });
        out.push(bodyIndent + fence);
      }
    });
  }

  function render(doc) {
    if (!doc || typeof doc !== 'object') { throw err('templateBadJson'); }
    var tree = doc.tree;
    if (!tree || typeof tree !== 'object') { throw err('templateTreeMissing'); }
    var out = [];
    var name = doc.name;
    if (typeof name === 'string' && name.trim()) { out.push('# ' + name.trim()); }
    var description = doc.description;
    if (typeof description === 'string' && description) {
      description.split('\n').forEach(function (line) {
        out.push(line ? '> ' + line : '>');
      });
    }
    if (out.length) { out.push(''); }
    renderTree(tree, 0, out);
    return out.join('\n') + '\n';
  }

  function parse(text) {
    if (typeof text !== 'string') { throw err('templateBadMarkdown'); }
    var src = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    if (src.charAt(0) === '\uFEFF') { src = src.slice(1); }
    var lines = src.split('\n');
    var n = lines.length;
    var i = 0;

    while (i < n && !lines[i].trim()) { i += 1; }
    var name = '';
    if (i < n && lines[i].indexOf('# ') === 0) {
      name = lines[i].slice(2).trim();
      i += 1;
    }
    var desc = [];
    while (i < n && (lines[i] === '>' || lines[i].indexOf('> ') === 0)) {
      desc.push(lines[i].indexOf('> ') === 0 ? lines[i].slice(2) : lines[i].slice(1));
      i += 1;
    }

    var tree = {};
    var stack = [{ depth: -1, node: tree }];
    while (i < n) {
      var line = lines[i];
      if (!line.trim()) { i += 1; continue; }
      var m = ITEM_RE.exec(line);
      if (!m) { throw err('templateBadMarkdown', { reason: 'unexpected line' }); }
      var indent = m[1].length;
      if (indent % 2) { throw err('templateBadMarkdown', { reason: 'odd indent' }); }
      var depth = indent / 2;
      var rest = m[2].trim();
      var isDir = rest.charAt(rest.length - 1) === '/';
      var seg = isDir ? rest.slice(0, -1).trim() : rest;
      if (seg.indexOf(DIR_MARK) === 0) {
        isDir = true;
        seg = seg.slice(DIR_MARK.length).trim();
      }
      if (!seg) { throw err('templateBadMarkdown', { reason: 'empty name' }); }

      while (stack.length && stack[stack.length - 1].depth >= depth) { stack.pop(); }
      if (!stack.length || stack[stack.length - 1].depth !== depth - 1) {
        throw err('templateBadMarkdown', { reason: 'indent jump' });
      }
      var parent = stack[stack.length - 1].node;
      if (Object.prototype.hasOwnProperty.call(parent, seg)) {
        throw err('templateSiblingDuplicated', { name: seg });
      }
      i += 1;

      if (isDir) {
        var child = {};
        parent[seg] = child;
        stack.push({ depth: depth, node: child });
        continue;
      }

      var content = '';
      if (i < n) {
        var bodyIndent = new Array(depth + 2).join('  ');
        var next = lines[i];
        if (next.indexOf(bodyIndent) === 0 && next.charAt(bodyIndent.length) === '`') {
          var head = next.slice(bodyIndent.length);
          var run = 0;
          while (run < head.length && head.charAt(run) === '`') { run += 1; }
          if (run >= FENCE_MIN) {
            var fence = new Array(run + 1).join('`');
            i += 1;
            var body = [];
            var closed = false;
            while (i < n) {
              var cur = lines[i];
              if (cur.trim() === fence) { closed = true; i += 1; break; }
              if (cur === '') { body.push(''); }
              else if (cur.indexOf(bodyIndent) === 0) { body.push(cur.slice(bodyIndent.length)); }
              else { throw err('templateBadMarkdown', { reason: 'malformed body' }); }
              i += 1;
            }
            if (!closed) { throw err('templateBadMarkdown', { reason: 'unclosed fence' }); }
            content = body.join('\n');
          }
        }
      }
      parent[seg] = content;
    }

    return { name: name, description: desc.join('\n'), tree: tree };
  }

  var api = { render: render, parse: parse, DIR_MARK: DIR_MARK };
  root.QMDemoMd = api;
  // Node 侧自检用（构建期的等价性断言），浏览器里没有 module 就跳过
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
})(typeof window !== 'undefined' ? window : globalThis);
