# login-demo/modules/database.py
from __future__ import annotations
import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib

DB_PATH = "users.db"

def init_db():
    """初始化数据库（用户表 + 视频表）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 用户表：username 是唯一标识
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,  -- ← 唯一约束
        password_hash TEXT NOT NULL,
        nickname TEXT DEFAULT '',
        avatar TEXT DEFAULT 'default_avatar.png',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL
    )
    """)

    # 视频表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL UNIQUE,
        uploaded_by TEXT NOT NULL,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    # 兼容旧数据库：检查并添加缺失字段
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'nickname' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")
        print("🔧 已添加 'nickname' 字段")
    if 'avatar' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT 'default_avatar.png'")
        print("🔧 已添加 'avatar' 字段")
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def clean_expired_users():
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
    return hashlib.sha256(password.encode()).hexdigest()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# --- 用户相关函数 ---
def create_user(username: str, password: str, nickname: str = '') -> bool:
    password_hash = hash_password(password)
    expires_at = datetime.now() + timedelta(days=60)
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
    old_password_hash = hash_password(old_password)
    new_password_hash = hash_password(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        row = cursor.fetchone()
        if not row or row[0] != old_password_hash:
            return False, "原密码错误"
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_password_hash, username)
        )
        conn.commit()
        return True, "密码修改成功"

def user_exists(username: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE username = ? AND expires_at >= ?",
            (username, datetime.now())
        )
        return cursor.fetchone() is not None

def get_user_info(username: str) -> dict | None:
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
    updates = []
    params = []
    if nickname is not None:
        updates.append("nickname = ?")
        params.append(nickname)
    if avatar is not None:
        updates.append("avatar = ?")
        params.append(avatar)
    if not updates:
        return False
    set_clause = ", ".join(updates)
    params.append(username)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {set_clause} WHERE username = ?", params)
        conn.commit()
        return cursor.rowcount > 0  # ← 只更新，不创建

# --- 视频相关函数 ---
def add_video(title: str, filename: str, uploaded_by: str) -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO videos (title, filename, uploaded_by) VALUES (?, ?, ?)",
                (title, filename, uploaded_by)
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def get_all_videos() -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, filename, uploaded_by, uploaded_at FROM videos ORDER BY uploaded_at DESC")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "filename": row[2],
                "uploaded_by": row[3],
                "uploaded_at": row[4]
            }
            for row in rows
        ]

# 新增：删除视频（需验证密码）
def delete_video_by_id(video_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 先查文件名用于删除物理文件
        cursor.execute("SELECT filename FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row:
            return False
        filename = row[0]
        # 删除数据库记录
        cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        if deleted:
            # 删除物理文件
            file_path = os.path.join("static/videos", filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        return deleted