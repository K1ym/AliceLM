"""
Alice RAG - 检索增强生成模块

职责:
- 视频内容向量化存储
- 语义搜索
- 为 Agent 提供知识检索能力
"""

from .service import RAGService, FallbackRAGService, SearchResult, get_rag_client
from .client import RAGFlowClient
from .chroma_client import ChromaClient

__all__ = [
    "RAGService",
    "FallbackRAGService",
    "SearchResult",
    "RAGFlowClient",
    "ChromaClient",
    "get_rag_client",
]

