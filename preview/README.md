# preview/ · 试运行区

本目录存放**开发期的试运行副本**。它不是交付物，随时可清空、可重建。

## 用途

`preview/V<版本>/` 是待落地版本的临时工作副本，开发与校验都在这里做完，再由
`tools/promote.py` 落地到主线 `src/`。

**关键事实**：preview 里的内容**不是独有信息** —— 同一份内容必然已被
`tools/store.py commit` 写进对象池（`store/objects/`），并已被 git 跟踪。
因此清空 preview **不会丢失任何东西**。

## 规则（详见 `docs/项目约定.md` §P1-7）

| 编号 | 规则 |
|---|---|
| R1 | **只服务当前一次开发**：`promote` 落地后即清空，**不跨版本保留**（不长期并存多个版本副本） |
| R2 | 删除统一用 **`git rm -r`**，不用 `rm -rf`；需要时用 `git checkout <commit> -- preview/` 取回 |
| R3 | **不归档进 `legacy/`** —— `legacy/` 只收「不可再生的历史证据」（工具快照、旧编号预览） |
| R4 | 对照旧版请用 `python tools/store.py checkout <版本>`，不靠 preview 残留 |
| R5 | 本目录**保留在 git 跟踪内**（靠本文件占位），**禁止**写入 `.gitignore` —— 试错期需要版本保护 |

## 现状

**（2026-10-09）已按上述规则清空**，共两次：

| 次序 | 时间 | 清空对象 | 内容去向 |
|---|---|---|---|
| 首次 | 21:36–21:46 | `V0.0.2/`（26 文件）、`V0.0.3/`（27 文件） | git（`b51a121` 之前）+ store 对象池（52 blob） |
| 第二次 | 22:18–22:22 | `V0.0.4/`（27 文件）、`V0.0.5/`（29 文件） | git（`319a17d` / `ed45548`）+ store 对象池（73 blob） |

第二次清空前逐项核验过：两个副本与 `versions/<版本>/MANIFEST.json` 的 sha256 **逐字节一致**（27/27、29/29），
且全部 blob 在对象池中，另存独立备份于 `D:\Data\WorkBuddy\_sandbox\qingman_preview_backup_20261009\`。

**删除后本目录仅保留本文件**（R5 要求的占位，使 `preview/` 仍在 git 跟踪内）。

## 下次开发时怎么建

```bat
python tools\release.py bump --kind patch      :: 先升版
mkdir preview\V<新版本>
xcopy /E /I src preview\V<新版本>\src
copy start.bat preview\V<新版本>\
echo V<新版本> > preview\V<新版本>\VERSION
```

完整五步流程见 `README.md`「开发流程」一节。
