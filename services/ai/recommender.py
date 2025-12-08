"""
相关视频推荐服务
P2-13: 相关视频推荐
"""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from packages.db import Video, Tag, VideoTag
from packages.logging import get_logger

from alice.rag import RAGService, SearchResult

logger = get_logger(__name__)


@dataclass
class Recommendation:
    """推荐结果"""
    video_id: int
    bvid: str
    title: str
    score: float
    reason: str  # 推荐理由


class Recommender:
    """相关视频推荐器"""

    def __init__(
        self,
        db: Session,
        rag_service: Optional[RAGService] = None,
    ):
        """
        初始化推荐器
        
        Args:
            db: 数据库会话
            rag_service: RAG服务（可选）
        """
        self.db = db
        self.rag = rag_service

    def get_related_videos(
        self,
        video: Video,
        limit: int = 5,
    ) -> List[Recommendation]:
        """
        获取相关视频
        
        Args:
            video: 当前视频
            limit: 返回数量
            
        Returns:
            推荐列表
        """
        recommendations = []
        seen_ids = {video.id}

        # 策略1: 基于标签匹配
        tag_recs = self._recommend_by_tags(video, limit, seen_ids)
        recommendations.extend(tag_recs)
        seen_ids.update(r.video_id for r in tag_recs)

        # 策略2: 基于语义相似度（如果RAG可用）
        if self.rag and self.rag.is_available() and len(recommendations) < limit:
            semantic_recs = self._recommend_by_semantic(
                video,
                limit - len(recommendations),
                seen_ids,
            )
            recommendations.extend(semantic_recs)
            seen_ids.update(r.video_id for r in semantic_recs)

        # 策略3: 基于作者
        if len(recommendations) < limit:
            author_recs = self._recommend_by_author(
                video,
                limit - len(recommendations),
                seen_ids,
            )
            recommendations.extend(author_recs)

        logger.info(
            "recommendations_generated",
            video_id=video.id,
            count=len(recommendations),
        )

        return recommendations[:limit]

    def _recommend_by_tags(
        self,
        video: Video,
        limit: int,
        exclude_ids: set,
    ) -> List[Recommendation]:
        """基于标签推荐"""
        # 获取当前视频的标签
        video_tags = (
            self.db.query(VideoTag)
            .filter(VideoTag.video_id == video.id)
            .all()
        )
        
        if not video_tags:
            return []
        
        tag_ids = [vt.tag_id for vt in video_tags]
        
        # 查找有相同标签的其他视频
        related = (
            self.db.query(Video, VideoTag)
            .join(VideoTag)
            .filter(
                VideoTag.tag_id.in_(tag_ids),
                Video.id.notin_(exclude_ids),
                Video.tenant_id == video.tenant_id,
            )
            .limit(limit * 2)
            .all()
        )
        
        # 统计标签重叠度
        video_scores = {}
        for v, vt in related:
            if v.id not in video_scores:
                video_scores[v.id] = {"video": v, "score": 0, "tags": []}
            video_scores[v.id]["score"] += vt.confidence
            video_scores[v.id]["tags"].append(vt.tag_id)
        
        # 排序
        sorted_videos = sorted(
            video_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[:limit]
        
        return [
            Recommendation(
                video_id=item["video"].id,
                bvid=item["video"].source_id,
                title=item["video"].title,
                score=item["score"],
                reason=f"共享 {len(item['tags'])} 个标签",
            )
            for item in sorted_videos
        ]

    def _recommend_by_semantic(
        self,
        video: Video,
        limit: int,
        exclude_ids: set,
    ) -> List[Recommendation]:
        """基于语义相似度推荐"""
        if not self.rag:
            return []
        
        # 使用标题和摘要作为查询
        query = video.title
        if video.summary:
            query += " " + video.summary[:200]
        
        results = self.rag.search(
            tenant_id=video.tenant_id,
            query=query,
            top_k=limit + len(exclude_ids),
        )
        
        recommendations = []
        for r in results:
            if r.video_id and r.video_id not in exclude_ids:
                recommendations.append(Recommendation(
                    video_id=r.video_id,
                    bvid="",  # 需要从数据库获取
                    title=r.video_title or "",
                    score=r.score,
                    reason="内容相似",
                ))
                
                if len(recommendations) >= limit:
                    break
        
        return recommendations

    def _recommend_by_author(
        self,
        video: Video,
        limit: int,
        exclude_ids: set,
    ) -> List[Recommendation]:
        """基于作者推荐"""
        if not video.author:
            return []
        
        same_author = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == video.tenant_id,
                Video.author == video.author,
                Video.id.notin_(exclude_ids),
            )
            .limit(limit)
            .all()
        )
        
        return [
            Recommendation(
                video_id=v.id,
                bvid=v.source_id,
                title=v.title,
                score=0.5,
                reason=f"同一UP主: {video.author}",
            )
            for v in same_author
        ]

    def find_videos_by_concept(
        self,
        tenant_id: int,
        concept: str,
        limit: int = 10,
    ) -> List[Recommendation]:
        """
        根据概念查找视频
        
        Args:
            tenant_id: 租户ID
            concept: 概念关键词
            limit: 返回数量
            
        Returns:
            推荐列表
        """
        # 使用RAG搜索
        if self.rag and self.rag.is_available():
            results = self.rag.search(tenant_id, concept, limit)
            return [
                Recommendation(
                    video_id=r.video_id or 0,
                    bvid="",
                    title=r.video_title or "",
                    score=r.score,
                    reason=f"包含概念: {concept}",
                )
                for r in results
                if r.video_id
            ]
        
        # 降级到标题搜索
        videos = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.title.ilike(f"%{concept}%"),
            )
            .limit(limit)
            .all()
        )
        
        return [
            Recommendation(
                video_id=v.id,
                bvid=v.source_id,
                title=v.title,
                score=0.5,
                reason=f"标题包含: {concept}",
            )
            for v in videos
        ]
