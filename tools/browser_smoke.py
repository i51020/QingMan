"""青蔓 QingMan · 无头浏览器冒烟（§P0-2 T7，V0.0.25）。

把「**页面跑起来才现形**」的那一类缺陷固化为常驻脚本。与相邻两件工具的分工：

  * `tools/verify.py` —— 静态交付校验（语法 / 结构 / 指纹 / 守卫），不跑页面；
  * `tools/smoke.py`  —— HTTP 层端到端（接口语义，不需要浏览器）；
  * 本脚本            —— **运行时页面层**：真实浏览器加载真实页面，验证渲染与交互。

背景（全项目审查 `docs/审查报告_架构与逻辑_20261010.md`）：P1-1（帮助页每次切语言
成倍追加分节）与 P1-2（首屏默认示例不随语言且被永久落盘）两处缺陷**实测确认时
三项门禁（verify / unittest / smoke）全绿** —— 它们只在页面真正跑起来时才现形。
本脚本把它们变成常态守卫，而不是靠一次性的临时探针。

校验项：
  1. 探针完成（浏览器确实跑到最后一步并写出结果行）
  2. 页面载入无未捕获异常 / 无漏翻 / 无请求失败（扫浏览器控制台日志）
  3. 主界面·默认示例随语言（英文偏好下节点名必须为英文，无中文）
  4. 主界面·皮肤样式表已装载、模板库已接入（首屏两条异步链跑通）
  5. 帮助页·分节渲染幂等（切换语言后分节/导航计数不得累积；P1-1 回归位）
  6. 帮助页·语言切换联动 `<html lang>`
  7. 帮助页·版本徽标 = `VERSION` 且后端可达（`help-stale` 已摘除）
  8. 支持页·V0.0.18 拆页后仍完好

用法：
    python tools/browser_smoke.py [--keep] [--browser PATH] [--sandbox DIR]
                                  [--port N] [--budget MS]

退出码：0 全部通过（**未检测到浏览器则跳过并返回 0**）；1 存在失败项。

约定（§P0-2 T6）：
  * 全程在沙盒内进行 —— 复制 `src/`（与 `VERSION`、`templates/`）到沙盒后再起服务。
    原因：`config.DATA_DIR` 恒为 `<项目根>/data`，直接跑真实 `src/` 时首屏默认示例会
    经 `saveNow()` 写进**真实** `data/editor.json`。
  * 探针页写在**沙盒副本**的静态目录里，随沙盒一并清除，不落入主线。
  * 浏览器用户数据目录也落在沙盒内，localStorage 不污染本机浏览器配置。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

RESULTS: list[tuple[bool, str, str]] = []

# 控制台日志里**致命**的 token：命中即判定页面行为异常。
# `Uncaught`      —— 未捕获异常（脚本抛错 / 模块加载失败）；
# `[i18n] missing key` —— 漏翻（取词表缺键，界面会直接显示键名）；
# `[QingMan] request failed` —— 前端请求失败（接口或接线出错）。
# 注：`[QingMan] launch icon upload skipped` / `logo.svg unavailable` 属「尽力而为」的
# 装饰性动作，在无头环境下本就可能失败，**不计入失败**，仅在备注里提示。
FATAL_CONSOLE = ("Uncaught", "[i18n] missing key", "[QingMan] request failed")

# 探针启动时自报的一条日志 —— 用作「控制台日志通道可用」的**正面控制**（§P2-13）：
# 收得到它，才证明 `--enable-logging=stderr` 确实在投递；否则「无未捕获异常」的 PASS 不可信。
SELF_REPORT = "[qm-smoke] probe-boot"

BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

PROBE_NAME = "_probe_ui.html"

# 探针页：同源 iframe 驱动**真实页面**（不复制页面骨架，测的就是线上那份）。
# 全程事件驱动（iframe onload + setTimeout 轮询），不用 Promise 链 ——
# 无头浏览器的 `--virtual-time-budget` 不等待未决 Promise（经验教训）。
PROBE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>QingMan browser smoke probe</title>
</head>
<body>
<div id="out">START</div>
<script>
var out = document.getElementById('out');
console.log('[qm-smoke] probe-boot');   /* 正面控制：证明控制台日志通道确实在投递（§P2-13） */
var m = {};
var CJK = /[\\u4e00-\\u9fff]/;

function names(doc) {
  var list = doc.querySelectorAll('.tree-name');
  var arr = [];
  for (var i = 0; i < list.length; i += 1) { arr.push(list[i].textContent); }
  return arr;
}

function frame(url, probe, done) {
  var f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;left:-9999px;top:0;width:1100px;height:820px;border:0';
  f.onload = function () {
    var n = 240;
    (function tick() {
      var doc = f.contentDocument;
      var ok = false;
      try { ok = Boolean(doc) && Boolean(probe(doc)); } catch (e) { ok = false; }
      if (ok) { return done(doc); }
      if (n <= 0) { return done(doc); }
      n -= 1;
      setTimeout(tick, 25);
    }());
  };
  f.src = url;
  document.body.appendChild(f);
}

/* 阶段 1：英文偏好下的首屏默认示例（P1-2 回归位）。
   先写偏好再建 iframe —— localStorage 与 iframe 同源共享，页面启动即读到 en-US。 */
try { localStorage.setItem('qm.lang', 'en-US'); } catch (e) {}
try { localStorage.removeItem('qm.skin'); } catch (e) {}

frame('./index.html', function (doc) {
  return doc.querySelectorAll('.tree-row').length > 0
    && doc.querySelectorAll('#templateList li').length > 0;
}, function (doc) {
  try {
    m.htmlLang = doc ? doc.documentElement.lang : '';
    m.idxRows = doc ? doc.querySelectorAll('.tree-row').length : -1;
    m.idxCjk = names(doc).filter(function (s) { return CJK.test(s); }).length;
    m.idxSkin = doc && doc.getElementById('skinLink') ? 1 : 0;
    m.tplRows = doc ? doc.querySelectorAll('#templateList li.tpl-row').length : -1;
  } catch (e) { m.err1 = String(e && e.message ? e.message : e); }
  phase2();
});

/* 阶段 2：帮助页分节幂等（P1-1 回归位）+ 语言切换 + 版本徽标。
   探针只等「后端实测值已回来」（help-stale 摘除），随后用页面自己的语言下拉驱动切换 ——
   走的是真实用户路径（select change → setLocale → qmlocalechange → renderSections）。 */
function phase2() {
  frame('./help.html', function (doc) {
    var cell = doc.getElementById('aboutVersion');
    return doc.querySelectorAll('.help-section').length > 0
      && Boolean(cell) && !cell.classList.contains('help-stale');
  }, function (doc) {
    try {
      m.secBefore = doc.querySelectorAll('.help-section').length;
      m.navBefore = doc.querySelectorAll('#helpNavList li').length;
      var chip = doc.getElementById('helpChipVersion');
      m.chip = chip ? chip.textContent : '';
      var cell = doc.getElementById('aboutVersion');
      m.stale = cell ? (cell.classList.contains('help-stale') ? 1 : 0) : -1;
      var sel = doc.getElementById('helpLangSelect');
      m.hasSelect = sel ? 1 : 0;
      if (sel) {
        sel.value = 'en-US';
        sel.dispatchEvent(new Event('change'));
        m.secEn = doc.querySelectorAll('.help-section').length;
        m.langEn = doc.documentElement.lang;
        sel.value = 'zh-CN';
        sel.dispatchEvent(new Event('change'));
        m.secZh = doc.querySelectorAll('.help-section').length;
        m.navZh = doc.querySelectorAll('#helpNavList li').length;
        m.langZh = doc.documentElement.lang;
      }
    } catch (e) { m.err2 = String(e && e.message ? e.message : e); }
    phase3();
  });
}

/* 阶段 3：支持页（V0.0.18 从帮助页拆出，应保持完好） */
function phase3() {
  frame('./support.html', function (doc) {
    return doc.querySelectorAll('.help-qr').length > 0;
  }, function (doc) {
    try {
      m.qr = doc.querySelectorAll('.help-qr').length;
      m.thanks = doc.querySelectorAll('.help-thanks').length;
    } catch (e) { m.err3 = String(e && e.message ? e.message : e); }
    var parts = [];
    for (var k in m) {
      if (Object.prototype.hasOwnProperty.call(m, k)) { parts.push(k + '=' + m[k]); }
    }
    out.textContent = 'RESULT ' + parts.join(' | ');
  });
}
</script>
</body>
</html>
"""


def check(ok: bool, name: str, note: str = "") -> None:
    RESULTS.append((bool(ok), name, note))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_browser(explicit: str | None) -> str | None:
    """按 `--browser` → 环境变量 `QM_BROWSER` → 常见安装路径 → PATH 的顺序探测。"""
    for candidate in (explicit, os.environ.get("QM_BROWSER")):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    for name in ("msedge", "msedge.exe", "chrome", "chrome.exe", "chromium", "chromium.exe"):
        hit = shutil.which(name)
        if hit:
            return hit
    return None


def browser_drivable(path: str, timeout: float = 25.0) -> tuple[bool, str]:
    """前置探测：该可执行文件能否被**无头驱动**（`--dump-dom` 是否产出 DOM）。

    像夸克这类「启动器语义」的 exe，命令行契约不转发 —— `--headless=new --dump-dom`
    会静默退出、stdout 为空。那属于**环境不支持**，应显式跳过，而非判成
    「探针完成 FAIL」（把环境问题误读成页面缺陷，§P2-11）。
    """
    with tempfile.TemporaryDirectory(prefix="qm_browser_probe_") as prof:
        try:
            proc = subprocess.run(
                [path, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
                 f"--user-data-dir={prof}", "--dump-dom", "about:blank"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"无法启动：{exc}"
    if not (proc.stdout or "").strip():
        return False, "headless `--dump-dom` 无任何输出（疑似启动器语义 / 非 Chromium）"
    return True, ""


def sandbox_base() -> Path:
    """`--keep` / `--sandbox` 缺省时的沙盒父目录（§P2-10：不再硬编码绝对盘符路径）。

    环境变量 `QM_SANDBOX` 优先；否则取**项目根的上两级**下的 `_sandbox/`
    —— 与历史约定 `D:/Data/WorkBuddy/_sandbox` 等价，但随项目位置自动跟随。
    """
    env = os.environ.get("QM_SANDBOX", "").strip()
    return Path(env) if env else (PROJECT_ROOT.parent.parent / "_sandbox")


def wait_health(port: int, seconds: float) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.3)
    return False


def as_int(value, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_metrics(stdout: str) -> dict[str, str] | None:
    """从 `--dump-dom` 的输出里取探针写下的 `RESULT k=v | k=v` 行。

    锚定到探针的输出容器 —— 脚本源码里也有 `'RESULT '` 这个字面量，
    宽松匹配会连源码一起命中（实测：会把 `RESULT ' + parts.join(...)` 捞进来）。
    §P2-12：**已去掉宽松兜底分支** —— 只认 `<div id="out">RESULT …</div>`；
    取不到锚定的结果行即返回 None（宁可 FAIL，也不捞源码字面量假通过）。
    """
    match = re.search(r'<div id="out">RESULT ([^<]*)</div>', stdout)
    if not match:
        return None
    metrics: dict[str, str] = {}
    for part in match.group(1).split("|"):
        key, sep, value = part.strip().partition("=")
        if sep:
            metrics[key.strip()] = value.strip()
    return metrics or None


def console_lines(stderr: str, origin: str) -> list[str]:
    """浏览器控制台日志中**属于本项目页面**的那几行。

    必须过滤两类噪声，否则「无未捕获异常」这一项会被污染：
      * `chrome-extension://` / `devtools://` —— 浏览器自身扩展的日志
        （实测：本机 Edge 的 ProtocolLaunch 扩展每次都会打一条）；
      * 非本服务 origin 的来源 —— 只认 `<origin>/...`，即探针页与其同源 iframe。
    """
    picked = []
    for line in stderr.splitlines():
        if "INFO:CONSOLE" not in line and "ERROR:CONSOLE" not in line:
            continue
        if "chrome-extension://" in line or "devtools://" in line:
            continue
        if origin and f"source: {origin}" not in line:
            continue
        picked.append(line)
    return picked


def run_browser(browser: str, url: str, profile: Path, budget: int, timeout: float):
    args = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--enable-logging=stderr",          # 让未捕获异常 / 漏翻告警可见（本脚本的核心抓手）
        f"--user-data-dir={profile}",
        f"--virtual-time-budget={budget}",
        "--dump-dom",
        url,
    ]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return proc.stdout or "", proc.stderr or "", proc.returncode


def verify_metrics(metrics: dict[str, str], expected_version: str, expect_templates: bool) -> None:
    console_free = metrics.get("htmlLang") == "en-US"
    rows = as_int(metrics.get("idxRows"))
    cjk = as_int(metrics.get("idxCjk"))
    check(console_free and rows >= 5 and cjk == 0,
          "主界面·默认示例随语言",
          f"lang={metrics.get('htmlLang')} 节点 {rows} 行 / 含中文名 {cjk} 个"
          + ("" if cjk == 0 else "（P1-2 回归：示例未随语言）"))

    check(as_int(metrics.get("idxSkin")) == 1, "主界面·皮肤样式表已装载",
          f"skinLink={'有' if as_int(metrics.get('idxSkin')) == 1 else '无'}")

    if expect_templates:
        tpl = as_int(metrics.get("tplRows"))
        check(tpl >= 1, "主界面·模板库已接入", f"模板行 {tpl} 条")

    sec_before = as_int(metrics.get("secBefore"), 0)
    sec_en = as_int(metrics.get("secEn"), 0)
    sec_zh = as_int(metrics.get("secZh"), 0)
    nav_before = as_int(metrics.get("navBefore"), 0)
    nav_zh = as_int(metrics.get("navZh"), 0)
    stable = (sec_before > 0 and sec_before == sec_en == sec_zh and nav_before == nav_zh)
    check(stable, "帮助页·分节渲染幂等",
          f"分节 {sec_before} → {sec_en} → {sec_zh}" + (f"（导航 {nav_before}/{nav_zh}）")
          + ("" if stable else "，计数不一致 —— 语言切换在累积（P1-1 回归）"))

    check(metrics.get("langEn") == "en-US" and metrics.get("langZh") == "zh-CN",
          "帮助页·语言切换联动 html lang",
          f"en-US → {metrics.get('langEn')} / zh-CN → {metrics.get('langZh')}")

    chip = metrics.get("chip", "")
    stale = as_int(metrics.get("stale"), -1)
    check(chip == expected_version and stale == 0,
          "帮助页·版本徽标 = VERSION（后端可达）",
          f"徽标 {chip or '(空)'} vs VERSION {expected_version}；"
          f"后端标注 {'陈旧' if stale != 0 else '正常'}")

    qr = as_int(metrics.get("qr"), 0)
    thanks = as_int(metrics.get("thanks"), 0)
    check(qr == 1 and thanks == 1, "支持页·拆页后完好",
          f".help-qr={qr} .help-thanks={thanks}")


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 无头浏览器冒烟")
    parser.add_argument("--browser", default=None, help="浏览器可执行文件路径（缺省自动探测 Edge/Chrome）")
    parser.add_argument("--port", type=int, default=0, help="0 = 自动挑一个空闲端口")
    parser.add_argument("--sandbox", default=None, help="沙盒目录（缺省用系统临时目录）")
    parser.add_argument("--keep", action="store_true", help="保留沙盒（默认测完即清）")
    parser.add_argument("--budget", type=int, default=20000, help="浏览器虚拟时间预算（毫秒）")
    parser.add_argument("--timeout", type=float, default=120.0, help="浏览器进程超时（秒）")
    parser.add_argument("--ready-timeout", type=float, default=15.0, help="等待服务就绪（秒）")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    if not browser:
        check(True, "浏览器探测", "未检测到 Edge/Chrome —— 已跳过页面级冒烟（本次未验证）")
        print("[冒烟·页面] 未检测到 Chromium 系浏览器（可用 --browser 指定路径后重跑）")
        width = max(len(name) for _ok, name, _note in RESULTS) + 2
        for ok, name, note in RESULTS:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        print("[冒烟·页面] 共 1 项 · 失败 0 项（跳过 1）")
        return 0

    # 前置探测（§P2-11）：`--browser` 指向不可无头驱动的 exe（如夸克启动器）时**跳过**，
    # 而不是让它走到「探针完成 FAIL」—— 那会把「环境不支持」误判成「页面有缺陷」。
    drivable, why = browser_drivable(browser)
    if not drivable:
        check(True, "浏览器可驱动性", f"已跳过页面级冒烟：{why}")
        print(f"[冒烟·页面] 浏览器不可无头驱动：{browser}")
        print(f"[冒烟·页面] 原因：{why}（属环境不支持，非页面缺陷；可用 --browser 换一个）")
        width = max(len(name) for _ok, name, _note in RESULTS) + 2
        for ok, name, note in RESULTS:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        print("[冒烟·页面] 共 1 项 · 失败 0 项（跳过 1）")
        return 0

    if not (SRC_DIR / "server").is_dir():
        print(f"[失败] 未找到服务端：{SRC_DIR / 'server'}")
        return 1

    if args.sandbox:
        sandbox = Path(args.sandbox).resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    elif args.keep:
        sandbox = sandbox_base() / f"qingman_browser_{time.strftime('%Y%m%d')}"
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        sandbox = Path(tempfile.mkdtemp(prefix="qm_browser_"))
        cleanup = True

    version_file = PROJECT_ROOT / "VERSION"
    expected_version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
    templates_dir = PROJECT_ROOT / "templates"

    print(f"[冒烟·页面] 浏览器：{browser}")
    print(f"[冒烟·页面] 沙盒：{sandbox}")

    sandbox_src = sandbox / "src"

    # 复用同一沙盒时，先清掉**本脚本自己**上次留下的产物（只看这几个已知名字，
    # 不动沙盒里其它内容）。`data/` 必须清：残留的 editor.json 会被
    # `restoreDocument()` 复原，于是走不到「默认构建」这条路径，
    # 「默认示例随语言」一项就会假通过。
    stale = [name for name in ("src", "templates", "VERSION", "data", "browser-profile")
             if (sandbox / name).exists()]
    if stale:
        print(f"[冒烟·页面] 复用沙盒，清理上次产物：{', '.join(stale)}")
        for name in stale:
            target = sandbox / name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink()

    shutil.copytree(SRC_DIR, sandbox_src)
    if version_file.is_file():
        shutil.copy2(version_file, sandbox / "VERSION")
    if templates_dir.is_dir():
        shutil.copytree(templates_dir, sandbox / "templates")
    (sandbox_src / "web" / PROBE_NAME).write_text(PROBE_HTML, encoding="utf-8", newline="\n")

    port = args.port or free_port()
    env = dict(os.environ, QM_PORT=str(port), QM_OPEN_BROWSER="0", PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(
        [sys.executable, "-m", "server"], cwd=str(sandbox_src), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace",
    )

    stderr = ""
    try:
        if not wait_health(port, args.ready_timeout):
            check(False, "服务启动", f"{args.ready_timeout}s 内未就绪")
        else:
            origin = f"http://127.0.0.1:{port}"
            url = f"{origin}/{PROBE_NAME}"
            timed_out = False
            try:
                stdout, stderr, code = run_browser(
                    browser, url, sandbox / "browser-profile", args.budget, args.timeout)
            except subprocess.TimeoutExpired:
                stdout, stderr, code = "", "", -1
                timed_out = True
                check(False, "浏览器运行", f"{args.timeout}s 内未返回")

            if timed_out:
                stderr = ""
            console = console_lines(stderr, origin)
            # 正面控制（§P2-13）：先证「日志通道在投递」，再谈「无未捕获异常」。
            alive = any(SELF_REPORT in line for line in console)
            check(alive, "控制台日志通道可用（正面控制）",
                  "已收到探针自报，日志通道正常" if alive else
                  "未收到探针自报 —— `--enable-logging` 通道可能失效，「无未捕获异常」判定不可信")
            fatal = [line for line in console if any(tok in line for tok in FATAL_CONSOLE)]
            noisy = [line for line in console
                     if SELF_REPORT not in line and not any(tok in line for tok in FATAL_CONSOLE)]
            check(not fatal, "页面载入无未捕获异常 / 无漏翻",
                  ("；".join(line.split("]", 1)[-1].strip()[:110] for line in fatal[:3])
                   if fatal else
                   f"本项目页面控制台 {len(console)} 条消息，无致命项"
                   + (f"（容忍 {len(noisy)} 条装饰性告警）" if noisy else "")))

            metrics = parse_metrics(stdout)
            check(metrics is not None, "探针完成",
                  "已取到页面指标" if metrics else f"未取到结果行（退出码 {code}）")
            if metrics:
                for key in ("err1", "err2", "err3"):
                    if key in metrics:
                        check(False, "探针脚本自身异常", f"{key}={metrics[key]}")
                verify_metrics(metrics, expected_version, templates_dir.is_dir())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        if cleanup:
            shutil.rmtree(sandbox, ignore_errors=True)

    width = max(len(name) for _ok, name, _note in RESULTS) + 2
    failed = 0
    print("-" * 78)
    for ok, name, note in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        if not ok:
            failed += 1
    print("-" * 78)
    print(f"[冒烟·页面] 共 {len(RESULTS)} 项 · 失败 {failed} 项")
    print(f"[冒烟·页面] 结论：{'全部通过' if not failed else '不通过'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
