"""
问答路由
P3-03: 问答API
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.db import Tenant
from services.ai import RAGService, Summarizer

from ..deps import get_db, get_current_tenant
from ..schemas import QARequest, QAResponse, QASource, SearchRequest, SearchResult

router = APIRouter()

# 服务实例（延迟初始化）
_rag_service = None
_summarizer = None


def get_rag_service() -> RAGService:
    """获取RAG服务"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_summarizer() -> Summarizer:
    """获取摘要服务"""
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    基于知识库问答
    
    使用RAG从视频内容中检索相关信息并生成回答
    """
    rag = get_rag_service()
    
    # 检查服务可用性
    if not rag.is_available():
        # 降级到简单模式
        from services.ai.rag.service import FallbackRAGService
        rag = FallbackRAGService(db)
    
    try:
        result = rag.ask(
            tenant_id=tenant.id,
            question=request.question,
            video_ids=request.video_ids,
        )
        
        sources = []
        for s in result.get("sources", []):
            if isinstance(s, dict):
                sources.append(QASource(
                    video_id=s.get("video_id", 0),
                    title=s.get("title", ""),
                    relevance=s.get("score", 0.5),
                ))
        
        return QAResponse(
            answer=result["answer"],
            sources=sources,
            conversation_id=result.get("conversation_id"),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答服务异常: {e}",
        )


@router.post("/search", response_model=List[SearchResult])
async def search_videos(
    request: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    语义搜索视频内容
    
    在视频转写文本中进行语义搜索
    """
    rag = get_rag_service()
    
    # 检查服务可用性
    if not rag.is_available():
        from services.ai.rag.service import FallbackRAGService
        rag = FallbackRAGService(db)
    
    try:
        results = rag.search(
            tenant_id=tenant.id,
            query=request.query,
            top_k=request.top_k,
        )
        
        return [
            SearchResult(
                video_id=r.video_id or 0,
                title=r.video_title or "",
                content=r.content[:500],
                score=r.score,
            )
            for r in results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索服务异常: {e}",
        )


@router.post("/summarize")
async def summarize_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    生成视频摘要
    
    对指定视频重新生成AI摘要
    """
    from packages.db import Video
    import json
    
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在",
        )
    
    if not video.transcript_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="视频尚未转写",
        )
    
    from pathlib import Path
    transcript_path = Path(video.transcript_path)
    
    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转写文件不存在",
        )
    
    transcript = transcript_path.read_text(encoding="utf-8")
    
    summarizer = get_summarizer()
    
    try:
        analysis = summarizer.analyze(
            transcript=transcript,
            title=video.title,
            author=video.author,
            duration=video.duration or 0,
        )
        
        # 更新数据库
        video.summary = analysis.summary
        video.key_points = json.dumps(analysis.key_points, ensure_ascii=False)
        video.concepts = json.dumps(analysis.concepts, ensure_ascii=False)
        db.commit()
        
        return {
            "video_id": video_id,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "concepts": analysis.concepts,
            "tags": analysis.tags,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"摘要生成失败: {e}",
        )
