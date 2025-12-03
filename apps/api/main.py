"""
AliceLM API
FastAPI应用入口
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.config import get_config
from packages.db import init_db
from packages.logging import get_logger

from .routers import videos, qa, auth, folders, knowledge, config as config_router, bilibili, conversations, system, suggestions

logger = get_logger(__name__)
app_config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """应用生命周期管理"""
    logger.info("api_starting", app_name=app_config.app_name)
    init_db()
    yield
    logger.info("api_shutdown")


app = FastAPI(
    title="AliceLM API",
    description="B站视频学习助手API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if app_config.debug else None,
    redoc_url="/redoc" if app_config.debug else None,
)

# CORS配置
import os

_cors_origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    # frp公网访问
    "http://124.70.75.139:3000",
]

# 添加公网地址（如果配置了）
if os.getenv("PUBLIC_HOST"):
    _cors_origins.append(f"http://{os.getenv('PUBLIC_HOST')}")
    _cors_origins.append(f"https://{os.getenv('PUBLIC_HOST')}")

# 开发环境：使用正则允许所有localhost/127.0.0.1端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if app_config.debug else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["视频"])
app.include_router(folders.router, prefix="/api/v1/folders", tags=["收藏夹"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["问答"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识图谱"])
app.include_router(config_router.router, prefix="/api/v1/config", tags=["配置"])
app.include_router(bilibili.router, prefix="/api/v1/bilibili", tags=["B站绑定"])
app.include_router(conversations.router, prefix="/api/v1", tags=["对话"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(suggestions.router, prefix="/api/v1/suggestions", tags=["灵感建议"])


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1")
async def api_info():
    """API信息"""
    return {
        "name": app_config.app_name,
        "version": "0.1.0",
        "endpoints": {
            "videos": "/api/v1/videos",
            "folders": "/api/v1/folders",
            "conversations": "/api/v1/conversations",
            "qa": "/api/v1/qa",
            "auth": "/api/v1/auth",
            "knowledge": "/api/v1/knowledge",
            "config": "/api/v1/config",
            "bilibili": "/api/v1/bilibili",
        }
    }
