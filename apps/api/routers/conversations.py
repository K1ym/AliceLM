"""
对话API路由
"""

from datetime import datetime
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.db import Conversation, Message, MessageRole, User
from packages.logging import get_logger
from services.ai import RAGService
from services.ai.llm import LLMManager, Message as LLMMessage, create_llm_from_config
from services.ai.context_compressor import ContextCompressor, create_compressor_from_config

from ..deps import get_db, get_current_user
from .config import get_task_llm_config, get_user_prompt

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

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """对话详情响应"""
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


# ============== API ==============

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取对话列表"""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )
    
    result = []
    for conv in conversations:
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
        ))
    
    return result


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新对话"""
    conversation = Conversation(
        tenant_id=user.tenant_id,
        user_id=user.id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
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
    db: Session = Depends(get_db),
):
    """删除对话"""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )
    
    # 删除关联的消息
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    # 删除对话
    db.delete(conversation)
    db.commit()
    
    return {"message": "对话已删除", "id": conversation_id}


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取对话详情"""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )
    
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    
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


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除对话"""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "删除成功"}


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
    db: Session = Depends(get_db),
):
    """
    发送消息并获取流式AI回复
    
    返回SSE格式的流式响应：
    - type: thinking - 思维链内容
    - type: content - 正常回复内容
    - type: done - 完成，包含完整内容
    - type: error - 错误信息
    """
    # 提前提取需要的值（避免Session detach问题）
    user_id = user.id
    tenant_id = user.tenant_id
    message_content = request.content
    
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )
    
    # 保存用户消息
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=message_content,
    )
    db.add(user_message)
    
    # 更新对话标题（首条消息时）
    if not conversation.title:
        conversation.title = message_content[:30] + ("..." if len(message_content) > 30 else "")
    
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_message)
    
    # 预先获取配置（在Session有效时）
    llm_config = get_task_llm_config(db, user_id, "chat")
    compress_config = get_task_llm_config(db, user_id, "context_compress")
    chat_system_prompt = get_user_prompt(db, user_id, "chat")
    
    # 预先获取历史和压缩信息（在流式前完成）
    all_history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history_data = [{"role": m.role.value, "content": m.content, "id": m.id} for m in all_history]
    total_chars = sum(len(m["content"]) for m in history_data)
    compressed_context = conversation.compressed_context
    compressed_at_id = conversation.compressed_at_message_id or 0
    
    # 如果需要压缩，在流式前执行（阻塞但避免流中卡顿）
    if total_chars > CONTEXT_CHAR_THRESHOLD and len(history_data) > KEEP_RECENT_MESSAGES:
        old_msgs = history_data[:-KEEP_RECENT_MESSAGES]
        msgs_to_compress = [m for m in old_msgs if m["id"] > compressed_at_id]
        
        if msgs_to_compress:
            # 创建LLM
            if llm_config.get("api_key") and llm_config.get("base_url"):
                temp_llm = create_llm_from_config(
                    base_url=compress_config.get("base_url") or llm_config["base_url"],
                    api_key=compress_config.get("api_key") or llm_config["api_key"],
                    model=compress_config.get("model") or llm_config["model"],
                )
            else:
                temp_llm = get_llm_manager()
            
            compressor = ContextCompressor(llm_manager=temp_llm)
            result = compressor.compress(msgs_to_compress, compressed_context)
            
            # 保存压缩结果
            conversation.compressed_context = result.compressed
            conversation.compressed_at_message_id = old_msgs[-1]["id"] if old_msgs else 0
            db.commit()
            
            compressed_context = result.compressed
            logger.info(
                "context_compressed_before_stream",
                conversation_id=conversation_id,
                compressed_count=result.original_count,
            )
    
    async def generate_stream():
        from starlette.concurrency import iterate_in_threadpool
        from packages.db import get_db_context
        
        full_content = ""
        full_reasoning = ""
        
        def sync_generator():
            """同步生成器"""
            nonlocal full_content, full_reasoning
            
            try:
                # 构建LLM
                if llm_config.get("api_key") and llm_config.get("base_url"):
                    llm = create_llm_from_config(
                        base_url=llm_config["base_url"],
                        api_key=llm_config["api_key"],
                        model=llm_config["model"],
                    )
                else:
                    llm = get_llm_manager()
                
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
                    with get_db_context() as save_db:
                        ai_message = Message(
                            conversation_id=conversation_id,
                            role=MessageRole.ASSISTANT,
                            content=full_content,
                            sources=json.dumps({"reasoning": full_reasoning}) if full_reasoning else None,
                        )
                        save_db.add(ai_message)
                        save_db.commit()
                        save_db.refresh(ai_message)
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
