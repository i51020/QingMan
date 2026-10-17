"""青蔓 QingMan · 在线版完整项目包（可部署产物 + 构建源码 + 手册）。

**为什么单独打一个包**：`build_static_site.py` 的产物只能"部署"，不能"再构建" ——
接手的人拿到 `site/` 之后，改不了注入逻辑（后端、模板文法移植、PWA、下载入口都在构建脚本里）。
这个包把「可直接托管的产物」与「能重建它的最小源码集」放在一起，并附上唯一权威手册。

**与其它包的分工**：

| 包 | 给谁 | 能不能重建 |
|---|---|---|
| 便携发布包 `package_release.py` | 最终用户（本机版） | 不能，也不需要 |
| 接续包 / 完整开发包 `handoff_pack.py` | 接手开发者（全套仓库） | 能，但很重（含 .git / store） |
| **在线版完整项目包**（本工具） | **只负责在线版的人** | **能**（含构建脚本与注入资源，不含仓库历史） |

**用法**：`py -3 tools/pack_online.py [--out-dir dist] [--built-at 固定时间] [--verify 包路径]`
产物：`dist/QingMan-在线版-完整包-<版本>.zip`
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE.parent))

import package_release as pr  # noqa: E402  （复用确定性打包与 sha256 清单）
import build_static_site as bss  # noqa: E402

VERSION = pr.VERSION if hasattr(pr, "VERSION") else (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DATE = time.strftime("%Y%m%d")
PREFIX = f"QingMan-在线版-完整包-{VERSION}"

DEPLOY_README = """青蔓 QingMan · 在线版完整项目包
====================================

版本：{version}    打包日期：{date}

一、这个包里有什么
------------------
  site/                     可直接托管的静态站点（已注入浏览器内后端 / PWA / 帮助页下载入口）
  在线版手册.md             能力矩阵、端点契约、部署步骤、排障 —— 先读这份
  build/build_static_site.py  构建脚本（从 src/ 重新生成 site/ 用；本包不含 src/）
  build/web-demo/           在线版全部的注入资源：
                              demo-backend.js   浏览器内后端
                              md-template.js    模板 .md 文法的 JS 移植
                              make_icons.py     PWA 图标生成（纯标准库）
  VERSION                   版本号（唯一来源）

二、怎么部署
------------
  1) 安装 CLI：  npm install -g edgeone@latest
  2) 登录：      edgeone login --site china
  3) 发布：      cd site && PAGES_SOURCE=skills edgeone makers deploy -n <项目名> --json

  也可以直接上传 site/ 到任意静态托管（Nginx / OSS / GitHub Pages）。

三、注意
--------
  · 预览域名必须带 ?eo_token=...&eo_time=... 访问，否则任何路径都 401（含静态资源）。
  · 生成目录需要 Edge / Chrome：浏览器要向用户申请文件夹写权限。
  · site/ 里没有本机版下载包（打包时用 --no-download 跳过）；若需要，请在
    `site/downloads/` 放 QingMan-<版本>-portable.zip，帮助页的下载按钮会自动可用。
  · 发布目录请保持干净：EdgeOne 构建器会清理上一轮 .edgeone/assets，脏目录容易失败。

四、想改行为怎么办
------------------
  改 build/web-demo/ 下的文件 → 用完整仓库的 `py -3 tools/build_static_site.py` 重建，
  或直接手改 site/ 内对应文件（注意 site/js/demo-*.js 是构建期拷贝，改这里不会回到仓库）。

手册文件：在线版手册.md
"""


def collect(site_dir: Path) -> "list[tuple[Path, str]]":
    """打包清单：site/ 全量 + 手册 + 构建源码 + VERSION + 部署说明（内存生成）。"""
    files: "list[tuple[Path, str]]" = []
    for path in sorted(site_dir.rglob("*")):
        if path.is_file():
            files.append((path, "site/" + path.relative_to(site_dir).as_posix()))
    for rel in ("docs/在线版手册.md", "VERSION"):
        src = ROOT / rel
        if not src.is_file():
            raise SystemExit(f"[FAIL] 缺必需件：{rel}")
        files.append((src, Path(rel).name))
    for rel in ("tools/build_static_site.py",
                "tools/web-demo/demo-backend.js",
                "tools/web-demo/md-template.js",
                "tools/web-demo/make_icons.py"):
        src = ROOT / rel
        if not src.is_file():
            raise SystemExit(f"[FAIL] 缺必需件：{rel}")
        files.append((src, "build/" + Path(rel).name
                      if "/web-demo/" not in rel else "build/web-demo/" + Path(rel).name))
    return files


def build(out_dir: Path, built_at: "str | None" = None) -> Path:
    staging = Path(tempfile.mkdtemp(prefix="qm_online_"))
    site_root = Path(tempfile.mkdtemp(prefix="qm_site_"))
    site_tmp = site_root / "site"     # 传给 build() 的路径必须**还不存在**，否则它会改名让路
    try:
        info = bss.build(site_tmp, "zh-CN", with_download=False)
        files = collect(site_tmp)
        manifest = pr.build_staging(staging, files, None, built_at)
        manifest["package"] = "online"
        (staging / "README_部署说明.txt").write_text(
            DEPLOY_README.format(version=VERSION, date=time.strftime("%Y-%m-%d")),
            encoding="utf-8", newline="\n")
        manifest["files"]["README_部署说明.txt"] = {
            "size": (staging / "README_部署说明.txt").stat().st_size,
            "sha256": pr.sha256_file(staging / "README_部署说明.txt"),
        }
        pr.write_manifest(staging, manifest)
        out = out_dir / f"{PREFIX}.zip"
        pr.build_zip(staging, out, prefix=PREFIX)
        print(f"  site {info['files']} 文件 / {info['bytes'] / 1024:.0f} KB")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(site_root, ignore_errors=True)
    return out


def verify(zip_path: Path) -> int:
    problems: "list[str]" = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    prefix = names[0].split("/")[0] if names else ""
    for must in ("在线版手册.md", "VERSION", "README_部署说明.txt", "发布包清单.json",
                 "site/index.html", "site/help.html", "site/sw.js", "site/manifest.webmanifest",
                 "site/js/demo-backend.js", "site/js/md-template.js", "site/js/pwa.js",
                 "site/api/env.js", "site/api/locales.js",
                 "build/build_static_site.py", "build/web-demo/demo-backend.js",
                 "build/web-demo/md-template.js", "build/web-demo/make_icons.py"):
        if f"{prefix}/{must}" not in names:
            problems.append(f"缺 {must}")
    # 产物自洽：页面注入痕迹必须在
    with zipfile.ZipFile(zip_path) as zf:
        html = zf.read(f"{prefix}/site/index.html").decode("utf-8", "ignore")
    for token in ("demo-backend.js", "manifest.webmanifest", "qmOnlineNotice"):
        if token not in html:
            problems.append(f"index.html 未注入 {token}")
    print(f"[在线版包] {zip_path.name}  {zip_path.stat().st_size / 1024:.0f} KB  文件 {len(names)} 个")
    if problems:
        for item in problems:
            print(f"  [FAIL] {item}")
        return 1
    print("  [OK] 手册 / 构建源码 / 可托管产物 齐备；页面注入痕迹齐全")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="构建青蔓在线版完整项目包")
    ap.add_argument("--out-dir", default=str(ROOT / "dist"))
    ap.add_argument("--built-at", help="固定构建时间（复算用）")
    ap.add_argument("--verify", metavar="ZIP", help="只自检已构建的包")
    args = ap.parse_args(argv)
    if args.verify:
        return verify(Path(args.verify))
    out = build(Path(args.out_dir), args.built_at)
    print(f"[构建] {out}")
    return verify(out)


if __name__ == "__main__":
    raise SystemExit(main())
