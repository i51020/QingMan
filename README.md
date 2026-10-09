# 青蔓 QingMan

本地离线运行的**目录树设计器**：可视化编辑目录树，一键在磁盘上生成真实目录结构。

- 中文名：**青蔓**
- 英文名：**QingMan**
- 当前版本：**V0.0.6**
- 运行环境：Windows 10/11 + Python 3.8+，完全离线，仅监听 `127.0.0.1`

## 快速开始

```bat
:: 双击项目根目录下的 start.bat 即可
start.bat
```

脚本会自动定位 `src/`、用 `python -m server` 启动后端、扫描 8765–8775 端口、打开浏览器。

手动启动（等价）：

```bash
cd src
python -m server
```

### 运行要求（§P2 第 2 项）

| 项 | 要求 |
|---|---|
| Python | **≥ 3.8**（下限；工具层刻意不用 `Path.write_text(newline=…)`，该参数 3.10 才加入） |
| 浏览器 | **Chromium 内核 ≥ 88**（Edge 88 / Chrome 88 及以上）。界面零 Web 框架、零构建，仅用 **ES2020**（可选链 `?.`、空值合并 `??`），故对浏览器版本要求很低 |
| 网络 | 无需联网。服务**只监听 `127.0.0.1`**，数据不离开本机 |

> **提升浏览器下限的规则**：一旦引入任一 **ES2022+** API（如 `Object.groupBy` / `toSorted` / `findLast`），必须把上表下限提升到该 API 的首次支持版本，并同步 `docs/项目约定.md` §P2 第 2 项。

**快捷键**：`Ctrl / Cmd + S` 立即保存目录树（跳过 800ms 防抖）。本版仅此一项，其余键位未设。

## 目录结构

```
QingMan/
├─ VERSION              版本号唯一来源（内容：V0.0.6）
├─ CHANGELOG.md         版本记录
├─ start.bat            启动入口
├─ README.md            本文件
├─ src/                 主线源码（"当前版本"，只在确认后改动）
│  ├─ web/              前端：index.html（主界面）+ help.html（帮助页）+ css/ + js/ + assets/
│  │  ├─ assets/        品牌资源：logo.svg（顶栏标记，经 CSS mask 着色）
│  │  ├─ css/
│  │  │  ├─ tokens.css  设计变量唯一来源（**唯一允许出现裸色值的文件**）
│  │  │  ├─ base.css    基础元素 + 品牌区（两页共用）
│  │  │  ├─ layout.css  主界面布局
│  │  │  ├─ help.css    帮助页布局
│  │  │  └─ skins/      皮肤契约与皮肤文件（皮肤 = 一组变量覆盖，组件不感知皮肤 → §P0-3 L5）
│  │  └─ js/
│  │     ├─ i18n/       取词层：index.js（运行时 t() / applyStatic() / applySkin()）+ zh-CN.js（136 键取词表）
│  │     └─ …           其余模块文案一律走 t()，**不得直写中文**（§P0-3 L1）
│  ├─ server/           后端：Python 标准库，零第三方依赖
│  └─ shared/           前后端共享契约：schema.json / error-codes.json
├─ data/                运行时数据：editor.json（编辑态文档；**不进 git**，见 §P0-7）
├─ store/               内容寻址仓库
│  ├─ objects/          blob 池：路径 = 内容的 SHA-256，跨版本自动去重
│  └─ .trash/           checkout 时多余文件的回收区（不真删）
├─ versions/            版本清单（**只增不改**）
│  ├─ V0.0.6/           MANIFEST.json（基线 r1，当前版本）
│  ├─ V0.0.5/           MANIFEST.json
│  ├─ V0.0.4/           MANIFEST.json
│  ├─ V0.0.3/           MANIFEST.json（基线 r1）+ MANIFEST-r<N>.json（同版本修订）
│  ├─ V0.0.2/           MANIFEST.json
│  └─ V0.0.1/           MANIFEST.json（基线 r1）+ MANIFEST-r<N>.json（同版本修订）
├─ preview/             试运行区（**只服务单次开发**：`promote` 后即清空，不跨版本保留 —— §P1-7）
│  └─ README.md         用途与规则说明（占位，使目录保留在 git 跟踪内）
├─ templates/           17 套中文目录树模板（内容资产）
├─ tests/               回归测试网（标准库 unittest，零第三方依赖 —— §P0-2）
│  ├─ test_dtree_core.py   切分 / 统计 / 文档校验 / check_target(R1–R5) / build_tree(R6–R8)
│  ├─ test_routes.py       生成守卫 / 写入 / 编辑态往返 / 健康
│  ├─ test_store.py        manifest_digest 改名可检出 / parse_ref / 修订链
│  └─ test_versioning.py   bump 三语义（minor 重置 PATCH、major 重置 MINOR+PATCH）
├─ tools/               工具链：store / verify / versioning / release / promote / handoff / smoke
├─ legacy/              历史归档，命名 `<对象>-<日期>/`，只增不删
│  ├─ tools-20261009/    改造前的工具备份
│  └─ preview-20261009/  旧编号预览版 V0.01 全量归档（22 文件，git 保留重命名历史）
├─ docs/                项目手册 / 项目约定 / 任务进度 / 错误笔记 / 接续说明
├─ .git/                过程历史仓库（git，覆盖全项目）
├─ .gitattributes       `* -text` —— 禁止换行转换，保护 SHA-256 指纹
└─ .gitignore           忽略 __pycache__ / store/.trash/ / data/ / 编辑器垃圾
```

## 任务进度

**进度以时间线为准，版本号为参考。**

- 当前做到哪一步 → 看 `docs/任务进度.md` **最上方（最新）**的条目
- 版本号只是索引标签，允许跳号、合并、同一版本内多次推进
- 某个版本具体改了什么 → 看 `CHANGELOG.md`

## 版本约定

**SemVer 三段式：`V<MAJOR>.<MINOR>.<PATCH>`，从 V0.0.1 起。**（旧「V0.01 起、每次 +0.01」规则已于 2026-10-09 作废）

| 递增 | 语义 | 例子 |
|---|---|---|
| `patch` | 修复、纠错 | V0.0.1 → V0.0.2 |
| `minor` | 新增功能 / 逻辑迭代 | V0.0.2 → V0.1.0 |
| `major` | 不兼容变更 | V0.1.0 → V1.0.0 |

**触发规则**：凡改动 `src/` 或交付契约 → 升级；纯文档、纯工具改动 → **不升版**，只在 `docs/任务进度.md` 记一条时间线。

**不升版也要留回退点**：若裁定不升版却改了 `src/`，同一版本内追加**修订**（`r2`、`r3`…），清单落在 `versions/<版本>/MANIFEST-r<N>.json`，可精确取回。规则见 `docs/项目约定.md` §P0-6。

| 步骤 | 命令 | 说明 |
|---|---|---|
| 1. 预览开发 | `python tools/release.py bump --kind patch`，再建 `preview/V<版本>/` | **先升版再建副本** —— 预览副本也含 `VERSION`。试错保护来自**主线仍停在上一版**；**副本不进索引**（§P1-7 生效后），清空按 `git ls-files preview/V<版本>` 二分：**非空** → `git rm -r`；**为空** → `git clean -fd`（**不要 `git add`**）。详见 §P1-7「清空细则」 |
| 2. 交付校验 | `python tools/verify.py preview/V<版本>` | 主线 **51 项**、预览目录 **48 项**（预览无 `docs/`，少「接续说明实况段」与「源码 § 引用可解析」两项；另无 `tests/`，再少「回归测试网」一项 —— 共少 3；带 `--against` 另加 2 项），不通过不落地 |
| 3. 落地主线 | `python tools/promote.py --from preview/V<版本> --force` | 单向：预览 → 主线，只复制不删除（主线非空时需 `--force`） |
| 4. 提交版本 | `python tools/store.py commit --note "说明"` | 写入 blob 池 + 生成清单（同版本则追加修订） |
| 5. 升级版本号 | 见第 1 步 | 本步实际在**第 1 步之前**就要做（版本号须先升）；此处保留编号只为与 §P0-6 修订机制对照 |

**改主线之前必须先 commit**，否则该版本没有回退点。

**⚠️ 版本号与 `store.py commit` 的配套顺序**：`commit` 打的是**「此刻盘上的 `src/`」+「此刻的 `VERSION`」**这个组合，两者必须已配套。若先把 `VERSION` 升到新版**却尚未落地**，此时执行 `release.py snapshot`（= `store.py commit`）会把**上一版的代码**装进**新版本的清单**。落地前请用 `python tools/verify.py . --against <上一版>` 先确认主线仍等于上一版基线（见 `docs/错误笔记.md` §三.18）。

**改 `src/` 后必跑三件套（§P0-2 T5）**：

```bash
python tools/verify.py .                      # 交付校验
python -m unittest discover -s tests          # 单元测试
python tools/smoke.py                         # 端到端冒烟（起真实服务 + 沙盒目录，测完即清）
```

三项全过才算完成。单元测试可用 `QM_SRC=<版本根>/src` 指向**预览版**，这样落地前就能过全部门禁。

## 编辑态持久化

主界面的目录树**自动保存**到项目根 `data/editor.json`：编辑后防抖 800ms 自动写盘，`Ctrl+S` 可立即保存，顶栏 chip 显示「未保存 / 保存中 / 已保存 HH:MM / 保存失败」。刷新或重开浏览器后自动恢复。

接口：`GET /api/editor`（读取）／`PUT /api/editor`（写入，需防护头）。契约见 `src/shared/schema.json` 的 `editorDocument`；规则见 `docs/项目约定.md` §P0-7。

> 之所以不用 `localStorage`：它按 origin（含**端口**）隔离，而本服务端口是**扫描**出来的、并不固定 —— 端口一变 origin 就变，草稿会静默消失。

## 界面文案与皮肤（§P0-3）

**文案零直写**：界面上的每一句中文都来自 `src/web/js/i18n/zh-CN.js` 的取词表（**144 键**），代码里通过 `t(key)` 取；HTML 用 `data-i18n` / `data-i18n-title` / `data-i18n-placeholder` / `data-i18n-aria-label` 属性声明键名，加载时由 `applyStatic()` 统一填充。**后续加 `en-US.js` 即在 `DICTIONARIES` 注册即可切换**，无需改任何组件。

| 约定 | 内容 |
|---|---|
| key 命名 | `<模块>.<元素>.<语义>`，如 `inspector.title`、`tree.menu.delete`、`toast.saved` |
| 取词运行时 | `src/web/js/i18n/index.js`：`t()` / `applyStatic()` / `setLocale()` / `applySkin()` / `initPrefs()` |
| 颜色 | 组件 CSS **只允许 `var(--qm-*)`**，禁止裸色值；新增变量先在 `tokens.css` 定义（**唯一允许写色值的文件**） |
| 皮肤 | 皮肤 = **一组变量覆盖文件** `src/web/css/skins/<name>.css`，经 `applySkin()` 注入 `<link id="skinLink">`。**组件 CSS 不得感知皮肤**（不写 `.skin-dark .btn` 这类选择器） |
| 偏好 | `localStorage` 的 `qm.lang` / `qm.skin` / `qm.genBar`；启动顺序 `initPrefs()` → `applyStatic()` → `initGenBar()` → `render()` |
| ⚠️ 新增偏好键 | 必须声明在 `i18n/index.js`（**导出常量**），不能写在别的模块里 —— 「取词键闭包」检查会排除 `i18n/` 目录，而把 JS 里任何 `a.b` 形式的字面量都当成取词键，写在别处会被误判为"漏翻" |
| SVG 着色 | 一律 ① CSS `mask` 取形状 或 ② 内联 `currentColor`。**禁止 `<img src="*.svg">`** —— `<img>` 中的 SVG 是独立文档，`currentColor` 不继承 |

以上七条外加 L7/L8，由 `verify.py` 的 7 项守卫（§P0-3 系列）逐条把关。

## 中栏：生成参数区可折叠

中栏顶部的三个生成参数（根文件夹名 / 目标位置 / 仅演练）是**"一个项目设一次"的低频项**，却长期占据一整行。**V0.0.6 起可折叠**：收起后只留一行摘要，形如

```
▶ 目标 E:\我的项目 · 根名 我的项目 · 演练中
```

| 行为 | 说明 |
|---|---|
| 切换 | 点击摘要行（`#btnGenToggle`）展开／收起；`aria-expanded` 与 `title` 同步更新 |
| 默认 | **首次启动恒为展开** —— 目标位置不跨会话保存，故与帮助页引导顺序（先填目标位置）一致 |
| 记忆 | 折叠态存 `localStorage['qm.genBar']`（`'open'` / `'closed'`），**只在启动时定一次**，之后完全由用户控制 |
| ⚠️ 不要改成"动态推断" | 若每次渲染按"目标位置是否已填"推断，用户**输入第一个字符**就会触发自动收起，与引导顺序相反。行为探针已把这条写成断言 |
| 摘要实时刷新 | `#inRoot` / `#inTarget` 的 `input`、`#inDryRun` 的 `change` 都会重画摘要行 |
| 兜底 | 目标位置为空时点「一键生成」→ **自动展开**并聚焦，否则输入框不可见、`focus()` 无处落地 |

**参数留在原位、不迁右栏的理由**（裁定记录见 `docs/项目约定.md` §P2 第 15 项）：三项是**作业级（job-scoped）可编辑参数**，而右栏是**选中节点级（selection-scoped）只读属性** —— `inspector.render()` 在无选中时**整栏清空为 `—`**，与"目标位置是必填项、必须始终可编辑"直接冲突。参数项增至 6+ 时再评估迁移，届时须在右栏**单开「生成设置」分区**且**不随选中清空**。

## 存储机制

采用**内容寻址存储**（借鉴 Git 思路）：

- `store/objects/<sha256前2位>/<sha256>` —— 文件内容按 SHA-256 存放，**相同内容只存一份**，跨版本自动去重
- `versions/<版本>/MANIFEST.json` —— 版本**基线**（修订 r1）：「路径 → 指纹」映射 + 元数据（时间 / 父版本 / 说明 / 清单摘要）
- `versions/<版本>/MANIFEST-r<N>.json` —— 同版本**后续修订**（r2、r3…），任何已有清单都不覆盖

实测数据：`V0.0.1@r3` → `V0.0.2` 的 26 个文件里**新增 11 个 blob、复用 15 个**（对象池 35 → 46）；`V0.0.2` → `V0.0.3` 的 27 个文件里**新增 6 个 blob、复用 21 个**；`V0.0.4` → `V0.0.5` 的 29 个文件里**新增 13 个 blob、复用 16 个**；`V0.0.5` → `V0.0.6` 的 29 个文件里**新增 6 个 blob、复用 23 个**。

| 命令 | 作用 |
|---|---|
| `python tools/store.py commit --note "说明"` | 提交当前 `src/` 状态；同版本已有清单时**追加修订** |
| `python tools/store.py checkout <版本[@rN]>` | 回退到指定版本／修订 |
| `python tools/store.py log` | 列出版本链（同版本内按修订倒序） |
| `python tools/store.py diff <版本[@rN]> <版本[@rN]>` | 输出 改动 / 新增 / 缺失 |
| `python tools/store.py fsck` | 校验对象池完整性 |

## 回退

```bash
python tools/store.py checkout V0.0.6         # 取当前版本（= 该版本最高修订）
python tools/store.py checkout V0.0.1@r1      # 精确回退到某个修订
python tools/verify.py . --against V0.0.6     # 与当前版本清单比对
```

回退时「当前有、目标版本没有」的文件，会先复制进 `store/.trash/<时间戳>/` 并**逐字节校验**，通过后才移除原文件 —— 全程不真删。

## 过程历史（git）

两套机制**分工不重叠**：

| 机制 | 回答的问题 | 覆盖范围 |
|---|---|---|
| **git** | 什么时候、改了哪些行、为什么改 | **全项目**（含 `tools/` `docs/` `templates/`） |
| **`tools/store.py`** | 某个交付版本如何完整取回 | `src/` + `start.bat` + `VERSION` |

```bash
git log --oneline          # 过程历史
git diff                   # 未提交的改动
git status                 # 工作区状态
```

- 提交信息模板：`<类型>(<范围>): <描述>`，如 `feat(web): 节点描述字段与右键动态文案`
- 凡改动 `src/`，**git 提交与 `store.py commit` 成对执行**
- `.gitattributes` 固定 `* -text`：本项目用 SHA-256 指纹校验内容，**任何换行转换都会让指纹全部失配**，故禁止 git 改写换行

## 详细文档

- **接续说明（跨会话交接入口 —— 新会话先读这份）→ `docs/接续说明.md`**
- **工程约定（代码怎么写、规矩怎么立，P0/P1）→ `docs/项目约定.md`**
- 架构、接口、版本流程细则 → `docs/项目手册.md`
- 任务进度（时间线口径）→ `docs/任务进度.md`
- 开发纪律、技术坑点、交付清单 → `docs/错误笔记.md`
- 版本变更明细 → `CHANGELOG.md`
