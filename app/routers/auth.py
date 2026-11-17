"""登录、当前用户、退出登录。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import session_ttl_seconds
from app.db import db_session
from app.deps import AuthContext, get_auth
from app.schemas import LoginRequest, LoginResponse, MessageOut, UserOut
from app.security import hash_token, new_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# 账号不存在和密码错误必须给同一句提示,否则等于告诉别人"这个账号是存在的"
LOGIN_FAILED_DETAIL = "账号或密码错误"


@router.post("/login", response_model=LoginResponse, summary="账号密码登录")
def login(payload: LoginRequest) -> LoginResponse:
    now = datetime.now(timezone.utc)

    with db_session() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()

        # 账号不存在 / 密码不匹配 → 同一个 401 提示
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=LOGIN_FAILED_DETAIL,
            )

        token = new_session_token()
        ttl = session_ttl_seconds()

        # 顺手清理这个用户已经过期的会话,避免表无限增长
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND expires_at <= ?",
            (user["id"], now.isoformat()),
        )
        conn.execute(
            """
            INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                hash_token(token),
                user["id"],
                now.isoformat(),
                (now + timedelta(seconds=ttl)).isoformat(),
            ),
        )

    return LoginResponse(access_token=token, expires_in=ttl)


@router.get("/me", response_model=UserOut, summary="获取当前登录用户")
def me(auth: AuthContext = Depends(get_auth)) -> UserOut:
    return UserOut(id=auth.user_id, username=auth.username, display_name=auth.display_name)


@router.post("/logout", response_model=MessageOut, summary="退出登录")
def logout(auth: AuthContext = Depends(get_auth)) -> MessageOut:
    # 删掉会话行 —— 退出之后,同一个凭证再拿来用就查不到了,自然 401
    with db_session() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (auth.session_id,))
    return MessageOut(detail="已退出登录")
