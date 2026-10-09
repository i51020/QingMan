"""青蔓 QingMan · 业务路由。

每个函数只负责「收数据 → 交给核心逻辑 → 返回可序列化 dict」，
不碰 HTTP 细节，便于后续 CLI / 测试直接调用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from server import config, dtree_core
from server.dtree_core import TreeError

GENERATE_PATH = "/api/generate"
HEALTH_PATH = "/api/health"


def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "app": config.APP_NAME_EN,
        "nameZh": config.APP_NAME_ZH,
        "version": config.read_version(),
    }


def generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    tree = payload.get("tree")
    if not isinstance(tree, dict):
        raise TreeError("treeMissing")

    target = payload.get("target")
    if not isinstance(target, str) or not target.strip():
        raise TreeError("targetMissing")

    base = Path(target.strip()).expanduser()

    root = payload.get("root")
    root = root.strip() if isinstance(root, str) else ""
    if root:
        ok, reason = dtree_core.validate_segment(root)
        if not ok:
            raise TreeError(
                "segmentInvalid", name=root, reason=dtree_core.message(reason, name=root)
            )
        base = base / root

    result = dtree_core.build_tree(tree, base, dry_run=bool(payload.get("dryRun")))
    result["ok"] = True
    return result
