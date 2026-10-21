<!-- dsh-context-guard:begin session-3a8d544a-d986-4175-8e2b-12c6a31b25b5 -->

### 交接（人工结论 · 2026-10-21 15:35 · V0.4.5）

> 上方机器的「自动交接草稿」已按规程折进本节并删除（它只有机器事实、没有结论，
> 留着只会误导后来者把旧快照当现状）。**项目接续的唯一入口仍是 `docs/接续说明.md`**；
> 本节只回答「这一轮到底发生了什么、下次从哪继续」。

---

#### 一 · 这一轮做了什么

用户报障：**「在线实测选择一个目录作为模板库后，模板文件没有载入」**（第 5 次同类报障）。

前四轮（V0.4.1 → V0.4.4）都是读代码推浏览器权限语义，三次改错方向。本轮**先建真机复现链**
再动手：`build_static_site.py` 产出在线版 → 注入伪造 `showDirectoryPicker` 的探针 →
**无头 Edge + CDP** 驱动真实页面（点击 `#btnPickDir`，抓 DOM 与全部 `/api/templates*` 往返）。

复现出**两个真缺陷**，均已在 V0.4.5 修掉：

| # | 缺陷 | 真机表现 |
|---|---|---|
| 1 | `PUT /api/templates-dir` 用 `handle.name === wantDir` **按名字短路**，不调 `commitDir` | 刷新后句柄失权 → 用户重选**同一个**文件夹 → picker 返回的同名**新句柄被丢弃**，继续用失权的旧句柄 ⇒ **永远 403**，重选多少次都没用（这正是「改了几次仍不能用」的根因） |
| 2 | 目录分支列表项漏 `dirs`/`files`；解析失败的文件混进可载入列表 | 每行「undefined 目录 · undefined 文件」；坏件列成点了就报错的「模板」，原因不说 |

修法：判据改为「**有没有待定句柄**」；列表走 `scanDirTemplates`（回传 `dirs`/`files` 与
`skipped`）；新增 `POST /api/templates-dir/grant` + 列表里一颗「**重新授权**」按钮
（`requestPermission` 只在该点击手势里调用，仅在线版渲染，本机版行为不变）。

**门禁**：`verify` 121/0 · `unittest` **624 OK** · `smoke` 35/0 · `browser_smoke` 39/0。
**真机**：场景 A（首次绑定）与场景 B（失权后重选同名目录）在**最终发布产物**上均绿。

---

#### 二 · 踩过的坑（下次别重犯）

1. **`--virtual-time-budget` 下 IndexedDB 永不回调**（`onsuccess`/`onerror` 都不来）。
   我第一次用 `browser_smoke` 那套跑，看到列表卡在「正在读取模板库…」，差点误判成死锁。
   **真机复现浏览器行为必须用 CDP + 真实时间**（已写入 `docs/DSH环境备忘.md` §六点五）。
2. **无头 Edge 在受限沙箱下起不来**（`mojo platform_channel: 拒绝访问` = 命名管道被禁）。
   跑浏览器类门禁/探针要 `danger-full-access`；`tempfile.mkdtemp()` 的 0700 目录同理。
3. **探针会往 `dist/_probe/` 写 Edge profile**（含 CR 字节）—— 跑完必须删，否则
   `verify` 的「换行一致性」会逐文件点名（它扫工作树，不看 `.gitignore`）。
4. **「同名 = 同一个句柄」是错的**：浏览器恢复授权时，同一个文件夹会给出**名称相同、
   权限不同**的新句柄。任何「按名字就认定已经是它」的短路都必须改成「看有没有新句柄」。
5. **新增 Node 侧单测替身时别忘了注入序**：`readDirTemplates` 现在会解析 `.md`，
   而 `md-template.js` 必须**先载入**（线上注入序也是它在前）。`test_online_store`
   原先只喂 `online-store.js`，改完立刻红 —— 那是替身缺件，不是产品缺陷。

---

#### 三 · 未做完 / 下一步

1. ⏳ **V0.4.5 尚未部署**。产物已构建并真机验证：`dist/makers-live-v045`（66 文件 /
   18.2 MB，内置便携包）。部署属**对外动作**，且本机**没有** Cloudflare 令牌
   （上一枚已在对话中明文出现、建议吊销）。需要用户：① 明确授权部署；② 提供新令牌。
   命令见 `docs/DSH环境备忘.md` §四（`wrangler-dist/cli.js pages deploy … --no-bundle`）。
   部署后按 §六 核对：`js/demo-data.js` 的 version、`sw.js` 的 `CACHE`、以及
   `js/demo-backend.js` **SHA256 与 `dist/makers-live-v045` 同名文件逐字节一致**。
2. **用户侧确认口径**：装过 PWA 的浏览器可能仍加载旧缓存（SW 是网络优先，正常会自愈）；
   若仍异常，先 Ctrl+Shift+R 强刷，再看控制台 `request failed:` 的具体 code。
3. `HANDOVER.md` 是 `dsh-context-guard` 插件生成物，**仍未纳入 git**。
   是否入库 / 加 `.gitignore` 依旧待定（本会话沿用「不入库」的现状）。
4. 令牌：本会话**没有**使用任何 Cloudflare 令牌（全程未联网部署）。

<!-- dsh-context-guard:end -->
