# modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import secrets, os, glob, shutil, hashlib, mimetypes, time, zipfile, io
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


# --- [1. 视频流引擎] ---
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
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_total_size),
        "Content-Type": mime_type,
        "Cache-Control": "public, max-age=31536000",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
        "Connection": "keep-alive"
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)


@router.get("/video-stream/{filename}")
async def video_stream(filename: str, range: str = Header(None)):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path): raise HTTPException(status_code=404)
    return send_video_range(file_path, range)


# --- [2. 账号管理（新增搜索与批量功能）] ---
@router.get("/admin/users")
async def admin_user_page(request: Request, q: str = ""):
    s = check_session(request)
    if not s or s["role"] != "admin": return RedirectResponse("/index")
    users = db_get_all_users()
    if q:
        users = [u for u in users if q.lower() in u['username'].lower() or q.lower() in u['nickname'].lower()]
    return templates.TemplateResponse("admin_users.html",
                                      {"request": request, "users": users, "role": s["role"], "search_q": q})


@router.post("/admin/delete-user")
async def handle_delete_user(request: Request, target_user: str = Form(...)):
    s = check_session(request)
    if not s or s["role"] != "admin": return JSONResponse({"status": "error", "msg": "权限不足"}, status_code=403)
    if target_user == s["username"]: return JSONResponse({"status": "error", "msg": "不能注销自己"}, status_code=400)
    db_delete_user(target_user)
    lock_file = os.path.join(DATA_DIR, f"{target_user}.lock")
    if os.path.exists(lock_file): os.remove(lock_file)
    return JSONResponse({"status": "ok"})


@router.post("/admin/batch-delete-users")
async def batch_delete_users(request: Request, usernames: list = Form(...)):
    s = check_session(request)
    if not s or s["role"] != "admin": raise HTTPException(status_code=403)
    for u in usernames:
        if u != s["username"]:
            db_delete_user(u)
            lock_f = os.path.join(DATA_DIR, f"{u}.lock")
            if os.path.exists(lock_f): os.remove(lock_f)
    return RedirectResponse("/admin/users", 303)


# --- [3. 成绩单管理与批量下载] ---
@router.get("/view-record/{fname}")
async def view_record(request: Request, fname: str):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    if s["role"] != "admin" and not fname.startswith(s["username"]): raise HTTPException(status_code=403)
    file_path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(file_path): raise HTTPException(status_code=404)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return templates.TemplateResponse("view_record.html", {"request": request, "content": content, "filename": fname})


@router.get("/download-record/{fname}")
async def dl(request: Request, fname: str):
    s = check_session(request)
    if not s: return RedirectResponse("/index")
    if s["role"] == "admin" or fname.startswith(s["username"]):
        file_path = os.path.join(DATA_DIR, fname)
        if os.path.exists(file_path): return FileResponse(file_path, filename=fname)
    raise HTTPException(status_code=403)


@router.post("/admin/batch-delete-records")
async def batch_delete_records(request: Request, filenames: list = Form(...)):
    s = check_session(request)
    if not s or s["role"] != "admin": raise HTTPException(status_code=403)
    for f in filenames:
        fpath = os.path.join(DATA_DIR, os.path.basename(f))
        if os.path.exists(fpath): os.remove(fpath)
    return RedirectResponse("/profile", 303)


@router.post("/admin/batch-download-records")
async def batch_download_records(request: Request, filenames: list = Form(...)):
    s = check_session(request)
    if not s or s["role"] != "admin": raise HTTPException(status_code=403)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for fname in filenames:
            safe_name = os.path.basename(fname)
            fpath = os.path.join(DATA_DIR, safe_name)
            if os.path.exists(fpath): zip_file.write(fpath, safe_name)
    zip_buffer.seek(0)
    return StreamingResponse(zip_buffer, media_type="application/x-zip-compressed", headers={
        "Content-Disposition": f"attachment; filename=Batch_Records_{int(time.time())}.zip"})


# --- [4. 基础路由] ---
@router.get("/")
async def root_path(): return RedirectResponse(url="/index")


@router.get("/index")
async def welcome_page(request: Request): return templates.TemplateResponse("index.html", {"request": request})


@router.get("/home")
async def home_pg(request: Request):
    s = check_session(request)
    if not s: return RedirectResponse("/index")
    info = get_user_info(s["username"])
    return templates.TemplateResponse("home.html",
                                      {"request": request, "nickname": info["nickname"], "user_avatar": info["avatar"],
                                       "role": s["role"]})


@router.get("/video-catalog")
async def v_catalog(request: Request):
    if not check_session(request): return RedirectResponse("/index")
    return templates.TemplateResponse("video_catalog.html", {"request": request})


@router.get("/test-catalog")
async def t_catalog(request: Request):
    if not check_session(request): return RedirectResponse("/index")
    return templates.TemplateResponse("test_catalog.html", {"request": request})


# --- [5. 鉴权与账号系统] ---
@router.get("/login-page")
async def lp(request: Request): return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register-page")
async def rp(request: Request): return templates.TemplateResponse("register.html", {"request": request})


@router.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...),
                       admin_serial: str = Form(None)):
    if role == "admin" and admin_serial != "123456": return templates.TemplateResponse("login.html",
                                                                                       {"request": request,
                                                                                        "error": "管理员验证码错误"})
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
    return templates.TemplateResponse("register.html", {"request": request, "error": "注册失败：用户名可能已被占用"})


@router.post("/logout")
async def lo(request: Request):
    sid = request.cookies.get("session_id");
    if sid in active_sessions: del active_sessions[sid]
    res = RedirectResponse("/index", 303);
    res.delete_cookie("session_id");
    return res


# --- [6. 个人中心与进度同步（含搜索）] ---
@router.get("/profile")
async def profile_page(request: Request, record_q: str = ""):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    info = get_user_info(s["username"])
    path_pattern = os.path.join(DATA_DIR, "*_成绩单_*.txt") if s["role"] == "admin" else os.path.join(DATA_DIR,
                                                                                                      f"{s['username']}_成绩单_*.txt")
    recs = sorted([os.path.basename(x) for x in glob.glob(path_pattern)], reverse=True)
    if record_q:
        recs = [r for r in recs if record_q.lower() in r.lower()]
    return templates.TemplateResponse("profile.html",
                                      {"request": request, "nickname": info["nickname"], "avatar": info["avatar"],
                                       "role": s["role"], "records": recs, "record_q": record_q})


@router.get("/change-password")
async def cp_pg(request: Request):
    if not check_session(request): return RedirectResponse("/index")
    return templates.TemplateResponse("change_password.html", {"request": request})


@router.post("/change-password-action")
async def handle_change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...)):
    s = check_session(request)
    if not s: return RedirectResponse("/index")
    if verify_user(s["username"], old_password):
        ph = hashlib.sha256(new_password.encode()).hexdigest()
        with get_user_db() as conn:
            conn.execute("UPDATE users SET password=? WHERE username=?", (ph, s["username"]))
            conn.commit()
        return templates.TemplateResponse("change_password.html",
                                          {"request": request, "error": "密码修改成功！", "success": True})
    return templates.TemplateResponse("change_password.html", {"request": request, "error": "原密码验证不正确"})


@router.post("/update-profile")
async def up_p(request: Request, nickname: str = Form(None), avatar_file: UploadFile = File(None)):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    av = None
    if avatar_file and avatar_file.filename:
        fn = f"{s['username']}_av{os.path.splitext(avatar_file.filename)[1]}"
        with open(f"static/uploads/{fn}", "wb") as b: b.write(await avatar_file.read())
        av = f"/static/uploads/{fn}"
    update_user_info(s["username"], nickname, av);
    return RedirectResponse("/profile", 303)


@router.get("/get-video-progress")
async def g_progress(request: Request):
    s = check_session(request);
    return JSONResponse(db_get_progress(s["username"]) if s else [])


@router.post("/update-progress")
async def u_progress(request: Request, video_id: int = Form(...), progress: str = Form(...)):
    s = check_session(request);
    if s: db_update_progress(s["username"], video_id, progress)
    return {"status": "ok"}


# --- [7. 视频管理：包含排序与AJAX] ---
@router.get("/videos")
async def v_list(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    return templates.TemplateResponse("videos.html",
                                      {"request": request, "videos": get_all_videos(), "role": s["role"]})


@router.post("/swap-video-order")
async def swap_v(request: Request, v1_id: int = Form(...), v2_id: int = Form(...)):
    s = check_session(request)
    if s and s["role"] == "admin":
        with get_res_db() as conn:
            v1 = conn.execute("SELECT title, filename FROM videos WHERE id=?", (v1_id,)).fetchone()
            v2 = conn.execute("SELECT title, filename FROM videos WHERE id=?", (v2_id,)).fetchone()
            if v1 and v2:
                conn.execute("UPDATE videos SET title=?, filename=? WHERE id=?", (v2['title'], v2['filename'], v1_id))
                conn.execute("UPDATE videos SET title=?, filename=? WHERE id=?", (v1['title'], v1['filename'], v2_id))
                conn.commit();
                return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error"}, status_code=403)


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
    return JSONResponse({"status": "ok"})


# --- [8. 考核测试与三段式成绩导出] ---
@router.get("/eeg-test")
async def eeg_test_page(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    if "test_start" not in s: s["test_start"] = time.time()
    lock = os.path.exists(os.path.join(DATA_DIR, f"{s['username']}.lock"))
    return templates.TemplateResponse("eeg_test.html",
                                      {"request": request, "questions": db_get_questions(), "role": s["role"],
                                       "answered": db_get_user_answers(s["username"]), "already_finished": lock})


@router.post("/submit-answer")
async def s_ans(request: Request, qid: int = Form(...), opt: str = Form(...)):
    s = check_session(request);
    if s: db_submit_answer(s["username"], qid, opt);
    return {"status": "ok"}


@router.post("/finish-test")
async def finish_test(request: Request):
    s = check_session(request);
    if not s: return RedirectResponse("/index")
    u = s["username"];
    now = datetime.now()
    if os.path.exists(os.path.join(DATA_DIR, f"{u}.lock")): return RedirectResponse("/profile", 303)
    u_info = get_user_info(u);
    nickname = u_info["nickname"] if u_info else "未知"
    qs = db_get_questions();
    ans = db_get_user_answers(u)
    video_progs = db_get_progress(u)
    total_score = 0;
    start_ts = s.get("test_start", time.time())
    duration_str = f"{int(time.time() - start_ts) // 60}分{int(time.time() - start_ts) % 60}秒"

    for q in qs:
        if ans.get(q['id'], {}).get('is_correct'): total_score += 1

    score_ratio = total_score / len(qs) if len(qs) > 0 else 0
    grade = "A" if score_ratio >= 0.75 else "B" if score_ratio >= 0.50 else "C" if score_ratio >= 0.25 else "D"

    idx = len(glob.glob(os.path.join(DATA_DIR, f"{u}_成绩单_*.txt"))) + 1
    fpath = os.path.join(DATA_DIR, f"{u}_成绩单_{idx}.txt")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n        深圳大学神经语言学实验室 - 实验考核报告\n" + "=" * 70 + "\n")
        f.write(
            f"用户昵称: {nickname} | 账号: {u}\n考核时间: {now.strftime('%Y-%m-%d %H:%M:%S')} | 耗时: {duration_str}\n最终成绩: {total_score}/{len(qs)} | 评级: {grade}\n\n")

        # 第一部分：答题总览
        f.write("-" * 22 + " [第一部分：答题总览] " + "-" * 22 + "\n")
        f.write(f"{'题号':<10}{'用户作答':<15}{'正确答案':<15}{'结果':<10}\n")
        for i, q in enumerate(qs, 1):
            ua = ans.get(q['id'], {})
            u_opt = ua.get('selected_option', '-')
            res = "√" if ua.get('is_correct') else "×"
            f.write(f"{i:<12}{u_opt:<18}{q['answer']:<18}{res:<10}\n")

        # 第二部分：详细解析
        f.write("\n" + "-" * 22 + " [第二部分：题目详细解析] " + "-" * 22 + "\n")
        for i, q in enumerate(qs, 1):
            ua = ans.get(q['id'], {})
            f.write(
                f"题{i}: {q['content']}\n选项: A:{q['option_a']} B:{q['option_b']} C:{q['option_c']} D:{q['option_d']}\n")
            f.write(
                f"用户作答: {ua.get('selected_option', '未填')} | 正确答案: {q['answer']} | {'√' if ua.get('is_correct') else '×'}\n" + "-" * 30 + "\n")

        # 第三部分：学习进度
        f.write("\n" + "-" * 22 + " [第三部分：课件进度存档] " + "-" * 22 + "\n")
        if video_progs:
            f.write(f"{'课件名称':<40}{'观看进度':<10}\n")
            for vp in video_progs:
                f.write(f"{vp['title']:<43}{vp['progress']:<10}\n")
        else:
            f.write("暂无课件观看记录。\n")
        f.write("\n报告由系统自动生成。")

    with open(os.path.join(DATA_DIR, f"{u}.lock"), "w") as lock:
        lock.write("L")
    if "test_start" in s: del s["test_start"]
    with get_user_db() as conn:
        conn.execute("DELETE FROM user_answers WHERE username=?", (u,)); conn.commit()
    return RedirectResponse("/profile", 303)


@router.post("/add-question")
async def aq(content: str = Form(...), option_a: str = Form(...), option_b: str = Form(...), option_c: str = Form(...),
             option_d: str = Form(...), answer: str = Form(...)):
    db_add_question(content, option_a, option_b, option_c, option_d, answer.upper());
    return JSONResponse({"status": "ok"})


@router.post("/edit-question")
async def edit_q(request: Request, qid: int = Form(...), content: str = Form(...), option_a: str = Form(...),
                 option_b: str = Form(...), option_c: str = Form(...), option_d: str = Form(...),
                 answer: str = Form(...)):
    s = check_session(request)
    if s and s["role"] == "admin":
        with get_res_db() as conn:
            conn.execute(
                "UPDATE questions SET content=?, option_a=?, option_b=?, option_c=?, option_d=?, answer=? WHERE id=?",
                (content, option_a, option_b, option_c, option_d, answer.upper(), qid))
            conn.commit();
            return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error"}, status_code=403)


@router.post("/delete-question")
async def dq(request: Request, qid: int = Form(...)):
    s = check_session(request);
    if s and s["role"] == "admin": db_delete_question(qid); return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error"}, status_code=403)


@router.post("/reset-all")
async def handle_reset_all(request: Request):
    s = check_session(request)
    if s and s["role"] == "admin":
        db_reset_all_answers();
        [os.remove(f) for f in glob.glob(os.path.join(DATA_DIR, "*.lock"))]
    return RedirectResponse("/profile", 303)