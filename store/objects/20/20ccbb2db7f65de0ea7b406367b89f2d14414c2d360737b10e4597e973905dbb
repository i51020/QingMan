"""青蔓 QingMan · 服务端通用助手（与业务无关、被多处复用）。

**为什么单独成文件**：`templates` 需要原子写的唯一临时名，而 `routes` 既需要它、
又要从 `templates` 取回业务函数 —— 助手留在 `routes` 里就成环。抽到这里的条件是
**与业务无关 + 被两处以上使用**，两者缺一不进。

**不进来**：任何带 `TreeError` 业务错误码语义的东西（那是 `routes` / `templates` 的事）。
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path


def _tmp_sibling(path: Path) -> Path:
    """返回与 `path` **同目录**、**唯一命名**的临时文件路径（原子写用）。

    固定名 `<name>.tmp` 会让两个并发写**互相覆盖临时文件**、再各自 `os.replace` 抢结果
    （A-P3-2）。唯一名（pid + 随机 token）消除该竞争；仍在同一目录 → `os.replace` 依旧是
    同盘原子替换（跨盘会退化为非原子复制，故**不可**用系统临时目录）。
    """
    token = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
    return path.with_name(f"{path.name}.{token}.tmp")
