"""
RAG服务
P2-07: 转写文本入库
P2-08: 语义搜索
P2-09: RAG问答

支持多种后端:
- ChromaDB (轻量级，开发环境推荐)
- RAGFlow (生产环境)
"""

from typing import List, Optional, Dict, Any, Union, Protocol

from sqlalchemy.orm import Session

from packages.db import Video
from packages.config import get_config
from packages.logging import get_logger

logger = get_logger(__name__)


class RAGClient(Protocol):
    """RAG 客户端协议 - 定义统一接口"""
    def is_available(self) -> bool: ...
    def get_or_create_dataset(self, tenant_id: str) -> str: ...
    def upload_document(self, dataset_id: str, video_id: int, title: str, transcript: str, metadata: Optional[Dict] = None) -> str: ...
    def search(self, dataset_id: str, query: str, top_k: int = 5) -> List: ...
    def ask(self, dataset_id: str, question: str, conversation_id: Optional[str] = None) -> Dict[str, Any]: ...


def get_rag_client(user_id: int = None) -> RAGClient:
    """
    根据配置获取 RAG 客户端
    
    Args:
        user_id: 用户ID (用于读取用户配置的 embedding 端点)
    
    配置项: rag.provider = "chroma" | "ragflow"
    """
    config = get_config()
    provider = getattr(config.rag, 'provider', 'chroma')
    
    if provider == "ragflow":
        from .client import RAGFlowClient
        logger.info("rag_provider", provider="ragflow")
        return RAGFlowClient()
    else:
        from .chroma_client import ChromaClient
        logger.info("rag_provider", provider="chroma", user_id=user_id)
        return ChromaClient(user_id=user_id)


# 为了兼容性，从 chroma_client 导入 SearchResult
try:
    from .chroma_client import SearchResult
except ImportError:
    from .client import SearchResult


class RAGService:
    """RAG服务 - 自动选择后端"""

    def __init__(self, client: Optional[RAGClient] = None):
        """
        初始化RAG服务
        
        Args:
            client: RAG客户端 (可选，默认根据配置自动选择)
        """
        self.client = client or get_rag_client()
        self._dataset_cache: Dict[str, str] = {}

    def _get_dataset_id(self, tenant_id: str) -> str:
        """获取租户的Dataset ID"""
        cache_key = str(tenant_id)
        
        if cache_key not in self._dataset_cache:
            self._dataset_cache[cache_key] = self.client.get_or_create_dataset(cache_key)
        
        return self._dataset_cache[cache_key]

    def index_video(
        self,
        tenant_id: int,
        video: Video,
        transcript: str,
    ) -> str:
        """
        索引视频内容
        
        Args:
            tenant_id: 租户ID
            video: 视频对象
            transcript: 转写文本
            
        Returns:
            文档ID
        """
        dataset_id = self._get_dataset_id(str(tenant_id))
        
        doc_id = self.client.upload_document(
            dataset_id=dataset_id,
            video_id=video.id,
            title=video.title,
            transcript=transcript,
            metadata={
                "source_type": video.source_type,
                "source_id": video.source_id,
                "author": video.author,
                "duration": video.duration,
            },
        )

        logger.info(
            "video_indexed",
            video_id=video.id,
            source_id=video.source_id,
            doc_id=doc_id,
        )
        
        return doc_id

    def search(
        self,
        tenant_id: int,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            tenant_id: 租户ID
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        dataset_id = self._get_dataset_id(str(tenant_id))
        return self.client.search(dataset_id, query, top_k)

    def ask(
        self,
        tenant_id: int,
        question: str,
        video_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        知识库问答
        
        Args:
            tenant_id: 租户ID
            question: 问题
            video_ids: 限定的视频ID列表（可选）
            
        Returns:
            问答结果
        """
        dataset_id = self._get_dataset_id(str(tenant_id))
        
        # TODO: 如果指定了video_ids，需要过滤
        
        result = self.client.ask(dataset_id, question)
        
        return {
            "answer": result["answer"],
            "sources": result["sources"],
        }

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client.is_available()


class FallbackRAGService(RAGService):
    """
    降级RAG服务
    当RAGFlow不可用时，使用简单的全文搜索
    """

    def __init__(self, db: Session):
        """
        初始化降级服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self._client = None

    def search(
        self,
        tenant_id: int,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """降级搜索 - 使用数据库LIKE查询"""
        from packages.db import Video
        
        videos = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.title.ilike(f"%{query}%"),
            )
            .limit(top_k)
            .all()
        )
        
        return [
            SearchResult(
                chunk_id=str(v.id),
                content=v.title,
                score=0.5,  # 简单匹配分数
                metadata={"source_type": v.source_type, "source_id": v.source_id},
                video_id=v.id,
                video_title=v.title,
            )
            for v in videos
        ]

    def ask(
        self,
        tenant_id: int,
        question: str,
        video_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """降级问答 - 返回搜索结果"""
        results = self.search(tenant_id, question, top_k=3)
        
        if not results:
            return {
                "answer": "抱歉，我没有找到相关内容。",
                "sources": [],
            }
        
        # 简单拼接
        answer = f"找到 {len(results)} 个相关视频：\n"
        for r in results:
            answer += f"- {r.video_title}\n"
        
        return {
            "answer": answer,
            "sources": [{"video_id": r.video_id, "title": r.video_title} for r in results],
        }

    def is_available(self) -> bool:
        """数据库降级始终可用"""
        return True
