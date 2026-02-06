# app.py
import uvicorn
import socket
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from modules.routes import router
from modules.database import init_db


# 🌟 推荐的新版 Lifespan 处理器，替代过时的 @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- [启动时运行] ---
    # 1. 确保文件夹存在
    for folder in ["Data", "static/uploads", "static/videos"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 已创建文件夹: {folder}")

    # 2. 初始化数据库 (包含自动修复逻辑)
    print("📡 正在检查/初始化数据库...")
    init_db()
    print("✅ 数据库已就绪")

    yield  # 此时应用正在运行...

    # --- [关闭时运行] ---
    print("🔌 正在关闭服务...")


app = FastAPI(lifespan=lifespan)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


def get_host_ip():
    """获取本机真实局域网IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    local_ip = get_host_ip()
    port = 8000

    print("\n" + "█" * 60)
    print("🚀  深大神经语言学实验室平台 - 服务已就绪")
    print("█" * 60)
    print(f"👉 【本机极速访问】:  http://127.0.0.1:{port}")
    print(f"👉 【本机极速访问】:  http://localhost:{port}")
    print("-" * 60)
    print(f"🛠️  【账号管理后台】:  http://127.0.0.1:{port}/admin/users")
    print(f"🛠️  【局域网管理入口】:  http://{local_ip}:{port}/admin/users")
    print("-" * 60)
    print(f"📱 【同 Wi-Fi 设备访问】: http://{local_ip}:{port}")
    print(f"📡 【内网穿透访问】: (请使用你的花生壳/frp提供的公网网址)")
    print("█" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port)