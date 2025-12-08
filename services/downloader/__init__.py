"""
下载服务模块

支持多内容源的统一下载接口。
"""

# 抽象接口
from .base import (
    ContentDownloader,
    ContentMetadata,
    DownloadMode,
    DownloadResult,
    get_downloader,
    list_downloaders,
    register_downloader,
)

# 具体实现
from .bilibili_downloader import BilibiliDownloader
from .podcast_downloader import PodcastDownloader

# 兼容旧代码
from .bbdown import (
    BBDownService,
    DownloadMode as BBDownMode,
    DownloadResult as BBDownResult,
    SubtitleInfo,
    get_bbdown_service,
)

# 注册默认下载器
register_downloader(BilibiliDownloader())
register_downloader(PodcastDownloader())

__all__ = [
    # 新接口
    "ContentDownloader",
    "ContentMetadata",
    "DownloadMode",
    "DownloadResult",
    "get_downloader",
    "list_downloaders",
    "register_downloader",
    "BilibiliDownloader",
    "PodcastDownloader",
    # 兼容旧代码
    "BBDownService",
    "SubtitleInfo",
    "get_bbdown_service",
]
