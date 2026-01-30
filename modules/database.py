# modules/database.py
from __future__ import annotations

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT DEFAULT '',
        avatar TEXT DEFAULT '/static/icons/default.png',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL
    )""")

    # 视频表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL UNIQUE,
        uploaded_by TEXT NOT NULL,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # 题目表 (新增)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        answer TEXT NOT NULL
    )""")

    # 用户答题记录表 (新增)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        question_id INTEGER NOT NULL,
        selected_option TEXT NOT NULL,
        is_correct BOOLEAN NOT NULL,
        UNIQUE(username, question_id)
    )""")

    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# --- 用户与视频函数 (保持原有) ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, password: str, nickname: str = '') -> bool:
    password_hash = hash_password(password)
    expires_at = datetime.now() + timedelta(days=60)
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (username, password_hash, nickname, expires_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, nickname, expires_at))
            conn.commit()
            return True
    except: return False

def verify_user(username: str, password: str) -> bool:
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?", (username, datetime.now())).fetchone()
        return row is not None and row[0] == password_hash

def get_user_info(username: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT nickname, avatar FROM users WHERE username = ?", (username,)).fetchone()
        return {"nickname": row[0], "avatar": row[1]} if row else None

def update_user_info(username: str, nickname: str = None, avatar: str = None) -> bool:
    with get_db_connection() as conn:
        if nickname: conn.execute("UPDATE users SET nickname = ? WHERE username = ?", (nickname, username))
        if avatar: conn.execute("UPDATE users SET avatar = ? WHERE username = ?", (avatar, username))
        conn.commit()
        return True

def add_video(title, filename, uploaded_by):
    with get_db_connection() as conn:
        try:
            conn.execute("INSERT INTO videos (title, filename, uploaded_by) VALUES (?, ?, ?)", (title, filename, uploaded_by))
            conn.commit()
            return True
        except: return False

def get_all_videos():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY uploaded_at DESC").fetchall()
        return [dict(row) for row in rows]

def delete_video_by_id(video_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
        return True

# --- 题目相关函数 (新增) ---
def db_get_questions():
    with get_db_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM questions").fetchall()]

def db_add_question(content, a, b, c, d, ans):
    with get_db_connection() as conn:
        conn.execute("INSERT INTO questions (content, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?)",
                     (content, a, b, c, d, ans))
        conn.commit()

def db_delete_question(qid):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.execute("DELETE FROM user_answers WHERE question_id = ?", (qid,))
        conn.commit()

def db_submit_answer(username, qid, selected):
    with get_db_connection() as conn:
        q = conn.execute("SELECT answer FROM questions WHERE id = ?", (qid,)).fetchone()
        if not q: return None
        is_correct = (selected == q['answer'])
        conn.execute("INSERT OR REPLACE INTO user_answers (username, question_id, selected_option, is_correct) VALUES (?,?,?,?)",
                     (username, qid, selected, is_correct))
        conn.commit()
        return is_correct

def db_get_user_answers(username):
    with get_db_connection() as conn:
        rows = conn.execute("SELECT question_id, is_correct, selected_option FROM user_answers WHERE username = ?", (username,)).fetchall()
        return {r['question_id']: {"is_correct": r['is_correct'], "selected": r['selected_option']} for r in rows}

def db_reset_all_answers():
    with get_db_connection() as conn:
        conn.execute("DELETE FROM user_answers")
        conn.commit()