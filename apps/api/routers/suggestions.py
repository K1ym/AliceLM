"""
灵感建议路由
生成基于用户上下文的对话启发
"""

from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.db import User, Video, VideoStatus
from packages.logging import get_logger
from services.ai.llm import LLMManager, Message as LLMMessage, create_llm_from_config

from ..deps import get_db, get_current_user
from .config import get_task_llm_config

logger = get_logger(__name__)
router = APIRouter()

# 缓存：{cache_key: (suggestions, expire_time)}
_suggestion_cache: dict[str, tuple[list, datetime]] = {}
CACHE_TTL_MINUTES = 30


class Suggestion(BaseModel):
    """单条建议"""
    text: str
    icon: str  # lucide图标名
    action: str  # ask / summarize / compare


class SuggestionsResponse(BaseModel):
    """建议列表响应"""
    suggestions: List[Suggestion]
    context: Optional[str] = None  # 生成上下文说明


def _get_cache_key(user_id: int, video_ids: List[int]) -> str:
    """生成缓存key"""
    data = f"{user_id}:{','.join(map(str, sorted(video_ids)))}"
    return hashlib.md5(data.encode()).hexdigest()


def _get_cached(cache_key: str) -> Optional[List[Suggestion]]:
    """获取缓存"""
    if cache_key in _suggestion_cache:
        suggestions, expire_time = _suggestion_cache[cache_key]
        if datetime.utcnow() < expire_time:
            return suggestions
        del _suggestion_cache[cache_key]
    return None


def _set_cache(cache_key: str, suggestions: List[Suggestion]):
    """设置缓存"""
    expire_time = datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES)
    _suggestion_cache[cache_key] = (suggestions, expire_time)
    
    # 清理过期缓存（简单策略：超过100个时清理）
    if len(_suggestion_cache) > 100:
        now = datetime.utcnow()
        expired_keys = [k for k, (_, exp) in _suggestion_cache.items() if exp < now]
        for k in expired_keys:
            del _suggestion_cache[k]


def _generate_default_suggestions() -> List[Suggestion]:
    """生成默认建议（无视频时）"""
    return [
        Suggestion(text="粘贴B站链接导入视频", icon="Link", action="import"),
        Suggestion(text="浏览我的知识库", icon="Library", action="browse"),
        Suggestion(text="今天学点什么", icon="Sparkles", action="ask"),
    ]


async def _generate_suggestions_from_videos(
    videos: List[Video],
    db: Session,
    user_id: int,
) -> List[Suggestion]:
    """基于视频生成智能建议"""
    
    # 构建视频上下文
    video_context = "\n".join([
        f"- {v.title} (作者: {v.author})" + (f" 摘要: {v.summary[:100]}..." if v.summary else "")
        for v in videos[:5]
    ])
    
    prompt = f"""基于用户最近观看的视频，生成3个有启发性的对话开场建议。

用户最近的视频：
{video_context}

要求：
1. 每条建议15-25个字
2. 要具体，引用视频内容
3. 引发思考，不是简单总结
4. 语气自然，像朋友聊天

返回JSON数组格式：
[
  {{"text": "建议内容", "icon": "Sparkles", "action": "ask"}},
  {{"text": "建议内容", "icon": "GitCompare", "action": "compare"}},
  {{"text": "建议内容", "icon": "Lightbulb", "action": "ask"}}
]

可用的icon: Sparkles, Lightbulb, GitCompare, MessageCircle, BookOpen, Target
可用的action: ask, summarize, compare

只返回JSON，不要其他内容。"""

    try:
        # 获取用户配置的LLM
        llm_config = get_task_llm_config(db, user_id, "chat")
        
        if llm_config.get("api_key") and llm_config.get("base_url"):
            llm = create_llm_from_config(
                base_url=llm_config["base_url"],
                api_key=llm_config["api_key"],
                model=llm_config.get("model", "gpt-4o-mini"),
            )
        else:
            llm = LLMManager()
        
        messages = [LLMMessage(role="user", content=prompt)]
        response = llm.chat(messages)
        
        # 解析JSON
        result = json.loads(response.content.strip())
        suggestions = [Suggestion(**item) for item in result[:3]]
        
        logger.info("suggestions_generated", user_id=user_id, count=len(suggestions))
        return suggestions
        
    except Exception as e:
        logger.warning("suggestions_generation_failed", error=str(e))
        # 降级：基于视频标题生成简单建议
        fallback = []
        if videos:
            fallback.append(Suggestion(
                text=f"聊聊《{videos[0].title[:15]}...》的核心观点",
                icon="MessageCircle",
                action="ask",
            ))
        if len(videos) >= 2:
            fallback.append(Suggestion(
                text=f"对比这两个视频的不同视角",
                icon="GitCompare",
                action="compare",
            ))
        fallback.append(Suggestion(
            text="帮我总结最近学到的内容",
            icon="BookOpen",
            action="summarize",
        ))
        return fallback[:3]


@router.get("", response_model=SuggestionsResponse)
async def get_suggestions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取灵感建议
    基于用户最近的视频生成个性化建议
    """
    # 获取用户最近处理完成的视频
    recent_videos = (
        db.query(Video)
        .filter(
            Video.tenant_id == user.tenant_id,
            Video.status == VideoStatus.DONE.value,
        )
        .order_by(Video.processed_at.desc())
        .limit(5)
        .all()
    )
    
    # 无视频时返回默认建议
    if not recent_videos:
        return SuggestionsResponse(
            suggestions=_generate_default_suggestions(),
            context="开始你的学习之旅",
        )
    
    # 检查缓存
    video_ids = [v.id for v in recent_videos]
    cache_key = _get_cache_key(user.id, video_ids)
    cached = _get_cached(cache_key)
    
    if cached:
        logger.info("suggestions_cache_hit", user_id=user.id)
        return SuggestionsResponse(
            suggestions=cached,
            context=f"基于《{recent_videos[0].title[:20]}...》等视频",
        )
    
    # 生成新建议
    suggestions = await _generate_suggestions_from_videos(recent_videos, db, user.id)
    
    # 缓存结果
    _set_cache(cache_key, suggestions)
    
    return SuggestionsResponse(
        suggestions=suggestions,
        context=f"基于《{recent_videos[0].title[:20]}...》等视频",
    )
