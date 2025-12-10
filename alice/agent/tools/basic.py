"""
基础本地工具

这些工具不依赖第三方服务，可直接使用。
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from ..tool_router import AliceTool


class EchoTool(AliceTool):
    """
    Echo 工具 - 用于调试
    
    原样返回输入内容，用于测试工具调用是否正常。
    """
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "调试工具，原样返回输入内容。用于测试工具调用是否正常。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "要回显的消息"
                }
            },
            "required": ["message"]
        }
    
    async def run(self, args: Dict[str, Any]) -> str:
        message = args.get("message", "")
        return f"[Echo] {message}"


class CurrentTimeTool(AliceTool):
    """
    当前时间工具
    
    返回当前系统时间。
    """
    
    @property
    def name(self) -> str:
        return "current_time"
    
    @property
    def description(self) -> str:
        return "获取当前系统时间。当用户询问时间相关问题时使用。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "时间格式，默认为 ISO 格式",
                    "enum": ["iso", "human", "timestamp"]
                }
            },
            "required": []
        }
    
    async def run(self, args: Dict[str, Any]) -> str:
        fmt = args.get("format", "human")
        now = datetime.now()
        
        if fmt == "iso":
            return now.isoformat()
        elif fmt == "timestamp":
            return str(int(now.timestamp()))
        else:  # human
            return now.strftime("%Y年%m月%d日 %H:%M:%S")


class SleepTool(AliceTool):
    """
    Sleep 工具 - 用于调试
    
    暂停指定秒数，用于测试异步调用。
    """
    
    @property
    def name(self) -> str:
        return "sleep"
    
    @property
    def description(self) -> str:
        return "调试工具，暂停指定秒数。最大 10 秒。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "暂停秒数，最大 10 秒"
                }
            },
            "required": ["seconds"]
        }
    
    async def run(self, args: Dict[str, Any]) -> str:
        seconds = min(args.get("seconds", 1), 10)  # 最大 10 秒
        await asyncio.sleep(seconds)
        return f"已暂停 {seconds} 秒"


class GetTimelineSummaryTool(AliceTool):
    """
    获取时间线摘要工具

    调用 TimelineService 获取用户最近的活动摘要。
    """

    def __init__(self, db=None):
        self._db = db

    @property
    def name(self) -> str:
        return "get_timeline_summary"

    @property
    def description(self) -> str:
        return "获取用户最近的学习活动摘要，包括观看的视频、提问记录等。"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "统计天数，默认 7 天",
                    "default": 7
                },
                "tenant_id": {
                    "type": "integer",
                    "description": "租户 ID（由系统自动填充）"
                }
            },
            "required": []
        }

    async def run(self, args: Dict[str, Any]) -> str:
        days = args.get("days", 7)
        tenant_id = args.get("tenant_id")

        if self._db is None:
            return f"[模拟] 最近 {days} 天的时间线摘要：暂无数据"

        if tenant_id is None:
            return f"[错误] 未提供 tenant_id，无法获取时间线摘要"

        try:
            from alice.one import TimelineService
            service = TimelineService(self._db)
            summary = await service.get_recent_summary(
                tenant_id=tenant_id,
                days=days,
            )
            
            total = summary.get("total_events", 0)
            counts = summary.get("event_counts", {})
            
            result = f"最近 {days} 天活动摘要：\n"
            result += f"- 总事件数：{total}\n"
            for event_type, count in counts.items():
                result += f"- {event_type}：{count} 次\n"
            
            return result
            
        except Exception as e:
            return f"获取时间线摘要失败：{str(e)}"


class GetVideoSummaryTool(AliceTool):
    """
    获取视频摘要工具
    
    获取指定视频的摘要信息。
    """
    
    def __init__(self, db=None):
        self._db = db
    
    @property
    def name(self) -> str:
        return "get_video_summary"
    
    @property
    def description(self) -> str:
        return "获取指定视频的摘要信息，包括标题、时长、主要内容等。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_id": {
                    "type": "integer",
                    "description": "视频 ID"
                }
            },
            "required": ["video_id"]
        }
    
    async def run(self, args: Dict[str, Any]) -> str:
        video_id = args.get("video_id")
        
        if video_id is None:
            return "错误：需要提供 video_id"
        
        if self._db is None:
            return f"[模拟] 视频 {video_id} 的摘要：这是一个测试视频"
        
        try:
            from packages.db.models import Video
            from sqlalchemy import select
            
            stmt = select(Video).where(Video.id == video_id)
            result = self._db.execute(stmt)
            video = result.scalar_one_or_none()
            
            if video is None:
                return f"未找到视频 ID: {video_id}"
            
            summary = f"视频信息：\n"
            summary += f"- 标题：{video.title}\n"
            summary += f"- 时长：{video.duration or '未知'} 秒\n"
            summary += f"- 状态：{video.status.value}\n"
            
            if video.summary:
                summary += f"- 摘要：{video.summary[:200]}..."
            
            return summary
            
        except Exception as e:
            return f"获取视频摘要失败：{str(e)}"


class SearchVideosTool(AliceTool):
    """
    搜索视频工具
    
    在用户的视频库中搜索相关视频。
    """
    
    def __init__(self, db=None):
        self._db = db
    
    @property
    def name(self) -> str:
        return "search_videos"
    
    @property
    def description(self) -> str:
        return "在用户的视频库中搜索相关视频。返回匹配的视频列表。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    async def run(self, args: Dict[str, Any]) -> str:
        query = args.get("query", "")
        limit = args.get("limit", 5)
        
        if not query:
            return "错误：需要提供搜索关键词"
        
        if self._db is None:
            return f"[模拟] 搜索「{query}」的结果：暂无数据"
        
        try:
            from packages.db.models import Video
            from sqlalchemy import select, or_
            
            # 简单的标题搜索
            stmt = (
                select(Video)
                .where(
                    or_(
                        Video.title.contains(query),
                        Video.summary.contains(query) if Video.summary else False,
                    )
                )
                .limit(limit)
            )
            result = self._db.execute(stmt)
            videos = result.scalars().all()
            
            if not videos:
                return f"未找到与「{query}」相关的视频"
            
            results = f"找到 {len(videos)} 个相关视频：\n"
            for v in videos:
                results += f"- [{v.id}] {v.title}\n"
            
            return results
            
        except Exception as e:
            return f"搜索视频失败：{str(e)}"


# ============== 工具注册 ==============

def get_basic_tools(db=None) -> list:
    """获取所有基础工具实例"""
    return [
        EchoTool(),
        CurrentTimeTool(),
        SleepTool(),
        GetTimelineSummaryTool(db),
        GetVideoSummaryTool(db),
        SearchVideosTool(db),
    ]


def register_basic_tools(router, db=None):
    """向 ToolRouter 注册所有基础工具"""
    for tool in get_basic_tools(db):
        router.register_tool(tool)
