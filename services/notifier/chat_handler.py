"""
微信问答交互处理
P2-10: 微信问答交互
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from packages.logging import get_logger
from services.ai import RAGService, Summarizer

logger = get_logger(__name__)


@dataclass
class ChatRequest:
    """问答请求"""
    tenant_id: int
    user_id: str
    question: str
    conversation_id: Optional[str] = None


@dataclass
class ChatResponse:
    """问答响应"""
    answer: str
    sources: list
    conversation_id: Optional[str] = None


class WeChatChatHandler:
    """微信问答处理器"""

    # 命令前缀
    COMMANDS = {
        "问": "ask",
        "搜": "search",
        "帮助": "help",
    }

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        summarizer: Optional[Summarizer] = None,
    ):
        """
        初始化问答处理器
        
        Args:
            rag_service: RAG服务
            summarizer: 摘要服务
        """
        self.rag = rag_service or RAGService()
        self.summarizer = summarizer

    def handle_message(self, request: ChatRequest) -> ChatResponse:
        """
        处理微信消息
        
        Args:
            request: 问答请求
            
        Returns:
            问答响应
        """
        question = request.question.strip()
        
        # 解析命令
        command, content = self._parse_command(question)
        
        logger.info(
            "chat_request",
            tenant_id=request.tenant_id,
            command=command,
            question=content[:50],
        )

        if command == "help":
            return self._handle_help()
        elif command == "search":
            return self._handle_search(request.tenant_id, content)
        else:
            return self._handle_ask(request, content)

    def _parse_command(self, text: str) -> tuple[str, str]:
        """解析命令"""
        for prefix, cmd in self.COMMANDS.items():
            if text.startswith(prefix):
                return cmd, text[len(prefix):].strip()
        
        # 默认为问答
        return "ask", text

    def _handle_help(self) -> ChatResponse:
        """处理帮助命令"""
        help_text = """📚 AliceLM 问答助手

使用方式：
• 直接提问：发送任何问题，AI将基于视频内容回答
• 搜索视频：发送「搜 关键词」搜索相关视频
• 查看帮助：发送「帮助」

示例：
- Python装饰器是什么？
- 搜 机器学习
- 这个视频讲了什么？"""

        return ChatResponse(answer=help_text, sources=[])

    def _handle_search(self, tenant_id: int, query: str) -> ChatResponse:
        """处理搜索命令"""
        if not query:
            return ChatResponse(
                answer="请输入搜索关键词，例如：搜 Python",
                sources=[],
            )

        try:
            results = self.rag.search(tenant_id, query, top_k=5)
            
            if not results:
                return ChatResponse(
                    answer=f"未找到与「{query}」相关的视频",
                    sources=[],
                )

            # 格式化结果
            answer = f"🔍 找到 {len(results)} 个相关视频：\n\n"
            for i, r in enumerate(results, 1):
                score_emoji = "🔥" if r.score > 0.8 else "📺"
                answer += f"{score_emoji} {i}. {r.video_title}\n"

            return ChatResponse(answer=answer, sources=[])

        except Exception as e:
            logger.error("search_failed", query=query, error=str(e))
            return ChatResponse(
                answer="搜索失败，请稍后重试",
                sources=[],
            )

    def _handle_ask(self, request: ChatRequest, question: str) -> ChatResponse:
        """处理问答"""
        if not question:
            return ChatResponse(
                answer="请输入您的问题",
                sources=[],
            )

        try:
            result = self.rag.ask(
                tenant_id=request.tenant_id,
                question=question,
            )

            answer = result["answer"]
            sources = result.get("sources", [])

            # 添加来源引用
            if sources:
                answer += "\n\n📖 参考视频："
                for s in sources[:3]:
                    if isinstance(s, dict) and s.get("title"):
                        answer += f"\n• {s['title']}"

            return ChatResponse(
                answer=answer,
                sources=sources,
                conversation_id=result.get("conversation_id"),
            )

        except Exception as e:
            logger.error("ask_failed", question=question, error=str(e))
            return ChatResponse(
                answer="抱歉，处理问题时出错了，请稍后重试",
                sources=[],
            )

    def format_for_wechat(self, response: ChatResponse) -> Dict[str, Any]:
        """格式化为微信消息格式"""
        return {
            "msgtype": "text",
            "text": {
                "content": response.answer,
            }
        }
