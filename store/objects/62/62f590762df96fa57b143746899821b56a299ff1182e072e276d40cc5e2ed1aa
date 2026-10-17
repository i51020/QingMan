/**
 * 青蔓 QingMan · 模板排序口径（V0.3.3 · **纯数据模块**：无 DOM、无 window、零依赖）
 *
 * **六条规则，按段优先**（逐段取尽才往下走）：
 *
 *   ① **本次新建**（`created`）—— 本会话内新建的模板（且未使用过），最高优先；
 *   ② **本次单个导入**（`single`）—— 本会话内用导入按钮逐个导入的（且未使用过）；
 *   ③ **本次批量导入 / 外部新增**（`batch`）—— 一次出现多个，或轮询发现的外部新增；
 *   ④ **最近使用**（`last` 降序）—— 用过的模板里，最近用过的在前；
 *   ⑤ **使用次数**（`count` 降序）—— 最近使用打平时，用得多的在前；
 *   ⑥ **名称**（**按拼音**、数字按大小，先忽略大小写再按原文）→ **文件名**（兜底）
 *      —— 纯名称序也是「首次进入 / 点刷新」的唯一口径（`SORT_NAME` 模式）。
 *
 * **段 ③ 内按名称排**：一次批量导入的模板在用户眼里没有先后之别，只有名字可依。
 * **段 ①② 内按「本次会话的操作先后」（后建的在前）** —— V0.3.8 修正，见 `freshSeq`。
 *
 * ---
 *
 * **为什么用「本次操作」而不是文件时间戳**：批量复制 10 个文件时，`st_birthtime`
 * 逐个相差 5~9 毫秒（实测），按秒分桶在**文件多 / 慢盘 / 网络盘**时会跨秒，
 * 同一批被拆成两组，「同批按名称」就只在一组内成立。而「本次操作」由调用方
 * 直接告知是哪一批 —— 整批一起进、永远不会拆。代价是状态只活在**当前标签页**
 * （`sessionStorage`）：F5 保留、关标签页清空 —— 恰与「首次进入按名称」一致。
 *
 * **为什么段 ①②③ 只收「未使用过」的**：模板一旦被载入使用（次数 ≥ 1），就退出
 * 新段、按 ④⑤ 重排。于是「新导入」是一个**待用队列**：用过即出队，不会永远压顶。
 *
 * **为什么单独成文件**：`modules/templates.js` 顶层 import `core/api.js`，而它读
 * `window.location.origin` —— 在 Node 里导不进来。排序是**用户可见行为**，必须能被
 * 单测直接钉住（`tests/test_frontend_js.py`），故纯函数独立成文件。
 */

/** 纯名称序：首次进入、点刷新后的基线（忽略新建段与使用记录）。 */
export const SORT_NAME = 'name';
/** 六段规则：本会话内发生过新建 / 导入 / 外部新增。 */
export const SORT_EVENT = 'event';

/**
 * 新段编号（**数字小的先**）。
 *
 * `RANK_NONE = 3` 必须**大于**三个新段 —— 它表示「不属于任何新段」（已使用过，或没有
 * 文件名），要排在最後。写成 `-1` 会让「其余」段抢到最前面（首次实现即犯，被
 * `tests/test_frontend_js.py` 的 `TPL/new-first` 当场抓住）。
 */
const RANK_CREATED = 0;
const RANK_SINGLE = 1;
const RANK_BATCH = 2;
const RANK_NONE = 3;

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

/**
 * 语言感知比较器 —— **中文按拼音、数字按大小**（V0.3.10）。
 *
 * 旧实现直接比字符串（`a < b`），那就是 **UTF-16 码位序**：
 * `乙(U+4E59) < 甲(U+7532) < 辛(U+8F9B)`，跟用户读到的读音毫无关系，
 * 中文名一多就看着像乱序（用户报障「排序为什么没排出个顺序」）。
 * 实测同一组 `甲 乙 丙 丁 戊 辛`：码位序 `丁丙乙戊甲辛`，拼音序 `丙丁甲戊辛乙`。
 *
 * `numeric: true` 是同一类问题的另一半：码位序下 `模板10` 排在 `模板2` **前面**
 * （`'1' < '2'`），用户读到的是「10 比 2 小」。加上后得到 `模板1, 模板2, 模板10`。
 *
 * 退化路径：拿不到 `Intl.Collator`（极旧内核 / 被裁剪的 ICU）时回到码位序 ——
 * 排序看起来「还是旧样子」，但**不抛错、也不会变成随机序**。
 * 宁可维持旧观感，也不让列表在某台机器上炸掉。该路径有单测 `TPL/collate-fallback`。
 */
const collator = createCollator();

function createCollator() {
  try {
    if (typeof Intl === 'undefined' || typeof Intl.Collator !== 'function') return null;
    return new Intl.Collator('zh-Hans-CN', { numeric: true });
  } catch (err) {
    return null;   // 非法 locale / ICU 裁剪：一律退回码位序，绝不把异常抛给排序调用方
  }
}

function cmp(a, b) {
  return a < b ? -1 : (a > b ? 1 : 0);
}

/** 名称/文件名统一走这里：有 Collator 用 Collator，没有则退回码位序。 */
function collate(a, b) {
  return collator ? collator.compare(a, b) : cmp(a, b);
}

/** 名称 → 文件名，两级兜底。段内与 `SORT_NAME` 模式共用。 */
function cmpNameThenFile(a, b) {
  const an = nameKey(a);
  const bn = nameKey(b);
  let r = collate(an[0], bn[0]);
  if (r) return r;
  r = collate(an[1], bn[1]);
  if (r) return r;
  const af = fileKey(a);
  const bf = fileKey(b);
  r = collate(af[0], bf[0]);
  if (r) return r;
  return collate(af[1], bf[1]);
}

/**
 * 使用记录里的一项 → `[最近使用毫秒戳, 使用次数]`。
 *
 * sessionStorage / localStorage 都可能被手改或残留旧结构 —— 脏值一律按 0 处理，
 * **绝不抛错**：排序是展示层的事，读坏一条记录不该让模板列表变成一片空白。
 */
function usageOf(usage, file) {
  const record = usage && typeof usage === 'object' ? usage[file] : null;
  if (!record || typeof record !== 'object') return [0, 0];
  const last = Number(record.last);
  const count = Number(record.count);
  return [Number.isFinite(last) ? last : 0, Number.isFinite(count) ? count : 0];
}

function inList(list, file) {
  return Array.isArray(list) && list.indexOf(file) >= 0;
}

/**
 * 模板属于哪个新段。
 *
 * **`count > 0` 一律返回 `RANK_NONE`** —— 这条是「用过即出队」的唯一实现点。
 * 若漏掉它，新建的模板会永远压在最上面，用户再也看不到 ④⑤ 的效果。
 */
function freshRank(file, count, fresh) {
  if (!file || count > 0) return RANK_NONE;
  const f = fresh || {};
  if (inList(f.created, file)) return RANK_CREATED;
  if (inList(f.single, file)) return RANK_SINGLE;
  if (inList(f.batch, file)) return RANK_BATCH;
  return RANK_NONE;
}

/**
 * 一次导入操作该进哪个新段（V0.3.4）。
 *
 * 用户口径：**「单个导入的模板」与「新载入的批量模板」是两个不同优先段**。
 * 判据只能是**这一次选了几个文件**，不能看「最后成功几个」——
 * 选 5 个、4 个同名跳过，那仍然是「一次批量导入」这一动作，不该降级成②段。
 *
 * @param {number} count 本次选中的文件数
 * @returns {'batch'|'single'}
 */
export function importBucket(count) {
  return Number(count) > 1 ? 'batch' : 'single';
}

/**
 * 外部新增（轮询发现的名字）→ 新的会话状态（V0.3.4 修正）。
 *
 * **首次进入 / 刚点刷新必须「只登记、不建段」**：此时 `known` 为空，列表里**全部**
 * 模板都会被判成「没见过」—— 但那批是盘上**已有**的存量，不是「本次批量导入」。
 * 旧实现把它们整批写进 `batch` 段，只是靠 `mode=SORT_NAME` 暂时不参与比较；
 * 一旦 `mode` 切到 `SORT_EVENT`（载入 / 新建 / 导入都会切），这批存量立刻冒充
 * ③ 段（rank 2），把**真正用过的**模板（rank 3）全部压到后面 —— 实测在 6 套模板
 * 上表现为「刚载入的 C 排到最后」：`A,B,D,E,F,C`（正确应为 `C,A,B,D,E,F`）。
 *
 * @param {object} sess `{mode, created, single, batch, known}`
 * @param {string[]} files 本轮列表里「上轮没见过」的文件名
 * @returns {{firstSight: boolean, session: object}} 新对象，不改入参
 */
export function planExternal(sess, files) {
  const s = sess || {};
  const known = Array.isArray(s.known) ? s.known.slice() : [];
  const firstSight = known.length === 0;
  // 只有**确实不在 known 里**的才算新增 —— 调用方通常已做差集，但纯函数不该指望它：
  // 传入全量清单时，多算一项就会让一个老模板凭空变成「本次批量导入」。
  const added = [];
  for (const f of (files || []).filter(Boolean)) {
    if (known.indexOf(f) < 0) {
      known.push(f);
      added.push(f);
    }
  }

  // 首次进入：段一律清空 —— 存量既不进 ③，也不该继承上一会话（刷新后）的残留段
  if (firstSight) {
    return {
      firstSight: true,
      session: {
        mode: SORT_NAME,
        created: Array.isArray(s.created) ? s.created.slice() : [],
        single: Array.isArray(s.single) ? s.single.slice() : [],
        batch: [],
        known,
      },
    };
  }

  const batch = Array.isArray(s.batch) ? s.batch.slice() : [];
  for (const f of added) if (batch.indexOf(f) < 0) batch.push(f);
  return {
    firstSight: false,
    session: {
      mode: SORT_EVENT,
      created: Array.isArray(s.created) ? s.created.slice() : [],
      single: Array.isArray(s.single) ? s.single.slice() : [],
      batch,
      known,
    },
  };
}

/**
 * 段 ① / ② 内的次序：**本会话内的操作先后，后发生的在前**（V0.3.8）。
 *
 * 为什么不能沿用「段内按名称」：
 *   `markCreated` / `markImported([f], 1)` **每次只推进一个文件** —— ①、② 两段里
 *   每一条都是**独立的一次用户动作**，从来没有「同批」可言。而名称序与动作发生的
 *   先后毫无关系，于是「刚建完的那个」会被名字更小的老条目顶到中间。实测（甲→乙→辛
 *   依次新建）：`乙,甲,辛` —— 最新的「辛」反而垫底。用户口径是「我刚建的那套应该
 *   在第一个」。
 *   ③ 段相反：`markExternal` / 批量导入**一次推入一整批**，批内无先后，故仍按名称。
 *
 * 取数组下标即可 —— `markFresh` 恒为**追加**（`push`），下标越大 = 越晚发生。
 * 无需额外时间戳，也就不存在「同毫秒并列」的排序不稳定问题。
 *
 * @param {string} file 文件名
 * @param {number} rank `freshRank` 的结果
 * @param {object} fresh `{created, single, batch}`
 * @returns {number} 该段的操作序号；不在段内返回 0
 */
function freshSeq(file, rank, fresh) {
  const bucket = rank === RANK_CREATED ? 'created'
    : (rank === RANK_SINGLE ? 'single' : null);
  if (!bucket) return 0;
  const list = (fresh || {})[bucket];
  if (!Array.isArray(list)) return 0;
  const i = list.indexOf(file);
  return i < 0 ? 0 : i;
}

/**
 * 两条模板的比较器（供 `Array.prototype.sort` 直接使用）。
 * @param {object} a 模板项 `{file, name, ...}`
 * @param {object} b 模板项
 * @param {object} [ctx] `{mode, usage, fresh:{created,single,batch}}`
 * @returns {number} 负数 → a 在前
 */
export function compareTemplates(a, b, ctx) {
  const c = ctx || {};
  if (c.mode === SORT_NAME) return cmpNameThenFile(a, b);

  const au = usageOf(c.usage, a && a.file);
  const bu = usageOf(c.usage, b && b.file);
  const ra = freshRank(a && a.file, au[1], c.fresh);
  const rb = freshRank(b && b.file, bu[1], c.fresh);

  if (ra !== rb) return ra - rb;          // 段号小的在前（RANK_NONE 最大 ⇒ 排最后）
  if (ra === RANK_CREATED || ra === RANK_SINGLE) {
    // ①②：后发生的在前（见 freshSeq）。全等才退回名称 —— 保证结果仍可复现。
    const sa = freshSeq(a && a.file, ra, c.fresh);
    const sb = freshSeq(b && b.file, ra, c.fresh);
    if (sa !== sb) return sb - sa;
    return cmpNameThenFile(a, b);
  }
  if (ra !== RANK_NONE) return cmpNameThenFile(a, b);   // ③ 同批：按名称

  if (au[0] !== bu[0]) return bu[0] - au[0];   // ④ 最近使用在前
  if (au[1] !== bu[1]) return bu[1] - au[1];   // ⑤ 用得多的在前
  return cmpNameThenFile(a, b);                // ⑥ 名称 → 文件名
}

/**
 * 排序模板列表。**不改入参**（返回新数组）。
 *
 * 末尾用「原始下标」兜底：即使两条模板所有键全等，也保持后端给的相对次序 ——
 * 不依赖引擎的排序稳定性（V8 稳定，但这是实现细节，不是契约）。
 *
 * @param {object[]} items 后端 `GET /api/templates` 的 `items`
 * @param {object} [ctx] 见 `compareTemplates`
 * @returns {object[]} 新数组
 */
export function sortTemplates(items, ctx) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item, index) => ({ item, index }))
    .sort((x, y) => compareTemplates(x.item, y.item, ctx) || (x.index - y.index))
    .map((row) => row.item);
}
