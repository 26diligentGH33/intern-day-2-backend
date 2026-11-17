"""自选功能:待办清单。所有接口都要求登录,并且只能操作自己的数据。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import db_session
from app.deps import AuthContext, get_auth
from app.schemas import MessageOut, TodoCreate, TodoOut, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])

NOT_FOUND_DETAIL = "待办不存在"


def _row_to_todo(row) -> TodoOut:
    return TodoOut(
        id=int(row["id"]),
        title=str(row["title"]),
        done=bool(row["done"]),
        created_at=str(row["created_at"]),
    )


@router.get("", response_model=list[TodoOut], summary="获取当前用户的待办列表")
def list_todos(auth: AuthContext = Depends(get_auth)) -> list[TodoOut]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, title, done, created_at
            FROM todos
            WHERE user_id = ?
            ORDER BY done ASC, id DESC
            """,
            (auth.user_id,),
        ).fetchall()
    return [_row_to_todo(row) for row in rows]


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED, summary="新增待办")
def create_todo(payload: TodoCreate, auth: AuthContext = Depends(get_auth)) -> TodoOut:
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (user_id, title, done, created_at) VALUES (?, ?, 0, ?)",
            (auth.user_id, payload.title, now),
        )
        row = conn.execute(
            "SELECT id, title, done, created_at FROM todos WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_todo(row)


@router.patch("/{todo_id}", response_model=TodoOut, summary="修改待办状态或内容")
def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    auth: AuthContext = Depends(get_auth),
) -> TodoOut:
    with db_session() as conn:
        # 带上 user_id 条件:别人的待办一律当作不存在,不能靠猜 id 越权
        current = conn.execute(
            "SELECT id, title, done, created_at FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, auth.user_id),
        ).fetchone()
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)

        title = payload.title if payload.title is not None else current["title"]
        done = int(payload.done) if payload.done is not None else int(current["done"])

        conn.execute(
            "UPDATE todos SET title = ?, done = ? WHERE id = ? AND user_id = ?",
            (title, done, todo_id, auth.user_id),
        )
        row = conn.execute(
            "SELECT id, title, done, created_at FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()
    return _row_to_todo(row)


@router.delete("/{todo_id}", response_model=MessageOut, summary="删除待办")
def delete_todo(todo_id: int, auth: AuthContext = Depends(get_auth)) -> MessageOut:
    with db_session() as conn:
        cursor = conn.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, auth.user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return MessageOut(detail="已删除")
