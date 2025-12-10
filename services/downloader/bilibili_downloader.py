"""
B 站内容下载器

基于 BBDown 和 yt-dlp 实现。
"""

import asyncio
import re
from pathlib import Path
from typing import Optional

import httpx

from packages.config import get_config
from packages.logging import get_logger

from .base import ContentDownloader, ContentMetadata, DownloadMode, DownloadResult
from .bbdown import BBDownService, DownloadMode as BBDownMode

logger = get_logger(__name__)


class BilibiliDownloader(ContentDownloader):
    """B 站内容下载器"""

    def __init__(
        self,
        output_dir: str = "data/downloads",
        sessdata: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        config = get_config()
        self.sessdata = sessdata or getattr(config, "bilibili_sessdata", None)

        # 复用 BBDownService
        self._bbdown = BBDownService(
            output_dir=output_dir,
            cookie=self.sessdata,
        )

    @property
    def source_type(self) -> str:
        return "bilibili"

    async def download(
        self,
        source_id: str,
        mode: DownloadMode = DownloadMode.AUDIO,
        output_dir: Optional[Path] = None,
    ) -> DownloadResult:
        """下载 B 站视频/音频"""
        # 确保 BV 格式正确
        bvid = self._normalize_bvid(source_id)

        # 映射下载模式
        bbdown_mode = {
            DownloadMode.VIDEO: BBDownMode.VIDEO,
            DownloadMode.AUDIO: BBDownMode.AUDIO,
            DownloadMode.SUBTITLE: BBDownMode.SUBTITLE,
        }.get(mode, BBDownMode.AUDIO)

        # 调用 BBDown
        result = await self._bbdown.download_video(
            bvid=bvid,
            mode=bbdown_mode,
            with_subtitle=True,
        )

        # 读取字幕内容
        subtitle_content = None
        if result.subtitle_path and result.subtitle_path.exists():
            try:
                subtitle_content = result.subtitle_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("read_subtitle_failed", source_id=bvid, error=str(e))

        return DownloadResult(
            success=result.success,
            file_path=result.file_path,
            subtitle_path=result.subtitle_path,
            subtitle_content=subtitle_content,
            error=result.error,
            duration=result.duration,
        )

    async def get_metadata(self, source_id: str) -> ContentMetadata:
        """获取 B 站视频元数据"""
        bvid = self._normalize_bvid(source_id)

        api_url = "https://api.bilibili.com/x/web-interface/view"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(api_url, params={"bvid": bvid}, headers=headers)
            data = resp.json()

            if data["code"] != 0:
                raise ValueError(f"获取视频信息失败: {data.get('message', 'Unknown error')}")

            info = data["data"]
            return ContentMetadata(
                source_type="bilibili",
                source_id=bvid,
                title=info["title"],
                author=info["owner"]["name"],
                duration=info["duration"],
                cover_url=info.get("pic"),
                source_url=f"https://www.bilibili.com/video/{bvid}",
                extra={
                    "aid": info["aid"],
                    "view": info["stat"]["view"],
                    "danmaku": info["stat"]["danmaku"],
                },
            )

    async def validate_source_id(self, source_id: str) -> bool:
        """验证 bvid 格式"""
        return bool(re.match(r"^BV[a-zA-Z0-9]{10}$", self._normalize_bvid(source_id)))

    def _normalize_bvid(self, source_id: str) -> str:
        """标准化 bvid 格式"""
        if not source_id.startswith("BV"):
            return f"BV{source_id}"
        return source_id
