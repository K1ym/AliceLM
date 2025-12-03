"""
音频处理模块
整合自 exAudio.py
"""

import subprocess
from pathlib import Path
from typing import Optional

from packages.logging import get_logger

logger = get_logger(__name__)


class AudioProcessor:
    """音频处理器"""

    def __init__(self, output_dir: str = "data/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check_video_integrity(self, video_path: Path) -> bool:
        """使用FFmpeg验证视频文件完整性"""
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(video_path), "-f", "null", "-"],
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.stderr:
            logger.warning("video_integrity_issue", path=str(video_path), error=result.stderr)
            return False
        return True

    def extract_audio(self, video_path: Path, output_name: Optional[str] = None) -> Path:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_name: 输出文件名（不含扩展名）
            
        Returns:
            音频文件路径
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 检查视频完整性
        if not self.check_video_integrity(video_path):
            logger.warning("video_may_be_corrupted", path=str(video_path))

        # 输出文件名
        if output_name is None:
            output_name = video_path.stem
        
        audio_path = self.output_dir / f"{output_name}.mp3"

        logger.info("extracting_audio", video=str(video_path), audio=str(audio_path))

        # 使用ffmpeg提取音频（比moviepy更快更稳定）
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # 不要视频
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-ar", "16000",  # 16kHz采样率，适合语音识别
            "-y",  # 覆盖已存在的文件
            str(audio_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("audio_extraction_failed", error=result.stderr)
            raise Exception(f"音频提取失败: {result.stderr}")

        logger.info("audio_extracted", path=str(audio_path))
        return audio_path

    def get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 0.0
