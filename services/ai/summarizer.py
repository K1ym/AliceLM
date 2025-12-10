"""
摘要生成服务
P2-03: 摘要生成
P2-04: 核心观点提取
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

from packages.logging import get_logger
from alice.errors import AliceError, LLMError, LLMConnectionError, NetworkError

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
    except Exception as e:
        logger.warning("summary_quick_prompt_fallback", error=str(e))
    
    return "你是一个专业的内容摘要助手，善于提炼核心信息。"


class Summarizer:
    """摘要生成器"""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        初始化摘要生成器
        
        Args:
            llm_manager: LLM管理器实例（如果不提供，从 ControlPlane 获取）
        """
        if llm_manager is not None:
            self.llm = llm_manager
        else:
            # 从 ControlPlane 获取带缓存的 LLM
            try:
                from alice.control_plane import get_control_plane
                cp = get_control_plane()
                self.llm = cp.create_llm_for_task_sync("summary")
            except (LLMError, LLMConnectionError, NetworkError) as e:
                logger.error("summarizer_llm_init_failed", error=str(e), exc_info=True)
                raise
            except Exception as e:
                # 回退到默认
                logger.exception("summarizer_llm_init_unexpected")
                self.llm = LLMManager()

    def analyze(
        self,
        transcript: str,
        title: str = "",
        author: str = "",
        duration: int = 0,
    ) -> VideoAnalysis:
        """
        同步分析视频内容
        """
        max_chars = 15000
        if len(transcript) > max_chars:
            half = max_chars // 2
            transcript = transcript[:half] + "\n...[中间内容省略]...\n" + transcript[-half:]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=title or "未知",
            author=author or "未知",
            duration=duration // 60 if duration else 0,
            transcript=transcript,
        )
        
        system_prompt = _get_summary_prompt()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        logger.info("summarizing", title=title, transcript_length=len(transcript))

        try:
            response = self.llm.chat(messages, temperature=0.3)
            result = self._parse_response(response.content)
            logger.info("summarize_complete", title=title, summary_length=len(result.summary))
            return result
        except (LLMError, LLMConnectionError, NetworkError) as e:
            logger.error("summarize_failed", title=title, error=str(e), exc_info=True)
            raise
        except Exception as e:
            logger.exception("summarize_failed_unexpected", title=title)
            raise LLMError(f"摘要生成失败: {e}") from e

    async def analyze_async(
        self,
        transcript: str,
        title: str = "",
        author: str = "",
        duration: int = 0,
    ) -> VideoAnalysis:
        """
        异步分析视频内容
        """
        max_chars = 15000
        if len(transcript) > max_chars:
            half = max_chars // 2
            transcript = transcript[:half] + "\n...[中间内容省略]...\n" + transcript[-half:]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=title or "未知",
            author=author or "未知",
            duration=duration // 60 if duration else 0,
            transcript=transcript,
        )
        
        system_prompt = _get_summary_prompt()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        logger.info("summarizing_async", title=title, transcript_length=len(transcript))

        try:
            response = await self.llm.chat_async(messages, temperature=0.3)
            result = self._parse_response(response.content)
            logger.info("summarize_async_complete", title=title, summary_length=len(result.summary))
            return result
        except (LLMError, LLMConnectionError, NetworkError) as e:
            logger.error("summarize_async_failed", title=title, error=str(e), exc_info=True)
            raise
        except Exception as e:
            logger.exception("summarize_async_failed_unexpected", title=title)
            raise LLMError(f"摘要生成失败: {e}") from e

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
