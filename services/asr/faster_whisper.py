"""
Faster-Whisper ASR实现
使用CTranslate2优化，速度更快
"""

from typing import Optional

from packages.logging import get_logger

from .base import ASRProvider, TranscriptResult, TranscriptSegment

logger = get_logger(__name__)


class FasterWhisperProvider(ASRProvider):
    """Faster-Whisper模型（推荐）"""

    name = "faster_whisper"

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        compute_type: str = "float16",
    ):
        """
        初始化Faster-Whisper模型
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large-v2/large-v3)
            device: 设备 (auto/cpu/cuda)
            compute_type: 计算类型 (float16/int8/int8_float16)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            from faster_whisper import WhisperModel
            
            # 确定设备
            if self.device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            else:
                device = self.device

            # CPU不支持float16
            compute_type = self.compute_type
            if device == "cpu" and compute_type == "float16":
                compute_type = "int8"

            logger.info(
                "loading_faster_whisper",
                model=self.model_size,
                device=device,
                compute_type=compute_type,
            )

            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
            )

            logger.info("faster_whisper_loaded", model=self.model_size)

        return self._model

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """执行转写"""
        model = self._load_model()

        # 默认提示词
        if prompt is None:
            prompt = "以下是普通话的句子。"

        logger.info("transcribing", audio=audio_path, model=self.model_size)

        # 转写
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            initial_prompt=prompt,
            vad_filter=True,  # 使用VAD过滤静音
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # 收集结果
        segments = []
        full_text = []

        for seg in segments_iter:
            segments.append(TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            ))
            full_text.append(seg.text.strip())

        duration = segments[-1].end if segments else 0.0

        transcript = TranscriptResult(
            text=" ".join(full_text),
            segments=segments,
            language=info.language,
            duration=duration,
        )

        logger.info(
            "transcription_complete",
            audio=audio_path,
            text_length=len(transcript.text),
            segments=len(segments),
            language=info.language,
        )

        return transcript

    def is_available(self) -> bool:
        """检查faster-whisper是否可用"""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False
