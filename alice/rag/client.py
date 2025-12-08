"""
RAGFlow API客户端
P2-05/P2-06: RAGFlow部署与封装
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import httpx

from packages.config import get_config
from packages.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    video_id: Optional[int] = None
    video_title: Optional[str] = None


@dataclass
class RAGFlowConfig:
    """RAGFlow配置"""
    base_url: str = "http://localhost:9380"
    api_key: str = ""


class RAGFlowClient:
    """RAGFlow API客户端"""

    def __init__(self, config: Optional[RAGFlowConfig] = None):
        """
        初始化RAGFlow客户端
        
        Args:
            config: RAGFlow配置
        """
        if config is None:
            app_config = get_config()
            config = RAGFlowConfig(
                base_url=app_config.rag.base_url,
                api_key=app_config.rag.api_key,
            )
        
        self.config = config
        self.client = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=30,
        )

    def is_available(self) -> bool:
        """检查RAGFlow是否可用"""
        try:
            resp = self.client.get("/api/v1/health")
            return resp.status_code == 200
        except Exception:
            return False

    # ========== Dataset管理 ==========

    def create_dataset(self, tenant_id: str, name: str = "videos") -> str:
        """
        为租户创建知识库
        
        Args:
            tenant_id: 租户ID
            name: 知识库名称
            
        Returns:
            dataset_id
        """
        dataset_name = f"tenant_{tenant_id}_{name}"
        
        resp = self.client.post("/api/v1/dataset", json={
            "name": dataset_name,
            "description": f"AliceLM知识库 - 租户{tenant_id}",
            "embedding_model": "BAAI/bge-large-zh-v1.5",
            "chunk_method": "naive",
            "parser_config": {
                "chunk_token_count": 512,
                "layout_recognize": False,
            }
        })
        
        if resp.status_code == 200:
            data = resp.json()
            logger.info("dataset_created", tenant_id=tenant_id, dataset_id=data["data"]["id"])
            return data["data"]["id"]
        else:
            logger.error("dataset_create_failed", status=resp.status_code, body=resp.text)
            raise Exception(f"创建Dataset失败: {resp.text}")

    def get_or_create_dataset(self, tenant_id: str) -> str:
        """获取或创建租户知识库"""
        dataset_name = f"tenant_{tenant_id}_videos"
        
        # 查询是否存在
        resp = self.client.get("/api/v1/dataset", params={"name": dataset_name})
        
        if resp.status_code == 200:
            datasets = resp.json().get("data", [])
            if datasets:
                return datasets[0]["id"]
        
        # 不存在则创建
        return self.create_dataset(tenant_id)

    # ========== 文档管理 ==========

    def upload_document(
        self,
        dataset_id: str,
        video_id: int,
        title: str,
        transcript: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        上传转写文档
        
        Args:
            dataset_id: 知识库ID
            video_id: 视频ID
            title: 视频标题
            transcript: 转写文本
            metadata: 元数据
            
        Returns:
            document_id
        """
        doc_metadata = {
            "video_id": video_id,
            "title": title,
            **(metadata or {}),
        }
        
        # RAGFlow支持直接上传文本
        resp = self.client.post(
            f"/api/v1/dataset/{dataset_id}/document",
            json={
                "name": f"video_{video_id}.txt",
                "content": transcript,
                "metadata": doc_metadata,
            }
        )
        
        if resp.status_code == 200:
            doc_id = resp.json()["data"]["id"]
            logger.info("document_uploaded", video_id=video_id, doc_id=doc_id)
            return doc_id
        else:
            logger.error("document_upload_failed", video_id=video_id, error=resp.text)
            raise Exception(f"上传文档失败: {resp.text}")

    # ========== 搜索 ==========

    def search(
        self,
        dataset_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            dataset_id: 知识库ID
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            搜索结果列表
        """
        resp = self.client.post(
            f"/api/v1/dataset/{dataset_id}/retrieval",
            json={
                "query": query,
                "top_k": top_k,
            }
        )
        
        if resp.status_code != 200:
            logger.error("search_failed", error=resp.text)
            return []
        
        results = []
        for chunk in resp.json().get("data", []):
            results.append(SearchResult(
                chunk_id=chunk.get("id", ""),
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {}),
                video_id=chunk.get("metadata", {}).get("video_id"),
                video_title=chunk.get("metadata", {}).get("title"),
            ))
        
        logger.info("search_complete", query=query[:50], results=len(results))
        return results

    # ========== 问答 ==========

    def ask(
        self,
        dataset_id: str,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        RAG问答
        
        Args:
            dataset_id: 知识库ID
            question: 问题
            conversation_id: 会话ID（可选）
            
        Returns:
            问答结果
        """
        payload = {
            "question": question,
            "dataset_ids": [dataset_id],
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        resp = self.client.post("/api/v1/chat", json=payload)
        
        if resp.status_code != 200:
            logger.error("ask_failed", error=resp.text)
            raise Exception(f"问答失败: {resp.text}")
        
        data = resp.json()["data"]
        
        logger.info(
            "ask_complete",
            question=question[:50],
            answer_length=len(data.get("answer", "")),
        )
        
        return {
            "answer": data.get("answer", ""),
            "sources": data.get("sources", []),
            "conversation_id": data.get("conversation_id"),
        }

    def close(self):
        """关闭客户端"""
        self.client.close()
