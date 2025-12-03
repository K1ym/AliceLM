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
            .filter(Video.tenant_id == tenant_id, Video.bvid == bvid)
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
            query = query.filter(Video.folder_id == folder_id)
        
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
            query = query.filter(Video.folder_id == folder_id)
        
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
