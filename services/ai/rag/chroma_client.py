"""
ChromaDB 客户端
轻量级本地向量存储，支持迁移到 RAGFlow
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os

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
class ChromaConfig:
    """ChromaDB配置"""
    persist_directory: str = "data/chroma"
    collection_prefix: str = "tenant"
    embedding_model: str = "text-embedding-3-small"  # OpenAI embedding


class ChromaClient:
    """ChromaDB 客户端 - 与 RAGFlowClient 接口兼容"""

    def __init__(self, config: Optional[ChromaConfig] = None):
        """
        初始化 ChromaDB 客户端
        
        Args:
            config: ChromaDB 配置
        """
        import chromadb
        from chromadb.config import Settings
        
        if config is None:
            app_config = get_config()
            persist_dir = getattr(app_config.rag, 'chroma_persist_dir', 'data/chroma')
            config = ChromaConfig(persist_directory=persist_dir)
        
        self.config = config
        
        # 确保目录存在
        os.makedirs(config.persist_directory, exist_ok=True)
        
        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=config.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # OpenAI embedding function
        self._embedding_fn = None
        
        logger.info("chromadb_initialized", persist_dir=config.persist_directory)

    def _get_embedding_function(self):
        """获取 embedding 函数"""
        if self._embedding_fn is None:
            from chromadb.utils import embedding_functions
            
            app_config = get_config()
            api_key = app_config.llm.api_key
            
            if api_key:
                # 有 API key 时使用 OpenAI embedding
                base_url = getattr(app_config.llm, 'base_url', None)
                try:
                    self._embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=api_key,
                        api_base=base_url,
                        model_name=self.config.embedding_model,
                    )
                    logger.info("embedding_function", type="openai")
                except Exception as e:
                    logger.warning("openai_embedding_failed", error=str(e))
                    self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                    logger.info("embedding_function", type="default")
            else:
                # 无 API key 时使用默认 embedding (本地)
                self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                logger.info("embedding_function", type="default")
        
        return self._embedding_fn

    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False

    # ========== Collection(Dataset)管理 ==========

    def _get_collection_name(self, tenant_id: str) -> str:
        """获取租户的 collection 名称"""
        return f"{self.config.collection_prefix}_{tenant_id}_videos"

    def create_dataset(self, tenant_id: str, name: str = "videos") -> str:
        """
        为租户创建知识库 (collection)
        
        Args:
            tenant_id: 租户ID
            name: 知识库名称
            
        Returns:
            collection_name (作为 dataset_id)
        """
        collection_name = self._get_collection_name(tenant_id)
        
        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._get_embedding_function(),
            metadata={"tenant_id": tenant_id, "description": f"AliceLM知识库 - 租户{tenant_id}"}
        )
        
        logger.info("collection_created", tenant_id=tenant_id, name=collection_name)
        return collection_name

    def get_or_create_dataset(self, tenant_id: str) -> str:
        """获取或创建租户知识库"""
        return self.create_dataset(tenant_id)

    # ========== 文档管理 ==========

    def upload_document(
        self,
        dataset_id: str,  # collection_name
        video_id: int,
        title: str,
        transcript: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        上传转写文档
        
        Args:
            dataset_id: collection 名称
            video_id: 视频ID
            title: 视频标题
            transcript: 转写文本
            metadata: 元数据
            
        Returns:
            document_id
        """
        collection = self.client.get_collection(
            name=dataset_id,
            embedding_function=self._get_embedding_function()
        )
        
        # 分块存储 (每块约 500 字)
        chunks = self._split_text(transcript, chunk_size=500)
        
        doc_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"video_{video_id}_chunk_{i}"
            doc_ids.append(chunk_id)
            
            chunk_metadata = {
                "video_id": video_id,
                "title": title,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(metadata or {}),
            }
            
            # 检查是否已存在，存在则更新
            existing = collection.get(ids=[chunk_id])
            if existing['ids']:
                collection.update(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                )
            else:
                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                )
        
        logger.info(
            "document_uploaded",
            video_id=video_id,
            chunks=len(chunks),
            collection=dataset_id,
        )
        
        return f"video_{video_id}"

    def _split_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """简单分块"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        current = ""
        
        # 按句子分割
        sentences = text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
        
        for sentence in sentences:
            if len(current) + len(sentence) <= chunk_size:
                current += sentence
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence
        
        if current:
            chunks.append(current.strip())
        
        return chunks if chunks else [text]

    def delete_document(self, dataset_id: str, video_id: int) -> bool:
        """删除视频的所有分块"""
        try:
            collection = self.client.get_collection(
                name=dataset_id,
                embedding_function=self._get_embedding_function()
            )
            
            # 查找所有属于该视频的分块
            results = collection.get(
                where={"video_id": video_id}
            )
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                logger.info("document_deleted", video_id=video_id, chunks=len(results['ids']))
            
            return True
        except Exception as e:
            logger.error("document_delete_failed", video_id=video_id, error=str(e))
            return False

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
            dataset_id: collection 名称
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            搜索结果列表
        """
        try:
            collection = self.client.get_collection(
                name=dataset_id,
                embedding_function=self._get_embedding_function()
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            
            if results['ids'] and results['ids'][0]:
                for i, chunk_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    # ChromaDB 返回距离，转换为相似度分数
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    score = 1.0 / (1.0 + distance)  # 转换为 0-1 分数
                    
                    search_results.append(SearchResult(
                        chunk_id=chunk_id,
                        content=results['documents'][0][i] if results['documents'] else "",
                        score=score,
                        metadata=metadata,
                        video_id=metadata.get("video_id"),
                        video_title=metadata.get("title"),
                    ))
            
            logger.info("search_complete", query=query[:50], results=len(search_results))
            return search_results
            
        except Exception as e:
            logger.error("search_failed", error=str(e))
            return []

    # ========== 问答 (需要 LLM) ==========

    def ask(
        self,
        dataset_id: str,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        RAG 问答 - 搜索 + LLM 生成
        
        Args:
            dataset_id: collection 名称
            question: 问题
            conversation_id: 会话ID（暂不使用）
            
        Returns:
            问答结果
        """
        # 1. 搜索相关内容
        search_results = self.search(dataset_id, question, top_k=5)
        
        if not search_results:
            return {
                "answer": "抱歉，我没有找到相关内容。",
                "sources": [],
            }
        
        # 2. 构建上下文
        context_parts = []
        sources = []
        seen_videos = set()
        
        for r in search_results:
            context_parts.append(f"【{r.video_title}】\n{r.content}")
            if r.video_id and r.video_id not in seen_videos:
                sources.append({
                    "video_id": r.video_id,
                    "title": r.video_title,
                    "score": r.score,
                })
                seen_videos.add(r.video_id)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # 3. 调用 LLM 生成答案
        try:
            from openai import OpenAI
            
            app_config = get_config()
            client = OpenAI(
                api_key=app_config.llm.api_key,
                base_url=getattr(app_config.llm, 'base_url', None),
            )
            
            response = client.chat.completions.create(
                model=app_config.llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个知识助手。根据提供的视频内容回答用户问题。如果内容不足以回答，请诚实说明。回答要简洁明了。"
                    },
                    {
                        "role": "user",
                        "content": f"参考内容：\n{context}\n\n问题：{question}"
                    }
                ],
                max_tokens=1000,
            )
            
            answer = response.choices[0].message.content
            
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            # 降级：返回搜索结果摘要
            answer = f"找到 {len(sources)} 个相关视频：\n"
            for s in sources[:3]:
                answer += f"- {s['title']}\n"
        
        logger.info("ask_complete", question=question[:50], sources=len(sources))
        
        return {
            "answer": answer,
            "sources": sources,
        }

    # ========== 数据导出 (用于迁移) ==========

    def export_all_documents(self, dataset_id: str) -> List[Dict]:
        """
        导出所有文档 (用于迁移到 RAGFlow)
        
        Returns:
            文档列表 [{"video_id": int, "title": str, "content": str, "metadata": dict}]
        """
        collection = self.client.get_collection(
            name=dataset_id,
            embedding_function=self._get_embedding_function()
        )
        
        all_data = collection.get(include=["documents", "metadatas"])
        
        # 按 video_id 合并分块
        videos = {}
        for i, chunk_id in enumerate(all_data['ids']):
            metadata = all_data['metadatas'][i]
            video_id = metadata.get('video_id')
            
            if video_id not in videos:
                videos[video_id] = {
                    "video_id": video_id,
                    "title": metadata.get('title', ''),
                    "chunks": [],
                    "metadata": {k: v for k, v in metadata.items() 
                                if k not in ['chunk_index', 'total_chunks']},
                }
            
            videos[video_id]['chunks'].append({
                'index': metadata.get('chunk_index', 0),
                'content': all_data['documents'][i],
            })
        
        # 排序并合并分块
        result = []
        for video in videos.values():
            video['chunks'].sort(key=lambda x: x['index'])
            video['content'] = ''.join(c['content'] for c in video['chunks'])
            del video['chunks']
            result.append(video)
        
        return result

    def close(self):
        """关闭客户端"""
        pass  # ChromaDB PersistentClient 不需要显式关闭
