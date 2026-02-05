# modules/database.py
import sqlite3, hashlib, os, random, string
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = "users.db"

def init_db():
    """初始化数据库结构，包含用户、视频、题目、答案及视频进度表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 用户表：头像默认指向校徽
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, nickname TEXT, avatar TEXT DEFAULT '/static/szu_logo.png', expires_at DATETIME)")
    # 教学视频表
    c.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, filename TEXT, uploaded_by TEXT, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    # 实验测试题目表
    c.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, answer TEXT)")
    # 答题记录表：username 和 question_id 唯一绑定，用于限制答题次数
    c.execute("CREATE TABLE IF NOT EXISTS user_answers (username TEXT, question_id INTEGER, selected_option TEXT, is_correct BOOLEAN, UNIQUE(username, question_id))")
    # 视频观看进度表
    c.execute("CREATE TABLE IF NOT EXISTS video_progress (username TEXT, video_id INTEGER, progress TEXT, PRIMARY KEY(username, video_id))")
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """数据库连接上下文管理器，确保连接安全关闭"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_user(u, p):
    """注册新用户：赋予随机昵称及默认校徽头像"""
    ph = hashlib.sha256(p.encode()).hexdigest()
    ex = datetime.now() + timedelta(days=60)
    # 自动生成随机昵称，保证新账号的个性化
    nk = "用户_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    try:
        with get_db() as c:
            c.execute("INSERT INTO users (username, password_hash, nickname, expires_at) VALUES (?,?,?,?)", (u, ph, nk, ex))
            c.commit()
            return True
    except Exception as e:
        # 🌟 最小改动：打印错误原因，方便你查看为什么注册失败
        print(f"注册报错: {e}")
        return False

def verify_user(u, p):
    """校验用户登录凭证"""
    ph = hashlib.sha256(p.encode()).hexdigest()
    with get_db() as c:
        r = c.execute("SELECT password_hash FROM users WHERE username = ? AND expires_at >= ?", (u, datetime.now())).fetchone()
        return r and r[0] == ph

def get_user_info(u):
    """严格根据用户名获取资料，实现账号隔离，防止串号"""
    with get_db() as c:
        r = c.execute("SELECT nickname, avatar FROM users WHERE username = ?", (u,)).fetchone()
        return dict(r) if r else None

def db_reset_all_answers():
    """【核心恢复】：管理员特权功能，清空所有人的答题记录，释放答题机会"""
    with get_db() as conn:
        conn.execute("DELETE FROM user_answers")
        conn.commit()

def db_add_question(c, a, b, co, d, ans):
    """添加实验题目"""
    with get_db() as conn:
        conn.execute("INSERT INTO questions (content, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?)", (c,a,b,co,d,ans))
        conn.commit()

def db_update_progress(u, vid, prog):
    """更新视频观看百分比"""
    with get_db() as c:
        c.execute("INSERT OR REPLACE INTO video_progress (username, video_id, progress) VALUES (?,?,?)", (u, vid, prog))
        c.commit()

def db_get_progress(u):
    """获取指定用户的视频进度"""
    with get_db() as c:
        # 🌟 核心修复：将 Row 对象转换为标准的 dict 字典，否则前端 fetch 会报“同步失败”
        rows = c.execute("SELECT v.title, p.progress FROM video_progress p JOIN videos v ON p.video_id = v.id WHERE p.username = ?", (u,)).fetchall()
        return [dict(r) for r in rows]

def db_get_questions():
    """获取所有题目"""
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM questions").fetchall()]

def db_submit_answer(u, qid, s):
    """记录用户作答结果"""
    with get_db() as conn:
        q = conn.execute("SELECT answer FROM questions WHERE id = ?", (qid,)).fetchone()
        is_c = (s == q[0])
        conn.execute("INSERT OR REPLACE INTO user_answers (username, question_id, selected_option, is_correct) VALUES (?,?,?,?)", (u, qid, s, is_c))
        conn.commit()
        return is_c

def db_get_user_answers(u):
    """获取指定用户已回答的题目集合"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM user_answers WHERE username = ?", (u,)).fetchall()
        return {r['question_id']: dict(r) for r in rows}

def add_video(t, f, u):
    """添加视频记录"""
    with get_db() as c:
        c.execute("INSERT INTO videos (title, filename, uploaded_by) VALUES (?,?,?)", (t,f,u))
        c.commit()

def get_all_videos():
    """视频目录展示"""
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM videos ORDER BY uploaded_at DESC").fetchall()]

def delete_video_by_id(vid):
    """删除视频"""
    with get_db() as c:
        c.execute("DELETE FROM videos WHERE id = ?", (vid,))
        c.commit()

def db_delete_question(qid):
    """删除题目"""
    with get_db() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.commit()

def update_user_info(u, n=None, a=None):
    """更新个人资料（昵称、头像）"""
    with get_db() as c:
        if n: c.execute("UPDATE users SET nickname = ? WHERE username = ?", (n, u))
        if a: c.execute("UPDATE users SET avatar = ? WHERE username = ?", (a, u))
        c.commit()