"""
收藏夹扫描器
检测新视频并加入处理队列
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from packages.db import Video, VideoStatus, WatchedFolder, get_db_context
from packages.logging import get_logger

from .bilibili import BilibiliClient, VideoInfo

logger = get_logger(__name__)


class FolderScanner:
    """收藏夹扫描器"""

    def __init__(self, tenant_id: int, sessdata: Optional[str] = None):
        """
        初始化扫描器
        
        Args:
            tenant_id: 租户ID
            sessdata: B站登录cookie
        """
        self.tenant_id = tenant_id
        self.client = BilibiliClient(sessdata)

    def scan_folder(self, folder: WatchedFolder, db: Session) -> List[Video]:
        """
        扫描单个收藏夹，检测新视频
        
        Args:
            folder: 监控的收藏夹
            db: 数据库会话
            
        Returns:
            新增的视频列表
        """
        new_videos = []

        try:
            if folder.folder_type == "season":
                _, videos = self.client.fetch_season(folder.folder_id)
            else:
                _, videos = self.client.fetch_favlist(folder.folder_id)

            for video_info in videos:
                # 检查是否已存在
                exists = db.query(Video).filter(
                    Video.tenant_id == self.tenant_id,
                    Video.source_id == video_info.source_id,
                ).first()

                if exists:
                    # 如果存在但没有关联收藏夹，更新关联
                    if exists.watched_folder_id is None:
                        exists.watched_folder_id = folder.id
                    continue

                # 创建新视频记录
                video = Video(
                    tenant_id=self.tenant_id,
                    watched_folder_id=folder.id,
                    bvid=video_info.source_id,
                    title=video_info.title,
                    author=video_info.author,
                    duration=video_info.duration,
                    cover_url=video_info.cover_url,
                    source_type="bilibili",
                    source_url=f"https://www.bilibili.com/video/{video_info.source_id}",
                    status=VideoStatus.PENDING.value,
                    collected_at=datetime.utcnow(),
                )
                db.add(video)
                new_videos.append(video)

            # 更新扫描时间
            folder.last_scan_at = datetime.utcnow()
            db.commit()

            logger.info(
                "folder_scanned",
                folder_id=folder.folder_id,
                folder_name=folder.name,
                new_videos=len(new_videos),
            )

        except Exception as e:
            logger.error(
                "folder_scan_error",
                folder_id=folder.folder_id,
                error=str(e),
            )
            raise

        return new_videos

    def scan_all_folders(self, db: Session) -> List[Video]:
        """
        扫描所有活跃的收藏夹
        
        Args:
            db: 数据库会话
            
        Returns:
            所有新增的视频列表
        """
        folders = db.query(WatchedFolder).filter(
            WatchedFolder.tenant_id == self.tenant_id,
            WatchedFolder.is_active == True,
        ).all()

        all_new_videos = []
        for folder in folders:
            try:
                new_videos = self.scan_folder(folder, db)
                all_new_videos.extend(new_videos)
            except Exception as e:
                logger.error("scan_folder_failed", folder_id=folder.folder_id, error=str(e))
                continue

        logger.info(
            "all_folders_scanned",
            tenant_id=self.tenant_id,
            folder_count=len(folders),
            new_videos=len(all_new_videos),
        )

        return all_new_videos

    def add_folder(
        self,
        folder_id: str,
        folder_type: str,
        name: str,
        db: Session,
    ) -> WatchedFolder:
        """
        添加监控收藏夹
        
        Args:
            folder_id: 收藏夹ID
            folder_type: 类型(favlist/season)
            name: 名称
            db: 数据库会话
            
        Returns:
            创建的WatchedFolder对象
        """
        # 检查是否已存在
        exists = db.query(WatchedFolder).filter(
            WatchedFolder.tenant_id == self.tenant_id,
            WatchedFolder.folder_id == folder_id,
        ).first()

        if exists:
            logger.info("folder_already_exists", folder_id=folder_id)
            return exists

        folder = WatchedFolder(
            tenant_id=self.tenant_id,
            folder_id=folder_id,
            folder_type=folder_type,
            name=name,
            platform="bilibili",
            is_active=True,
        )
        db.add(folder)
        db.commit()

        logger.info("folder_added", folder_id=folder_id, name=name)
        return folder

    def close(self):
        """关闭客户端"""
        self.client.close()
