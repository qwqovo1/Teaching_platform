# Teaching_platform/login-demo/app.py
import os
import base64
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from modules.routes import router

app = FastAPI(title="教学平台")

# 挂载静态文件目录
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/videos", exist_ok=True)  # 确保视频目录存在
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")
# 注意：/static 已包含 /static/videos，无需单独挂载

templates = Jinja2Templates(directory="templates")
app.include_router(router)

@app.get("/")
async def root(request: Request):
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

# === 新增：视频页面路由 ===
@app.get("/videos")
async def videos_page(request: Request):
    return templates.TemplateResponse("videos.html", {"request": request})
# =========================

def create_default_avatar():
    DEFAULT_AVATAR_PATH = "static/default-avatar.png"
    if not os.path.exists(DEFAULT_AVATAR_PATH):
        pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        with open(DEFAULT_AVATAR_PATH, "wb") as f:
            f.write(base64.b64decode(pixel_b64))

create_default_avatar()

if __name__ == "__main__":
    import uvicorn
    print("🚀 教学平台已启动！")
    print("🌐 访问地址:")
    print("  欢迎页: http://localhost:8000")
    print("  登录页: http://localhost:8000/login-page")
    print("  注册页: http://localhost:8000/register-page")
    print("  视频页: http://localhost:8000/videos")
    print("  首页（需登录）: http://localhost:8000/home")
    uvicorn.run(app, host="0.0.0.0", port=8000)