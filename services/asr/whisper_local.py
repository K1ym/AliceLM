"""
本地Whisper ASR实现
整合自 speech2text.py
"""

import platform
from typing import Optional

from packages.logging import get_logger

from .base import ASRProvider, TranscriptResult, TranscriptSegment

logger = get_logger(__name__)


class WhisperLocalProvider(ASRProvider):
    """本地Whisper模型"""

    name = "whisper_local"

    def __init__(self, model_size: str = "medium", device: str = "auto"):
        """
        初始化Whisper模型
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large)
            device: 设备 (auto/cpu/cuda/mps)
        """
        self.model_size = model_size
        self.device = device
        self._model = None

    def _get_device(self) -> str:
        """确定使用的设备"""
        if self.device != "auto":
            return self.device

        try:
            import torch
            
            # Apple Silicon
            if platform.system() == "Darwin" and hasattr(torch.backends, "mps"):
                if torch.backends.mps.is_available():
                    # Whisper在MPS上可能不稳定，暂用CPU
                    return "cpu"
            
            # CUDA
            if torch.cuda.is_available():
                return "cuda"
            
            return "cpu"
        except ImportError:
            return "cpu"

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            import whisper
            
            device = self._get_device()
            logger.info("loading_whisper", model=self.model_size, device=device)
            
            self._model = whisper.load_model(self.model_size, device=device)
            
            logger.info("whisper_loaded", model=self.model_size, device=device)
        
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

        # 转写选项
        options = {
            "initial_prompt": prompt,
            "verbose": False,
        }
        if language:
            options["language"] = language

        result = model.transcribe(audio_path, **options)

        # 构建结果
        segments = [
            TranscriptSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
            )
            for seg in result.get("segments", [])
        ]

        duration = segments[-1].end if segments else 0.0

        transcript = TranscriptResult(
            text=result["text"].strip(),
            segments=segments,
            language=result.get("language", "zh"),
            duration=duration,
        )

        logger.info(
            "transcription_complete",
            audio=audio_path,
            text_length=len(transcript.text),
            segments=len(segments),
        )

        return transcript

    def is_available(self) -> bool:
        """检查whisper是否可用"""
        try:
            import whisper
            return True
        except ImportError:
            return False
