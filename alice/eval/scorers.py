"""
Eval 评分器

提供不同的评分策略
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from alice.agent.types import AgentResult
from .models import EvalCase, EvalResult

logger = logging.getLogger(__name__)


class BaseScorer(ABC):
    """评分器基类"""
    
    @abstractmethod
    async def score(self, case: EvalCase, agent_result: AgentResult) -> EvalResult:
        """
        对 Agent 结果进行评分
        
        Args:
            case: 评估用例
            agent_result: Agent 执行结果
            
        Returns:
            EvalResult
        """
        pass


class SimpleScorer(BaseScorer):
    """
    简单规则评分器
    
    基于关键词匹配和工具调用检查进行评分
    """
    
    async def score(self, case: EvalCase, agent_result: AgentResult) -> EvalResult:
        answer = agent_result.answer or ""
        tools_called = [s.tool_name for s in agent_result.steps if s.tool_name]
        
        # 计算关键词匹配
        keywords_matched = []
        keyword_score = 0.0
        
        if case.expected_keywords:
            for kw in case.expected_keywords:
                if kw.lower() in answer.lower():
                    keywords_matched.append(kw)
            keyword_score = len(keywords_matched) / len(case.expected_keywords)
        else:
            keyword_score = 1.0 if answer else 0.0
        
        # 计算工具调用匹配
        tool_score = 0.0
        if case.expected_tool_calls:
            matched_tools = set(tools_called) & set(case.expected_tool_calls)
            tool_score = len(matched_tools) / len(case.expected_tool_calls)
        else:
            tool_score = 1.0  # 没有预期工具要求
        
        # 简单字符串相似度（如果有预期答案）
        answer_score = 0.0
        if case.expected_answer:
            answer_score = self._simple_similarity(answer, case.expected_answer)
        else:
            answer_score = 0.5 if answer else 0.0
        
        # 综合评分
        if case.expected_answer:
            final_score = answer_score * 0.5 + keyword_score * 0.3 + tool_score * 0.2
        else:
            final_score = keyword_score * 0.6 + tool_score * 0.4
        
        # 判断成功
        success = final_score >= 0.3 and len(answer) > 0
        
        reasoning = f"关键词匹配: {len(keywords_matched)}/{len(case.expected_keywords) or 'N/A'}, "
        reasoning += f"工具调用: {tools_called}, "
        reasoning += f"答案长度: {len(answer)}"
        
        return EvalResult(
            case_id=case.id,
            success=success,
            score=round(final_score, 3),
            answer=answer,
            reasoning=reasoning,
            tools_called=tools_called,
            keywords_matched=keywords_matched,
            raw_agent_result=agent_result,
        )
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算"""
        if not text1 or not text2:
            return 0.0
        
        # 分词
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard 相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class LLMScorer(BaseScorer):
    """
    LLM 评分器
    
    使用 LLM 对 Agent 回答进行评估
    """
    
    SCORING_PROMPT = """你是一个评估助手。请评估 AI 的回答质量。

问题：{question}

预期答案（参考）：{expected_answer}

AI 的实际回答：{actual_answer}

请根据以下标准打分（0-10分）：
1. 准确性：回答是否准确、正确
2. 完整性：是否回答了问题的所有方面
3. 清晰度：回答是否清晰、易懂

请输出格式：
分数：X/10
理由：[简短说明]
"""
    
    def __init__(self, llm_manager=None):
        """
        Args:
            llm_manager: LLM 管理器，用于调用 LLM 评分
        """
        self._llm = llm_manager
    
    async def score(self, case: EvalCase, agent_result: AgentResult) -> EvalResult:
        answer = agent_result.answer or ""
        tools_called = [s.tool_name for s in agent_result.steps if s.tool_name]
        
        # 如果没有 LLM，退化为简单评分
        if self._llm is None:
            simple_scorer = SimpleScorer()
            return await simple_scorer.score(case, agent_result)
        
        try:
            # 构造评分 prompt
            prompt = self.SCORING_PROMPT.format(
                question=case.query,
                expected_answer=case.expected_answer or "（无参考答案）",
                actual_answer=answer or "（无回答）",
            )
            
            # 调用 LLM
            response = await self._llm.chat([
                {"role": "user", "content": prompt}
            ])
            
            # 解析分数
            score, reasoning = self._parse_score(response)
            success = score >= 5.0 and len(answer) > 0
            
            return EvalResult(
                case_id=case.id,
                success=success,
                score=score / 10.0,  # 归一化到 0-1
                answer=answer,
                reasoning=reasoning,
                tools_called=tools_called,
                raw_agent_result=agent_result,
            )
            
        except Exception as e:
            logger.error(f"LLM scoring failed: {e}")
            # 失败时退化为简单评分
            simple_scorer = SimpleScorer()
            return await simple_scorer.score(case, agent_result)
    
    def _parse_score(self, response: str) -> Tuple[float, str]:
        """从 LLM 响应中解析分数"""
        # 匹配 "分数：X/10" 或 "X/10" 格式
        match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', response)
        if match:
            score = float(match.group(1))
        else:
            # 尝试匹配单独的数字
            match = re.search(r'分数[：:]\s*(\d+(?:\.\d+)?)', response)
            if match:
                score = float(match.group(1))
            else:
                score = 5.0  # 默认中等分数
        
        # 提取理由
        reasoning_match = re.search(r'理由[：:]\s*(.+)', response, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()[:200]
        else:
            reasoning = response[:200]
        
        return min(max(score, 0), 10), reasoning
