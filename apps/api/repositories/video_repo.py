"""
视频仓储
视频相关的数据访问操作
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from packages.db import Video, VideoStatus
from .base import BaseRepository


class VideoRepository(BaseRepository[Video]):
    """视频仓储类"""
    
    def __init__(self, db: Session):
        super().__init__(db, Video)
    
    def get_by_bvid(self, tenant_id: int, bvid: str) -> Optional[Video]:
        """根据BV号获取视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.source_id == bvid)
            .first()
        )
    
    def list_by_tenant(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        folder_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Video]:
        """获取租户的视频列表"""
        query = self.db.query(Video).filter(Video.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Video.status == status)
        
        if folder_id:
            query = query.filter(Video.watched_folder_id == folder_id)
        
        if search:
            query = query.filter(Video.title.ilike(f"%{search}%"))
        
        return query.order_by(desc(Video.created_at)).offset(skip).limit(limit).all()
    
    def count_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        folder_id: Optional[int] = None,
    ) -> int:
        """统计租户的视频数量"""
        query = self.db.query(Video).filter(Video.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Video.status == status)
        
        if folder_id:
            query = query.filter(Video.watched_folder_id == folder_id)
        
        return query.count()
    
    def get_by_status(self, tenant_id: int, status: str) -> List[Video]:
        """获取指定状态的视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.status == status)
            .all()
        )
    
    def update_status(self, video_id: int, status: str, error_message: str = None) -> Optional[Video]:
        """更新视频状态"""
        video = self.get(video_id)
        if video:
            video.status = status
            if error_message:
                video.error_message = error_message
            self.db.commit()
            self.db.refresh(video)
        return video
    
    def get_processing_queue(self, tenant_id: int) -> List[Video]:
        """获取处理中的视频队列"""
        return (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.status.in_([
                    VideoStatus.PENDING.value,
                    VideoStatus.DOWNLOADING.value,
                    VideoStatus.TRANSCRIBING.value,
                    VideoStatus.ANALYZING.value,
                ])
            )
            .order_by(Video.created_at.asc())
            .all()
        )
    
    def get_failed_videos(self, tenant_id: int, limit: int = 10) -> List[Video]:
        """获取失败的视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.FAILED.value)
            .order_by(desc(Video.created_at))
            .limit(limit)
            .all()
        )
    
    def get_recent_done(self, tenant_id: int, limit: int = 5) -> List[Video]:
        """获取最近完成的视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.DONE.value)
            .order_by(desc(Video.processed_at))
            .limit(limit)
            .all()
        )
    
    def get_stats(self, tenant_id: int) -> dict:
        """获取视频统计"""
        from sqlalchemy import func
        
        total = self.db.query(func.count(Video.id)).filter(Video.tenant_id == tenant_id).scalar() or 0
        
        # 按状态分组统计
        status_counts = (
            self.db.query(Video.status, func.count(Video.id))
            .filter(Video.tenant_id == tenant_id)
            .group_by(Video.status)
            .all()
        )
        
        stats = {s.value: 0 for s in VideoStatus}
        for status_val, count in status_counts:
            stats[status_val] = count
        
        return {
            "total": total,
            "done": stats.get(VideoStatus.DONE.value, 0),
            "pending": stats.get(VideoStatus.PENDING.value, 0),
            "failed": stats.get(VideoStatus.FAILED.value, 0),
            "processing": (
                stats.get(VideoStatus.DOWNLOADING.value, 0) +
                stats.get(VideoStatus.TRANSCRIBING.value, 0) +
                stats.get(VideoStatus.ANALYZING.value, 0)
            ),
        }
    
    def get_done_videos(self, tenant_id: int) -> List[Video]:
        """获取所有完成的视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.DONE.value)
            .all()
        )
    
    def get_recent_done(self, tenant_id: int, limit: int = 5) -> List[Video]:
        """获取最近完成的视频"""
        return (
            self.db.query(Video)
            .filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.DONE.value)
            .order_by(Video.processed_at.desc())
            .limit(limit)
            .all()
        )
    
    def update_analysis(
        self,
        video_id: int,
        summary: str = None,
        key_points: str = None,
        concepts: str = None,
    ) -> Optional[Video]:
        """更新视频分析结果"""
        video = self.get(video_id)
        if not video:
            return None
        
        if summary is not None:
            video.summary = summary
        if key_points is not None:
            video.key_points = key_points
        if concepts is not None:
            video.concepts = concepts
        
        self.db.commit()
        self.db.refresh(video)
        return video
    
    def reset_for_reprocess(self, video: Video) -> Video:
        """重置视频状态以重新处理"""
        video.status = VideoStatus.PENDING.value
        video.error_message = None
        self.db.commit()
        self.db.refresh(video)
        return video
