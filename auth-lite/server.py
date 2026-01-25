from __future__ import annotations

import hashlib

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal, engine

BASE_DIR = Path(__file__).resolve().parent

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Independent Login Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/api/register")
async def register(payload: dict, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="该用户名已被注册")

    user = models.User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return JSONResponse({"message": "注册成功", "username": user.username})


@app.post("/api/login")
async def login(payload: dict, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        raise HTTPException(status_code=400, detail="请输入账号和密码")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or user.password_hash != hash_password(password):
        raise HTTPException(status_code=401, detail="账号或密码不正确")

    return JSONResponse({"message": "登录成功", "username": user.username})
