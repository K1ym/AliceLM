"""
配置仓储
用户配置相关的数据访问操作
"""

from typing import Optional

from sqlalchemy.orm import Session

from packages.db import UserConfig
from .base import BaseRepository


class ConfigRepository(BaseRepository[UserConfig]):
    """配置仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, UserConfig)
    
    def get_by_key(self, user_id: int, key: str) -> Optional[UserConfig]:
        """根据用户ID和配置键获取配置"""
        return (
            self.db.query(UserConfig)
            .filter(UserConfig.user_id == user_id, UserConfig.key == key)
            .first()
        )
    
    def get_value(self, user_id: int, key: str) -> Optional[str]:
        """获取配置值"""
        config = self.get_by_key(user_id, key)
        return config.value if config else None
    
    def set_value(self, user_id: int, key: str, value: str) -> UserConfig:
        """设置配置值（创建或更新）"""
        config = self.get_by_key(user_id, key)
        
        if config:
            config.value = value
        else:
            config = UserConfig(user_id=user_id, key=key, value=value)
            self.db.add(config)
        
        self.db.commit()
        self.db.refresh(config)
        return config
