"""
ToolExecutor - ReAct 循环执行器

职责：
- 根据 AgentPlan 驱动 ReAct 循环
- 流程：LLM 思考 → 选择工具 → 执行 → 注入 observation → 继续
- 管理执行步骤，收集 AgentStep 用于回放

"""

import json
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from .types import (
    AgentTask, AgentPlan, AgentStep, AgentResult, AgentCitation,
    AgentRunState, ToolResult, ToolTrace,
)

logger = logging.getLogger(__name__)


# ReAct 循环的系统提示模板
REACT_SYSTEM_PROMPT = """你是一个智能助手，可以通过调用工具来完成任务。

## 执行计划
{plan}

## 可用工具
{tools}

## 回复格式
每次回复必须是以下格式之一：

1. 调用工具时：
```json
{{"thought": "我的思考过程...", "action": "工具名", "action_input": {{"参数名": "参数值"}}}}
```

2. 给出最终答案时：
```json
{{"thought": "我的思考过程...", "final_answer": "最终回答内容"}}
```

注意：只输出 JSON，不要有其他内容。"""

# 下一步提示模板
NEXT_STEP_PROMPT = """用户问题：{query}

{observations}

基于当前状态，决定下一步行动：
1. 如果需要更多信息，调用合适的工具
2. 如果已有足够信息，给出最终答案
3. 如果任务已完成，使用 final_answer"""


class ToolExecutor:
    """
    ReAct 循环执行器
    
    负责执行 AgentPlan，驱动 thought → tool_call → observation 循环。
    
    ReAct 循环：
    1. think() - LLM 思考，决定下一步行动
    2. act() - 执行工具调用
    3. 收集 observation，追加到上下文
    4. 重复直到给出最终答案或达到最大步数
    
    """
    
    # 特殊工具名（终止执行）
    TERMINAL_TOOL_NAMES = ["terminate", "finish", "final_answer"]
    
    def __init__(self, tool_router=None, max_steps: int = 10, max_observe: int = 2000):
        """
        Args:
            tool_router: ToolRouter 实例，用于分发工具调用
            max_steps: 最大执行步数，防止无限循环
            max_observe: 观察结果最大字符数
        """
        self.tool_router = tool_router
        self.max_steps = max_steps
        self.max_observe = max_observe
        self.state = AgentRunState.IDLE
        
        # 工具调用追踪
        self.tool_traces: List[ToolTrace] = []
    
    async def execute(
        self,
        task: AgentTask,
        plan: AgentPlan,
        context: Optional[dict] = None,
        system_prompt: str = "",
        available_tools: Optional[List[str]] = None,
    ) -> AgentResult:
        """
        执行 ReAct 循环
        
        流程：
        1. 初始化状态为 RUNNING
        2. 循环执行 step() = think() + act()
        3. 检查是否完成或达到最大步数
        4. 返回结果（包含 tool_traces）
        
        Args:
            task: AgentTask 输入
            plan: TaskPlanner 生成的执行计划
            context: 上下文信息（messages 等）
            system_prompt: 基础 system prompt
            available_tools: 可用工具列表
            
        Returns:
            AgentResult 包含最终答案、执行步骤和工具追踪
        """
        steps: List[AgentStep] = []
        citations: List[AgentCitation] = []
        observations: List[str] = []
        self.tool_traces = []  # 重置工具追踪
        
        # 状态转换
        self.state = AgentRunState.RUNNING
        
        try:
            # 如果是简单计划，直接调用 LLM 回答
            if len(plan.steps) == 1 and plan.steps[0] == "直接回答用户问题":
                logger.info("Simple plan, using direct LLM response")
                answer = await self._direct_llm_response(
                    task.query, 
                    system_prompt, 
                    context
                )
                self.state = AgentRunState.FINISHED
                return AgentResult(
                    answer=answer,
                    citations=citations,
                    steps=[AgentStep(step_idx=0, thought="直接回答用户问题")],
                    tool_traces=self.tool_traces,
                )
            
            # 获取工具 schema
            tool_schemas = []
            if self.tool_router and available_tools:
                tool_schemas = self.tool_router.list_tool_schemas(available_tools)
            
            # ReAct 主循环
            for step_idx in range(self.max_steps):
                # 检查状态
                if self.state == AgentRunState.FINISHED:
                    break
                
                logger.info(f"🔄 Executing step {step_idx + 1}/{self.max_steps}")
                
                # Step = Think + Act
                step, should_continue = await self._step(
                    step_idx=step_idx,
                    task=task,
                    plan=plan,
                    tool_schemas=tool_schemas,
                    observations=observations,
                    system_prompt=system_prompt,
                    context=context,
                )
                
                steps.append(step)
                
                # 检查是否有最终答案
                if step.observation and "final_answer:" in step.observation.lower():
                    # 提取最终答案
                    answer = step.observation.split("final_answer:", 1)[-1].strip()
                    if answer.startswith('"') and answer.endswith('"'):
                        answer = answer[1:-1]
                    self.state = AgentRunState.FINISHED
                    logger.info(f"🏁 Got final answer at step {step_idx + 1}")
                    return AgentResult(
                        answer=answer,
                        citations=citations,
                        steps=steps,
                        tool_traces=self.tool_traces,
                    )
                
                if not should_continue:
                    break
            
            # 达到最大步数，强制生成答案
            if self.state != AgentRunState.FINISHED:
                logger.warning(f"⚠️ Reached max steps ({self.max_steps}), forcing final answer")
                
                final_answer = await self._generate_final_answer(
                    task.query,
                    observations,
                    system_prompt,
                )
                
                steps.append(AgentStep(
                    step_idx=len(steps),
                    thought="达到最大执行步数，强制生成答案",
                ))
                
                self.state = AgentRunState.FINISHED
                return AgentResult(
                    answer=final_answer,
                    citations=citations,
                    steps=steps,
                    tool_traces=self.tool_traces,
                )
            
            # 正常完成
            return AgentResult(
                answer="任务执行完成",
                citations=citations,
                steps=steps,
                tool_traces=self.tool_traces,
            )
            
        except Exception as e:
            self.state = AgentRunState.ERROR
            logger.error(f"🚨 Execution error: {e}")
            return AgentResult(
                answer=f"执行出错: {str(e)}",
                citations=[],
                steps=steps,
                tool_traces=self.tool_traces,
            )
    
    async def _step(
        self,
        step_idx: int,
        task: AgentTask,
        plan: AgentPlan,
        tool_schemas: List[Dict],
        observations: List[str],
        system_prompt: str,
        context: Optional[dict],
    ) -> Tuple[AgentStep, bool]:
        """
        执行单个步骤 (think + act)
        
        Returns:
            (AgentStep, should_continue)
        """
        # Think: 调用 LLM 获取决策
        messages = self._build_messages(
            task.query,
            plan,
            tool_schemas,
            observations,
            system_prompt,
            context,
        )
        
        response = await self._call_llm(messages)
        
        # 解析响应
        parsed = self._parse_response(response)
        
        thought = parsed.get("thought", "")
        action = parsed.get("action")
        action_input = parsed.get("action_input", {})
        final_answer = parsed.get("final_answer")
        
        # 记录步骤
        step = AgentStep(
            step_idx=step_idx,
            thought=thought,
            tool_name=action,
            tool_args=action_input if action else None,
        )
        
        logger.info(f"✨ Thought: {thought[:100]}...")
        
        # 如果有最终答案
        if final_answer:
            step.observation = f"final_answer: {final_answer}"
            logger.info(f"🎯 Final answer received")
            self.state = AgentRunState.FINISHED
            return step, False
        
        # Act: 执行工具调用
        if action and self.tool_router:
            observation = await self._execute_tool(action, action_input)
            
            # 截断观察结果
            if len(observation) > self.max_observe:
                observation = observation[:self.max_observe] + "... (truncated)"
            
            step.observation = observation
            observations.append(f"[Step {step_idx + 1}] {observation}")
            
            logger.info(f"🎯 Tool '{action}' result: {observation[:100]}...")
            
            # 检查终止工具
            if self._is_terminal_tool(action):
                logger.info(f"🏁 Terminal tool '{action}' completed the task!")
                self.state = AgentRunState.FINISHED
                return step, False
            
            return step, True
        
        # 没有工具调用也没有最终答案
        step.observation = f"无法解析响应: {response[:200]}"
        step.error = "解析失败"
        observations.append(f"[Step {step_idx + 1}] 解析失败")
        
        return step, True
    
    def _is_terminal_tool(self, name: str) -> bool:
        """检查是否为终止工具"""
        return name.lower() in [n.lower() for n in self.TERMINAL_TOOL_NAMES]
    
    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        执行单个工具调用
        
        包含错误处理和追踪记录（ToolTrace）
        """
        if not name:
            return "Error: Invalid tool name"
        
        logger.info(f"🔧 Activating tool: '{name}'...")
        started_at = datetime.now()
        
        try:
            result = await self.tool_router.execute(name, args)
            finished_at = datetime.now()
            
            # 构建 ToolResult
            tool_result = ToolResult(
                success=True,
                output=result,
                summary=str(result)[:500] if result else None,
            )
            
            # 记录 ToolTrace
            trace = ToolTrace(
                tool_name=name,
                tool_args=args,
                result=tool_result,
                started_at=started_at,
                finished_at=finished_at,
            )
            self.tool_traces.append(trace)
            
            # 格式化输出
            observation = (
                f"Observed output of tool `{name}`:\n{str(result)}"
                if result
                else f"Tool `{name}` completed with no output"
            )
            return observation
            
        except Exception as e:
            finished_at = datetime.now()
            error_msg = str(e)
            
            # 构建失败的 ToolResult
            tool_result = ToolResult(
                success=False,
                error=error_msg,
            )
            
            # 记录 ToolTrace
            trace = ToolTrace(
                tool_name=name,
                tool_args=args,
                result=tool_result,
                started_at=started_at,
                finished_at=finished_at,
            )
            self.tool_traces.append(trace)
            
            logger.error(f"Tool '{name}' error: {error_msg}")
            return f"⚠️ Tool '{name}' error: {error_msg}"
    
    def _build_messages(
        self,
        query: str,
        plan: AgentPlan,
        tool_schemas: List[Dict],
        observations: List[str],
        base_system_prompt: str,
        context: Optional[dict],
    ) -> List[Dict[str, str]]:
        """构建 ReAct 循环的消息"""
        # 格式化计划
        plan_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(plan.steps)])
        
        # 格式化工具
        tools_text = self._format_tools_for_prompt(tool_schemas)
        
        # 系统提示
        system_content = base_system_prompt + "\n\n" + REACT_SYSTEM_PROMPT.format(
            plan=plan_text,
            tools=tools_text,
        )
        
        messages = [{"role": "system", "content": system_content}]
        
        # 添加历史对话（如果有）
        if context and context.get("messages"):
            for msg in context["messages"]:
                if msg.get("role") != "system":
                    messages.append(msg)
        
        # 用户消息 + 观察结果
        obs_text = "\n".join(observations) if observations else "（尚无观察结果）"
        user_content = NEXT_STEP_PROMPT.format(
            query=query,
            observations=obs_text,
        )
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    def _format_tools_for_prompt(self, tool_schemas: List[Dict]) -> str:
        """格式化工具列表供 prompt 使用"""
        if not tool_schemas:
            return "无可用工具"
        
        lines = []
        for schema in tool_schemas:
            func = schema.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})
            
            param_str = ", ".join(params.keys()) if params else "无参数"
            lines.append(f"- {name}: {desc} (参数: {param_str})")
        
        return "\n".join(lines)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试直接解析 JSON
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group()
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue
        
        # 解析失败，尝试提取关键信息
        result = {"thought": response[:200]}
        
        # 检查是否包含最终答案的关键词
        if "final_answer" in response.lower() or "最终答案" in response:
            result["final_answer"] = response
        
        return result
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM"""
        try:
            from services.ai.llm import LLMManager
            
            llm = LLMManager()
            return llm.chat(messages)
            
        except Exception as e:
            logger.error(f"🚨 LLM call failed: {e}")
            return f'{{"thought": "LLM 调用失败", "final_answer": "抱歉，AI 服务暂时不可用。"}}'
    
    async def _direct_llm_response(
        self, 
        query: str, 
        system_prompt: str,
        context: Optional[dict],
    ) -> str:
        """直接 LLM 响应（不走 ReAct）"""
        messages = [{"role": "system", "content": system_prompt}]
        
        if context and context.get("messages"):
            for msg in context["messages"]:
                if msg.get("role") != "system":
                    messages.append(msg)
        
        messages.append({"role": "user", "content": query})
        
        return await self._call_llm(messages)
    
    async def _generate_final_answer(
        self,
        query: str,
        observations: List[str],
        system_prompt: str,
    ) -> str:
        """基于观察结果生成最终答案"""
        obs_text = "\n".join(observations) if observations else "无观察结果"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""用户问题：{query}

执行过程中的观察结果：
{obs_text}

请基于以上信息，给出最终的回答。"""},
        ]
        
        return await self._call_llm(messages)
    
    async def cleanup(self):
        """清理资源"""
        logger.info(f"🧹 Cleaning up ToolExecutor resources...")
        self.state = AgentRunState.IDLE
        self.tool_traces = []
