"""
对话服务
对话相关的业务逻辑
"""

from typing import Optional, List, Tuple, AsyncGenerator

from packages.db import Conversation, Message, Video, User
from packages.logging import get_logger

from ..repositories.conversation_repo import ConversationRepository, MessageRepository
from ..repositories.video_repo import VideoRepository

logger = get_logger(__name__)


class ChatService:
    """对话服务类"""
    
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        video_repo: VideoRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.video_repo = video_repo
    
    def create_conversation(
        self,
        user: User,
        video_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        """创建对话"""
        # 验证视频是否存在
        if video_id:
            video = self.video_repo.get(video_id)
            if not video or video.tenant_id != user.tenant_id:
                raise ValueError("视频不存在")
        
        conversation = self.conversation_repo.create(
            user_id=user.id,
            video_id=video_id,
            title=title or "新对话",
        )
        
        logger.info(
            "conversation_created",
            conversation_id=conversation.id,
            user_id=user.id,
            video_id=video_id,
        )
        
        return conversation
    
    def get_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Optional[Conversation]:
        """获取对话"""
        conversation = self.conversation_repo.get(conversation_id)
        if conversation and conversation.user_id == user_id:
            return conversation
        return None
    
    def list_conversations(
        self,
        user_id: int,
        video_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Conversation], int]:
        """获取对话列表"""
        conversations = self.conversation_repo.list_by_user(
            user_id=user_id,
            video_id=video_id,
            skip=skip,
            limit=limit,
        )
        total = self.conversation_repo.count_by_user(user_id, video_id)
        return conversations, total
    
    def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """获取对话消息"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("对话不存在")
        
        return self.message_repo.list_by_conversation(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
        )
    
    def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
    ) -> Message:
        """添加消息"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("对话不存在")
        
        return self.message_repo.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
    
    def delete_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> bool:
        """删除对话及其消息"""
        conversation = self.get_conversation(conversation_id, user_id)
        if conversation:
            return self.conversation_repo.delete_with_messages(conversation_id)
        return False
    
    def get_message_count(self, conversation_id: int) -> int:
        """获取对话消息数量"""
        return len(self.message_repo.list_by_conversation(conversation_id))
    
    def send_user_message(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
    ) -> Message:
        """
        发送用户消息
        - 保存消息
        - 自动更新对话标题（首条消息时）
        - 更新对话时间戳
        """
        from packages.db import MessageRole
        
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("对话不存在")
        
        # 创建用户消息
        user_message = self.message_repo.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=content,
        )
        
        # 更新对话标题（首条消息时）
        if not conversation.title or conversation.title == "新对话":
            title = content[:30] + ("..." if len(content) > 30 else "")
            self.conversation_repo.update_title_and_timestamp(conversation, title)
        
        return user_message
    
    def update_compressed_context(
        self,
        conversation_id: int,
        user_id: int,
        compressed_context: str,
        compressed_at_message_id: int,
    ) -> None:
        """更新对话的压缩上下文"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("对话不存在")
        
        self.conversation_repo.update_compressed_context(
            conversation, compressed_context, compressed_at_message_id
        )
    
    def save_ai_message(
        self,
        conversation_id: int,
        content: str,
        sources: str = None,
    ) -> Message:
        """保存AI回复消息"""
        from packages.db import MessageRole
        
        return self.message_repo.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=content,
            sources=sources,
        )
