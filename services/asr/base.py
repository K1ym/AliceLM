"""
ASR抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranscriptSegment:
    """转写片段"""
    start: float      # 开始时间（秒）
    end: float        # 结束时间（秒）
    text: str         # 转写文本


@dataclass
class TranscriptResult:
    """转写结果"""
    text: str                                    # 完整文本
    segments: List[TranscriptSegment] = field(default_factory=list)  # 分段信息
    language: str = "zh"                         # 检测到的语言
    duration: float = 0.0                        # 音频时长


class ASRProvider(ABC):
    """ASR提供者抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """
        执行转写
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码（可选，自动检测）
            prompt: 提示词（可选）
            
        Returns:
            转写结果
        """
        pass

    def is_available(self) -> bool:
        """检查是否可用"""
        return True
