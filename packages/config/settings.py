"""
配置管理系统
支持YAML配置 + 环境变量覆盖
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(default="sqlite:///data/bili_learner.db")
    echo: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_prefix="ALICE_DB_")


class ASRSettings(BaseSettings):
    """ASR配置"""
    provider: str = Field(default="faster_whisper")
    model_size: str = Field(default="medium")
    device: str = Field(default="auto")
    
    model_config = SettingsConfigDict(env_prefix="ALICE_ASR_")


class LLMSettings(BaseSettings):
    """LLM配置"""
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    api_key: str = Field(default="")
    base_url: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(env_prefix="ALICE_LLM_")


class RAGSettings(BaseSettings):
    """RAG配置"""
    provider: str = Field(default="chroma")  # chroma / ragflow
    base_url: str = Field(default="http://localhost:9380")  # RAGFlow URL
    api_key: str = Field(default="")
    chroma_persist_dir: str = Field(default="data/chroma")  # ChromaDB 数据目录
    
    model_config = SettingsConfigDict(env_prefix="ALICE_RAG_")


class WeChatSettings(BaseSettings):
    """微信通知配置"""
    webhook_url: str = Field(default="")
    corp_id: str = Field(default="")
    agent_id: str = Field(default="")
    secret: str = Field(default="")
    enabled: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_prefix="ALICE_WECHAT_")


class BilibiliSettings(BaseSettings):
    """B站配置"""
    sessdata: str = Field(default="")
    poll_interval: int = Field(default=300)  # 秒
    
    model_config = SettingsConfigDict(env_prefix="ALICE_BILI_")


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
    
    model_config = SettingsConfigDict(
        env_prefix="ALICE_",
        env_nested_delimiter="__",
    )


def load_yaml_config(config_path: str) -> dict[str, Any]:
    """加载单个YAML配置文件"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def deep_merge(base: dict, override: dict) -> dict:
    """深度合并配置字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_layered_config(config_dir: str = "config", env: Optional[str] = None) -> dict[str, Any]:
    """
    分层加载配置
    
    加载顺序: base → {env} → local → 环境变量
    后加载的覆盖先加载的
    
    Args:
        config_dir: 配置目录
        env: 环境名称 (dev/prod)，默认从 ALICE_ENV 读取
    """
    config_path = Path(config_dir)
    env = env or os.getenv("ALICE_ENV", "dev")
    
    # 1. 加载 base 配置
    config = load_yaml_config(config_path / "base" / "default.yaml")
    
    # 2. 加载环境配置
    env_config = load_yaml_config(config_path / env / "default.yaml")
    config = deep_merge(config, env_config)
    
    # 3. 加载 local 配置（不提交到 git）
    local_config = load_yaml_config(config_path / "local" / "default.yaml")
    config = deep_merge(config, local_config)
    
    return config


def get_settings(config_dir: str = "config", env: Optional[str] = None) -> Settings:
    """获取配置实例，支持分层YAML + ENV"""
    # 加载分层配置
    yaml_config = load_layered_config(config_dir, env)
    
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


def reset_config():
    """重置配置（用于测试）"""
    global _settings
    _settings = None

