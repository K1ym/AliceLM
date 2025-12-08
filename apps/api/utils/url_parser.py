"""
URL 解析工具

解析各平台 URL，提取 source_type 和 source_id。
"""

import hashlib
import re
from typing import Tuple


def parse_source(url: str) -> Tuple[str, str]:
    """
    解析 URL 返回 (source_type, source_id)

    Args:
        url: 内容 URL

    Returns:
        (source_type, source_id)

    Raises:
        ValueError: 不支持的 URL 格式
    """
    url = url.strip()

    # B 站
    if "bilibili.com" in url or "b23.tv" in url:
        source_id = extract_bvid(url)
        if source_id:
            return "bilibili", source_id
        raise ValueError(f"无法从 URL 提取 BV 号: {url}")

    # YouTube
    if "youtube.com" in url or "youtu.be" in url:
        source_id = extract_youtube_id(url)
        if source_id:
            return "youtube", source_id
        raise ValueError(f"无法从 URL 提取 YouTube ID: {url}")

    # 播客/RSS
    if url.endswith(".rss") or url.endswith(".xml") or "feed" in url.lower():
        return "podcast", hash_url(url)

    # 直接音频链接
    audio_exts = (".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac")
    if any(url.lower().endswith(ext) for ext in audio_exts):
        return "podcast", hash_url(url)

    raise ValueError(f"不支持的 URL 格式: {url}")


def extract_bvid(url: str) -> str:
    """从 B 站 URL 提取 BV 号"""
    # 匹配 BV 号格式
    match = re.search(r"(BV[a-zA-Z0-9]{10})", url)
    if match:
        return match.group(1)

    # 尝试匹配 av 号（旧格式）
    av_match = re.search(r"av(\d+)", url, re.IGNORECASE)
    if av_match:
        # 返回 av 号，后续可以转换
        return f"av{av_match.group(1)}"

    return ""


def extract_youtube_id(url: str) -> str:
    """从 YouTube URL 提取视频 ID"""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return ""


def hash_url(url: str) -> str:
    """生成 URL 的短哈希作为 source_id"""
    return hashlib.md5(url.encode()).hexdigest()[:12]
