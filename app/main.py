"""FastAPI 应用入口。

启动时做两件事:建表 + 空库补种练习账号。
关闭时不额外处理,SQLite 是文件库,不需要断开连接池。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import cors_origins, seed_demo_data
from app.db import init_db
from app.routers import auth as auth_router
from app.routers import todos as todos_router
from app.seed import seed

logger = logging.getLogger("uvicorn.error")

DESCRIPTION = """
练习项目的后端接口。

- 登录成功后拿到 Bearer 凭证,放进 `Authorization: Bearer <token>` 访问受保护接口。
- 所有 `/todos` 接口都要求登录,未携带或携带无效凭证返回 `401`。
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    if seed_demo_data():
        created = seed()
        if created:
            logger.info("已写入虚构练习账号:%s", ", ".join(created))
    yield


app = FastAPI(
    title="Intern Day 2 Backend",
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,  # 用 Bearer 头传凭证,不需要 cookie 跨域
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router.router)
app.include_router(todos_router.router)


@app.get("/health", tags=["meta"], summary="健康检查")
def health() -> dict[str, str]:
    """不需要登录,用于容器健康检查和联调前的前置确认。"""
    return {
        "status": "ok",
        "service": "intern-day-2-backend",
        "time": datetime.now(timezone.utc).isoformat(),
    }
