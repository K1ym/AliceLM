"""
对话仓储
对话相关的数据访问操作
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from packages.db import Conversation, Message
from .base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """对话仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, Conversation)
    
    def list_by_user(
        self,
        user_id: int,
        video_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Conversation]:
        """获取用户的对话列表"""
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)
        
        if video_id:
            query = query.filter(Conversation.video_id == video_id)
        
        return query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()
    
    def count_by_user(self, user_id: int, video_id: Optional[int] = None) -> int:
        """统计用户的对话数量"""
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)
        
        if video_id:
            query = query.filter(Conversation.video_id == video_id)
        
        return query.count()
    
    def get_with_messages(self, conversation_id: int) -> Optional[Conversation]:
        """获取对话及其消息"""
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )


class MessageRepository(BaseRepository[Message]):
    """消息仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, Message)
    
    def list_by_conversation(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """获取对话的消息列表"""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:
        """添加消息"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
