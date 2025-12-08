"""
播客/RSS 内容下载器

支持从 RSS feed 下载播客音频。
"""

import hashlib
import time
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from packages.logging import get_logger

from .base import ContentDownloader, ContentMetadata, DownloadMode, DownloadResult

logger = get_logger(__name__)


class PodcastDownloader(ContentDownloader):
    """播客/RSS 内容下载器"""

    def __init__(self, output_dir: str = "data/downloads/podcast"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_type(self) -> str:
        return "podcast"

    async def download(
        self,
        source_id: str,
        mode: DownloadMode = DownloadMode.AUDIO,
        output_dir: Optional[Path] = None,
    ) -> DownloadResult:
        """
        下载播客音频

        Args:
            source_id: 音频 URL 或 RSS item guid
            mode: 下载模式（播客只支持 AUDIO）
            output_dir: 输出目录
        """
        start_time = time.time()
        work_dir = output_dir or self.output_dir

        # source_id 可能是直接的音频 URL
        audio_url = source_id

        try:
            async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
                # 下载音频
                logger.info("podcast_download_start", url=audio_url[:100])

                resp = await client.get(audio_url)
                resp.raise_for_status()

                # 确定文件扩展名
                content_type = resp.headers.get("content-type", "")
                ext = self._get_extension(content_type, audio_url)

                # 生成文件名
                file_hash = hashlib.md5(audio_url.encode()).hexdigest()[:12]
                file_name = f"{file_hash}{ext}"
                file_path = work_dir / file_name

                work_dir.mkdir(parents=True, exist_ok=True)

                # 保存文件
                file_path.write_bytes(resp.content)

                duration = time.time() - start_time
                logger.info(
                    "podcast_download_complete",
                    url=audio_url[:100],
                    file_path=str(file_path),
                    size_mb=len(resp.content) / 1024 / 1024,
                    duration=duration,
                )

                return DownloadResult(
                    success=True,
                    file_path=file_path,
                    duration=duration,
                )

        except Exception as e:
            logger.error("podcast_download_failed", url=audio_url[:100], error=str(e))
            return DownloadResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )

    async def get_metadata(self, source_id: str) -> ContentMetadata:
        """
        获取播客元数据

        对于直接的音频 URL，返回基本信息。
        如果需要完整元数据，应该从 RSS feed 解析。
        """
        # 从 URL 提取基本信息
        file_hash = hashlib.md5(source_id.encode()).hexdigest()[:12]

        return ContentMetadata(
            source_type="podcast",
            source_id=file_hash,
            title=f"Podcast Episode ({file_hash})",
            author="Unknown",
            duration=0,
            source_url=source_id,
        )

    async def get_metadata_from_rss(
        self,
        feed_url: str,
        guid: str,
    ) -> Optional[ContentMetadata]:
        """
        从 RSS feed 获取特定 episode 的元数据

        Args:
            feed_url: RSS feed URL
            guid: episode 的 guid

        Returns:
            ContentMetadata 或 None
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()

                root = ET.fromstring(resp.content)
                channel = root.find("channel")

                if channel is None:
                    return None

                podcast_title = channel.findtext("title", "Unknown Podcast")

                for item in channel.findall("item"):
                    item_guid = item.findtext("guid", "")
                    if item_guid == guid:
                        # 找到匹配的 episode
                        enclosure = item.find("enclosure")
                        audio_url = enclosure.get("url") if enclosure is not None else None

                        # 解析时长
                        duration_str = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration", "0")
                        duration = self._parse_duration(duration_str)

                        return ContentMetadata(
                            source_type="podcast",
                            source_id=guid,
                            title=item.findtext("title", "Unknown Episode"),
                            author=podcast_title,
                            duration=duration,
                            source_url=audio_url,
                            extra={
                                "feed_url": feed_url,
                                "description": item.findtext("description", ""),
                                "pub_date": item.findtext("pubDate", ""),
                            },
                        )

                return None

        except Exception as e:
            logger.error("rss_parse_failed", feed_url=feed_url, error=str(e))
            return None

    async def list_episodes(self, feed_url: str, limit: int = 20) -> list[ContentMetadata]:
        """
        列出 RSS feed 中的 episodes

        Args:
            feed_url: RSS feed URL
            limit: 最大返回数量

        Returns:
            ContentMetadata 列表
        """
        episodes = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()

                root = ET.fromstring(resp.content)
                channel = root.find("channel")

                if channel is None:
                    return []

                podcast_title = channel.findtext("title", "Unknown Podcast")

                for item in channel.findall("item")[:limit]:
                    enclosure = item.find("enclosure")
                    audio_url = enclosure.get("url") if enclosure is not None else None

                    if not audio_url:
                        continue

                    guid = item.findtext("guid", audio_url)
                    duration_str = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration", "0")

                    episodes.append(ContentMetadata(
                        source_type="podcast",
                        source_id=guid,
                        title=item.findtext("title", "Unknown Episode"),
                        author=podcast_title,
                        duration=self._parse_duration(duration_str),
                        source_url=audio_url,
                        extra={
                            "feed_url": feed_url,
                            "pub_date": item.findtext("pubDate", ""),
                        },
                    ))

        except Exception as e:
            logger.error("rss_list_failed", feed_url=feed_url, error=str(e))

        return episodes

    def _get_extension(self, content_type: str, url: str) -> str:
        """根据 content-type 或 URL 确定文件扩展名"""
        type_map = {
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/aac": ".aac",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/flac": ".flac",
        }

        for mime, ext in type_map.items():
            if mime in content_type:
                return ext

        # 从 URL 推断
        url_lower = url.lower()
        for ext in [".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac"]:
            if ext in url_lower:
                return ext

        return ".mp3"  # 默认

    def _parse_duration(self, duration_str: str) -> int:
        """解析时长字符串为秒数"""
        if not duration_str:
            return 0

        try:
            # 纯数字（秒）
            if duration_str.isdigit():
                return int(duration_str)

            # HH:MM:SS 或 MM:SS 格式
            parts = duration_str.split(":")
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])

        except (ValueError, IndexError):
            pass

        return 0
