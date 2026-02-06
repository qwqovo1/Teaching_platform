import sqlite3, hashlib, os, random, string
from datetime import datetime, timedelta
from contextlib import contextmanager

USER_DB = "users.db"
RES_DB = "resources.db"


def init_db():
    """初始化双数据库：包含自动检查并补全字段逻辑"""
    # 1. 用户数据库初始化
    with get_user_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE, 
            password TEXT, 
            nickname TEXT, 
            avatar TEXT DEFAULT '/static/szu_logo.png', 
            expires_at DATETIME)""")

        # 🌟 自动修复逻辑：检查是否存在 role 字段，没有则添加
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'role' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
            print("🔧 已自动补全 users 表的 role 字段")

        conn.execute("""CREATE TABLE IF NOT EXISTS user_answers (
            username TEXT, 
            question_id INTEGER, 
            selected_option TEXT, 
            is_correct BOOLEAN, 
            UNIQUE(username, question_id))""")

        conn.execute("""CREATE TABLE IF NOT EXISTS video_progress (
            username TEXT, 
            video_id INTEGER, 
            progress TEXT, 
            PRIMARY KEY(username, video_id))""")
        conn.commit()

    # 2. 资源数据库初始化
    with get_res_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            title TEXT, 
            filename TEXT, 
            uploaded_by TEXT, 
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            content TEXT, 
            option_a TEXT, 
            option_b TEXT, 
            option_c TEXT, 
            option_d TEXT, 
            answer TEXT)""")
        conn.commit()


@contextmanager
def get_user_db():
    conn = sqlite3.connect(USER_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_res_db():
    conn = sqlite3.connect(RES_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_user(u, p):
    ph = hashlib.sha256(p.encode()).hexdigest()
    ex = datetime.now() + timedelta(days=60)
    nk = "学研员_" + ''.join(random.choices(string.ascii_letters + string.digits, k=4))
    try:
        with get_user_db() as c:
            c.execute("INSERT INTO users (username, password, nickname, expires_at, role) VALUES (?,?,?,?,?)",
                      (u, ph, nk, ex, 'student'))
            c.commit()
            return True
    except Exception as e:
        print(f"注册失败: {e}")
        return False


def verify_user(u, p):
    ph = hashlib.sha256(p.encode()).hexdigest()
    with get_user_db() as c:
        r = c.execute("SELECT password FROM users WHERE username = ? AND expires_at >= ?",
                      (u, datetime.now())).fetchone()
        return r and r['password'] == ph


def get_user_info(u):
    with get_user_db() as c:
        r = c.execute("SELECT nickname, avatar, role FROM users WHERE username = ?", (u,)).fetchone()
        return dict(r) if r else None


def db_get_all_users():
    with get_user_db() as c:
        rows = c.execute("SELECT username, nickname, avatar, role, expires_at FROM users").fetchall()
        return [dict(r) for r in rows]


def db_delete_user(u):
    with get_user_db() as c:
        c.execute("DELETE FROM users WHERE username = ?", (u,))
        c.execute("DELETE FROM user_answers WHERE username = ?", (u,))
        c.execute("DELETE FROM video_progress WHERE username = ?", (u,))
        c.commit()
    return True


def update_user_info(u, n=None, a=None):
    with get_user_db() as c:
        if n: c.execute("UPDATE users SET nickname = ? WHERE username = ?", (n, u))
        if a: c.execute("UPDATE users SET avatar = ? WHERE username = ?", (a, u))
        c.commit()


def add_video(t, f, u):
    with get_res_db() as c:
        c.execute("INSERT INTO videos (title, filename, uploaded_by) VALUES (?, ?, ?)", (t, f, u))
        c.commit()


def get_all_videos():
    with get_res_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM videos ORDER BY uploaded_at DESC").fetchall()]


def delete_video_by_id(vid):
    with get_res_db() as c:
        c.execute("DELETE FROM videos WHERE id = ?", (vid,))
        c.commit()


def db_get_questions():
    with get_res_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM questions").fetchall()]


def db_add_question(c, a, b, co, d, ans):
    with get_res_db() as conn:
        conn.execute(
            "INSERT INTO questions (content, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?)",
            (c, a, b, co, d, ans))
        conn.commit()


def db_delete_question(qid):
    with get_res_db() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.commit()


def db_submit_answer(u, qid, s):
    with get_res_db() as r_conn:
        q = r_conn.execute("SELECT answer FROM questions WHERE id = ?", (qid,)).fetchone()
    if q:
        is_c = (s == q['answer'])
        with get_user_db() as u_conn:
            u_conn.execute(
                "INSERT OR REPLACE INTO user_answers (username, question_id, selected_option, is_correct) VALUES (?,?,?,?)",
                (u, qid, s, is_c))
            u_conn.commit()
            return is_c
    return False


def db_get_user_answers(u):
    with get_user_db() as conn:
        rows = conn.execute("SELECT * FROM user_answers WHERE username = ?", (u,)).fetchall()
        return {r['question_id']: dict(r) for r in rows}


def db_update_progress(u, vid, prog):
    with get_user_db() as c:
        c.execute("INSERT OR REPLACE INTO video_progress (username, video_id, progress) VALUES (?,?,?)", (u, vid, prog))
        c.commit()


def db_get_progress(u):
    with get_user_db() as u_conn:
        progs = u_conn.execute("SELECT video_id, progress FROM video_progress WHERE username = ?", (u,)).fetchall()
    with get_res_db() as r_conn:
        v_map = {row['id']: row['title'] for row in r_conn.execute("SELECT id, title FROM videos").fetchall()}
    return [{"title": v_map.get(p['video_id'], "已删视频"), "progress": p['progress']} for p in progs]


def db_reset_all_answers():
    with get_user_db() as conn:
        conn.execute("DELETE FROM user_answers")
        conn.commit()