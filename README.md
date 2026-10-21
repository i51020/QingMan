# 青蔓 QingMan

本地离线运行的**目录树设计器**：可视化编辑目录树，一键在磁盘上生成真实目录结构。

- 中文名：**青蔓**
- 英文名：**QingMan**
- 当前版本：**V0.4.3**
- 运行环境：Windows 10/11 + Python 3.8+，完全离线，仅监听 `127.0.0.1`
- 实测环境：**Windows 11**（鼠标 + 键盘）。触屏与其他操作系统**未验证**，故不做针对性适配

## 快速开始

```bat
:: 双击项目根目录下的 start.bat 即可
start.bat
```

脚本会自动定位 `src/`、优先用 `py -3`（回退 `python`）启动后端、扫描 8765–8775 端口、打开浏览器。

手动启动（等价）：

```bash
cd src
python -m server
```

### 运行要求（§P2 第 2 项）

| 项 | 要求 |
|---|---|
| Python | **≥ 3.8**（下限；工具层刻意不用 `Path.write_text(newline=…)`，该参数 3.10 才加入）。**门禁基线解释器 = `py -3`**（本机 3.14.8，与 `start.bat` 同口径）—— 校验基线数字以此为准，报数须附解释器 + zlib 指纹，见 `docs/项目约定.md` §编码基线 |
| 浏览器 | **Chromium 内核 ≥ 88**（Edge 88 / Chrome 88 及以上）。界面零 Web 框架、零构建，仅用 **ES2020**（可选链 `?.`、空值合并 `??`），故对浏览器版本要求很低 |
| 网络 | 无需联网。服务**只监听 `127.0.0.1`**，数据不离开本机 |

> **提升浏览器下限的规则**：一旦引入任一 **ES2022+** API（如 `Object.groupBy` / `toSorted` / `findLast`），必须把上表下限提升到该 API 的首次支持版本，并同步 `docs/项目约定.md` §P2 第 2 项。

**快捷键**：`Ctrl / Cmd + S` 立即保存目录树（跳过 800ms 防抖）· `Delete` 删除选中节点 · `F2` 重命名选中节点。完整键位表见帮助页（键位小节由校验守卫把关，引入新键位即强制登记）。

## 目录结构

```
QingMan/
├─ VERSION              版本号唯一来源（内容：V0.0.23）
├─ CHANGELOG.md         版本记录
├─ start.bat            启动入口
├─ README.md            本文件
├─ src/                 主线源码（"当前版本"，只在确认后改动）
│  ├─ web/              前端：index.html（主界面）+ help.html（帮助页）+ support.html（支持页）+ css/ + js/ + assets/
│  │  ├─ assets/        品牌资源：logo.svg（顶栏标记，经 CSS mask 着色）+ sponsor-wechat.png（赞赏码）
│  │  ├─ css/
│  │  │  ├─ tokens.css  设计变量唯一来源（颜色 / 圆角 / 间距 / **字号尺度 `--qm-fs-*`** / 字体族）（**唯一允许出现裸色值与裸字号的文件**）
│  │  │  ├─ base.css    基础元素 + 品牌区（三页共用）
│  │  │  ├─ layout.css  主界面布局
│  │  │  ├─ help.css    帮助页 / 支持页布局
│  │  │  └─ skins/      皮肤契约（README.md）+ 16 款皮肤文件（皮肤 = 一组变量覆盖，组件不感知皮肤 → §P0-3 L5）
│  │  └─ js/
│  │     ├─ main.js     主界面装配层：状态 → 视图 → 交互绑定 → 编辑态自动保存 → 自检
│  │     ├─ help.js     帮助页渲染层：填充占位 → 渲染分节（幂等）→ 取后端版本
│  │     ├─ support.js  支持页渲染层
│  │     ├─ i18n/       取词层：index.js 运行时（t() / applyStatic() / setLocale() / applySkin() / initPrefs() / watchLocale()）
│  │     │              + skins.js 皮肤注册表（语言包已迁至项目根 `locales/`，V0.3.0）
│  │     ├─ core/       bus.js 事件总线 · store.js 状态仓库 · api.js 后端调用唯一入口（其余模块禁用 fetch）· errors.js 错误码本地化
│  │     ├─ modules/    tree-model.js 数据模型：增删改查 / 统计 / id 唯一性 / 文档序列化（纯数据，不碰 DOM 与网络）
│  │     │              selection.js 选择集合语义（V0.0.43 拆出）· templates.js 模板库（V0.0.48 拆出）—— 均为解单文件 64K 上限
│  │     └─ ui/         tree-view.js 目录树 · inspector.js 属性面板 · ctx-menu.js 右键菜单 · toast.js 轻提示
│  │                    lang-picker.js 语言选择 · skin-picker.js 皮肤选择 · launch-icon.js 皮肤联动图标
│  ├─ server/           后端：Python 标准库，零第三方依赖（routes 端点 / templates 模板 / common 助手 / dtree_core 核心 / config 配置）
│  └─ shared/           前后端共享契约：schema.json / error-codes.json
├─ data/                运行时数据：editor.json（编辑态文档；**不进 git**，见 §P0-7）
├─ store/               内容寻址仓库
│  ├─ objects/          blob 池：路径 = 内容的 SHA-256，跨版本自动去重
│  └─ .trash/           checkout 时多余文件的回收区（不真删）
├─ versions/            版本清单（**只增不改**，V0.0.1 … V0.0.51 每版一目录）
│  ├─ V0.0.51/          MANIFEST.json（基线 r1，当前版本）＋ 必要的 MANIFEST-r<N>.json
│  └─ V0.0.1/           MANIFEST.json（基线 r1）+ MANIFEST-r<N>.json（同版本修订）
├─ preview/             试运行区（**只服务单次开发**：`promote` 后即清空，不跨版本保留 —— §P1-7）
│  └─ README.md         用途与规则说明（占位，使目录保留在 git 跟踪内）
├─ locales/             语言包（**内容资产**，V0.3.0 自 src/web/locales 迁出，**不计入代码预算**）
│  ├─ zh-CN.js          中文取词表 + helpSections（LOCALE / NAME / dict / helpSections）
│  ├─ en-US.js          英文取词表（与中文键集零差异）
│  └─ README.md         新增一门语言的契约与步骤
├─ templates/           内置模板库：**仅 `P0_空白项目模板.json`**（+ 运行时 `.trash/` 软删除回收区）
├─ templates-pack/      独立可分发的**模板包**（16 套业务模板 `.md`(主) + `.json`(等价) +
│                       来源说明 + `pack.manifest.json`；**不含** P0 —— 全项目只内置一套空模板）
│                       `QingMan-模板包.zip` 由 `tools/pack_templates.py` 确定性重建，**不入库**
├─ tests/               回归测试网（**13 模块**，标准库 unittest，零第三方依赖 —— §P0-2）
│  ├─ test_dtree_core.py   切分 / 统计 / 文档校验 / check_target(R1–R5) / build_tree(R6–R8)
│  ├─ test_routes.py       生成守卫 / 写入 / 编辑态往返 / 健康 / 模板 CRUD 与覆盖写 / 模板目录选择（打桩不弹框）/ 保真导出
│  ├─ test_config.py       体积上限分层自洽 / 路径与开关派生
│  ├─ test_launch_icon.py  皮肤联动图标上传校验（PNG-in-ICO）
│  ├─ test_store.py        manifest_digest 改名可检出 / parse_ref / 修订链 / fingerprint_diff / is_within
│  ├─ test_versioning.py   bump 三语义（minor 重置 PATCH、major 重置 MINOR+PATCH）
│  ├─ test_handoff.py      实况段渲染（版本/修订 tag 分列 · 语义版本排序 · 时间线日期 · git 状态细分）
│  ├─ test_browser_smoke.py 页面冒烟纯函数（指标解析 / 控制台过滤 / verify_metrics 判定 / sandbox_base）
│  ├─ test_promote.py      list_files 判据（VERSION 单存即算非空）/ 默认源推导
│  ├─ test_smoke.py        sandbox_base（与 browser_smoke 一致）
│  ├─ test_pack_templates.py 模板包：17/17 等价 / 清单 digest 可复算 / zip 确定性 / 孤儿与坏内容拒收
│  └─ test_verify.py       托管 node 取最新（版本键 · 数字排序 · 跳过无 node.exe 目录）
├─ tools/               工具链：store / verify / versioning / release / promote / handoff / smoke /
│                       browser_smoke / pack_templates
├─ legacy/              历史归档，命名 `<对象>-<日期>/`，只增不删
│  ├─ tools-20261009/    改造前的工具备份
│  └─ preview-20261009/  旧编号预览版 V0.01 全量归档（22 文件，git 保留重命名历史）
├─ docs/                项目手册 / 项目约定 / 任务进度 / 错误笔记 / 接续说明 / 审查报告
├─ .git/                过程历史仓库（git，覆盖全项目）
├─ .gitattributes       `* -text` —— 禁止换行转换，保护 SHA-256 指纹
└─ .gitignore           忽略 __pycache__ / store/.trash/ / data/ / 编辑器垃圾
```

## 目录树操作

| 操作 | 方式 |
|---|---|
| 新建子项 / 重命名 / 删除 | 工具栏按钮，或节点**右键菜单**（同一套具名函数，两处共用） |
| 移动节点 | 拖拽节点到目标目录（根节点不可拖）。移动前先过 `canMove()` 校验：不改数据的判断，返回 `true / notDir / cycle / exists / root` —— 自环、目标已存在、拖到根均被拦下 |
| 删除 / 重命名快捷键 | `Delete` 删除选中节点 · `F2` 重命名选中节点（输入态自动让位，不抢键） |
| 撤销 / 重做 | 每步操作入栈（上限 50）。**note 编辑按会话合并**：一次连续编辑只占一格历史，失焦 / 切选中即并为一步 —— 避免逐字符吃光栈 |

## 模板库

模板 = 一棵可复用的目录树（嵌套字典：目录 = `{}`，文件 = 字符串内容），两种等价载体：

| 载体 | 形态 | 定位 |
|---|---|---|
| `.json` | `{name, description, updated, tree}` | 规范格式；**写出**必带 `schemaVersion`，**读取**容忍缺失 |
| `.md` | `# 名称` + `> 描述` + `- 节点/`（每级 2 空格缩进；文件正文用围栏块） | **主分发格式** —— AI / Agent / Skill 可直接读取；与 `.json` **逐节点等价**、可成环（导出 → 再导入） |

**交付形态（V0.0.37 起，V0.2.0 修订）**：工具**只内置 `P0_空白项目模板.json`**（唯一内置空案例）；16 套业务模板在 `templates-pack/` 里**单独打包**（`tools/pack_templates.py --zip <路径>`），**不随发布包分发**（`tools/package_release.py` 的白名单只含 `src/` + `templates/`）。用户拿到模板包后**自行解压进 `templates/`** 即可 —— 列表按扩展名识别，`.json` / `.md` 都认。
**默认落点（V0.2.0）**：未绑定时恒为**程序目录的 `templates/`**；settings 里记录的绑定目录**若已不存在则视为未绑定**（防止移动目录后模板列表永久不可用）。运行态模板库 = **内置层** ∪ **用户绑定目录**（`QM_TEMPLATES_DIR` / settings，见下表）。
**界面形态（V0.0.38 起）**：模板行**无常驻按钮**，全部操作收进**右键菜单** —— 载入 / 重命名 / 复制 / 导出 / 删除；行带**来源徽标**（内置层 / 用户层）；列表每 **2500ms** 轮询刷新（`file+mtime+size` 变化才重渲染）。

| 操作 | 说明 |
|---|---|
| 载入 | 右键菜单「载入」：把该模板的树载入编辑区（不改模板文件） |
| 另存为模板 | 把当前树存为命名模板。**同名默认拒写**（返回 `templateExists`）；用户**显式确认**后带 `overwrite:true` 才覆盖，且旧模板先入 `<模板目录>/.trash/<时间戳>/` 再写新文件 |
| 重命名 | `POST /api/templates/<名称>`：**同时改文件名与文件内 `name` 字段**（两者不一致会让「点了 A 却载入 B」）。旧文件移入回收站保底；**保持原格式**（`.md` 进 `.md` 出） |
| 复制 | 右键菜单「复制」：以当前模板为蓝本另存一份（默认名加 `-copy` 后缀），不覆盖原模板 |
| 删除 | `DELETE /api/templates/<名称>`：**软删除**，移入 `<模板目录>/.trash/<时间戳>/`，不真删 |
| 导入 | `POST /api/templates/import`：`.md` / `.json` 文本 → 归一（**全量校验** + 保持原格式）→ 落用户库；同名默认拒写（界面同名时二次确认） |
| 导出 | `GET /api/templates-export/<名称>[?format=json\|md]`：**不带 `format` ＝ 原文件文本回传（保真，不再序列化）**；带 `format` 时由后端**等价转换**（同一 `render_md_template` / `parse_md_template`，转换前过全量校验）。界面右键给两项：「导出为 .json」「导出为 .md —— 导出的文件可被再次导入（与导入成环） |
| 模板目录绑定 | `GET` / `PUT /api/templates-dir`：绑定「用户模板库」目录，解析优先级 **`QM_TEMPLATES_DIR` env > settings > 默认 `templates/`**；界面用 `POST /api/templates-dir/pick` 弹**原生目录框**（`QM_NO_GUI_PICK=1` 可关断，不可用降级为手动粘贴路径） |
| 实时刷新 | 前端每 **2500ms** 轮询 `GET /api/templates`；签名（`file+mtime+size`）不变则**不碰 DOM**（保住滚动位置 / hover 态）；切后台（`visibilitychange`）暂停 |
| 包校验 / 打包 | `python tools/pack_templates.py`：17 套逐套校验 + 清单（含 sha256）+ 确定性 zip；`--check` 只校验不写盘 |

> 模板目录 **不在版本交付清单内**（同理 `templates-pack/`），故 `list_templates()` 在目录缺失时返回 `available=false` + 空列表（**不报错**）—— 否则预览副本一启动就满屏红。
> `templates-pack/pack.manifest.json` 的 `digest` 与 zip `sha256` **均可独立复算**（规则写在清单的 `digestRule` 字段里，`verify` 按同一规则独立复算一遍）。

## 皮肤与语言（V0.3.0）

**两者都是「外部数据」，不是代码** —— 所以它们都不吃 `src/` 预算。

### 皮肤

| 项 | 现状 |
|---|---|
| 数量 | **16 款**（`src/web/css/skins/s01…s16`），出厂默认 **S16 暖灰·琥珀** |
| 形式 | 每个皮肤文件**只做变量重新赋值**（`--qm-*`），组件 CSS **不感知皮肤**（§P0-3 L5；守卫 7d / 7d-1 双向隔离） |
| 注册 | `src/web/js/i18n/skins.js` 的 `SKINS` 数组：`cid` / `file` / `label`（取词键）/ `swatch`（三色预览） |
| 契约 | `src/web/css/skins/README.md`：变量白名单、`--qm-surface-2` 与 `--qm-surface` 的 CIE L* 落差 ≤1.5 且方向随区制、WCAG AA 配对 |
| 新增一款（**开发操作**） | ① 复制现有皮肤文件改名 `s17-…css`；② 只改色值，**不引入新变量**；③ 在 `SKINS` 加一行 + 语言包加 `skin.17` 名称；④ 跑 `verify`（款数从目录派生，自动纳入对比度/落差判据） |

### 语言

| 项 | 现状 |
|---|---|
| 数量 | **2 个内置包**（zh-CN / en-US）+ 可任意增删的扩展包 |
| 形式 | `locales/<tag>.js`：导出 `LOCALE`（须与文件名一致）/ `NAME`（母语自描述名）/ `dict` / `helpSections` |
| 加载 | 内置两包**静态 import**（首屏同步取词）；扩展包由 `/api/locales.js` 枚举、前端 `import()` 按需加载 |
| 新增一门（**放文件即可**） | 把 `locales/<tag>.js` 放进去 → 刷新即出现在语言选择器；**无需改任何代码** |
| 校验 | 中英键集必须零差异（守卫 7b 家族）；帮助文案不得含 Markdown 标记（7an） |

**为什么语言包要迁出 `src/`**：它们是内容资产，与 `.js/.py` 抢同一个代码预算会让「多写两句文案」变成「挤占代码空间」。
迁出后 `src/` 重新只度量代码复杂度（V0.3.0：`src/` 从 646,726 B 降到 **约 572 K**）。

## 在线版（V0.3.0 · 静态构建）

同一套 `src/web` 可以构建成**在线版**，部署到静态托管后访客用浏览器直接使用：

```bash
py -3 tools/build_static_site.py --out dist/makers-live   # 产出可直接托管的目录
```

在线版与本地版的差别只有一条：**写盘通道**。本地版由 Python 写你填的路径；在线版由浏览器的
File System Access API 写你**点选**的文件夹（需 Edge / Chrome）。草稿存浏览器 `localStorage`，
模板导入导出照常，并可"安装"为 PWA 应用、离线打开。桌面快捷方式 `.lnk` 在线版不提供（无意义），
等价物是 PWA 安装。

在线版没有自己的源代码分支 —— 全部能力都在构建期注入（`js/demo-backend.js`、`js/md-template.js`、
`js/pwa.js` + `sw.js` + `manifest.webmanifest`），`src/` 不感知。详见 **`docs/在线版手册.md`**。

## 安全模型（V0.2.1 审计）

**边界**：服务只 `bind 127.0.0.1`，不监听任何外网接口；无第三方依赖（无供应链面）。

| 威胁 | 处置 | 证据 |
|---|---|---|
| 跨站页面调 API（CSRF） | 写操作须带自定义头 `X-QingMan`；跨站要带它必先过 CORS 预检，而 `do_OPTIONS` 一律 403 | 黑盒：无头 403 / 跨站 Origin 403 / OPTIONS 403 |
| DNS rebinding | `Host` 必须是 `127.0.0.1` / `localhost` / `[::1]`；带 `Origin` 时还须 scheme=http 且端口等于绑定端口 | 黑盒：`Host: evil.com` → 403 |
| 路径穿越（静态 / 模板 / 生成） | 静态：`resolve()` 后必须 `relative_to(web_root)`；模板：文件名白名单 + `is_within` 复核（防符号链接）；生成：`check_target` 黑名单 | 黑盒：`/../VERSION`、`%2e%2e%2f`、`..%5c` 全 403；`templates-export/../../VERSION` 404 |
| 点击劫持 | `X-Frame-Options: SAMEORIGIN` + CSP `frame-ancestors 'self'`（**跨源**全挡；保留同源是给自动化探针用） | 响应头实测 |
| XSS | 前端零 `innerHTML` / `eval`；文案全走 i18n 文本节点；CSP `script-src 'self'`（无 `unsafe-inline`） | 静态扫描 0 命中 + CSP 实测 |
| MIME 嗅探 / Referer 泄露 | `X-Content-Type-Options: nosniff` · `Referrer-Policy: no-referrer` · `Cross-Origin-Resource-Policy: same-origin` | 响应头实测 |
| 信息泄露（指纹） | `Server` 头只报 `QingMan/<版本>`，**不报 Python 版本** | 实测 `Server: QingMan/V0.2.0` |
| 任意文件写入 | `generate` 只写用户指定且通过四类黑名单的目标；模板/图标/编辑态路径全部服务端固定 | 既有判据 + 单测 |
| 任意文件读取 | 无「按路径读文件」的端点：`templates-export` 走白名单，`open-dir` 只认三个枚举标识 | 黑盒：`open-dir` 任意路径 400 |

**明确不防（据实）**：

1. **本机其他进程 / 其他系统用户**可以直接调这套 API —— loopback HTTP **没有身份认证**。同一台电脑上，
   另一个用户的程序能读到 `data/editor.json`、能触发「生成」（目标仍受黑名单限制）。
   这是「本地单机工具」的固有取舍：真正的隔离要靠操作系统账户，而不是应用层口令。
   缓解手段（若确有多人共用一台机器的场景）：各自用独立 Windows 账户，或把程序放进仅自己可读的目录。
2. **本机 DoS**：`ThreadingHTTPServer` 无连接数上限，本地进程可刷请求占用线程。属本地信任边界内。
3. **不防恶意模板内容**：模板只是目录树文本，落盘时按文件名/结构校验，不做「内容是否含恶意路径」的道德审查
   —— 生成目标的黑名单才是唯一的安全边界（`..` 段名会被 `validate_segment` 拒绝）。

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
| 2. 交付校验 | `python tools/verify.py preview/V<版本>` | 主线 **94 项**、预览目录 **89 项**（预览无 `docs/`，少「接续说明实况段」「实况段·版本 tag 行」「实况段·时间线日期」与「源码 § 引用可解析」四项；另无 `tests/`，再少「回归测试网」一项 —— 共少 5；带 `--against` 另加 2 项），不通过不落地 |
| 3. 落地主线 | `python tools/promote.py --from preview/V<版本> --force` | 单向：预览 → 主线，只复制不删除（主线非空时需 `--force`） |
| 4. 提交版本 | `python tools/store.py commit --note "说明"` | 写入 blob 池 + 生成清单（同版本则追加修订） |
| 5. 升级版本号 | 见第 1 步 | 本步实际在**第 1 步之前**就要做（版本号须先升）；此处保留编号只为与 §P0-6 修订机制对照 |

**改主线之前必须先 commit**，否则该版本没有回退点。

**⚠️ 版本号与 `store.py commit` 的配套顺序**：`commit` 打的是**「此刻盘上的 `src/`」+「此刻的 `VERSION`」**这个组合，两者必须已配套。若先把 `VERSION` 升到新版**却尚未落地**，此时执行 `release.py snapshot`（= `store.py commit`）会把**上一版的代码**装进**新版本的清单**。落地前请用 `python tools/verify.py . --against <上一版>` 先确认主线仍等于上一版基线（见 `docs/错误笔记.md` §三.18）。

**改 `src/` 后必跑四件套（§P0-2 T5，V0.0.25 起）**：

```bash
python tools/verify.py .                      # 交付校验（静态）
python -m unittest discover -s tests          # 单元测试
python tools/smoke.py                         # 端到端冒烟（HTTP 层；起真实服务 + 沙盒目录，测完即清）
python tools/browser_smoke.py                 # 页面级冒烟（无头浏览器 21 项；未装浏览器则跳过）
```

四项全过才算完成。单元测试可用 `QM_SRC=<版本根>/src` 指向**预览版**，这样落地前就能过全部门禁。

**改 `templates-pack/` 后另跑**：`python tools/pack_templates.py --check` —— 17 套 `.md`↔`.json` 逐节点等价 + 清单 `digest` 与 zip `sha256` 复算（不写盘）。

> **zip `sha256` 有运行时敏感性**（《错误笔记》§三.78）：zip 字节由 `zlib` 实现决定，`py -3`（3.14.8 / **zlib-ng**）与 3.13（上游 zlib）重建出的字节**不同**（实测 24,270 B vs 24,693 B）。故清单 `zip` 块记了**构建时指纹** `env = {python, zlib}`：`--check` **指纹一致才比绝对 `sha256`**，不一致则降级为**自洽断言**（同一份源连跑两次字节相同）并**显式说明降级** —— 不是跳过，也不会静默放过。
>
> ⚠️ **`--zip <路径>` 会回写 `pack.manifest.json`**（§三.79）：非 `--check` 路径一律"先写清单、再写 zip"，且自定义落点以**绝对路径**记入 `zip.file`（入库清单必须是仓内规范名 `QingMan-模板包.zip`，已由 `unittest` 把关）。**要做跨运行时字节对比，请先把 `templates-pack/` 整体复制到临时目录**（或在代码里用 `build_zip_bytes()` 只读取字节），不要在仓库内直接 `--zip` 到外部路径。

> `browser_smoke.py` 覆盖「**只有页面跑起来才现形**」的那一类缺陷（页面无未捕获异常·无漏翻、帮助页分节渲染幂等、默认示例随语言、支持页完好）—— 这类问题在 `verify` / `unittest` / `smoke` 三项全绿时依然会漏网。它自动探测 Edge/Chrome，可在沙盒内跑（`--keep` 保留现场、`--browser PATH` 指定浏览器）。见 `docs/项目约定.md` §P0-2 T7。

## 编辑态持久化

主界面的目录树**自动保存**到项目根 `data/editor.json`：编辑后防抖 800ms 自动写盘，`Ctrl+S` 可立即保存，顶栏 chip 显示「未保存 / 保存中 / 已保存 HH:MM / 保存失败」。刷新或重开浏览器后自动恢复。

接口：`GET /api/editor`（读取）／`PUT /api/editor`（写入，需防护头）。契约见 `src/shared/schema.json` 的 `editorDocument`；规则见 `docs/项目约定.md` §P0-7。

> 之所以不用 `localStorage`：它按 origin（含**端口**）隔离，而本服务端口是**扫描**出来的、并不固定 —— 端口一变 origin 就变，草稿会静默消失。

## 界面文案与皮肤（§P0-3）

**文案零直写**：界面上的每一句中文都来自语言包 `locales/zh-CN.js` 的取词表，代码里通过 `t(key)` 取；HTML 用 `data-i18n` / `data-i18n-title` / `data-i18n-placeholder` / `data-i18n-aria-label` / `data-i18n-alt` 属性声明键名，加载时由 `applyStatic()` 统一填充。**出厂语言（zh-CN / en-US）静态内置、键集零差异**；**其余语言包放 `locales/<tag>.js`（V0.3.0 起在项目根，**不算代码预算**），后端 `/api/locales.js` 枚举、前端按需 `import()` 动态加载 —— 新增一门语言只需放一个文件，无需改任何代码**（契约与步骤见 `locales/README.md`）。

| 约定 | 内容 |
|---|---|
| key 命名 | `<模块>.<元素>.<语义>`，如 `inspector.title`、`tree.menu.delete`、`toast.saved` |
| 取词运行时 | `src/web/js/i18n/index.js`：`t()` / `applyStatic()` / `setLocale()` / `applySkin()` / `initPrefs()` / `watchLocale()` |
| 颜色 | 组件 CSS **只允许 `var(--qm-*)`**，禁止裸色值；新增变量先在 `tokens.css` 定义（**唯一允许写色值的文件**） |
| 字号 | 组件 CSS 字号**只允许 `var(--qm-fs-*)`**（V0.0.51@r10 起）：`tokens.css` 定 **9 档尺度**（`--qm-fs-3xs` 9px … `--qm-fs-3xl` 16px），组件不得写裸 `font-size`（含 `1rem` / `inherit`），守卫 **7c-1**，覆盖面含 `skins/`。⚠️ **L4 的强制范围已据实收窄为「色值与字号」**（2026-10-17 裁定：「丙」不机器化）—— 间距 / 描边 / 圆角等尺寸档位**不做机器化**（《项目约定》§P2 第 44 项） |
| 皮肤形态 | 皮肤文件**顶层只许 `:root` + `--qm-*` 声明**（V0.0.51@r10 后续起）：不得写组件选择器（`.btn` / `[data-qm-skin=…]`）、不得写非 `--qm-*` 声明 —— 与「组件 CSS 不感知皮肤」**方向相反**，合起来才是**双向隔离**；守卫 **7d-9**，现状 16 款零违规 |
| 皮肤 | 皮肤 = **一组变量覆盖文件** `src/web/css/skins/<name>.css`（已内置 **16 款**；出厂默认 **S16 暖灰·琥珀**），经 `applySkin()` 注入 `<link id="skinLink">`。**组件 CSS 不得感知皮肤**（不写 `.skin-dark .btn` 这类选择器） |
| 偏好 | `localStorage` 的 **4 键**（权威清单 ＝ 《项目约定》§P0-3 L6）：`qm.lang` / `qm.skin` / `qm.inspMode` / `qm.launchIcon`；启动顺序 `initPrefs()` → `applyStatic()` → `renderGenBar()` → `render()` |
| ⚠️ 新增偏好键 | 必须声明在 `i18n/index.js`（**导出常量**），不能写在别的模块里 —— 「取词键闭包」检查会排除 `i18n/` 目录，而把 JS 里任何 `a.b` 形式的字面量都当成取词键，写在别处会被误判为"漏翻" |
| SVG 着色 | 一律 ① CSS `mask` 取形状 或 ② 内联 `currentColor`。**禁止 `<img src="*.svg">`** —— `<img>` 中的 SVG 是独立文档，`currentColor` 不继承 |

以上七条外加 L7/L8，由 `verify.py` 的 **15 项**守卫（名称含 `§P0-3`；判项名去重后以 AST 取 `check()` 第 2 实参复核）逐条把关。

## 中栏：生成参数区可折叠

中栏顶部的三个生成参数（根文件夹名 / 目标位置 / 仅演练）是**"一个项目设一次"的低频项**，却长期占据一整行。**V0.0.6 起可折叠**：收起后只留一行摘要，形如

```
▶ 目标 E:\我的项目 · 根名 我的项目 · 演练中
```

| 行为 | 说明 |
|---|---|
| 形态 | **常显，不可折叠**（V0.0.51@r9 撤销折叠）。摘要行是常驻**状态行**（`<p id="genSummary">`），不是开关 |
| 为何撤销 | 折叠态原持久化于 `qm.genBar` 且**永久记住** —— 用户随手一收，此后每次打开「目标位置」整行连同「选择目录」按钮都不见了，像功能消失。参数区只占一行，省下的高度不值这个风险 |
| 摘要实时刷新 | `#inTarget` 的 `input`、`#inDryRun` 的 `change` 都会重画摘要行；根名改变由 `doRename` 直接刷新 |
| 摘要的用途 | 生成前**核验句**：会建到哪（目标位置）· 建成什么名字（根名 / 不建根）· 演练还是写盘 |
| 兜底 | 目标位置为空时点「一键生成」→ 提示并聚焦输入框（参数区恒可见，无需再"自动展开"） |

**参数留在原位、不迁右栏的理由**（裁定记录见 `docs/项目约定.md` §P2 第 15 项）：三项是**作业级（job-scoped）可编辑参数**，而右栏是**选中节点级（selection-scoped）只读属性** —— `inspector.render()` 在无选中时**整栏清空为 `—`**，与"目标位置是必填项、必须始终可编辑"直接冲突。参数项增至 6+ 时再评估迁移，届时须在右栏**单开「生成设置」分区**且**不随选中清空**。

## 存储机制

采用**内容寻址存储**（借鉴 Git 思路）：

- `store/objects/<sha256前2位>/<sha256>` —— 文件内容按 SHA-256 存放，**相同内容只存一份**，跨版本自动去重
- `versions/<版本>/MANIFEST.json` —— 版本**基线**（修订 r1）：「路径 → 指纹」映射 + 元数据（时间 / 父版本 / 说明 / 清单摘要）
- `versions/<版本>/MANIFEST-r<N>.json` —— 同版本**后续修订**（r2、r3…），任何已有清单都不覆盖

早期实测数据（去重效果）：`V0.0.1@r3` → `V0.0.2` 的 26 个文件里**新增 11 个 blob、复用 15 个**（对象池 35 → 46）；`V0.0.2` → `V0.0.3` 的 27 个文件里**新增 6 个 blob、复用 21 个**；`V0.0.4` → `V0.0.5` 的 29 个文件里**新增 13 个 blob、复用 16 个**；`V0.0.5` → `V0.0.6` 的 29 个文件里**新增 6 个 blob、复用 23 个**。最新版本的实际去重数可在 `python tools/store.py log` 与对应 `MANIFEST.json` 中查看。

| 命令 | 作用 |
|---|---|
| `python tools/store.py commit --note "说明"` | 提交当前 `src/` 状态；同版本已有清单时**追加修订** |
| `python tools/store.py checkout <版本[@rN]>` | 回退到指定版本／修订 |
| `python tools/store.py log` | 列出版本链（同版本内按修订倒序） |
| `python tools/store.py diff <版本[@rN]> <版本[@rN]>` | 输出 改动 / 新增 / 缺失 |
| `python tools/store.py fsck` | 校验对象池完整性 |

## 回退

```bash
python tools/store.py checkout V0.0.51        # 取当前版本（= 该版本最高修订）
python tools/store.py checkout V0.0.1@r1      # 精确回退到某个修订
python tools/verify.py . --against V0.0.51    # 与当前版本清单比对
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
- 手册的历史注记存档（V0.0.27→V0.0.51，不追改）→ `docs/项目手册_沿革注记_20261017.md`
- 任务进度（时间线口径）→ `docs/任务进度.md`
- 开发纪律、技术坑点、交付清单 → `docs/错误笔记.md`
- 版本变更明细 → `CHANGELOG.md`
