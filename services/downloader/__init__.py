"""
下载服务模块
"""

from .bbdown import (
    BBDownService,
    DownloadMode,
    DownloadResult,
    SubtitleInfo,
    get_bbdown_service,
)

__all__ = [
    "BBDownService",
    "DownloadMode",
    "DownloadResult",
    "SubtitleInfo",
    "get_bbdown_service",
]
