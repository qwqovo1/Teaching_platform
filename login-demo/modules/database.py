# login-demo/modules/database.py
from __future__ import annotations

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib

DB_PATH = "users.db"


def init_db():
    """初始化数据库表"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 创建 users 表，包含头像、昵称和过期时间字段
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                avatar TEXT DEFAULT 'default_avatar.png', -- 默认头像
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
    else:
        # 如果数据库已存在，检查并添加缺失的字段
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 检查 nickname 字段是否存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]

        if 'nickname' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")
            print("🔧 已添加 'nickname' 字段到 'users' 表")

        if 'avatar' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT 'default_avatar.png'")
            print("🔧 已添加 'avatar' 字段到 'users' 表")

        conn.commit()
        conn.close()


def clean_expired_users():
    """清理过期的用户记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()
    cursor.execute("DELETE FROM users WHERE expires_at < ?", (now,))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted_count > 0:
        print(f"🧹 已清理 {deleted_count} 条过期用户记录")


def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


@contextmanager
def get_db_connection():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def create_user(username: str, password: str, nickname: str = '') -> bool:
    """创建新用户，有效期 2 个月"""
    password_hash = hash_password(password)
    expires_at = datetime.now() + timedelta(days=60)  # 2 个月 = 60 天

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, nickname, expires_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, nickname, expires_at)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # 用户名已存在


def verify_user(username: str, password: str) -> bool:
    """验证用户凭据"""
    password_hash = hash_password(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        row = cursor.fetchone()

    return row is not None and row[0] == password_hash


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """修改密码：验证旧密码，更新新密码"""
    old_password_hash = hash_password(old_password)
    new_password_hash = hash_password(new_password)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 先验证旧密码
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        row = cursor.fetchone()

        if not row or row[0] != old_password_hash:
            return False, "原密码错误"

        # 更新密码
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_password_hash, username)
        )
        conn.commit()

    return True, "密码修改成功"


def user_exists(username: str) -> bool:
    """检查用户是否存在（且未过期）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        return cursor.fetchone() is not None


def get_user_info(username: str) -> dict | None:
    """获取用户的昵称和头像"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nickname, avatar FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        row = cursor.fetchone()
        if row:
            return {"nickname": row[0], "avatar": row[1]}
        else:
            return None


def update_user_info(username: str, nickname: str = None, avatar: str = None) -> bool:
    """更新用户的昵称和/或头像"""
    updates = []
    params = []

    if nickname is not None:
        updates.append("nickname = ?")
        params.append(nickname)
    if avatar is not None:
        updates.append("avatar = ?")
        params.append(avatar)

    if not updates:
        return False  # 没有提供任何要更新的字段

    set_clause = ", ".join(updates)
    params.append(username)  # 最后一个参数是 WHERE 条件的 username

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {set_clause} WHERE username = ?", params)
        conn.commit()
        # 检查是否有行被更新
        return cursor.rowcount > 0