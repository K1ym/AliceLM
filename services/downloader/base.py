"""
内容下载器抽象接口

定义统一的下载器接口，支持多内容源扩展。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DownloadMode(Enum):
    """下载模式"""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    file_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    subtitle_content: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0  # 下载耗时（秒）


@dataclass
class ContentMetadata:
    """内容元数据"""
    source_type: str
    source_id: str
    title: str
    author: str
    duration: int = 0  # 秒
    cover_url: Optional[str] = None
    source_url: Optional[str] = None
    extra: dict = field(default_factory=dict)  # 平台特有字段


class ContentDownloader(ABC):
    """
    内容下载器抽象接口

    所有平台的下载器都需要实现这个接口。
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """返回支持的内容源类型，如 'bilibili', 'youtube', 'podcast'"""
        pass

    @abstractmethod
    async def download(
        self,
        source_id: str,
        mode: DownloadMode = DownloadMode.AUDIO,
        output_dir: Optional[Path] = None,
    ) -> DownloadResult:
        """
        下载内容

        Args:
            source_id: 内容源 ID（如 bvid, youtube_id, rss_guid）
            mode: 下载模式（视频/音频/字幕）
            output_dir: 输出目录

        Returns:
            DownloadResult
        """
        pass

    @abstractmethod
    async def get_metadata(self, source_id: str) -> ContentMetadata:
        """
        获取内容元数据

        Args:
            source_id: 内容源 ID

        Returns:
            ContentMetadata
        """
        pass

    async def validate_source_id(self, source_id: str) -> bool:
        """
        验证 source_id 是否有效

        默认实现返回 True，子类可覆盖。
        """
        return True


# 下载器注册表
_downloaders: dict[str, ContentDownloader] = {}


def register_downloader(downloader: ContentDownloader) -> None:
    """注册下载器"""
    _downloaders[downloader.source_type] = downloader


def get_downloader(source_type: str) -> ContentDownloader:
    """
    获取指定类型的下载器

    Args:
        source_type: 内容源类型

    Returns:
        ContentDownloader

    Raises:
        ValueError: 不支持的内容源类型
    """
    if source_type not in _downloaders:
        available = ", ".join(_downloaders.keys()) or "无"
        raise ValueError(f"不支持的内容源类型: {source_type}，可用类型: {available}")
    return _downloaders[source_type]


def list_downloaders() -> list[str]:
    """列出所有已注册的下载器类型"""
    return list(_downloaders.keys())
