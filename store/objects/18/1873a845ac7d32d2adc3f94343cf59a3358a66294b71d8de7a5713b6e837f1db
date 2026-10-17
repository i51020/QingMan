/**
 * 青蔓 QingMan · 模板排序口径（V0.3.2 · **纯数据模块**：无 DOM、无 window、零依赖）
 *
 * 排序四级，逐级只有上一级相等才往下走：
 *
 *   ① **显示名**（`name`，先小写再原名）—— 主键。用户唯一能感知的标识；
 *   ② **最近使用**（`last` 降序）—— 同名的两套模板里，刚用过的在前；
 *   ③ **使用次数**（`count` 降序）—— 同名的两套模板里，用得多的在前；
 *   ④ **文件名**（`file`，先小写再原名）—— 兜底，保证顺序确定、跨平台可复现。
 *
 * **为什么主键是显示名，而不是「使用记录」**：文件名序（V0.0.38~V0.3.1）会让
 * 「文件名 ≠ 显示名」的模板排在名字对不上的位置；而纯使用记录序会让列表随每次
 * 载入重新洗牌（上一版刚修过“排序总是变化”）。显示名是唯一**既稳定又与用户认知
 * 一致**的键；使用记录只在前两级打平时起作用，因此不会把列表搅乱。
 *
 * **为什么单独成文件**：`modules/templates.js` 顶层 import `core/api.js`，而它读
 * `window.location.origin` —— 在 Node 里导不进来。排序是**用户可见行为**，必须能被
 * 单测直接钉住（`tests/test_frontend_js.py`），故纯函数独立成文件。
 */

/** 显示名比较键：小写 → 原文（仅在大小写不同时才靠第二段分出次序）。 */
function nameKey(item) {
  const raw = item && item.name != null ? item.name : '';
  const name = String(raw).trim();
  return [name.toLowerCase(), name];
}

/** 文件名比较键（兜底用，口径与 `online-store.byFile` 一致）。 */
function fileKey(item) {
  const raw = item && item.file != null ? item.file : '';
  const file = String(raw);
  return [file.toLowerCase(), file];
}

function cmp(a, b) {
  return a < b ? -1 : (a > b ? 1 : 0);
}

/**
 * 使用记录里的一项 → `[最近使用毫秒戳, 使用次数]`。
 *
 * localStorage 可被手改、也可能残留旧结构 —— 脏值一律按 0 处理，**绝不抛错**：
 * 排序是展示层的事，读坏一条记录不该让模板列表变成一片空白。
 */
function usageOf(usage, file) {
  const record = usage && typeof usage === 'object' ? usage[file] : null;
  if (!record || typeof record !== 'object') return [0, 0];
  const last = Number(record.last);
  const count = Number(record.count);
  return [Number.isFinite(last) ? last : 0, Number.isFinite(count) ? count : 0];
}

/**
 * 两条模板的比较器（供 `Array.prototype.sort` 直接使用）。
 * @param {object} a 模板项 `{file, name, ...}`
 * @param {object} b 模板项
 * @param {object} [usage] 使用记录 `{ [file]: {last, count} }`
 * @returns {number} 负数 → a 在前
 */
export function compareTemplates(a, b, usage) {
  const an = nameKey(a);
  const bn = nameKey(b);
  let r = cmp(an[0], bn[0]);
  if (r) return r;
  r = cmp(an[1], bn[1]);
  if (r) return r;

  const au = usageOf(usage, a && a.file);
  const bu = usageOf(usage, b && b.file);
  if (au[0] !== bu[0]) return bu[0] - au[0];   // ② 最近使用在前
  if (au[1] !== bu[1]) return bu[1] - au[1];   // ③ 用得多的在前

  const af = fileKey(a);
  const bf = fileKey(b);
  r = cmp(af[0], bf[0]);
  if (r) return r;
  return cmp(af[1], bf[1]);
}

/**
 * 排序模板列表。**不改入参**（返回新数组）。
 *
 * 末尾用「原始下标」兜底：即使两条模板四项键全等，也保持后端给的相对次序 ——
 * 不依赖引擎的排序稳定性（V8 稳定，但这是实现细节，不是契约）。
 *
 * @param {object[]} items 后端 `GET /api/templates` 的 `items`
 * @param {object} [usage] 使用记录
 * @returns {object[]} 新数组
 */
export function sortTemplates(items, usage) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item, index) => ({ item, index }))
    .sort((x, y) => compareTemplates(x.item, y.item, usage) || (x.index - y.index))
    .map((row) => row.item);
}
