# 版本记录 · 青蔓 QingMan

> **定位**：本文件是**版本制明细表**，只回答「某个版本改了什么」。
> **进度以时间线为准**，要判断当前做到哪一步，请看 `docs/任务进度.md`。

版本规则：**SemVer 三段式 `V<MAJOR>.<MINOR>.<PATCH>`，从 V0.0.1 起**（2026-10-09 采用）。递增语义：`patch` 修复 ／ `minor` 逻辑迭代 ／ `major` 不兼容变更。旧「V0.01 起、每次 +0.01」规则已作废。**不升版也要留回退点**：同版本内的改动追加为修订 `r2`、`r3`…（见 §P0-6）。提交前必须先 `store.py commit`。

---

## V0.0.27 — 2026-10-11

**主题**：`src/` 审查**批 1** 整改（《审查报告_src_20261011》§五 **第一档 + 第二档**）—— 4 项 P2 修复。本版起**真正改 `src/`**，故 **升 patch 版 `V0.0.26` → `V0.0.27`**。

| # | 文件 | 项 | 处置 |
|---|---|---|---|
| 1 | `src/server/routes.py` | **A-P2-1** | `load_editor` / `load_template` 捕获由 `except OSError` → **`except (OSError, UnicodeDecodeError)`**：非法 UTF-8 的 `editor.json` / 模板不再漏网裸崩，改为 `TreeError(editorReadFailed / templateReadFailed)` 优雅报错 |
| 2 | `src/server/app.py` | **A-P2-1（侧）** | `do_GET` 整体加 `except Exception` 兜底（**对齐 `do_POST`**）—— 任何漏网异常回落 500 JSON，不再裸崩请求线程 |
| 3 | `src/server/dtree_core.py` | **A-P2-4** | `_load_error_codes()` 同扩捕获（该函数在**模块顶层**执行）：`error-codes.json` 非法编码时回落空表，`import server` 不再崩 |
| 4 | `tools/verify.py` + `src/web/css/{tokens,base}.css` | **D-P2-1** | 「组件 CSS 无裸色值」判据由「**仅 `#hex`**」扩为「`#hex` ∪ `rgb()/rgba()/hsl()/hsla()`」，并**提为模块级函数 `raw_color_hits()`**（承担判定职责 → 可单测）；`base.css` 2 处裸 `rgba()` 改走**新增 token** `--qm-btn-hi` / `--qm-btn-lo`（**同值搬迁 → 零视觉变更**） |
| 5 | `src/web/js/ui/skin-picker.js` | **C-P2-1** | 抽出 `fill()` 并注册 `qmlocalechange`（**与 `lang-picker` 同构** + 补 `if (!selectEl) return`）→ 换语言后皮肤下拉文案刷新 |
| 6 | `src/web/js/i18n/{zh-CN,en-US}.js` + `src/shared/schema.json` | **升版例行动作** | `help.versionFallback` 与契约 `version` 同步至 `V0.0.27` |

**反向验证（全部真实运行，非推演）**：

| 项 | 手法 | 结果 |
|---|---|---|
| A-P2-1 | 副本注入（捕获退回 `except OSError`）→ 跑 `EditorRoundTripTests.test_bad_encoding_raises_not_crashes` | **FAILED (errors=1)** |
| A-P2-4 | 副本注入（同）→ 跑 `ErrorCodesTests.test_bad_encoding_returns_empty_not_raise` | **FAILED (errors=1)** |
| D-P2-1 | ① 副本注入裸 `rgba` → `verify`「组件 CSS 无裸色值」**FAIL**（基线 PASS）；**旧判据**对同一文件命中为空 → **漏网成因坐实**；② 判据退回 `#hex` → `RawColorHitsTests` **FAILED (failures=2)** | 双向实证 |
| C-P2-1 | 副本停用 `qmlocalechange` 注册 → 跑 `browser_smoke` | **恰该项 FAIL**（浏览器实测 `en='Moonlight Prologue · Pen Gray' → zh=同值`），**页面断言 10 → 11 项** |

**新增测试（+10，`unittest` 222 → 232 OK）**：`test_routes.py` **+1**（A-P2-1）· `test_dtree_core.py` **+4**（A-P2-4：非法编码 / 缺文件 / 坏 JSON / 正常解析）· `test_verify.py` **+4**（`raw_color_hits`：`#hex` / `rgb`·`rgba` / `hsl` / 不误伤 `var()`）· `test_browser_smoke.py` **+1**（C-P2-1 回归位；`verify_metrics` 判定数 7 → 8）。

| 项 | 结果 |
|---|---|
| `verify.py .` | **82/0** |
| `verify.py . --against V0.0.27` | **84/0**（指纹一致） |
| `unittest` | **Ran 232 tests · OK** |
| `smoke.py` | **17/0** |
| `browser_smoke.py` | **11/0** |

**性质**：改 `src/` + 交付契约 → **升 patch 版 `V0.0.26` → `V0.0.27`**；含 store 快照（`V0.0.27@r1` → 同步版本戳后 `@r2`）与 git tag。

> **教训（同《错误笔记》§三.41）**：升版顺序须为 **bump → 同步版本兜底值 / 契约版本戳 → store commit**。本次先 `commit` 后同步，令 `V0.0.27@r1` 装的是**旧版本戳**，须补 `@r2` 修正。

---

## `src/` 前后端逐行审查（不升版 · 只读）— 2026-10-11

**主题**：产出《`docs/审查报告_src_20261011.md`》—— 对 `src/`（**6655 行**）的**首次逐行审查**，分 **A 后端 / B 前端核心 / C 前端 UI+i18n / D CSS+HTML** 四批。**全程只读，未改动任何源码。**

**结论**：**P0 = 0 · P1 = 0 · P2 = 7 · P3 = 19**（另附正面清单）。

**P2 摘要**：
- **A-P2-1** `load_editor` / `load_template` **漏捕 `UnicodeDecodeError`** → `do_GET` 无兜底**裸崩**（**临时目录实证**：GBK `editor.json` → `UnicodeDecodeError`）。同项目 `list_templates`/`rename_template`/`verify.py` 均已捕，唯此两处漏 → **内部不一致**。
- **A-P2-2** `validate_segment` **未拒尾随空格 / 尾随点** → `build_tree` 用原始名落盘，**记录名 ≠ 磁盘名**（**实证**：记录 `…\a b ` / `…\c.`，磁盘 `a b` / `c`）。
- **A-P2-3** `validate_ico` docstring 承诺「宽高值域校验」**但代码未实现**（名实不符，同 P2-14 族）。
- **A-P2-4** `_load_error_codes()` 模块级执行 + 漏捕编码错误 → `error-codes.json` 非法编码时**服务起不来**。
- **B-P2-1** 前端新建 / 重命名**不校验名字合法性** → UI 先「成功」、自动保存时才被后端拒（前后端校验不对称）。
- **C-P2-1** `skin-picker` **未监听 `qmlocalechange`** → 换语言后皮肤下拉**不刷新**（`lang-picker` 有，两者不一致）。
- **D-P2-1** 「组件 CSS 无裸色值」守卫**判据只匹配 `#hex`**（`verify.py` L556）→ `base.css` 2 处裸 `rgba()` **逃逸**（**守卫盲区**，同「换行守卫盲区」族）。

**正面清单（节选）**：R1–R5 实现与《项目约定》**逐条一致**；`build_tree` **唯一生产调用点**已 `check_target`；路径穿越双检；`os.replace` 原子写贯穿；软删除贯穿；前端**无 `innerHTML`**；i18n 双键 **298 = 298 零差异**；CSS 变量闭包 28 项齐备。

**性质**：只读审查 + 文档 → **不升版**（`VERSION` 仍 `V0.0.26`）。**整改未开始**，报告 §五 给出四档顺序供裁决。

---

## 工具链 P2 收口补记 · `verify.py` L1027 无守卫读取（不升版）— 2026-10-11

**主题**：收口下一节末尾「一处附带发现」——`tools/verify.py:1027` 的**无守卫 `read_text()`**（读 `src/web/js/i18n/zh-CN.js`；同段 L1010 / L1018 / L1024 均有 `is_file()` 守卫）。

**为何必须修**：该行所在的「帮助支持拆两页 V0.0.18」检查，**排在「体积上限 §P2 第 4 项」之前** → 缺 `src/` 时**先崩在此行**，使组 2 刚做的 **P2-14「缺 `src/` 显式 FAIL」修复根本执行不到**（被崩溃遮蔽）。

**侦察（穷尽）**：`verify.py` 全文 **19** 个 `.read_text()` 调用点逐一判定 —— **18 处受保护**（`glob`/`rglob` 循环 11 处 · `try/except (OSError, ValueError)` 3 处 · 前置 `is_file()` 4 处：L462 / L506-508 / L917 / L1495），**仅 L1027 一处无守卫**（**非系统性缺陷**）。

**处置**：补 `is_file()` 守卫，与同段三处同款式（缺文件取空串）：

```python
zc18 = root / "src/web/js/i18n/zh-CN.js"
z18 = zc18.read_text(encoding="utf-8") if zc18.is_file() else ""
if re.search(r"kind:\s*'support'", z18):
    split_bad.append("zh-CN.js 仍注册 support 渲染分支")
```

**反向验证（最小根 = `tools/` + `tests/` + `VERSION` + `start.bat`，无 `src/`；修复前后对照）**：

| 观测量 | 修复前 | 修复后 |
|---|---|---|
| `Traceback` | 有（L1027 `FileNotFoundError`） | **0 次** |
| 「帮助支持拆两页」行 | **不出现**（崩溃抢先） | **`[FAIL]` 优雅报缺 12 项键** |
| 「体积上限」行 | **不出现** | **`[FAIL] 未找到 …\src 下任何文件（src/ 缺失？）`** —— P2-14 修复**解蔽、可达** |
| 「结论」行 | **不出现** | `共 78 项 · 失败 62 项 → 不通过` |

**验证**：四件套 verify **82/0**（`--against V0.0.26` **84/0**）· unittest **222 OK** · smoke **17/0** · browser_smoke **10/0**。

**性质**：纯 `tools/` → **不升版**（`VERSION` 仍 `V0.0.26`）、无 store 修订，回退点＝ git commit。

---

## 工具链 P2 整改（组 1~4 · 不升版）— 2026-10-11

**主题**：《审查报告_工具链_20261010》**§四 P2 台账**的逐条裁决与整改 —— 即「第 2 步（工具链整改）」的**收口**。前五子步（2.1~2.5）处理了 **P1** 与三处低成本 P2；本节把**余下 16 项 P2**（`P2-1/2/6` 已于 2.5 修）一次处置完。

**裁决前置（逐条对照盘上源码复核）**：19 项中 **P2-3 现象被证伪** —— 报告称「`--against V0.0.1@rX` 静默回退到最新修订」，实测为 **FAIL「无法判定」**（**安全方向**，未回退），仅残留「文案不精确」，故采纳**文案订正**而非「补默认值」。其余 15 项现象均在，逐项处置。

**分 4 组，每组独立走完「改 → 反向验证 → 四件套 → 提交」闭环**（提交 `7d574d0` / `87fe44d` / `9fbb059` / `d7b7772`，各附一次 handoff 刷新提交）。

| 组 | 文件 | 项 | 处置 |
|---|---|---|---|
| **1** | `tools/store.py` | **P2-4 / 5 / 8 / 9** | ① `do_commit` 内层文件级 `digest` 改名 **`blob_digest`**（区别外层清单级 `digest`）；② `do_checkout` 回收目录名加序号（`<stamp>` 冲突则 `<stamp>_02`…）**防同秒撞**；③ `commit --from` 加 `is_within` 复核（`--root` **之内**子目录 → 硬拦；**之外** → 警告，保留「同构树快照」历史正当用法）；④ 抽出**指纹比对单点** `fingerprint_diff(root, recorded)`，供 `handoff` / `verify` 复用 |
| **2** | `tools/verify.py` | **P2-3 / 14 / 15 / 16 / 17 / 18** | ① 非法修订引用（`@rX` 非 ≥1 整数）**显式报错**（原静默 `rev=None`）；② 缺 `src/` 时**体积上限项显式 FAIL**（原包在 `if src_files:` 内→少一项）；③ 默认皮肤号改 **`DEFAULT_SKIN_CID` 反查**（原硬编码 `cids[5]` 索引猜）；④ **多余位置参数报错**（原静默忽略）；⑤ 回归测试网**加轻量内容判据**（测试文件内须含 `def test_`，空壳计入不全）；⑥ 锚点 `"\\u4e00"` → **`"CJK"`**（原依赖三层转义，极脆） |
| **3** | `tools/browser_smoke.py` | **P2-10 / 11 / 12 / 13** | ① 新增 `sandbox_base()`（`QM_SANDBOX` 优先，否则 `项目根/../../_sandbox`）**去硬编码盘符**；② 新增前置探测 `browser_drivable()` —— `--browser` 指向**不可驱动/非 Chromium**（如夸克）时**「跳过 + 明确原因」退出 0**（原误判为「页面有缺陷」）；③ `parse_metrics` **去掉宽松兜底正则**（原会捞到探针源码字面量）；④ 探针页加**正面控制** `console.log('[qm-smoke] probe-boot')` + 新增「**控制台日志通道可用**」断言（原通道失效则「无致命」**静默通过**）。**页面断言 9 → 10 项** |
| **4** | `tools/smoke.py` + `promote.py` + `handoff.py` | **P2-10 侧 / 7 / 19** | ① `smoke.py` 同构补 `sandbox_base()`；② `promote.py` 的 `list_files` 判据由 `COPY_FILES` 改 **`PRESENCE_FILES`（含 `VERSION`）** —— `VERSION` 单存也算「主线非空」（`COPY_FILES` 仍只管复制）；③ `handoff.py` 实况段 git 状态行**细分「已修改 M / 未跟踪 K」**（原把任何未跟踪文件笼统算作「未提交改动」） |

### 新增测试（+24 项，`unittest` 198 → 222 OK）

| 文件 | 增量 | 覆盖 |
|---|---|---|
| `tests/test_store.py` | **+7** | `fingerprint_diff`（改/增/缺）/ `is_within` / `commit --from`（root 内拒 / root 外警，子进程实跑）/ `checkout` 回收目录**同秒不撞** |
| `tests/test_verify.py` | **+2** | 多余位置参数被拒 / 单参数不误判 |
| `tests/test_browser_smoke.py` | **+4**（26 → 30） | `parse_metrics` **无兜底**（`test_no_container_returns_none`）/ `sandbox_base`（2）/ `browser_drivable`（1）/ 探针**自报行**在场（1） |
| `tests/test_promote.py` | **新增 6** | `list_files`（核心：**`VERSION` 单存即算非空**）/ 默认源推导 |
| `tests/test_smoke.py` | **新增 3** | `sandbox_base`（含与 `browser_smoke` **一致**的锁定用例） |
| `tests/test_handoff.py` | **+2** | 干净树报「工作区干净」/ 脏树**拆分「已修改 / 未跟踪」** |

**关键修正（测试用例自身缺陷，反向验证抓到）**：`test_store.py` 的 P2-5 用例初版用**不同名**文件（`extra_a.py` / `extra_b.py`）—— 即便回收目录撞车也**不互相覆盖**，抓不到缺陷。改为**同一路径 `src/extra.py` 两次不同内容**（首次回收后用户又建同名文件），断言两份回收副本内容分别为 `"A\n"` / `"B\n"`。反向验证确认：注入缺陷后**该用例精确 FAIL**，基线 PASS。

**一处附带发现（未擅自扩大范围）**：反向验证 P2-14 时，在「只含 `tools/`+`tests/`+`VERSION`+`start.bat`」的**最小根**上，`verify.py` **L1027 无守卫 `read_text()`**（读 `src/web/js/i18n/zh-CN.js`，同段 L1018 / L1024 均有 `is_file()` 守卫）→ 缺 `src/` 时**直接 Traceback**，到不了「体积上限」项。故报告 P2-14 的前提「少一项而非 FAIL」**不精确**（实为**先崩溃**）；本轮仍按「缺 `src/` 显式 FAIL」处置该组改动，崩溃点**如实记录、未顺手修**（避免超出本轮裁定范围），留待后续。

### 验证

| 门禁 | 结果 |
|---|---|
| 反向验证（逐组注入缺陷） | 组 1 → `test_same_second_checkouts_keep_both_trash_copies` / `test_from_inside_root_is_rejected` **精确 FAIL**；组 2 → P2-14/17/18 三项**精确 FAIL**（全量副本注入）；组 3 → `test_no_container_returns_none` / `test_probe_emits_self_report_line` **精确 FAIL**；组 4 → P2-7/10/19 对应**精确 FAIL**。**P2-3 / P2-16 为现场实测通过**；**P2-11 以夸克实测** → 「跳过 + 明确原因」退出 **0** |
| 四件套（终态） | verify **82/0**（`--against V0.0.26` **84/0**）· unittest **222 OK** · smoke **17/0** · browser_smoke **10/0** |

> **性质**：只改 `tools/` + `tests/`（+ 文档），**不升版**（`VERSION` 仍 `V0.0.26`）。
> `tools/` 不在 store 清单范围（清单只覆盖 `src/** + start.bat + VERSION`）→ **无 store 修订**，回退点＝ **git commit**。

---

## V0.0.26 — 2026-10-10

**主题**：编辑态**轮转备份** —— `save_editor` 落盘前把**上一版**轮转进 `data/.bak/`，保留最近 5 份。源自《审查报告_工具链_20261010》§七 第 6 条（「第 3 步」）。

**动机**：`save_editor` 是「写 `.tmp` → `os.replace` 原子替换」，**替换即覆盖上一版**；`load_editor` 只在**文件损坏**时保护，**挡不住「合法但错误」的覆盖** —— 用户一次误操作 + 一次自动保存（防抖 800ms），上一版即永久消失。这是编辑态唯一的**不可逆**路径。

### 变更

| # | 位置 | 内容 |
|---|---|---|
| 1 | `src/server/config.py` | 新增 `EDITOR_BACKUP_DIR`（`data/.bak`）/ `EDITOR_BACKUP_KEEP`（可用 `QM_EDITOR_BACKUP_KEEP` 覆盖，默认 **5**）/ `EDITOR_BACKUP_TRASH_DIRNAME`（`.trash`） |
| 2 | `src/server/routes.py` | 新增 `_backup_editor()` / `_prune_editor_backups()`；`save_editor` 在**体积检查之后、原子替换之前**调用 —— 顺序不可颠倒（颠倒则备份到的是新内容）。响应新增 `backup: {ok, file, pruned[, reason]}` |
| 3 | `src/shared/schema.json` | `version` → `V0.0.26`（守卫 9a 要求 == `VERSION`）；`editorResponse` 补 `backup` 字段；`editorDocument` 注明轮转位置 |
| 4 | `src/web/js/i18n/{zh-CN,en-US}.js` | `help.versionFallback` → `V0.0.26`（守卫 7h 要求 == `VERSION`） |
| 5 | `tools/verify.py` | 「编辑态接口与错误码」锚点补 `EDITOR_BACKUP_KEEP` / `_backup_editor`（守卫计数不变，仍 **82**） |

### 设计取舍

1. **备份放 `data/` 而非 `store/`**：`store/` 是**可交付版本**的对象池（只覆盖 `src/** + start.bat + VERSION`），编辑态是**用户内容**，两者不同域。
2. **软删除，不真删**：超限旧备份**移入 `data/.bak/.trash/<时间戳>/`**，而非 `unlink`。原因有二 —— ① 项目总原则「只复制不删除」是**全项目硬不变量**，`verify.py` 7q 守卫**明令禁止 `routes.py` 出现 `unlink`/`remove`**；② 与 `templates/.trash/` 同一体例，误清可人工找回。
3. **失败不阻断保存**：备份是**增强**，主契约是「存得下」；备份失败（磁盘不可写等）时保存照常成功，仅在响应 `backup.ok=false` + `reason` 回报，**不静默**。
4. **文件名带微秒**（`editor-YYYYMMDD-HHMMSS-%f.json`）：裁剪依托「名字序 = 时间序」，**秒级不够** —— 见下「踩坑」。

### 踩坑（本轮实测抓到，已修）

**「按名字序裁剪」在秒级时间戳下会删掉最新那份**：同秒内多份备份靠 `_NNN` 后缀区分，而一旦某份被裁掉、**其名字被后一次保存重新占用**，新文件就排到了后缀文件的**前面**，于是「保留最近 N 份」把**刚写的那份**当成最旧淘汰（实测：第 6 次保存后，`.bak/` 里最新的是**第 4 版**）。
**修法**：时间戳带**微秒**（`%f`）→ 名字**全局单调**，不再复用。同微秒兜底后缀用 `_NNN`（`_`(0x5F) > `.`(0x2E)，与创建序一致），**不可**用 `-NNN`（`-`(0x2D) < `.`，方向相反）。已固化为回归用例 `test_prune_never_drops_the_newest`。

### 验证

| 项 | 结果 |
|---|---|
| 单元测试 | 新增 `tests/test_routes.py::EditorBackupTests`（**13 项**：首次无备份 / 备份=**上一版**逐字节 / 被拒保存不留备份 / 上限裁最旧 / 软删除进 `.trash` / 名字序=时间序 / 同微秒不覆盖 / **裁剪不丢最新** / 失败不阻断 / 保持 LF / 报告迁移数）→ `unittest` 185 → **198 OK** |
| 反向验证 | 临时副本把时间戳改回**秒级** → `test_prune_never_drops_the_newest` **精确 FAIL**（`'editor-20261010-233000.json' not found in ['…_002','…_003']`）；主线同用例 **OK** |
| 四件套 | verify **82/0** · unittest **198 OK** · smoke **17/0** · browser_smoke **9/9**（版本徽标 `V0.0.26`） |
| 守卫 | `verify` 7q「routes.py 不得真删」**通过**（淘汰走 `shutil.move`，非 `unlink`）；9a 契约版本戳、7h 版本兜底一致均通过 |

**性质**：改 `src/` + 交付契约 → **升 patch 版 `V0.0.25` → `V0.0.26`**；含 store 快照与 git tag。

---

## 工具链整改（不升版）— 2026-10-10

**主题**：`tools/` 工具链逐行审查（《审查报告_工具链_20261010》）后的 **第 2 步**，逐子步推进：

- **2.1** 修掉「**守卫自身的盲区**」：`verify` 的「换行一致性」只扫 `src/`，而全项目唯一含 CR 的目录
  恰是 `versions/`（**29 份 MANIFEST 全部 CRLF**）。
- **2.2** 修掉「**工具间体例不一致**」：`smoke.py` 复用沙盒不清自身产物 → 第二次必报假失败。
- **2.3** 修掉「**自洽检查证不了内容正确**」：实况段「版本 tag」只列修订 tag、「时间线最新」日期恒为
  `(未标日期)`；并补两条内容断言（verify 80 → **82**）。
- **2.4** 补「**守卫的守卫**」：`browser_smoke.py` / `handoff.py` 的判定逻辑此前零单测 →
  新增 `tests/test_browser_smoke.py`（26 项）、`tests/test_handoff.py`（18 项），unittest 130 → **174 OK**。
- **2.5** 收尾三处顺手项：`verify` 无 node 时文案与行为不一致（说「跳过」实为「失败」）、
  `find_node` 硬编码 node 版本路径、`release.py` 回退点提示晚于改写 —— 并补 `tests/test_verify.py`。

> **性质**：只改 `tools/`（+ 归一 `versions/` 清单字节），**不升版**（`VERSION` 仍 `V0.0.25`）。
> `store.py` 的版本清单只覆盖 `src/** + VERSION + start.bat`，**不含 `tools/`** → 本轮**无 store 修订**，
> 回退点为 **git commit**。

### 修复

- **P1-1 根因**：`tools/store.py` 的 MANIFEST 写盘点补 `newline="\n"`（此前是全项目**唯一**漏写处，
  Windows 下落盘为 CRLF）。隔离实证：`do_commit` → MANIFEST **0 CR**（修复前 **15**）。
- **P1-1 守卫**：`tools/verify.py`「换行一致性」扫描范围由 `src/ + VERSION + start.bat` 扩为
  **纳入版本控制的文本文件全集**（含 `versions/**/MANIFEST*.json`）；排除 `data/`（运行时数据）、
  `store/`（对象库）、`.git/`、`__pycache__/`、`.trash/`；`start.bat` 仍单列要求纯 CRLF。
- **历史归一**：`versions/**/MANIFEST*.json` **29 份** CRLF → LF，逐份断言 `json.loads` **语义不变**。

### 验证

| 门禁 | 结果 |
|---|---|
| 反向验证（扩范围后 · 归一前） | 「换行一致性」**FAIL**，精确点名 **29 份**清单（此前完全漏检） |
| `verify.py` | **80 项 / 失败 0** |
| `unittest` | **130 OK** |
| `smoke.py` | **17 项 / 失败 0** |
| `browser_smoke.py` | **9 / 9** |
| 隔离实证 | `store.do_commit` → MANIFEST **0 CR** |

### 2.2 —— 工具间一致性（P1-2：复用型工具须清自身产物）

**问题**：`tools/smoke.py` 的 `--keep` / `--sandbox` 语义是「复用沙盒」，但运行前**不清**上次产物
→ 复用同一沙盒时第 7 项 `dryRun` 断言 `not target.exists()` 恒为 False，**第二次起必报假失败**
（实测 `17/0` → `16/1`）。而 `browser_smoke.py` **早已修了同类问题**（复用前清自身产物）——
两件工具体例不一致，这正是缺陷能长期潜伏的原因。

**处置**

- `tools/smoke.py`：在选定沙盒后、起服务前，按已知名清单 `("生成结果", "big")` 清残留
  （对齐 `browser_smoke.py` 写法；**只清已知名，不动沙盒内其它内容**）。
- `docs/项目约定.md`：§P1-4 新增「**复用型沙盒工具**（工具间一致性）」行；§P2 台账新增第 **17** 项。

**验证**

| 门禁 | 结果 |
|---|---|
| 反向验证（修复前） | 同一沙盒连跑 → 第 2 次 **FAIL**（`dryRun → 200 created=True`），`16/1` |
| 修复后 | 同一沙盒连跑 **3 次** → 均 **17/0**（第 2 次起打印「复用沙盒，清理上次产物」） |
| 边界实验 | 预置 `生成结果/` `big/` `keepme.txt` → `生成结果/` 重建、`big/` 已清且未重建、`keepme.txt` **幸存** |
| `verify.py` / `unittest` / `smoke.py` / `browser_smoke.py` | **80/0** · **130 OK** · **17/0** · **9/9** |

### 2.3 —— 实况段渲染失真（P1-3：自洽检查证不了内容正确）

**问题**：`verify` 第 8 项只做「实况段与盘上一致」的**自洽比对**，而实况段**由同一函数渲染** ——
故它只能证「不过期」，**证不了「内容正确」**。两处失真因此长期隐身：

- **P1-3a**：`handoff.py` 只执行 `git tag -l "V*-r*"` → 实况段**只列修订 tag**（`V0.0.1-r2` /
  `V0.0.1-r3`），**24 个版本 tag 全部缺席**；接手方会误判「最新 tag 停在 `V0.0.1-r3`」。
- **P1-3b**：日期正则 `^###\s+(\d{4}-\d{2}-\d{2})\s*$` 不容忍 `### 2026-10-10（续十五）` 的括号后缀
  → 「时间线最新」日期**恒为 `(未标日期)`**。

**处置**

- `tools/handoff.py`：新增 `split_tags()`，渲染改为**版本 tag 与修订 tag 分列**（版本 tag 列「最近 5 个
  + 总数」，按语义版本升序）；日期正则放宽为 `^###\s+(\d{4}-\d{2}-\d{2})`。
- `tools/verify.py`：新增 **8c** 两条内容断言（80 → **82**）——「版本 tag 行必须列出真实版本 tag」
  「时间线最新必须解析出日期」。
- `docs/项目约定.md`：§P1-6 新增 **H7**；§P2 台账新增第 **18** 项。

> **一处专业收窄**：报告原建议断言「tag 行**必含当前 `VERSION`**」—— 实测不可取：发布流为
> `bump → store commit → handoff → git commit+tag`，`bump` 后、`git tag` 前该 tag **尚不存在**，
> 硬断言会在**合法中间态**产生假红。故实现为「`VERSION` 已打 tag 时必须出现；否则至少需有一个
> 形态合法的版本 tag」。

**验证**

| 门禁 | 结果 |
|---|---|
| 反向验证·对照组（整项目副本，未注入） | 版本 tag 行 **PASS**（`24 个版本 tag，最新 V0.0.25`）· 时间线日期 **PASS**（`2026-10-10 · 22:16 …`） |
| 反向验证·注入旧行为 | 两项**精确 FAIL**：`版本 tag 行漏列当前 V0.0.25` / `日期未解析：(未标日期)` |
| `verify.py` / `unittest` / `smoke.py` / `browser_smoke.py` | **82/0** · **130 OK** · **17/0** · **9/9** |

### 2.4 —— 守卫的守卫缺位（P1-4：判定逻辑补单测）

**问题**：`tools/` 共 8 个脚本，此前**只有 `store` / `versioning` 有单测**。`browser_smoke.py` 的 5 个纯函数
（`find_browser` / `parse_metrics` / `console_lines` / `as_int` / `verify_metrics`）是 **9 项页面断言的
全部判定逻辑**，`handoff.py` 的渲染函数是**接续卡内容的唯一来源**，却都**零测试** —— 而 `verify` 对它们
只做**静态 token 锚定**（防被削成空壳），**不验证判定逻辑本身是否正确**：`verify_metrics` 的阈值
（`sec_before == sec_en == sec_zh` / `cjk == 0` / `chip == VERSION`）一旦被写坏，静态锚定拦不住。

**处置**

- 新增 `tests/test_browser_smoke.py`（**26 项**）：`as_int` 边界 / `parse_metrics` 容器锚定与
  「探针源码字面量不得被当成结果行」/ `console_lines` 的 origin 与扩展噪声过滤 / `find_browser` 优先级 /
  `verify_metrics` 全 PASS 与**回归位**（喂 P1-1 指标 `7→14→21` → **恰好**「分节渲染幂等」FAIL；
  喂 P1-2 指标 `cjk=6` → **恰好**「默认示例随语言」FAIL）。
- 新增 `tests/test_handoff.py`（**18 项**）：`_version_key` / `split_tags`（**语义版本排序，非字典序**：
  `V0.0.10` 必须排在 `V0.0.2` 之后）/ `timeline_latest`（**带 `（续十六）` 后缀的标题必须解析出日期**）/
  `replace_block`（只改标记之间、缺标记报错）/ `render_live`（版本 tag 行含当前 `VERSION`、修订 tag 行
  与之分离、时间线日期真实、渲染纯函数）。
- `tools/verify.py`：「回归测试网 §P0-2」必需清单补两个新测试文件。

**验证**

| 门禁 | 结果 |
|---|---|
| 新增两模块单跑 | `test_browser_smoke` **26 OK** · `test_handoff` **18 OK** |
| `unittest` 全量 | 130 → **174 OK** |
| `verify.py` / `smoke.py` / `browser_smoke.py` | **82/0** · **17/0** · **9/9** |

### 2.5 —— 工具链收尾三处顺手项（P2-1 / P2-2 / P2-6）

| # | 项 | 处置 |
|---|---|---|
| **P2-1** | `verify.py` 无 node 时**文案与行为不一致**：文案说「跳过」，行为却是 `check(False, ...)` | **裁定：不做「真跳过」，只把文案改准** —— JS 语法是交付门禁的一项，静默少一项会让「覆盖变薄」看起来和「全过」一样（同《错误笔记》§三.33 的教训）。改为「未找到 node —— JS 语法检查无法执行（本条为必需项）」 |
| **P2-2** | `find_node()` 硬编码 `versions/22.22.2-6/node.exe` —— 托管运行时一升级即失效 | 改为扫描托管目录下**全部版本**取最新：新增 `node_version_key()` 与 `iter_managed_nodes()`（**按数字比较**，非字典序；跳过无 `node.exe` 的目录，如 `current` / `.locks`） |
| **P2-6** | `release.py` 的「请先 `store.py commit` 留好回退点」打印在**改写 `VERSION` 之后**（为时已晚） | 提示移到写盘**之前** |

**验证**（均为真实运行）

| 项 | 实证 |
|---|---|
| P2-1 | 子进程以 `PATH=""` + `HOME=<空目录>` 运行 `verify` → `[FAIL] JS 语法  未找到 node —— JS 语法检查无法执行（本条为必需项）`，全文**不含**「跳过」 |
| P2-2 | 伪造 HOME、托管目录只放 `24.21.0/node.exe` → `find_node()` 返回**该路径**；旧硬编码路径**不存在**（旧实现必然返回死路径） |
| P2-6 | 临时副本实跑 `release.py bump` → 输出顺序为「`[提示] …留好回退点…`」→「`[升级] V0.0.1 → V0.0.2`」 |
| 新增测试 | `tests/test_verify.py`（**8 项**：版本键 / 取最新 / 跳过无 `node.exe` 目录 / 空目录降级 / 返回路径必须真实存在）+ `tests/test_versioning.py` **+3**（`do_bump` 写 LF、**提示早于升级**、失败不动文件） |

| 门禁 | 结果 |
|---|---|
| `unittest` | 174 → **185 OK** |
| `verify.py` / `smoke.py` / `browser_smoke.py` | **82/0** · **17/0** · **9/9** |

---

## V0.0.25 — 2026-10-10

**主题**：全项目架构与逻辑审查的**最后一步** —— 把「**只有页面跑起来才现形**」的一类缺陷
固化为常态守卫：新增 `tools/browser_smoke.py`（无头浏览器页面级冒烟），`verify` 79 → **80** 项，
`§P0-2` 立 **T7** 并把 T5 由三件套扩为**四件套**。

> **立项依据**：用户「采纳建议，分步，依次执行」（第 4 步）。
> **用户环境**：Windows 11 本机，仅**鼠标 + 键盘**；触屏与其他 OS **无法验证** —— 同类改动不做。
> **为什么需要它**：P1-1 / P1-2 两处缺陷（V0.0.22 修复）在当时 **verify 74/0 · unittest 120 OK ·
> smoke 17/0 三项全绿**的情况下依然漏网 —— 静态守卫与 HTTP 层冒烟都覆盖不到「页面渲染与交互」。

### 新增（工具链）

- **`tools/browser_smoke.py`**（约 460 行，纯标准库 + 系统浏览器）—— **9 项**页面级冒烟：
  1. 探针完成（浏览器确实跑到最后一步并写出结果行）
  2. 页面载入**无未捕获异常 / 无漏翻 / 无请求失败**
  3. 主界面·**默认示例随语言**（英文偏好下节点名必须为英文）— P1-2 回归位
  4. 主界面·皮肤样式表已装载
  5. 主界面·模板库已接入
  6. 帮助页·**分节渲染幂等**（切语言后分节/导航计数不得累积）— P1-1 回归位
  7. 帮助页·语言切换联动 `<html lang>`
  8. 帮助页·版本徽标 == `VERSION` 且后端可达（`help-stale` 已摘除）
  9. 支持页·V0.0.18 拆页后仍完好

**实现要点**（都是踩过的坑，写进代码注释）：

- **必须复制 `src/` 到沙盒再起服务** —— `config.DATA_DIR` 恒为 `<项目根>/data`，
  直接跑真实 `src/` 会让首屏默认示例经 `saveNow()` 写进**真实** `data/editor.json`
- **同源 iframe 驱动真实页面** —— 测的就是线上那份骨架；驱动语言切换走**真实用户路径**
  （`#helpLangSelect` 派发 `change` → `setLocale` → `qmlocalechange` → `renderSections`）
- **全程事件驱动**（iframe `onload` + `setTimeout` 轮询），不用 Promise 链 ——
  无头浏览器的 `--virtual-time-budget` **不等待未决 Promise**
- **控制台抓手的取得方式**：`--enable-logging=stderr` 会把 `Uncaught Error: …` 与
  `console.warn` 文案写入 stderr（实测确认，含 **iframe 内**的脚本错误）
- **日志必须按 origin 过滤** —— 实测本机 Edge 的 `ProtocolLaunch` 扩展每次都会打一条
  `chrome-extension://…` 日志；只认 `<origin>/…` 来源，「无未捕获异常」才不会被污染
- **结果行解析锚定到探针输出容器** —— 探针源码里也有 `'RESULT '` 字面量，宽松匹配会连源码一起捞进来
- **复用沙盒时先清本脚本自己的产物**（`src` / `templates` / `VERSION` / `data` / `browser-profile`）；
  其中 `data/` 非清不可 —— 残留的 `editor.json` 会被 `restoreDocument()` 复原，
  「默认示例随语言」就会**假通过**
- **未检测到浏览器时优雅跳过并退出 0**（`--browser` 可指定路径），不误报

### 守卫与文档

- **`tools/verify.py`**：79 → **80** 项 ——
  - 新增「**浏览器冒烟覆盖 V0.0.25**」：静态锚定该脚本的 10 个关键断言 token
    （控制台日志开关 / `Uncaught` / `[i18n] missing key` / `.help-section` / `qm.lang` /
    切换驱动 / `.tree-name` / `\u4e00` / `copytree` 沙盒隔离 / 探针页），防止守卫被削成空壳
  - 「回归测试网 §P0-2」必需清单补 `tools/browser_smoke.py`
- **`docs/项目约定.md`**：`§P0-2` 新增 **T7**（页面级冒烟）条款；**T5 由三件套扩为四件套**
  （`verify` → `unittest` → `smoke` → `browser_smoke`）

### 验证

| 项 | 结果 |
|---|---|
| `verify.py` | **80 项 0 失败**（+1） |
| `unittest` | **130 OK**（本轮无新增测试） |
| `smoke.py` | **17 项 0 失败** |
| `browser_smoke.py`（主基线） | **9 项 0 失败** —— 节点 6 行 / 含中文名 0 / 模板 17 / 分节 `7 → 7 → 7` / 徽标 `V0.0.25` |
| **反向验证**（注入已知缺陷，确认能被抓到） | ① P1-1 → `[FAIL] 帮助页·分节渲染幂等 分节 7 → 14 → 21`；② P1-2 → `[FAIL] 含中文名 6 个`；③ 支持页模块抛错 → `[FAIL] Uncaught Error: NEG_PROBE_THROW` + `[FAIL] 支持页 .help-qr=0` |

**隔离纪律**：全部实证在 `D:\Data\WorkBuddy\_sandbox\` 副本内进行，**测后即删**；
核验 `data/editor.json` mtime 未变、真实模板仍 17 套。

---

## V0.0.24 — 2026-10-10

**主题**：全项目架构与逻辑审查的 **P3 收口** —— 6 项整洁与健壮性修正（`verify` 78 → **79** 项，`unittest` 127 → **130** OK）。

> **立项依据**：用户「采纳建议，分步，依次执行」（第 3 步）。来源见 `docs/审查报告_架构与逻辑_20261010.md` §P3-8 ~ §P3-13。
> **用户环境**：Windows 11 本机，仅**鼠标 + 键盘**；触屏与其他 OS **无法验证** —— 同类改动不做。

### 变更（`src/`）

- **P3-8 属性面板变量声明顺序**（`web/js/ui/inspector.js`）
  - `let currentId` 由 `input` 监听器**之后**上移到**之前**。运行期本无 TDZ 风险（监听器只在其后触发），
    但顺序反直觉、重构易踩坑
- **P3-9 启动图标去重改为持久化**（`web/js/ui/launch-icon.js` + `i18n/index.js`）
  - 原「上次上传指纹」为模块级变量，**页面重载即归零** → 每次打开主界面必 POST 一次 `/api/launch-icon` 并写盘
  - 改为经 `readPref`/`writePref` 持久化到 `localStorage['qm.launchIcon']`；i18n 运行时新增 `ICON_KEY`
    并**导出** `readPref` / `writePref`（持久化单一访问点，其他模块不再直访 `window.localStorage`）
- **P3-10 `canMove` 新增 `missing` 返回值**（`modules/tree-model.js` + `main.js` + 双语）
  - 节点不存在原返回语义混淆的 `'root'`（会提示成「根节点不可移动」，误导）；改为 `'missing'`，
    `onMove` 映射表补 `toast.moveMissing`（中英对齐）
- **P3-11 模板失败回滚**（`server/routes.py`）
  - `save_template`：体积检查**前移到同名覆盖之前**（原超限时旧模板已入回收站 → 原位凭空消失，半完成态）；
    写新文件失败时**把旧件从回收站移回原位**
  - `rename_template`：旧件入回收站失败时**把新文件也移入回收站**，避免新旧并存
  - 两者均只用 `os.replace`、不真删（延续「只复制不删除」）
- **P3-12 代码整洁**（`web/js/main.js`）
  - 合并对 `./ui/inspector.js` 的两条 import（`createInspector` + `copyText`）；
    清 `applyTemplate` 行首多余空格（报告写 787 行，实测盘上 **792** 行 —— V0.0.22 上移 `initPrefs` 致行号位移）
- **P3-13 `build_tree` 类型冲突对称**（`server/dtree_core.py` + 契约）
  - 树要建**文件**、磁盘同名是**目录**时，原**静默计入 `existed`**（用户误以为已生成）；改为与反向情形
    对称，报错 `pathConflictDir`（新增错误码，`error-codes.json` / 中 / 英三处齐备）

### 守卫与测试

- **`tools/verify.py`**：78 → **79** 项 —— 新增「**P3 整洁与健壮性 V0.0.24**」，逐条钉住：
  `currentId` 声明顺序 / 图标指纹持久化 / `canMove` missing / 模板回滚（含体积检查前置）/ import 合并 /
  `pathConflictDir` 对称
- **`tests/test_routes.py`**：新增 2 项回滚测试（`mock.patch("os.replace")` 定点失败）→ **+2**
- **`tests/test_dtree_core.py`**：新增 1 项类型对称测试（`pathConflictDir`）→ **+1**
- `unittest`：127 → **130 OK**

### 验证（全部实测）

| 项 | 结果 |
|---|---|
| `verify.py` | **79 项 0 失败** |
| `unittest` | **130 OK** |
| `smoke.py` | **17 项 0 失败**（服务读到 `V0.0.24`） |
| Node 模型层 | `canMove` 七态 **7/7**（含新增 `missing`） |
| Node 驱动真实模块（P3-9） | 首次 POST **1** 次 → 二次调用 / 模拟重载后均 **1**（不再增）—— **4/4** |
| 无头 Edge | `index.html` 默认示例 6 行、`ctxMenu` 就位；import 合并后模块装配正常 |
| 指纹比对 | `V0.0.24@r1` 一致 |

> **注**：P3-8 / P3-12 属结构性整理（无独立运行期签名），由静态守卫钉住；
> P3-11 回滚由单测（真实临时目录 + mock 定点失败）覆盖；P3-9 由 Node 驱动真实模块实测覆盖。

---

## V0.0.23 — 2026-10-10

**主题**：全项目架构与逻辑审查的 **P2 收口** —— 契约 / 文档漂移订正 + 两处误报与死码修正（修正后**无行为回归**，`verify` 反而由 77 增至 78 项）。

> **立项依据**：用户「采纳建议，分步，依次执行」（第 2 步）。来源见 `docs/审查报告_架构与逻辑_20261010.md` §P2。
> **用户环境**：Windows 11 本机，仅**鼠标 + 键盘**；触屏与其他 OS **无法验证** —— 故该类改动在本环境**不做**（不实证不交付）。

### 变更（`src/` 与 `start.bat`）

- **共享契约版本戳同步**（`shared/schema.json`）
  - `version` 由 `V0.0.17` 改为与 `VERSION` 同步（此前停在 V0.0.17，**契约漂移 6 个版本**）
  - 补 `templateSaveRequest.overwrite`（严格 `true` 才覆盖）、`templateSaveResponse.overwritten`；
    订正陈旧注释「同名模板已存在时返回 templateExists，**绝不覆盖**」→ 明示 `overwrite:true` 时覆盖
  - 补 `templateListResponse` / `templateRenameRequest` / `templateRenameResponse` / `templateDeleteResponse`
    —— 模板 5 类接口此前在契约中**完全缺席**
- **帮助页死代码清理**（`web/js/help.js`）
  - 删 `buildSupport()` 及其 `kind === 'support'` 分支。该分节自 V0.0.18 拆为独立页 `support.html`
    后已无任何消费者（`helpSections` 实况 7 节：ol/ul/ul/note/ul/about/ul，**无 support**）
  - `.help-support` / `.help-qr` / `.help-thanks` CSS **保留** —— `support.js` 仍在用
- **启动脚本解释器判定修正**（`start.bat`）
  - 原第 11 行无条件用 `python -V` 判定 → `py -3` 可用但 `python` 不在 PATH 时**误报**「未检测到 Python 3.8+」；
    改为判定**已选定**的 `%PY%`（`py -3` 失败才回退 `python`），并把注释由 `::` 改 `rem`（批处理内更稳）

### 文档订正（不进版本清单，随 `src/` 同版交付）

- **`README.md`**：`V0.0.6` → `V0.0.23`；目录树补 8 个缺失模块 + `support.html` + `sponsor-wechat.png`；
  键数 `136/144` → **296**；校验项 `52/49` → **77/74**；测试模块 `4` → **6**；皮肤 **15 款**；
  新增「**目录树操作**」「**模板库**」两节；快捷键补 `Delete` / `F2`；§P0-3 守卫 `7` → **11**；回退示例版本号对齐
- **`docs/项目手册.md`**：同源订正 —— 版本 / 模块树 / §五 接口表（补 `/api/env.js` `/api/templates`(GET·POST·POST\<name\>·DELETE)
  `/api/shortcut` `/api/launch-icon`）/ §六 环境变量（`6` → **12**，含上限分层自洽说明）/ 键数 **296** / 校验项 **77·74**；
  §三 补「**实测环境：Windows 11，鼠标 + 键盘；触屏与其他 OS 未验证**」

### 守卫（`tools/verify.py` 77 → **78 项**）

- **共享契约版本戳**：`schema.json` 的 `version` 必须等于 `VERSION`（缺 `VERSION` 的预览目录跳过）
- 「回归测试网」必需文件清单补 `tests/test_config.py` / `tests/test_launch_icon.py`（防新模块失去保护）
- 文档头部校验清单同步（补 9a；「四模块」措辞改为「全部 `test_*.py`」）

### 测试

- **无新增** —— 本轮为契约 / 文档 / 死码 / 误报修正；`unittest` 维持 **127 OK**

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **78 项 0 失败**（+1：共享契约版本戳） |
| `unittest` | **127 OK** |
| `smoke.py` | **17 项 0 失败**（服务读到版本 = `V0.0.23`） |
| `schema.json` JSON 合法性 | 顶层 15 键解析通过，`version=V0.0.23` 与 `VERSION` 一致 |
| **无头 Edge 实证 · 帮助页** | 渲染 **7 分节** + 导航 **7 项**；版本徽标取到后端实测值 `V0.0.23` |
| **无头 Edge 实证 · 支持页** | `.help-qr` ×1、`.help-thanks` ×1、赞赏码 `sponsor-wechat.png` 就位（`buildSupport` 移出帮助页后支持页仍正常） |
| 隔离 | 实证在 `_sandbox/qm_p2_probe_20261010/` 副本内起服务，**测后即删**；`data/editor.json` mtime 未变、真实模板仍 **17 套**、`git status` 仅列预期 10 个改动文件 |

### 已知边界

- `help.support.lead` 等少量取词键在帮助页拆页后已无消费者 —— **保留不删**（键闭包守卫只查「引用 ⊆ 字典」，
  多余键无害；删键反而有漏改风险）。同类清理留待「取词表瘦身」专项
- `docs/项目约定.md` 中的 **L2/L3 条目**（"实测 116 个引用键 ⊆ 144 键（V0.0.6）"、"zh-CN.js 为唯一取词表（136 键）"）
  属**带版本时间戳的决策记录**，**非现状断言** —— 故**不改写**，保留其历史原貌（现状以本 CHANGELOG 与 README / 手册为准）

---

## V0.0.22 — 2026-10-10

**主题**：全项目架构与逻辑审查的 **P1 修复** —— 三处「静态守卫覆盖不到」的真实缺陷。

> **立项依据**：2026-10-10 全项目架构/逻辑审查（`docs/审查报告_架构与逻辑_20261010.md`）。
> 审查基线 verify **74/0** · unittest **120 OK** · smoke **17/0** **三绿** —— 恰恰说明下列三处
> 缺陷都在既有静态守卫的**覆盖范围之外**，由逐行静态阅读 + 无头浏览器实证 / 量化计算确认。

### 变更（`src/`）

- **帮助页分节幂等**（`web/js/help.js`）
  - `renderSections()` 渲染前**清空** `#helpSections` 与 `#helpNavList`。此前只 `appendChild`、从不清空，
    而 `qmlocalechange` 监听**每次切换语言都调它** → 分节与导航成倍累积（无头 Edge 实测 **7 → 14 → 21**）
- **默认示例随语言**（`web/js/main.js`）
  - `initPrefs()` 提到**模块顶部**、早于 `defaultRoot()`。此前 `defaultRoot()` 跑在模块顶层，此刻 i18n
    仍是出厂 `zh-CN` → 英文环境首屏示例为中文名，且随即被 `restoreDocument()` 的 `saveNow()` **永久落盘**，
    语言探测（V0.0.14 真 OS 语言）形同虚设
- **体积上限两层自洽**（`server/config.py`）
  - `MAX_BODY_BYTES` 由固定 `256KB` 改为**从业务上限派生**：`BUSINESS_MAX_BYTES = max(编辑态 8MB,
    模板 2MB, 2×图标)`，另留 256KB 组帧余量；`QM_MAX_BODY` 只能**抬高**该值（`max()` 兜底）
  - 此前 `_read_body()` 用 256KB 先于各业务检查拦下请求体 → `editorTooLarge` / `templateTooLarge` /
    `iconTooLarge` **永远不可达**，用户只拿到误导性的 413 `bodyTooLarge`

### 守卫（`tools/verify.py` 74 → **77 项**）

- **请求体上限一致性 V0.0.22**：子进程实测导入 `config`（`-B` 免写 `__pycache__`），断言
  `MAX_BODY_BYTES ≥ max(各业务上限)`
- **帮助页分节渲染幂等 V0.0.22**：`renderSections` 函数体内必须含清空语句
- **默认示例取词前置 V0.0.22**：`initPrefs()` 必须早于 `defaultRoot()` 调用点
- 「回归测试网」note 改为**按实际 `test_*.py` 计数**（防「四模块」这类会随新增模块漂移的硬编码）

### 测试

- `tests/` 新增 **`test_config.py`**（6 项，子进程导入 `config`，支持 `QM_SRC`）→ `unittest` **120 → 127 OK**

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **77 项 0 失败**（+3：三条 V0.0.22 守卫） |
| `unittest` | **127 OK**（+7：新增 `test_config.py`） |
| `smoke.py` | **17 项 0 失败** |
| **无头 Edge 实证 · 帮助页分节幂等** | `BEFORE sec=7 nav=7` → `en-US 7/7` → `zh-CN 7/7`（**修复前实测 7 → 14 → 21**） |
| **无头 Edge 实证 · 英文环境默认示例** | `HTML_LANG=en-US` → 示例名**全英文**：`QingMan Sample Project / Materials / Raw / Tidied / Output / README.md`（修复前为中文名） |
| **配置上限实测** | 传输 `8,650,752` ≥ 业务 `8,388,608`（编辑态 8MB / 模板 2MB / 图标 256KB），业务错误码**可达** |
| 隔离 | 全过程在 `_sandbox` 副本内起服务，**测后即删**；`data/editor.json` mtime 未变、真实模板仍 **17 套** |

### 已知边界

- 默认示例的取词只发生在**首次生成时**（`defaultRoot()`）；一旦落盘，示例名属**用户数据**，
  随后切换语言**不再**改名（有意为之）
- `QM_MAX_BODY` 只能**抬高**传输上限，**不能**低于业务上限（防两层不一致复现）
- 本轮仅修 P1 三项；审查报告的 **P2**（契约/文档漂移：`schema.json` version 停在 V0.0.17、`README.md`
  与 `docs/项目手册.md` 停在 V0.0.6、`start.bat` 的 Python 探测、`help.js` 死代码）、**P3** 清理，
  以及「无头浏览器冒烟」守卫**留待后续步骤**

---

## V0.0.21 — 2026-10-10

**主题**：模板覆盖写 —— 同名模板由「一律拒写」升级为「**显式确认后可覆盖**」（旧模板先入回收站）。

> **立项依据**：V0.0.13 起「另存为模板」遇同名**一律拒写**（`templateExists`），用户想更新既有模板只能改名或先删除重存。
> V0.0.21 把「旧的那套丢不丢」的决定权**明确交回用户**：默认行为不变（仍拒写），仅当用户**二次确认**后带
> `overwrite: true` 才覆盖，且**旧模板先入回收站**（延续项目总原则「只复制不删除」）。

### 变更（`src/`）

- **后端**（`routes.py`）
  - `save_template` 新增 `overwrite` 判定：**严格 `is True`**（防 `"true"` 等真值字符串被误当开关）；未带该字段时行为与旧版**完全一致**（仍 `raise templateExists`）
  - 覆盖分支：先把旧文件 `os.replace` 移入 `templates/.trash/<时间戳>/`（复用 `_template_trash_dir`），再原子写新文件 —— 误覆盖可人工找回
  - 返回值新增 `overwritten` 布尔（新建 / 覆盖一目了然）
- **前端**（`main.js`）
  - `saveAsTemplate`：捕获 `templateExists` → `confirm` **二次确认**（文案明示「原模板将移入回收站」）→ 确认后带 `overwrite: true` 重发；成功后按 `overwritten` 分流提示（`template.overwritten` / `template.saved`）
- **i18n**：新增 2 键（`template.overwriteConfirm` / `template.overwritten`），中英对齐
- **守卫**：`verify.py` 73 → **74 项**，新增**「模板覆盖写」**（后端 `is True` 严格判定 / 默认仍拒写 / 覆盖前必入回收站 / 返回 `overwritten` / 前端 `templateExists` 捕获与 `overwrite: true` 重发与二次确认 / 两语取词）

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **74 项 0 失败** |
| `unittest` | **120 OK**（+4：覆盖前旧文件入回收站且逐字节保真 / 缺失或显式 false 仍拒写 / 真值字符串不得开启 / overwrite 但目标不存在则新建不误报） |
| `smoke.py` | **17 项 0 失败** |
| **E 盘真实文件系统实证**（直接加载产品源码，非 mock） | **13 项 0 失败**：新建 `overwritten=false` / 同名拒写且内容不污染 / 字符串 `"true"` 不开启 / 覆盖 `overwritten=true` 且内容为新 / `.trash` 旧副本逐字节一致 / 列表非递归扫不到 `.trash` / 覆盖不存在名不误报 / 落盘仍 LF 且带 `schemaVersion` |
| 浏览器 E2E · 覆盖写真实 HTTP 往返（Edge headless 同源，同步 XHR） | **8 项 0 失败**：新建 `overwritten=false` / 同名拒写 `templateExists` / 拒写后内容仍 v1 / `overwrite=true` 成功 `overwritten=true` / 覆盖后内容 v2 / 字符串 `"true"` 不开启 / 覆盖不存在名新建 / 探针清毕**真实模板仍 17 套** |
| 前端 JS 语法（Node `--check`） | 8 个改动模块全 OK |

### 已知边界

- 覆盖仍是**软删除**：旧模板留在 `templates/.trash/<时间戳>/`，需人工清理（有意为之）
- 覆盖判据为**严格 `is True`**：前端必须传布尔 `true`，字符串 `"true"` 不生效（防误触发）
- **headless Edge 排查备注**：`--dump-dom` 对**含同步 XHR 的页**需配 `--virtual-time-budget` 才稳定取到结果；测试页路径写错（`cd` 未在后台子 shell 生效 → 404）会表现为「恒 pending」，**非脚本缺陷**（本轮据此定位并修复）

---

## V0.0.20 — 2026-10-10

**主题**：note 编辑按会话入栈（修 V0.0.17 撤销栈缺陷）+ 模板 CRUD 补全（删除 / 重命名）。

> **立项依据**：① **重做修复** —— V0.0.17 的 note 编辑每敲一键就 `pushHistory()` 一次，
> 打一段字即可吃光 50 步撤销栈，且一次 Ctrl+Z 只退回一个字符；② **模板 CRUD** —— 此前只有
> 读（V0.0.11）与另存为（V0.0.13），缺「删」与「改名」，用户建错模板只能去文件系统手动清。

### 变更（`src/`）

- **note 编辑会话**（`main.js` + `inspector.js`）
  - 新增 `noteHistoryId`：**同一节点连续编辑只在第一次入撤销栈**，一次 Ctrl+Z 退回编辑前整体状态
  - 会话终止三条件：**失焦**（`propNote` blur）／**切换选中节点**（`render()` 比对 `lastRenderedSelectedId`）／**撤销重做后**（`restoreHistory`）
  - `inspector.resetEditing()`：撤销/重做恢复了模型值后**显式作废编辑暂存** —— 否则 render 的防打断光标逻辑会让输入框仍显示回退前旧文本（模型与 UI 脱节）
- **模板 CRUD**（后端 `routes.py` / `app.py` / `config.py` + 前端 `api.js` / `main.js` / `layout.css`）
  - `DELETE /api/templates/<name>` → `delete_template`：**软删除**，移入 `templates/.trash/<时间戳>/`（项目总原则「只复制不删除」；`.trash` 以 `.` 开头且非递归，`glob("*.json")` 天然扫不到）
  - `POST /api/templates/<name>` → `rename_template`：**同时改文件名与文件内 `name` 字段**（否则列表显示名与 URL 脱节）；同名目标拒绝（沿用 `templateExists`）；旧文件移入回收站保底
  - 路径校验收敛到 `_template_path_or_raise`（白名单 + `is_within` 单一来源，`load_template` 一并复用）
  - 前端：模板列表项新增「重命名 / 删除」按钮（`.tpl-ops`，hover / 聚焦显形）；删除有二次确认；操作后刷新列表
  - 错误码新增 `templateDeleteFailed` / `templateRenameFailed`（`error-codes.json` + 中英取词）
- **i18n**：新增 12 键（`template.rename/renameTip/renamePrompt/renamed/delete/deleteTip/deleteConfirm/deleted/opFailed` + `err.templateDeleteFailed/templateRenameFailed`），中英对齐
- **守卫**：`verify.py` 72 → **73 项**，新增**「模板 CRUD + note 会话」**（后端删除必走回收站且**禁止 unlink/remove** / 后端—前端贯通 / `onNoteChange` 按会话守卫入栈 / `resetEditing` 齐备 / 错误码登记）

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **73 项 0 失败** |
| `unittest` | **116 OK**（+9：软删除入回收站 / 删除路径穿越拒 / 重命名改文件名+内层 name / 重命名拒重名 / 同名 noop / 非法名与缺失分支） |
| `smoke.py` | **17 项 0 失败** |
| 浏览器 E2E · 模板 CRUD 真实 HTTP 往返（Edge headless 同源） | **13 项 0 失败**：创建→列表可见→重命名→旧名 404 新名 200 且 name 同步→列表换名→DELETE→不可读→不存在 404→路径穿越拒→缺防护头 403→**探针清毕真实模板仍 17 套** |
| 浏览器 E2E · note 会话与模板 UI（iframe 载入真实页面派发事件） | **15 项 0 失败**：模板行 2 个操作按钮且文案非空 / **连续 3 次输入后一次 Ctrl+Z 即回到编辑前（未停在中间态 ab）** / 静态键与接线齐备 |

### 已知边界

- 软件删除**不真删**：文件留在 `templates/.trash/<时间戳>/`，需人工清理（有意为之，防误删）
- 重命名只改模板名，不改树内容；「覆盖已有模板」仍不支持（沿用同名拒写，删除+另存即可达成）
- note 编辑会话按「失焦 / 切节点 / 撤销」切分：**同一节点长时间连续编辑始终只占一格历史**（设计取舍：宁可粒度粗，不可淹没栈）

---

## V0.0.19 — 2026-10-10

**主题**：树交互增强 —— 拖拽移动节点 + 右键快捷菜单 + `Delete` / `F2` 快捷键。

> **立项依据**：三栏编辑器此前对目录树只有「工具栏按钮 + 单击选中」两条交互路径；
> 移动节点必须「删除重建」，重命名/删除要先把鼠标移到中栏工具栏。本轮补齐三种**就地操作**，
> 让树本身成为完整操作面（拖拽=移动，右键=上下文菜单，键位=键盘流）。

### 变更（`src/`）

- **数据模型**（`tree-model.js`）
  - 新增 `isSelfOrDescendant(node, id)`：判断节点是否在目标子树内（防环基础）
  - 新增 `canMove(root, id, targetDirId)`：**不改数据**的合法性检查，返回 `true | 'notDir' | 'cycle' | 'exists' | 'root'` —— 让调用方能在**入撤销栈之前**判定
  - 新增 `moveNode(root, id, targetDirId)`：复用 `canMove`（校验单一来源），通过则从原父移除、挂到目标目录下；纯数据操作，撤销栈由调用方管理
- **树视图**（`tree-view.js`）
  - 节点行 `draggable`（根节点除外）；`dragstart` / `dragover` / `drop` / `dragleave` 全接线，目录行作落点并高亮
  - `contextmenu` 事件回传 `onContext(id, x, y)`；新回调 `onMove(id, targetDirId)`
  - 视图内重渲染改用 `currentSelectedId` 快照，避免折叠/拖拽时闭包取旧值
- **右键菜单**（新增 `ui/ctx-menu.js` + `index.html` `#ctxMenu`）
  - `showAt(x, y, items)` 收集菜单项并由调用方注入动作 —— **菜单本身零业务逻辑**
  - 视口边缘翻转防溢出；`Escape` / 点击外部 / 窗口失焦关闭；`↑` / `↓` 键盘导航
  - 菜单项与工具栏**共用同一组动作函数**（`doAddChild` / `doRename` / `doDelete` 由内联处理器提取为具名函数）
- **主入口**（`main.js`）
  - 拖拽：`canMove` 前置校验 → `pushHistory()` → `moveNode()` → 展开目标目录 → 状态提示（**顺序保证撤销快照是改动前状态**）
  - 右键：先选中被右键节点再弹菜单；根节点禁用「重命名 / 删除」、非目录禁用「新建子节点」
  - 键位：`Delete` 删除、`F2` 重命名（**在 typing 守卫之后**，输入框/textarea 内不拦截）
- **样式**（`layout.css`）：新增 `.is-drop-target`（落点高亮，只用既有变量）与 `.ctx-menu` / `.ctx-item`（面板质感复用 `--qm-surface` / `--qm-line` / `--qm-r-sm` / 阴影 token）
- **i18n**：新增 9 键（`tree.copyPath` + `status.moved` + `toast.moveNotDir/moveCycle/moveRoot` + `help.kbd.delete/rename` + `help.tree.6/tree.7`），中英对齐；帮助页键位表同步登记 `Delete` / `F2`
- **后端零改动**（纯前端交互）

### 变更（`tools/` 与测试）

- `verify.py`：71 → **72 项**（`REQUIRED_IDS` 补 `ctxMenu`；新增守卫**「树交互增强」**：`moveNode` 复用 `canMove` / `canMove` 带防环与同名拦截（AST 钉函数体）/ 视图层五事件接线 / `main.js` 前置校验与三具名函数 / 两键位接线 / 取词键齐备 / 菜单容器存在）

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **72 项 0 失败** |
| `unittest` | **107 OK** |
| `smoke.py` | **17 项 0 失败** |
| Node 模型层实证（`_sandbox/qm_move_20261010/`，直接加载产品源码） | **25 项 0 失败**：四类拦截（根/非目录/环/同名）/ 非法移动零改动 / 合法移动父子关系与计数 / id 唯一性保持 / 往返移动 id 不变 / 序列化往返保留 / 整树移动子树完整 / `isSelfOrDescendant` 边界 / 同名大小写不敏感 |
| 浏览器 E2E 静态断言（Edge headless 同源） | **26 项 0 失败**：`ctx-menu.js` 导出 / 拖拽与右键接线 / `main.js` 前置校验与具名函数 / 键位接线 / 模型三导出 / CSS 类 / 菜单容器位置 / 中英新键齐备 / 四页 200 |
| 浏览器 E2E 行为（iframe 载入真实页面派发事件） | **13 项 0 失败**：树已渲染 / 根不可拖其余可拖 / 右键菜单显示 4 项且文案非空 / 根上重命名删除禁用 / 菜单不溢出视口 / `Escape` 关闭 / 子节点重命名删除可用 |

### 已知边界

- 拖拽用于 **HTML5 DnD**，触摸设备无原生支持（桌面优先，与 V0.0.18 后裁定的 Windows 优先一致）
- 右键菜单为**自定义菜单**，仅在树节点行内拦截；树空白处仍弹浏览器原生菜单
- `Delete` / `F2` 在输入框内不生效（保留原生编辑行为）

---

## V0.0.18 — 2026-10-10

**主题**：帮助/支持拆两页 —— 「支持与赞赏」从帮助页分节独立为 `support.html`，帮助页瘦身、入口直达。

> **立项依据**：帮助页承载「使用说明 + 关于 + 支持赞赏」三职责，赞赏码图占比大、
> 与「查问题」场景无关；拆页后帮助页纯文档检索，赞赏入口一步直达。

### 变更（`src/web/`）

- **新页**：`support.html` + `js/support.js` —— 赞赏码展示页，复用 `base.css`/皮肤/`env.js` 同步语言注入（与 `help.html` 同构）；文案全走 `support.*` 取词键
- **帮助页**：`helpSections` 删除 `support` 分节（zh/en 同步）；「关于」表新增「支持与赞赏」行，`window.open('./support.html')` 跳转
- **主界面**：顶栏「支持」按钮 `btnSupport` 由帮助页锚点 `#support` 改为直接开 `support.html`（`main.js`）
- **i18n**：`help.support.*` 键组迁移为顶级 `support.*`（`titleTag/thanks/toHelp` 等），zh/en 键对齐
- **后端零改动**（纯前端拆页）

### 变更（`tools/` 与测试）

- `verify.py`：`REQUIRED_FILES` 补 `support.html` / `js/support.js`（68 → 71 项）
  - 新增守卫**「帮助支持拆两页」**：helpSections 无 `support` 分节 / `main.js` 开 `support.html` 无旧锚点 / about 表含跳转 / `support.js` 文案走取词
  - 三处页面列表守卫（键闭包 / 无硬编码中文 / env.js 顺序）加入 `support.html`

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 71 项 0 失败 |
| `unittest` | 107 OK |
| `smoke.py` | 17 项 0 失败 |
| 浏览器 E2E（Edge headless · 同源驱动真实页面） | 17 项 0 失败：support.html 三引用齐备无硬编码中文 / support.js 渲染赞赏码且字面量无中文（剥注释同 verify 口径）/ zh-en helpSections 无 support 分节且专属键齐备 / main.js 新入口无旧锚点 / help.js about 表互链 / 两页真实 HTTP 200 |

### 已知边界

- `support.html` 是独立页面（非弹窗），从主界面打开会新开窗口/标签
- 赞赏码图 `sponsor-wechat.png` 沿用 V0.0.8 引入的资源，未随拆页变更

---

## V0.0.17 — 2026-10-10

**主题**：属性栏 note 编辑 + 三粒度复制 + .md 纯文本边界 —— 节点可写说明，随文档持久化。

> **立项依据**：多轮只读分析锁定的决策落地 —— 保留 `.md`（B）、模板载入自动填 `说明文档.md`
> 到根 note、根说明为独立副本不回写（X）、工具不解析/渲染/校验 Markdown（纯文本边界）。

### 变更（`src/`）

- **数据模型**（`tree-model.js`）
  - 节点增加可选 `note` 字段（string；`normalizeNote` 把非字符串归空串，老文档缺失视为空 —— **schemaVersion 不升**）
  - `toDocumentNode` / `fromDocumentNode` 双端带 note（编辑态持久化往返保留）
  - **`toPlainTree` 不含 note** —— note 是编辑态元数据，不参与 `/api/generate` 落盘
  - 新增 `adoptTemplateNote(root)`：根 note 为空时取根下 `说明文档.md`（兜底首个 `*.md`）的 content 填入 —— **独立副本**，原 .md 保留不动；已有 note 不覆盖；纯函数便于单测
- **属性栏**（`inspector.js` + `index.html` + `layout.css`）
  - 「说明」`textarea`（纯文本编辑，随选中节点切换；未选中禁用）—— 编辑与重命名同路：入撤销栈（可 Ctrl+Z）→ `markDirty()` 自动保存
  - 三粒度复制按钮：**复制名称** / **复制路径** / **复制说明**（`navigator.clipboard` 优先，`execCommand` 降级）
- **i18n**：新增 10 键（`inspector.noteTitle/notePlaceholder/copy/copyNameTip/copyPathTip/copyNote/copyNoteTip` + `status.noteUpdated` + `template.noteAdopted` + `toast.copied/copyFailed`）
- **后端零改动**：`validate_document` 对未知字段本就宽容（note 随文档原样保存）；错误码零新增
- **schema.json**：`editorNode` 增加 `note` 描述，版本标注 V0.0.17

### 变更（`tools/` 与测试）

- `verify.py`：`REQUIRED_IDS` 补 `propNote` / `btnCopyName` / `btnCopyPath` / `btnCopyNote`；新增守卫**「note 契约与 .md 边界」**（67 → 68 项）：序列化两端带 note（正则钉函数体）/ `toPlainTree` 不含 note / `inspector.js` 无 `innerHTML`（纯文本边界）/ 模板提炼与复制按钮接线齐备
- 「JS 文案经取词表」守卫新增**数据字面量豁免**：`说明文档.md` 是约定文件名（数据标识非文案）
- `tests/test_routes.py` 新增 note 测试（+1）：含 note 文档保存往返 + 老文档（无 note）依旧可存

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 68 项 0 失败 |
| `unittest` | 107 OK |
| `smoke.py` | 17 项 0 失败 |
| Node note 实证（E 盘） | 12 项 0 失败：normalizeNote 容忍 / 提炼命中「说明文档.md」优先 / 独立副本 / 已有 note 不覆盖 / 无 md → null / 序列化往返保留 / 老文档兼容 / id 唯一性 / toPlainTree 不含 note |
| 浏览器 E2E（Edge headless · 同源驱动真实页面） | 17 项 0 失败：主页含 propNote/btnCopyNote、无 checklist；模型导出与函数体判据；inspector 无 innerHTML；main.js 三按钮接线；**真实 PUT/GET /api/editor 含 note 文档往返**（测后已清理恢复） |

### 已知边界

- note 不参与生成落盘（`/api/generate` 的树里没有说明）—— 说明属于编辑态元数据；若日后要生成 README 类文件，另行立项
- 模板提炼只看**根的直接子层**；深层 .md 不提炼
- 复制走 `navigator.clipboard`（127.0.0.1 安全上下文可用）；`execCommand` 降级在现代浏览器已弃用，仅兜底

---

## V0.0.16 — 2026-10-10

**主题**：服务状态三态 + 左栏自检迁移 —— 启动自检从常驻左栏收敛为顶栏一个「服务状态」chip。

> **立项依据**：左栏 `checklist` 的 4 项自检（modules / backend / model / write）是**一次性诊断
> 信息**，其中 modules/model 启动即恒真、backend 顶栏已体现、write 生成后才反馈 —— 信息密度低
> 却常驻左栏。故把自检收敛为顶栏「服务状态」三态，左栏只留模板工作区。

### 变更（`src/`）

- **前端**
  - `index.html`：移除左栏 `#checklist` 块（「骨架自检」标题 + 4 项清单）；`chipBackend` 初始态改为 `connecting`
  - `main.js`：`markCheck` / `failCheck` 删除，改为 `setServiceState(state)` 三态 —— `connecting`（连接中·灰）/ `ready`（服务就绪·绿）/ `offline`（服务不可用·红），复用现有 `chip-ghost` / `chip-ok` / `chip-bad` 视觉，不新造
  - `boot()` 收敛：探测前 `connecting`、`health()` 成功 `ready`、失败 `offline`；`write` 自检并入生成结果（`statusBar` 已反馈）、`modules`/`model` 并入 `ready` 态
  - `qmlocalechange` 用 `setServiceState(serviceState)` 刷新 chip 文案（语言切换后同步）
- **i18n**：删 `sidebar.checkTitle` + `check.modules/backend/model/write` + `topbar.backendOn/Off`（7 键），新增 `topbar.backend.connecting/ready/offline`（3 键）
- **CSS**：删 `.checklist` 整套死代码（layout.css）

### 变更（`tools/`）

- `verify.py`：`REQUIRED_IDS` 移除 `checklist`；新增守卫**「服务状态三态」**（66 → 67 项），判据三端：左栏清单已移除 / 顶栏三态接线（`SERVICE_CHIP_CLASS` + `setServiceState`）/ 三态取词键齐备 —— 防「删了清单却忘了接线三态」或反向回归

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 67 项 0 失败 |
| `unittest` | 106 OK |
| `smoke.py` | 17 项 0 失败 |

---

## V0.0.15 — 2026-10-10

**主题**：桌面快捷方式图标「皮肤联动」—— 图标配色跟随当前皮肤，换肤即变色。

> **立项依据**：V0.0.9 的 `_write_lnk` **从不设置 IconLocation**，桌面快捷方式显示的是
> `.bat` 的默认控制台图标。且皮肤是前端 CSS 变量概念，后端不掌握调色板 —— 要让图标
> 随皮肤变色，只能由前端按当前皮肤绘制 ICO、后端负责落盘与接线。

### 变更（`src/`）

- **后端**（`routes.py` / `config.py` / `app.py`）
  - 新增 `POST /api/launch-icon`（`save_launch_icon`）：base64 ICO → `validate_ico` 结构校验 → 原子落盘 `data/qm-launch.ico`（恒定路径，无穿越面）
  - `validate_ico` 只认 **PNG-in-ICO**：魔数 / 目录项 1–16 / 尺寸合法值 / 每帧偏移与长度落于文件内 / 每帧 PNG 头尾完整 —— 防任意文件挂名上传
  - `_write_lnk` 增加 `icon` 参数，`create_shortcut` 请求带 `icon` 时先落盘再写 `IconLocation`；下载降级路径**刻意不主题化**（.lnk 指向的绝对路径在用户机器上不存在，主题化只会换裂图标）
  - `_refresh_icon_cache`：`SHChangeNotify(SHCNE_ASSOCCHANGED)` 尽力刷新 Explorer 缓存，失败静默
  - 新增 4 个错误码 `iconDataMissing` / `iconInvalid` / `iconTooLarge` / `iconWriteFailed`
- **前端**（新增 `ui/launch-icon.js`）
  - 字形 = `logo.svg` 的 path（运行时 `fetch` 解析，**单一事实源**）；底板 = `--qm-surface`；字形色 = `--qm-accent`，对比度 < 3:1 时回退 `--qm-text`（守卫只兜底）
  - 16/32/48/256 四档 PNG → `buildIco` 组包（纯函数，Node 可复用验证）
  - `ensureLaunchIcon()`：换肤后重传同路径 ICO（去重：配色未变不重传）；`applySkin` 在样式表 `onload` 后派发 `qmskinchange`，确保读到新皮肤计算值
  - `createShortcut` 点击时先渲染图标再 POST，失败走 null → 默认图标，不阻塞
- **既有 bug 修复**：`_lnk_script` 原用 Python `repr`（`!r`）转义路径，反斜杠被加倍成 `\\`，而 PowerShell 单引号里反斜杠是字面量 —— `.lnk` 里写的是 `D:\\Data\\...` 错路径。改为 `_ps_quote`（反斜杠→正斜杠、单引号翻倍）

### 变更（`tools/` 与测试）

- `verify.py` 新增守卫**「快捷方式图标契约」**（65 → 66 项）：AST 钉函数体，确认 `_lnk_script` 真拼 IconLocation、`create_shortcut` 串联落盘+刷缓存、`save_launch_icon` 过 `validate_ico` + 原子替换、`validate_ico` 校验 PNG 帧完整性
- `tests/test_launch_icon.py` 新增 **16 条**（套件 90 → 104）：`validate_ico` 正反例、`_lnk_script` 的 IconLocation 拼装与**双反斜杠回归锁**、`save_launch_icon` 落盘往返

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 66 项 0 失败 |
| `unittest` | 104 OK |
| `smoke.py` | 17 项 0 失败 |
| Node ICO 往返（E 盘） | 5 项：`parseLogoSvg` 取到 d(29476)+viewBox / 对比度守卫 s06=4.85·深色=7.00 / `buildIco` 目录项=4·offset 落范围 |
| 后端 `validate_ico` | 接受 Node 产物(114154B) + 拒绝空/魔数错/截断 → `iconInvalid` |
| 浏览器 Path2D（Edge headless） | 29476 字符超长 path 解析+fill 成功，`nonWhitePx=9555`（~14.6% 画布） |
| HTTP 探针 | `/api/launch-icon` 200 + 落盘字节一致(114154B)；无 `X-QingMan` 头 → 403 |
| `.lnk` 实证（PowerShell 真生成） | IconLocation 写入 + 双反斜杠修复（841→821 字节） |

### 已知边界

- 下载降级路径的 `.lnk` 不主题化（见上）；主题化仅覆盖「直接写桌面」路径
- `validate_ico` 只做结构校验，不解析 PNG 内部 IHDR 尺寸 —— 防恶意文件，不承担图像深检
- `SHChangeNotify` 刷新 Explorer 缓存是尽力而为：个别系统版本可能需重启资源管理器才生效（图标文件本身已更新，不影响下次创建）

---

## V0.0.12 — 2026-10-10

**主题**：错误消息随语言切换 —— 后端错误码全量登记 `err.<code>`，并给语言加上「跟随系统」档。

> **立项依据**：`src/shared/error-codes.json` 的 45 条错误码**全部是中文**，英文界面下弹中文错误（V0.0.11 只本地化了新增的 3 个模板错误码）。同时 `initPrefs()` **只读 `qm.lang`、无则硬兜底 `zh-CN`**，没有任何系统探测。

### 变更（`src/`）

- **错误消息本地化**
  - 后端零改动：`_fail()` 本就返回结构化 `{ok, code, message, detail}`，`detail` 的键恰好就是占位符名，前端按 `err.<code>` 重新成句即可
  - 新增 `src/web/js/core/errors.js`：`localizeError()` / `errorCode()` / `describeError()`，主界面与帮助页共用
  - **44 个错误码全部登记**中英译文（此前仅 3 个）；未登记的码回退后端原文，存量行为不破坏
  - **8 处 catch 全量接线**：`main.js` 6 处 `err.message` → `localizeError(err)`（其中生成失败处改用 `describeError()` 带错误码徽标），`inspector.js` 1 处同步
  - **暴露错误码**：错误提示追加「错误码：xxx」徽标，`api.js` 抛错时 `console.warn` 留痕 —— 技术排查用稳定标识，不依赖文案搜索
- **语言策略**
  - `qm.lang` 新增 `'auto'`（跟随系统），且是下拉里**显式可见的一档** —— 否则用户手动选过一次就永久失去回到自动的路径
  - **BCP 47 降级匹配** `matchLocale()`：逐级剥离子标签，最后按主语言子标签兜底。`zh-Hant-TW` → `zh-CN`、`en-GB` → `en-US`（精确匹配会让繁体用户落到英文界面）
  - 新增 `src/web/js/ui/lang-picker.js`，主界面与帮助页共用
  - 帮助页新增语言下拉；`watchLocale()` 监听 `storage` 事件实现跨页面实时同步
- **不可翻译项的固有边界**：`ioError` / `internalError` / `editorReadFailed` / `shortcutFailed` / `templateReadFailed` 5 条含 `{message}`，其值来自 Python `str(exc)`，英文界面下会与系统原文混排 —— 属预期，枚举 errno 自建映射代价过大

### 变更（`tools/`）

- `verify.py` 新增两道守卫（共 61 → 63 项）
  - **错误码本地化闭包**：44 个码必须在两份取词表齐备，且占位符集合三方（原文 / 中文 / 英文）完全一致
  - **语言策略**：`auto` 一档 + 降级匹配 + 跨页同步齐备

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | **63 项 0 失败** |
| `unittest` | 80 OK |
| `smoke.py` | 17 项 0 失败 |
| Node 实证 · 降级匹配 | 26 项 0 失败（含 `zh-Hant-TW`→`zh-CN`、`en-GB`→`en-US`、无 navigator 不崩） |
| Node 实证 · 错误跟随语言 | 17 项 0 失败（中英切换、未登记码回退、无 code 边界） |
| **守卫反向实证** | 缺键 → FAIL；占位符不一致 → FAIL；去掉 auto 档 → FAIL（首版判据被 `labelOf()` 残留引用蒙混，已收紧为检查选项列表） |

---

## V0.0.14 — 2026-10-10

**主题**：「跟随系统」跟的是**操作系统语言**，不再是浏览器语言。

> **立项依据**：V0.0.12 的「跟随系统」取的是 `navigator.languages` —— 那是**浏览器**的语言偏好，可以
> 被单独改写（安装时选了别的语言、或用户在浏览器设置里调过），与「系统显示语言」不是一回事。
> 浏览器默认继承 OS 语言只是**巧合**，一旦被改过就再也对不上。真值只能问 OS。

### 变更（`src/`）

- **后端取真值**
  - `routes.os_locale()`：Windows 走 `GetUserDefaultLocaleName()`（Vista+，直接返回 `zh-CN` 形态的 BCP 47 标签）；非 Windows 或调用失败一律返回**空串** —— 探测失败不得改变既有行为
  - `health()` 增加 `osLocale` 字段：OS 语言与浏览器语言不一致时，看这一项就知道前端采信了谁
- **同步注入，杜绝语言闪烁**
  - 新增 `GET /api/env.js`：返回一行 `window.__QM_OS_LOCALE__ = "zh-CN";`
  - **为什么不是接口**：语言必须在**首屏渲染之前**定下来。走 `fetch` 会让界面先按浏览器语言画一遍、拿到结果再跳变
  - `<script src="./api/env.js">` 是**普通脚本**，执行早于 module 脚本（`type="module"` 天生 defer），故取值零延迟；主界面与帮助页均已接线
  - 产物恒为 ASCII 且经 `json.dumps` 转义 —— 无注入面
- **前端优先级链**：`显式选择` → **`window.__QM_OS_LOCALE__`** → `navigator.languages` → BCP 47 降级匹配 → `zh-CN`
  - 浏览器语言退居**兜底**：仅在 OS 值取不到（非 Windows / 脚本未加载）时生效，且仍走 V0.0.12 的降级链

### 变更（`tools/` 与测试）

- `verify.py` 新增守卫**「OS 语言注入（跟随系统）」**（64 → 65 项），判据三处：后端真值来源、`env.js` **早于** module 脚本、`systemLocales()` 内 OS 语言**排在** `navigator` 之前
  - **反向实证 2 组**：去掉 `env.js` → FAIL；把 `navigator` 挪到 `osLocale()` 之前 → FAIL
- `tests/test_routes.py` 新增 `OsLocaleTests`（**3 条**，套件 87 → 90）：值为 BCP 47 或空串、脚本形态可 JSON 解析且纯 ASCII、取不到时写空串而非拼进异常

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 65 项 0 失败 |
| `unittest` | 90 OK |
| `smoke.py` | 17 项 0 失败 |
| Node 实证 · 优先级链 | 11 项 0 失败：OS 覆盖浏览器 / OS 空回落浏览器 / OS 不受支持继续看浏览器 / `zh-Hant-TW` 降级 / 全无落默认 / 显式选择压过 OS / 无该字段静默回落 / 无 `window` 不抛错 / 两个页面 `env.js` 顺序 |
| HTTP 层探针（沙盒） | 9 项 0 失败：`/api/env.js` 200 + `text/javascript` + 纯 ASCII + **本机真值 `zh-CN`**、`health.osLocale` 一致、`index.html` 顺序正确 |
| 守卫反向实证 | 2 组均正确 FAIL → 还原后 PASS |

### 已知边界

- 非 Windows 平台 `os_locale()` 返回空串 → 行为与 V0.0.12 完全一致（回落浏览器语言）。青蔓当前只面向 Windows，真值通道在 macOS / Linux 上尚未接通

---

## V0.0.13 — 2026-10-10

**主题**：模板「另存为模板」—— 模板库由只读变为可写，并按 §P2 第 7 项引入 `schemaVersion`。

> **立项依据**：V0.0.11 接入 17 套模板后，左栏**只能读不能写** —— 用户编辑出来的目录树没有沉淀路径。而 §P2 第 7 项留的重议条件正是「青蔓开始写模板时」，本版本即触发点。

### 变更（`src/`）

- **后端新增 `POST /api/templates`**
  - 落盘载荷由 `save_template()` **单点构造**：`schemaVersion` / `name` / `description` / `updated` / `tree`
  - **写入必带 `schemaVersion`（=1），读取仍容忍缺失** —— 17 套老模板一个字不动，`load_template()` 用 `doc.get("schemaVersion", 1)` 兜底。只读路径零迁移成本（§P2 第 7 项重议裁定）
  - **同名一律拒写**（`templateExists`）：静默覆盖会毁掉既有模板，改名是用户该做的决定，与落盘规则 R7/R8 同一取舍
  - **安全**：落盘路径**不由用户给出**，恒定拼在 `templates/` 之下；用户输入只有模板名，先过文件名白名单（不含路径分隔符），再 `is_within` 复核 —— 与 `generate()` 不同，此处没有路径穿越面
  - 原子写（tmp + `os.replace`）+ 显式 `newline="\n"`（§编码基线）
  - 上限：模板名 60 字符、规模复用 `MAX_NODES`（500）、体积 2 MB —— 全在服务端判定
- **前端**
  - 左栏「模板列表」标题行新增**「另存为模板」**按钮（`#btnSaveTemplate`）；`window.prompt` 取名（默认带出当前根节点名），成功后**立刻刷新列表**，否则用户会以为没生效
  - `api.saveTemplate()` 复用既有 `X-QingMan` 写操作防护头；缺头由服务端 403 `missingGuardHeader`
- **错误码新增 8 条**：`templateNameEmpty` / `templateNameInvalid` / `templateNameTooLong` / `templateTreeMissing` / `templateTooManyNodes` / `templateTooLarge` / `templateExists` / `templateWriteFailed`，中英 `err.*` 齐备
  - **有意不含 `{message}`**：避免像既有 5 条那样在英文界面里混排 Python 异常原文
- **契约**：`schema.json` 的 `template` 段补 `schemaVersion`，并新增 `templateSaveRequest` / `templateSaveResponse`

### 变更（`tools/` 与测试）

- `verify.py` 新增守卫**「模板保存契约 §P2 第 7 项」**（63 → 64 项）
  - 判据钉在三处：**落盘载荷同时含 `tree` 与 `schemaVersion`**（用 AST 取 `save_template` 函数体）、拒覆盖同名、读取容忍缺失
  - **反向实证 3 组**：删掉 `do_POST` 分发 → FAIL；写入不带版本戳 → FAIL；去掉拒覆盖 → FAIL
  - 首版判据被 `list_templates` 返回体里的同名字面量蒙混（删掉写入仍 PASS），已改为 AST 定位函数体 —— 与 V0.0.12「auto 档」守卫同类教训
- `tests/test_routes.py` 新增 **7 条**（套件 80 → 87）：往返含版本戳、`.json` 后缀不叠加、同名拒写且原文件未被改写、非法名、超长名、非法 `tree`、规模超限

### 验证

| 项 | 结果 |
|---|---|
| 主线 `verify.py` | 64 项 0 失败 |
| `unittest` | 87 OK |
| `smoke.py` | 17 项 0 失败 |
| HTTP 层探针（沙盒） | 20 项 0 失败：缺防护头 403 / 保存 200 / 落盘含 `schemaVersion` / 落盘为 LF / 同名 400 `templateExists` 且**原文件未被改写** / 非法名 400 / 列表含新模板 / 8 条 `err.*` 中英齐备 |
| 守卫反向实证 | 3 组均正确 FAIL → 还原后 PASS |

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
