"""
Stage S1: Alice One 模块测试
"""

import pytest


class TestAliceOneStructure:
    """S1: Alice One 结构测试"""

    def test_timeline_service_import(self):
        """验证 TimelineService 可导入"""
        from alice.one import TimelineService, TimelineEventDTO, record_event
        
        # TimelineService 需要 db session，这里只验证导入
        assert TimelineService is not None
        assert record_event is not None

    def test_identity_service_import(self):
        """验证 AliceIdentityService 可导入"""
        from alice.one import (
            AliceIdentityService,
            AliceIdentity,
            AlicePersona,
            get_alice_identity,
        )
        
        assert AliceIdentityService is not None
        assert get_alice_identity is not None

    def test_context_assembler_import(self):
        """验证 ContextAssembler 可导入"""
        from alice.one import (
            ContextAssembler,
            AssembledContext,
            ContextCitation,
            assemble_context,
        )
        
        assert ContextAssembler is not None
        assert assemble_context is not None


class TestAlicePersona:
    """AlicePersona 测试"""

    def test_default_persona(self):
        """验证默认人格配置"""
        from alice.one import AlicePersona
        
        persona = AlicePersona()
        assert persona.name == "Alice"
        assert persona.style == "friendly"
        assert persona.language == "zh-CN"

    def test_custom_persona(self):
        """验证自定义人格配置"""
        from alice.one import AlicePersona
        
        persona = AlicePersona(
            name="小艾",
            description="专业的学习教练",
            style="coach",
            custom_instructions="请多用提问引导用户思考",
        )
        
        assert persona.name == "小艾"
        assert persona.style == "coach"
        assert "提问" in persona.custom_instructions


class TestTimelineModels:
    """Timeline 数据模型测试"""

    def test_event_type_enum(self):
        """验证 EventType 枚举"""
        from packages.db.models import EventType
        
        assert EventType.VIDEO_ADDED.value == "video_added"
        assert EventType.QUESTION_ASKED.value == "question_asked"
        assert EventType.AGENT_RUN.value == "agent_run"

    def test_scene_type_enum(self):
        """验证 SceneType 枚举"""
        from packages.db.models import SceneType
        
        assert SceneType.CHAT.value == "chat"
        assert SceneType.LIBRARY.value == "library"
        assert SceneType.CONSOLE.value == "console"


class TestAgentRunModels:
    """AgentRun 数据模型测试"""

    def test_agent_run_status_enum(self):
        """验证 AgentRunStatus 枚举"""
        from packages.db.models import AgentRunStatus
        
        assert AgentRunStatus.RUNNING.value == "running"
        assert AgentRunStatus.COMPLETED.value == "completed"
        assert AgentRunStatus.FAILED.value == "failed"


class TestContextCitation:
    """ContextCitation 测试"""

    def test_context_citation_creation(self):
        """验证 ContextCitation 可创建"""
        from alice.one import ContextCitation
        
        citation = ContextCitation(
            type="video",
            id="123",
            title="测试视频",
            snippet="这是一段视频内容...",
            url="/video/123",
        )
        
        assert citation.type == "video"
        assert citation.id == "123"
        assert citation.title == "测试视频"


class TestTimelineEventDTO:
    """TimelineEventDTO 测试"""

    def test_timeline_event_dto_creation(self):
        """验证 TimelineEventDTO 可创建"""
        from datetime import datetime
        from alice.one import TimelineEventDTO
        
        event = TimelineEventDTO(
            id=1,
            tenant_id=1,
            user_id=1,
            event_type="video_processed",
            scene="system",
            video_id=123,
            conversation_id=None,
            title="视频处理完成",
            context={"duration": 120},
            created_at=datetime.utcnow(),
        )
        
        assert event.event_type == "video_processed"
        assert event.video_id == 123
        assert event.context["duration"] == 120
