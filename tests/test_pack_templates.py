"""青蔓 QingMan · pack_templates 单元测试（§P0-2 T2 / §P2 第 19 项 / 批 6D）。

覆盖 `tools/pack_templates.py` 承担判定职责的**纯函数**与两条核心不变量：

  * **内容保真**：16 套的 `.md` 与 `.json` **逐节点等价**（name / description / tree），
    且 `.md` 自身是往返不动点 —— 任一单边改动都必须被拒。
  * **可复算**：清单 `digest` 与 zip `sha256` 都能由盘上内容独立复算出来；且 zip 是
    **确定性**的（同一份源连跑两次字节相同，§P1-4 工具幂等）。
  * **项目内只有一套空模板**（2026-10-16 裁定）：`templates/` 只留内置
    `P0_空白项目模板.json` 一套；包内**不得**再收它的同名件。这是**负向守卫** ——
    正向的「包内 16 套」由 `discover()` 直接给出，负向的「不许再有第二套空模板」
    只有断言才守得住。
  * **打包与清单解耦**（《错误笔记》§三.79）：`--zip <路径>` **只产 zip**，不触碰仓内
    清单 —— 否则「打到别处」会把外部路径回写进仓库产物（机器相关的值渗进版本库）。
  * **运行时指纹**（§三.78）：清单 `zip.env` 登记构建时的 `python` / `zlib`，使
    「绝对 `sha256` 只在**同一运行时**内可比」这一前提**可判定**。指纹一致 → 强判
    绝对 `sha256`；不一致 → 降级为自洽断言并**显式声明降级**（不 skip、不静默）。
  * **退出码契约**：1 = 环境 / IO（目录或内置件缺失）；2 = 内容不通过（孤儿 `.md` /
    缺同名件 / 等价性 / 规范渲染 / 清单失配）。两类必须可分，见 `CheckModeTests`。

破坏性用例一律在**临时副本**上进行，不触碰仓库内真实 `templates/` 与 `templates-pack/`。
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import pack_templates as pt  # noqa: E402

REAL_PACK = _ROOT / "templates-pack"
REAL_TPL = _ROOT / "templates"


def _quiet(func, *args, **kwargs):
    """吞掉工具的 stdout（保持测试输出干净），返回其返回值。"""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def _quiet_capture(func, *args, **kwargs):
    """吞掉 stdout 并返回 `(返回值, 输出文本)` —— 用于断言退出码**与**提示语同时正确。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(*args, **kwargs)
    return rc, buf.getvalue()


def _fixture():
    """临时副本：真实 templates/ + templates-pack/（排除可再生的 zip）。"""
    tmp = Path(tempfile.mkdtemp(prefix="qm_pack_test_"))
    pack = tmp / "templates-pack"
    tpl = tmp / "templates"
    shutil.copytree(REAL_PACK, pack, ignore=shutil.ignore_patterns("*.zip"))
    shutil.copytree(REAL_TPL, tpl)
    return tmp, pack, tpl


class PackLayoutTests(unittest.TestCase):
    """盘上布局：内置只留一套空模板；包内 16 套 `.md` + 16 套 `.json` + 1 说明件。"""

    def test_templates_dir_has_only_builtin(self):
        left = sorted(p.name for p in REAL_TPL.iterdir())
        self.assertEqual(left, [pt.BUILTIN_JSON],
                         f"templates/ 应只留内置 {pt.BUILTIN_JSON}，实测 {left}")

    def test_pack_dir_counts(self):
        mds = [p.name for p in REAL_PACK.glob("*.md")]
        jsons = [p.name for p in REAL_PACK.glob("*.json")
                 if p.name != pt.MANIFEST_NAME]
        self.assertEqual(len(mds), 17, f"包内 .md 应为 16 套 + 1 说明，实测 {len(mds)}")
        self.assertEqual(len(jsons), 16, f"包内 .json 应为 16 套，实测 {len(jsons)}")

    def test_discover_is_pack_only(self):
        """包只盘点自身 16 套，且**不引用包外文件**（2026-10-16 裁定）。"""
        entries = pt.discover(REAL_PACK, REAL_TPL)
        self.assertEqual(len(entries), 16)
        self.assertFalse(any(e["builtin"] for e in entries),
                         "包内不应再有内置项（P0 已移出，见 §三.80）")
        self.assertNotIn(pt.BUILTIN_JSON[:-5], {e["stem"] for e in entries})
        for e in entries:
            for rel in (e["json_rel"], e["md_rel"]):
                self.assertFalse(rel.startswith("..") or "/" in rel,
                                 f"{e['stem']} 的引用越出了包目录：{rel}")

    def test_rejects_builtin_template_in_pack(self):
        """包内出现内置空模板的同名件 → 拒（否则导入后会有第二套空模板）。"""
        tmp, pack, tpl = _fixture()
        try:
            (pack / (pt.BUILTIN_JSON[:-5] + ".md")).write_text(
                "# 第二套空模板\n- 甲/\n", encoding="utf-8", newline="\n")
            with self.assertRaises(pt.PackError) as ctx:
                pt.discover(pack, tpl)
            self.assertIn("不得再收内置空模板的同名件", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rejects_business_template_in_builtin_dir(self):
        """业务模板回流到 templates/ → 拒（「工具不带业务模板」失守）。"""
        tmp, pack, tpl = _fixture()
        try:
            shutil.copy2(REAL_PACK / "S5_文档资料库.json", tpl / "S5_文档资料库.json")
            with self.assertRaises(pt.PackError) as ctx:
                pt.discover(pack, tpl)
            self.assertIn("应只留内置空模板", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)



class PackEquivalenceTests(unittest.TestCase):
    """16/16 逐节点等价 + 规模与来源说明自洽。"""

    def test_all_entries_pass(self):
        entries = pt.discover(REAL_PACK, REAL_TPL)
        n, dirs, files = pt.validate_pack(entries)
        self.assertEqual((n, dirs, files), (16, 475, 18),
                         "16 套 / 475 目录 / 18 文件（与《模板库来源说明》一致）")

    def test_rejects_md_json_mismatch(self):
        tmp, pack, tpl = _fixture()
        try:
            md = pack / "P1_实拍短视频项目.md"
            md.write_text(md.read_text(encoding="utf-8").replace("- 日志/", "- 日志X/", 1),
                          encoding="utf-8", newline="\n")
            entries = pt.discover(pack, tpl)
            with self.assertRaises(pt.PackError) as ctx:
                pt.validate_pack(entries)
            self.assertIn("tree 不等价", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rejects_noncanonical_md(self):
        """语义不变但非规范形（多一层缩进的空行）也必须被拒。"""
        tmp, pack, tpl = _fixture()
        try:
            md = pack / "P7_策划项目.md"
            text = md.read_text(encoding="utf-8")
            md.write_text(text + "\n\n", encoding="utf-8", newline="\n")
            entries = pt.discover(pack, tpl)
            with self.assertRaises(pt.PackError) as ctx:
                pt.validate_pack(entries)
            self.assertIn("规范渲染", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rejects_missing_json_twin(self):
        """孤儿 `.md`（`.json` 被删）必须被拒 —— 只按 `.json` 收集会让它静默消失。"""
        tmp, pack, tpl = _fixture()
        try:
            (pack / "S5_文档资料库.json").unlink()
            with self.assertRaises(pt.PackError) as ctx:
                pt.discover(pack, tpl)
            self.assertIn("孤儿", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rejects_missing_md_twin(self):
        tmp, pack, tpl = _fixture()
        try:
            (pack / "S5_文档资料库.md").unlink()
            with self.assertRaises(pt.PackError) as ctx:
                pt.discover(pack, tpl)
            self.assertIn("缺同名 .md", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_doc_file_is_not_orphan(self):
        """说明件无 `.json` 等价件，但**不得**被判孤儿。"""
        entries = pt.discover(REAL_PACK, REAL_TPL)
        stems = {e["stem"] for e in entries}
        self.assertNotIn("模板库来源说明", stems)
        self.assertEqual(len(entries), 16)


class ManifestTests(unittest.TestCase):
    """清单 digest 可复算；且覆盖 digestRule 自身。"""

    def test_manifest_matches_disk(self):
        entries = pt.discover(REAL_PACK, REAL_TPL)
        want = pt.canonical_bytes(pt.build_payload(entries))
        got = pt.canonical_bytes(pt.load_manifest(REAL_PACK))
        self.assertEqual(want, got, "清单主体应与盘上模板一致（否则有人改了模板未重生成清单）")

    def test_digest_recomputable(self):
        manifest = pt.load_manifest(REAL_PACK)
        self.assertEqual(manifest["digest"], pt.payload_digest(manifest))
        self.assertEqual(manifest["digestRule"], pt.DIGEST_RULE)

    def test_digest_covers_digest_rule(self):
        """规则文本本身也进 digest —— 改写规则同样会失配。"""
        manifest = pt.load_manifest(REAL_PACK)
        tampered = dict(manifest)
        tampered["digestRule"] = manifest["digestRule"] + " "
        self.assertNotEqual(pt.payload_digest(tampered), manifest["digest"])

    def test_totals_match_entries(self):
        manifest = pt.load_manifest(REAL_PACK)
        self.assertEqual(manifest["count"], 16)
        self.assertEqual(manifest["totals"], {"dirs": 475, "files": 18})
        self.assertEqual(sum(t["dirs"] for t in manifest["templates"]), 475)
        self.assertEqual(sum(t["files"] for t in manifest["templates"]), 18)
        for item in manifest["templates"]:
            self.assertTrue(item["md"]["sha256"] and item["json"]["sha256"])


class DeterministicZipTests(unittest.TestCase):
    """zip 确定性：字节可复现、条目固定、时间戳固定、清单不入包。"""

    def test_zip_bytes_reproducible(self):
        a = pt.build_zip_bytes(REAL_PACK)
        b = pt.build_zip_bytes(REAL_PACK)
        self.assertEqual(a, b, "同一份源连跑两次 zip 必须字节相同")

    def test_members_exclude_manifest_and_zip(self):
        names = [p.name for p in pt.zip_members(REAL_PACK)]
        self.assertEqual(len(names), 33, f"33 个成员（17 .md + 16 .json），实测 {len(names)}")
        self.assertNotIn(pt.MANIFEST_NAME, names)
        self.assertFalse([n for n in names if n.lower().endswith(".zip")])
        self.assertEqual(names, sorted(names), "成员须按名字典序")

    def test_entry_stamp_and_mode_fixed(self):
        data = pt.build_zip_bytes(REAL_PACK)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                self.assertEqual(info.date_time, pt.ZIP_STAMP)
                self.assertEqual(info.external_attr, pt.ZIP_MODE)

    def test_manifest_records_build_env_fingerprint(self):
        """清单 `zip` 块必须登记**构建时运行时指纹**与**仓内落点**（§三.78 / §三.79）。

        没有指纹，「同一运行时才比绝对 sha256」这条前提就**无法判定** —— 只能假设，
        而假设正是 CPython 3.14（zlib-ng）与本机 3.13（上游 zlib）之间那 423 字节
        差异长期隐身的原因。

        `zip.file` 另立一条**与运行时不相关**的判据：入库清单只能描述**仓内**那一份
        zip。2026-10-16 起它**结构上不可能漂移** —— `--zip <外部路径>` 已改为只产 zip、
        不写清单（§三.79 裁定的落点），`zip.file` 恒由默认模式写成 `ZIP_NAME`。本断言
        作为**护栏**保留：日后若有人把回写行为放回来，此断言即红。
        """
        manifest = pt.load_manifest(REAL_PACK)
        zblock = manifest.get("zip") or {}
        env = zblock.get("env")
        self.assertIsInstance(env, dict, "zip.env 缺失：跨运行时字节不可判（§三.78）")
        for key in ("python", "zlib"):
            self.assertTrue(isinstance(env.get(key), str) and env[key],
                            f"zip.env.{key} 须为非空字符串，实测 {env.get(key)!r}")
        # ★ 刻意**不**断言「env == 本运行时指纹」：那会让受管 3.13（仅作下限抽样）
        #   下恒红，而红的原因是"你换了解释器"、不是"清单错了" —— 正是 §三.78 要消灭的
        #   假红。清单与当前运行时的关系改由 `test_manifest_zip_sha256_matches_build`
        #   按指纹分流把关（那两个分支都成立）。
        self.assertEqual(zblock.get("file"), pt.ZIP_NAME,
                         f"入库清单的 zip.file 须为仓内规范名 {pt.ZIP_NAME!r}；"
                         f"实测 {zblock.get('file')!r}")
        # 只断言「盘上清单恰好有」不够 —— 那摘掉**登记点**也抓不住（反向验证 N2 实测）。
        # 故直接打构建函数：finalize_manifest 必须负责写入指纹。
        built = pt.finalize_manifest({"count": 0}, REAL_PACK, "x.zip", b"")
        self.assertEqual(built["zip"]["env"], pt.build_env_fingerprint(),
                         "finalize_manifest 必须登记运行时指纹（登记点缺失即红）")

    def test_manifest_zip_sha256_matches_build(self):
        """指纹一致 → 比绝对 sha256；不一致 → 降级为**自洽断言**（§三.78）。

        降级分支**不是跳过**：它仍断言「同一份源连跑两次字节相同」—— 那才是
        「确定性」的真实语义。用 `skipTest` 会让覆盖变薄，而绿看起来与全过无异
        （§P2 第 20 项）。
        """
        manifest = pt.load_manifest(REAL_PACK)
        zinfo = manifest["zip"]
        self.assertEqual(zinfo["members"], 33)
        if zinfo.get("env") == pt.build_env_fingerprint():
            self.assertEqual(zinfo["sha256"],
                             pt.sha256_bytes(pt.build_zip_bytes(REAL_PACK)),
                             "同一运行时下绝对 sha256 必须一致")
        else:
            self.assertTrue(pt.zip_self_consistent(REAL_PACK),
                            "跨运行时改判自洽后，本运行时仍须连跑两次字节相同")

    def test_zip_self_consistent_detects_drift(self):
        """反向用例：构建一旦不自洽，判据必须为 False（否则它只是空壳）。"""
        real = pt.build_zip_bytes
        calls = {"n": 0}

        def flaky(pack_dir):
            calls["n"] += 1
            return real(pack_dir) + bytes([calls["n"]])

        pt.build_zip_bytes = flaky
        try:
            self.assertFalse(pt.zip_self_consistent(REAL_PACK, real(REAL_PACK)),
                             "两次构建不同却判 True —— 自洽断言失效")
        finally:
            pt.build_zip_bytes = real

    def test_fmt_env_marks_missing(self):
        """旧清单（无 env）须渲染成「未登记」—— 「空」与「有」必须可辨。"""
        self.assertEqual(pt._fmt_env(None), "未登记")
        self.assertEqual(pt._fmt_env({}), "未登记")
        self.assertEqual(pt._fmt_env({"python": "3.14.8", "zlib": "1.3.1.zlib-ng"}),
                         "python 3.14.8 / zlib 1.3.1.zlib-ng")


class CheckModeTests(unittest.TestCase):
    """`--check` / 默认模式的三态：干净副本通过；内容坏 / 清单缺失或过期 → 2（不得抛栈）。"""

    def test_check_passes_on_fresh_copy(self):
        tmp, pack, tpl = _fixture()
        try:
            self.assertEqual(
                _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)]), 0)
            self.assertEqual(
                _quiet(pt.main, ["--check", "--pack-dir", str(pack),
                                 "--templates-dir", str(tpl)]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_broken_content_returns_2_not_traceback(self):
        """`.md` 非规范渲染是**内容校验失败**（退出码 2），不能以 traceback 收场。"""
        tmp, pack, tpl = _fixture()
        try:
            self.assertEqual(
                _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)]), 0)
            md = pack / "S2_个人知识库.md"
            md.write_text(md.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
            self.assertEqual(
                _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)]), 2)
            self.assertEqual(
                _quiet(pt.main, ["--check", "--pack-dir", str(pack),
                                 "--templates-dir", str(tpl)]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_env_returns_1(self):
        tmp, pack, tpl = _fixture()
        try:
            (tpl / pt.BUILTIN_JSON).unlink()
            self.assertEqual(
                _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_orphan_and_missing_twin_are_content_errors(self):
        """孤儿 `.md` / 缺同名件属**内容**校验失败（退出码 2），不得与环境错误（1）同码。

        反向验证 N7a（2026-10-11）暴露：二者原本都由 `discover()` 抛出，被 main 的
        discover 分支统一归为 1，而 docstring 声称其为 2。修法是拆出 `PackIOError`
        只承载环境类错误。本用例锁住该契约，避免日后合并回一个码位。
        """
        tmp, pack, tpl = _fixture()
        try:
            (pack / "S5_文档资料库.json").unlink()
            rc, msg = _quiet_capture(pt.main, ["--check", "--pack-dir", str(pack),
                                               "--templates-dir", str(tpl)])
            self.assertEqual(rc, 2, f"孤儿 .md 应返 2，实测 {rc}：{msg.strip()}")
            self.assertIn("孤儿", msg)

            shutil.copy2(REAL_PACK / "S5_文档资料库.json", pack / "S5_文档资料库.json")
            (pack / "S4_财务台账.md").unlink()
            rc, msg = _quiet_capture(pt.main, ["--check", "--pack-dir", str(pack),
                                               "--templates-dir", str(tpl)])
            self.assertEqual(rc, 2, f"缺同名件应返 2，实测 {rc}：{msg.strip()}")
            self.assertIn("缺同名 .md", msg)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_pack_dir_returns_1(self):
        """包目录整个缺失 → 环境错误（1），与内容错误（2）码位对的上半部分。"""
        tmp, pack, tpl = _fixture()
        try:
            shutil.rmtree(pack)
            rc, msg = _quiet_capture(pt.main, ["--check", "--pack-dir", str(pack),
                                               "--templates-dir", str(tpl)])
            self.assertEqual(rc, 1, f"包目录缺失应返 1，实测 {rc}：{msg.strip()}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_detects_missing_manifest(self):
        tmp, pack, tpl = _fixture()
        try:
            (pack / pt.MANIFEST_NAME).unlink()
            self.assertEqual(
                _quiet(pt.main, ["--check", "--pack-dir", str(pack),
                                 "--templates-dir", str(tpl)]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_downgrades_on_env_mismatch(self):
        """指纹不符 → 降级为自洽断言：退出码 0，但**必须显式声明降级**（§三.78）。

        这是本轮修复的正面用例：修复前该场景**必然 FAIL**（`py -3` / zlib-ng 下
        重建出的 24,693 B zip 与清单记录的 24,270 B 版本 sha256 永不相同）。
        """
        tmp, pack, tpl = _fixture()
        try:
            self.assertEqual(_quiet(pt.main, ["--pack-dir", str(pack),
                                              "--templates-dir", str(tpl)]), 0)
            path = pack / pt.MANIFEST_NAME
            data = json.loads(path.read_text(encoding="utf-8"))
            data["zip"]["env"] = {"python": "3.0.0", "zlib": "0.0.0-other-runtime"}
            path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
            rc, out = _quiet_capture(pt.main, ["--check", "--pack-dir", str(pack),
                                               "--templates-dir", str(tpl)])
            self.assertEqual(rc, 0, f"指纹不符应降级通过，实测 {rc}\n{out}")
            self.assertIn("运行时指纹与清单不一致", out, "降级必须显式声明，不得静默放过")
            self.assertIn("绝对 sha256 未比对", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_flags_sha_mismatch_when_env_matches(self):
        """指纹一致 → 绝对 sha256 仍须强判（降级不得顺手放过真失配）。"""
        tmp, pack, tpl = _fixture()
        try:
            self.assertEqual(_quiet(pt.main, ["--pack-dir", str(pack),
                                              "--templates-dir", str(tpl)]), 0)
            path = pack / pt.MANIFEST_NAME
            data = json.loads(path.read_text(encoding="utf-8"))
            data["zip"]["sha256"] = "0" * 64      # env 一字不动
            path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
            rc, out = _quiet_capture(pt.main, ["--check", "--pack-dir", str(pack),
                                               "--templates-dir", str(tpl)])
            self.assertEqual(rc, 2, f"同运行时下 sha256 失配应判 2，实测 {rc}\n{out}")
            self.assertIn("zip sha256 复算失配", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_detects_tampered_manifest(self):
        """清单被手改（digest 与内容不符）→ 复算失配。"""
        tmp, pack, tpl = _fixture()
        try:
            _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)])
            path = pack / pt.MANIFEST_NAME
            data = json.loads(path.read_text(encoding="utf-8"))
            data["digest"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
            self.assertEqual(
                _quiet(pt.main, ["--check", "--pack-dir", str(pack),
                                 "--templates-dir", str(tpl)]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_manifest_write_is_lf(self):
        tmp, pack, tpl = _fixture()
        try:
            _quiet(pt.main, ["--pack-dir", str(pack), "--templates-dir", str(tpl)])
            raw = (pack / pt.MANIFEST_NAME).read_bytes()
            self.assertNotIn(b"\r", raw, "清单必须是纯 LF（§编码基线）")
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw.decode("utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_zip_mode_does_not_touch_manifest(self):
        """`--zip <路径>` 只产 zip，**不得**动仓内清单（2026-10-16 裁定，§三.79）。

        这是本裁定的**正面锁**：把 `--zip` 分支摘掉、退回「写清单 + 写 zip」的老路径，
        本用例必红 —— 否则它就只是空壳。
        """
        tmp, pack, tpl = _fixture()
        try:
            self.assertEqual(_quiet(pt.main, ["--pack-dir", str(pack),
                                              "--templates-dir", str(tpl)]), 0)
            man = pack / pt.MANIFEST_NAME
            before = man.read_bytes()
            out = tmp / "别处" / "包.zip"
            out.parent.mkdir(parents=True, exist_ok=True)
            rc = _quiet(pt.main, ["--zip", str(out), "--pack-dir", str(pack),
                                  "--templates-dir", str(tpl)])
            self.assertEqual(rc, 0)
            self.assertEqual(man.read_bytes(), before,
                             "`--zip` 改写了仓内清单：打包与清单又耦合回去了（§三.79）")
            self.assertTrue(out.is_file(), "`--zip` 未产出 zip")
            self.assertEqual(out.read_bytes(), pt.build_zip_bytes(pack),
                             "落点虽在包外，内容仍须是同一份确定性 zip")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
