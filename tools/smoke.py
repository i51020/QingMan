"""青蔓 QingMan · 端到端冒烟（§P0-2 T4）。

把「启动服务 → 健康检查 → 演练不写盘 → 真实落盘 → 重复生成幂等 → 错误分支 →
落盘安全边界 → 路径穿越」固化为常驻脚本，取代一次性的临时冒烟。

用法：
    python tools/smoke.py [--keep] [--port 8799] [--sandbox DIR]

退出码：0 全部通过；1 存在失败项。
约定：
  * 全程在沙盒目录内进行（§P0-2 T6），默认 `D:\\Data\\WorkBuddy\\_sandbox\\qingman_smoke_<日期>\\`，测完即清。
  * 复用 `--sandbox` / `--keep` 指定的沙盒时，运行前先清掉**本脚本上次留下的产物**（仅 `生成结果` / `big`），
    使工具本身**幂等**：同一沙盒连跑两次结论一致（§项目约定 §P2 第 17 项「工具间一致性」）。
  * 只读地使用真实 `src/`（不复制、不改动）；仅 `/api/editor` 的写接口不在本冒烟范围内
    （其单元测试在临时目录内进行，见 tests/test_routes.py）。
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

RESULTS: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, note: str = "") -> None:
    RESULTS.append((bool(ok), name, note))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def sandbox_base() -> Path:
    """`--keep` 沙盒的父目录（§P2-10：不再硬编码绝对盘符路径）。

    与 `tools/browser_smoke.py` 的 `sandbox_base` 同构（§P2 第 17 项「工具间一致性」）：
    `QM_SANDBOX` 环境变量优先；否则取**项目根的上两级**下的 `_sandbox/`。
    """
    env = os.environ.get("QM_SANDBOX", "").strip()
    return Path(env) if env else (PROJECT_ROOT.parent.parent / "_sandbox")


class Client:
    """极简 HTTP 客户端：直接控制请求行，避免被 urllib 规范化掉路径穿越用例。"""

    def __init__(self, port: int) -> None:
        self.port = port

    def request(self, method: str, path: str, body: bytes | None = None,
                guard: bool = True, ctype: bool = True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if body is not None:
            headers["Content-Length"] = str(len(body))
            if ctype:
                headers["Content-Type"] = "application/json; charset=utf-8"
        if guard:
            headers["X-QingMan"] = "1"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = None
        return resp.status, data, raw

    def post_json(self, path: str, obj, **kw):
        return self.request("POST", path, json.dumps(obj, ensure_ascii=False).encode("utf-8"), **kw)


def wait_ready(client: Client, seconds: float = 15.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            status, _data, _raw = client.request("GET", "/api/health")
            if status == 200:
                return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def run_checks(client: Client, sandbox: Path) -> None:
    target = sandbox / "生成结果"
    tree = {"素材": {"原图": {}, "已整理": {}}, "说明.md": "由冒烟生成\n"}
    version_text = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    # 1. 健康检查
    status, data, _ = client.request("GET", "/api/health")
    check(status == 200 and data and data.get("ok"), "GET /api/health → 200",
          f"{status} version={data.get('version') if data else '?'}")

    # 2. 写操作防护头
    status, data, _ = client.post_json("/api/generate", {"tree": tree, "target": str(target)},
                                      guard=False)
    check(status == 403 and data and data.get("code") == "missingGuardHeader",
          "缺 X-QingMan 头 → 403", f"{status} {data.get('code') if data else '?'}")

    # 3. 请求体非法 JSON
    status, data, _ = client.request("POST", "/api/generate", "{不是 json".encode("utf-8"))
    check(status == 400 and data and data.get("code") == "badJson",
          "非法 JSON → 400", f"{status} {data.get('code') if data else '?'}")

    # 4. 缺少 tree / target
    status, data, _ = client.post_json("/api/generate", {"target": str(target)})
    check(status == 400 and data and data.get("code") == "treeMissing",
          "缺 tree → 400", f"{status} {data.get('code') if data else '?'}")
    status, data, _ = client.post_json("/api/generate", {"tree": tree})
    check(status == 400 and data and data.get("code") == "targetMissing",
          "缺 target → 400", f"{status} {data.get('code') if data else '?'}")

    # 5. 落盘安全边界（§P0-1）—— 必须 4xx + 明确错误码，不能是 500
    blocked_probe = os.environ.get("SystemRoot", r"C:\Windows")
    guard_cases = [
        ("盘根", Path.cwd().anchor, "targetTooShallow"),
        ("系统目录子树", blocked_probe + r"\System32\qingman-smoke", "targetBlocked"),
        ("项目自身", str(PROJECT_ROOT), "targetReserved"),
    ]
    for label, bad_target, expect in guard_cases:
        status, data, _ = client.post_json("/api/generate", {"tree": tree, "target": bad_target})
        code = data.get("code") if data else None
        check(status == 400 and code == expect, f"安全边界·{label} → 400 {expect}",
              f"{status} {code}")

    # 6. 规模超限（服务端直接拒，不依赖前端确认）
    big = {f"d{i}": {} for i in range(501)}
    status, data, _ = client.post_json("/api/generate", {"tree": big, "target": str(sandbox / "big")})
    check(status == 400 and data and data.get("code") == "tooManyNodes",
          "规模超限 → 400 tooManyNodes", f"{status} {data.get('code') if data else '?'}")
    check(not (sandbox / "big").exists(), "超限未落盘", "未创建目录")

    # 7. dryRun 不写盘
    status, data, _ = client.post_json("/api/generate",
                                      {"tree": tree, "target": str(target), "dryRun": True})
    check(status == 200 and data and data.get("dryRun") and not target.exists(),
          "dryRun → 200 且不写盘", f"{status} created={target.exists()}")

    # 8. 真实落盘逐项核对
    status, data, _ = client.post_json("/api/generate",
                                      {"tree": tree, "target": str(target), "dryRun": False})
    ok_files = (target / "素材" / "原图").is_dir() and (target / "说明.md").is_file()
    check(status == 200 and data and data.get("ok") and ok_files, "真实落盘 → 文件就位",
          f"{status} dirs={len(data.get('createdDirs', [])) if data else '?'} "
          f"files={len(data.get('createdFiles', [])) if data else '?'}")
    check((target / "说明.md").read_bytes() == "由冒烟生成\n".encode("utf-8"),
          "落盘内容逐字节一致（LF）", "无 CR")

    # 9. 重复生成幂等（R7）
    status, data, _ = client.post_json("/api/generate",
                                      {"tree": tree, "target": str(target), "dryRun": False})
    check(status == 200 and data and not data["createdDirs"] and not data["createdFiles"]
          and len(data["existed"]) >= 3, "重复生成幂等 → created 空 / existed 满",
          f"{status} existed={len(data.get('existed', [])) if data else '?'}")

    # 10. 静态文件路径穿越
    status, data, _ = client.request("GET", "/..%2f..%2fVERSION")
    check(status == 403 and data and data.get("code") == "badPath",
          "路径穿越 → 403 badPath", f"{status} {data.get('code') if data else '?'}")
    status, _data, raw = client.request("GET", "/index.html")
    check(status == 200 and b"<html" in raw.lower(), "静态文件正常 → 200", str(status))

    # 11. 版本号与 VERSION 一致
    status, data, _ = client.request("GET", "/api/health")
    check(data and data.get("version") == version_text,
          "服务读到的版本 = VERSION 文件", f"{data.get('version') if data else '?'} vs {version_text}")


def main() -> int:
    parser = argparse.ArgumentParser(description="青蔓 QingMan 端到端冒烟")
    parser.add_argument("--port", type=int, default=0, help="0 = 自动挑一个空闲端口")
    parser.add_argument("--sandbox", default=None, help="沙盒目录，缺省 D:\\Data\\WorkBuddy\\_sandbox\\qingman_smoke_<日期>")
    parser.add_argument("--keep", action="store_true", help="保留沙盒（默认测完即清）")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    if not (SRC_DIR / "server").is_dir():
        print(f"[失败] 未找到服务端：{SRC_DIR / 'server'}")
        return 1

    if args.sandbox:
        sandbox = Path(args.sandbox).resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    elif args.keep:
        sandbox = sandbox_base() / f"qingman_smoke_{time.strftime('%Y%m%d')}"
        sandbox.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        sandbox = Path(tempfile.mkdtemp(prefix="qm_smoke_"))
        cleanup = True

    # 复用同一沙盒（--sandbox / --keep）时，先清掉**本脚本自己**上次留下的产物
    # （只看这几个已知名字，不动沙盒里其它内容）。不清的话第 7 项 `dryRun` 断言
    # `not target.exists()` 恒为 False → 第二次起必然误报 FAIL。
    # 体例与 `browser_smoke.py` 一致（§项目约定 §P2 第 17 项「工具间一致性」）。
    stale = [name for name in ("生成结果", "big") if (sandbox / name).exists()]
    if stale:
        print(f"[冒烟] 复用沙盒，清理上次产物：{', '.join(stale)}")
        for name in stale:
            victim = sandbox / name
            if victim.is_dir():
                shutil.rmtree(victim, ignore_errors=True)
            else:
                victim.unlink()

    port = args.port or free_port()
    env = dict(os.environ, QM_PORT=str(port), QM_OPEN_BROWSER="0", PYTHONDONTWRITEBYTECODE="1")

    print(f"[冒烟] 服务：{SRC_DIR}  端口：{port}")
    print(f"[冒烟] 沙盒：{sandbox}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "server"], cwd=str(SRC_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    client = Client(port)
    try:
        if not wait_ready(client, args.timeout):
            check(False, "服务启动", f"{args.timeout}s 内未就绪")
        else:
            run_checks(client, sandbox)
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
    print("-" * 76)
    for ok, name, note in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)} {note}")
        if not ok:
            failed += 1
    print("-" * 76)
    print(f"[冒烟] 共 {len(RESULTS)} 项 · 失败 {failed} 项")
    print(f"[冒烟] 结论：{'全部通过' if not failed else '不通过'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
