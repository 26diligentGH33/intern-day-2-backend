"""依赖注入:从 Authorization 头解析出当前登录用户。

这是"后端独立鉴权"的核心 —— 前端的路由保护只是体验优化,真正的门在这里。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status

from app.db import db_session
from app.security import hash_token

# 未登录、凭证伪造、过期、已退出,统一返回这一句话,避免把细节泄露给攻击者
UNAUTHORIZED_DETAIL = "登录状态无效或已过期,请重新登录"


@dataclass(frozen=True)
class AuthContext:
    user_id: int
    username: str
    display_name: str
    session_id: int


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def get_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthContext:
    """受保护接口都挂这个依赖。校验顺序:请求头格式 → 凭证是否存在 → 是否过期。"""
    token = _extract_bearer(authorization)
    now = datetime.now(timezone.utc).isoformat()

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.expires_at,
                   u.id AS user_id, u.username, u.display_name
            FROM sessions AS s
            JOIN users AS u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (hash_token(token),),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=UNAUTHORIZED_DETAIL,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 过期凭证视为无效,顺手清掉
        if row["expires_at"] <= now:
            conn.execute("DELETE FROM sessions WHERE id = ?", (row["session_id"],))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=UNAUTHORIZED_DETAIL,
                headers={"WWW-Authenticate": "Bearer"},
            )

    return AuthContext(
        user_id=int(row["user_id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        session_id=int(row["session_id"]),
    )


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, username, display_name FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


__all__ = ["AuthContext", "Depends", "UNAUTHORIZED_DETAIL", "get_auth", "get_user_by_id"]
