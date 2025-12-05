"""
TaskPlanner - 任务规划器

职责：
- 接收 AgentTask + Context
- 输出 AgentPlan（step 列表）
- 将复杂任务拆解为可执行的多步计划

"""

import json
import logging
import re
import time
from typing import List, Optional, Dict, Any

from .types import AgentTask, AgentPlan, PlanStepState

logger = logging.getLogger(__name__)


# 规划系统提示
PLANNING_SYSTEM_PROMPT = """你是一个专业的任务规划助手，负责将复杂任务分解为清晰、可执行的步骤。

你的工作是：
1. 分析请求，理解任务范围
2. 创建清晰、可操作的计划
3. 关注关键里程碑，而非过于详细的子步骤
4. 考虑步骤间的依赖关系

注意事项：
- 将任务分解为逻辑步骤，每步都有明确的成果
- 避免过度细节化
- 当任务简单时，返回单步计划
"""

PLANNING_USER_PROMPT = """## 可用工具
{tools_description}

## 用户请求
{query}

## 任务
请为这个请求创建一个合理的执行计划。

## 输出格式
只输出 JSON 对象，包含以下字段：
{{
    "title": "计划标题",
    "steps": ["步骤1", "步骤2", "步骤3"]
}}

如果是简单问题，只需一步即可：
{{
    "title": "直接回答",
    "steps": ["直接回答用户问题"]
}}

请输出："""


class TaskPlanner:
    """
    任务规划器
    
    负责将 AgentTask 拆解为多步执行计划。
    对于简单问题返回单步计划，复杂问题返回多步计划。
    
    """
    
    def __init__(self, use_llm_planning: bool = True):
        """
        Args:
            use_llm_planning: 是否使用 LLM 进行规划。
                              False 时直接返回单步计划（用于简单场景或测试）
        """
        self.use_llm_planning = use_llm_planning
        # 存储计划
        self.plans: Dict[str, Dict[str, Any]] = {}
    
    async def plan(
        self, 
        task: AgentTask, 
        context: Optional[dict] = None,
        available_tools: Optional[List[str]] = None
    ) -> AgentPlan:
        """
        为任务生成执行计划
        
        Args:
            task: AgentTask 输入
            context: 上下文信息
            available_tools: 当前可用的工具列表
            
        Returns:
            AgentPlan 包含执行步骤
        """
        plan_id = f"plan_{int(time.time())}"
        
        # 简单场景检测
        if self._is_simple_query(task.query):
            logger.info("Simple query detected, using single-step plan")
            plan = AgentPlan(
                steps=["直接回答用户问题"],
                current_step=0
            )
            self._store_plan(plan_id, "直接回答", plan.steps)
            return plan
        
        # 如果不使用 LLM 规划，直接返回单步
        if not self.use_llm_planning:
            plan = AgentPlan(
                steps=["直接回答用户问题"],
                current_step=0
            )
            self._store_plan(plan_id, "直接回答", plan.steps)
            return plan
        
        # 使用 LLM 生成计划
        try:
            title, steps = await self._create_plan_with_llm(
                task.query, 
                available_tools or []
            )
            logger.info(f"Generated plan '{title}' with {len(steps)} steps: {steps}")
            
            plan = AgentPlan(steps=steps, current_step=0)
            self._store_plan(plan_id, title, steps)
            return plan
            
        except Exception as e:
            logger.warning(f"Planning failed: {e}, falling back to default plan")
            # 创建默认计划
            default_steps = ["分析请求", "执行任务", "验证结果"]
            plan = AgentPlan(steps=default_steps, current_step=0)
            self._store_plan(plan_id, f"Plan for: {task.query[:50]}", default_steps)
            return plan
    
    def _store_plan(self, plan_id: str, title: str, steps: List[str]) -> None:
        """存储计划"""
        self.plans[plan_id] = {
            "title": title,
            "steps": steps,
            "step_statuses": [PlanStepState.NOT_STARTED.value] * len(steps),
            "created_at": time.time(),
        }
    
    def mark_step(self, plan_id: str, step_index: int, status: str) -> None:
        """标记步骤状态"""
        if plan_id in self.plans:
            plan = self.plans[plan_id]
            if step_index < len(plan["step_statuses"]):
                plan["step_statuses"][step_index] = status
    
    def get_plan_text(self, plan_id: str) -> str:
        """获取计划文本表示"""
        if plan_id not in self.plans:
            return "无计划"
        
        plan = self.plans[plan_id]
        marks = PlanStepState.get_status_marks()
        lines = [f"# {plan['title']}"]
        
        for i, step in enumerate(plan["steps"]):
            status = plan["step_statuses"][i] if i < len(plan["step_statuses"]) else PlanStepState.NOT_STARTED.value
            mark = marks.get(status, "[ ]")
            lines.append(f"{mark} {i+1}. {step}")
        
        return "\n".join(lines)
    
    def _is_simple_query(self, query: str) -> bool:
        """检测是否为简单问题（不需要工具）"""
        simple_patterns = [
            r"^你好",
            r"^hi\b",
            r"^hello\b",
            r"^谢谢",
            r"^好的",
            r"^嗯",
            r"^是什么意思",
            r"解释.{0,10}$",
        ]
        
        query_lower = query.lower().strip()
        
        # 太短的问题视为简单
        if len(query) < 10:
            return True
        
        for pattern in simple_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True
        
        return False
    
    async def _create_plan_with_llm(
        self, 
        query: str, 
        available_tools: List[str]
    ) -> tuple:
        """
        使用 LLM 生成执行计划
        """
        from services.ai.llm import LLMManager
        
        # 构建工具描述
        tools_desc = self._format_tools_description(available_tools)
        
        # 构建 prompt
        user_prompt = PLANNING_USER_PROMPT.format(
            tools_description=tools_desc,
            query=query,
        )
        
        llm = LLMManager()
        response = llm.chat([
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        
        # 解析响应
        title, steps = self._parse_plan_response(response, query)
        
        # 确保至少有一步
        if not steps:
            steps = ["直接回答用户问题"]
            title = "直接回答"
        
        return title, steps
    
    def _format_tools_description(self, tools: List[str]) -> str:
        """格式化工具描述"""
        if not tools:
            return "无可用工具，只能直接回答。"
        
        tool_descs = {
            "echo": "echo - 调试工具，原样返回输入",
            "current_time": "current_time - 获取当前时间",
            "sleep": "sleep - 暂停执行指定秒数",
            "get_timeline_summary": "get_timeline_summary - 获取用户学习时间线摘要",
            "get_video_summary": "get_video_summary - 获取指定视频的摘要",
            "search_videos": "search_videos - 在视频库中搜索相关视频",
        }
        
        lines = []
        for t in tools:
            desc = tool_descs.get(t, f"{t} - 工具")
            lines.append(f"- {desc}")
        
        return "\n".join(lines) if lines else "无可用工具"
    
    def _parse_plan_response(self, response: str, query: str) -> tuple:
        """
        解析 LLM 返回的计划
        """
        title = f"Plan for: {query[:30]}"
        steps = []
        
        try:
            # 尝试提取 JSON 对象
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group()
                data = json.loads(json_str)
                
                if isinstance(data, dict):
                    title = data.get("title", title)
                    steps = data.get("steps", [])
                    if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
                        return title, steps
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 尝试提取 JSON 数组
        try:
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                json_str = match.group()
                steps = json.loads(json_str)
                if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
                    return title, steps
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 解析失败，尝试按行分割
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        steps = [
            line.lstrip('0123456789.-) ') 
            for line in lines 
            if len(line) > 3 and not line.startswith('{') and not line.startswith('[')
        ]
        
        return title, steps[:10]  # 最多 10 步
