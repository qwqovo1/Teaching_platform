# login-demo/modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import secrets
from datetime import datetime
import os

from .config import VIDEO_DELETE_PASSWORD

active_sessions = {}
router = APIRouter()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads"
VIDEO_UPLOAD_DIR = "static/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)

from .database import (
    create_user, verify_user, change_password, get_user_info, update_user_info,
    add_video, get_all_videos, delete_video_by_id
)
from .utils import validate_password_strength, validate_username, cleanup_if_needed

def check_session(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in active_sessions:
        return False
    if datetime.now().timestamp() > active_sessions[session_id]["expires"]:
        del active_sessions[session_id]
        return False
    return True

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    cleanup_if_needed()
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("change_password.html", {"request": request})

@router.get("/home", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    user_info = get_user_info(username)
    if not user_info:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username,
        "nickname": user_info["nickname"],
        "user": user_info
    })

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    user_info = get_user_info(username)
    if not user_info:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "username": username,
        "nickname": user_info["nickname"],
        "avatar": user_info["avatar"]
    })

@router.get("/videos", response_class=HTMLResponse)
async def videos_page(request: Request):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    videos = get_all_videos()
    return templates.TemplateResponse("videos.html", {"request": request, "videos": videos})

@router.get("/upload-video-page", response_class=HTMLResponse)
async def upload_video_page(request: Request):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("upload_video.html", {"request": request})

@router.post("/register")
async def register_user(username: str = Form(...), password: str = Form(...)):
    is_valid, msg = validate_username(username)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    is_valid, msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    if create_user(username, password):
        return RedirectResponse(url="/login-page", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="用户名已存在")

@router.post("/login")
async def login_user(username: str = Form(...), password: str = Form(...)):
    if verify_user(username, password):
        session_id = secrets.token_urlsafe(32)
        active_sessions[session_id] = {
            "username": username,
            "expires": datetime.now().timestamp() + 3600 * 24 * 7
        }
        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=3600 * 24 * 7)
        return response
    else:
        raise HTTPException(status_code=400, detail="账号或密码错误")

@router.post("/change-password-action")
async def change_password_action(request: Request, old_password: str = Form(...), new_password: str = Form(...)):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    success, message = change_password(username, old_password, new_password)
    if success:
        return RedirectResponse(url="/home", status_code=303)
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/logout")
async def logout_user(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in active_sessions:
        del active_sessions[session_id]
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response

@router.post("/update-profile")
async def update_profile(
        request: Request,
        nickname: str = Form(...),
        avatar_upload: UploadFile = File(None)
):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    avatar_path = None
    if avatar_upload and avatar_upload.filename:
        filename = f"{username}_{secrets.token_hex(8)}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await avatar_upload.read())
        avatar_path = f"/static/uploads/{filename}"

    success = update_user_info(username, nickname=nickname, avatar=avatar_path)
    if success:
        user_info = get_user_info(username)
        active_sessions[session_id]['nickname'] = user_info["nickname"]
        active_sessions[session_id]['avatar'] = user_info["avatar"]
        return RedirectResponse(url="/profile", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="更新失败")

# --- 修改后的上传路由：增加密码验证 ---
@router.post("/upload-video")
async def upload_video(
        request: Request,
        title: str = Form(...),
        upload_password: str = Form(...), # 新增
        video_file: UploadFile = File(...)
):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)

    if upload_password != "123456":
        raise HTTPException(status_code=400, detail="上传密码错误")

    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]

    allowed_types = ["video/mp4", "video/avi", "video/mov", "video/quicktime", "video/webm"]
    if video_file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 MP4/AVI/MOV/WebM 格式")

    ext = os.path.splitext(video_file.filename)[1].lower()
    safe_filename = f"{username}_{secrets.token_hex(8)}{ext}"
    file_path = os.path.join(VIDEO_UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(await video_file.read())

    if add_video(title=title, filename=safe_filename, uploaded_by=username):
        return RedirectResponse(url="/videos", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="视频上传失败")

@router.get("/list-videos")
async def list_videos_api():
    videos = get_all_videos()
    return JSONResponse({"videos": videos})

@router.post("/delete-video")
async def delete_video(
        request: Request,
        video_id: int = Form(...),
        delete_password: str = Form(...)
):
    if not check_session(request):
        raise HTTPException(status_code=403, detail="请先登录")
    if delete_password != VIDEO_DELETE_PASSWORD:
        raise HTTPException(status_code=400, detail="删除密码错误")
    success = delete_video_by_id(video_id)
    if success:
        return RedirectResponse(url="/videos", status_code=303)
    else:
        raise HTTPException(status_code=404, detail="视频不存在")