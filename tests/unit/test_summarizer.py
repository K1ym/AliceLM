"""
services.ai.summarizer 单元测试
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.ai.llm import LLMManager, LLMResponse
from services.ai.summarizer import Summarizer, VideoAnalysis


class TestSummarizer:
    """测试 Summarizer"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM Manager"""
        llm = MagicMock(spec=LLMManager)
        llm.chat.return_value = LLMResponse(
            content='{"summary": "这是摘要", "key_points": ["观点1", "观点2"], "concepts": ["概念1"], "tags": ["标签1"]}',
            model="gpt-4",
            usage={"total_tokens": 100},
            finish_reason="stop",
        )
        llm.chat_async = AsyncMock(return_value=LLMResponse(
            content='{"summary": "异步摘要", "key_points": ["观点1"], "concepts": [], "tags": []}',
            model="gpt-4",
            usage={"total_tokens": 50},
            finish_reason="stop",
        ))
        return llm
    
    def test_init_with_llm_manager(self, mock_llm):
        """使用提供的 LLM Manager 初始化"""
        summarizer = Summarizer(llm_manager=mock_llm)
        assert summarizer.llm == mock_llm
    
    def test_analyze_returns_video_analysis(self, mock_llm):
        """analyze 返回 VideoAnalysis"""
        summarizer = Summarizer(llm_manager=mock_llm)
        
        result = summarizer.analyze(
            transcript="这是一段视频内容...",
            title="测试视频",
            author="测试作者",
            duration=300,
        )
        
        assert isinstance(result, VideoAnalysis)
        assert result.summary == "这是摘要"
        assert len(result.key_points) == 2
    
    def test_analyze_truncates_long_transcript(self, mock_llm):
        """长文本应被截断"""
        summarizer = Summarizer(llm_manager=mock_llm)
        
        # 创建超长文本
        long_transcript = "a" * 20000
        
        result = summarizer.analyze(
            transcript=long_transcript,
            title="长视频",
        )
        
        # 检查调用时文本已被截断
        call_args = mock_llm.chat.call_args
        messages = call_args[0][0]
        user_message = [m for m in messages if m.role == "user"][0]
        assert len(user_message.content) < 20000
    
    def test_has_analyze_async_method(self, mock_llm):
        """应有 analyze_async 方法"""
        summarizer = Summarizer(llm_manager=mock_llm)
        assert hasattr(summarizer, 'analyze_async')
        assert callable(summarizer.analyze_async)
    
    def test_analyze_async(self, mock_llm):
        """测试异步分析（同步执行 async 以避免插件依赖）"""
        summarizer = Summarizer(llm_manager=mock_llm)

        result = asyncio.run(
            summarizer.analyze_async(
                transcript="视频内容",
                title="测试",
            )
        )

        assert isinstance(result, VideoAnalysis)
        assert result.summary == "异步摘要"


class TestVideoAnalysis:
    """测试 VideoAnalysis"""
    
    def test_default_values(self):
        """默认值"""
        analysis = VideoAnalysis(
            summary="摘要",
            key_points=["观点1"],
        )
        assert analysis.concepts == []
        assert analysis.tags == []
        assert analysis.language == "zh"
    
    def test_all_fields(self):
        """所有字段"""
        analysis = VideoAnalysis(
            summary="摘要",
            key_points=["观点1", "观点2"],
            concepts=["概念1"],
            tags=["标签1", "标签2"],
            language="en",
        )
        assert len(analysis.key_points) == 2
        assert len(analysis.concepts) == 1
        assert analysis.language == "en"
