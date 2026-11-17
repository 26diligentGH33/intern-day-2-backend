"""集中读取环境变量。

所有可调参数都从这里读,业务代码不直接 os.getenv,方便在 README 里一次性说明。
"""

from __future__ import annotations

import os
from pathlib import Path

# app/config.py 的上一级就是仓库根目录
BASE_DIR = Path(__file__).resolve().parent.parent


def database_path() -> Path:
    """SQLite 文件位置。相对路径按仓库根目录解析。"""
    raw = os.getenv("DATABASE_PATH", "data/app.db")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    # 目录不存在时 SQLite 会自动建文件但不会建目录,这里先补上
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def session_ttl_seconds() -> int:
    """登录凭证有效期。默认 8 小时;自测时可以调成 1 分钟验证过期。"""
    return int(os.getenv("SESSION_TTL_MINUTES", "480")) * 60


def cors_origins() -> list[str]:
    """允许跨域访问的前端来源,逗号分隔。"""
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def seed_demo_data() -> bool:
    """启动时是否在空库里写入虚构练习账号。默认开启,方便他人一键复现。"""
    return os.getenv("SEED_DEMO_DATA", "true").lower() in {"1", "true", "yes"}
