"""虚构练习账号的初始化。

两种用法:
1. 启动时自动补种(app.main 的 lifespan 里调用),库空才写,不会覆盖你改过的密码。
2. 手动执行:uv run python -m app.seed
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import seed_demo_data
from app.db import db_session, init_db
from app.security import hash_password

# 全部是虚构数据,密码只出现在这里和 README 的"练习账号"一节
DEMO_USERS: list[tuple[str, str, str]] = [
    ("alice", "Alice 的练习空间", "Passw0rd!2027"),
    ("bob", "Bob 的练习空间", "Passw0rd!2027"),
]

DEMO_TODOS: dict[str, list[tuple[str, bool]]] = {
    "alice": [
        ("读完 FastAPI 官方教程的教程章节", True),
        ("给待办接口补一个按状态筛选的参数", False),
        ("把 PR 描述里的验证记录补全", False),
    ],
    "bob": [
        ("确认 docker compose up 能起来", True),
        ("截图登录成功页面", False),
    ],
}


def seed(force: bool = False) -> list[str]:
    """写入练习账号。返回本次实际新建的账号名。

    force=False 时,只要用户表非空就整体跳过,避免每次重启都重复插入。
    """
    init_db()
    created: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    with db_session() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if existing and not force:
            return created

        for username, display_name, password in DEMO_USERS:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, display_name, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, display_name, hash_password(password), now),
                )
                user_id = cursor.lastrowid
                created.append(username)
            else:
                user_id = row["id"]

            # 只给新建的账号补几条示例待办,让空列表状态也能被验证
            if username in DEMO_TODOS and not conn.execute(
                "SELECT 1 FROM todos WHERE user_id = ? LIMIT 1", (user_id,)
            ).fetchone():
                for title, done in DEMO_TODOS[username]:
                    conn.execute(
                        "INSERT INTO todos (user_id, title, done, created_at) VALUES (?, ?, ?, ?)",
                        (user_id, title, int(done), now),
                    )

    return created


def main() -> None:
    created = seed(force=False)
    if created:
        print(f"[seed] 已创建练习账号:{', '.join(created)}")
    else:
        print("[seed] 用户表已有数据,未做任何修改")
    print("[seed] 账号 / 密码:")
    for username, display_name, password in DEMO_USERS:
        print(f"  - {username} / {password}  ({display_name})")


if __name__ == "__main__":
    main()
