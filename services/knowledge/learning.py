"""
学习追踪服务
P4-06: 学习记录服务
P4-07: 周报生成
P4-08: 复习提醒
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

from packages.db import Video, User
from packages.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LearningRecord:
    """学习记录"""
    video_id: int
    user_id: int
    viewed_at: datetime
    duration_seconds: int = 0
    completed: bool = False
    notes: str = ""


@dataclass
class LearningStats:
    """学习统计"""
    total_videos: int
    total_duration: int  # 秒
    completed_videos: int
    concepts_learned: List[str]
    videos_by_day: Dict[str, int]
    top_authors: List[Dict]


@dataclass
class WeeklyReport:
    """周报"""
    user_id: int
    week_start: datetime
    week_end: datetime
    stats: LearningStats
    highlights: List[str]
    recommendations: List[Dict]


class LearningService:
    """学习追踪服务"""

    def __init__(self, db: Session):
        self.db = db
        self._records: Dict[tuple, LearningRecord] = {}  # (user_id, video_id) -> record

    def record_view(
        self,
        user_id: int,
        video_id: int,
        duration_seconds: int = 0,
        completed: bool = False,
    ) -> LearningRecord:
        """记录观看"""
        key = (user_id, video_id)

        if key not in self._records:
            self._records[key] = LearningRecord(
                video_id=video_id,
                user_id=user_id,
                viewed_at=datetime.utcnow(),
            )

        record = self._records[key]
        record.duration_seconds += duration_seconds
        record.viewed_at = datetime.utcnow()

        if completed:
            record.completed = True

        logger.info(
            "learning_recorded",
            user_id=user_id,
            video_id=video_id,
            duration=duration_seconds,
        )

        return record

    def get_user_stats(
        self,
        user_id: int,
        days: int = 7,
    ) -> LearningStats:
        """获取用户学习统计"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return LearningStats(0, 0, 0, [], {}, [])

        tenant_id = user.tenant_id
        since = datetime.utcnow() - timedelta(days=days)

        # 获取已完成的视频
        videos = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.status == "done",
                Video.processed_at >= since,
            )
            .all()
        )

        # 统计
        total_videos = len(videos)
        total_duration = sum(v.duration or 0 for v in videos)

        # 用户观看记录中标记为完成的
        user_records = [r for r in self._records.values() if r.user_id == user_id]
        completed_videos = sum(1 for r in user_records if r.completed)

        # 概念统计
        all_concepts = []
        for v in videos:
            try:
                concepts = json.loads(v.concepts or "[]")
                all_concepts.extend(concepts)
            except json.JSONDecodeError:
                pass
        concepts_learned = list(set(all_concepts))

        # 每日统计
        videos_by_day = defaultdict(int)
        for v in videos:
            if v.processed_at:
                day = v.processed_at.strftime("%Y-%m-%d")
                videos_by_day[day] += 1

        # 作者统计
        author_counts = defaultdict(int)
        for v in videos:
            if v.author:
                author_counts[v.author] += 1
        top_authors = [
            {"author": a, "count": c}
            for a, c in sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return LearningStats(
            total_videos=total_videos,
            total_duration=total_duration,
            completed_videos=completed_videos,
            concepts_learned=concepts_learned[:20],
            videos_by_day=dict(videos_by_day),
            top_authors=top_authors,
        )

    def generate_weekly_report(
        self,
        user_id: int,
    ) -> WeeklyReport:
        """
        生成周报
        
        Args:
            user_id: 用户ID
            
        Returns:
            周报对象
        """
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        week_end = now

        stats = self.get_user_stats(user_id, days=7)

        # 生成亮点
        highlights = []
        if stats.total_videos > 0:
            highlights.append(f"本周学习了 {stats.total_videos} 个视频")
        if stats.total_duration > 0:
            hours = stats.total_duration // 3600
            minutes = (stats.total_duration % 3600) // 60
            highlights.append(f"总学习时长 {hours}小时{minutes}分钟")
        if stats.concepts_learned:
            highlights.append(f"涉及 {len(stats.concepts_learned)} 个核心概念")
        if stats.top_authors:
            top_author = stats.top_authors[0]["author"]
            highlights.append(f"最常学习的UP主: {top_author}")

        # 推荐（基于学习的概念）
        recommendations = []
        # TODO: 基于概念推荐相关视频

        logger.info(
            "weekly_report_generated",
            user_id=user_id,
            total_videos=stats.total_videos,
        )

        return WeeklyReport(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            stats=stats,
            highlights=highlights,
            recommendations=recommendations,
        )

    def get_review_suggestions(
        self,
        user_id: int,
        limit: int = 5,
    ) -> List[Dict]:
        """
        获取复习建议
        
        基于艾宾浩斯遗忘曲线，建议复习较早学习的内容
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # 获取用户观看记录
        user_records = [
            r for r in self._records.values()
            if r.user_id == user_id and r.completed
        ]

        if not user_records:
            return []

        # 按时间排序，取最早的
        user_records.sort(key=lambda r: r.viewed_at)

        suggestions = []
        now = datetime.utcnow()

        for record in user_records[:limit]:
            days_ago = (now - record.viewed_at).days
            if days_ago >= 1:  # 至少1天前的内容
                video = self.db.query(Video).filter(Video.id == record.video_id).first()
                if video:
                    suggestions.append({
                        "video_id": video.id,
                        "title": video.title,
                        "days_since_view": days_ago,
                        "reason": f"已过 {days_ago} 天，建议复习",
                    })

        return suggestions
