"""
视频下载模块
支持yt-dlp和BBDown双后端
"""

import asyncio
import glob
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from packages.config import get_config
from packages.logging import get_logger
from alice.errors import AliceError, NetworkError

logger = get_logger(__name__)


class DownloadBackend:
    """下载后端类型"""
    YT_DLP = "yt-dlp"
    BBDOWN = "bbdown"


class VideoDownloader:
    """视频下载器"""

    def __init__(self, output_dir: str = "data/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_bilibili(self, bvid: str, sessdata: Optional[str] = None) -> Path:
        """
        下载B站视频（使用yt-dlp）
        
        Args:
            bvid: BV号
            sessdata: 登录cookie（用于下载高清视频）
            
        Returns:
            下载的视频文件路径
        """
        if not bvid.startswith("BV"):
            bvid = "BV" + bvid

        video_url = f"https://www.bilibili.com/video/{bvid}"
        video_dir = self.output_dir / bvid
        video_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(video_dir / "%(title).50s.%(ext)s")

        logger.info("downloading_video", bvid=bvid, url=video_url)

        # 构建yt-dlp命令（使用虚拟环境中的yt-dlp）
        yt_dlp_path = Path(sys.executable).parent / "yt-dlp"
        cmd = [
            str(yt_dlp_path),
            "-f", "bestvideo+bestaudio/best",  # 更宽松的格式选择
            "--merge-output-format", "mp4",     # 合并为mp4
            "-o", output_template,
            "--no-playlist",
            "--socket-timeout", "30",
        ]
        
        # 如果有cookie，添加参数
        if sessdata:
            # 创建临时cookie文件（Netscape格式）
            cookie_file = video_dir / "cookies.txt"
            with open(cookie_file, "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t{sessdata}\n")
            cmd.extend(["--cookies", str(cookie_file)])
        
        cmd.append(video_url)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
            )

            # 清理cookie文件
            cookie_file = video_dir / "cookies.txt"
            if cookie_file.exists():
                cookie_file.unlink()

            if result.returncode != 0:
                logger.error("download_failed", bvid=bvid, stderr=result.stderr)
                raise Exception(f"下载失败: {result.stderr}")

            # 查找下载的视频文件
            video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.webm")) + list(video_dir.glob("*.mkv"))
            if not video_files:
                raise FileNotFoundError(f"未找到下载的视频文件: {video_dir}")

            video_path = video_files[0]

            # 清理xml/json等附加文件
            for f in video_dir.glob("*.xml"):
                f.unlink()
            for f in video_dir.glob("*.json"):
                f.unlink()

            logger.info("download_complete", bvid=bvid, path=str(video_path))
            return video_path

        except subprocess.TimeoutExpired as e:
            logger.error("download_timeout", bvid=bvid, exc_info=True)
            raise NetworkError(f"下载超时: {bvid}") from e
        except (OSError, IOError) as e:
            logger.error("download_error_io", bvid=bvid, error=str(e), exc_info=True)
            raise
        except Exception as e:
            logger.exception("download_error_unexpected", bvid=bvid)
            raise

    def get_video_path(self, bvid: str) -> Optional[Path]:
        """获取已下载视频的路径"""
        video_dir = self.output_dir / bvid
        if not video_dir.exists():
            return None

        video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.flv"))
        return video_files[0] if video_files else None

    async def download_audio_async(
        self,
        bvid: str,
        sessdata: Optional[str] = None,
        prefer_bbdown: bool = True,
    ) -> tuple[Path, Optional[str]]:
        """
        异步下载音频（支持BBDown）
        
        Args:
            bvid: BV号
            sessdata: 登录cookie
            prefer_bbdown: 优先使用BBDown
        
        Returns:
            (音频路径, AI字幕内容或None)
        """
        from services.downloader import get_bbdown_service, DownloadMode
        
        if prefer_bbdown:
            try:
                bbdown = get_bbdown_service()
                if bbdown.bbdown_path:
                    result = await bbdown.download_video(
                        bvid,
                        mode=DownloadMode.AUDIO,
                        with_subtitle=True,
                    )
                    
                    if result.success and result.file_path:
                        # 读取AI字幕
                        ai_subtitle = None
                        if result.subtitle_path and result.subtitle_path.exists():
                            ai_subtitle = result.subtitle_path.read_text(encoding="utf-8")
                            logger.info("ai_subtitle_found", bvid=bvid)
                        
                        return result.file_path, ai_subtitle
                    
                    logger.warning("bbdown_failed_fallback", bvid=bvid, error=result.error)
            except (NetworkError, OSError, IOError) as e:
                logger.error("bbdown_error_fallback", bvid=bvid, error=str(e), exc_info=True)
            except Exception as e:
                logger.exception("bbdown_error_fallback_unexpected", bvid=bvid)
        
        # 回退到yt-dlp
        video_path = self.download_bilibili(bvid, sessdata)
        return video_path, None

    def download_audio_sync(
        self,
        bvid: str,
        sessdata: Optional[str] = None,
    ) -> Path:
        """
        同步下载（仅yt-dlp，用于兼容现有代码）
        """
        return self.download_bilibili(bvid, sessdata)
