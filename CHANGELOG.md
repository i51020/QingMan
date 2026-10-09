# 版本记录 · 青蔓 QingMan

> **定位**：本文件是**版本制明细表**，只回答「某个版本改了什么」。
> **进度以时间线为准**，要判断当前做到哪一步，请看 `docs/任务进度.md`。

版本规则：**SemVer 三段式 `V<MAJOR>.<MINOR>.<PATCH>`，从 V0.0.1 起**（2026-10-09 采用）。递增语义：`patch` 修复 ／ `minor` 逻辑迭代 ／ `major` 不兼容变更。旧「V0.01 起、每次 +0.01」规则已作废。**不升版也要留回退点**：同版本内的改动追加为修订 `r2`、`r3`…（见 §P0-6）。提交前必须先 `store.py commit`。

---

## V0.0.3 — 2026-10-09

**主题**：品牌标记进入界面 —— 顶栏接入青蔓 logo，颜色跟随主题变量而非硬编码。

> 用户裁定：① **不留**白色圆角底板，只做透明底纯标记；② 落盘 `src/web/assets/`，版本号 ＝ **V0.0.3（patch）**；③ favicon 简化版待预览后另判。
>
> **后续（2026-10-09 21:26）**：上述 ③ 已结案 —— favicon / 小尺寸简化标记裁定 **现在不做**（依据 16px 尺寸实测；详见 `docs/项目约定.md` §P2 第 9 项）。

### 变更

- **新增资源** `src/web/assets/logo.svg`（30,094 B）：源自 `E:\本地资源库\共用资产\品牌资产\Logo\青蔓QingMan\青蔓logo设计_02_01.svg`，只取可见图形 `path1`；剔除不可见的 `path2` 与白色圆角底板图层；viewBox 由原画布 `541.867²` 裁至图形包围盒 `403.610 × 422.634`（图形放大约 1.34 倍）
- **顶栏接入**：`index.html` 与 `help.html` 的品牌区新增 `<span class="brand-logo" aria-hidden="true">`（纯装饰；语义由相邻品牌文字提供）
- **着色方式**：CSS mask 取形状 + `background-color: var(--qm-accent-ink)` —— 浅色 `#1d6d50` / 深色 `#7dd6b0`，**一份文件随主题切换**
- **样式归位**：`.brand` / `.brand-mark` / `.brand-sub` / `.brand-logo` 由 `layout.css` 移至 `base.css`，供主界面与帮助页共用

### 本次修复 / 消除的缺陷

| 缺陷 | 处理 |
|---|---|
| 帮助页未引用 `layout.css`，其品牌区（青蔓 / QingMan / 使用说明）**一直无样式** | `.brand-*` 上移至两页共用的 `base.css` |
| 源 SVG 中 `path2` 与 `path1` 同形（1748 点）却为 `fill:none`，属**不可见冗余** | 落盘副本中剔除 |
| 源 SVG 含白色圆角底板图层，直接用于深色界面会形成突兀白块 | 落盘副本只取图形，剔除底板与画布留白 |
| 源 SVG 的 `fill:#000000` 硬编码 → 深色主题下几乎不可见 | 落盘副本改 `currentColor`，颜色交由 CSS 变量 |

### 验证（均为实测）

| 项 | 结果 |
|---|---|
| `tools/verify.py preview/V0.0.3` | **36 项全部通过** |
| 沙盒服务冒烟（preview 副本独立启动 8790） | 首页 / `assets/logo.svg` / `base.css` / `help.html` 全 **200**；`logo.svg` → `image/svg+xml` |
| 计算样式探针 | `--qm-accent-ink: #7dd6b0` → `logo.background: rgb(125, 214, 176)`；`mask-image` 指向 `assets/logo.svg`；盒子 22×22 |
| 双主题渲染 | 浅色深绿 `#1d6d50` / 深色浅绿 `#7dd6b0`，**颜色跟随变量，非硬编码** |

### src/ 代码

`src/web/assets/logo.svg`（新增）、`src/web/index.html`、`src/web/help.html`、`src/web/css/base.css`、`src/web/css/layout.css`。

---

## V0.0.2 — 2026-10-09

**主题**：编辑态不再随刷新丢失 —— 确立编辑态数据契约并由后端持久化；id 唯一性由「概率」改为「判定」。

> 用户裁定：持久化载体＝后端文件；保存模式＝自动保存；流程＝新建 `preview/V0.0.2/` 走完整五步；版本号＝ **V0.0.2（patch）**。

### 变更

- **编辑态数据契约**：`src/shared/schema.json` 新增 `editorNode` / `editorDocument` / `editorResponse` 三段，前后端同一份定义
- **持久化**：新增 `GET /api/editor` 与 `PUT /api/editor`，文档落在项目根 `data/editor.json`；写入用「临时文件 + `os.replace`」**原子替换**
- **自动保存**：编辑后防抖 800ms 自动写盘；顶栏新增保存状态 chip（未保存 / 保存中 / 已保存 HH:MM / 保存失败）；`Ctrl+S` 跳过防抖立即保存
- **id 唯一性（N3）**：`uid()` 由「时间基 + 计数」改为**对已用集合判定后派发**；新增 `reserveIds()`（恢复文档后登记既有 id）、`assertUniqueIds()`（让唯一性可断言）、`resetIdRegistry()`
- **同级重名检测**：新增 `hasSiblingName()`，**大小写不敏感**（落盘目标多为 Windows 文件系统）；新建与重命名均拦截
- **文档序列化**：新增 `toDocumentNode()` / `fromDocumentNode()`；后者对非法结构抛错并标明出错路径

### 本次修复 / 消除的缺陷

| 缺陷 | 处理 |
|---|---|
| 刷新页面即丢失全部编辑内容（`main.js` 每次用硬编码示例重建） | 后端持久化 + 启动恢复 |
| `uid()` 无冲突检测，且计数随页面重载归零 → 并入持久化后可能撞号 | 改为集合判定派发；实测固定时钟下不登记既有 id **必然**撞号，`reserveIds()` 后消除 |
| 同层同名节点会被 `toPlainTree` **静默覆盖** | 新建 / 重命名阶段拦截（大小写不敏感） |
| 服务端对编辑态文档**无任何校验** | `dtree_core.validate_document()`：结构、命名、id 唯一、同层重名、规模上限，任一不合法**拒写** |
| 文档损坏时若静默当作空文档，会**悄悄覆盖用户数据** | `editorCorrupt` 显式报错，前端提示且不写盘 |

### 验证（均为实测）

| 项 | 结果 |
|---|---|
| `tools/verify.py preview/V0.0.2` | **36 项全部通过**（新增「编辑态契约」「编辑态接口与错误码」两项） |
| 接口冒烟（preview 独立启动 8794） | `GET /api/editor` 首次 `doc=null`；`PUT` 合法 → 200 + `stats{dirs:1,files:1}`；回读一致 |
| 拒写分支 | 重复 id → 400 `editorIdDuplicated`；同级重名 → 400 `editorSiblingDuplicated`；非法段名 → 400 `segmentInvalid`；缺防护头 → 403 `missingGuardHeader`；损坏文档 → 400 `editorCorrupt` |
| 拒写不污染 | 连续 3 次非法 `PUT` 之后，回读仍是上一次合法内容 |
| 数据模型单元断言 | **23/23 通过**（含固定时钟下「不 `reserve` 必撞号 → `reserve` 后不撞号」的对照证明） |
| 原子写入 | `data/` 下无 `.tmp` 残留 |

### src/ 代码

`src/web/js/modules/tree-model.js`、`src/web/js/main.js`、`src/web/js/core/api.js`、`src/web/index.html`、`src/server/{config,dtree_core,routes,app}.py`、`src/shared/{schema,error-codes}.json`。

---

## V0.0.1 — 2026-10-09

**主题**：版本号重制为 SemVer 三段式；交付机制由全量快照改为内容寻址存储。

> **编号说明**：本版 `src/` 内容与旧编号快照 `versions/V0.01/` **逐字节相同**。重制的是**编号规则与交付机制**，不是应用代码。旧编号 `V0.01` 保留为 `V0.0.1` 的别名（记于 `MANIFEST.json` 的 `legacyAlias` 字段）。

### 修订索引（同版本多修订，2026-10-09 采用）

> 规则见 `docs/项目约定.md` §P0-6。版本号不变，但每次改动都留独立清单，均可精确回退。

| 修订 | 清单文件 | 时间 | 内容 | 取回命令 |
|---|---|---|---|---|
| **r1** | `MANIFEST.json` | 2026-10-09 13:38:44 | 版本号重制为 SemVer；启用内容寻址存储 | `store.py checkout V0.0.1@r1` |
| **r2** | `MANIFEST-r2.json` | 2026-10-09 15:42 | N1 本地服务调用来源校验 + 旧编号统一 | `store.py checkout V0.0.1@r2` |
| **r3** | `MANIFEST-r3.json` | 2026-10-09 16:15 | 帮助页独立成页（内容走 i18n 取词）+ 主界面版本号全部剔除 | `store.py checkout V0.0.1@r3` |

### 变更

- **版本号**：`V<主>.<两位次>`（+0.01 固定步进）→ **SemVer `V<MAJOR>.<MINOR>.<PATCH>`**，起始 V0.0.1
- **存储**：全量快照（`SNAPSHOT.json` + MD5）→ **内容寻址存储**（`store/objects/` blob 池 + `MANIFEST.json`）
- **指纹**：MD5 → **SHA-256**；清单摘要改为「路径 + 指纹」排序后整体哈希（**文件改名也能检出**）
- **回退**：手工 `cp -r` → `store.py checkout`；多余文件先进 `store/.trash/` 回收区并逐字节校验
- **新增工具**：`tools/store.py`（commit / checkout / log / diff / fsck）
- **兼容层**：`tools/release.py` 保留旧命令，内部转发到新机制

### 本次修复 / 消除的缺陷

| 缺陷 | 处理 |
|---|---|
| `verify.py` 的 `md5()` 定义后**从未被调用**（死代码），而错误笔记承诺的「未动文件与基线 MD5 一致」检查项**从未实现** | 补齐为 `--against <版本>` 指纹比对；死代码已删除 |
| `release.py` 只记录清单，**无任何反查工具** | 新增 `verify --against` 与 `store diff` |
| 旧聚合校验丢路径，**文件改名检测不出** | 清单摘要改为含路径参与运算 |
| 快照目录名可能与其内容版本**不符** | 新增「清单自洽」校验项 |

### 验证（均为实测）

| 项 | 结果 |
|---|---|
| `tools/verify.py`（主线，含 `--against V0.0.1`） | **31 项全部通过** |
| 沙盒端到端 | 改动/新增/移除三类差异准确识别 → commit V0.0.2 → diff 正确 → checkout 回退后与 V0.0.1 **完全一致** → 回收区收存 2 个文件 → `fsck` 25 blob **0 损坏** |
| 去重效果 | V0.0.2 的 23 个文件新增 **3** 个 blob、复用 **20** 个（对象池 22→25，而非 45） |

### src/ 代码

**无改动**（与 V0.01 逐字节相同）。

### r2 · 2026-10-09 15:42 —— N1 来源校验与旧编号统一（**同版本内，未升版**）

> 用户裁定：N1 落地与旧编号统一**均不升版**，VERSION 仍 `V0.0.1`。清单：`versions/V0.0.1/MANIFEST-r2.json`。

| 文件 | 内容 |
|---|---|
| `src/server/app.py` | 新增 `host_of()` · `_guard()` · `_guard_write()` · `do_OPTIONS` —— **本地服务调用来源校验**（Host 白名单 + Origin 严格同源 + 写操作防护头 + 拒答 CORS 预检）。此前全文无来源校验，任意网页可盲发 POST 触发磁盘写入 |
| `src/server/config.py` | 新增 `ALLOWED_HOSTS` · `GUARD_HEADER` · `GUARD_HEADER_VALUE` 与 `_env_list()` |
| `src/shared/error-codes.json` | 新增 4 码：`hostRejected` · `originRejected` · `missingGuardHeader` · `methodNotAllowed` |
| `src/web/js/core/api.js` | `DEFAULT_HEADERS` 固定携带 `X-QingMan: 1` |
| `src/web/index.html` | 版本徽标 + 侧栏文案 `V0.01` → `V0.0.1`（**编号重制漏改**） |
| `src/shared/schema.json` | `"version"` `V0.01` → `V0.0.1`（**编号重制漏改**） |

**验证**：沙盒冒烟 **25/25 通过**（含「被拒请求均未落盘」单独断言）；5 个 `.py` ast 通过、2 个 JSON 合法、`api.js` ESM 语法通过；缓存残留 0。

**✅ 遗留已清（2026-10-09 16:15）**：原「本轮改动 `src/` 但未升版 → 无 store 回退点」的问题，已由 `tools/store.py` 的**同版本多修订**机制解决 —— 该状态已固化为 `versions/V0.0.1/MANIFEST-r2.json`，可用 `store.py checkout V0.0.1@r2` 完整取回。机制细节见 `docs/项目约定.md` §P0-6。

### r3 · 2026-10-09 16:15 —— 帮助页独立成页 + 主界面版本号剔除（**同版本内，未升版**）

> 用户裁定：版本徽标只在帮助页显示；帮助页做**独立页**、内容抽成**独立文件**；快捷键节先留空。清单：`versions/V0.0.1/MANIFEST-r3.json`。

| 文件 | 内容 |
|---|---|
| `src/web/help.html` | **新增**。帮助页骨架 —— 纯空壳 + `data-i18n` 键名，一个中文字面量都不写 |
| `src/web/js/i18n/zh-CN.js` | **新增**。帮助页正文与分节结构的**唯一数据源**（快速开始 / 界面说明 / 目录树操作 / 快捷键 / 安全说明 / 版本与关于 / 免责声明） |
| `src/web/js/help.js` | **新增**。只做三件事：填充静态占位 → 渲染分节 → 取后端实测版本 |
| `src/web/css/help.css` | **新增**。帮助页布局；色彩、圆角、间距全部取 `var(--qm-*)` |
| `src/web/index.html` | 移除顶部版本徽标 `#chipVersion`；侧栏文案去掉版本号；顶栏右侧新增「帮助」按钮 `#btnHelp` |
| `src/web/js/main.js` | 不再往主界面写版本号（后端 chip 改为「后端已连接」、状态栏去掉版本）；绑定帮助按钮，**新标签**打开帮助页 |
| `src/web/css/layout.css` | 补 `.topbar-right` 弹性布局（原先未定义，直接加第二个元素会竖排） |
| `tools/verify.py` | 必需文件 +4；关键 id `chipVersion` → `btnHelp`；指纹比对由固定 `MANIFEST.json` 改为对齐**最高修订**；新增「帮助页无硬编码中文」校验项；移除已无用的 `import json` |

**帮助页交互**：顶栏「帮助」→ `window.open('./help.html', '_blank', 'noopener')`。用新标签而非同标签跳转，原因是主界面内存里可能正握着一棵**尚未落盘**的目录树，跳转会丢掉编辑态。版本徽标在帮助页出现两处（顶栏 chip + 「版本与关于」信息表）；后端未连接时回退本机记录值并附提示，保证离线也能看帮助。

**快捷键**：按要求**先留空**（`help.kbd.pending` 占位），待功能面稳定后统一约定，已登记入 `docs/项目约定.md` §P2。

**验证**（均为实测）：

| 项 | 结果 |
|---|---|
| `tools/verify.py . --against V0.0.1` | **36 项全部通过**（含「指纹比对 V0.0.1@r3 完全一致」「帮助页无硬编码中文」） |
| 沙盒运行时冒烟 | 服务启动 → `/api/health` 返回 `V0.0.1` → `/`、`/help.html`、`/css/help.css`、`/js/help.js`、`/js/i18n/zh-CN.js` 全部 **200** |
| 取词闭环检查 | **48 项断言全通过**：`helpSections` 键位、`help.html` 的 7 个 `data-i18n` 键、`help.js` 的 10 个字面量键全部在字典中命中；`help.html` 零中文字面量 |
| 对象池 | `fsck` **35 blob / 0 损坏**；`diff V0.0.1@r1 V0.0.1@r3` = 改动 8 / 新增 4 / 缺失 0 |

**去重效果**：r3 的 26 个文件里新增 **7** 个 blob、复用 **19** 个（对象池 28→35，而非 78）。

---

## V0.01 — 2026-10-09（旧编号，已重制为 V0.0.1）

**主题**：最小可运行骨架，跑通「架构 → 预览 → 落地 → 快照 → 回退」闭环。

### 新增

- **专业架构拆分**（放弃单文件 HTML）
  - 前端按职责分为 `core/`（总线、仓库、接口）、`modules/`（数据模型）、`ui/`（树视图、属性面板、轻提示）
  - 后端拆为 `config` / `dtree_core` / `routes` / `app` 四个模块，`dtree_core` 为纯逻辑层，不依赖 HTTP
  - 前后端共享契约落在 `src/shared/`：`schema.json`（数据结构）+ `error-codes.json`（错误码与文案）
- **目录树编辑**：新建子节点、重命名、删除、展开/折叠、节点选中与属性查看
- **一键生成**：`仅演练（dryRun）` 与真实落盘两种模式；重复生成幂等
- **本地后端**：`127.0.0.1` 单机服务，端口 8765–8775 自动扫描，零第三方依赖
- **安全**：静态文件路径穿越防护、请求体大小上限、目录名校验（非法字符 / 系统保留名 / `.` `..`）
- **版本工具链**：`tools/versioning.py`（版本号运算）、`release.py`（快照 + 递增 + 列表）、`promote.py`（预览→主线单推）、`verify.py`（29 项交付校验）
- **环境变量开关**（便于自动化测试）：`QM_PORT` / `QM_PORT_END` / `QM_HOST` / `QM_OPEN_BROWSER` / `QM_MAX_BODY`
- **内容资产**：`templates/` 收录 17 套中文目录树模板（P0–P9 / S2–S8）

### 验证

| 项目 | 结果 |
|---|---|
| `tools/verify.py`（预览版） | 29 项全部通过 |
| `tools/verify.py`（主线） | 29 项全部通过 |
| 实机冒烟测试 | 15 项全部通过（含演练不写盘、真实落盘、结构一致、幂等、4 组错误分支、路径穿越） |

### 本版修复

- 嵌套错误码占位符未二次填充，导致报错文案出现字面量 `{name}` —— 已在 `dtree_core` 与 `routes` 修正并复测通过
- `tools/verify.py` 的 Python 语法检查由 `py_compile` 改为 `ast` 只读解析：原实现**每次校验都会写入 `__pycache__`**，使校验污染被校验目录，导致「未动文件与基线 MD5 一致」永远无法通过。属**工具层修复**，不改变 V0.01 交付内容（`tools/` 不随代码快照复制）

### 尚未实现（规划中）

- 模板库接入界面（导入 / 导出 / 新建 / 删除 / 悬停预览）
- 节点描述字段、多选与批量操作、三段式拖拽指示、右键菜单
- 皮肤系统、中英双语
- 桌面快捷方式创建、目标位置原生文件夹选择对话框
- 布局微调：生成参数区 / 工具栏 / 树的顺序与弹窗式生成交互
