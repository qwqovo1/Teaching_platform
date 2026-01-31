# modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import secrets, os, glob, shutil, hashlib
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


# --- [优化：边下边播增强引擎，大幅提升内网穿透下的流畅度] ---
def send_video_range(file_path: str, range_header: str):
    file_size = os.path.getsize(file_path)
    start, end = 0, file_size - 1

    if range_header:
        range_str = range_header.replace("bytes=", "")
        parts = range_str.split("-")
        if parts[0]: start = int(parts[0])
        if parts[1]: end = int(parts[1])

    end = min(end, file_size - 1)
    chunk_total_size = (end - start) + 1

    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_total_size
            while remaining > 0:
                # 采用 1MB 级动态缓冲区，减少网络往返延迟
                chunk_to_read = min(remaining, 1024 * 1024)
                data = f.read(chunk_to_read)
                if not data: break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_total_size),
        "Content-Type": "video/mp4",
        "Cache-Control": "public, max-age=31536000", # 强缓存策略
        "X-Content-Type-Options": "nosniff"
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)


@router.get("/video-stream/{filename}")
async def video_stream(filename: str, range: str = Header(None)):
    """边下边播路由引擎"""
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    return send_video_range(file_path, range)


# --- [1] 入口与分类页 ---
@router.get("/")
async def root_path():
    """修复根目录访问"""
    return RedirectResponse(url="/index")

@router.get("/index")
async def welcome_page(request: Request): return templates.TemplateResponse("index.html", {"request": request})


@router.get("/video-catalog")
async def v_catalog(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    return templates.TemplateResponse("video_catalog.html", {"request": request})


@router.get("/test-catalog")
async def t_catalog(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/login-page")
    return templates.TemplateResponse("test_catalog.html", {"request": request})


# --- [2] 鉴权路由 ---
@router.get("/login-page")
async def lp(request: Request): return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register-page")
async def rp(request: Request): return templates.TemplateResponse("register.html", {"request": request})


@router.post("/login")
async def handle_login(username: str = Form(...), password: str = Form(...), role: str = Form(...),
                       admin_serial: str = Form(None)):
    if role == "admin" and admin_serial != "123456":
        return templates.TemplateResponse("login.html", {"request": {}, "error": "管理员序列号错误"})
    if verify_user(username, password):
        sid = secrets.token_urlsafe(32)
        active_sessions[sid] = {"username": username, "role": role}
        res = RedirectResponse("/home", 303)
        res.set_cookie("session_id", sid, httponly=True)
        return res
    return templates.TemplateResponse("login.html", {"request": {}, "error": "账号或密码错误"})


@router.post("/register")
async def handle_register(username: str = Form(...), password: str = Form(...)):
    if create_user(username, password): return RedirectResponse("/login-page", 303)
    return templates.TemplateResponse("register.html", {"request": {}, "error": "注册失败"})


@router.post("/logout")
async def lo(request: Request):
    sid = request.cookies.get("session_id")
    if sid in active_sessions: del active_sessions[sid]
    res = RedirectResponse("/index", 303)
    res.delete_cookie("session_id")
    return res


# --- [3] 个人中心与进度 ---
@router.get("/profile")
async def profile_page(request: Request):
    s = check_session(request)
    if not s: return RedirectResponse("/login-page")
    info = get_user_info(s["username"])
    recs = [os.path.basename(x) for x in glob.glob(os.path.join(DATA_DIR, f"{s['username']}-成绩单-*.txt"))]
    return templates.TemplateResponse("profile.html",
                                      {"request": request, "nickname": info["nickname"], "avatar": info["avatar"],
                                       "role": s["role"], "records": recs})


@router.get("/get-video-progress")
async def g_progress(request: Request):
    s = check_session(request)
    if not s: return JSONResponse([])
    return JSONResponse([{"title": r["title"], "progress": r["progress"]} for r in db_get_progress(s["username"])])


@router.post("/update-progress")
async def u_progress(request: Request, video_id: int = Form(...), progress: str = Form(...)):
    s = check_session(request)
    if s: db_update_progress(s["username"], video_id, progress)
    return {"status": "ok"}


# --- [4] 实验答题核心 (序号命名+锁定) ---
@router.get("/eeg-test")
async def eeg_test_page(request: Request):
    s = check_session(request)
    if not s: return RedirectResponse("/login-page")
    already_finished = os.path.exists(os.path.join(DATA_DIR, f"{s['username']}.lock"))
    return templates.TemplateResponse("eeg_test.html", {
        "request": request, "questions": db_get_questions(),
        "role": s["role"], "answered": db_get_user_answers(s["username"]),
        "already_finished": already_finished
    })


@router.post("/finish-test")
async def finish_test(request: Request):
    s = check_session(request)
    if not s: return RedirectResponse("/login-page")
    u = s["username"]
    if os.path.exists(os.path.join(DATA_DIR, f"{u}.lock")): return RedirectResponse("/profile", 303)

    qs = db_get_questions()
    ans = db_get_user_answers(u)
    if not ans: return RedirectResponse("/eeg-test", 303)

    score = sum(1 for v in ans.values() if v["is_correct"])
    idx = len(glob.glob(os.path.join(DATA_DIR, f"{u}-成绩单-*.txt"))) + 1
    filepath = os.path.join(DATA_DIR, f"{u}-成绩单-{idx}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"实验成绩单 | 账号: {u} | 得分: {score}/{len(qs)} | 时间: {datetime.now()}\n" + "=" * 50 + "\n")
        for i, q in enumerate(qs, 1):
            a = ans.get(q['id'], {})
            tag = "√" if a.get('is_correct') else "×"
            f.write(
                f"题{i}: {q['content']}\n选项: A:{q['option_a']} B:{q['option_b']} C:{q['option_c']} D:{q['option_d']}\n")
            f.write(f"用户选择: {a.get('selected_option', '-')} | 判定: {tag}\n\n")

    with open(os.path.join(DATA_DIR, f"{u}.lock"), "w") as lock:
        lock.write("locked")
    with get_db() as conn:
        conn.execute("DELETE FROM user_answers WHERE username = ?", (u,))
        conn.commit()
    return RedirectResponse("/profile", 303)


# --- [5] 管理员功能 ---
@router.post("/reset-all")
async def handle_reset_all(request: Request):
    s = check_session(request)
    if s and s["role"] == "admin":
        db_reset_all_answers()
        for f in glob.glob(os.path.join(DATA_DIR, "*.lock")):
            try: os.remove(f)
            except: pass
    return RedirectResponse("/profile", 303)


@router.post("/add-question")
async def aq(content: str = Form(...), option_a: str = Form(...), option_b: str = Form(...), option_c: str = Form(...),
             option_d: str = Form(...), answer: str = Form(...)):
    db_add_question(content, option_a, option_b, option_c, option_d, answer)
    return RedirectResponse("/eeg-test", 303)


@router.post("/upload-video")
async def uv(request: Request, title: str = Form(...), video_file: UploadFile = File(...)):
    s = check_session(request)
    if s and s["role"] == "admin":
        fn = f"{secrets.token_hex(4)}_{video_file.filename}"
        with open(os.path.join(VIDEO_DIR, fn), "wb") as f: f.write(await video_file.read())
        add_video(title, fn, s["username"])
    return RedirectResponse("/videos", 303)


# --- [其他路由] ---
@router.get("/videos")
async def v_list(request: Request):
    s = check_session(request)
    if not s: return RedirectResponse("/login-page")
    return templates.TemplateResponse("videos.html",
                                      {"request": request, "videos": get_all_videos(), "role": s["role"]})


@router.post("/submit-answer")
async def s_ans(request: Request, qid: int = Form(...), opt: str = Form(...)):
    s = check_session(request)
    db_submit_answer(s["username"], qid, opt)
    return {"status": "ok"}


@router.post("/update-profile")
async def up_p(request: Request, nickname: str = Form(None), avatar_file: UploadFile = File(None)):
    s = check_session(request)
    av = None
    if avatar_file and avatar_file.filename:
        fn = f"{s['username']}_av{os.path.splitext(avatar_file.filename)[1]}"
        with open(f"static/uploads/{fn}", "wb") as b: b.write(await avatar_file.read())
        av = f"/static/uploads/{fn}"
    update_user_info(s["username"], nickname, av)
    return RedirectResponse("/profile", 303)


@router.get("/home")
async def home_pg(request: Request):
    s = check_session(request); info = get_user_info(s["username"])
    return templates.TemplateResponse("home.html",
                                      {"request": request, "nickname": info["nickname"], "user_avatar": info["avatar"],
                                       "role": s["role"]})


@router.get("/download-record/{fname}")
async def dl(fname: str): return FileResponse(os.path.join(DATA_DIR, fname))

@router.get("/change-password")
async def cp_pg(request: Request): return templates.TemplateResponse("change_password.html", {"request": request})

@router.post("/delete-question")
async def dq(qid: int = Form(...)):
    db_delete_question(qid); return RedirectResponse("/eeg-test", 303)

@router.post("/delete-video")
async def dv(video_id: int = Form(...)):
    delete_video_by_id(video_id); return RedirectResponse("/videos", 303)