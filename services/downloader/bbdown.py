"""
BBDown 服务封装
提供B站视频下载、音频下载、AI字幕获取功能
"""

import asyncio
import json
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from enum import Enum

import httpx

from packages.config import get_config
from packages.logging import get_logger

logger = get_logger(__name__)


class DownloadMode(Enum):
    """下载模式"""
    VIDEO = "video"  # 下载视频
    AUDIO = "audio"  # 仅下载音频
    SUBTITLE = "subtitle"  # 仅下载字幕


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    file_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None  # AI字幕路径
    error: Optional[str] = None
    duration: float = 0  # 下载耗时（秒）


@dataclass
class SubtitleInfo:
    """字幕信息"""
    content: str  # SRT格式内容
    language: str = "zh"
    source: str = "bilibili_ai"  # bilibili_ai / local_asr


class BBDownService:
    """
    BBDown服务封装
    
    支持两种模式：
    1. 命令行模式：直接调用BBDown二进制
    2. 服务模式：调用BBDown HTTP API (需要先启动 BBDown serve)
    """
    
    def __init__(
        self,
        output_dir: str = "data/downloads",
        bbdown_path: Optional[str] = None,
        serve_url: Optional[str] = None,
        cookie: Optional[str] = None,
    ):
        """
        初始化BBDown服务
        
        Args:
            output_dir: 下载输出目录
            bbdown_path: BBDown二进制路径（命令行模式）
            serve_url: BBDown服务地址（服务模式，如 http://localhost:12450）
            cookie: B站cookie (SESSDATA)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.bbdown_path = bbdown_path or self._find_bbdown()
        self.serve_url = serve_url
        self.cookie = cookie
        
        logger.info(
            "bbdown_service_init",
            mode="serve" if serve_url else "cli",
            bbdown_path=self.bbdown_path,
        )

    def _find_bbdown(self) -> Optional[str]:
        """查找BBDown二进制"""
        # 检查常见路径
        project_root = Path(__file__).parent.parent.parent
        paths = [
            str(project_root / "bin" / "BBDown"),  # 项目bin目录
            "BBDown",
            "./BBDown",
            "/usr/local/bin/BBDown",
            str(Path.home() / ".dotnet/tools/BBDown"),
        ]
        
        for path in paths:
            if Path(path).exists() or shutil.which(path):
                return path
        
        return None

    async def download_video(
        self,
        source_id: str,
        mode: DownloadMode = DownloadMode.AUDIO,
        with_subtitle: bool = True,
        quality: Optional[str] = None,
    ) -> DownloadResult:
        """
        下载视频/音频
        
        Args:
            source_id: BV号
            mode: 下载模式
            with_subtitle: 是否下载AI字幕
            quality: 画质优先级（如 "1080P 高码率"）
        
        Returns:
            DownloadResult
        """
        import time
        start_time = time.time()
        
        if self.serve_url:
            result = await self._download_via_api(source_id, mode, with_subtitle, quality)
        else:
            result = await self._download_via_cli(source_id, mode, with_subtitle, quality)
        
        result.duration = time.time() - start_time
        return result

    async def _download_via_cli(
        self,
        bvid: str,
        mode: DownloadMode,
        with_subtitle: bool,
        quality: Optional[str],
    ) -> DownloadResult:
        """通过命令行下载"""
        if not self.bbdown_path:
            return DownloadResult(success=False, error="BBDown not found")
        
        if not bvid.startswith("BV"):
            bvid = f"BV{bvid}"
        
        video_url = f"https://www.bilibili.com/video/{bvid}"
        work_dir = (self.output_dir / bvid).resolve()  # 使用绝对路径
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建命令
        cmd = [self.bbdown_path]
        
        # 模式选择
        if mode == DownloadMode.AUDIO:
            cmd.append("--audio-only")
        elif mode == DownloadMode.SUBTITLE:
            cmd.append("--sub-only")
        
        # AI字幕（默认跳过，需要移除skip-ai来启用）
        # 注意：BBDown默认--skip-ai是开启的，要下载AI字幕需要不加这个参数
        # 但BBDown的设计是默认跳过，所以我们检查with_subtitle来决定
        # 实际上需要查看BBDown的具体实现
        
        # 画质
        if quality:
            cmd.extend(["--dfn-priority", quality])
        
        # Cookie
        if self.cookie:
            cmd.extend(["-c", f"SESSDATA={self.cookie}"])
        
        # 工作目录和输出
        cmd.extend(["--work-dir", str(work_dir)])
        cmd.append(video_url)
        
        logger.info("bbdown_cli_start", bvid=bvid, cmd=" ".join(cmd[:5]) + "...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600,  # 10分钟超时
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error("bbdown_cli_failed", bvid=bvid, error=error_msg)
                return DownloadResult(success=False, error=error_msg)
            
            # 查找下载的文件
            file_path = self._find_downloaded_file(work_dir, mode)
            subtitle_path = self._find_subtitle_file(work_dir) if with_subtitle else None
            
            if not file_path and mode != DownloadMode.SUBTITLE:
                return DownloadResult(success=False, error="Downloaded file not found")
            
            logger.info(
                "bbdown_cli_complete",
                bvid=bvid,
                file_path=str(file_path) if file_path else None,
                subtitle_path=str(subtitle_path) if subtitle_path else None,
            )
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                subtitle_path=subtitle_path,
            )
            
        except asyncio.TimeoutError:
            logger.error("bbdown_cli_timeout", bvid=bvid)
            return DownloadResult(success=False, error="Download timeout")
        except Exception as e:
            logger.error("bbdown_cli_error", bvid=bvid, error=str(e))
            return DownloadResult(success=False, error=str(e))

    async def _download_via_api(
        self,
        bvid: str,
        mode: DownloadMode,
        with_subtitle: bool,
        quality: Optional[str],
    ) -> DownloadResult:
        """通过BBDown API下载"""
        if not self.serve_url:
            return DownloadResult(success=False, error="BBDown serve URL not configured")
        
        if not bvid.startswith("BV"):
            bvid = f"BV{bvid}"
        
        # 构建请求体
        payload = {
            "Url": bvid,
            "WorkDir": str(self.output_dir / bvid),
        }
        
        if mode == DownloadMode.AUDIO:
            payload["AudioOnly"] = True
        elif mode == DownloadMode.SUBTITLE:
            payload["SubOnly"] = True
        
        if quality:
            payload["DfnPriority"] = quality
        
        if self.cookie:
            payload["Cookie"] = f"SESSDATA={self.cookie}"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 添加任务
                resp = await client.post(
                    f"{self.serve_url}/add-task",
                    json=payload,
                )
                
                if resp.status_code != 200:
                    return DownloadResult(success=False, error=f"API error: {resp.text}")
                
                # 轮询等待完成
                for _ in range(120):  # 最多等待10分钟
                    await asyncio.sleep(5)
                    
                    status_resp = await client.get(f"{self.serve_url}/get-tasks")
                    if status_resp.status_code != 200:
                        continue
                    
                    tasks = status_resp.json()
                    finished = tasks.get("Finished", [])
                    
                    # 查找我们的任务
                    for task in finished:
                        if bvid in task.get("Url", ""):
                            if task.get("IsSuccessful"):
                                work_dir = self.output_dir / bvid
                                file_path = self._find_downloaded_file(work_dir, mode)
                                subtitle_path = self._find_subtitle_file(work_dir)
                                
                                return DownloadResult(
                                    success=True,
                                    file_path=file_path,
                                    subtitle_path=subtitle_path,
                                )
                            else:
                                return DownloadResult(success=False, error="Task failed")
                
                return DownloadResult(success=False, error="Timeout waiting for task")
                
        except Exception as e:
            logger.error("bbdown_api_error", bvid=bvid, error=str(e))
            return DownloadResult(success=False, error=str(e))

    def _find_downloaded_file(self, work_dir: Path, mode: DownloadMode) -> Optional[Path]:
        """查找下载的文件（递归搜索）"""
        if mode == DownloadMode.AUDIO:
            patterns = ["*.m4a", "*.aac", "*.mp3", "*.flac"]
        else:
            patterns = ["*.mp4", "*.mkv", "*.flv"]
        
        for pattern in patterns:
            # 递归搜索
            files = list(work_dir.rglob(pattern))
            if files:
                return files[0]
        
        return None

    def _find_subtitle_file(self, work_dir: Path) -> Optional[Path]:
        """查找字幕文件（递归搜索）"""
        patterns = ["*.srt", "*.ass", "*.vtt"]
        
        for pattern in patterns:
            # 递归搜索
            files = list(work_dir.rglob(pattern))
            if files:
                return files[0]
        
        return None

    async def get_ai_subtitle(self, bvid: str) -> Optional[SubtitleInfo]:
        """
        获取B站AI字幕
        
        Args:
            bvid: BV号
        
        Returns:
            SubtitleInfo 或 None
        """
        # 下载字幕
        result = await self.download_video(bvid, mode=DownloadMode.SUBTITLE, with_subtitle=True)
        
        if not result.success or not result.subtitle_path:
            return None
        
        try:
            content = result.subtitle_path.read_text(encoding="utf-8")
            return SubtitleInfo(
                content=content,
                language="zh",
                source="bilibili_ai",
            )
        except Exception as e:
            logger.error("subtitle_read_error", bvid=bvid, error=str(e))
            return None

    async def check_ai_subtitle_available(self, bvid: str) -> bool:
        """
        检查视频是否有AI字幕
        
        这需要解析B站API，暂时通过尝试下载来判断
        """
        # TODO: 直接调用B站API检查字幕可用性
        subtitle = await self.get_ai_subtitle(bvid)
        return subtitle is not None


# 单例
_bbdown_service: Optional[BBDownService] = None


def get_bbdown_service() -> BBDownService:
    """获取BBDown服务单例"""
    global _bbdown_service
    if _bbdown_service is None:
        config = get_config()
        _bbdown_service = BBDownService(
            output_dir="data/downloads",
            cookie=getattr(config, "bilibili_sessdata", None),
        )
    return _bbdown_service
