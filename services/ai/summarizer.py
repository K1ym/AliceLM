"""
摘要生成服务
P2-03: 摘要生成
P2-04: 核心观点提取
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

from packages.logging import get_logger

from .llm import LLMManager, Message

logger = get_logger(__name__)


@dataclass
class VideoAnalysis:
    """视频分析结果"""
    summary: str                        # 摘要（50-200字）
    key_points: List[str]              # 核心观点（3-5条）
    concepts: List[str] = field(default_factory=list)  # 关键概念
    tags: List[str] = field(default_factory=list)      # 推荐标签
    language: str = "zh"                # 语言


# 硬编码 prompt 保留为回退（当 ControlPlane 不可用时）
_FALLBACK_SYSTEM_PROMPT = """你是一个专业的视频内容分析助手。你的任务是分析视频转写文本，提取关键信息。

请严格按照以下JSON格式输出：
{
    "summary": "50-200字的摘要，概括视频主要内容",
    "key_points": ["核心观点1", "核心观点2", "核心观点3"],
    "concepts": ["关键概念1", "关键概念2"],
    "tags": ["标签1", "标签2", "标签3"]
}

只输出JSON，不要有其他内容。"""


USER_PROMPT_TEMPLATE = """请分析以下视频内容：

标题：{title}
作者：{author}
时长：{duration}分钟

转写文本：
{transcript}

请提取摘要、核心观点、关键概念和标签。"""


def _get_summary_prompt() -> str:
    """获取摘要 prompt（通过 ControlPlane）"""
    try:
        from alice.control_plane import get_control_plane
        cp = get_control_plane()
        prompt = cp.get_prompt_sync("summary")
        if prompt:
            return prompt
    except Exception as e:
        logger.warning(f"Failed to get prompt from ControlPlane: {e}")
    
    return _FALLBACK_SYSTEM_PROMPT


def _get_summary_quick_prompt() -> str:
    """获取快速摘要 prompt"""
    try:
        from alice.control_plane import get_control_plane
        cp = get_control_plane()
        prompt = cp.get_prompt_sync("summary_quick")
        if prompt:
            return prompt
    except Exception:
        pass
    
    return "你是一个专业的内容摘要助手，善于提炼核心信息。"


class Summarizer:
    """摘要生成器"""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        初始化摘要生成器
        
        Args:
            llm_manager: LLM管理器实例
        """
        self.llm = llm_manager or LLMManager()

    def analyze(
        self,
        transcript: str,
        title: str = "",
        author: str = "",
        duration: int = 0,
    ) -> VideoAnalysis:
        """
        分析视频内容
        
        Args:
            transcript: 转写文本
            title: 视频标题
            author: 作者
            duration: 时长（秒）
            
        Returns:
            VideoAnalysis对象
        """
        # 限制转写文本长度（避免超出token限制）
        max_chars = 15000
        if len(transcript) > max_chars:
            # 取前后各一半
            half = max_chars // 2
            transcript = transcript[:half] + "\n...[中间内容省略]...\n" + transcript[-half:]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=title or "未知",
            author=author or "未知",
            duration=duration // 60 if duration else 0,
            transcript=transcript,
        )
        
        # 从 ControlPlane 获取 prompt
        system_prompt = _get_summary_prompt()

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        logger.info(
            "summarizing",
            title=title,
            transcript_length=len(transcript),
        )

        try:
            response = self.llm.chat(messages, temperature=0.3)
            
            # 解析JSON响应
            result = self._parse_response(response.content)
            
            logger.info(
                "summarize_complete",
                title=title,
                summary_length=len(result.summary),
                key_points_count=len(result.key_points),
            )

            return result

        except Exception as e:
            logger.error("summarize_failed", title=title, error=str(e))
            raise

    def _parse_response(self, content: str) -> VideoAnalysis:
        """解析LLM响应"""
        # 尝试提取JSON
        content = content.strip()
        
        # 处理可能的markdown代码块
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"无法解析LLM响应: {content[:200]}")

        return VideoAnalysis(
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
            concepts=data.get("concepts", []),
            tags=data.get("tags", []),
        )

    def generate_summary_only(self, transcript: str, max_length: int = 200) -> str:
        """仅生成摘要（快速模式）"""
        prompt = f"""请用{max_length}字以内概括以下内容的核心观点：

{transcript[:8000]}

摘要："""
        
        # 从 ControlPlane 获取 prompt
        system_prompt = _get_summary_quick_prompt()

        return self.llm.complete(
            prompt,
            system_prompt=system_prompt,
            temperature=0.3,
        )
