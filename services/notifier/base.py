"""
通知器抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotifyMessage:
    """通知消息"""
    title: str
    content: str
    url: Optional[str] = None
    video_bvid: Optional[str] = None


class NotifierBase(ABC):
    """通知器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """通知器名称"""
        pass

    @abstractmethod
    def send(self, message: NotifyMessage) -> bool:
        """
        发送通知
        
        Args:
            message: 通知消息
            
        Returns:
            是否发送成功
        """
        pass

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return True
