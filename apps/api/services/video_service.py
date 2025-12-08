"""
视频服务
视频相关的业务逻辑
"""

import re
from typing import Optional, List, Tuple
import httpx

from packages.db import Video, VideoStatus, Tenant
from packages.logging import get_logger

from ..repositories.video_repo import VideoRepository

logger = get_logger(__name__)


class VideoService:
    """视频服务类"""
    
    def __init__(self, repo: VideoRepository):
        self.repo = repo
    
    async def parse_bvid(self, url_or_text: str) -> str:
        """解析 BV 号"""
        url_or_text = url_or_text.strip()
        
        # 如果包含b23.tv短链接，先解析真实URL
        b23_match = re.search(r'https?://b23\.tv/([a-zA-Z0-9]+)', url_or_text)
        if b23_match:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                    resp = await client.head(f"https://b23.tv/{b23_match.group(1)}")
                    url_or_text = str(resp.url)
            except Exception as e:
                logger.warning("b23_redirect_failed", error=str(e))
        
        # 解析BV号
        bvid_match = re.search(r'(BV[a-zA-Z0-9]+)', url_or_text)
        if not bvid_match:
            raise ValueError("无效的B站视频URL或BV号")
        
        return bvid_match.group(1)
    
    async def import_video(
        self,
        url: str,
        tenant: Tenant,
        auto_process: bool = True,
    ) -> Tuple[Video, bool]:
        """
        导入视频
        
        Returns:
            (Video, is_new): 视频对象和是否为新创建
        """
        bvid = await self.parse_bvid(url)

        # 检查是否已存在
        existing = self.repo.get_by_source(tenant.id, "bilibili", bvid)
        if existing:
            return existing, False

        # 获取视频信息
        video_info = await self._fetch_video_info(bvid)

        # 创建视频记录
        video = self.repo.create(
            tenant_id=tenant.id,
            source_type="bilibili",
            source_id=bvid,
            title=video_info.get("title", bvid),
            author=video_info.get("owner", {}).get("name", ""),
            cover_url=video_info.get("pic", ""),
            duration=video_info.get("duration", 0),
            status=VideoStatus.PENDING if auto_process else VideoStatus.IMPORTED,
        )

        logger.info("video_imported", video_id=video.id, source_id=bvid)
        
        return video, True
    
    async def _fetch_video_info(self, bvid: str) -> dict:
        """获取视频信息"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid},
                )
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("data", {})
        except Exception as e:
            logger.warning("fetch_video_info_failed", bvid=bvid, error=str(e))
        return {}
    
    def get_video(self, video_id: int, tenant_id: int) -> Optional[Video]:
        """获取视频详情"""
        video = self.repo.get(video_id)
        if video and video.tenant_id == tenant_id:
            return video
        return None
    
    def list_videos(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        folder_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Video], int]:
        """获取视频列表"""
        videos = self.repo.list_by_tenant(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            status=status,
            folder_id=folder_id,
            search=search,
        )
        total = self.repo.count_by_tenant(
            tenant_id=tenant_id,
            status=status,
            folder_id=folder_id,
        )
        return videos, total
    
    def delete_video(self, video_id: int, tenant_id: int) -> bool:
        """删除视频"""
        video = self.get_video(video_id, tenant_id)
        if video:
            return self.repo.delete(video_id)
        return False
    
    def get_processing_queue(self, tenant_id: int) -> dict:
        """获取处理队列状态"""
        processing = self.repo.get_processing_queue(tenant_id)
        failed = self.repo.get_failed_videos(tenant_id, limit=10)
        done = self.repo.get_recent_done(tenant_id, limit=5)
        
        return {
            "processing": processing,
            "failed": failed,
            "done": done,
            "counts": {
                "processing": len(processing),
                "failed": len(failed),
                "done": len(done),
            }
        }
    
    def update_status(self, video_id: int, tenant_id: int, status: str) -> Optional[Video]:
        """更新视频状态"""
        video = self.get_video(video_id, tenant_id)
        if video:
            return self.repo.update_status(video_id, status)
        return None
    
    def retry_failed(self, video_id: int, tenant_id: int) -> Optional[Video]:
        """重试失败的视频"""
        from packages.db import VideoStatus
        
        video = self.get_video(video_id, tenant_id)
        if video and video.status == VideoStatus.FAILED.value:
            return self.repo.update_status(video_id, VideoStatus.PENDING.value)
        return None
    
    def reprocess_video(self, video_id: int, tenant_id: int) -> Optional[Video]:
        """重新处理视频"""
        video = self.get_video(video_id, tenant_id)
        if not video:
            return None
        
        video = self.repo.reset_for_reprocess(video)
        logger.info("video_reprocess", video_id=video_id)
        return video
    
    def get_stats(self, tenant_id: int) -> dict:
        """获取视频统计"""
        return self.repo.get_stats(tenant_id)
    
    def get_top_tags(self, tenant_id: int, limit: int = 5) -> List[dict]:
        """获取热门标签"""
        import json
        from collections import Counter
        
        videos = self.repo.get_done_videos(tenant_id)
        tag_counter: Counter = Counter()
        
        for video in videos:
            if video.concepts:
                try:
                    concepts = json.loads(video.concepts)
                    if isinstance(concepts, list):
                        for concept in concepts:
                            if isinstance(concept, str) and concept.strip():
                                tag_counter[concept.strip()] += 1
                except json.JSONDecodeError:
                    pass
        
        return [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(limit)]
    
    def get_recent_done(self, tenant_id: int, limit: int = 5) -> List[Video]:
        """获取最近完成的视频"""
        return self.repo.get_recent_done(tenant_id, limit)
    
    def update_analysis(
        self,
        video_id: int,
        tenant_id: int,
        summary: str = None,
        key_points: str = None,
        concepts: str = None,
    ) -> Optional[Video]:
        """更新视频分析结果"""
        video = self.get_video(video_id, tenant_id)
        if not video:
            return None
        return self.repo.update_analysis(video_id, summary, key_points, concepts)
