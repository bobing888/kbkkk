"""原子文件 IO 工具。

移植自 KB github-HKUDS-Vibe-Trading.md §3 "Atomic persistence":
> Session JSON uses temporary files and replacement-style commits.
> This protects against partial writes but does not eliminate concurrent-writer races.

适用场景：
- signals/calibration.py 的本地落盘
- 任何 JSON 配置 / state 文件
- 进程崩溃 / 断电时不会出现"半写"文件损坏

注意：
- 单进程安全（原子 rename）
- 多进程并发写入**仍然不安全**——需要外加文件锁（参考 T9）
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(
    path: str | Path,
    data: Any,
    *,
    ensure_ascii: bool = False,
    indent: int | None = 2,
) -> None:
    """原子写 JSON：写临时文件 → os.replace。

    步骤：
    1. 创建父目录（若不存在）
    2. 写同目录下 .tmp 临时文件
    3. fsync 落盘
    4. os.replace 原子替换原文件

    失败时 tmp 文件会保留（不删除），便于人工排查。

    Args:
        path: 目标文件路径
        data: 可 JSON 序列化对象
        ensure_ascii: 默认 False（中文友好）
        indent: 缩进，默认 2
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 在目标同目录下创建临时文件——保证 os.replace 是原子 rename
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # 失败保留 tmp 便于排查，不删除
        raise


def atomic_read_json(path: str | Path, default: Any = None) -> Any:
    """读 JSON，读失败时返回 default（不抛异常）。"""
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


__all__ = ["atomic_write_json", "atomic_read_json"]