# 青蔓 QingMan · DSH 环境备忘

> **本文不是接续入口。** 项目交接一律看 `docs/接续说明.md`（§P1-6 **H1「单一入口」**）。
> 本文只记 **DSH 这个运行平台特有**的坑 —— 这些内容对项目本身没有意义，
> 换到别的平台（WorkBuddy / 本机直跑）就不适用。
>
> **定位依据**：H1 禁止另立第二份接续文件。本文刻意**不含**「锚点 / 实况 / 待办」三要素
> （那是 H2 规定的接续说明职责），只做「环境差异说明」，因此不构成第二入口。
>
> 最后更新：2026-10-21（V0.4.0）

---

## 一、两处项目目录（为什么要小心）

DSH 的 workspace 被固定在 `D:\Data\deepseek-harness\default-workspace\QingMan`，
且**沙箱只允许写这个路径**。因此本机有两份工作树：

| | DSH 工作区（**主线**） | 旧存档（只读） |
|---|---|---|
| 路径 | `D:\Data\deepseek-harness\default-workspace\QingMan` | `D:\Data\WorkBuddy\2026-10-09-12-26-55\QingMan` |
| 版本 | **V0.4.0** | V0.3.12 |
| 角色 | 后续开发都在这里 | 历史存档，仅供对照 |

> **权威判断以 `docs/接续说明.md` §1.1 为准** —— 那里有完整的版本差异表与「该用哪个」的判据。
> 本文不重复维护该表，避免两处说法漂移。

---

## 二、沙箱坑 1：`tempfile.mkdtemp()` 建的目录写不进去

**现象**：

```
PermissionError: [Errno 13] Permission denied:
  '...\_qm_tmp\tmpXXXXXXXX\a.txt'
[WinError 5] 拒绝访问
```

`verify.py` / `unittest` / `smoke.py` / `browser_smoke.py` **四个门禁全部**会撞上。

**原因**：Python 的 `tempfile.mkdtemp()` 以 **0700** 建目录，而 DSH 受限沙箱的令牌对该目录
没有写权限。**这不是项目缺陷，是沙箱边界 —— 不要改工具代码。**

**解法**：跑门禁时用 `danger-full-access`（一次授权，比改代码干净）。

---

## 三、沙箱坑 2：控制台是 GBK，特殊符号会崩

**现象**：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2194'
```

`verify.py` 打印带 `↔` 的项名就会挂。

**解法**：每次跑 Python 前设两个环境变量：

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
```

> 相关坑：`py -3 -m py_compile` 会**尝试写 `__pycache__`** 而报 WinError 5。
> 只想查语法时改用 `ast.parse()`（只读），或确保带 `-B`。

---

## 四、wrangler 在沙箱里跑不起来（部署必看）

**现象**：

```
Error: spawn EPERM
  at runWrangler (.../wrangler/bin/wrangler.js:24:9)
```

**原因**：wrangler 启动器用 **`ipc` 通道** spawn 子进程，受限沙箱禁止命名管道。
绕过启动器直接跑 `cli.js` 仍会被 **esbuild 的服务**拦住（同样是 spawn）。

**解法（实测可行）**：直接跑 `wrangler-dist/cli.js` + `--no-bundle`

```powershell
$env:CLOUDFLARE_API_TOKEN='<令牌>'
$env:CLOUDFLARE_ACCOUNT_ID='9b8748b981bb35f5a86ae23842b50305'
$env:ESBUILD_WORKER_THREADS='0'
node .\.wrangler-tool\node_modules\wrangler\wrangler-dist\cli.js `
  pages deploy dist/makers-live-v040 --project-name=qingman --branch=main `
  --commit-dirty=true --no-bundle
```

> **⚠ 2026-10-21 实测补充**：本机 `wrangler@4.151.3` 走 Direct Upload 时，**上传全部 200、创建部署恒 401**
> （`Authentication error [code: 10000]`）。同一个令牌用 `wrangler@3` **一次部署成功** ——
> 令牌权限没问题（`/user/tokens/verify` 为 active、`GET pages/projects/qingman` 为 200）。
> **别把它误判成「令牌缺 Pages:Edit」**：先用 `wrangler@3` 复测，再怀疑权限。
> 另外：`wrangler whoami` 报「Failed to automatically retrieve account IDs」是**最小权限令牌的正常现象**，
> 只要显式传了 `CLOUDFLARE_ACCOUNT_ID` 就不影响部署。
**三个要点**：
- `--no-bundle` 吃掉 esbuild 那一步（纯静态站不需要打包 `_worker.js`）
- **必须**直接指向 `wrangler-dist/cli.js`，**不能**用 `.bin\wrangler.cmd`
- 安装用隔离前缀，**不要全局装**：`npm install wrangler --prefix ./.wrangler-tool`

---

## 五、部署目标（避免建错项目 / 换掉域名）

| 项 | 值 |
|---|---|
| 账号 ID | `9b8748b981bb35f5a86ae23842b50305` |
| Pages 项目 | `qingman`（production 分支 `main`） |
| 项目 ID | `4e3652bb-1e52-4703-9b6e-0cb0e1b991b9` |
| 生产地址 | https://qingman.pages.dev |

**域名不变的原则**：永远部署到**同一个项目 `qingman` 的 `main` 分支**。这样
`https://qingman.pages.dev` 长期有效，用户的书签与已安装 PWA 都不受影响。

> 令牌只走**进程环境变量**，不落盘、不写配置文件。用毕请到面板吊销。

---

## 六、部署后怎么核对（别只看「部署成功」）

```powershell
# 1) 版本号
curl.exe -sS https://qingman.pages.dev/js/demo-data.js | Select-String 'version'
# 2) SW 缓存名（应随 VERSION 变）
curl.exe -sS https://qingman.pages.dev/sw.js | Select-String 'CACHE ='
# 3) 关键文件逐字节比对（最硬的证据）
curl.exe -sS -o live.js https://qingman.pages.dev/js/demo-backend.js
(Get-FileHash live.js -Algorithm SHA256).Hash
(Get-FileHash 'dist/makers-live-v040/js/demo-backend.js' -Algorithm SHA256).Hash
```

三者一致才算真的生效。**Pages 会做路径重写**（`/index.html` → 308 → `/`、
`/help.html` → `/help`），校验内容要跟重定向后的目标，否则会误判「文件缺失」。

---

## 六点五、真机复现（浏览器行为类缺陷）：别用 `--virtual-time-budget`

**现象**：`browser_smoke.py` 那套 `--headless=new --virtual-time-budget=N --dump-dom`
可以驱动页面点击与定时器，但**IndexedDB 的请求回调永远不会触发**（`onsuccess` / `onerror`
都不来）—— 因为 virtual time 毫秒级烧完整段预算，真实 I/O 没有墙钟时间。

**后果**：2026-10-21 复现「选目录后模板没载入」时，探针把「IDB 没走完」表现成了
「列表卡在『正在读取模板库…』」，差点被误判成产品死锁（与《错误笔记》§三「替身不可靠」同源）。

**解法**（实测可行）：真机复现改用 **CDP**，给足真实时间：

```powershell
msedge --headless=new --remote-debugging-port=9333 --user-data-dir=<临时> about:blank
# 然后用 Node（v22+ 自带 global WebSocket）：
#   PUT /json/new?<url> → 连 webSocketDebuggerUrl → Runtime.evaluate 点击 / 读 DOM
```

配套做法：把待测站用 `tools/build_static_site.py` 产出到 `dist/_probe/site`，
再注入一个伪造 `showDirectoryPicker` 的探针脚本（真实 `window`、真实 `fetch` 拦截、
真实 `templates.js`，只有文件系统是替身）。这条链能复现「首次绑定 / 失权重选」等状态。

**清理**：探针会往 `dist/_probe/` 写 Edge profile（含 CR 字节），跑完必删 ——
否则 `verify.py` 的「换行一致性」会把它们逐一点名（`dist/` 虽在 `.gitignore` 里，
但换行守卫扫的是**工作树**，不看 git 忽略）。

---
## 七、其它

- **`sw.js` 缓存名由 `VERSION` 派生**（`qm-static-<VERSION>`）。版本不升，已安装用户的
  service worker 可能继续交付旧 JS —— 所以**行为变更一定要升版**。
- **发布属对外动作**：即使手上有令牌，也要先取得用户明确授权再部署。
- **原始项目目录对 DSH 是只读的**，不能直接把它当 workspace 用。

---

## 状态行

定位：DSH 运行环境备忘（**非**接续入口）｜权威接续：`docs/接续说明.md`｜覆盖：沙箱 tempfile 坑 / GBK 输出坑 / wrangler 绕启动器 / 部署目标与核对法｜**不维护**：版本号、待办、时间线（那些在接续说明与任务进度里）
