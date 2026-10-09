# 青蔓 QingMan

本地离线运行的**目录树设计器**：可视化编辑目录树，一键在磁盘上生成真实目录结构。

- 中文名：**青蔓**
- 英文名：**QingMan**
- 当前版本：**V0.0.1**（最小可运行骨架）
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

## 目录结构

```
QingMan/
├─ VERSION              版本号唯一来源（内容：V0.0.1）
├─ CHANGELOG.md         版本记录
├─ start.bat            启动入口
├─ README.md            本文件
├─ src/                 主线源码（"当前版本"，只在确认后改动）
│  ├─ web/              前端：index.html（主界面）+ help.html（帮助页）+ css/ + js/
│  │  └─ js/i18n/       取词表：zh-CN.js（帮助页正文的唯一数据源）
│  ├─ server/           后端：Python 标准库，零第三方依赖
│  └─ shared/           前后端共享契约：schema.json / error-codes.json
├─ store/               内容寻址仓库
│  ├─ objects/          blob 池：路径 = 内容的 SHA-256，跨版本自动去重
│  └─ .trash/           checkout 时多余文件的回收区（不真删）
├─ versions/            版本清单
│  ├─ V0.0.1/           MANIFEST.json（基线 r1）+ MANIFEST-r<N>.json（同版本修订）
│  └─ V0.01/            旧编号全量快照（历史遗留，原样保留）
├─ preview/             试运行区（**按需新建** `preview/V<版本>/`，平时为空）
├─ templates/           17 套中文目录树模板（内容资产）
├─ tools/               工具链：store / verify / versioning / release / promote
├─ legacy/              历史归档，命名 `<对象>-<日期>/`，只增不删
│  ├─ tools-20261009/    改造前的工具备份
│  └─ preview-20261009/  旧编号预览版 V0.01 全量归档（22 文件，git 保留重命名历史）
├─ docs/                项目手册 / 项目约定 / 任务进度 / 错误笔记
├─ .git/                过程历史仓库（git，覆盖全项目）
├─ .gitattributes       `* -text` —— 禁止换行转换，保护 SHA-256 指纹
└─ .gitignore           仅忽略 __pycache__ / store/.trash/ / 编辑器垃圾
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
| 1. 预览开发 | — | 按需新建 `preview/V<版本>/` 试跑，主线不受影响 |
| 2. 交付校验 | `python tools/verify.py preview/V<版本>` | **36 项**校验，不通过不落地 |
| 3. 落地主线 | `python tools/promote.py --from preview/V<版本>` | 单向：预览 → 主线，只复制不删除 |
| 4. 提交版本 | `python tools/store.py commit --note "说明"` | 写入 blob 池 + 生成清单（同版本则追加修订） |
| 5. 升级版本号 | `python tools/release.py bump --kind patch` | 或 `minor` / `major`；不升版则跳过本步 |

**改主线之前必须先 commit**，否则该版本没有回退点。

## 存储机制

采用**内容寻址存储**（借鉴 Git 思路）：

- `store/objects/<sha256前2位>/<sha256>` —— 文件内容按 SHA-256 存放，**相同内容只存一份**，跨版本自动去重
- `versions/<版本>/MANIFEST.json` —— 版本**基线**（修订 r1）：「路径 → 指纹」映射 + 元数据（时间 / 父版本 / 说明 / 清单摘要）
- `versions/<版本>/MANIFEST-r<N>.json` —— 同版本**后续修订**（r2、r3…），任何已有清单都不覆盖

实测数据：V0.0.1 → V0.0.2 的 23 个文件里**只新增 3 个 blob、复用 20 个**（对象池 22→25，而非 45）。

| 命令 | 作用 |
|---|---|
| `python tools/store.py commit --note "说明"` | 提交当前 `src/` 状态；同版本已有清单时**追加修订** |
| `python tools/store.py checkout <版本[@rN]>` | 回退到指定版本／修订 |
| `python tools/store.py log` | 列出版本链（同版本内按修订倒序） |
| `python tools/store.py diff <版本[@rN]> <版本[@rN]>` | 输出 改动 / 新增 / 缺失 |
| `python tools/store.py fsck` | 校验对象池完整性 |

## 回退

```bash
python tools/store.py checkout V0.0.1         # 取该版本最高修订
python tools/store.py checkout V0.0.1@r1      # 精确回退到基线修订
python tools/verify.py . --against V0.0.1     # 与最高修订清单比对
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

- **工程约定（代码怎么写、规矩怎么立，P0/P1）→ `docs/项目约定.md`**
- 架构、接口、版本流程细则 → `docs/项目手册.md`
- 任务进度（时间线口径）→ `docs/任务进度.md`
- 开发纪律、技术坑点、交付清单 → `docs/错误笔记.md`
- 版本变更明细 → `CHANGELOG.md`
