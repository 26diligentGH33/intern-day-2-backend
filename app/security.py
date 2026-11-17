"""密码哈希与登录凭证的生成/校验。

两条原则:
1. 密码只存 bcrypt 哈希,永不落库明文,也不出现在日志和响应里。
2. 凭证是后端随机生成的不透明字符串;数据库里只存它的 sha256,
   这样即使数据库被读走,拿到的哈希也无法当凭证使用。
"""

from __future__ import annotations

import hashlib
import secrets

import bcrypt

# bcrypt 只接受前 72 字节,超长密码先截断避免抛异常
_MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    """生成带随机盐的 bcrypt 哈希,形如 $2b$12$..."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码。哈希格式损坏时返回 False 而不是抛错。"""
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    """32 字节随机数 → URL 安全的 43 字符字符串,不可猜测、不含用户信息。"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """凭证明文只回给前端一次,库里存哈希。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
