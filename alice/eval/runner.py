"""
Eval Runner

执行评估套件并收集结果
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from alice.agent import AgentTask, AgentResult, Scene, AliceAgentCore
from .models import EvalCase, EvalSuite, EvalResult, EvalSuiteResult
from .scorers import BaseScorer, SimpleScorer

logger = logging.getLogger(__name__)


class EvalRunner:
    """
    评估执行器
    
    运行 EvalSuite 中的所有用例，收集并返回结果
    """
    
    def __init__(
        self,
        db: Session,
        scorer: Optional[BaseScorer] = None,
    ):
        """
        Args:
            db: 数据库 session
            scorer: 评分器，默认使用 SimpleScorer
        """
        self.db = db
        self.scorer = scorer or SimpleScorer()
        self._agent_core: Optional[AliceAgentCore] = None
    
    def _get_agent_core(self) -> AliceAgentCore:
        """获取 AgentCore 实例"""
        if self._agent_core is None:
            self._agent_core = AliceAgentCore(self.db)
        return self._agent_core
    
    async def run_suite(
        self,
        suite: EvalSuite,
        tenant_id: str,
        user_id: Optional[str] = None,
        stop_on_error: bool = False,
    ) -> EvalSuiteResult:
        """
        运行评估套件
        
        Args:
            suite: 评估套件
            tenant_id: 租户 ID
            user_id: 用户 ID
            stop_on_error: 遇到错误时是否停止
            
        Returns:
            EvalSuiteResult
        """
        logger.info(f"Starting eval suite: {suite.name} ({len(suite.cases)} cases)")
        
        suite_result = EvalSuiteResult(
            suite_id=suite.id,
            suite_name=suite.name,
            started_at=datetime.utcnow(),
        )
        
        for i, case in enumerate(suite.cases):
            logger.info(f"Running case {i+1}/{len(suite.cases)}: {case.id}")
            
            try:
                result = await self.run_case(case, tenant_id, user_id)
                suite_result.results.append(result)
                
                logger.info(
                    f"Case {case.id}: score={result.score:.2f}, "
                    f"success={result.success}, time={result.execution_time_ms}ms"
                )
                
            except Exception as e:
                logger.error(f"Case {case.id} failed: {e}")
                
                error_result = EvalResult(
                    case_id=case.id,
                    success=False,
                    score=0.0,
                    answer="",
                    error=str(e),
                )
                suite_result.results.append(error_result)
                
                if stop_on_error:
                    break
        
        # 计算统计
        suite_result.compute_stats()
        
        logger.info(
            f"Eval suite completed: {suite.name} - "
            f"passed={suite_result.passed_cases}/{suite_result.total_cases}, "
            f"avg_score={suite_result.avg_score:.2f}"
        )
        
        return suite_result
    
    async def run_case(
        self,
        case: EvalCase,
        tenant_id: str,
        user_id: Optional[str] = None,
    ) -> EvalResult:
        """
        运行单个评估用例
        
        Args:
            case: 评估用例
            tenant_id: 租户 ID
            user_id: 用户 ID
            
        Returns:
            EvalResult
        """
        start_time = time.time()
        
        # 解析 scene
        try:
            scene = Scene(case.scene)
        except ValueError:
            scene = Scene.CHAT
        
        # 构造 AgentTask
        task = AgentTask(
            tenant_id=tenant_id,
            scene=scene,
            query=case.query,
            user_id=user_id,
            video_id=case.video_id,
            extra_context={
                **case.extra_context,
                "eval_case_id": case.id,
                "user_role": "admin",  # Eval 使用 admin 权限
            },
        )
        
        # 执行 Agent
        agent_core = self._get_agent_core()
        agent_result = await agent_core.run_task(task)
        
        # 计算执行时间
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # 评分
        eval_result = await self.scorer.score(case, agent_result)
        eval_result.execution_time_ms = execution_time_ms
        
        return eval_result
    
    async def run_single(
        self,
        query: str,
        tenant_id: str,
        scene: str = "chat",
        expected_answer: Optional[str] = None,
        expected_keywords: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> EvalResult:
        """
        快速运行单个测试
        
        便捷方法，用于快速测试单个问题
        """
        case = EvalCase(
            scene=scene,
            query=query,
            expected_answer=expected_answer,
            expected_keywords=expected_keywords or [],
        )
        
        return await self.run_case(case, tenant_id, user_id)


# 预定义的测试套件
DEFAULT_EVAL_CASES = [
    {
        "scene": "chat",
        "query": "你好，请介绍一下你自己",
        "expected_keywords": ["Alice", "助手"],
    },
    {
        "scene": "chat",
        "query": "现在几点了？",
        "expected_tool_calls": ["current_time"],
    },
    {
        "scene": "chat",
        "query": "计算 123 * 456 的结果",
        "expected_keywords": ["56088"],
        "expected_tool_calls": ["calculator"],
    },
    {
        "scene": "research",
        "query": "什么是 MCP 协议？",
        "expected_keywords": ["Model", "Context", "Protocol"],
    },
]


def get_default_suite() -> EvalSuite:
    """获取默认测试套件"""
    return EvalSuite.from_dict_list("default", DEFAULT_EVAL_CASES)
