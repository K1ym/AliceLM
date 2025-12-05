"""
AliceAgentCore - Agent 引擎统一入口

职责：
- 接收 AgentTask，返回 AgentResult
- 内部协调 StrategySelector / TaskPlanner / ToolExecutor / ToolRouter / MemoryManager
- 所有入口场景（chat / library / video / graph / timeline / tasks / console）
  最终都通过 AliceAgentCore.run_task() 处理
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from .types import AgentTask, AgentResult, AgentStep, AgentCitation
from .strategy import StrategySelector
from .tool_router import ToolRouter

logger = logging.getLogger(__name__)


class AliceAgentCore:
    """
    Alice Agent 引擎统一入口
    
    内部组件：
    - StrategySelector: 根据 scene/intent 选择执行策略
    - ToolRouter: 工具分发（本地 + MCP）
    - TaskPlanner: 将任务拆成多步计划（S4 实现）
    - ToolExecutor: ReAct 循环执行（S4 实现）
    """
    
    def __init__(self, db: Session, enable_tools: bool = True):
        """
        初始化 Agent Core
        
        Args:
            db: 数据库 Session
            enable_tools: 是否启用工具（默认 True）
        """
        self.db = db
        self.strategy_selector = StrategySelector()
        self.enable_tools = enable_tools
        
        # 创建并注册基础工具
        if enable_tools:
            self.tool_router = ToolRouter.create_with_basic_tools(db)
        else:
            self.tool_router = None
        
        # S4 实现后启用
        # self.task_planner = TaskPlanner()
        # self.tool_executor = ToolExecutor()
    
    async def run_task(self, task: AgentTask) -> AgentResult:
        """
        执行 Agent 任务
        
        流程：
        1. StrategySelector 根据 scene 选择 Strategy
        2. 从 AliceIdentityService 获取 persona + tool_scopes
        3. ContextAssembler 组装上下文
        4. 调用 LLM 生成回答（暂不启用工具）
        5. 返回 AgentResult
        
        Args:
            task: AgentTask 输入
            
        Returns:
            AgentResult 包含 answer, citations, steps 等
        """
        steps: List[AgentStep] = []
        citations: List[AgentCitation] = []
        
        try:
            # Step 1: 选择策略
            strategy = self.strategy_selector.select(task)
            logger.info(f"Selected strategy: {strategy.name} for scene: {task.scene}")
            steps.append(AgentStep(
                step_idx=0,
                thought=f"根据场景 {task.scene.value} 选择 {strategy.name} 策略",
            ))
            
            # Step 2: 获取 Alice 身份
            from alice.one import AliceIdentityService
            identity_service = AliceIdentityService(self.db)
            identity = await identity_service.get_identity(
                tenant_id=int(task.tenant_id) if task.tenant_id.isdigit() else 1,
                user_id=int(task.user_id) if task.user_id and task.user_id.isdigit() else None,
                scene=task.scene.value,
            )
            logger.info(f"Got identity: {identity.persona.name}, tools: {len(identity.enabled_tools)}")
            
            # Step 3: 组装上下文
            from alice.one import ContextAssembler
            assembler = ContextAssembler(self.db)
            context = await assembler.assemble(
                tenant_id=int(task.tenant_id) if task.tenant_id.isdigit() else 1,
                query=task.query,
                user_id=int(task.user_id) if task.user_id and task.user_id.isdigit() else None,
                video_id=task.video_id,
                scene=task.scene.value,
                extra_context=task.extra_context,
            )
            
            # 提取 citations
            for c in context.citations:
                citations.append(AgentCitation(
                    type=c.type,
                    id=c.id,
                    title=c.title,
                    snippet=c.snippet,
                    url=c.url,
                ))
            
            # Step 4: 获取可用工具
            tool_schemas = []
            if self.enable_tools and self.tool_router:
                tool_schemas = self.tool_router.list_tool_schemas(
                    allowed_tools=identity.enabled_tools
                )
                logger.info(f"Available tools: {len(tool_schemas)}")
            
            # Step 5: 构建 messages
            messages = self._build_messages(
                system_prompt=identity.system_prompt,
                strategy_suffix=strategy.get_system_prompt_suffix(),
                context_messages=context.messages,
            )
            
            steps.append(AgentStep(
                step_idx=1,
                thought=f"构建上下文，包含 {len(messages)} 条消息，{len(tool_schemas)} 个工具",
            ))
            
            # Step 6: 调用 LLM（附带工具 schema）
            answer, tool_calls = await self._call_llm_with_tools(messages, tool_schemas)
            
            # Step 7: 处理工具调用（如果有）
            if tool_calls and self.tool_router:
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("arguments", {})
                    
                    steps.append(AgentStep(
                        step_idx=len(steps),
                        thought=f"调用工具 {tool_name}",
                        tool_name=tool_name,
                        tool_args=tool_args,
                    ))
                    
                    # 执行工具
                    tool_result = await self.tool_router.execute_safe(tool_name, tool_args)
                    steps[-1].observation = str(tool_result.get("result", tool_result.get("error", "")))
                    
                    if not tool_result.get("success"):
                        steps[-1].error = tool_result.get("error")
                
                # 如果有工具调用，需要再次调用 LLM 生成最终答案
                # 暂时简化处理：将工具结果追加到 answer
                tool_results_text = "\n".join([
                    f"[{s.tool_name}]: {s.observation}" 
                    for s in steps if s.tool_name
                ])
                if tool_results_text:
                    answer = f"{answer}\n\n工具调用结果：\n{tool_results_text}"
            
            steps.append(AgentStep(
                step_idx=2,
                thought="调用 LLM 生成回答",
                observation=answer[:200] + "..." if len(answer) > 200 else answer,
            ))
            
            logger.info(f"Agent completed, answer length: {len(answer)}")
            
            return AgentResult(
                answer=answer,
                citations=citations,
                steps=steps,
            )
            
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            steps.append(AgentStep(
                step_idx=len(steps),
                thought="执行出错",
                error=str(e),
            ))
            return AgentResult(
                answer=f"抱歉，处理您的请求时出现了问题：{str(e)}",
                citations=[],
                steps=steps,
            )
    
    def _build_messages(
        self,
        system_prompt: str,
        strategy_suffix: str,
        context_messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """构建发送给 LLM 的 messages"""
        messages = []
        
        # System prompt
        full_system = f"{system_prompt}\n\n{strategy_suffix}".strip()
        messages.append({"role": "system", "content": full_system})
        
        # Context messages（已包含检索结果和用户消息）
        for msg in context_messages:
            # 避免重复的 system message
            if msg.get("role") == "system" and messages:
                # 合并到已有的 system message
                messages[0]["content"] += f"\n\n{msg['content']}"
            else:
                messages.append(msg)
        
        return messages
    
    async def _call_llm_with_tools(
        self, 
        messages: List[Dict[str, str]], 
        tool_schemas: List[Dict[str, Any]]
    ) -> tuple:
        """
        调用 LLM 生成回答（支持工具调用）
        
        Returns:
            (answer, tool_calls): answer 是文本回答，tool_calls 是工具调用列表
        """
        try:
            from services.ai.llm import LLMManager
            
            llm = LLMManager()
            
            # 转换 messages 格式
            formatted_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
            ]
            
            # 如果有工具，使用 function calling
            if tool_schemas:
                # 尝试使用工具调用（目前 LLMManager 可能不支持，降级处理）
                try:
                    response = llm.chat(
                        formatted_messages,
                        tools=tool_schemas,
                    )
                    
                    # 解析响应
                    if isinstance(response, dict):
                        # 如果返回的是结构化响应
                        answer = response.get("content", "")
                        tool_calls = response.get("tool_calls", [])
                        return answer, tool_calls
                    else:
                        # 普通文本响应
                        return response, []
                        
                except TypeError:
                    # LLMManager.chat 不支持 tools 参数，降级
                    logger.warning("LLM does not support tools, falling back to plain chat")
                    response = llm.chat(formatted_messages)
                    return response, []
            else:
                response = llm.chat(formatted_messages)
                return response, []
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # 降级返回
            return f"抱歉，AI 服务暂时不可用。您的问题是：{messages[-1].get('content', '')}", []


# 便捷函数
async def run_agent_task(db: Session, task: AgentTask) -> AgentResult:
    """
    便捷函数：执行 Agent 任务
    
    用法：
        result = await run_agent_task(db, AgentTask(...))
    """
    core = AliceAgentCore(db)
    return await core.run_task(task)
