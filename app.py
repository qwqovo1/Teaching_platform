# app.py
import os
import base64
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from modules.routes import router
from modules.database import init_db

init_db()
app = FastAPI(title="深圳大学 - 神经语言学实验室平台")

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/videos", exist_ok=True)
os.makedirs("Data", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
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

@app.get("/video-catalog")
async def video_catalog(request: Request):
    from modules.routes import check_session
    if not check_session(request):
        return RedirectResponse(url="/login-page", status_code=303)
    return templates.TemplateResponse("video_catalog.html", {"request": request})

@app.get("/test-catalog")
async def test_catalog(request: Request):
    from modules.routes import check_session
    if not check_session(request):
        return RedirectResponse(url="/login-page", status_code=303)
    return templates.TemplateResponse("test_catalog.html", {"request": request})

def create_default_avatar():
    path = "static/default-avatar.png"
    if not os.path.exists(path):
        pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        with open(path, "wb") as f:
            f.write(base64.b64decode(pixel_b64))

create_default_avatar()

if __name__ == "__main__":
    import uvicorn
    print("🚀 教学平台已启动！")
    print("🌐 访问地址： http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)