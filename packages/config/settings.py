"""
配置管理系统
支持YAML配置 + 环境变量覆盖
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(default="sqlite:///data/bili_learner.db")
    echo: bool = Field(default=False)
    
    class Config:
        env_prefix = "ALICE_DB_"


class ASRSettings(BaseSettings):
    """ASR配置"""
    provider: str = Field(default="faster_whisper")
    model_size: str = Field(default="medium")
    device: str = Field(default="auto")
    
    class Config:
        env_prefix = "ALICE_ASR_"


class LLMSettings(BaseSettings):
    """LLM配置"""
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    api_key: str = Field(default="")
    base_url: Optional[str] = Field(default=None)
    
    class Config:
        env_prefix = "ALICE_LLM_"


class RAGSettings(BaseSettings):
    """RAG配置"""
    provider: str = Field(default="ragflow")
    base_url: str = Field(default="http://localhost:9380")
    api_key: str = Field(default="")
    
    class Config:
        env_prefix = "ALICE_RAG_"


class WeChatSettings(BaseSettings):
    """微信通知配置"""
    webhook_url: str = Field(default="")
    corp_id: str = Field(default="")
    agent_id: str = Field(default="")
    secret: str = Field(default="")
    enabled: bool = Field(default=False)
    
    class Config:
        env_prefix = "ALICE_WECHAT_"


class BilibiliSettings(BaseSettings):
    """B站配置"""
    sessdata: str = Field(default="")
    poll_interval: int = Field(default=300)  # 秒
    
    class Config:
        env_prefix = "ALICE_BILI_"


class Settings(BaseSettings):
    """主配置"""
    app_name: str = Field(default="AliceLM")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production")
    
    # 子配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    asr: ASRSettings = Field(default_factory=ASRSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    wechat: WeChatSettings = Field(default_factory=WeChatSettings)
    bilibili: BilibiliSettings = Field(default_factory=BilibiliSettings)
    
    class Config:
        env_prefix = "ALICE_"
        env_nested_delimiter = "__"


def load_yaml_config(config_path: str = "config/default.yaml") -> dict[str, Any]:
    """加载YAML配置文件"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_settings(config_path: Optional[str] = None) -> Settings:
    """获取配置实例，支持YAML + ENV"""
    # 加载YAML配置
    yaml_config = {}
    if config_path:
        yaml_config = load_yaml_config(config_path)
    elif Path("config/default.yaml").exists():
        yaml_config = load_yaml_config("config/default.yaml")
    
    # 创建Settings实例（环境变量会自动覆盖）
    return Settings(**yaml_config)


# 全局配置实例
_settings: Optional[Settings] = None


def get_config() -> Settings:
    """获取全局配置"""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings
