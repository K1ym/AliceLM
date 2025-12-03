"""
上下文压缩服务
用于压缩超长对话历史，实现超长上下文支持
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from packages.logging import get_logger
from .llm import LLMManager, Message

logger = get_logger(__name__)

# 默认阈值配置
DEFAULT_CONTEXT_THRESHOLD = 20000  # 字符数阈值，超过则触发压缩
DEFAULT_KEEP_RECENT = 6  # 保留最近N条消息不压缩


COMPRESS_SYSTEM_PROMPT = """你是一个对话历史压缩助手。你的任务是将一段对话历史压缩成简洁的摘要，保留关键信息。

要求：
1. 保留对话中的关键信息、重要结论、用户的偏好和需求
2. 使用第三人称描述（"用户询问了..."，"助手回答了..."）
3. 按时间顺序组织，突出因果关系
4. 压缩后的内容应该能让后续对话无缝衔接
5. 控制在500-1000字以内

输出格式：
直接输出压缩后的对话摘要，不需要其他格式。"""

COMPRESS_USER_PROMPT = """请压缩以下对话历史：

{conversation}

请输出压缩后的摘要："""


@dataclass
class CompressResult:
    """压缩结果"""
    compressed: str  # 压缩后的摘要
    original_count: int  # 原始消息数
    original_chars: int  # 原始字符数
    compressed_chars: int  # 压缩后字符数


class ContextCompressor:
    """上下文压缩器"""

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        context_threshold: int = DEFAULT_CONTEXT_THRESHOLD,
        keep_recent: int = DEFAULT_KEEP_RECENT,
    ):
        """
        初始化压缩器
        
        Args:
            llm_manager: LLM管理器（用于压缩）
            context_threshold: 上下文字符数阈值
            keep_recent: 保留最近N条消息不压缩
        """
        self.llm = llm_manager or LLMManager()
        self.context_threshold = context_threshold
        self.keep_recent = keep_recent

    def should_compress(self, messages: List[dict]) -> bool:
        """
        判断是否需要压缩
        
        Args:
            messages: 消息列表 [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            是否需要压缩
        """
        if len(messages) <= self.keep_recent:
            return False
        
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars > self.context_threshold

    def compress(
        self,
        messages: List[dict],
        existing_summary: Optional[str] = None,
    ) -> CompressResult:
        """
        压缩对话历史
        
        Args:
            messages: 消息列表（不包括最近keep_recent条）
            existing_summary: 已有的压缩摘要（如果有的话，会一起压缩）
        
        Returns:
            压缩结果
        """
        if not messages:
            return CompressResult(
                compressed="",
                original_count=0,
                original_chars=0,
                compressed_chars=0,
            )

        # 构建对话文本
        conversation_parts = []
        
        # 如果有已存在的摘要，先加入
        if existing_summary:
            conversation_parts.append(f"[之前的对话摘要]\n{existing_summary}\n")
        
        # 添加新消息
        for msg in messages:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            conversation_parts.append(f"{role}: {content}")
        
        conversation_text = "\n\n".join(conversation_parts)
        original_chars = len(conversation_text)

        # 调用LLM压缩
        try:
            llm_messages = [
                Message(role="system", content=COMPRESS_SYSTEM_PROMPT),
                Message(role="user", content=COMPRESS_USER_PROMPT.format(conversation=conversation_text)),
            ]
            
            response = self.llm.chat(llm_messages, temperature=0.3)
            compressed = response.content.strip()
            
            logger.info(
                "context_compressed",
                original_count=len(messages),
                original_chars=original_chars,
                compressed_chars=len(compressed),
                ratio=f"{len(compressed)/original_chars*100:.1f}%",
            )
            
            return CompressResult(
                compressed=compressed,
                original_count=len(messages),
                original_chars=original_chars,
                compressed_chars=len(compressed),
            )
            
        except Exception as e:
            logger.error("context_compress_failed", error=str(e))
            # 失败时返回简单截断
            fallback = conversation_text[:1000] + "..." if len(conversation_text) > 1000 else conversation_text
            return CompressResult(
                compressed=f"[压缩失败，原始摘要] {fallback}",
                original_count=len(messages),
                original_chars=original_chars,
                compressed_chars=len(fallback),
            )

    def build_context(
        self,
        compressed_summary: Optional[str],
        recent_messages: List[dict],
    ) -> List[Message]:
        """
        构建最终的上下文消息列表
        
        Args:
            compressed_summary: 压缩后的历史摘要
            recent_messages: 最近的消息列表
        
        Returns:
            LLM消息列表
        """
        messages = []
        
        # 添加压缩摘要作为系统上下文
        if compressed_summary:
            messages.append(Message(
                role="system",
                content=f"以下是之前对话的摘要，请基于此上下文继续对话：\n\n{compressed_summary}",
            ))
        
        # 添加最近的消息
        for msg in recent_messages:
            messages.append(Message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))
        
        return messages


def create_compressor_from_config(
    base_url: str,
    api_key: str,
    model: str,
    context_threshold: int = DEFAULT_CONTEXT_THRESHOLD,
    keep_recent: int = DEFAULT_KEEP_RECENT,
) -> ContextCompressor:
    """
    根据配置创建压缩器
    
    Args:
        base_url: API地址
        api_key: API密钥
        model: 模型名称
        context_threshold: 上下文阈值
        keep_recent: 保留最近消息数
    
    Returns:
        ContextCompressor实例
    """
    from .llm import create_llm_from_config
    
    llm = create_llm_from_config(base_url, api_key, model)
    return ContextCompressor(
        llm_manager=llm,
        context_threshold=context_threshold,
        keep_recent=keep_recent,
    )
