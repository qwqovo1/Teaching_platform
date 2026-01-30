# 深圳大学 - 神经语言学实验室教学平台

本项目是一个基于 **FastAPI** 开发的综合性教学管理平台，专门为 **深圳大学神经语言学实验室** 设计。平台集成了用户权限管理、个人信息定制以及视频教学资源分类展示等功能，并采用了现代化的“马卡龙”视觉设计风格。

## 🚀 项目特性

### 1. 视觉与交互体验 (UI/UX)
- **清新视觉风格**：采用明亮的马卡龙渐变背景（天空蓝、樱花粉、淡紫），营造舒适的学术研究氛围。
- **动态装饰元素**：全站集成 CSS 动画实现的悬浮粒子（小星星、花朵），增加页面的活力感。
- **黄金比例设计**：核心交互组件（输入框、分类按钮）严格遵循 **0.618 黄金比例**，视觉观感更协调。
- **毛玻璃效果 (Glassmorphism)**：容器采用半透明磨砂质感，结合顶部固定导航栏，提升界面层次感。

### 2. 核心功能
- **权限管理**：完整的用户注册、登录、修改密码及 Session 会话管理。
- **视频课室**：
  - **一级分类目录**：提供脑电（EEG）实验视频及其他待定科研分类。
  - **视频流播放**：支持 MP4/MOV/AVI/WebM 等多种科研常用视频格式。
  - **安全操作**：视频上传与删除均设有独立授权密码（默认：`123456`），防止误操作。
- **个人中心**：支持自定义昵称和头像上传，数据实时更新。
- **自动清理**：内置数据库过期记录清理机制，维护系统轻量运行。

## 🛠️ 技术栈

- **后端**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.9+)
- **前端**: HTML5, CSS3, [Jinja2 Templates](https://jinja.palletsprojects.com/)
- **数据库**: SQLite3
- **运行环境**: Uvicorn, Anaconda/Conda
- **主要依赖**: `python-multipart` (文件上传), `pydantic` (模型验证), `passlib` (密码哈希)

## 📂 目录结构

```text
Teaching_platform/
├─app.py                # 项目入口文件 (启动路由与静态挂载)
├─static/               # 静态资源
│  ├─css/               # 包含全局美化样式 global.css
│  ├─icons/             # 默认头像及图标 (default.png)
│  ├─uploads/           # 用户上传的个人头像
│  └─videos/            # 教学视频资源存储
├─templates/            # 网页模板 (base, index, login, videos 等)
├─modules/              # 核心业务逻辑
│  ├─database.py        # SQLite 数据库操作
│  ├─routes.py          # 路由逻辑处理
│  ├─utils.py           # 校验与清理工具
│  └─config.py          # 系统配置文件 (包含授权密码)
├─unity/                # (扩展) Unity 实验组件 Assets
└─webgl/                # (扩展) WebGL 实验发布内容
```

## 📦 安装与启动

### 1. 环境准备
确保已安装 Anaconda 并激活您的环境（基于您的配置）：
```bash
conda activate py39_fix
```

### 2. 安装依赖
```bash
pip install fastapi uvicorn jinja2 python-multipart pydantic
```

### 3. 运行项目
在项目根目录下执行：
```bash
python app.py
```

启动后，访问地址：
- **欢迎页**: `http://localhost:8000`
- **后台管理**: `http://localhost:8000/docs` (FastAPI Swagger UI)

## 🔐 关键配置说明

- **上传/删除授权密码**: `123456` (可在 `modules/config.py` 中修改)
- **数据库路径**: `users.db` (首次启动自动初始化)
- **静态资源挂载**: `/static` 映射至本地根目录的 `static` 文件夹。

## 📝 开发者说明
- **样式修改**: 如需调整背景或动画，请修改 `static/css/global.css`。
- **页面布局**: 全站基于 `base.html` 继承，导航栏固定在顶部，内容区域通过 `.main-content` 类控制内边距。

---
**© 2024 深圳大学神经语言学实验室 | 保留所有权利**