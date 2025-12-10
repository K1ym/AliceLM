"""
数据库模型定义
"""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ============== 枚举类型 ==============

class TenantPlan(enum.Enum):
    """租户订阅计划"""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class UserRole(enum.Enum):
    """用户角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class VideoStatus(enum.Enum):
    """视频处理状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    INDEXING = "indexing"  # 向量化索引中
    DONE = "done"
    FAILED = "failed"


# ============== 租户与用户 ==============

class Tenant(Base):
    """租户/组织"""
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # 订阅计划
    plan: Mapped[TenantPlan] = mapped_column(Enum(TenantPlan), default=TenantPlan.FREE)
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 配额限制
    max_videos: Mapped[int] = mapped_column(Integer, default=100)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=10)
    max_users: Mapped[int] = mapped_column(Integer, default=1)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="tenant")
    configs: Mapped[List["TenantConfig"]] = relationship("TenantConfig", back_populates="tenant")
    watched_folders: Mapped[List["WatchedFolder"]] = relationship(
        "WatchedFolder", back_populates="tenant"
    )


class User(Base):
    """用户"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)

    # 基本信息
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 第三方绑定（微信保留，其他平台迁移到 UserPlatformBinding）
    wechat_openid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 角色与权限
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    learning_records: Mapped[List["LearningRecord"]] = relationship(
        "LearningRecord", back_populates="user"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", order_by="Conversation.updated_at.desc()"
    )
    platform_bindings: Mapped[List["UserPlatformBinding"]] = relationship(
        "UserPlatformBinding", back_populates="user"
    )


class UserPlatformBinding(Base):
    """用户平台绑定 - 存储各平台的认证凭证"""
    __tablename__ = "user_platform_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    platform: Mapped[str] = mapped_column(String(20))  # bilibili / youtube / podcast / ...
    platform_uid: Mapped[str] = mapped_column(String(100))
    credentials: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: token/sessdata/...

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="platform_bindings")

    __table_args__ = (
        UniqueConstraint("user_id", "platform", name="uq_user_platform"),
    )


class TenantConfig(Base):
    """租户配置"""
    __tablename__ = "tenant_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)

    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="configs")

    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_config"),)


class UserConfig(Base):
    """用户配置 - 个人AI设置"""
    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_config"),)


# ============== 视频与标签 ==============

class Video(Base):
    """视频"""
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)

    # 来源收藏夹（可选）
    watched_folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("watched_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # 内容源信息
    source_type: Mapped[str] = mapped_column(String(20), default="bilibili", index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)  # bvid / youtube_id / rss_guid / file_hash
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 内容元数据
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(100))
    duration: Mapped[int] = mapped_column(Integer, default=0)
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 处理状态（存储枚举的value而非name）
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # 文件路径
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transcript_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # AI生成内容
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concepts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 处理配置
    asr_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 时间戳
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="videos")
    watched_folder: Mapped[Optional["WatchedFolder"]] = relationship("WatchedFolder", back_populates="videos")
    tags: Mapped[List["VideoTag"]] = relationship("VideoTag", back_populates="video")

    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_id", name="uq_tenant_source"),
        Index("ix_tenant_status", "tenant_id", "status"),
        Index("ix_tenant_source_type", "tenant_id", "source_type"),
    )


class Tag(Base):
    """标签"""
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    videos: Mapped[List["VideoTag"]] = relationship("VideoTag", back_populates="tag")


class VideoTag(Base):
    """视频-标签关联"""
    __tablename__ = "video_tags"

    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    video: Mapped["Video"] = relationship("Video", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="videos")


# ============== 监控与学习 ==============

class WatchedFolder(Base):
    """监控的收藏夹"""
    __tablename__ = "watched_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)

    folder_id: Mapped[str] = mapped_column(String(50))
    folder_type: Mapped[str] = mapped_column(String(20))  # favlist / season / subscription
    name: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(20), default="bilibili")

    last_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="watched_folders")
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="watched_folder")

    __table_args__ = (UniqueConstraint("tenant_id", "folder_id", name="uq_tenant_folder"),)


class LearningRecord(Base):
    """学习记录（旧表，保留兼容）"""
    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"), index=True)

    action: Mapped[str] = mapped_column(String(20))  # viewed / asked / reviewed / exported
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON额外数据

    user: Mapped["User"] = relationship("User", back_populates="learning_records")


# ============== Timeline 系统 ==============

class EventType(enum.Enum):
    """时间线事件类型"""
    # 视频相关
    VIDEO_ADDED = "video_added"           # 新视频入库
    VIDEO_PROCESSED = "video_processed"   # 视频处理完成
    VIDEO_VIEWED = "video_viewed"         # 用户观看
    
    # 问答相关
    QUESTION_ASKED = "question_asked"     # 用户提问
    ANSWER_RECEIVED = "answer_received"   # 收到回答
    
    # 学习相关
    REVIEW_SCHEDULED = "review_scheduled" # 复习提醒
    REVIEW_COMPLETED = "review_completed" # 完成复习
    
    # 报告相关
    REPORT_GENERATED = "report_generated" # 生成报告/周报
    
    # 知识图谱相关
    CONCEPT_LEARNED = "concept_learned"   # 学到新概念
    CONCEPT_LINKED = "concept_linked"     # 概念关联
    
    # Agent 相关
    AGENT_RUN = "agent_run"               # Agent 执行任务
    TOOL_CALLED = "tool_called"           # 工具被调用
    
    # 系统相关
    USER_LOGIN = "user_login"             # 用户登录
    CONFIG_CHANGED = "config_changed"     # 配置变更


class SceneType(enum.Enum):
    """事件发生的场景"""
    CHAT = "chat"
    LIBRARY = "library"
    VIDEO = "video"
    GRAPH = "graph"
    TIMELINE = "timeline"
    TASKS = "tasks"
    CONSOLE = "console"
    SETTINGS = "settings"
    WECHAT = "wechat"
    MCP = "mcp"
    SYSTEM = "system"  # 后台任务


class TimelineEvent(Base):
    """
    统一时间线事件
    
    演进自 LearningRecord，增加 event_type / scene / context 字段，
    用于记录系统中所有重要事件，供 Alice One 构建用户画像和上下文。
    """
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # 事件类型与场景
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), index=True)
    scene: Mapped[SceneType] = mapped_column(Enum(SceneType), index=True)
    
    # 关联实体（可选）
    video_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("videos.id"), nullable=True, index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("conversations.id"), nullable=True)
    
    # 事件内容
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 事件简述
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON: 详细上下文
    
    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_timeline_tenant_user_time", "tenant_id", "user_id", "created_at"),
        Index("ix_timeline_tenant_type_time", "tenant_id", "event_type", "created_at"),
    )


# ============== Agent 执行记录 ==============

class AgentRunStatus(enum.Enum):
    """Agent 运行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(Base):
    """Agent 运行记录"""
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # 任务信息
    scene: Mapped[str] = mapped_column(String(50))
    query: Mapped[str] = mapped_column(Text)
    strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 状态
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus), default=AgentRunStatus.RUNNING)
    
    # 结果
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 任务规划JSON
    safety_level: Mapped[str] = mapped_column(String(20), default="normal")  # low/normal/high
    
    # Token 使用
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 总执行耗时(毫秒)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 错误码: LLM_ERROR/TOOL_ERROR/NETWORK_ERROR/...
    
    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    steps: Mapped[List["AgentStep"]] = relationship("AgentStep", back_populates="run", order_by="AgentStep.step_idx")


class AgentStep(Base):
    """Agent 执行步骤"""
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    
    step_idx: Mapped[int] = mapped_column(Integer)
    thought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_args: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="tool")  # tool/thought/confirm
    requires_user_confirm: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_trace_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ToolTrace 序列化 JSON
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 步骤执行耗时(毫秒)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="steps")


# ============== 对话系统 ==============

class MessageRole(enum.Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    """对话"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    # 对话信息
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 自动从首条消息生成
    
    # 上下文压缩
    compressed_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 压缩后的历史摘要
    compressed_at_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 压缩到哪条消息为止
    
    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )


class Message(Base):
    """对话消息"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )

    # 消息内容
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    
    # 引用来源（RAG检索结果）
    sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: [{video_id, chunk, score}]
    
    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
