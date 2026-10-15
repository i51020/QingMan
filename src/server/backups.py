"""青蔓 QingMan · 历史版本（V0.0.51@r9）。

**为什么单独成文件**：`routes.py` 在 V0.0.51@r8 已达 60.9K，逼近 `verify` 7f 的
**单文件 64K** 上限；本功能（一对端点 + 枚举 + 恢复）加进去实测 66K 直接触线。
故按 V0.0.43 / V0.0.48 的同一手法拆出（`selection.js` / `templates.js` 是同因）。

**为什么要这个功能**：`_backup_editor` 早已每次保存前把当前版轮转进 `data/.bak/`，
代码注释也写明了动机「用户一次误操作 + 一次保存，上一版就永久消失」—— 但**出口一直
没做**：没有任何端点、没有任何界面能取回。用户只能自己开资源管理器、认出 17 位时间戳
文件名、改名覆盖 `editor.json`；对零基础用户等于没有。本模块就是那个出口。

**依赖方向**：本模块 `import routes`（**只为复用 `save_editor`**），routes 不反向依赖
本模块，故无循环。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from server import config, routes
from server.dtree_core import TreeError

# 列表只读；恢复是写操作（app.py 已把它并入 `_guard_write` 的覆盖面）。
EDITOR_BACKUPS_PATH = "/api/editor-backups"
EDITOR_RESTORE_PATH = "/api/editor-restore"

# 备份文件名的**完整**形态（比 routes 的 glob 严）：`editor-<8位日期>-<6位时刻>-<6位微秒>[_NNN].json`。
# 枚举时取名字里的戳当排序键 —— 回收站里的备份仍保留原戳，故归档件与在库件能放在
# 同一条时间轴上排。**这个正则才是真正的过滤器**：下面的 glob 只是粗筛。
_EDITOR_BACKUP_GLOB = "editor-*.json"
_EDITOR_BACKUP_NAME_RE = re.compile(r"^editor-(\d{8}-\d{6}-\d{6}(?:_\d{3})?)\.json$")


def _iter_editor_backups() -> "List[tuple[str, str, Path]]":
    """枚举全部历史版本 → `[(id, stamp, path)]`，按**新→旧**排序。

    `id` ＝ 相对 `data/.bak/` 的 posix 路径，**它同时是恢复请求的标识**：恢复端点拿它
    去**重新枚举一次**做白名单比对（同 `open_directory` 的枚举标识体例），不接任意路径，
    故无需再做 `..` 转义 —— 穿越串压根不会出现在枚举结果里。

    两处都收：在库的 `editor-*.json`（最近 `EDITOR_BACKUP_KEEP` 份）与轮转淘汰的
    `.bak/.trash/<戳>/editor-*.json`（**软删除，永不真删**）。少收一处，用户就少一段能
    救回来的历史 —— 而这正是本功能的全部意义。
    """
    out: "List[tuple[str, str, Path]]" = []
    bak_dir = config.EDITOR_BACKUP_DIR
    if not bak_dir.is_dir():
        return out

    def _add(path: Path) -> None:
        m = _EDITOR_BACKUP_NAME_RE.match(path.name)
        if m:
            out.append((path.relative_to(bak_dir).as_posix(), m.group(1), path))

    for path in bak_dir.glob(_EDITOR_BACKUP_GLOB):
        _add(path)
    trash = bak_dir / config.EDITOR_BACKUP_TRASH_DIRNAME
    if trash.is_dir():
        for sub in trash.iterdir():
            if sub.is_dir():
                for path in sub.glob(_EDITOR_BACKUP_GLOB):
                    _add(path)
    out.sort(key=lambda item: item[1], reverse=True)   # 戳定宽 → 名字序即时间序
    return out


def _entry(item: "tuple[str, str, Path]") -> Dict[str, Any]:
    """一条枚举结果 → 前端可渲染的一条。**单份坏掉也不抛**，只标 `broken`。"""
    bid, _stamp, path = item
    entry: Dict[str, Any] = {
        "id": bid,
        "name": path.name,
        "archived": bid.startswith(config.EDITOR_BACKUP_TRASH_DIRNAME + "/"),
        "bytes": 0, "savedAt": "", "rootName": "", "broken": False,
    }
    try:
        entry["bytes"] = path.stat().st_size
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("root"), dict):
            raise ValueError("root")
        entry["savedAt"] = str(doc.get("savedAt") or "")
        entry["rootName"] = str(doc["root"].get("name") or "")
    except (OSError, UnicodeDecodeError, ValueError):
        # 一份坏掉不该让整张列表打不开 —— 它仍要出现（用户得知道它存在），
        # 只是恢复会被 `restore_editor` 以 editorBackupCorrupt 单独挡下。
        entry["broken"] = True
    return entry


def list_editor_backups() -> Dict[str, Any]:
    """列出可恢复的历史版本（只读）。"""
    return {
        "ok": True,
        "dir": str(config.EDITOR_BACKUP_DIR),
        "keep": config.EDITOR_BACKUP_KEEP,
        "backups": [_entry(it) for it in _iter_editor_backups()],
    }


def restore_editor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """把某个历史版本**恢复为当前版本**。

    刻意**不新增写盘逻辑** —— 直接调 `routes.save_editor`。于是自动获得两条正确语义：
      ① 恢复前的那一版会先被 `_backup_editor` 轮转进 `.bak/` → **恢复本身也可回退**
         （不会「恢复错了就再也回不去」）；
      ② 结构校验、体积上限、原子替换全部沿用同一条路径，永不与保存行为漂移。
    全程只有复制 + `os.replace` 原子替换，符合「只复制不删除」硬不变量。
    """
    raw = payload.get("id")
    if not isinstance(raw, str) or not raw.strip():
        raise TreeError("editorBackupNotFound", id=str(raw))
    wanted = raw.strip()

    target = None
    for bid, _stamp, path in _iter_editor_backups():
        if bid == wanted:            # 白名单比对：只认「枚举得到的那几个 id」
            target = path
            break
    if target is None:
        raise TreeError("editorBackupNotFound", id=wanted)

    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise TreeError("editorBackupCorrupt", name=target.name)
    if not isinstance(doc, dict) or not isinstance(doc.get("root"), dict):
        raise TreeError("editorBackupCorrupt", name=target.name)

    result = routes.save_editor({"doc": doc})
    result["restored"] = {
        "id": wanted,
        "name": target.name,
        "rootName": str(doc["root"].get("name") or ""),
    }
    return result
