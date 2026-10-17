"""青蔓 QingMan · 发布包构建与自检（V0.1.0 · 「装给别人用」）。

**为什么需要它**：本项目此前只服务「作者本机」—— `start.bat` 要求机器上已装 Python，
`data/` 写在程序目录。要交给其他用户，必须把**运行时**和**用户数据落点**一起解决。
本工具负责前者（把一份 Python 运行时随包带出去），`config.resolve_data_dir()` 负责后者。

**产物**：`dist/QingMan-<VERSION>-portable.zip`，解压即用：

    QingMan-<VERSION>/
      start.bat              双击启动（优先 runtime\\python.exe）
      VERSION
      README_使用说明.md
      发布包清单.json         每文件 sha256 + 字节数 + 运行时来源
      src/  templates/  templates-pack/
      runtime/               可选：裁剪过的 CPython（带 tkinter，目录选择框可用）

**裁剪口径**（runtime）：只留下运行本项目所需的解释器与标准库 —— 去掉
`Doc / include / libs / Scripts / Lib/test / Lib/site-packages / Lib/idlelib / Lib/ensurepip`
等与运行无关的目录。**不做二进制修补、不捆绑第三方包**：仍然是标准 CPython。

**确定性**：zip 内条目按路径排序、时间戳固定为 1980-01-01、压缩级别固定，
同一份输入两次构建**逐字节一致**（与 `pack_templates.py` 同体例）。

**用法**：

    py -3 tools/package_release.py                     # 自动探测本机 Python 作运行时
    py -3 tools/package_release.py --runtime-dir D:\\Python313
    py -3 tools/package_release.py --no-runtime         # 只打源码包（接收者自备 Python）
    py -3 tools/package_release.py --verify dist\\QingMan-V0.1.0-portable.zip

**边界**：本工具**只读**项目、**只写** `dist/` 与临时目录；不删除任何文件。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "V0.0.0"
PKG_DIRNAME = f"QingMan-{VERSION}"
ZIP_NAME = f"{PKG_DIRNAME}-portable.zip"

# 随包内容（**白名单**：只列该带的，避免把开发期资产带出去）
INCLUDE_DIRS = ("src", "templates", "templates-pack")
INCLUDE_FILES = ("VERSION", "start.bat", "README_使用说明.md")

# 排除（**黑名单**：白名单内的脏东西）
EXCLUDE_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".qingman", "data"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".zip", ".log"}

# 运行时裁剪：这些顶层/子树不带
RUNTIME_DROP_TOP = {"Doc", "include", "libs", "Scripts", "Lib"}
RUNTIME_DROP_LIB = {"test", "tests", "site-packages", "idlelib", "ensurepip",
                    "lib2to3", "turtledemo", "distutils", "venv"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_project_files() -> "list[tuple[Path, str]]":
    """返回 `[(绝对路径, 包内相对路径)]`，已按排除规则过滤并排序。"""
    out: "list[tuple[Path, str]]" = []
    for name in INCLUDE_FILES:
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f"[错误] 缺少发布必需文件：{name}")
        out.append((path, name))
    for name in INCLUDE_DIRS:
        base = ROOT / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in EXCLUDE_DIR_NAMES for part in rel.parts):
                continue
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            out.append((path, rel.as_posix()))
    return sorted(out, key=lambda kv: kv[1])


def iter_runtime_files(runtime_dir: Path) -> "list[tuple[Path, str]]":
    """运行时的随包文件（裁剪后），相对路径以 `runtime/` 开头。"""
    out: "list[tuple[Path, str]]" = []
    for path in sorted(runtime_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(runtime_dir)
        parts = rel.parts
        if parts and parts[0] in RUNTIME_DROP_TOP:
            if parts[0] != "Lib":
                continue
            # Lib 下只按白名单裁剪子目录
            if len(parts) > 1 and parts[1] in RUNTIME_DROP_LIB:
                continue
        if any(part == "__pycache__" for part in parts):
            continue
        if path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        out.append((path, f"runtime/{rel.as_posix()}"))
    return out


def detect_runtime_dir(explicit: "str | None") -> "Path | None":
    """定位一份可用的 CPython 安装目录（优先命令行指定，其次当前解释器的 base_prefix）。"""
    if explicit:
        path = Path(explicit).expanduser()
        if not (path / "python.exe").is_file():
            raise SystemExit(f"[错误] 不是有效的 Python 目录（缺 python.exe）：{path}")
        return path
    probe = subprocess.run([sys.executable, "-c", "import sys;print(sys.base_prefix)"],
                           capture_output=True, text=True, encoding="utf-8")
    base = Path((probe.stdout or "").strip())
    return base if (base / "python.exe").is_file() else None


def runtime_version(runtime_dir: Path) -> str:
    out = subprocess.run([str(runtime_dir / "python.exe"), "-c",
                          "import sys;print(sys.version.split()[0])"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (out.stdout or "").strip() or "unknown"


def build_staging(staging: Path, files: "list[tuple[Path, str]]",
                  runtime: "tuple[Path, list[tuple[Path, str]]] | None") -> dict:
    """把文件逐个复制进 `staging`，返回清单字典。"""
    entries: dict[str, dict] = {}
    for src, rel in files:
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        entries[rel] = {"size": dest.stat().st_size, "sha256": sha256_file(dest)}
    if runtime:
        rdir, rfiles = runtime
        for src, rel in rfiles:
            dest = staging / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            entries[rel] = {"size": dest.stat().st_size, "sha256": sha256_file(dest)}
    return {
        "schema": "qm-release/1",
        "version": VERSION,
        "builtAt": time.strftime("%Y-%m-%dT%H:%M:%S%z") or "",
        "runtime": ({"bundled": True, "python": runtime_version(runtime[0]),
                     "source": str(runtime[0])} if runtime else {"bundled": False}),
        "fileCount": len(entries),
        "totalBytes": sum(v["size"] for v in entries.values()),
        "files": {k: entries[k] for k in sorted(entries)},
    }


def write_manifest(staging: Path, manifest: dict) -> None:
    (staging / "发布包清单.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")


def build_zip(staging: Path, zip_path: Path) -> int:
    """确定性打包：条目排序 + 固定时间戳 + 固定压缩级别。"""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(staging.rglob("*")):
            if not path.is_file():
                continue
            rel = f"{PKG_DIRNAME}/{path.relative_to(staging).as_posix()}"
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path.stat().st_size


def _free_port(start: int = 8891) -> int:
    for port in range(start, start + 30):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("[错误] 找不到空闲端口")


def verify_package(zip_path: Path) -> int:
    """解压到临时目录并在**随包运行时**上真实起服务，再打一个健康检查请求。"""
    if not zip_path.is_file():
        raise SystemExit(f"[错误] 找不到发布包：{zip_path}")
    tmp = Path(tempfile.mkdtemp(prefix="qm_verify_"))
    failures: "list[str]" = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            zf.extractall(tmp)
        # ① 结构检查
        for must in ("start.bat", "VERSION", "src/server/__main__.py", "发布包清单.json",
                     "README_使用说明.md"):
            if f"{PKG_DIRNAME}/{must}" not in names:
                failures.append(f"缺 {must}")
        for banned in ("data/", "store/", ".git/", "versions/", "tests/", "tools/", "docs/"):
            if any(f"/{banned}" in n for n in names):
                failures.append(f"误带 {banned}")
        pkg = tmp / PKG_DIRNAME
        manifest = json.loads((pkg / "发布包清单.json").read_text(encoding="utf-8"))
        if manifest.get("version") != VERSION:
            failures.append(f"清单版本 {manifest.get('version')} != VERSION {VERSION}")
        # ② 运行时检查（不依赖本机 Python）
        py = pkg / "runtime" / "python.exe"
        if not py.is_file():
            failures.append("未带运行时（--no-runtime 构建，跳过启动检查）")
        else:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", QM_OPEN_BROWSER="0",
                       QM_PORT=str(_free_port()), QM_DATA_DIR=str(tmp / "userdata"))
            env.pop("QM_TEMPLATES_DIR", None)
            env.pop("QM_SETTINGS", None)
            proc = subprocess.Popen([str(py), "-B", "-m", "server"], cwd=str(pkg / "src"),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env=env, text=True, encoding="utf-8", errors="replace")
            try:
                import urllib.request
                port = env["QM_PORT"]
                ok = False
                for _ in range(60):
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                                    timeout=1) as resp:
                            body = json.loads(resp.read().decode("utf-8"))
                        ok = body.get("ok") is True
                        if ok:
                            break
                    except Exception:               # 服务尚未监听：继续等
                        time.sleep(0.25)
                if not ok:
                    failures.append("随包运行时启动后 /api/health 未返回 ok")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"[发布包] {zip_path.name}  {zip_path.stat().st_size/1024/1024:.1f} MB")
    if failures:
        for item in failures:
            print(f"  [FAIL] {item}")
        return 1
    print("  [OK] 结构 / 清单 / 随包运行时启动 / 健康检查 全部通过")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="构建青蔓发布包（便携版）")
    ap.add_argument("--runtime-dir", help="用作随包运行时的 Python 安装目录（缺省自动探测）")
    ap.add_argument("--no-runtime", action="store_true", help="不随包携带运行时")
    ap.add_argument("--out-dir", default=str(ROOT / "dist"), help="产物目录（默认 dist/）")
    ap.add_argument("--verify", metavar="ZIP", help="只自检已构建的发布包，不重新构建")
    args = ap.parse_args(argv)

    if args.verify:
        return verify_package(Path(args.verify))

    runtime_dir = None if args.no_runtime else detect_runtime_dir(args.runtime_dir)
    if not args.no_runtime and runtime_dir is None:
        raise SystemExit("[错误] 未找到可用 Python；请用 --runtime-dir 指定或加 --no-runtime")

    files = iter_project_files()
    runtime = (runtime_dir, iter_runtime_files(runtime_dir)) if runtime_dir else None
    staging = Path(tempfile.mkdtemp(prefix="qm_pkg_"))
    try:
        manifest = build_staging(staging, files, runtime)
        write_manifest(staging, manifest)
        out = Path(args.out_dir) / ZIP_NAME
        size = build_zip(staging, out)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    rt = manifest["runtime"]
    print(f"[构建] {out}")
    print(f"  版本     {VERSION}")
    print(f"  文件     {manifest['fileCount']} 个 · {manifest['totalBytes']/1024/1024:.1f} MB（未压缩）")
    print(f"  压缩包   {size/1024/1024:.1f} MB")
    print(f"  运行时   {'随包 · Python ' + rt['python'] if rt['bundled'] else '未携带（接收者需自备 Python）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
