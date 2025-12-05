"""
Alice One - 身份与上下文层

核心组件：
- AliceIdentityService: Alice 人格与工具配置
- TimelineService: 统一时间线服务
- ContextAssembler: 上下文组装器
"""

from .identity import (
    AliceIdentityService,
    AliceIdentity,
    AlicePersona,
    get_alice_identity,
)
from .timeline import (
    TimelineService,
    TimelineEventDTO,
    record_event,
)
from .context import (
    ContextAssembler,
    AssembledContext,
    ContextCitation,
    assemble_context,
)
from .entrypoints import (
    handle_chat_request,
    handle_qa_request,
    handle_video_chat_request,
    handle_console_request,
)

__all__ = [
    # Identity
    "AliceIdentityService",
    "AliceIdentity",
    "AlicePersona",
    "get_alice_identity",
    # Timeline
    "TimelineService",
    "TimelineEventDTO",
    "record_event",
    # Context
    "ContextAssembler",
    "AssembledContext",
    "ContextCitation",
    "assemble_context",
    # Entrypoints
    "handle_chat_request",
    "handle_qa_request",
    "handle_video_chat_request",
    "handle_console_request",
]
