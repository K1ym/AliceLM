"""
API ASR提供者
支持OpenAI兼容的语音识别API（如硅基流动、Groq等）
支持长音频自动分片处理
"""

import subprocess
import tempfile
import concurrent.futures
from pathlib import Path
from typing import Optional, List, Tuple

import httpx

from packages.logging import get_logger
from .base import ASRProvider, TranscriptResult, TranscriptSegment

logger = get_logger(__name__)

# 分片配置
CHUNK_DURATION_SECONDS = 600  # 10分钟
CHUNK_OVERLAP_SECONDS = 2     # 片段重叠，避免切断句子
MAX_PARALLEL_CHUNKS = 3       # 最大并行处理数


class APIASRProvider(ASRProvider):
    """OpenAI兼容API的ASR提供者"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "whisper-1",
    ):
        """
        初始化API ASR提供者
        
        Args:
            base_url: API地址（如 https://api.siliconflow.cn/v1）
            api_key: API密钥
            model: 模型名称
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @property
    def name(self) -> str:
        return "api"

    def _convert_to_mp3(self, audio_path: str) -> str:
        """将音频转换为mp3格式（如果需要）"""
        path = Path(audio_path)
        supported_formats = {".mp3", ".wav", ".pcm", ".opus", ".webm"}
        
        if path.suffix.lower() in supported_formats:
            return audio_path
        
        # 转换为mp3
        mp3_path = path.with_suffix(".mp3")
        if mp3_path.exists():
            return str(mp3_path)
        
        logger.info("converting_audio_to_mp3", src=audio_path, dst=str(mp3_path))
        
        try:
            subprocess.run(
                ["ffmpeg", "-i", audio_path, "-acodec", "libmp3lame", "-q:a", "2", str(mp3_path), "-y"],
                check=True,
                capture_output=True,
            )
            return str(mp3_path)
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg_convert_failed", error=e.stderr.decode() if e.stderr else str(e))
            raise RuntimeError(f"音频格式转换失败: {e}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True,
                text=True,
                check=True,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning("ffprobe_duration_failed", error=str(e), audio_path=audio_path)
            return 0.0

    def _split_audio(self, audio_path: str, chunk_duration: int = CHUNK_DURATION_SECONDS) -> List[Tuple[str, float]]:
        """
        将音频切分为多个片段
        
        Returns:
            List of (chunk_path, start_time) tuples
        """
        duration = self._get_audio_duration(audio_path)
        if duration <= chunk_duration:
            return [(audio_path, 0.0)]
        
        chunks = []
        path = Path(audio_path)
        chunk_dir = path.parent / f"{path.stem}_chunks"
        chunk_dir.mkdir(exist_ok=True)
        
        start = 0.0
        chunk_idx = 0
        
        while start < duration:
            chunk_path = chunk_dir / f"chunk_{chunk_idx:03d}.mp3"
            
            # 使用 ffmpeg 切分
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ss", str(start),
                "-t", str(chunk_duration + CHUNK_OVERLAP_SECONDS),
                "-acodec", "libmp3lame",
                "-q:a", "2",
                str(chunk_path),
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                chunks.append((str(chunk_path), start))
                logger.debug("audio_chunk_created", chunk=chunk_idx, start=start, path=str(chunk_path))
            except subprocess.CalledProcessError as e:
                logger.error("audio_split_failed", chunk=chunk_idx, error=e.stderr.decode() if e.stderr else str(e))
                raise RuntimeError(f"音频分片失败: {e}")
            
            start += chunk_duration
            chunk_idx += 1
        
        logger.info("audio_split_complete", total_chunks=len(chunks), duration=duration)
        return chunks

    def _transcribe_chunk(self, chunk_info: Tuple[str, float], language: Optional[str], prompt: Optional[str]) -> Tuple[float, TranscriptResult]:
        """转写单个音频片段"""
        chunk_path, start_offset = chunk_info
        result = self._transcribe_single(chunk_path, language, prompt)
        return start_offset, result

    def _merge_transcripts(self, results: List[Tuple[float, TranscriptResult]]) -> TranscriptResult:
        """合并多个转写结果，调整时间戳"""
        # 按开始时间排序
        results.sort(key=lambda x: x[0])
        
        all_segments = []
        all_text_parts = []
        total_duration = 0.0
        detected_language = "zh"
        
        for start_offset, result in results:
            # 调整每个 segment 的时间戳
            for seg in result.segments:
                adjusted_seg = TranscriptSegment(
                    start=seg.start + start_offset,
                    end=seg.end + start_offset,
                    text=seg.text,
                )
                all_segments.append(adjusted_seg)
            
            all_text_parts.append(result.text)
            
            if result.duration > 0:
                total_duration = max(total_duration, start_offset + result.duration)
            
            if result.language:
                detected_language = result.language
        
        # 去除重叠部分的重复文本
        merged_segments = self._deduplicate_segments(all_segments)
        
        return TranscriptResult(
            text=" ".join(all_text_parts),
            segments=merged_segments,
            language=detected_language,
            duration=total_duration,
        )

    def _deduplicate_segments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """去除因重叠导致的重复片段"""
        if not segments:
            return []
        
        # 按开始时间排序
        segments.sort(key=lambda s: s.start)
        
        deduped = [segments[0]]
        for seg in segments[1:]:
            last = deduped[-1]
            # 如果当前片段开始时间在上一个片段结束之后，直接添加
            if seg.start >= last.end - 0.5:  # 0.5秒容差
                deduped.append(seg)
            # 否则检查是否为重复内容
            elif seg.text.strip() != last.text.strip():
                # 不同内容，调整开始时间后添加
                adjusted = TranscriptSegment(
                    start=max(seg.start, last.end),
                    end=seg.end,
                    text=seg.text,
                )
                if adjusted.start < adjusted.end:
                    deduped.append(adjusted)
        
        return deduped

    def _transcribe_single(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """转写单个音频文件（不分片）"""
        url = f"{self.base_url}/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        data = {
            "model": self.model,
            "response_format": "verbose_json",
        }
        
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt
        
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (Path(audio_path).name, f, "audio/mpeg")}
                
                with httpx.Client(timeout=300.0) as client:
                    response = client.post(
                        url,
                        headers=headers,
                        data=data,
                        files=files,
                    )
            
            if response.status_code != 200:
                logger.error(
                    "api_asr_failed",
                    status=response.status_code,
                    error=response.text,
                )
                raise Exception(f"API ASR失败: {response.text}")
            
            result = response.json()
            
            segments = []
            if "segments" in result:
                for seg in result["segments"]:
                    segments.append(TranscriptSegment(
                        start=seg.get("start", 0),
                        end=seg.get("end", 0),
                        text=seg.get("text", ""),
                    ))
            
            return TranscriptResult(
                text=result.get("text", ""),
                segments=segments,
                language=result.get("language", "zh"),
                duration=result.get("duration", 0.0),
            )
            
        except httpx.TimeoutException:
            logger.error("api_asr_timeout", audio_path=audio_path)
            raise Exception("API ASR超时")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """
        使用API进行转写，自动处理长音频分片
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            prompt: 提示词
        """
        # 转换为支持的格式
        audio_path = self._convert_to_mp3(audio_path)
        
        # 检查是否需要分片
        duration = self._get_audio_duration(audio_path)
        
        if duration <= CHUNK_DURATION_SECONDS:
            # 短音频，直接处理
            logger.info("asr_direct_transcribe", duration=duration, audio_path=audio_path)
            try:
                result = self._transcribe_single(audio_path, language, prompt)
                logger.info(
                    "api_asr_complete",
                    model=self.model,
                    duration=result.duration,
                    text_length=len(result.text),
                )
                return result
            except Exception as e:
                logger.error("api_asr_error", error=str(e))
                raise
        
        # 长音频，分片处理
        logger.info("asr_chunked_transcribe", duration=duration, chunk_size=CHUNK_DURATION_SECONDS)
        
        try:
            chunks = self._split_audio(audio_path)
            results: List[Tuple[float, TranscriptResult]] = []
            
            # 并行处理分片
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_CHUNKS) as executor:
                futures = {
                    executor.submit(self._transcribe_chunk, chunk, language, prompt): chunk
                    for chunk in chunks
                }
                
                for future in concurrent.futures.as_completed(futures):
                    chunk = futures[future]
                    try:
                        start_offset, result = future.result()
                        results.append((start_offset, result))
                        logger.info(
                            "chunk_transcribe_complete",
                            chunk_start=start_offset,
                            text_length=len(result.text),
                        )
                    except Exception as e:
                        logger.error("chunk_transcribe_failed", chunk=chunk[0], error=str(e))
                        raise
            
            # 合并结果
            transcript = self._merge_transcripts(results)
            
            logger.info(
                "api_asr_complete",
                model=self.model,
                duration=transcript.duration,
                text_length=len(transcript.text),
                chunks=len(chunks),
            )
            
            return transcript
            
        except Exception as e:
            logger.error("api_asr_error", error=str(e))
            raise

    def is_available(self) -> bool:
        """检查API是否可用"""
        return bool(self.api_key and self.base_url)


def create_api_asr(base_url: str, api_key: str, model: str) -> APIASRProvider:
    """
    创建API ASR提供者
    
    Args:
        base_url: API地址
        api_key: API密钥
        model: 模型名称
    
    Returns:
        APIASRProvider实例
    """
    return APIASRProvider(base_url=base_url, api_key=api_key, model=model)
