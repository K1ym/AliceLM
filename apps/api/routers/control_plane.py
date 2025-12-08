"""
控制平面 API 路由

提供 ControlPlane 核心信息的只读 API：
- 模型 profile 列表
- 场景工具列表
- Prompt key 列表

用于 Settings/Console/开发者面板
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from packages.db import User
from ..deps import get_current_user

router = APIRouter()


# ============== Response Models ==============

class ModelProfileResponse(BaseModel):
    """模型 Profile 响应"""
    id: str
    kind: str
    provider: str
    model: str
    base_url: Optional[str] = None


class ModelsListResponse(BaseModel):
    """模型列表响应"""
    profiles: List[ModelProfileResponse]


class ResolvedModelResponse(BaseModel):
    """解析后的模型响应"""
    profile_id: Optional[str] = None
    kind: str
    provider: str
    model: str
    base_url: Optional[str] = None
    api_key_masked: Optional[str] = None  # 脱敏后的 API key


class ModelResolveResponse(BaseModel):
    """模型解析响应"""
    task_type: str
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    resolved: ResolvedModelResponse


class ToolInfoResponse(BaseModel):
    """工具信息响应"""
    name: str
    description: Optional[str] = None
    dangerous: bool = False
    enabled: bool = True


class ToolsListResponse(BaseModel):
    """工具列表响应"""
    scene: Optional[str] = None
    tools: List[ToolInfoResponse]
    all_scenes: Optional[Dict[str, List[str]]] = None


class PromptInfoResponse(BaseModel):
    """Prompt 信息响应"""
    key: str
    value: str
    overridden: bool = False


class PromptsListResponse(BaseModel):
    """Prompt 列表响应"""
    prompts: List[PromptInfoResponse]


class ControlPlaneSummaryResponse(BaseModel):
    """控制平面状态摘要"""
    models: Dict[str, Dict[str, Any]]
    scenes: Dict[str, List[str]]
    prompts: List[str]


# ============== API Endpoints ==============

@router.get("/models", response_model=ModelsListResponse)
async def list_model_profiles(
    kind: Optional[str] = Query(None, description="过滤类型: chat/embedding/asr"),
    user: User = Depends(get_current_user),
):
    """
    列出所有模型 profiles
    
    用于前端展示可选模型配置
    """
    from alice.control_plane import get_control_plane
    
    cp = get_control_plane()
    profile_ids = cp.list_model_profiles(kind=kind)
    
    profiles = []
    for pid in profile_ids:
        profile = cp.models.get_profile(pid)
        if profile:
            profiles.append(ModelProfileResponse(
                id=pid,
                kind=profile.kind,
                provider=profile.provider,
                model=profile.model,
                base_url=None,  # base_url 在运行时解析
            ))
    
    return ModelsListResponse(profiles=profiles)


@router.get("/models/resolve", response_model=ModelResolveResponse)
async def resolve_model_for_task(
    task_type: str = Query(..., description="任务类型: chat/summary/embedding/asr"),
    user_id: Optional[int] = Query(None, description="用户 ID（可选，默认用当前用户）"),
    user: User = Depends(get_current_user),
):
    """
    查看某任务实际使用的模型
    
    展示 tenant/user 配置叠加后的最终结果
    """
    from alice.control_plane import get_control_plane
    
    cp = get_control_plane()
    
    # 使用传入的 user_id 或当前用户
    target_user_id = user_id or user.id
    
    resolved = await cp.resolve_model(
        task_type=task_type,
        tenant_id=user.tenant_id if hasattr(user, 'tenant_id') else None,
        user_id=target_user_id,
    )
    
    # 脱敏 API key
    masked_key = None
    if resolved.api_key:
        key = resolved.api_key
        if len(key) > 8:
            masked_key = key[:4] + "****" + key[-4:]
        else:
            masked_key = "****"
    
    return ModelResolveResponse(
        task_type=task_type,
        tenant_id=user.tenant_id if hasattr(user, 'tenant_id') else None,
        user_id=target_user_id,
        resolved=ResolvedModelResponse(
            profile_id=resolved.profile_id,
            kind=resolved.kind,
            provider=resolved.provider,
            model=resolved.model,
            base_url=resolved.base_url,
            api_key_masked=masked_key,
        ),
    )


@router.get("/tools", response_model=ToolsListResponse)
async def list_tools(
    scene: Optional[str] = Query(None, description="场景: chat/research/video/console"),
    user: User = Depends(get_current_user),
):
    """
    列出场景可用工具
    
    不传 scene 时返回所有场景的映射
    """
    from alice.control_plane import get_control_plane
    
    cp = get_control_plane()
    
    if scene:
        # 返回指定场景的工具
        tool_names = cp.list_tools_for_scene(scene)
        tools = []
        
        for name in tool_names:
            config = cp.tools.get_tool_config(name)
            tools.append(ToolInfoResponse(
                name=name,
                description=config.description if config else None,
                dangerous=config.unsafe if config else False,
                enabled=config.enabled if config else True,
            ))
        
        return ToolsListResponse(scene=scene, tools=tools)
    else:
        # 返回所有场景的工具映射
        all_scenes = {}
        for scene_name in ["chat", "research", "video", "library", "console", "social", "media"]:
            all_scenes[scene_name] = cp.list_tools_for_scene(scene_name)
        
        return ToolsListResponse(
            scene=None,
            tools=[],
            all_scenes=all_scenes,
        )


@router.get("/prompts", response_model=PromptsListResponse)
async def list_prompts(
    key: Optional[str] = Query(None, description="指定 key，不传返回全部"),
    user: User = Depends(get_current_user),
):
    """
    列出 Prompt keys 及当前生效的文案
    
    展示用户覆盖状态
    """
    from alice.control_plane import get_control_plane
    
    cp = get_control_plane()
    
    # 获取所有 key
    all_keys = cp.list_prompt_keys()
    
    if key:
        # 只返回指定 key
        all_keys = [k for k in all_keys if k == key or key in k]
    
    prompts = []
    for k in all_keys:
        # 获取当前生效值（含用户覆盖）
        current_value = await cp.get_prompt(k, user_id=user.id)
        
        # 获取默认值
        default_value = cp.prompts.get_default(k) or ""
        
        # 判断是否被覆盖
        overridden = current_value != default_value and current_value != ""
        
        prompts.append(PromptInfoResponse(
            key=k,
            value=current_value[:500] + "..." if len(current_value) > 500 else current_value,
            overridden=overridden,
        ))
    
    return PromptsListResponse(prompts=prompts)


@router.get("/summary", response_model=ControlPlaneSummaryResponse)
async def get_control_plane_summary(
    user: User = Depends(get_current_user),
):
    """
    控制平面状态摘要
    
    用于 Console 的「Alice 当前状态」卡片
    """
    from alice.control_plane import get_control_plane
    
    cp = get_control_plane()
    
    # 获取各任务的模型
    models = {}
    for task_type in ["chat", "summary", "embedding", "asr"]:
        try:
            resolved = await cp.resolve_model(task_type, user_id=user.id)
            models[task_type] = {
                "profile_id": resolved.profile_id,
                "provider": resolved.provider,
                "model": resolved.model,
            }
        except Exception:
            models[task_type] = {"error": "未配置"}
    
    # 获取各场景的工具
    scenes = {}
    for scene in ["chat", "research", "video", "library", "console"]:
        scenes[scene] = cp.list_tools_for_scene(scene)
    
    # 获取 prompt keys
    prompts = cp.list_prompt_keys()
    
    return ControlPlaneSummaryResponse(
        models=models,
        scenes=scenes,
        prompts=prompts,
    )
