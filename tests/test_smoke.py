"""青蔓 QingMan · smoke 工具与「工具间一致性」单元测试（§P2-10 / §P2 第 17 项）。

`sandbox_base()` 在 `smoke.py` 与 `browser_smoke.py` 各有一份（同一体例）——
本文件既验其行为，也**锁住两份实现不得漂移**（§P2 第 17 项「工具间一致性」）。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_TOOLS = _HERE.parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import browser_smoke as bs  # noqa: E402
import smoke  # noqa: E402


class SandboxBaseTests(unittest.TestCase):

    def test_env_var_wins(self):
        old = os.environ.get("QM_SANDBOX")
        os.environ["QM_SANDBOX"] = "X:/my/sandbox"
        try:
            self.assertEqual(smoke.sandbox_base(), Path("X:/my/sandbox"))
        finally:
            if old is None:
                os.environ.pop("QM_SANDBOX", None)
            else:
                os.environ["QM_SANDBOX"] = old

    def test_default_follows_project_root(self):
        old = os.environ.pop("QM_SANDBOX", None)
        try:
            self.assertEqual(smoke.sandbox_base(), smoke.PROJECT_ROOT.parent.parent / "_sandbox")
        finally:
            if old is not None:
                os.environ["QM_SANDBOX"] = old

    def test_consistent_with_browser_smoke(self):
        # §P2 第 17 项「工具间一致性」：两份实现必须给出同一结果
        for env in (None, "Z:/somewhere/else"):
            old = os.environ.get("QM_SANDBOX")
            if env is None:
                os.environ.pop("QM_SANDBOX", None)
            else:
                os.environ["QM_SANDBOX"] = env
            try:
                self.assertEqual(smoke.sandbox_base(), bs.sandbox_base(),
                                 f"QM_SANDBOX={env} 时两工具不一致")
            finally:
                if old is None:
                    os.environ.pop("QM_SANDBOX", None)
                else:
                    os.environ["QM_SANDBOX"] = old


if __name__ == "__main__":
    unittest.main()
