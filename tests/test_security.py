"""青蔓 · 安全响应头单测（V0.2.1 · 安全审计）。

静态守卫（`verify` 7as）只能证明「声明还在源码里」，证明不了：
  ① 这些头**真的**被 `_send()` 发出（可能声明了却忘了遍历发送）；
  ② CSP 没有被悄悄放宽（比如为了图省事加回 `'unsafe-inline'`）；
  ③ Server 头是否仍然泄露解释器版本。
故此处从**模块对象**直接取值断言，与黑盒探针（真起服务读响应头）互为补角。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = (Path(os.environ["QM_SRC"]).resolve()
        if os.environ.get("QM_SRC") else _HERE.parents[1] / "src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from server import app  # noqa: E402

REQUIRED = {
    "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
    "Cross-Origin-Resource-Policy", "Content-Security-Policy",
}


class SecurityHeaderTests(unittest.TestCase):
    def test_required_headers_are_declared_once(self):
        names = [name for name, _value in app.SECURITY_HEADERS]
        self.assertEqual(len(names), len(set(names)), "响应头重复声明")
        self.assertLessEqual(REQUIRED, set(names), "缺少必需的安全响应头")

    def test_header_values_are_the_strict_ones(self):
        table = dict(app.SECURITY_HEADERS)
        # 阻断**跨源**嵌套即可；'none' 会把自家探针页（同源 iframe）一起挡掉
        self.assertEqual(table["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(table["X-Content-Type-Options"], "nosniff")
        self.assertEqual(table["Referrer-Policy"], "no-referrer")
        self.assertEqual(table["Cross-Origin-Resource-Policy"], "same-origin")

    def test_csp_is_strict(self):
        csp = dict(app.SECURITY_HEADERS)["Content-Security-Policy"]
        for directive in ("default-src 'self'", "script-src 'self'", "style-src 'self'",
                          "object-src 'none'", "base-uri 'none'",
                          "form-action 'none'", "frame-ancestors 'self'"):
            self.assertIn(directive, csp, f"CSP 缺 {directive}")
        self.assertNotIn("unsafe-inline", csp, "CSP 不应放开内联（页面无内联脚本/样式）")
        self.assertNotIn("unsafe-eval", csp, "CSP 不应放开 eval")
        # 图标册用 data: 的 SVG mask，必须保留这一项，否则整套图标会消失
        self.assertIn("img-src 'self' data:", csp)

    def test_server_header_hides_python_version(self):
        handler = object.__new__(app.Handler)
        handler.server_version = "QingMan/V0.0.0"
        self.assertEqual(app.Handler.version_string(handler), "QingMan/V0.0.0")
        self.assertNotIn("Python", app.Handler.version_string(handler))


if __name__ == "__main__":
    unittest.main()
