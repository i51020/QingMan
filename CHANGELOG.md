# 版本记录 · 青蔓 QingMan

> **定位**：本文件是**版本制明细表**，只回答「某个版本改了什么」。
> **进度以时间线为准**，要判断当前做到哪一步，请看 `docs/任务进度.md`。

版本规则：**SemVer 三段式 `V<MAJOR>.<MINOR>.<PATCH>`，从 V0.0.1 起**（2026-10-09 采用）。递增语义：`patch` 修复 ／ `minor` 逻辑迭代 ／ `major` 不兼容变更。旧「V0.01 起、每次 +0.01」规则已作废。**不升版也要留回退点**：同版本内的改动追加为修订 `r2`、`r3`…（见 §P0-6）。提交前必须先 `store.py commit`。

---

## V0.0.11 — 2026-10-10

**主题**：模板工作区接入 —— 左栏从「只有自检清单」变成真正能载入 17 套模板。

> **立项依据**：用户 10 条需求第 2 条「左=模板工作区」此前只落地了**标题**（V0.0.8），`templates/` 17 套在 `src/` **零引用**。本次接入后，三栏最后一栏名实相符，并同时解除 §P2 第 7 项挂起。

### 变更（`src/`）

- **后端模板接口**
  - `GET /api/templates` → 列表（文件名 / 名称 / 说明 / 目录数 / 文件数）
  - `GET /api/templates/<name>` → 单套完整 `tree` + 统计
  - **安全**：文件名先过白名单 `^[A-Za-z0-9_\u4e00-\u9fff-]+\.json$`（不含路径分隔符，源头堵死穿越），**再**校验解析后的绝对路径仍在 `templates/` 之内（防符号链接绕过）。7 组穿越名沙箱实测全部 `templateNotFound`
  - **优雅降级**：`templates/` **不在版本交付清单内**，预览副本里没有它 → 目录缺失时返回 `available=false` + 空列表，**不报错**
  - 单套损坏只跳过该套，不拖垮整个列表
  - 新增错误码 `templateNotFound` / `templateBadJson` / `templateReadFailed`
- **前端**
  - 左栏新增模板列表 `#templateList`（`#btn`-style 卡片，含名称与规模统计），点击二次确认后载入
  - 新增 `tree-model.js` 的 `fromNestedTree()`：**模板是嵌套字典**（目录=对象、文件=内容字符串），与编辑态文档的 `{id, type, children}` 不同 —— 由它转换并**按既有规则补发 id**（后端不发明第二套 id 规则）
  - 载入**走同一套撤销栈**（`pushHistory()`），可用 `Ctrl/Cmd+Z` 恢复
  - 新错误码在前端本地化（`err.templateNotFound` 等）；**未登记的旧错误码仍回退为后端原文**，与既有行为一致
- **取词表**：新增 `template.*` 与 `err.template*` 键（中英同步）；帮助页 `help.quickStart.3` / `help.ops.sidebar` 改回「可载入模板」的指引
- **§P2 第 7 项结案**：裁定**不引入 `schemaVersion`** —— 青蔓对模板只读不写，版本号的唯一用途（兼容判定）无对象；重议条件为「开始写模板时」

### 工具与测试

- `tests/test_routes.py` 新增 `TemplateTests`（**9 条**）：目录缺失降级、统计、损坏跳过、非 `.json` 忽略、载入返回嵌套结构、7 组路径穿越拒绝、非法后缀拒绝、损坏 `templateBadJson`、缺 `tree` 键 `templateBadJson`。**套件 71 → 80，全通过**
- 沙箱实证（三分支 + Node 转换）：17 套全部列出并载入、路径穿越全拒、预览副本降级正确；`fromNestedTree` 对 17 套的 **id 唯一**与**往返还原一致**（`treePayload` 输出 == 原模板 `tree`）全部通过

---

## V0.0.10 — 2026-10-10

**主题**：收口 —— 修「静态校验全绿但实机不成立」的三处缺口。

> **立项依据**：V0.0.9 收尾后的静态审计发现 2 个 P0 实机缺陷 + 3 个 P1 漂移。三者共同点是**静态断言看不见**：契约都对，用户看到的却是错的。

### 变更（`src/`）

- **默认皮肤 S06 真正生效（P0-a）**
  - 成因：`applySkin()` 在 `qm.skin` 为空时**直接 return、不注入样式表**，而 `skin-picker.js` 的下拉框 `value = saved || S06` 显示的是默认皮肤名 —— 首次启动「下拉写着 S06、界面却是 `tokens.css` 裸色」，用户裁定的默认皮肤**从未生效**
  - 改：`i18n/index.js` 新增 `defaultSkinFile()`，`getSkin()` 无偏好时返回出厂默认（S06）而非空串；`applySkin()` 恒注入 —— **产品不再存在「无皮肤」态**
  - 连带：`skin-picker.js` 移除语义重复的「默认（空）」选项，15 款全列；`skin.default` 取词键删除
- **帮助页版本号不再漂移（P1-a）**
  - `help.versionFallback` 中英两份均写死 `V0.0.5`，一路带到 V0.0.9（后端离线时向用户显示错误版本）→ 现同步为 `V0.0.10`
- **帮助页不与实况矛盾（P1-b）**
  - `help.quickStart.3` / `help.ops.sidebar` 原指引「在左栏模板工作区选模板」，但左栏**无任何模板控件**（只有 4 项骨架自检）→ 改为「模板库尚未接入」的诚实表述，待 V0.0.11 接入后改回
- **英文润色**：`help.support.thanks` 原为中式直译 "Bug fixes come as grace." → "bug fixes are best-effort."

### 工具（`verify.py`，不升版但须留痕）

- 新增 **7h「版本兜底一致」**：`zh-CN.js` / `en-US.js` 的 `help.versionFallback` 必须等于项目根 `VERSION`（防再次写死漂移）
- 新增 **7i「默认皮肤不可缺省」**：`i18n/index.js` 必须引用 `DEFAULT_SKIN_CID`（防再次退化为「无皮肤」裸色）

### 文档

- `docs/接续说明.md` §3.1 补 N4 撤销/重做、桌面快捷方式、UI overhaul 三条为 ✅；§3.2 新增第 10 项「模板库接入」待办（含 `schemaVersion` 决策提示）

---

## V0.0.9 — 2026-10-10

**主题**：功能补全 —— 撤销/重做（50 步）与点击 logo 生成桌面快捷方式。

> **立项依据**：用户 10 条需求中的第 7、8 两条，按 V0.0.8(UI) + V0.0.9(功能) 的版本切分落地。

### 变更（`src/`）

- **撤销 / 重做**
  - `main.js` 引入文档快照栈（`toDocumentNode` / `fromDocumentNode`），上限 **50 步**；工具栏 `#btnUndo` / `#btnRedo` 已预置，现启用
  - 键盘快捷键：`Ctrl / Cmd + Z` 撤销；`Ctrl / Cmd + Y` 与 `Ctrl / Cmd + Shift + Z` 重做；在输入框内保留原生撤销行为
  - 新建 / 重命名 / 删除前自动压栈；撤销后恢复选中 id（若已不存在则回根节点）并触发自动保存
  - `zh-CN.js` / `en-US.js` 帮助页键位表补登 `help.kbd.undo` / `help.kbd.redo`
- **桌面快捷方式**
  - 顶栏品牌区由静态展示改为可点击按钮 `#btnLogo`，点击二次确认后调用后端 `/api/shortcut`
  - 后端新增 `POST /api/shortcut`：优先用 PowerShell `WScript.Shell` 在用户桌面生成 `青蔓 QingMan.lnk`
  - 桌面不可写时降级：在临时目录生成同一份 `.lnk`，以 base64 返回前端触发下载
  - 新增错误码 `shortcutTargetMissing` / `shortcutFailed`；`config.START_BAT` 作为快捷方式目标

### 工具

- `verify.py` 关键 id 清单加入 `btnLogo`

### 验收（全部实测）

| 项 | 结果 |
|---|---|
| 预览 `verify.py preview/V0.0.9` | **56 项 0 失败** |
| 主线 `verify.py . --against V0.0.9` | **61 项 0 失败**，指纹 V0.0.9 完全一致 |
| `unittest` | **71 tests OK** |
| `tools/smoke.py` | **17 项 0 失败** |
| `.lnk` 生成 | 沙箱验证可生成非空快捷方式文件 |

---

## V0.0.8 — 2026-10-10

**主题**：UI  overhaul —— 15 款独立皮肤、中英双语、微信赞赏码支持页、模板名去编号前缀，以及整体切到**锐利新拟物**视觉风格。

> **立项依据**：用户基于参考项目 `E:\临时\20261009_目录树可视化管理器_1152_文心助手` 抛出 10 条需求，并逐条裁定：视觉风格＝锐利新拟物、15 皮肤全保留、默认 S06、模板 `name` 去编号前缀、支持页沿用参考项目微信赞赏码、版本切分 V0.0.8(UI) + V0.0.9(功能)。

### 变更（`src/`）

- **皮肤系统**
  - 新增 15 款皮肤 CSS：`src/web/css/skins/s01-cream-pink.css` … `s15-cream-sunrise.css`，全部通过 WCAG AA 对比度钳制（最小 4.53）
  - 新增皮肤注册表 `src/web/js/i18n/skins.js`：cid / file / label 键 / 三色色板；默认 `S06 月光序章·钢笔灰`
  - 新增 `ui/skin-picker.js`：按背景明度（亮 → 暗）实时排序皮肤下拉框
  - `tokens.css` 新增新拟物变量：`--qm-edge-hi` / `--qm-edge-lo` / `--qm-shadow-dark` / `--qm-shadow-light` / `--qm-inset` / `--qm-select-arrow`
- **中英双语**
  - 新增 `src/web/js/i18n/en-US.js`，键集与 `zh-CN.js` 完全一致；`i18n/index.js` 登记为第二语种
  - `zh-CN.js` 键表由 146 键扩至 **187 键**，新增语言/皮肤/撤销/重做/快捷方式/支持页等全部新文案
  - 顶栏新增语言下拉框 `#langSelect` 与皮肤下拉框 `#skinSelect`
- **锐利新拟物 UI**
  - `index.html`：顶栏加入语言/皮肤/支持按钮；三栏标题明确为「模板工作区 / 目录树工作区 / 属性工作区」；工具栏预置撤销/重做按钮（V0.0.9 启用）
  - `base.css` / `layout.css`：按钮/面板/输入框/树节点统一采用方向阴影 + 内嵌高光，模块边缘清晰立体；树选中态使用 `--qm-inset` 凹陷效果
- **支持页**
  - `help.html` / `help.js` / `help.css` 新增「支持青蔓」分节，展示压缩后的微信赞赏二维码 `src/web/assets/sponsor-wechat.png`（640×640 调色板，28.5 KB）
  - 主界面顶栏新增 `#btnSupport`，点击打开 `help.html#support`
- **模板库**
  - 17 套模板 `name` 字段统一去除 `P0_` / `S2_` 等编号前缀；`templates/模板库来源说明.md` 同步更新

### 工具

- **`tools/verify.py`** 新增 4 项守卫：
  - 「中英取词键对齐 §P0-3 L1」：en-US.js 与 zh-CN.js 键集必须一致
  - 「CSS 变量闭包 §P0-3 L4」：组件 / 皮肤引用的 `--qm-*` 必须在 `tokens.css` 定义
  - 「皮肤注册表 §P0-3 L5」：注册表与 `skins/*.css` 文件一一对应，默认皮肤存在
  - 「二进制换行豁免」：PNG 等二进制文件含 CR 字节不再误报
- 必需文件清单加入 `en-US.js`、`skins.js`、`assets/sponsor-wechat.png`；关键 id 清单加入 `langSelect` / `skinSelect` / `btnSupport` / `btnUndo` / `btnRedo`

### 验收（全部实测）

| 项 | 结果 |
|---|---|
| 预览 `verify.py preview/V0.0.8` | **56 项 0 失败** |
| 主线 `verify.py . --against V0.0.8` | **59 项 0 失败**，指纹 V0.0.8 完全一致 |
| `unittest` | **71 tests OK** |
| `tools/smoke.py` | **17 项 0 失败**（服务读到版本 = V0.0.8） |
| 皮肤对比度 | 15 款全部 ≥ 4.53（AA 门槛 4.5） |
| 体积 | `src/**` 合计 **208 KB** / 上限 400 KB；单文件最大 28.5 KB |
| store 清单 | V0.0.8：48 文件 / 新增 29 blob / 复用 19 / parent=V0.0.7 |

---

## V0.0.7 — 2026-10-09

**主题**：**§P2 台账全面收口**（15 项全部结案或挂起）＋ 三项一并落地 —— 生成文件**换行按扩展名分流**、浅色主题**对比度达标 WCAG AA**、帮助页**补登已有快捷键**。

> **立项依据**：用户裁定「§P2 表内仍未决的 11 项，按专业建议**分三档**依次执行」。执行前逐项做了盘上核查，**其中两处与既往文档描述不符**（见下「两处更正」）。

### 变更（`src/`，共 4 文件）

- **`server/dtree_core.py`** —— 生成文件**换行按扩展名分流**（§P2 第 12 项）：新增 `CRLF_SUFFIXES = (".bat", ".cmd", ".ps1")` 与 `newline_for(name)`；写入点由写死 `newline="\n"` 改为 `newline=newline_for(target.name)`，并把值里的 **CR / CRLF 先归一为 LF** 再交给 `open` 翻译（否则原值含 CRLF 会被译成 `\r\r\n`）。**判据是扩展名，不是 `os.linesep`** —— 后者会把平台差异重新引入产出，正是第 11 项要消灭的东西
- **`web/css/tokens.css`** —— 新增变量 **`--qm-btn-bg`**（浅色 `#2a8060` / 深色沿用 `#4fbf90`），并将浅色 **`--qm-warn`** 由 `#a8721a` 调深为 **`#946417`**（§P2 第 13 项）
- **`web/css/base.css`** —— `.btn-primary` 的 `background` / `border-color` 由 `var(--qm-accent)` 改用 `var(--qm-btn-bg)`。**品牌主色 `--qm-accent` 未动**（方案②：改动面最小、回滚最容易）
- **`web/js/i18n/zh-CN.js`** —— 帮助页键位表**补登已有快捷键**（§P2 第 8 项）：新增取词键 `help.kbd.save`（`Ctrl / Cmd + S — 立即保存`）；`help.kbd.pending` 语义由"待约定"改为"本版仅设上述一项"

### 工具

- **`tools/verify.py`** 新增两项守卫：**「CSS 类名形态 §P2 第 1 项」**（kebab-case，禁下划线 / 大写；**先剥离 `url()`**，否则 `url("…/logo.svg")` 里的 `.svg` 会被误判为类名）；**「体积上限 §P2 第 4 项」**（`src/**` ≤ 400K、单文件 ≤ 64K）。校验项数：主线 **49 → 51**（带 `--against` **51 → 53**）、预览 **46 → 48**
- 同批：模块 docstring 检查项清单补 7e / 7f；《错误笔记》§一.1 项数补【四更正】

### 两处更正（执行中发现，既往描述有误）

| # | 既往说法 | 盘上实况 |
|---|---|---|
| 1 | 「产品**零全局快捷键**、全鼠标驱动」（第 8 项建议的前提） | **不成立**：`main.js:364-370` 早已有 `Ctrl / Cmd + S` 立即保存（`preventDefault()` + `saveNow()`）。真问题是**键位存在却没写进帮助页** |
| 2 | §P2 判据「看**行首**是否带 ✅」 | **恒为假**：`✅` 全部落在**说明列内**，行首只有 `| 编号 |`。判据已更正为「看**说明列开头**是否含 ✅ / ⚠️」 |

### 验收（全部实测）

| 项 | 结果 |
|---|---|
| 预览 `verify.py preview/V0.0.7` | **48 项 0 失败** |
| 主线 `verify.py . --against V0.0.7` | **53 项**，指纹 `V0.0.7@r1` **完全一致** |
| `unittest` | **71 tests OK** |
| `tools/smoke.py` | **17 项 0 失败**（服务读到的版本 = V0.0.7） |
| **换行分流沙箱实证** | `.bat` / `.CMD` / `.ps1` → CRLF；`.md` / 无后缀 / `.txt` → LF；原值含 CRLF 的**未产生 `\r\r\n`** |
| **无头 Edge 对比度审计**（2 页 × 2 主题） | index 浅色 **0 处**、index 深色 **0 处**、help 浅色 **0 处**、help 深色 **0 处**（改前浅色 **2 处**）。实测 `.btn-primary` 白字 on `#2a8060` = **4.82**、`--qm-warn` 元素 = **4.87** |
| 新增守卫**反向**实证 | 探针含 `.bad_name` / `.GoodName` / 70K 单文件 → **三者全部被抓出**，且 `url("…/logo.SVG")` **未误报** |
| 对象池 | `store.py fsck` → **84 blob / 0 损坏**；V0.0.7 清单 **29 文件**（新增 5 blob、复用 24） |
| 漂移核对 | `--against V0.0.6` → **改动 4 / 新增 0 / 缺失 0**（恰为本次所改 4 个 `src/` 文件） |

**注**：`src/` 合计体积按**字节求和**为 **137 KB**（§P2 第 4 项基线口径）；`du` 的**磁盘块口径**为 180K，两者差在簇对齐。

---

## V0.0.6 — 2026-10-09

**主题**：中栏顶部的**生成参数区改为可折叠** —— 三项参数是"一个项目设一次"的低频项，却长期占据一整行；收起后只留一行摘要，关键设定仍一眼可见。

> **立项依据**：`docs/项目约定.md` §P2 第 14 项（中栏参数区形态）。用户提出「根文件夹名 / 目标位置 / 仅演练 留在原位还是归入右侧属性栏」。
>
> **裁定**：**留在原位**，理由是**作用域错配** —— 三项是**作业级（job-scoped）可编辑参数**，而右栏是**选中节点级（selection-scoped）只读属性**（`inspector.js` 明写"只读，不做任何编辑"），且 `inspector.render()` 在无选中时**整栏清空为 `—`**，与「目标位置是必填项、必须始终可编辑」硬冲突。另有三条支撑：①「仅演练」直接改写按钮行为、按帮助页引导在**点生成前**才取消勾选，挪到最右会看不见状态；② 目标位置是**长路径**，右栏固定 **280px** 太窄；③ 帮助页已固化分区语义（`help.ops.center` / `help.ops.inspector`）。
>
> **而"原位"的形态确实该改**：中栏顶部并排两条常驻 bar（`#genBar` + `#toolbar`），都带 `border-bottom`，读起来像两个互相竞争的工具栏。用户提出该问题本身即是信号。

### 变更

- **`index.html`**：`#genBar` 由「三个控件并排的一行」改为**两段结构** —— 折叠头（`.genbar-head` 按钮：`.genbar-caret` + `.genbar-summary`）＋ `.genbar-fields`（原有三个控件原样移入）
- **`layout.css`**：`#genBar` 改为纵向弹性布局；新增 `.genbar-head` / `.genbar-caret` / `.genbar-summary` / `.genbar-fields` 与 `#genBar.is-collapsed .genbar-fields { display: none }`。**无裸色值、不感知皮肤**（全走 `var(--qm-*)`），并补 `:focus-visible` 焦点环
- **`main.js`**：新增 `initGenBar()` / `genSummaryText()` / `renderGenBar()` / `setGenBarCollapsed()`；折叠头点击切换、`#inRoot` / `#inTarget` 的 `input` 与 `#inDryRun` 的 `change` 实时刷新摘要行
- **`i18n/index.js`**：新增偏好键 **`qm.genBar`**（`'open'` / `'closed'`）与 `getGenBarState()` / `setGenBarState()`
- **`zh-CN.js`**：新增 8 键 —— `gen.summaryEmpty` / `summaryTarget` / `summaryRoot` / `summaryDryRun` / `summaryWrite` / `summarySep` / `toggleExpand` / `toggleCollapse`；并在帮助页「界面说明」新增 `help.ops.genBar` 一条
- **`tools/verify.py`**：「偏好键名 §P0-3 L6」由要求 `qm.lang` / `qm.skin` 扩为**要求三个偏好键**（新增 `qm.genBar`），并改为列出**具体缺失键**而非笼统提示

### 三条设计决定（均有实测依据）

| 决定 | 理由 |
|---|---|
| **折叠态只在启动时定一次并落盘**，之后完全由用户控制 | 若在每次渲染时按"目标位置是否已填"动态推断，用户输入目标位置的**第一个字符**就会触发参数区自动收起 —— 恰好与帮助页引导顺序（先填目标位置）相反。探针已把这条写成断言（`输入过程不会自动收起/展开`） |
| **默认展开** | 目标位置目前不跨会话保存，故首次启动恒为展开 —— 帮助页的引导流程（`help.quickStart.4` 填写目标位置）无需多一次点击 |
| **目标位置为空时点「一键生成」→ 自动展开** | 否则参数区收起时该输入框不可见，`focus()` 无处落地，用户只收到"请先填写目标位置"却看不到该填哪里 |

### 验收（全部实测）

| 项 | 结果 |
|---|---|
| `verify.py preview/V0.0.6` | **46 项 0 失败** |
| `verify.py . --against V0.0.6` | **50 项 0 失败**（含实况段刷新后），指纹**完全一致** |
| 单元测试 | **71 项全过**（预览版 `src` 与主线各跑一遍） |
| `tools/smoke.py` | **17 项全过**，`/api/health` 报 `version=V0.0.6` |
| **行为探针**（注入式，无头 Edge） | **22 项 0 失败** —— 初始展开 / 摘要文案 / 收起后字段隐藏与 `aria-expanded` / 箭头 glyph / `title` / `qm.genBar` 落盘 / 输入时摘要实时刷新且**不自动收起** / 取消演练改显「写盘」/ 根名拼接 / 再次展开 / **空目标点生成自动展开并聚焦** / 运行期无控制台错误 |
| **WCAG 对比度审计**（注入式） | 浅色 **1 处**、深色 **0 处**。唯一一处是**既有** `.btn-primary` `#ffffff` on `--qm-accent #2f8f6b` = **3.99**（§P2 第 13 项，非本轮引入）；**新增的摘要行未引入任何新违规**（`--qm-text-dim` on `--qm-surface` ≈ 5.17，达标） |
| 取词键闭包 | **116 个引用键全部命中**（取词表 144 键） |
| 渲染 | 浅/深 × 展开/收起 共 4 态截图，中文全部正常、无裸 key；帮助页新条目正常渲染 |
| store 清单 | **29 文件 / 新增 6 blob / 复用 23 / parent=V0.0.5**（`sha256:626ca062e7ef96dd…`） |

### 仓库结构

- 按 **§P1-7** 在 `promote` 后**清空 `preview/V0.0.6/`**，**历史中不留痕**。【更正 2026-10-09：原文记的做法为"开发期 `git add` 进索引、落地后 `git rm -r -f`" —— 该做法**已作废**（沙箱实证：净效果为零；若漏 `git rm` 直接提交，副本会真的进历史）。正确判据与路线见 `docs/项目约定.md` §P1-7「清空细则」】

---

## V0.0.5 — 2026-10-09

**主题**：P0-3 双语与皮肤预留 —— 由"只有帮助页取词"推进到**全界面零硬编码文案**，并把皮肤机制从"口头约定"变成**可验收的契约**。

> 立项背景（`docs/项目约定.md` §P0-3）：中英双语与多皮肤都在路线图内。等到 V0.1.x 再做，等于重写全部 UI 模块与组件 CSS —— 所以先立约定、再把**主界面**这条最大的尾巴收掉。
>
> 立项时状态为"⚠️ 部分落地"：`help.js` 有 `t()`、`help.html` 已零中文字面量，**但主界面文案全部直写**，`skins/` 目录不存在。

### 变更

- **新增取词运行时** `src/web/js/i18n/index.js`（4,653 B）：`t(key, vars)`（支持 `{name}` 占位替换，缺键时 `console.warn` 而非静默）、`applyStatic(root)`（扫 `data-i18n` / `data-i18n-title` / `data-i18n-placeholder` / `data-i18n-aria-label`）、`setLocale()`、`getSkin()` / `setSkin()` / `applySkin()`、`initPrefs()`
- **取词表扩容** `zh-CN.js`：由"帮助页正文的唯一数据源"扩为**全界面唯一取词表**，**47 → 136 键**；按 `app/topbar`、`sidebar/check`、`gen`、`tree`、`inspector`、`status`、`toast`、`sample`、`module-internal`、`help`、`about` 分区；保留 `helpSections` 导出
- **主界面取词化** `index.html`：所有中文改为 `data-i18n*` 属性（含 `<title data-i18n="app.title">`）
- **JS 模块取词化**：`main.js`（全部 toast / status / 默认示例树走 `t()`，新增 `idList()` 用 `t('list.separator')` 拼列表）、`core/api.js`、`core/bus.js`、`ui/inspector.js`、`modules/tree-model.js`；`help.js` 删掉本地 `t()` 改从 `index.js` 导入（局部函数改名 `applyStatic` → `applyShell` 以避开同名导出）
- **新增设计变量** `tokens.css`：`--qm-on-accent`（浅色 `#ffffff` / 深色 `#0f1a16`）—— 为 L7 的清除动作提供语义化落点
- **新增皮肤契约** `src/web/css/skins/README.md`：皮肤 == **一组变量覆盖文件**，经 `applySkin()` 注入 `<link id="skinLink">`；**组件 CSS 不得感知皮肤**（不写 `.skin-dark .btn` 这类选择器）
- **偏好持久化**：`qm.lang` / `qm.skin` 两键写入 `localStorage`；启动顺序固定 `initPrefs(); applyStatic(document); render(); … boot();` —— **先恢复偏好再填字**，避免闪一次默认语言

### 本次消除的缺陷

| 缺陷 | 处理 |
|---|---|
| `src/web/css/base.css` 第 53、55 行**硬编码 `#fff`**（§P0-3 L7 登记在案） | 改 `color: var(--qm-on-accent)`。**计算值不变**（浅色下仍是 `#ffffff`），故属**纯重构、零视觉变化** |
| 主界面文案全部直写，改语言需逐文件grep | 全部经 `t()`；`verify.py` 三项把关（主界面 / 帮助页 / JS 均无中文字面量） |

### 验证（均为实测）

| 项 | 结果 |
|---|---|
| `tools/verify.py preview/V0.0.5` | **46 项 · 0 失败** |
| `tools/verify.py . --against V0.0.5` | **50 项 · 0 失败**；指纹比对**完全一致** |
| `python -m unittest discover -s tests` | **71 项全过**（对**预览版** `src/` 也跑了一遍，落地前后各一次） |
| `tools/smoke.py` | **17 项全过**，`/api/health` 报 `version=V0.0.5` |
| 无头 Edge 渲染（浅/深 × 首页/帮助页，4 张） | 页面注入错误捕获层后**全部 `NO-ERRORS`** —— 无 import 断裂、无 `console.error`；中文全部正常渲染、无裸 key 外露 |
| WCAG 对比度审计（注入式，遍历全部含文本元素） | 深色 **0 处**；浅色 **2 处**不达 AA，**均为既有色值、非本轮引入** → 见下"遗留" |
| 取词键闭包 | 108 个引用键（页面属性 + JS 字面量）**全部命中** 136 键取词表 |
| 换行一致性 | `src/**` 与 `VERSION` 全 LF（本轮改动未引入 CR，规范化确认为 no-op） |

### src/ 代码

**修改**（10）：`src/web/index.html`、`src/web/css/tokens.css`、`src/web/css/base.css`、`src/web/js/main.js`、`src/web/js/help.js`、`src/web/js/i18n/zh-CN.js`、`src/web/js/core/api.js`、`src/web/js/core/bus.js`、`src/web/js/modules/tree-model.js`、`src/web/js/ui/inspector.js`

**新增**（2）：`src/web/js/i18n/index.js`、`src/web/css/skins/README.md`

> `help.html` **不在改动清单内** —— 它早在 V0.0.1@r3 就已取词化（本次实测确认）。

### 遗留（已登记，待裁定）

| 项 | 说明 | 登记处 |
|---|---|---|
| 浅色主题 2 处对比度不达 WCAG AA | `.btn-primary` 白字 on `--qm-accent #2f8f6b` = **3.99**；`--qm-warn #a8721a` on `#f6f8fb` = **3.98**。**既有色值缺陷**，不在 P0-3 的 L1–L8 范围内；改配色属可见 UI 变更，**须用户裁定** | §P2 第 13 项 |
| 生成文件换行的扩展名例外 | 全局 `newline="\n"` 对 `.bat` / `.cmd` / `.ps1` 不正确（`cmd.exe` 跨行结构可能解析异常）。当前 17 套模板无此类后缀，**未触发** | §P2 第 12 项 |

### 工具链

- `tools/verify.py` 新增 9 项守卫：「主界面无硬编码中文」「JS 文案经取词表 §P0-3 L1」「取词键闭包 §P0-3 L2」「组件 CSS 无裸色值 §P0-3 L4」「组件 CSS 不感知皮肤 §P0-3 L5」「皮肤目录契约 §P0-3 L5」「偏好键名 §P0-3 L6」，并把 `src/web/js/i18n/index.js` 加入必需文件清单
- 发布流程照五步走：`bump` → 预览开发 → 校验 → `promote --force` → `store.py commit` → git 提交 + tag

---

## V0.0.4 — 2026-10-09

**主题**：P0-1 落盘安全边界 —— 给"青蔓唯一会写用户磁盘的动作"装上**服务端**闸门；同轮把 `src/` 内两处换行点一并规范化。

> 立项背景（`docs/项目约定.md` §P0-1）：生成目录是青蔓**唯一会写用户磁盘**的动作。原实现只校验 `target` 是非空字符串，**无任何路径约束**；`dryRun` 也来自请求体、服务端不强制。任何请求都能让它在 `C:\Windows` 下建目录树 —— 前端弹窗属 UI 层、可绕过。
>
> 立项时状态为"⚠️ 尚未实现"。

### 变更（R1–R8 全部落地在服务端）

| 规则 | 落点 |
|---|---|
| R1 路径规范化 | `config.resolve_path()`（`expanduser().resolve()`，异常时退回 `absolute()`）+ `dtree_core.check_target()` |
| R2 盘根黑名单 | `check_target()`：`path.parent == path` 或 `len(path.parts) < 2` → `targetTooShallow` |
| R3 系统目录黑名单 | `config.BLOCKED_SUBTREES`（`SystemRoot` / `System32`、`Program Files`、`Program Files (x86)`、`ProgramData`），**整棵子树**拒绝 → `targetBlocked` |
| R4 用户目录黑名单 | `config.BLOCKED_ROOTS`（`USERPROFILE` / `Desktop` / `Documents` / `Downloads`）**仅根本身**拒绝，**子目录放行** → `targetBlocked` |
| R5 项目自身黑名单 | 项目目录及其**上级**目录拒绝（防工具改自己）→ `targetReserved` |
| R6 规模阈值 | `config.MAX_NODES`（`QM_MAX_NODES`，默认 500）；`build_tree()` 用 `count_tree()` 算**计划规模**，超限即拒（`dryRun` 同样拦截）→ `tooManyNodes` |
| R7 覆盖策略 | 目录已存在 → 复用；文件已存在 → **跳过、不覆盖、不比对内容**，计入 `existed` |
| R8 永不删除 | 全程只 `mkdir` / 新建文件，**无任何删除调用** |

- **辅助函数**：`config.is_within(child, parent)` —— 因 **Python 下限 3.8**，不能用 3.9+ 的 `Path.is_relative_to`，故用 `relative_to` + `except ValueError` 自实现
- **接线**：`routes.generate()` 在写盘前调 `check_target(payload.get("target"))`；响应回填 `result["target"] = str(base)`；移除不再使用的 `from pathlib import Path`
- **错误码**：`error-codes.json` 新增 `targetInvalid` / `targetTooShallow` / `targetBlocked` / `targetReserved` / `tooManyNodes` —— **全部映射 400，无 500**（黑名单命中是"用户可修复"级，不是内部错误）

### 本次修复的缺陷

| 缺陷 | 处理 |
|---|---|
| `src/server/dtree_core.py:194` 写**生成的目录树文件**时裸用 `open("w")` → 默认 `newline=None` 把 `\n` 译为 `os.linesep`。**这不是洁癖而是真缺陷**：同一棵树在 Windows 产 CRLF、在 Linux 产 LF，**产出不可复现** | 改 `open(..., encoding="utf-8", newline="\n")` |
| `src/server/routes.py:112` 写 `data/editor.json` 同类问题 | 同上改法。该文件不入 git、不进版本清单，此改动**纯为消除平台漂移**，无用户可见影响 |
| `save_editor()` 返回的 `bytes` 取自**写入前的字符串长度**，而盘上文件在 Windows 下是 CRLF、比它长 → **响应里的 `bytes` 小于实际文件大小** | 随 `newline="\n"` 修复自动一致；`tests/test_routes.py` 专门断言 |

### 验证（均为实测）

| 项 | 结果 |
|---|---|
| `tools/verify.py` | 新增「**落盘安全边界 §P0-1**」守卫项（核 `config` 黑名单 / `dtree_core.check_target` / `routes` 接线 / 错误码四处齐备） |
| 沙盒探针（先行验证，非事后） | `C:\Windows\System32\evil` → `targetBlocked`；`Desktop` **子目录 → 放行**（验证 R4 的"仅根本身"语义）；项目**上级**目录 → `targetReserved`；盘根 → `targetTooShallow`；含 `..` 的路径 → 规范化后判定 |
| `python -m unittest discover -s tests` | 全过（`CheckTargetTests` 覆盖 R1–R5，`BuildTreeTests` 覆盖 R6–R8 + 生成内容 LF） |
| `tools/smoke.py` | **17 项全过**，含三项安全边界用例与「**超限未落盘**」断言 |

### src/ 代码

`src/server/config.py`（黑名单 + 辅助函数 + `MAX_NODES`）、`src/server/dtree_core.py`（`check_target()` + R6 前置 + `:194` 换行）、`src/server/routes.py`（接线 + `:112` 换行）、`src/shared/error-codes.json`（5 个错误码）。

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

### 同版本修订 r2（2026-10-09 21:39）· 换行规范化

**性质**：**不升版**（§P0-6 同版本追加修订）。语义零变化，仅统一换行符，属缺陷修复。

| 文件 | 变更 | 字节 |
|---|---|---|
| `VERSION` | CRLF → **LF** | 8 → 7 B |
| `start.bat` | LF → **CRLF** | 619 → 653 B（补 34 处 CR） |
| `src/web/assets/logo.svg` | CRLF → **LF** | 30,094 → 30,087 B（去 7 处 CR） |

**根因**：`Path.write_text` 默认 `newline=None` 会把 `\n` 译为 `os.linesep`（Windows 为 `\r\n`）。本项目以 SHA-256 指纹校验内容、`.gitattributes` 设 `* -text` 禁止换行转换，故字节漂移会直接造成指纹失配。`logo.svg` 的 CR 来自 V0.0.3 落盘时的生成脚本（沙盒，默认换行），属**同类根因**。

**工具修复**：`tools/release.py`（bump 写 `VERSION`）、`tools/promote.py`（落地写 `VERSION`）改用 `open(..., encoding="utf-8", newline="\n")`，照 `handoff.py` 既有范例（Python 下限 3.8，**不能**用 `write_text(newline=...)`）。

**新增验收**：`tools/verify.py` 增「换行一致性」项（校验 `src/**` 与 `VERSION` 不含 CR、`start.bat` 为纯 CRLF）。该校验上线时**立即抓出 `logo.svg` 缺陷**，非事后发现。

**验证**：`verify.py . --against V0.0.3` → **40 项全部通过**（对齐 r2 指纹）；`store.py commit` 27 文件 / 新增 3 blob / 复用 24；对象池 52 → **55** blob，`fsck` 0 损坏。

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
