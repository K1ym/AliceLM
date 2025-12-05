"""
ContextAssembler - 上下文组装器

职责：
- 基于 AgentTask 组装 LLM/Agent 所需的上下文
- 整合：最近对话 + RAG 检索 + 图谱 + Timeline
- 输出：messages + citations
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session


@dataclass
class ContextCitation:
    """引用来源"""
    type: str           # video / concept / timeline / web
    id: str
    title: str
    snippet: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssembledContext:
    """组装后的上下文"""
    # 发送给 LLM 的 messages
    messages: List[Dict[str, str]]
    
    # 引用列表（用于前端展示）
    citations: List[ContextCitation] = field(default_factory=list)
    
    # 原始检索结果（用于调试）
    raw_retrieval: Optional[Dict[str, Any]] = None


class ContextAssembler:
    """
    上下文组装器
    
    将各种来源的信息整合为 Agent 可用的上下文。
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def assemble(
        self,
        tenant_id: int,
        query: str,
        user_id: Optional[int] = None,
        video_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        scene: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> AssembledContext:
        """
        组装上下文
        
        Args:
            tenant_id: 租户 ID
            query: 用户查询
            user_id: 用户 ID
            video_id: 关联视频 ID
            conversation_id: 关联对话 ID
            scene: 当前场景
            extra_context: 额外上下文（前端传入）
            
        Returns:
            AssembledContext 包含 messages 和 citations
        """
        messages: List[Dict[str, str]] = []
        citations: List[ContextCitation] = []
        raw_retrieval: Dict[str, Any] = {}
        
        # 1. 获取最近对话历史
        if conversation_id:
            conversation_messages = await self._get_conversation_history(
                conversation_id, limit=10
            )
            messages.extend(conversation_messages)
        
        # 2. RAG 检索相关内容
        if query:
            rag_results = await self._retrieve_from_rag(
                tenant_id, query, video_id
            )
            if rag_results:
                raw_retrieval["rag"] = rag_results
                # 将检索结果加入上下文
                context_text = self._format_rag_results(rag_results)
                if context_text:
                    messages.insert(0, {
                        "role": "system",
                        "content": f"以下是与用户问题相关的视频内容：\n\n{context_text}"
                    })
                # 提取引用
                for r in rag_results:
                    citations.append(ContextCitation(
                        type="video",
                        id=str(r.get("video_id", "")),
                        title=r.get("title", ""),
                        snippet=r.get("content", "")[:200],
                    ))
        
        # 3. 查询图谱相关概念
        if scene in ["graph", "research"]:
            graph_results = await self._retrieve_from_graph(tenant_id, query)
            if graph_results:
                raw_retrieval["graph"] = graph_results
                for g in graph_results:
                    citations.append(ContextCitation(
                        type="concept",
                        id=str(g.get("id", "")),
                        title=g.get("name", ""),
                        snippet=g.get("description", "")[:200],
                    ))
        
        # 4. 查询时间线
        if scene in ["timeline", "research"]:
            timeline_results = await self._retrieve_from_timeline(
                tenant_id, user_id, query
            )
            if timeline_results:
                raw_retrieval["timeline"] = timeline_results
        
        # 5. 添加用户消息
        messages.append({
            "role": "user",
            "content": query
        })
        
        return AssembledContext(
            messages=messages,
            citations=citations,
            raw_retrieval=raw_retrieval if raw_retrieval else None,
        )
    
    async def _get_conversation_history(
        self,
        conversation_id: int,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """获取对话历史"""
        from packages.db.models import Message
        from sqlalchemy import select, desc
        
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = self.db.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
    
    async def _retrieve_from_rag(
        self,
        tenant_id: int,
        query: str,
        video_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """从 RAG 检索相关内容"""
        # TODO: 集成 RAGFlow / Chroma
        # 当前返回空结果
        return []
    
    async def _retrieve_from_graph(
        self,
        tenant_id: int,
        query: str,
    ) -> List[Dict[str, Any]]:
        """从知识图谱检索相关概念"""
        # TODO: 集成图谱查询
        return []
    
    async def _retrieve_from_timeline(
        self,
        tenant_id: int,
        user_id: Optional[int],
        query: str,
    ) -> List[Dict[str, Any]]:
        """从时间线检索相关事件"""
        # TODO: 集成 TimelineService
        return []
    
    def _format_rag_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化 RAG 检索结果"""
        if not results:
            return ""
        
        formatted = []
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "未知视频")
            content = r.get("content", "")
            formatted.append(f"[{i}] 来自《{title}》：\n{content}\n")
        
        return "\n".join(formatted)


async def assemble_context(
    db: Session,
    tenant_id: int,
    query: str,
    **kwargs
) -> AssembledContext:
    """
    便捷函数：组装上下文
    
    用法：
        ctx = await assemble_context(
            db, tenant_id=1,
            query="这个视频讲了什么？",
            video_id=123,
        )
    """
    assembler = ContextAssembler(db)
    return await assembler.assemble(tenant_id, query, **kwargs)
