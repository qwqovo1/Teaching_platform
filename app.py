# Teaching_platform/login-demo/app.py
import os
import base64
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modules.routes import router
from modules.database import init_db  # 初始化数据库

# 初始化数据库（创建 users 和 videos 表）
init_db()

app = FastAPI(title="教学平台")

# 创建必要目录，包括存放默认头像的 icons 目录
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/videos", exist_ok=True)
os.makedirs("static/icons", exist_ok=True)  # <-- 确保存放默认头像的目录存在

# 挂载静态文件（/static 包含 uploads, videos, icons）
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.include_router(router)

@app.get("/")
async def root(request: Request):
    """欢迎页（使用 index.html）"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login-page")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register-page")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/change-password")
async def change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})

# 注意：/videos、/home、/profile 等路由已在 modules/routes.py 中定义，
# 因此此处不再重复定义，避免冲突。

def create_default_avatar():
    DEFAULT_AVATAR_PATH = "static/icons/default.png"  # <-- 使用相对路径
    if not os.path.exists(DEFAULT_AVATAR_PATH):
        # 1x1 透明 PNG 像素（base64 编码）
        pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        with open(DEFAULT_AVATAR_PATH, "wb") as f:
            f.write(base64.b64decode(pixel_b64))

create_default_avatar()

if __name__ == "__main__":
    import uvicorn
    print("🚀 教学平台已启动！")
    print("🌐 访问地址:")
    print(" 欢迎页: http://localhost:8000")
    print(" 登录页: http://localhost:8000/login-page")
    print(" 注册页: http://localhost:8000/register-page")
    print(" 视频页: http://localhost:8000/videos")
    print(" 首页（需登录）: http://localhost:8000/home")
    uvicorn.run(app, host="0.0.0.0", port=8000)