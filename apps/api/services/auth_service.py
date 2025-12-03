"""
认证服务
用户登录、注册相关的业务逻辑
"""

from datetime import datetime
from typing import Optional, Tuple

import bcrypt

from packages.db import User
from packages.logging import get_logger

from ..repositories.user_repo import UserRepository, TenantRepository

logger = get_logger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8')[:72], 
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """哈希密码"""
    return bcrypt.hashpw(
        password.encode('utf-8')[:72], 
        bcrypt.gensalt()
    ).decode('utf-8')


class AuthService:
    """认证服务类"""
    
    def __init__(
        self,
        user_repo: UserRepository,
        tenant_repo: TenantRepository,
    ):
        self.user_repo = user_repo
        self.tenant_repo = tenant_repo
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.user_repo.get_by_email(email)
    
    def authenticate(self, email: str, password: str, debug_mode: bool = False) -> Optional[User]:
        """
        验证用户凭证
        
        Returns:
            User if authentication successful, None otherwise
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        
        # 开发模式下允许空密码登录
        if debug_mode and not user.password_hash:
            return user
        
        if not user.password_hash or not verify_password(password, user.password_hash):
            return None
        
        return user
    
    def register(
        self,
        email: str,
        username: str,
        password: str,
    ) -> Tuple[User, bool]:
        """
        注册新用户
        
        Returns:
            (User, is_new): 用户对象和是否为新创建
        """
        # 检查邮箱是否已存在
        existing = self.user_repo.get_by_email(email)
        if existing:
            return existing, False
        
        # 创建个人租户（flush但不commit，保持事务）
        tenant = self.tenant_repo.create_and_flush(
            name=f"{username}的空间",
            slug=f"user-{email.split('@')[0]}-{datetime.utcnow().timestamp():.0f}",
        )
        
        # 创建用户并提交事务
        user = self.user_repo.create(
            tenant_id=tenant.id,
            email=email,
            username=username,
            password_hash=hash_password(password),
        )
        
        logger.info("user_registered", user_id=user.id, email=email)
        return user, True
    
    def email_exists(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        return self.user_repo.get_by_email(email) is not None
