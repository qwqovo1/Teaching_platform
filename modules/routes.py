# modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import secrets, os, glob, shutil, hashlib, mimetypes, time
from datetime import datetime
from .database import *

router = APIRouter()
templates = Jinja2Templates(directory="templates")

active_sessions = {}
DATA_DIR = "Data"
UPLOAD_DIR = "static/uploads"
VIDEO_DIR = "static/videos"


def check_session(request: Request):
    sid = request.cookies.get("session_id")
    return active_sessions.get(sid)


# --- [1. 视频流引擎：修复黑屏] ---
def send_video_range(file_path: str, range_header: str):
    file_size = os.path.getsize(file_path)
    start, end = 0, file_size - 1
    if range_header:
        range_str = range_header.replace("bytes=", "");
        parts = range_str.split("-")
        if parts[0]: start = int(parts[0])
        if parts[1]: end = int(parts[1])
    end = min(end, file_size - 1);
    chunk_total_size = (end - start) + 1

    # 🌟 强制 MIME 为 video/mp4 解决 MOV 黑屏渲染问题
    mime_type = "video/mp4"

    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_total_size
            while remaining > 0:
                data = f.read(min(remaining, 1024 * 1024))
                if not data: break
                remaining -= len(data);
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes", "Content-Length": str(chunk_total_size),
        "Content-Type": mime_type, "Cache-Control": "public, max-age=31536000",
        "X-Content-Type-Options": "nosniff"
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)


@router.get("/video-stream/{filename}")
async def video_stream(filename: str, range: str = Header(None)):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path): raise HTTPException(status_code=404)
    return send_video_range(file_path, range)


# --- [2. 成绩单预览与下载] ---
@router.get("/view-record/{fname}")
async def view_record(request: Request, fname: str):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    # 鉴权：只能查看自己的
    if s["role"] != "admin" and not fname.startswith(s["username"]):
        raise HTTPException(status_code=403)
    file_path = os.path.join(DATA_DIR, fname)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return templates.TemplateResponse("view_record.html", {"request": request, "content": content, "filename": fname})


@router.get("/download-record/{fname}")
async def dl(request: Request, fname: str):
    s = check_session(request)
    if not s or s["role"] != "admin": raise HTTPException(status_code=403)
    return FileResponse(os.path.join(DATA_DIR, fname), filename=fname)


# --- [3. 基础页面路由] ---
@router.get("/")
async def root_path(): return RedirectResponse(url="/index")


@router.get("/index")
async def welcome_page(request: Request): return templates.TemplateResponse("index.html", {"request": request})


@router.get("/video-catalog")
async def v_catalog(request: Request): return templates.TemplateResponse("video_catalog.html", {"request": request})


@router.get("/test-catalog")
async def t_catalog(request: Request): return templates.TemplateResponse("test_catalog.html", {"request": request})


# --- [4. 鉴权与账号系统] ---
@router.get("/login-page")
async def lp(request: Request): return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register-page")
async def rp(request: Request): return templates.TemplateResponse("register.html", {"request": request})


@router.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...),
                       admin_serial: str = Form(None)):
    if role == "admin" and admin_serial != "123456":
        return templates.TemplateResponse("login.html", {"request": request, "error": "管理员验证码错误"})
    if verify_user(username, password):
        sid = secrets.token_urlsafe(32);
        active_sessions[sid] = {"username": username, "role": role}
        res = RedirectResponse("/home", 303);
        res.set_cookie("session_id", sid, httponly=True);
        return res
    return templates.TemplateResponse("login.html", {"request": request, "error": "账号密码错误"})


@router.post("/register")
async def handle_register(request: Request, username: str = Form(...), password: str = Form(...)):
    if create_user(username, password): return RedirectResponse("/login-page", 303)
    # 🌟 最小改动：提供更具体的失败提示
    return templates.TemplateResponse("register.html", {"request": request, "error": "注册失败：用户名可能已被占用"})


@router.post("/logout")
async def lo(request: Request):
    sid = request.cookies.get("session_id");
    if sid in active_sessions: del active_sessions[sid]
    res = RedirectResponse("/index", 303);
    res.delete_cookie("session_id");
    return res


# --- [5. 个人资料与进度记录] ---
@router.get("/profile")
async def profile_page(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    info = get_user_info(s["username"])
    path_pattern = os.path.join(DATA_DIR, "*_成绩单_*.txt") if s["role"] == "admin" else os.path.join(DATA_DIR,
                                                                                                      f"{s['username']}_成绩单_*.txt")
    recs = sorted([os.path.basename(x) for x in glob.glob(path_pattern)], reverse=True)
    return templates.TemplateResponse("profile.html",
                                      {"request": request, "nickname": info["nickname"], "avatar": info["avatar"],
                                       "role": s["role"], "records": recs})


@router.get("/get-video-progress")
async def g_progress(request: Request):
    s = check_session(request);
    return JSONResponse(db_get_progress(s["username"]) if s else [])


@router.post("/update-progress")
async def u_progress(request: Request, video_id: int = Form(...), progress: str = Form(...)):
    s = check_session(request);
    if s: db_update_progress(s["username"], video_id, progress)
    return {"status": "ok"}


@router.post("/update-profile")
async def up_p(request: Request, nickname: str = Form(None), avatar_file: UploadFile = File(None)):
    s = check_session(request);
    av = None
    if avatar_file and avatar_file.filename:
        fn = f"{s['username']}_av{os.path.splitext(avatar_file.filename)[1]}"
        with open(f"static/uploads/{fn}", "wb") as b: b.write(await avatar_file.read())
        av = f"/static/uploads/{fn}"
    update_user_info(s["username"], nickname, av);
    return RedirectResponse("/profile", 303)


@router.get("/change-password")
async def cp_pg(request: Request): return templates.TemplateResponse("change_password.html", {"request": request})


# --- [6. 视频管理：包含交换排序逻辑] ---
@router.get("/videos")
async def v_list(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    return templates.TemplateResponse("videos.html",
                                      {"request": request, "videos": get_all_videos(), "role": s["role"]})


@router.post("/swap-video-order")
async def swap_v(request: Request, v1_id: int = Form(...), v2_id: int = Form(...)):
    s = check_session(request)
    if s and s["role"] == "admin":
        with get_db() as conn:
            v1 = conn.execute("SELECT title, filename FROM videos WHERE id=?", (v1_id,)).fetchone()
            v2 = conn.execute("SELECT title, filename FROM videos WHERE id=?", (v2_id,)).fetchone()
            if v1 and v2:
                conn.execute("UPDATE videos SET title=?, filename=? WHERE id=?", (v2['title'], v2['filename'], v1_id))
                conn.execute("UPDATE videos SET title=?, filename=? WHERE id=?", (v1['title'], v1['filename'], v2_id))
                conn.commit()
    return RedirectResponse("/videos", 303)


@router.post("/upload-video")
async def uv(request: Request, title: str = Form(...), video_file: UploadFile = File(...)):
    s = check_session(request);
    if s and s["role"] == "admin":
        fn = f"{secrets.token_hex(4)}_{video_file.filename}"
        with open(os.path.join(VIDEO_DIR, fn), "wb") as f: f.write(await video_file.read())
        add_video(title, fn, s["username"])
    return RedirectResponse("/videos", 303)


@router.post("/delete-video")
async def dv(video_id: int = Form(...)):
    delete_video_by_id(video_id);
    return RedirectResponse("/videos", 303)


# --- [7. 测试管理：详细成绩单导出 + 题目编辑] ---
@router.get("/eeg-test")
async def eeg_test_page(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    if "test_start" not in s: s["test_start"] = time.time()
    lock = os.path.exists(os.path.join(DATA_DIR, f"{s['username']}.lock"))
    return templates.TemplateResponse("eeg_test.html",
                                      {"request": request, "questions": db_get_questions(), "role": s["role"],
                                       "answered": db_get_user_answers(s["username"]), "already_finished": lock})


@router.post("/submit-answer")
async def s_ans(request: Request, qid: int = Form(...), opt: str = Form(...)):
    s = check_session(request);
    db_submit_answer(s["username"], qid, opt);
    return {"status": "ok"}


@router.post("/finish-test")
async def finish_test(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    u = s["username"]
    if os.path.exists(os.path.join(DATA_DIR, f"{u}.lock")): return RedirectResponse("/profile", 303)

    qs = db_get_questions();
    ans = db_get_user_answers(u)
    total_score = 0;
    now = datetime.now()
    duration_sec = int(time.time() - s.get("test_start", time.time()))
    duration_str = f"{duration_sec // 60}分{duration_sec % 60}秒"

    idx = len(glob.glob(os.path.join(DATA_DIR, f"{u}_成绩单_*.txt"))) + 1
    fname = f"{u}_成绩单_{idx}.txt"
    fpath = os.path.join(DATA_DIR, fname)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"【深圳大学神经语言学实验室 - 实验报告】\n")
        f.write(f"账号/用户名: {u}\n答题时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n答题用时: {duration_str}\n")
        f.write("=" * 50 + "\n\n")

        for i, q in enumerate(qs, 1):
            ua = ans.get(q['id'], {})
            user_opt = ua.get('selected_option', '未作答')
            is_right = ua.get('is_correct', False)
            points = 1 if is_right else 0
            total_score += points

            f.write(f"题目 {i}: {q['content']}\n")
            f.write(f"选项: A:{q['option_a']} | B:{q['option_b']} | C:{q['option_c']} | D:{q['option_d']}\n")
            f.write(f"您的作答: {user_opt}\n正确答案: {q['answer']}\n")
            f.write(f"本题得分: {points}\n")
            f.write("-" * 30 + "\n")

        f.write(f"\n【最终统计结果】\n总题目数: {len(qs)}\n总得分: {total_score}\n" + "=" * 50)

    with open(os.path.join(DATA_DIR, f"{u}.lock"), "w") as lock:
        lock.write("L")
    if "test_start" in s: del s["test_start"]
    with get_db() as conn:
        conn.execute("DELETE FROM user_answers WHERE username=?", (u,)); conn.commit()
    return RedirectResponse("/profile", 303)


@router.post("/add-question")
async def aq(content: str = Form(...), option_a: str = Form(...), option_b: str = Form(...), option_c: str = Form(...),
             option_d: str = Form(...), answer: str = Form(...)):
    db_add_question(content, option_a, option_b, option_c, option_d, answer);
    return RedirectResponse("/eeg-test", 303)


@router.post("/edit-question")
async def edit_q(request: Request, qid: int = Form(...), content: str = Form(...), option_a: str = Form(...),
                 option_b: str = Form(...), option_c: str = Form(...), option_d: str = Form(...),
                 answer: str = Form(...)):
    s = check_session(request)
    if s and s["role"] == "admin":
        with get_db() as conn:
            conn.execute(
                "UPDATE questions SET content=?, option_a=?, option_b=?, option_c=?, option_d=?, answer=? WHERE id=?",
                (content, option_a, option_b, option_c, option_d, answer.upper(), qid))
            conn.commit()
    return RedirectResponse("/eeg-test", 303)


@router.post("/delete-question")
async def dq(request: Request, qid: int = Form(...)):
    s = check_session(request);
    if s and s["role"] == "admin": db_delete_question(qid)
    return RedirectResponse("/eeg-test", 303)


@router.post("/reset-all")
async def handle_reset_all(request: Request):
    s = check_session(request)
    if s and s["role"] == "admin":
        db_reset_all_answers();
        [os.remove(f) for f in glob.glob(os.path.join(DATA_DIR, "*.lock"))]
    return RedirectResponse("/profile", 303)


@router.get("/home")
async def home_pg(request: Request):
    s = check_session(request);
    info = get_user_info(s["username"])
    return templates.TemplateResponse("home.html",
                                      {"request": request, "nickname": info["nickname"], "user_avatar": info["avatar"],
                                       "role": s["role"]})