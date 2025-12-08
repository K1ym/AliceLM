"""
Control Plane 共享类型定义
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ModelKind(str, Enum):
    """模型类型"""
    CHAT = "chat"
    EMBEDDING = "embedding"
    ASR = "asr"
    TTS = "tts"
    RERANK = "rerank"


class ModelProfile(BaseModel):
    """模型配置单元"""
    id: str
    kind: str
    provider: str
    model: str
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    embedding_dim: Optional[int] = None
    description: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class ResolvedModel(BaseModel):
    """解析后的模型信息（给调用方使用）"""
    profile_id: str
    provider: str
    model: str
    kind: str
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    embedding_dim: Optional[int] = None
    
    # 运行时配置（从 tenant/user 配置合并）
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class ToolConfig(BaseModel):
    """工具配置"""
    name: str
    impl: str
    enabled: bool = True
    unsafe: bool = False
    scenes: List[str] = []
    description: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class ServiceConfig(BaseModel):
    """服务配置"""
    provider: str
    fallback: Optional[str] = None
    config: Dict[str, Any] = {}


class ProviderConfig(BaseModel):
    """Provider 实现配置"""
    impl: str
    config: Dict[str, Any] = {}


@dataclass
class ControlPlaneConfig:
    """控制平面配置集合"""
    model_profiles: Dict[str, ModelProfile] = field(default_factory=dict)
    task_defaults: Dict[str, str] = field(default_factory=dict)
    prompts: Dict[str, str] = field(default_factory=dict)
    tools: List[ToolConfig] = field(default_factory=list)
    scene_defaults: Dict[str, List[str]] = field(default_factory=dict)
    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
