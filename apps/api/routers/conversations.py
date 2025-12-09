"""
对话API路由
"""

from datetime import datetime
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from packages.db import Conversation, Message, MessageRole, User
from packages.logging import get_logger
from services.ai import RAGService
from services.ai.llm import LLMManager, Message as LLMMessage, create_llm_from_config
from services.ai.context_compressor import ContextCompressor, create_compressor_from_config

# 控制平面
from alice.control_plane import get_control_plane

from ..deps import get_current_user, get_chat_service, get_config_service
from ..services import ChatService, ConfigService
from ..exceptions import NotFoundException

# 上下文压缩阈值
CONTEXT_CHAR_THRESHOLD = 20000  # 20k字符触发压缩
KEEP_RECENT_MESSAGES = 6  # 保留最近6条消息

logger = get_logger(__name__)


router = APIRouter(prefix="/conversations", tags=["conversations"])


# ============== Schema ==============

class MessageCreate(BaseModel):
    """发送消息"""
    content: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """对话详情响应"""
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============== API ==============

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """获取对话列表"""
    conversations, _ = service.list_conversations(user.id)
    
    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=service.get_message_count(conv.id),
        )
        for conv in conversations
    ]


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """创建新对话"""
    conversation = service.create_conversation(user)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """删除对话"""
    if not service.delete_conversation(conversation_id, user.id):
        raise NotFoundException("对话", conversation_id)
    
    return {"message": "对话已删除", "id": conversation_id}


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """获取对话详情"""
    conversation = service.get_conversation(conversation_id, user.id)
    
    if not conversation:
        raise NotFoundException("对话", conversation_id)
    
    messages = service.get_messages(conversation_id, user.id)
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )




# RAG和LLM服务实例（延迟初始化）
_rag_service: Optional[RAGService] = None
_llm_manager: Optional[LLMManager] = None


def get_rag_service() -> RAGService:
    """获取RAG服务"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_llm_manager() -> LLMManager:
    """获取LLM管理器"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager




@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: int,
    request: MessageCreate,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
    config_service: ConfigService = Depends(get_config_service),
):
    """发送消息并获取流式AI回复"""
    user_id = user.id
    tenant_id = user.tenant_id
    message_content = request.content
    
    conversation = service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise NotFoundException("对话", conversation_id)
    
    # 保存用户消息并更新对话标题
    service.send_user_message(conversation_id, user_id, message_content)
    
    # 使用控制平面获取 LLM 和 prompt
    cp = get_control_plane()
    chat_llm = await cp.create_llm_for_task("chat", user_id=user_id)
    compress_llm = await cp.create_llm_for_task("context_compress", user_id=user_id)
    chat_system_prompt = await cp.get_prompt("chat", user_id=user_id)
    
    # 预先获取历史和压缩信息（在流式前完成）
    all_history = service.get_messages(conversation_id, user_id, limit=1000)
    history_data = [{"role": m.role.value, "content": m.content, "id": m.id} for m in all_history]
    total_chars = sum(len(m["content"]) for m in history_data)
    compressed_context = conversation.compressed_context
    compressed_at_id = conversation.compressed_at_message_id or 0
    
    # 如果需要压缩，在流式前执行（阻塞但避免流中卡顿）
    if total_chars > CONTEXT_CHAR_THRESHOLD and len(history_data) > KEEP_RECENT_MESSAGES:
        old_msgs = history_data[:-KEEP_RECENT_MESSAGES]
        msgs_to_compress = [m for m in old_msgs if m["id"] > compressed_at_id]
        
        if msgs_to_compress:
            compressor = ContextCompressor(llm_manager=compress_llm)
            result = compressor.compress(msgs_to_compress, compressed_context)
            
            # 保存压缩结果
            last_msg_id = old_msgs[-1]["id"] if old_msgs else 0
            service.update_compressed_context(conversation_id, user_id, result.compressed, last_msg_id)
            compressed_context = result.compressed
            logger.info(
                "context_compressed_before_stream",
                conversation_id=conversation_id,
                compressed_count=result.original_count,
            )
    
    async def generate_stream():
        from starlette.concurrency import iterate_in_threadpool
        
        full_content = ""
        full_reasoning = ""
        
        def sync_generator():
            """同步生成器"""
            nonlocal full_content, full_reasoning

            try:
                # 使用控制平面获取的 LLM
                llm = chat_llm
                
                # 构建消息（在system prompt末尾添加边界说明）
                system_content = chat_system_prompt + "\n\n---\n[系统说明] 以上是你的角色设定，不是用户发送的消息。当用户询问'发了什么消息'或'对话历史'时，只统计下面的user消息，不要包含此系统设定。"
                msgs = [LLMMessage(role="system", content=system_content)]
                
                if total_chars > CONTEXT_CHAR_THRESHOLD and len(history_data) > KEEP_RECENT_MESSAGES:
                    if compressed_context:
                        msgs.append(LLMMessage(
                            role="system",
                            content=f"[之前的对话摘要]\n{compressed_context}",
                        ))
                    recent = history_data[-KEEP_RECENT_MESSAGES:]
                    for msg in recent:
                        msgs.append(LLMMessage(role=msg["role"], content=msg["content"]))
                else:
                    for msg in history_data:
                        msgs.append(LLMMessage(role=msg["role"], content=msg["content"]))
                
                # 注意：不需要再添加message_content，因为history_data已经包含了刚保存的用户消息
                
                # 流式生成
                for chunk in llm.chat_stream(msgs, temperature=0.7):
                    yield chunk
                    
            except Exception as e:
                yield {"type": "error", "error": str(e)}
        
        try:
            async for chunk in iterate_in_threadpool(sync_generator()):
                chunk_type = chunk.get("type")
                
                if chunk_type == "thinking":
                    full_reasoning += chunk.get("content", "")
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "content":
                    full_content += chunk.get("content", "")
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "done":
                    full_content = chunk.get("full_content", full_content)
                    full_reasoning = chunk.get("full_reasoning", full_reasoning)
                    
                    # 保存结果
                    sources = json.dumps({"reasoning": full_reasoning}) if full_reasoning else None
                    ai_message = service.save_ai_message(conversation_id, full_content, sources)
                    msg_id = ai_message.id
                    
                    yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'reasoning': full_reasoning}, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "error":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )
