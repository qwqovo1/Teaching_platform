# modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import secrets, os, glob, shutil
from datetime import datetime
from .database import *

router = APIRouter()
templates = Jinja2Templates(directory="templates")
active_sessions = {}
DATA_DIR = "Data"
UPLOAD_DIR = "static/uploads"

def check_session(request: Request):
    sid = request.cookies.get("session_id")
    return active_sessions.get(sid)

@router.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    if create_user(username, password):
        return RedirectResponse(url="/login-page", status_code=303)
    return templates.TemplateResponse("register.html", {"request": {}, "error": "注册失败，用户名可能已存在"})

@router.post("/login")
async def login(username: str=Form(...), password: str=Form(...), role: str=Form(...), admin_serial: str=Form(None)):
    # 管理员序列号 123456 校验且无提示
    if role == "admin" and admin_serial != "123456":
        return templates.TemplateResponse("login.html", {"request": {}, "error": "认证序列号不正确"})
    if verify_user(username, password):
        sid = secrets.token_urlsafe(32)
        active_sessions[sid] = {"username": username, "role": role}
        res = RedirectResponse("/home", 303)
        res.set_cookie("session_id", sid, httponly=True)
        return res
    return templates.TemplateResponse("login.html", {"request": {}, "error": "账号或密码错误"})

@router.get("/home")
async def home(request: Request):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    info = get_user_info(u["username"])
    return templates.TemplateResponse("home.html", {"request": request, "nickname": info["nickname"], "user": info, "role": u["role"]})

@router.get("/profile")
async def profile(request: Request):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    info = get_user_info(u["username"])
    recs = [os.path.basename(x) for x in glob.glob(os.path.join(DATA_DIR, f"{u['username']}-*.txt"))]
    recs.sort(key=lambda x: int(x.split('-')[-1].split('.')[0]) if '-' in x else 0)
    return templates.TemplateResponse("profile.html", {"request": request, "nickname": info["nickname"], "avatar": info["avatar"], "role": u["role"], "records": recs})

@router.post("/update-profile")
async def update_profile(request: Request, nickname: str=Form(None), avatar_file: UploadFile=File(None)):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    avatar_url = None
    if avatar_file and avatar_file.filename:
        fn = f"{u['username']}_avatar{os.path.splitext(avatar_file.filename)[1]}"
        with open(os.path.join(UPLOAD_DIR, fn), "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/static/uploads/{fn}"
    update_user_info(u["username"], nickname, avatar_url)
    return RedirectResponse("/profile", 303)

@router.post("/change-password-action")
async def change_p_action(request: Request, old_password: str=Form(...), new_password: str=Form(...)):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    success, msg = change_password(u["username"], old_password, new_password)
    if success: return RedirectResponse("/home", 303)
    return templates.TemplateResponse("change_password.html", {"request": request, "error": msg})

@router.get("/videos")
async def videos(request: Request):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    return templates.TemplateResponse("videos.html", {"request": request, "videos": get_all_videos(), "role": u["role"]})

@router.post("/upload-video")
async def upload_v(request: Request, title: str=Form(...), video_file: UploadFile=File(...)):
    u = check_session(request)
    if not u or u["role"] != "admin": raise HTTPException(403, "无权操作")
    fn = f"{secrets.token_hex(4)}_{video_file.filename}"
    with open(f"static/videos/{fn}", "wb") as f: f.write(await video_file.read())
    add_video(title, fn, u["username"])
    return RedirectResponse("/videos", 303)

@router.post("/delete-video")
async def delete_v(request: Request, video_id: int=Form(...)):
    u = check_session(request)
    if u and u["role"] == "admin":
        delete_video_by_id(video_id)
        return RedirectResponse("/videos", 303)
    raise HTTPException(403, "权限拒绝")

@router.get("/eeg-test")
async def eeg_test(request: Request):
    u = check_session(request)
    if not u: return RedirectResponse("/login-page")
    return templates.TemplateResponse("eeg_test.html", {"request": request, "questions": db_get_questions(), "role": u["role"], "answered": db_get_user_answers(u["username"])})

@router.post("/submit-answer")
async def sub_ans(request: Request, qid: int=Form(...), opt: str=Form(...)):
    u = check_session(request)
    return {"is_correct": db_submit_answer(u["username"], qid, opt)}

@router.post("/finish-test")
async def finish(request: Request):
    u = check_session(request)
    uname = u["username"]
    qs = db_get_questions()
    ans = db_get_user_answers(uname)
    correct = sum(1 for v in ans.values() if v["is_correct"])
    idx = len(glob.glob(os.path.join(DATA_DIR, f"{uname}-*.txt"))) + 1
    filepath = os.path.join(DATA_DIR, f"{uname}-{idx}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"账号: {uname}\n得分: {correct}/{len(qs)}\n时间: {datetime.now()}\n")
    return RedirectResponse("/profile", 303)

@router.post("/reset-all")
async def reset_all(request: Request):
    u = check_session(request)
    if u and u["role"] == "admin":
        db_reset_all_answers()
    return RedirectResponse("/profile", 303)

@router.get("/download-record/{fname}")
async def download(fname: str):
    return FileResponse(os.path.join(DATA_DIR, fname))

@router.post("/logout")
async def logout(request: Request):
    sid = request.cookies.get("session_id")
    if sid in active_sessions: del active_sessions[sid]
    res = RedirectResponse("/", 303); res.delete_cookie("session_id"); return res

@router.post("/add-question")
async def add_q(content: str=Form(...), a: str=Form(...), b: str=Form(...), c: str=Form(...), d: str=Form(...), ans: str=Form(...)):
    db_add_question(content, a, b, c, d, ans)
    return RedirectResponse("/eeg-test", 303)

@router.post("/delete-question")
async def del_q(qid: int=Form(...)):
    db_delete_question(qid)
    return RedirectResponse("/eeg-test", 303)