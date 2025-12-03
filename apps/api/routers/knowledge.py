"""
知识图谱路由
P4-05: 图谱API
"""

from typing import List, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.db import Tenant, User
from services.knowledge import KnowledgeGraphService, LearningService

from ..deps import get_db, get_current_tenant, get_current_user

router = APIRouter()


@router.get("/graph")
async def get_knowledge_graph(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """获取知识图谱"""
    service = KnowledgeGraphService(db)
    graph = service.build_graph(tenant.id)
    return graph.to_dict()


@router.get("/concepts/{concept}/videos")
async def get_concept_videos(
    concept: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """获取包含某概念的视频列表"""
    service = KnowledgeGraphService(db)
    videos = service.get_concept_videos(tenant.id, concept)
    return [
        {
            "id": v.id,
            "bvid": v.bvid,
            "title": v.title,
            "author": v.author,
        }
        for v in videos
    ]


@router.get("/concepts/{concept}/related")
async def get_related_concepts(
    concept: str,
    limit: int = 10,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """获取相关概念"""
    service = KnowledgeGraphService(db)
    return service.get_related_concepts(tenant.id, concept, limit)


@router.get("/learning/stats")
async def get_learning_stats(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取学习统计"""
    service = LearningService(db)
    stats = service.get_user_stats(user.id, days)
    
    return {
        "total_videos": stats.total_videos,
        "total_duration": stats.total_duration,
        "completed_videos": stats.completed_videos,
        "concepts_learned": stats.concepts_learned,
        "videos_by_day": stats.videos_by_day,
        "top_authors": stats.top_authors,
    }


@router.get("/learning/weekly-report")
async def get_weekly_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取周报"""
    service = LearningService(db)
    report = service.generate_weekly_report(user.id)
    
    return {
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "highlights": report.highlights,
        "stats": {
            "total_videos": report.stats.total_videos,
            "total_duration": report.stats.total_duration,
            "concepts_learned": report.stats.concepts_learned,
        },
        "recommendations": report.recommendations,
    }


@router.get("/learning/review-suggestions")
async def get_review_suggestions(
    limit: int = 5,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取复习建议"""
    service = LearningService(db)
    return service.get_review_suggestions(user.id, limit)
