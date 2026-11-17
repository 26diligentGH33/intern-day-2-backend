"""请求/响应模型。

Pydantic 在这里承担参数校验:字段缺了、空了、超长,都会在进入业务逻辑之前
被拦下来,返回 422 和明确的字段说明。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, description="账号")
    password: str = Field(min_length=1, max_length=128, description="密码")

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("账号不能为空")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期,单位秒")


class UserOut(BaseModel):
    """只返回必要信息:不带密码哈希、不带其它敏感字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("待办内容不能为空")
        return value


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("待办内容不能为空")
        return value


class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
    created_at: str


class MessageOut(BaseModel):
    detail: str
