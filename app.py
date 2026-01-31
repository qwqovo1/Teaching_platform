# app.py
import uvicorn
import socket
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from modules.routes import router

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


def get_host_ip():
    """获取本机真实局域网IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 这里连接一个公网地址以诱导系统选出正确的局域网网卡
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

    # --- 醒目的末尾添加：访问提示加强 ---
    print("\n" + "█" * 60)
    print("🚀  深大神经语言学实验室平台 - 服务已就绪")
    print("█" * 60)
    print(f"👉 【本机极速访问】:  http://127.0.0.1:{port}")
    print(f"👉 【本机极速访问】:  http://localhost:{port}")
    print("-" * 60)
    print(f"📱 【同 Wi-Fi 设备访问】: http://{local_ip}:{port}")
    print(f"📡 【内网穿透访问】: (请使用你的花生壳/frp提供的公网网址)")
    print("█" * 60 + "\n")

    # host="0.0.0.0" 是关键，它允许外部网络（手机）访问
    uvicorn.run(app, host="0.0.0.0", port=port)