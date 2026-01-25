# login-demo/modules/routes.py
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import secrets
from datetime import datetime

# --- 将 active_sessions 定义在此模块内 ---
active_sessions = {}
# ------------------------------------------

from .database import create_user, verify_user, change_password, user_exists, get_user_info, update_user_info
from .utils import validate_password_strength, validate_username, cleanup_if_needed
import os

router = APIRouter()
# 修正模板路径：相对于 app.py 所在的 login-demo 目录
templates = Jinja2Templates(directory="templates")

# 上传文件的目录
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # 确保目录存在


def check_session(request: Request):
    """检查用户是否已登录"""
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in active_sessions:
        return False
    # 检查会话是否过期
    if datetime.now().timestamp() > active_sessions[session_id]["expires"]:
        del active_sessions[session_id]
        return False
    return True


def require_login(request: Request):
    """装饰器：要求用户已登录"""
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    return True


# --- 页面路由 ---

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """主页（登录页面）"""
    cleanup_if_needed()  # 每次访问清理过期用户
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """修改密码页面"""
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("change_password.html", {"request": request})


@router.get("/home", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """登录后的首页"""
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    user_info = get_user_info(username)
    if not user_info:
        # 如果无法获取用户信息（例如用户刚好过期），重定向到登录页
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("home.html",
                                      {"request": request, "username": username, "nickname": user_info["nickname"],
                                       "avatar": user_info["avatar"]})


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """个人中心页面"""
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]
    user_info = get_user_info(username)
    if not user_info:
        # 如果无法获取用户信息（例如用户刚好过期），重定向到登录页
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("profile.html",
                                      {"request": request, "username": username, "nickname": user_info["nickname"],
                                       "avatar": user_info["avatar"]})


# --- API 路由 ---

@router.post("/register")
async def register_user(username: str = Form(...), password: str = Form(...)):
    """处理注册"""
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
async def login_user(response: RedirectResponse, username: str = Form(...), password: str = Form(...)):
    """处理登录"""
    if verify_user(username, password):
        # 创建会话
        session_id = secrets.token_urlsafe(32)
        active_sessions[session_id] = {
            "username": username,
            "expires": datetime.now().timestamp() + 3600 * 24 * 7  # 7天过期
        }

        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=3600 * 24 * 7)
        return response
    else:
        raise HTTPException(status_code=400, detail="账号或密码错误")


@router.post("/change-password-action")
async def change_password_action(request: Request, old_password: str = Form(...), new_password: str = Form(...)):
    """处理密码修改"""
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
async def logout_user(response: RedirectResponse, request: Request):
    """处理登出"""
    session_id = request.cookies.get("session_id")
    if session_id in active_sessions:
        del active_sessions[session_id]

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response


@router.post("/update-profile")
async def update_profile(request: Request,
                         nickname: str = Form(...),
                         avatar_url: str = Form(None),  # 可选字段，用于手动输入URL
                         avatar_upload: UploadFile = File(None)):  # 可选文件上传
    """处理个人资料更新"""
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)

    session_id = request.cookies.get("session_id")
    username = active_sessions[session_id]["username"]

    # 1. 处理文件上传
    avatar_path = None
    if avatar_upload is not None:
        # 生成唯一的文件名
        filename = f"{username}_{secrets.token_hex(4)}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(await avatar_upload.read())

        # 设置相对路径
        avatar_path = f"/uploads/{filename}"
    elif avatar_url is not None and avatar_url.strip():
        # 如果用户没有上传文件，但提供了URL，则使用该URL
        avatar_path = avatar_url.strip()

    # 2. 更新数据库
    success = update_user_info(username, nickname=nickname, avatar=avatar_path)
    if success:
        # 更新会话中的信息
        active_sessions[session_id]['nickname'] = nickname
        active_sessions[session_id]['avatar'] = avatar_path
        return RedirectResponse(url="/profile", status_code=303)
    else:
        raise HTTPException(status_code=400, detail="更新失败，请稍后重试")