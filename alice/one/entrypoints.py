"""
统一入口适配层

所有主要入口（chat、qa、video、timeline、console）都通过此模块，
统一构造 AgentTask 并调用 AliceAgentCore.run_task()。
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from alice.agent import AgentTask, AgentResult, Scene, AliceAgentCore
from alice.one.identity import AliceIdentityService

logger = logging.getLogger(__name__)


async def handle_chat_request(
    db: Session,
    tenant_id: str,
    query: str,
    scene: str = "chat",
    user_id: Optional[str] = None,
    user_role: str = "normal",
    video_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    selection: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> AgentResult:
    """
    统一 Chat 入口适配器
    
    Args:
        db: 数据库 session
        tenant_id: 租户 ID
        query: 用户问题
        scene: 场景 (chat/research/timeline/library/video/graph/console)
        user_id: 用户 ID
        user_role: 用户角色 (admin/normal/guest)
        video_id: 关联视频 ID
        conversation_id: 对话 ID
        selection: 用户选中的文本
        extra_context: 额外上下文
        
    Returns:
        AgentResult
    """
    logger.info(f"handle_chat_request: scene={scene}, query={query[:50]}...")
    
    # 解析 scene
    try:
        scene_enum = Scene(scene)
    except ValueError:
        scene_enum = Scene.CHAT
    
    # 构造 extra_context
    ctx = extra_context or {}
    ctx["user_role"] = user_role
    ctx["source"] = "unified_entry"
    
    if conversation_id:
        ctx["conversation_id"] = conversation_id
    
    # 构造 AgentTask
    task = AgentTask(
        tenant_id=tenant_id,
        scene=scene_enum,
        query=query,
        user_id=user_id,
        video_id=video_id,
        selection=selection,
        extra_context=ctx,
    )
    
    # 执行 Agent
    core = AliceAgentCore(db)
    result = await core.run_task(task)
    
    return result


async def handle_qa_request(
    db: Session,
    tenant_id: str,
    question: str,
    video_ids: Optional[list] = None,
    user_id: Optional[str] = None,
    user_role: str = "normal",
) -> AgentResult:
    """
    统一 QA 入口适配器
    
    原 /qa/ask API 的统一入口版本
    """
    extra_context = {
        "source": "qa_api",
        "user_role": user_role,
    }
    
    if video_ids:
        extra_context["video_ids"] = video_ids
    
    return await handle_chat_request(
        db=db,
        tenant_id=tenant_id,
        query=question,
        scene="library",  # QA 使用 library 场景
        user_id=user_id,
        user_role=user_role,
        extra_context=extra_context,
    )


async def handle_video_chat_request(
    db: Session,
    tenant_id: str,
    video_id: int,
    question: str,
    selection: Optional[str] = None,
    user_id: Optional[str] = None,
    user_role: str = "normal",
) -> AgentResult:
    """
    统一视频问答入口适配器
    """
    return await handle_chat_request(
        db=db,
        tenant_id=tenant_id,
        query=question,
        scene="video",
        user_id=user_id,
        user_role=user_role,
        video_id=video_id,
        selection=selection,
        extra_context={
            "source": "video_detail",
            "user_role": user_role,
        },
    )


async def handle_console_request(
    db: Session,
    tenant_id: str,
    query: str,
    scene: str = "chat",
    user_id: Optional[str] = None,
    enable_unsafe_tools: bool = False,
    extra_context: Optional[Dict[str, Any]] = None,
) -> AgentResult:
    """
    Console/Admin 入口适配器
    
    允许访问更多工具和能力
    """
    ctx = extra_context or {}
    ctx["user_role"] = "admin"
    ctx["source"] = "console"
    ctx["enable_unsafe_tools"] = enable_unsafe_tools
    
    return await handle_chat_request(
        db=db,
        tenant_id=tenant_id,
        query=query,
        scene=scene,
        user_id=user_id,
        user_role="admin",
        extra_context=ctx,
    )
