# modules/database.py
import sqlite3
import hashlib
import os
import random
import string
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = "users.db"

def init_db():
    """初始化所有数据表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 用户表：默认头像路径设为要求的值
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE, 
        password_hash TEXT, 
        nickname TEXT, 
        avatar TEXT DEFAULT '/static/default-avatar.png', 
        expires_at DATETIME
    )""")
    # 视频表
    c.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, filename TEXT, uploaded_by TEXT, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    # 题目表
    c.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, answer TEXT)")
    # 答题记录表
    c.execute("CREATE TABLE IF NOT EXISTS user_answers (username TEXT, question_id INTEGER, selected_option TEXT, is_correct BOOLEAN, UNIQUE(username, question_id))")
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

def hash_p(p): return hashlib.sha256(p.encode()).hexdigest()

def create_user(u, p, nickname=None):
    """创建用户，若无昵称则生成8位随机字符"""
    ph, ex = hash_p(p), datetime.now() + timedelta(days=60)
    if not nickname:
        nickname = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    try:
        with get_db() as c:
            c.execute("INSERT INTO users (username, password_hash, nickname, expires_at) VALUES (?,?,?,?)", (u,ph,nickname,ex))
            c.commit(); return True
    except: return False

def verify_user(u, p):
    ph = hash_p(p)
    with get_db() as c:
        r = c.execute("SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?", (u, datetime.now())).fetchone()
        return r and r[0] == ph

def get_user_info(u):
    with get_db() as c:
        r = c.execute("SELECT nickname, avatar FROM users WHERE username = ?", (u,)).fetchone()
        return {"nickname": r[0], "avatar": r[1]} if r else None

def update_user_info(u, n=None, a=None):
    with get_db() as c:
        if n: c.execute("UPDATE users SET nickname = ? WHERE username = ?", (n, u))
        if a: c.execute("UPDATE users SET avatar = ? WHERE username = ?", (a, u))
        c.commit()

def change_password(username, old_p, new_p):
    """修改密码逻辑"""
    old_h, new_h = hash_p(old_p), hash_p(new_p)
    with get_db() as c:
        r = c.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if r and r[0] == old_h:
            c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_h, username))
            c.commit(); return True, "修改成功"
        return False, "原密码错误"

def add_video(t, f, u):
    with get_db() as c:
        c.execute("INSERT INTO videos (title, filename, uploaded_by) VALUES (?,?,?)", (t,f,u))
        c.commit()

def get_all_videos():
    with get_db() as c: return [dict(r) for r in c.execute("SELECT * FROM videos ORDER BY uploaded_at DESC").fetchall()]

def delete_video_by_id(vid):
    with get_db() as c: c.execute("DELETE FROM videos WHERE id = ?", (vid,)); c.commit()

def db_get_questions():
    with get_db() as c: return [dict(r) for r in c.execute("SELECT * FROM questions").fetchall()]

def db_add_question(c, a, b, co, d, ans):
    with get_db() as conn:
        conn.execute("INSERT INTO questions (content, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?)", (c,a,b,co,d,ans))
        conn.commit()

def db_delete_question(qid):
    with get_db() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.commit()

def db_submit_answer(u, qid, s):
    with get_db() as conn:
        q = conn.execute("SELECT answer FROM questions WHERE id = ?", (qid,)).fetchone()
        if not q: return False
        is_c = (s == q[0])
        conn.execute("INSERT OR REPLACE INTO user_answers (username, question_id, selected_option, is_correct) VALUES (?,?,?,?)", (u, qid, s, is_c))
        conn.commit(); return is_c

def db_get_user_answers(u):
    with get_db() as conn:
        rows = conn.execute("SELECT question_id, is_correct, selected_option FROM user_answers WHERE username = ?", (u,)).fetchall()
        return {r[0]: {"is_correct": r[1], "selected": r[2]} for r in rows}

def db_reset_all_answers():
    with get_db() as conn: conn.execute("DELETE FROM user_answers"); conn.commit()