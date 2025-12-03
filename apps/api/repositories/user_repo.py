"""
用户仓储
用户相关的数据访问操作
"""

from typing import Optional
from sqlalchemy.orm import Session

from packages.db import User, Tenant
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_tenant(self, tenant_id: int, email: str) -> Optional[User]:
        """根据租户和邮箱获取用户"""
        return (
            self.db.query(User)
            .filter(User.tenant_id == tenant_id, User.email == email)
            .first()
        )
    
    def update_bilibili_bind(self, user: User, uid: str, sessdata: str) -> None:
        """更新B站绑定信息"""
        user.bilibili_uid = uid
        user.bilibili_sessdata = sessdata
        self.db.commit()
    
    def clear_bilibili_bind(self, user: User) -> None:
        """清除B站绑定"""
        user.bilibili_uid = None
        user.bilibili_sessdata = None
        self.db.commit()


class TenantRepository(BaseRepository[Tenant]):
    """租户仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, Tenant)
    
    def get_default(self) -> Optional[Tenant]:
        """获取默认租户"""
        return self.db.query(Tenant).first()
    
    def get_or_create_default(self) -> Tenant:
        """获取或创建默认租户"""
        tenant = self.get_default()
        if not tenant:
            tenant = Tenant(name="default")
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)
        return tenant
    
    def create_and_flush(self, **data) -> Tenant:
        """创建租户并flush（不commit，用于事务中）"""
        tenant = Tenant(**data)
        self.db.add(tenant)
        self.db.flush()
        return tenant
