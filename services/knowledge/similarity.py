"""
视频相似度计算
P4-02: 视频相似度计算
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.db import Video
from packages.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SimilarityResult:
    """相似度结果"""
    video_id: int
    title: str
    score: float
    reasons: List[str]


class VideoSimilarityService:
    """视频相似度计算服务"""

    def __init__(self, db: Session):
        self.db = db

    def compute_similarity(
        self,
        video_a: Video,
        video_b: Video,
    ) -> float:
        """
        计算两个视频的相似度
        
        使用多维度加权计算:
        - 标签重叠: 40%
        - 概念重叠: 30%
        - 作者相同: 15%
        - 标题相似: 15%
        """
        scores = []
        weights = []

        # 标签重叠
        tag_score = self._compute_tag_overlap(video_a, video_b)
        if tag_score >= 0:
            scores.append(tag_score)
            weights.append(0.4)

        # 概念重叠
        concept_score = self._compute_concept_overlap(video_a, video_b)
        if concept_score >= 0:
            scores.append(concept_score)
            weights.append(0.3)

        # 作者相同
        author_score = 1.0 if video_a.author and video_a.author == video_b.author else 0.0
        scores.append(author_score)
        weights.append(0.15)

        # 标题相似
        title_score = self._compute_title_similarity(video_a.title, video_b.title)
        scores.append(title_score)
        weights.append(0.15)

        if not scores:
            return 0.0

        # 加权平均
        total_weight = sum(weights)
        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    def _compute_tag_overlap(self, video_a: Video, video_b: Video) -> float:
        """计算标签重叠度（Jaccard系数）"""
        import json

        try:
            tags_a = set(json.loads(video_a.key_points or "[]"))
            tags_b = set(json.loads(video_b.key_points or "[]"))
        except json.JSONDecodeError:
            return -1

        if not tags_a or not tags_b:
            return -1

        intersection = len(tags_a & tags_b)
        union = len(tags_a | tags_b)

        return intersection / union if union > 0 else 0.0

    def _compute_concept_overlap(self, video_a: Video, video_b: Video) -> float:
        """计算概念重叠度"""
        import json

        try:
            concepts_a = set(json.loads(video_a.concepts or "[]"))
            concepts_b = set(json.loads(video_b.concepts or "[]"))
        except json.JSONDecodeError:
            return -1

        if not concepts_a or not concepts_b:
            return -1

        intersection = len(concepts_a & concepts_b)
        union = len(concepts_a | concepts_b)

        return intersection / union if union > 0 else 0.0

    def _compute_title_similarity(self, title_a: str, title_b: str) -> float:
        """计算标题相似度（基于字符重叠）"""
        if not title_a or not title_b:
            return 0.0

        # 简单的字符级Jaccard
        chars_a = set(title_a.lower())
        chars_b = set(title_b.lower())

        intersection = len(chars_a & chars_b)
        union = len(chars_a | chars_b)

        return intersection / union if union > 0 else 0.0

    def find_similar_videos(
        self,
        video: Video,
        limit: int = 10,
        min_score: float = 0.1,
    ) -> List[SimilarityResult]:
        """
        查找相似视频
        
        Args:
            video: 目标视频
            limit: 返回数量
            min_score: 最低相似度阈值
            
        Returns:
            相似度排序的视频列表
        """
        # 获取同租户的其他视频
        candidates = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == video.tenant_id,
                Video.id != video.id,
                Video.status == "done",
            )
            .limit(100)  # 限制候选集大小
            .all()
        )

        results = []
        for candidate in candidates:
            score = self.compute_similarity(video, candidate)
            if score >= min_score:
                reasons = self._get_similarity_reasons(video, candidate)
                results.append(SimilarityResult(
                    video_id=candidate.id,
                    title=candidate.title,
                    score=score,
                    reasons=reasons,
                ))

        # 按分数降序排序
        results.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            "similar_videos_found",
            video_id=video.id,
            count=len(results[:limit]),
        )

        return results[:limit]

    def _get_similarity_reasons(self, video_a: Video, video_b: Video) -> List[str]:
        """获取相似原因"""
        import json
        reasons = []

        # 同作者
        if video_a.author and video_a.author == video_b.author:
            reasons.append(f"同一作者: {video_a.author}")

        # 共同概念
        try:
            concepts_a = set(json.loads(video_a.concepts or "[]"))
            concepts_b = set(json.loads(video_b.concepts or "[]"))
            common = concepts_a & concepts_b
            if common:
                reasons.append(f"共同概念: {', '.join(list(common)[:3])}")
        except json.JSONDecodeError:
            pass

        return reasons
