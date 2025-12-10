"""
问答路由
P3-03: 问答API
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.db import Tenant
from services.ai import RAGService, Summarizer

from ..deps import get_current_tenant, get_video_service, get_db
from ..services import VideoService
from ..exceptions import (
    AppException,
    NotFoundException,
    ProcessingException,
    ExternalServiceException,
)
from ..schemas import QARequest, QAResponse, QASource, SearchRequest, SearchResult
from alice.errors import LLMError, NetworkError

router = APIRouter()
logger = logging.getLogger(__name__)

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
        from alice.rag import FallbackRAGService
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
        
    except (LLMError, NetworkError) as e:
        logger.error("qa_ask_llm_error", exc_info=True)
        raise ExternalServiceException("RAG", str(e))
    except AppException:
        raise
    except Exception as e:
        logger.exception("qa_ask_unexpected")
        raise ProcessingException(f"问答服务异常: {e}")


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
        from alice.rag import FallbackRAGService
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
        
    except (LLMError, NetworkError) as e:
        logger.error("qa_search_llm_error", exc_info=True)
        raise ExternalServiceException("RAG", str(e))
    except AppException:
        raise
    except Exception as e:
        logger.exception("qa_search_unexpected")
        raise ProcessingException(f"搜索服务异常: {e}")


@router.post("/summarize")
async def summarize_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """生成视频摘要"""
    import json
    from pathlib import Path
    
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    if not video.transcript_path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "视频尚未转写")
    
    transcript_path = Path(video.transcript_path)
    if not transcript_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "转写文件不存在")
    
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
        service.update_analysis(
            video_id, tenant.id,
            summary=analysis.summary,
            key_points=json.dumps(analysis.key_points, ensure_ascii=False),
            concepts=json.dumps(analysis.concepts, ensure_ascii=False),
        )
        
        return {
            "video_id": video_id,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "concepts": analysis.concepts,
            "tags": analysis.tags,
        }
        
    except (LLMError, NetworkError) as e:
        logger.error("qa_summarize_llm_error", exc_info=True)
        raise ExternalServiceException("Summarizer", str(e))
    except AppException:
        raise
    except Exception as e:
        logger.exception("qa_summarize_unexpected")
        raise ProcessingException(f"摘要生成失败: {e}")
