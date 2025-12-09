"""
Agent API 路由
Stage S2: AliceAgentCore 统一入口

所有 Agent 请求都通过此路由，统一构造 AgentTask 并调用 AliceAgentCore。
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import Tenant, User
from alice.agent import AgentTask, AgentResult, Scene, AliceAgentCore

from ..deps import get_current_tenant, get_current_user, get_db

router = APIRouter()


# ============== Request/Response Schemas ==============

class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    query: str = Field(..., description="用户问题")
    scene: str = Field(default="chat", description="场景：chat/research/timeline/library/video/graph")
    video_id: Optional[int] = Field(default=None, description="关联视频 ID")
    conversation_id: Optional[int] = Field(default=None, description="对话 ID")
    selection: Optional[str] = Field(default=None, description="用户选中的文本")
    extra_context: Optional[dict] = Field(default=None, description="额外上下文")


class AgentCitationResponse(BaseModel):
    """引用来源"""
    type: str
    id: str
    title: str
    snippet: str
    url: Optional[str] = None


class AgentStepResponse(BaseModel):
    """执行步骤"""
    step_idx: int
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    observation: Optional[str] = None
    error: Optional[str] = None


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    answer: str
    citations: List[AgentCitationResponse] = []
    steps: List[AgentStepResponse] = []
    # 调试信息
    strategy: Optional[str] = None
    processing_time_ms: Optional[int] = None


# ============== API Endpoints ==============

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Agent 统一对话入口
    
    所有场景（chat/research/timeline/library/video/graph）都通过此接口，
    由 AliceAgentCore 内部根据 scene 选择合适的策略。
    """
    start_time = datetime.utcnow()
    
    # 解析 scene
    try:
        scene = Scene(request.scene)
    except ValueError:
        scene = Scene.CHAT
    
    # 构造 AgentTask
    task = AgentTask(
        tenant_id=str(tenant.id),
        scene=scene,
        query=request.query,
        user_id=str(user.id),
        video_id=request.video_id,
        selection=request.selection,
        extra_context=request.extra_context or {},
    )
    
    # 执行 Agent
    try:
        core = AliceAgentCore(db)
        result = await core.run_task(task)
        
        # 计算处理时间
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # 构造响应
        return AgentChatResponse(
            answer=result.answer,
            citations=[
                AgentCitationResponse(
                    type=c.type,
                    id=c.id,
                    title=c.title,
                    snippet=c.snippet,
                    url=c.url,
                )
                for c in result.citations
            ],
            steps=[
                AgentStepResponse(
                    step_idx=s.step_idx,
                    thought=s.thought,
                    tool_name=s.tool_name,
                    tool_args=s.tool_args,
                    observation=s.observation,
                    error=s.error,
                )
                for s in result.steps
            ],
            strategy=scene.value,
            processing_time_ms=processing_time_ms,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent 执行失败: {str(e)}",
        )


@router.get("/strategies")
async def list_strategies():
    """
    列出支持的策略
    """
    from alice.agent import StrategySelector, ChatStrategy, ResearchStrategy, TimelineStrategy
    
    strategies = [
        {
            "name": "chat",
            "description": "对话策略 - 日常对话、解释和轻量问答",
            "allowed_tools": ChatStrategy().allowed_tools,
        },
        {
            "name": "research",
            "description": "研究策略 - 深度检索、多轮推理、Web 搜索",
            "allowed_tools": ResearchStrategy().allowed_tools,
        },
        {
            "name": "timeline",
            "description": "时间线策略 - 学习轨迹、自我变化分析",
            "allowed_tools": TimelineStrategy().allowed_tools,
        },
    ]
    
    return {"strategies": strategies}


@router.get("/scenes")
async def list_scenes():
    """
    列出支持的场景
    """
    return {
        "scenes": [
            {"value": s.value, "name": s.name}
            for s in Scene
        ]
    }
