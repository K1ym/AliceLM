"""
配置管理路由
支持用户级别的配置读写
"""

import json
import httpx
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import User, UserConfig
from packages.logging import get_logger

from ..deps import get_db, get_current_user

router = APIRouter()
logger = get_logger(__name__)


# ========== Schemas ==========

class ASRConfig(BaseModel):
    """ASR配置"""
    provider: str = Field(default="faster_whisper", description="ASR提供商")
    # 本地模型配置
    model_size: str = Field(default="medium", description="本地模型大小")
    device: str = Field(default="auto", description="设备")
    # 外接API配置
    api_base_url: Optional[str] = Field(default=None, description="API地址")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_model: Optional[str] = Field(default=None, description="API模型名")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    base_url: Optional[str] = Field(default=None, description="API地址")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    endpoint_id: Optional[str] = Field(default=None, description="自定义端点ID")


class LLMEndpoint(BaseModel):
    """用户自定义的LLM端点"""
    id: str = Field(description="端点ID")
    name: str = Field(description="显示名称")
    base_url: str = Field(description="API地址")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    models: List[str] = Field(default_factory=list, description="可用模型列表")


class LLMEndpointCreate(BaseModel):
    """创建LLM端点"""
    name: str
    base_url: str
    api_key: str


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    type: str  # chat/embedding/audio


class LLMEndpointResponse(BaseModel):
    """端点响应"""
    id: str
    name: str
    base_url: str
    has_api_key: bool
    models: List[str]
    models_with_type: List[ModelInfo] = []  # 带类型的模型列表


class NotifyConfig(BaseModel):
    """通知配置"""
    wechat_enabled: bool = Field(default=False)
    webhook_url: Optional[str] = Field(default=None)


class ASRConfigResponse(BaseModel):
    """ASR配置响应"""
    provider: str
    model_size: str
    device: str
    api_base_url: Optional[str] = None
    has_api_key: bool = False
    api_model: Optional[str] = None


class LLMConfigResponse(BaseModel):
    """LLM配置响应"""
    provider: str
    model: str
    base_url: Optional[str] = None
    has_api_key: bool = False
    endpoint_id: Optional[str] = None  # 当前使用的自定义端点ID


# 模型类型
class ModelType:
    CHAT = "chat"           # 聊天/对话模型
    EMBEDDING = "embedding" # 向量化模型
    AUDIO = "audio"         # 音频模型

# 模型任务类型及其所需的模型类型
MODEL_TASK_REQUIRED_TYPES = {
    "chat": ModelType.CHAT,
    "summary": ModelType.CHAT,
    "knowledge": ModelType.CHAT,
    "mindmap": ModelType.CHAT,
    "tagger": ModelType.CHAT,
    "context_compress": ModelType.CHAT,  # 上下文压缩
    "asr": ModelType.AUDIO,
    "embedding": ModelType.EMBEDDING,
}

# 根据模型名称推断类型的规则
def infer_model_type(model_id: str) -> str:
    """根据模型ID推断模型类型"""
    model_lower = model_id.lower()
    
    # Embedding模型
    if any(kw in model_lower for kw in ["embed", "bge", "e5-", "gte-", "text-embedding", "jina"]):
        return ModelType.EMBEDDING
    
    # 音频模型 (ASR/TTS)
    if any(kw in model_lower for kw in ["whisper", "speech", "audio", "tts", "sensevoice", "funasr", "paraformer"]):
        return ModelType.AUDIO
    
    # 默认为聊天模型
    return ModelType.CHAT


class ModelTaskConfig(BaseModel):
    """单个任务的模型配置"""
    endpoint_id: Optional[str] = None  # 使用的端点ID，None表示使用预设
    model: str                         # 模型名称
    # 预设提供商配置（当endpoint_id为空时使用）
    provider: Optional[str] = None
    base_url: Optional[str] = None


class ModelTasksConfig(BaseModel):
    """所有任务的模型配置"""
    chat: Optional[ModelTaskConfig] = None
    summary: Optional[ModelTaskConfig] = None
    knowledge: Optional[ModelTaskConfig] = None
    mindmap: Optional[ModelTaskConfig] = None
    tagger: Optional[ModelTaskConfig] = None
    context_compress: Optional[ModelTaskConfig] = None
    asr: Optional[ModelTaskConfig] = None
    embedding: Optional[ModelTaskConfig] = None


class ModelTasksResponse(BaseModel):
    """任务模型配置响应"""
    chat: Optional[ModelTaskConfig] = None
    summary: Optional[ModelTaskConfig] = None
    knowledge: Optional[ModelTaskConfig] = None
    mindmap: Optional[ModelTaskConfig] = None
    tagger: Optional[ModelTaskConfig] = None
    context_compress: Optional[ModelTaskConfig] = None
    asr: Optional[ModelTaskConfig] = None
    embedding: Optional[ModelTaskConfig] = None


class ConfigResponse(BaseModel):
    """配置响应"""
    asr: ASRConfigResponse
    llm: LLMConfigResponse
    notify: NotifyConfig
    llm_endpoints: List[LLMEndpointResponse] = []  # 用户自定义端点列表
    model_tasks: ModelTasksResponse = ModelTasksResponse()  # 任务模型配置


class ConfigUpdateResponse(BaseModel):
    """配置更新响应"""
    success: bool
    message: str


# ========== Helper Functions ==========

def get_user_config(db: Session, user_id: int, key: str) -> Optional[str]:
    """获取用户配置"""
    config = (
        db.query(UserConfig)
        .filter(UserConfig.user_id == user_id, UserConfig.key == key)
        .first()
    )
    return config.value if config else None


def set_user_config(db: Session, user_id: int, key: str, value: str) -> None:
    """设置用户配置"""
    config = (
        db.query(UserConfig)
        .filter(UserConfig.user_id == user_id, UserConfig.key == key)
        .first()
    )
    
    if config:
        config.value = value
    else:
        config = UserConfig(user_id=user_id, key=key, value=value)
        db.add(config)
    
    db.commit()


def get_config_dict(db: Session, user_id: int, prefix: str) -> dict:
    """获取配置字典"""
    raw = get_user_config(db, user_id, prefix)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {}


def get_task_llm_config(db: Session, user_id: int, task_type: str) -> dict:
    """
    获取特定任务的LLM配置
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        task_type: 任务类型 (chat/summary/knowledge/mindmap/tagger)
    
    Returns:
        dict: {"base_url": str, "api_key": str, "model": str}
    """
    # 获取任务模型配置
    tasks_config = get_config_dict(db, user_id, "model_tasks")
    task_config = tasks_config.get(task_type, {}) if tasks_config else {}
    
    if task_config:
        endpoint_id = task_config.get("endpoint_id")
        if endpoint_id:
            # 使用自定义端点
            endpoints_raw = get_config_dict(db, user_id, "llm_endpoints")
            endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
            endpoint = next((ep for ep in endpoints_list if ep.get("id") == endpoint_id), None)
            if endpoint:
                return {
                    "base_url": endpoint["base_url"],
                    "api_key": endpoint["api_key"],
                    "model": task_config.get("model", ""),
                }
        else:
            # 使用预设配置
            return {
                "base_url": task_config.get("base_url", ""),
                "api_key": "",  # 预设配置需要从llm配置获取
                "model": task_config.get("model", ""),
            }
    
    # 回退到默认LLM配置
    llm_config = get_config_dict(db, user_id, "llm")
    return {
        "base_url": llm_config.get("base_url", ""),
        "api_key": llm_config.get("api_key", ""),
        "model": llm_config.get("model", "gpt-4o-mini"),
    }


# ========== Routes ==========

@router.get("", response_model=ConfigResponse)
async def get_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户配置
    
    返回用户的ASR、LLM、通知配置
    API密钥会脱敏处理
    """
    # ASR配置
    asr_config = get_config_dict(db, user.id, "asr")
    asr = ASRConfigResponse(
        provider=asr_config.get("provider", "faster_whisper"),
        model_size=asr_config.get("model_size", "medium"),
        device=asr_config.get("device", "auto"),
        api_base_url=asr_config.get("api_base_url"),
        has_api_key=bool(asr_config.get("api_key")),
        api_model=asr_config.get("api_model"),
    )
    
    # LLM配置 (脱敏)
    llm_config = get_config_dict(db, user.id, "llm")
    llm = LLMConfigResponse(
        provider=llm_config.get("provider", "openai"),
        model=llm_config.get("model", "gpt-4o-mini"),
        base_url=llm_config.get("base_url"),
        has_api_key=bool(llm_config.get("api_key")),
        endpoint_id=llm_config.get("endpoint_id"),
    )
    
    # 通知配置
    notify_config = get_config_dict(db, user.id, "notify")
    notify = NotifyConfig(
        wechat_enabled=notify_config.get("wechat_enabled", False),
        webhook_url=notify_config.get("webhook_url"),
    )
    
    # 用户自定义LLM端点列表
    endpoints_raw = get_config_dict(db, user.id, "llm_endpoints")
    endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
    llm_endpoints = []
    for ep in endpoints_list:
        models = ep.get("models", [])
        models_with_type = [
            ModelInfo(id=m, name=m, type=infer_model_type(m))
            for m in models
        ]
        llm_endpoints.append(LLMEndpointResponse(
            id=ep.get("id", ""),
            name=ep.get("name", ""),
            base_url=ep.get("base_url", ""),
            has_api_key=bool(ep.get("api_key")),
            models=models,
            models_with_type=models_with_type,
        ))
    
    # 任务模型配置
    tasks_raw = get_config_dict(db, user.id, "model_tasks")
    model_tasks = ModelTasksResponse()
    if tasks_raw:
        for task_type in ["chat", "summary", "knowledge", "mindmap", "tagger", "context_compress", "asr", "embedding"]:
            task_data = tasks_raw.get(task_type)
            if task_data:
                setattr(model_tasks, task_type, ModelTaskConfig(**task_data))
    
    return ConfigResponse(asr=asr, llm=llm, notify=notify, llm_endpoints=llm_endpoints, model_tasks=model_tasks)


@router.put("/asr", response_model=ConfigUpdateResponse)
async def update_asr_config(
    config: ASRConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新ASR配置
    
    本地模式: faster_whisper, whisper_local
    API模式: openai_whisper, groq_whisper, deepgram
    """
    local_providers = ["whisper_local", "faster_whisper"]
    api_providers = ["openai_whisper", "groq_whisper", "deepgram", "xunfei"]
    valid_sizes = ["tiny", "base", "small", "medium", "large", "large-v3"]
    
    all_providers = local_providers + api_providers
    if config.provider not in all_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的ASR提供商: {config.provider}",
        )
    
    # 本地模式验证
    if config.provider in local_providers:
        if config.model_size not in valid_sizes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的模型大小: {config.model_size}",
            )
    
    # API模式需要api_key (更新时才校验)
    # 允许不传api_key表示保留原有配置
    
    set_user_config(db, user.id, "asr", json.dumps(config.model_dump(exclude_none=True)))
    
    return ConfigUpdateResponse(success=True, message="ASR配置已更新")


@router.put("/llm", response_model=ConfigUpdateResponse)
async def update_llm_config(
    config: LLMConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新LLM配置
    
    支持任何OpenAI兼容的API
    """
    # 获取现有配置，合并api_key
    existing = get_config_dict(db, user.id, "llm")
    
    data = config.model_dump(exclude_none=True)
    
    # 如果使用自定义端点，不需要单独的api_key
    if config.endpoint_id:
        # 从端点获取api_key和base_url
        endpoints_raw = get_config_dict(db, user.id, "llm_endpoints")
        endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
        endpoint = next((ep for ep in endpoints_list if ep.get("id") == config.endpoint_id), None)
        if endpoint:
            data["base_url"] = endpoint["base_url"]
            data["api_key"] = endpoint["api_key"]
        else:
            raise HTTPException(status_code=404, detail="端点不存在")
    else:
        # 使用预设提供商，需要api_key
        if not config.api_key and existing.get("api_key"):
            data["api_key"] = existing["api_key"]
        
        if not data.get("api_key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API密钥不能为空",
            )
    
    set_user_config(db, user.id, "llm", json.dumps(data))
    
    return ConfigUpdateResponse(success=True, message="LLM配置已更新")


@router.put("/notify", response_model=ConfigUpdateResponse)
async def update_notify_config(
    config: NotifyConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新通知配置"""
    set_user_config(db, user.id, "notify", json.dumps(config.model_dump()))
    
    return ConfigUpdateResponse(success=True, message="通知配置已更新")


@router.put("/model-tasks", response_model=ConfigUpdateResponse)
async def update_model_tasks(
    config: ModelTasksConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新任务模型配置
    
    为不同任务指定不同的模型：
    - chat: 对话问答
    - summary: 视频摘要
    - knowledge: 知识图谱提取
    - mindmap: 思维导图生成
    - tagger: 标签提取
    - context_compress: 上下文压缩
    - asr: 语音识别
    - embedding: 向量化
    """
    data = {}
    for task_type in ["chat", "summary", "knowledge", "mindmap", "tagger", "context_compress", "asr", "embedding"]:
        task_config = getattr(config, task_type, None)
        if task_config:
            data[task_type] = task_config.model_dump(exclude_none=True)
    
    set_user_config(db, user.id, "model_tasks", json.dumps(data))
    
    return ConfigUpdateResponse(success=True, message="任务模型配置已更新")


@router.put("/model-tasks/{task_type}", response_model=ConfigUpdateResponse)
async def update_single_model_task(
    task_type: str,
    config: ModelTaskConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新单个任务的模型配置"""
    valid_types = ["chat", "summary", "knowledge", "mindmap", "tagger", "context_compress", "asr", "embedding"]
    if task_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的任务类型，支持: {valid_types}")
    
    # 获取现有配置
    tasks_raw = get_config_dict(db, user.id, "model_tasks") or {}
    tasks_raw[task_type] = config.model_dump(exclude_none=True)
    
    set_user_config(db, user.id, "model_tasks", json.dumps(tasks_raw))
    
    return ConfigUpdateResponse(success=True, message=f"{task_type}模型配置已更新")


# ========== LLM Endpoints CRUD ==========

@router.post("/llm/endpoints", response_model=LLMEndpointResponse)
async def create_llm_endpoint(
    endpoint: LLMEndpointCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    添加自定义LLM端点
    
    添加后会自动尝试获取可用模型列表
    """
    import uuid
    
    # 获取现有端点列表
    endpoints_raw = get_config_dict(db, user.id, "llm_endpoints")
    endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
    
    # 创建新端点
    endpoint_id = str(uuid.uuid4())[:8]
    new_endpoint = {
        "id": endpoint_id,
        "name": endpoint.name,
        "base_url": endpoint.base_url.rstrip("/"),
        "api_key": endpoint.api_key,
        "models": [],
    }
    
    # 尝试获取模型列表
    try:
        models = await _fetch_models_from_endpoint(new_endpoint["base_url"], endpoint.api_key)
        new_endpoint["models"] = [m["id"] for m in models]
    except Exception as e:
        logger.warning(f"Failed to fetch models for endpoint: {e}")
    
    endpoints_list.append(new_endpoint)
    set_user_config(db, user.id, "llm_endpoints", json.dumps({"endpoints": endpoints_list}))
    
    return LLMEndpointResponse(
        id=endpoint_id,
        name=new_endpoint["name"],
        base_url=new_endpoint["base_url"],
        has_api_key=True,
        models=new_endpoint["models"],
    )


@router.delete("/llm/endpoints/{endpoint_id}")
async def delete_llm_endpoint(
    endpoint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自定义LLM端点"""
    endpoints_raw = get_config_dict(db, user.id, "llm_endpoints")
    endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
    
    # 过滤掉要删除的端点
    new_list = [ep for ep in endpoints_list if ep.get("id") != endpoint_id]
    
    if len(new_list) == len(endpoints_list):
        raise HTTPException(status_code=404, detail="端点不存在")
    
    set_user_config(db, user.id, "llm_endpoints", json.dumps({"endpoints": new_list}))
    
    return {"success": True, "message": "端点已删除"}


@router.post("/llm/endpoints/{endpoint_id}/refresh")
async def refresh_endpoint_models(
    endpoint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """刷新端点的模型列表"""
    endpoints_raw = get_config_dict(db, user.id, "llm_endpoints")
    endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
    
    # 找到端点
    endpoint = None
    for ep in endpoints_list:
        if ep.get("id") == endpoint_id:
            endpoint = ep
            break
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="端点不存在")
    
    # 获取模型列表
    try:
        models = await _fetch_models_from_endpoint(endpoint["base_url"], endpoint["api_key"])
        endpoint["models"] = [m["id"] for m in models]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取模型失败: {str(e)}")
    
    set_user_config(db, user.id, "llm_endpoints", json.dumps({"endpoints": endpoints_list}))
    
    return {"success": True, "models": endpoint["models"]}


@router.get("/asr/providers")
async def get_asr_providers():
    """获取支持的ASR提供商列表"""
    return {
        "providers": [
            # 本地模式
            {
                "id": "faster_whisper",
                "name": "Faster-Whisper",
                "type": "local",
                "description": "本地运行，4x加速版Whisper，推荐",
            },
            {
                "id": "whisper_local",
                "name": "Whisper Local",
                "type": "local",
                "description": "OpenAI Whisper本地版",
            },
            # API模式
            {
                "id": "openai_whisper",
                "name": "OpenAI Whisper API",
                "type": "api",
                "description": "OpenAI云端Whisper API",
                "base_url": "https://api.openai.com/v1",
                "models": ["whisper-1"],
            },
            {
                "id": "groq_whisper",
                "name": "Groq Whisper",
                "type": "api",
                "description": "Groq超快Whisper API，免费额度大",
                "base_url": "https://api.groq.com/openai/v1",
                "models": ["whisper-large-v3", "whisper-large-v3-turbo"],
            },
            {
                "id": "deepgram",
                "name": "Deepgram",
                "type": "api",
                "description": "专业语音识别API",
                "base_url": "https://api.deepgram.com/v1",
                "models": ["nova-2", "nova-2-general"],
            },
            {
                "id": "xunfei",
                "name": "讯飞语音",
                "type": "api",
                "description": "讯飞实时语音识别",
                "base_url": "https://iat-api.xfyun.cn/v2/iat",
                "models": ["iat"],
            },
        ],
        "local_model_sizes": [
            {"id": "tiny", "name": "Tiny", "vram": "1GB", "speed": "32x"},
            {"id": "base", "name": "Base", "vram": "1GB", "speed": "16x"},
            {"id": "small", "name": "Small", "vram": "2GB", "speed": "6x"},
            {"id": "medium", "name": "Medium", "vram": "5GB", "speed": "2x"},
            {"id": "large", "name": "Large", "vram": "10GB", "speed": "1x"},
            {"id": "large-v3", "name": "Large-v3", "vram": "10GB", "speed": "1x"},
        ],
    }


@router.get("/llm/providers")
async def get_llm_providers():
    """获取LLM提供商预设配置"""
    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "default_models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1",
                "default_models": ["deepseek-chat", "deepseek-reasoner"],
            },
            {
                "id": "siliconflow",
                "name": "SiliconFlow",
                "base_url": "https://api.siliconflow.cn/v1",
                "default_models": ["Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-V3"],
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "base_url": "http://localhost:11434/v1",
                "default_models": ["qwen2.5", "llama3.2", "deepseek-r1:8b"],
            },
            {
                "id": "groq",
                "name": "Groq",
                "base_url": "https://api.groq.com/openai/v1",
                "default_models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            },
            {
                "id": "openai_compatible",
                "name": "OpenAI兼容API",
                "base_url": "",
                "default_models": [],
                "description": "任何兼容OpenAI格式的API",
            },
        ],
    }


class FetchModelsRequest(BaseModel):
    """获取模型列表请求"""
    base_url: Optional[str] = None
    api_key: Optional[str] = None


async def _fetch_models_from_endpoint(base_url: str, api_key: str) -> list:
    """从端点获取模型列表的内部函数"""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"获取模型列表失败: {response.text}",
            )
        
        data = response.json()
        models = []
        
        # 解析OpenAI格式的响应 - 返回所有模型，不过滤
        if "data" in data:
            for model in data["data"]:
                model_id = model.get("id", "")
                if model_id:  # 只要有id就返回
                    models.append({
                        "id": model_id,
                        "name": model_id,
                        "owned_by": model.get("owned_by", ""),
                    })
        
        return models


@router.post("/llm/models")
async def fetch_llm_models(
    request: FetchModelsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    从OpenAI兼容端点获取可用模型列表
    
    - 如果提供base_url和api_key，使用提供的值
    - 否则使用用户已保存的配置
    """
    try:
        # 获取用户已保存的配置
        existing = get_config_dict(db, user.id, "llm")
        
        # 确定使用哪个base_url和api_key
        base_url = request.base_url or existing.get("base_url")
        api_key = request.api_key or existing.get("api_key")
        
        if not base_url:
            raise HTTPException(status_code=400, detail="请先配置API Base URL")
        if not api_key:
            raise HTTPException(status_code=400, detail="请先配置API Key")
        
        models = await _fetch_models_from_endpoint(base_url, api_key)
        return {"models": models}
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="请求超时，请检查API地址")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")


# 保留旧接口兼容
@router.get("/llm/presets")
async def get_llm_presets():
    """获取LLM预设配置 (兼容旧接口)"""
    result = await get_llm_providers()
    return {"presets": result["providers"]}


# ========== Prompt 配置 ==========

class PromptConfig(BaseModel):
    """单个Prompt配置"""
    prompt_type: str
    content: str


class PromptsResponse(BaseModel):
    """Prompt配置响应"""
    prompts: dict  # {prompt_type: content}
    defaults: dict  # {prompt_type: default_content}
    descriptions: dict  # {prompt_type: description}
    structured: list  # 需要固定JSON格式的类型
    free: list  # 可自由修改的类型


@router.get("/prompts", response_model=PromptsResponse)
async def get_prompts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户的Prompt配置
    
    返回用户自定义的prompt，以及所有默认prompt供参考
    """
    from services.ai.prompts import DEFAULT_PROMPTS, PROMPT_DESCRIPTIONS, STRUCTURED_PROMPTS, FREE_PROMPTS
    
    # 获取用户自定义prompt
    user_prompts = get_config_dict(db, user.id, "custom_prompts") or {}
    
    return PromptsResponse(
        prompts=user_prompts,
        defaults=DEFAULT_PROMPTS,
        descriptions=PROMPT_DESCRIPTIONS,
        structured=list(STRUCTURED_PROMPTS),
        free=list(FREE_PROMPTS),
    )


@router.put("/prompts/{prompt_type}")
async def update_prompt(
    prompt_type: str,
    config: PromptConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新单个Prompt
    
    prompt_type: chat, summary, tagger, knowledge, mindmap, context_compress
    """
    from services.ai.prompts import DEFAULT_PROMPTS
    
    valid_types = list(DEFAULT_PROMPTS.keys())
    if prompt_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的prompt类型，支持: {valid_types}")
    
    # 获取现有配置
    prompts = get_config_dict(db, user.id, "custom_prompts") or {}
    prompts[prompt_type] = config.content
    
    set_user_config(db, user.id, "custom_prompts", json.dumps(prompts))
    
    return ConfigUpdateResponse(success=True, message=f"{prompt_type} prompt已更新")


@router.delete("/prompts/{prompt_type}")
async def reset_prompt(
    prompt_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    重置单个Prompt为默认值
    """
    from services.ai.prompts import DEFAULT_PROMPTS
    
    valid_types = list(DEFAULT_PROMPTS.keys())
    if prompt_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的prompt类型，支持: {valid_types}")
    
    prompts = get_config_dict(db, user.id, "custom_prompts") or {}
    if prompt_type in prompts:
        del prompts[prompt_type]
        set_user_config(db, user.id, "custom_prompts", json.dumps(prompts))
    
    return ConfigUpdateResponse(success=True, message=f"{prompt_type} prompt已重置为默认")


def get_user_prompt(db, user_id: int, prompt_type: str) -> str:
    """
    获取用户的prompt（优先自定义，否则默认）
    
    供其他模块调用
    """
    from services.ai.prompts import DEFAULT_PROMPTS
    
    user_prompts = get_config_dict(db, user_id, "custom_prompts") or {}
    return user_prompts.get(prompt_type) or DEFAULT_PROMPTS.get(prompt_type, "")
