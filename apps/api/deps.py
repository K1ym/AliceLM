"""
API依赖注入
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from packages.config import get_config
from packages.db import get_db_context, Tenant, User

from .repositories import (
    VideoRepository,
    ConversationRepository,
    MessageRepository,
    UserRepository,
    TenantRepository,
    FolderRepository,
    ConfigRepository,
)
from .services import VideoService, ChatService, FolderService, BilibiliService, ConfigService, AuthService

config = get_config()
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    with get_db_context() as db:
        yield db


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    获取当前认证用户
    
    支持两种模式:
    1. JWT Token认证
    2. 开发模式下允许无认证访问默认用户
    """
    # 开发模式允许无token访问
    if config.debug and credentials is None:
        user = db.query(User).filter(User.email == "admin@local").first()
        if user:
            return user
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=["HS256"],
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的Token",
            )
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token解析失败",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    """获取当前用户的租户"""
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在",
        )
    return tenant


# ========== Repository 依赖注入 ==========

def get_video_repo(db: Session = Depends(get_db)) -> VideoRepository:
    """获取视频仓储"""
    return VideoRepository(db)


def get_conversation_repo(db: Session = Depends(get_db)) -> ConversationRepository:
    """获取对话仓储"""
    return ConversationRepository(db)


def get_message_repo(db: Session = Depends(get_db)) -> MessageRepository:
    """获取消息仓储"""
    return MessageRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """获取用户仓储"""
    return UserRepository(db)


def get_folder_repo(db: Session = Depends(get_db)) -> FolderRepository:
    """获取收藏夹仓储"""
    return FolderRepository(db)


# ========== Service 依赖注入 ==========

def get_video_service(
    repo: VideoRepository = Depends(get_video_repo),
) -> VideoService:
    """获取视频服务"""
    return VideoService(repo)


def get_chat_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    video_repo: VideoRepository = Depends(get_video_repo),
) -> ChatService:
    """获取对话服务"""
    return ChatService(conversation_repo, message_repo, video_repo)


def get_folder_service(
    folder_repo: FolderRepository = Depends(get_folder_repo),
    video_repo: VideoRepository = Depends(get_video_repo),
) -> FolderService:
    """获取收藏夹服务"""
    return FolderService(folder_repo, video_repo)


def get_bilibili_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> BilibiliService:
    """获取B站服务"""
    return BilibiliService(user_repo)


def get_config_repo(db: Session = Depends(get_db)) -> ConfigRepository:
    """获取配置仓储"""
    return ConfigRepository(db)


def get_config_service(
    config_repo: ConfigRepository = Depends(get_config_repo),
) -> ConfigService:
    """获取配置服务"""
    return ConfigService(config_repo)


def get_tenant_repo(db: Session = Depends(get_db)) -> TenantRepository:
    """获取租户仓储"""
    return TenantRepository(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> AuthService:
    """获取认证服务"""
    return AuthService(user_repo, tenant_repo)
