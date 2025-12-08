"""
AliceLM MCP Server
P3-09/P3-10: MCP Server实现

供Claude Desktop等AI客户端调用
"""

import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 添加项目路径
sys.path.insert(0, str(__file__).rsplit("/apps", 1)[0])

from packages.config import get_config
from packages.db import init_db, get_db_context, Tenant, Video, VideoStatus
from packages.logging import get_logger

logger = get_logger(__name__)
config = get_config()

# 创建MCP Server
server = Server("bili-learner")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="search_videos",
            description="在视频库中搜索视频，支持标题关键词搜索",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_video_summary",
            description="获取指定视频的摘要和核心观点",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "B站视频BV号",
                    },
                },
                "required": ["source_id"],
            },
        ),
        Tool(
            name="get_video_transcript",
            description="获取视频的完整转写文本",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "B站视频BV号",
                    },
                },
                "required": ["source_id"],
            },
        ),
        Tool(
            name="ask_knowledge",
            description="基于视频知识库进行问答，AI会从所有视频内容中检索相关信息回答问题",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要问的问题",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="list_recent_videos",
            description="列出最近添加的视频",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回数量",
                        "default": 10,
                    },
                    "status": {
                        "type": "string",
                        "description": "状态过滤: pending/done/failed",
                    },
                },
            },
        ),
        Tool(
            name="get_stats",
            description="获取视频库统计信息",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """执行工具调用"""
    try:
        result = await execute_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as e:
        logger.error("mcp_tool_error", tool=name, error=str(e))
        return [TextContent(type="text", text=f"Error: {e}")]


async def execute_tool(name: str, args: dict[str, Any]) -> dict:
    """工具执行逻辑"""
    init_db()
    
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            return {"error": "租户未初始化，请先运行 cli.py init"}
        
        tenant_id = tenant.id
        
        if name == "search_videos":
            return await tool_search_videos(db, tenant_id, args)
        elif name == "get_video_summary":
            return await tool_get_video_summary(db, tenant_id, args)
        elif name == "get_video_transcript":
            return await tool_get_video_transcript(db, tenant_id, args)
        elif name == "ask_knowledge":
            return await tool_ask_knowledge(db, tenant_id, args)
        elif name == "list_recent_videos":
            return await tool_list_recent_videos(db, tenant_id, args)
        elif name == "get_stats":
            return await tool_get_stats(db, tenant_id)
        else:
            return {"error": f"Unknown tool: {name}"}


async def tool_search_videos(db, tenant_id: int, args: dict) -> dict:
    """搜索视频"""
    query = args.get("query", "")
    limit = args.get("limit", 10)
    
    videos = (
        db.query(Video)
        .filter(
            Video.tenant_id == tenant_id,
            Video.title.ilike(f"%{query}%"),
        )
        .limit(limit)
        .all()
    )
    
    return {
        "query": query,
        "count": len(videos),
        "videos": [
            {
                "source_id": v.source_id,
                "title": v.title,
                "author": v.author,
                "status": v.status.value,
                "summary": v.summary[:200] if v.summary else None,
            }
            for v in videos
        ],
    }


async def tool_get_video_summary(db, tenant_id: int, args: dict) -> dict:
    """获取视频摘要"""
    bvid = args.get("source_id", "")
    
    video = (
        db.query(Video)
        .filter(Video.tenant_id == tenant_id, Video.source_id == bvid)
        .first()
    )
    
    if not video:
        return {"error": f"视频不存在: {bvid}"}
    
    key_points = []
    if video.key_points:
        try:
            key_points = json.loads(video.key_points)
        except json.JSONDecodeError:
            pass
    
    concepts = []
    if video.concepts:
        try:
            concepts = json.loads(video.concepts)
        except json.JSONDecodeError:
            pass
    
    return {
        "source_id": video.source_id,
        "title": video.title,
        "author": video.author,
        "summary": video.summary,
        "key_points": key_points,
        "concepts": concepts,
        "status": video.status.value,
    }


async def tool_get_video_transcript(db, tenant_id: int, args: dict) -> dict:
    """获取转写文本"""
    from pathlib import Path
    
    bvid = args.get("source_id", "")
    
    video = (
        db.query(Video)
        .filter(Video.tenant_id == tenant_id, Video.source_id == bvid)
        .first()
    )
    
    if not video:
        return {"error": f"视频不存在: {bvid}"}
    
    if not video.transcript_path:
        return {"error": "视频尚未转写"}
    
    path = Path(video.transcript_path)
    if not path.exists():
        return {"error": "转写文件不存在"}
    
    transcript = path.read_text(encoding="utf-8")
    
    return {
        "source_id": video.source_id,
        "title": video.title,
        "transcript": transcript,
        "length": len(transcript),
    }


async def tool_ask_knowledge(db, tenant_id: int, args: dict) -> dict:
    """知识库问答"""
    from alice.rag import RAGService, FallbackRAGService
    
    question = args.get("question", "")
    
    rag = RAGService()
    
    if not rag.is_available():
        rag = FallbackRAGService(db)
    
    result = rag.ask(tenant_id=tenant_id, question=question)
    
    return {
        "question": question,
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }


async def tool_list_recent_videos(db, tenant_id: int, args: dict) -> dict:
    """列出最近视频"""
    limit = args.get("limit", 10)
    status_filter = args.get("status")
    
    query = db.query(Video).filter(Video.tenant_id == tenant_id)
    
    if status_filter:
        try:
            status_enum = VideoStatus(status_filter)
            query = query.filter(Video.status == status_enum)
        except ValueError:
            pass
    
    videos = query.order_by(Video.created_at.desc()).limit(limit).all()
    
    return {
        "count": len(videos),
        "videos": [
            {
                "source_id": v.source_id,
                "title": v.title,
                "author": v.author,
                "status": v.status.value,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in videos
        ],
    }


async def tool_get_stats(db, tenant_id: int) -> dict:
    """获取统计"""
    total = db.query(Video).filter(Video.tenant_id == tenant_id).count()
    done = db.query(Video).filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.DONE).count()
    pending = db.query(Video).filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.PENDING).count()
    failed = db.query(Video).filter(Video.tenant_id == tenant_id, Video.status == VideoStatus.FAILED).count()
    
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "failed": failed,
        "processing": total - done - pending - failed,
    }


async def main():
    """启动MCP Server"""
    logger.info("mcp_server_starting")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
