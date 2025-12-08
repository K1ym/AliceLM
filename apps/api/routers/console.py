"""
Console API 路由

提供 Agent 观测、Eval 执行和管理功能
仅限管理员使用
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import Tenant

from ..deps import get_current_tenant, get_db

router = APIRouter()


# ============== Schemas ==============

class AgentRunResponse(BaseModel):
    """Agent 执行日志响应"""
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    scene: str
    query: str
    answer: str
    success: bool
    duration_ms: int
    started_at: datetime
    finished_at: Optional[datetime] = None


class AgentRunDetailResponse(AgentRunResponse):
    """Agent 执行日志详情"""
    steps: List[dict] = []
    tool_traces: List[dict] = []
    citations: List[dict] = []
    extra_context: dict = {}


class AgentRunStatsResponse(BaseModel):
    """Agent 执行统计"""
    total_runs: int
    success_rate: float
    avg_duration_ms: int
    scenes: dict


class EvalCaseRequest(BaseModel):
    """Eval 用例请求"""
    scene: str = "chat"
    query: str
    expected_answer: Optional[str] = None
    expected_keywords: List[str] = []
    expected_tool_calls: List[str] = []


class EvalSuiteRequest(BaseModel):
    """Eval 套件请求"""
    name: str = "custom"
    cases: List[EvalCaseRequest]


class EvalResultResponse(BaseModel):
    """Eval 结果响应"""
    case_id: str
    success: bool
    score: float
    answer: str
    reasoning: Optional[str] = None
    tools_called: List[str] = []
    execution_time_ms: int


class EvalSuiteResultResponse(BaseModel):
    """Eval 套件结果响应"""
    suite_id: str
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_score: float
    total_time_ms: int
    results: List[EvalResultResponse]


# ============== Agent Runs API ==============

@router.get("/agent-runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    scene: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    获取 Agent 执行日志列表
    """
    from alice.agent.run_logger import get_agent_run_logger
    
    logger = get_agent_run_logger()
    runs = logger.get_runs(
        tenant_id=str(tenant.id),
        scene=scene,
        limit=limit,
        offset=offset,
    )
    
    return [
        AgentRunResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            user_id=r.user_id,
            scene=r.scene,
            query=r.query,
            answer=r.answer[:200] + "..." if len(r.answer) > 200 else r.answer,
            success=r.success,
            duration_ms=r.duration_ms,
            started_at=r.started_at,
            finished_at=r.finished_at,
        )
        for r in runs
    ]


@router.get("/agent-runs/stats", response_model=AgentRunStatsResponse)
async def get_agent_run_stats(
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    获取 Agent 执行统计
    """
    from alice.agent.run_logger import get_agent_run_logger
    
    logger = get_agent_run_logger()
    stats = logger.get_stats(tenant_id=str(tenant.id))
    
    return AgentRunStatsResponse(**stats)


@router.get("/agent-runs/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run_detail(
    run_id: str,
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    获取 Agent 执行日志详情
    """
    from alice.agent.run_logger import get_agent_run_logger
    
    logger = get_agent_run_logger()
    run = logger.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    
    if run.tenant_id != str(tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return AgentRunDetailResponse(
        id=run.id,
        tenant_id=run.tenant_id,
        user_id=run.user_id,
        scene=run.scene,
        query=run.query,
        answer=run.answer,
        success=run.success,
        duration_ms=run.duration_ms,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=run.steps,
        tool_traces=run.tool_traces,
        citations=run.citations,
        extra_context=run.extra_context,
    )


# ============== Eval API ==============

@router.post("/eval/run-suite", response_model=EvalSuiteResultResponse)
async def run_eval_suite(
    request: EvalSuiteRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    运行 Eval 套件
    """
    from alice.eval import EvalRunner, EvalSuite, EvalCase
    
    # 构造 EvalSuite
    cases = [
        EvalCase(
            scene=c.scene,
            query=c.query,
            expected_answer=c.expected_answer,
            expected_keywords=c.expected_keywords,
            expected_tool_calls=c.expected_tool_calls,
        )
        for c in request.cases
    ]
    
    suite = EvalSuite(name=request.name, cases=cases)
    
    # 运行
    runner = EvalRunner(db)
    suite_result = await runner.run_suite(
        suite=suite,
        tenant_id=str(tenant.id),
    )
    
    return EvalSuiteResultResponse(
        suite_id=suite_result.suite_id,
        suite_name=suite_result.suite_name,
        total_cases=suite_result.total_cases,
        passed_cases=suite_result.passed_cases,
        failed_cases=suite_result.failed_cases,
        avg_score=suite_result.avg_score,
        total_time_ms=suite_result.total_time_ms,
        results=[
            EvalResultResponse(
                case_id=r.case_id,
                success=r.success,
                score=r.score,
                answer=r.answer[:500] if r.answer else "",
                reasoning=r.reasoning,
                tools_called=r.tools_called,
                execution_time_ms=r.execution_time_ms,
            )
            for r in suite_result.results
        ],
    )


@router.post("/eval/run-default")
async def run_default_eval(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    运行默认 Eval 套件
    """
    from alice.eval import EvalRunner
    from alice.eval.runner import get_default_suite
    
    suite = get_default_suite()
    runner = EvalRunner(db)
    
    suite_result = await runner.run_suite(
        suite=suite,
        tenant_id=str(tenant.id),
    )
    
    return {
        "suite_name": suite_result.suite_name,
        "total_cases": suite_result.total_cases,
        "passed_cases": suite_result.passed_cases,
        "avg_score": suite_result.avg_score,
        "total_time_ms": suite_result.total_time_ms,
    }


# ============== Tools API ==============

@router.get("/tools")
async def list_tools(
    scene: str = "console",
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    列出可用工具（使用控制平面）
    """
    from alice.control_plane import get_control_plane
    from alice.agent.permissions import ToolVisibilityPolicy
    
    cp = get_control_plane()
    
    # 获取场景可用工具
    scene_tools = cp.list_tools_for_scene(scene)
    all_tools = [t.name for t in cp.tools.list_tools(enabled_only=False)]
    
    # 应用权限过滤
    policy = ToolVisibilityPolicy(user_role="admin", scene=scene, enable_unsafe=True)
    allowed_tools = policy.filter_tools(scene_tools)
    
    return {
        "scene": scene,
        "total_tools": len(all_tools),
        "scene_tools": len(scene_tools),
        "allowed_tools": len(allowed_tools),
        "tools": allowed_tools,
        "blocked_tools": [t for t in scene_tools if t not in allowed_tools],
    }
