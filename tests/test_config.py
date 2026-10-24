"""青蔓 QingMan · config 单元测试（V0.0.22）。

覆盖「请求体传输上限必须 ≥ 各业务上限」这一不变量。旧版把 `MAX_BODY_BYTES` 固定为
256KB，低于编辑态 8MB / 模板 2MB —— `_read_body()` 先于业务检查拦下请求体，使
`editorTooLarge` / `templateTooLarge` / `iconTooLarge` 永远不可达（用户只拿到误导性的
413 `bodyTooLarge`）。现该值**从业务上限派生**，本模块把这层关系钉死。

用法与其余测试一致：支持 `QM_SRC` 指向预览版，落地前即可过门禁；用子进程导入
配置（`-B` 免写 `__pycache__`）以避免污染主线进程内的 config 单例。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _HERE.parents[1] / "src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import config  # noqa: E402

_PROBE = ("import sys;sys.path.insert(0,{src!r});from server import config as c;"
          "print(c.MAX_BODY_BYTES,c.BUSINESS_MAX_BYTES,c.MAX_EDITOR_BYTES,"
          "c.TEMPLATE_MAX_BYTES,c.MAX_ICON_BYTES)")


def probe(extra_env: dict | None = None) -> list[int]:
    """在独立子进程导入 config，返回 [传输, 业务, 编辑态, 模板, 图标] 五个上限。"""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if extra_env:
        env.update(extra_env)
    out = subprocess.run([sys.executable, "-B", "-c", _PROBE.format(src=str(_SRC))],
                         env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise AssertionError("config 导入失败：" + (out.stderr or "").strip())
    return [int(x) for x in out.stdout.split()]


class BodyLimitInvariantTests(unittest.TestCase):
    """§P0-1：两层体积上限必须自洽，业务错误码才可达。"""

    def test_body_covers_editor_limit(self):
        body, _biz, editor, _tpl, _icon = probe()
        self.assertGreaterEqual(body, editor,
                                "传输上限低于编辑态上限 —— editorTooLarge 不可达")

    def test_body_covers_all_business_limits(self):
        body, _biz, editor, tpl, icon = probe()
        self.assertGreaterEqual(body, max(editor, tpl, icon))

    def test_business_max_is_derived_from_limits(self):
        _body, biz, editor, tpl, icon = probe()
        # 图标经 base64 传输有 4/3 膨胀，故按 2× 计入
        self.assertEqual(biz, max(editor, tpl, 2 * icon))

    def test_default_leaves_framing_headroom(self):
        body, biz, *_ = probe()
        self.assertGreater(body, biz, "默认应留组帧余量（严格大于业务上限）")

    def test_env_cannot_lower_below_business(self):
        # QM_MAX_BODY 只能抬高：调低到 1KB 也必须被 max() 兜回业务上限，否则不一致复现
        body, biz, *_ = probe({"QM_MAX_BODY": "1024"})
        self.assertGreaterEqual(body, biz)

    def test_env_can_raise(self):
        body, _biz, *_ = probe({"QM_MAX_BODY": str(64 * 1024 * 1024)})
        self.assertEqual(body, 64 * 1024 * 1024)

    def test_module_matches_probe(self):
        """进程内单例与子进程实测同源，防止两者漂移。"""
        self.assertEqual(config.MAX_BODY_BYTES, probe()[0])


class TemplatesDirResolutionTests(unittest.TestCase):
    """V0.0.35：运行态模板目录的解析优先级 `env > settings > 默认 templates/`。

    仍在**子进程**里导入 config（与 `probe` 同法）—— 复用同一进程会拿到被前一个用例
    污染过的模块状态。`QM_SETTINGS` 一律指向临时文件，绝不读写真机配置。
    """

    _PROBE_DIR = ("import sys;sys.path.insert(0,{src!r});from server import config as c;"
                  "print(c.templates_dir());print(c.templates_dir_source())")

    def _probe_dir(self, extra_env: dict) -> tuple[Path, str]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("QM_TEMPLATES_DIR", None)
        env.update(extra_env)
        out = subprocess.run([sys.executable, "-B", "-c", self._PROBE_DIR.format(src=str(_SRC))],
                             env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        if out.returncode != 0:
            raise AssertionError("config 导入失败：" + (out.stderr or "").strip())
        lines = out.stdout.strip().splitlines()
        return Path(lines[0]), lines[1]

    @staticmethod
    def _same(a: Path, b: Path) -> bool:
        # **必须 realpath**：GitHub Actions 的 `TMP` 是 8.3 短名（`C:\Users\RUNNER~1\...`），
        # 而 `config` 返回的是 `resolve()` 后的长名（`runneradmin`）。只 normcase 会把同一个
        # 目录判成两个 ⇒ CI 假红（2026-10-24 实证 3 例）。
        return (os.path.normcase(os.path.realpath(str(a)))
                == os.path.normcase(os.path.realpath(str(b))))

    def test_default_when_nothing_set(self):
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            dir_, source = self._probe_dir({"QM_SETTINGS": str(Path(d) / "settings.json")})
            self.assertEqual(source, "default")
            self.assertTrue(self._same(dir_, _SRC.parent / "templates"))

    def test_env_wins_over_settings(self):
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            settings = Path(d) / "settings.json"
            settings.write_text(json.dumps({"templatesDir": str(Path(d) / "bound")}),
                                encoding="utf-8")
            target = Path(d) / "envdir"
            dir_, source = self._probe_dir({"QM_SETTINGS": str(settings),
                                            "QM_TEMPLATES_DIR": str(target)})
            self.assertEqual(source, "env")
            self.assertTrue(self._same(dir_, target))

    def test_settings_used_when_env_absent(self):
        # V0.1.0：绑定目录**必须真实存在**才算数（悬空绑定会回落默认，见下一个用例）
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            settings = Path(d) / "settings.json"
            target = Path(d) / "bound"
            target.mkdir()
            settings.write_text(json.dumps({"templatesDir": str(target)}), encoding="utf-8")
            dir_, source = self._probe_dir({"QM_SETTINGS": str(settings)})
            self.assertEqual(source, "settings")
            self.assertTrue(self._same(dir_, target))

    def test_stale_binding_falls_back_to_default(self):
        """绑定目录被移动 / 删除后不得让模板列表永久"不可用" —— 回落默认并报告来源。"""
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            settings = Path(d) / "settings.json"
            gone = Path(d) / "moved-away"          # 故意不创建
            settings.write_text(json.dumps({"templatesDir": str(gone)}), encoding="utf-8")
            dir_, source = self._probe_dir({"QM_SETTINGS": str(settings)})
            self.assertEqual(source, "default")
            self.assertTrue(self._same(dir_, _SRC.parent / "templates"))

    def test_corrupt_settings_falls_back_to_default(self):
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            settings = Path(d) / "settings.json"
            settings.write_text("{不是合法 json", encoding="utf-8")
            dir_, source = self._probe_dir({"QM_SETTINGS": str(settings)})
            self.assertEqual(source, "default")
            self.assertTrue(self._same(dir_, _SRC.parent / "templates"))

    def test_env_wins_over_default(self):
        with tempfile.TemporaryDirectory(prefix="qm_cfg_") as d:
            target = Path(d) / "envonly"
            dir_, source = self._probe_dir({"QM_SETTINGS": str(Path(d) / "settings.json"),
                                            "QM_TEMPLATES_DIR": str(target)})
            self.assertEqual(source, "env")
            self.assertTrue(self._same(dir_, target))


class RuntimeDirResolutionTests(unittest.TestCase):
    """V0.1.0：数据 / 模板目录的「只读安装 · 多用户」解析（纯函数，无副作用）。

    分发前提：程序目录可能不可写（`Program Files`、网络盘、受管终端），
    此时必须退到每用户目录；而**旧布局已有数据**时绝不能改指别处（用户的稿子不能"消失"）。
    判据全部用纯函数 + 临时目录验证，不碰真机 `%APPDATA%`。
    """

    def test_env_override_wins(self):
        with tempfile.TemporaryDirectory(prefix="qm_data_") as d:
            project = Path(d) / "proj"
            project.mkdir()
            target = Path(d) / "custom"
            self.assertEqual(config.resolve_data_dir(project, str(target), Path(d) / "user"), target)

    def test_legacy_data_wins_over_per_user(self):
        # 旧布局有 editor.json ⇒ 即使目录"不可写"的判断不成立，也必须继续用它
        with tempfile.TemporaryDirectory(prefix="qm_data_") as d:
            project = Path(d) / "proj"
            (project / "data").mkdir(parents=True)
            (project / "data" / "editor.json").write_text("{}", encoding="utf-8")
            got = config.resolve_data_dir(project, "", Path(d) / "user")
            self.assertEqual(got, project / "data")

    def test_writable_project_uses_local(self):
        with tempfile.TemporaryDirectory(prefix="qm_data_") as d:
            project = Path(d) / "proj"
            project.mkdir()
            got = config.resolve_data_dir(project, "", Path(d) / "user")
            self.assertEqual(got, project / "data")

    def test_readonly_project_falls_back_to_per_user(self):
        # 不依赖真实只读：把「项目根」指成一个**不存在**的路径 ⇒ os.access 判不可写
        with tempfile.TemporaryDirectory(prefix="qm_data_") as d:
            ghost = Path(d) / "nope" / "proj"
            got = config.resolve_data_dir(ghost, "", Path(d) / "user")
            self.assertEqual(got, Path(d) / "user" / "data")

    def test_no_per_user_root_keeps_legacy(self):
        with tempfile.TemporaryDirectory(prefix="qm_data_") as d:
            ghost = Path(d) / "nope"
            self.assertEqual(config.resolve_data_dir(ghost, "", None), ghost / "data")


class TemplateSeedTests(unittest.TestCase):
    """只读安装下，每用户模板库必须**被播种**（否则模板列表是空的）。"""

    def test_seed_copies_bundled_into_empty(self):
        with tempfile.TemporaryDirectory(prefix="qm_seed_") as d:
            dest = Path(d) / "templates"
            copied = config.seed_templates(dest)
            self.assertEqual(sorted(copied), sorted(p.name for p in
                                                    config.DEFAULT_TEMPLATES_DIR.glob("*.json")))
            self.assertTrue(any(dest.glob("*.json")))

    def test_seed_skips_when_user_content_exists(self):
        with tempfile.TemporaryDirectory(prefix="qm_seed_") as d:
            dest = Path(d) / "templates"
            dest.mkdir()
            mine = dest / "S9_我自己的模板.json"
            mine.write_text("{}", encoding="utf-8")
            self.assertEqual(config.seed_templates(dest), [])
            self.assertEqual([p.name for p in dest.glob("*.json")], [mine.name])

    def test_seed_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="qm_seed_") as d:
            dest = Path(d) / "templates"
            first = config.seed_templates(dest)
            before = {p.name for p in dest.glob("*.json")}
            second = config.seed_templates(dest)
            self.assertTrue(first)
            self.assertEqual(second, [])
            self.assertEqual({p.name for p in dest.glob("*.json")}, before)


if __name__ == "__main__":
    unittest.main()
