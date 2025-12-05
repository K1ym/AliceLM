"""
AliceIdentityService - Alice One 身份服务

职责：
- 从 TenantConfig 读取 alice.* 命名空间配置
- 生成 system_prompt（人格/语气）
- 输出 enabled_tools / tool_scopes
- 为不同租户提供差异化的 Alice 人设
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class AlicePersona:
    """Alice 人格配置"""
    name: str = "Alice"
    description: str = "你的个人学习助手"
    style: str = "friendly"  # friendly / professional / coach
    language: str = "zh-CN"
    
    # 额外配置
    custom_instructions: Optional[str] = None


@dataclass
class AliceIdentity:
    """AliceIdentityService 输出"""
    # 人格
    persona: AlicePersona
    
    # System Prompt
    system_prompt: str
    
    # 工具配置
    enabled_tools: List[str] = field(default_factory=list)
    tool_scopes: Dict[str, List[str]] = field(default_factory=dict)
    
    # 其他配置
    settings: Dict[str, Any] = field(default_factory=dict)


# 默认 System Prompt 模板
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """你是 {name}，{description}。

## 你的特点
- 你熟悉用户观看过的所有视频内容
- 你能够帮助用户回顾、理解和关联知识
- 你会根据用户的学习历史提供个性化建议

## 你的风格
{style_description}

## 注意事项
- 回答要简洁明了，避免冗长
- 引用视频内容时，说明来源
- 如果不确定，诚实地说你不知道

{custom_instructions}
"""

STYLE_DESCRIPTIONS = {
    "friendly": "你友好、亲切，像朋友一样和用户交流。",
    "professional": "你专业、严谨，注重准确性和深度。",
    "coach": "你像教练一样引导用户思考，善于提问和启发。",
}


class AliceIdentityService:
    """
    Alice One 身份服务
    
    从租户配置中读取 Alice 人格设置，生成 system_prompt 和工具配置。
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_identity(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        scene: Optional[str] = None,
    ) -> AliceIdentity:
        """
        获取 Alice 身份配置
        
        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID（可选，用于个性化）
            scene: 当前场景（可选，用于调整工具范围）
            
        Returns:
            AliceIdentity 包含 persona, system_prompt, tools 等
        """
        # 读取租户级 Alice 配置
        alice_config = await self._get_tenant_alice_config(tenant_id)
        
        # 构建 Persona
        persona = AlicePersona(
            name=alice_config.get("name", "Alice"),
            description=alice_config.get("description", "你的个人学习助手"),
            style=alice_config.get("style", "friendly"),
            language=alice_config.get("language", "zh-CN"),
            custom_instructions=alice_config.get("custom_instructions"),
        )
        
        # 生成 System Prompt
        system_prompt = self._build_system_prompt(persona)
        
        # 获取工具配置
        enabled_tools = alice_config.get("enabled_tools", self._get_default_tools())
        tool_scopes = alice_config.get("tool_scopes", self._get_default_tool_scopes())
        
        # 根据场景过滤工具
        if scene:
            enabled_tools = self._filter_tools_by_scene(enabled_tools, tool_scopes, scene)
        
        return AliceIdentity(
            persona=persona,
            system_prompt=system_prompt,
            enabled_tools=enabled_tools,
            tool_scopes=tool_scopes,
            settings=alice_config.get("settings", {}),
        )
    
    async def _get_tenant_alice_config(self, tenant_id: int) -> Dict[str, Any]:
        """从 TenantConfig 读取 alice.* 配置"""
        from packages.db.models import TenantConfig
        
        stmt = select(TenantConfig).where(
            TenantConfig.tenant_id == tenant_id,
            TenantConfig.key.like("alice.%")
        )
        result = self.db.execute(stmt)
        configs = result.scalars().all()
        
        # 解析配置
        alice_config: Dict[str, Any] = {}
        for config in configs:
            # key 格式: alice.persona, alice.style, alice.tools 等
            key_parts = config.key.split(".", 1)
            if len(key_parts) == 2:
                sub_key = key_parts[1]
                try:
                    # 尝试解析 JSON
                    alice_config[sub_key] = json.loads(config.value)
                except json.JSONDecodeError:
                    alice_config[sub_key] = config.value
        
        return alice_config
    
    def _build_system_prompt(self, persona: AlicePersona) -> str:
        """构建 System Prompt"""
        style_desc = STYLE_DESCRIPTIONS.get(persona.style, STYLE_DESCRIPTIONS["friendly"])
        
        custom = ""
        if persona.custom_instructions:
            custom = f"\n## 特殊指示\n{persona.custom_instructions}"
        
        return DEFAULT_SYSTEM_PROMPT_TEMPLATE.format(
            name=persona.name,
            description=persona.description,
            style_description=style_desc,
            custom_instructions=custom,
        ).strip()
    
    def _get_default_tools(self) -> List[str]:
        """默认启用的工具"""
        return [
            "ask_video",
            "search_videos",
            "get_video_summary",
            "search_graph",
            "timeline_query",
            "current_time",
        ]
    
    def _get_default_tool_scopes(self) -> Dict[str, List[str]]:
        """默认工具范围配置"""
        return {
            "chat": [
                "ask_video",
                "search_videos",
                "get_video_summary",
                "current_time",
            ],
            "research": [
                "ask_video",
                "search_videos",
                "search_graph",
                "deep_web_research",
                "generate_report",
                "current_time",
            ],
            "timeline": [
                "timeline_query",
                "get_timeline_summary",
                "search_videos",
                "current_time",
            ],
            "library": [
                "search_videos",
                "get_video_summary",
                "current_time",
            ],
            "video": [
                "ask_video",
                "get_video_summary",
                "current_time",
            ],
            "graph": [
                "search_graph",
                "search_videos",
                "current_time",
            ],
            "console": [
                # Console 场景允许所有工具
                "ask_video",
                "search_videos",
                "get_video_summary",
                "search_graph",
                "timeline_query",
                "get_timeline_summary",
                "deep_web_research",
                "generate_report",
                "current_time",
                # Debug 工具
                "echo",
                "sleep",
            ],
        }
    
    def _filter_tools_by_scene(
        self,
        enabled_tools: List[str],
        tool_scopes: Dict[str, List[str]],
        scene: str,
    ) -> List[str]:
        """根据场景过滤可用工具"""
        scene_tools = tool_scopes.get(scene, tool_scopes.get("chat", []))
        return [t for t in enabled_tools if t in scene_tools]


async def get_alice_identity(
    db: Session,
    tenant_id: int,
    user_id: Optional[int] = None,
    scene: Optional[str] = None,
) -> AliceIdentity:
    """
    便捷函数：获取 Alice 身份
    
    用法：
        identity = await get_alice_identity(db, tenant_id=1, scene="chat")
        print(identity.system_prompt)
    """
    service = AliceIdentityService(db)
    return await service.get_identity(tenant_id, user_id, scene)
