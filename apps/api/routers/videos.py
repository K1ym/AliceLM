"""
视频路由
P3-02: 视频CRUD API
"""

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import Video, VideoStatus, Tenant, User
from packages.logging import get_logger

from ..deps import get_db, get_current_user, get_current_tenant, get_video_service
from ..services import VideoService
from ..exceptions import ValidationException, NotFoundException
from ..schemas import (
    VideoSummary,
    VideoDetail,
    VideoTranscript,
    PaginatedResponse,
)

logger = get_logger(__name__)

router = APIRouter()


# ========== 视频导入 ==========

class VideoImportRequest(BaseModel):
    """视频导入请求"""
    url: Optional[str] = Field(None, description="视频URL（B站/其他源）")
    source_type: str = Field(default="bilibili", description="内容源类型，如 bilibili")
    source_id: Optional[str] = Field(None, description="内容源ID，如 bvid")
    bvid: Optional[str] = Field(None, alias="bvid", description="向后兼容的BV号别名")
    auto_process: bool = Field(default=True, description="是否自动处理")


class VideoImportResponse(BaseModel):
    """视频导入响应"""
    id: int
    source_type: str
    source_id: str
    title: str
    status: str
    message: str


@router.post("", response_model=VideoImportResponse)
async def import_video(
    request: VideoImportRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """导入B站视频"""
    source_id = request.source_id or request.bvid
    source_type = request.source_type or "bilibili"

    if not source_id and not request.url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "必须提供 source_id 或 url")

    try:
        video, is_new = await service.import_video(
            source_type=source_type,
            source_id=source_id,
            url=request.url,
            auto_process=request.auto_process,
        )
        return VideoImportResponse(
            id=video.id,
            source_type=video.source_type,
            source_id=video.source_id,
            title=video.title,
            status=video.status,
            message="已加入处理队列" if is_new else "视频已存在",
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/batch")
async def import_videos_batch(
    urls: List[str],
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """批量导入视频（最多20个）"""
    if len(urls) > 20:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "单次最多导入20个视频")
    
    results = []
    for url in urls:
        try:
            video, is_new = await service.import_video(
                url=url,
                tenant=tenant,
                source_type="bilibili",
            )
            results.append({
                "url": url,
                "success": True,
                "data": VideoImportResponse(
                    id=video.id,
                    source_type=video.source_type,
                    source_id=video.source_id,
                    title=video.title,
                    status=video.status,
                    message="已加入处理队列" if is_new else "视频已存在",
                ),
            })
        except (ValueError, Exception) as e:
            results.append({"url": url, "success": False, "error": str(e)})
    
    return {
        "total": len(urls),
        "success": sum(1 for r in results if r["success"]),
        "results": results,
    }


@router.get("", response_model=PaginatedResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    folder_id: Optional[int] = Query(None, description="收藏夹过滤"),
    search: Optional[str] = Query(None, description="标题搜索"),
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """
    获取视频列表
    
    支持分页、状态过滤、收藏夹过滤、标题搜索
    """
    # 验证状态
    if status_filter:
        try:
            VideoStatus(status_filter)
        except ValueError:
            raise ValidationException(f"无效的状态: {status_filter}", field="status")
    
    # 使用 Service 获取数据
    skip = (page - 1) * page_size
    videos, total = service.list_videos(
        tenant_id=tenant.id,
        skip=skip,
        limit=page_size,
        status=status_filter,
        folder_id=folder_id,
        search=search,
    )
    
    # 转换为响应格式
    items = [
        VideoSummary(
            id=v.id,
            source_type=v.source_type,
            source_id=v.source_id,
            title=v.title,
            author=v.author,
            duration=v.duration,
            cover_url=v.cover_url,
            status=v.status,
            summary=v.summary,
            created_at=v.created_at,
            processed_at=v.processed_at,
        )
        for v in videos
    ]
    
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )


# ========== 处理队列（必须在 /{video_id} 之前） ==========

@router.get("/queue/list")
async def get_processing_queue(
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取处理队列"""
    queue_data = service.get_processing_queue(tenant.id)
    
    def video_to_dict(v):
        return {
            "id": v.id,
            "source_id": v.source_id,
            "title": v.title,
            "status": v.status,
            "error_message": v.error_message,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "processed_at": v.processed_at.isoformat() if v.processed_at else None,
        }
    
    # 获取并行队列信息
    from services.processor.queue import get_video_queue
    queue_info = get_video_queue().get_queue_info()
    
    return {
        "queue": [video_to_dict(v) for v in queue_data["processing"]],
        "failed": [video_to_dict(v) for v in queue_data["failed"]],
        "recent_done": [video_to_dict(v) for v in queue_data["done"]],
        "queue_count": queue_data["counts"]["processing"],
        "failed_count": queue_data["counts"]["failed"],
        "parallel_queue": queue_info,
    }


@router.get("/queue/info")
async def get_queue_info():
    """获取并行处理队列信息"""
    from services.processor.queue import get_video_queue
    return get_video_queue().get_queue_info()


@router.get("/{video_id}", response_model=VideoDetail)
async def get_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取视频详情"""
    video = service.get_video(video_id, tenant.id)
    
    if not video:
        raise NotFoundException("视频", video_id)
    
    # 解析JSON字段
    key_points = None
    concepts = None
    tags = None
    
    if video.key_points:
        try:
            key_points = json.loads(video.key_points)
        except json.JSONDecodeError:
            pass
    
    if video.concepts:
        try:
            concepts = json.loads(video.concepts)
        except json.JSONDecodeError:
            pass
    
    return VideoDetail(
        id=video.id,
        source_type=video.source_type,
        source_id=video.source_id,
        title=video.title,
        author=video.author,
        duration=video.duration,
        cover_url=video.cover_url,
        status=video.status,
        summary=video.summary,
        created_at=video.created_at,
        processed_at=video.processed_at,
        transcript_path=video.transcript_path,
        key_points=key_points,
        concepts=concepts,
        tags=tags,
        error_message=video.error_message,
    )


@router.get("/{video_id}/transcript", response_model=VideoTranscript)
async def get_transcript(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取视频转写文本"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    if not video.transcript_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转写文本不存在",
        )
    
    transcript_path = Path(video.transcript_path)
    
    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="转写文件不存在",
        )
    
    transcript = transcript_path.read_text(encoding="utf-8")
    
    # 尝试读取带时间戳的JSON版本
    segments = []
    json_path = transcript_path.with_suffix(".json")
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            segments = data.get("segments", [])
        except json.JSONDecodeError:
            pass
    
    # 如果没有分段信息，按段落生成segments
    if not segments and transcript:
        paragraphs = [p.strip() for p in transcript.split('\n') if p.strip()]
        if not paragraphs:
            paragraphs = [transcript]
        # 按段落生成伪segments（无时间戳）
        segments = [
            {"id": i, "start": 0, "end": 0, "text": p}
            for i, p in enumerate(paragraphs)
        ]
    
    return VideoTranscript(
        source_type=video.source_type,
        source_id=video.source_id,
        title=video.title,
        transcript=transcript,
        segments=segments,
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """删除视频"""
    if not service.delete_video(video_id, tenant.id):
        raise NotFoundException("视频", video_id)
    
    return {"message": "已删除", "video_id": video_id}


@router.post("/{video_id}/reprocess")
async def reprocess_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """重新处理视频"""
    video = service.reprocess_video(video_id, tenant.id)
    
    if not video:
        raise NotFoundException("视频", video_id)
    
    return {"message": "已加入处理队列", "video_id": video_id}


@router.get("/stats/summary")
async def get_stats(
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取视频统计"""
    return service.get_stats(tenant.id)


@router.get("/stats/tags")
async def get_top_tags(
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
    limit: int = Query(default=5, ge=1, le=20),
):
    """获取Top标签统计"""
    tags = service.get_top_tags(tenant.id, limit)
    return {
        "tags": [{"name": t["tag"], "count": t["count"]} for t in tags],
        "total_tags": len(tags),
    }


# ========== 立即处理视频 ==========

@router.post("/{video_id}/process")
async def process_video_now(
    video_id: int,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """立即开始处理视频"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    if video.status not in [VideoStatus.PENDING.value, VideoStatus.FAILED.value]:
        return {
            "message": f"视频状态为 {video.status}，无需处理",
            "status": video.status,
        }
    
    # 使用并行处理队列
    from services.processor.queue import get_video_queue
    
    queue = get_video_queue()
    submitted = queue.submit(video_id=video_id, user_id=user.id)
    
    if not submitted:
        return {
            "message": "视频已在处理队列中",
            "video_id": video_id,
            "status": "already_processing",
        }
    
    queue_info = queue.get_queue_info()
    
    return {
        "message": "已加入处理队列",
        "video_id": video_id,
        "status": "processing",
        "queue": queue_info,
    }


@router.get("/{video_id}/status")
async def get_video_status(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取视频处理状态"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    return {
        "id": video.id,
        "status": video.status,
        "error_message": video.error_message,
        "has_transcript": bool(video.transcript_path),
        "has_summary": bool(video.summary),
    }


@router.post("/{video_id}/cancel")
async def cancel_video_processing(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """取消视频处理"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    if video.status == VideoStatus.DONE.value:
        return {"message": "视频已处理完成，无法取消", "status": video.status}
    
    old_status = video.status
    updated = service.update_status(video_id, tenant.id, VideoStatus.PENDING.value)
    
    return {
        "message": "已取消处理",
        "video_id": video_id,
        "old_status": old_status,
        "new_status": "pending",
    }


@router.delete("/{video_id}/queue")
async def remove_from_queue(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """从队列中移除视频"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    if video.status not in [VideoStatus.PENDING.value, VideoStatus.FAILED.value]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"只能删除等待中或失败的任务，当前: {video.status}")
    
    service.delete_video(video_id, tenant.id)
    return {"message": "已从队列移除", "video_id": video_id}


# ========== 获取B站评论 ==========

@router.get("/{video_id}/comments")
async def get_video_comments(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    tenant: Tenant = Depends(get_current_tenant),
    service: VideoService = Depends(get_video_service),
):
    """获取视频的B站评论"""
    video = service.get_video(video_id, tenant.id)
    if not video:
        raise NotFoundException("视频", video_id)
    
    try:
        from services.watcher import BilibiliClient
        
        client = BilibiliClient()
        # 获取视频aid
        info = client._request(
            "https://api.bilibili.com/x/web-interface/view",
            {"source_id": video.source_id}
        )
        aid = info.get("aid")
        
        if not aid:
            return {"comments": [], "total": 0, "has_more": False}
        
        # 获取评论
        comments_data = client._request(
            "https://api.bilibili.com/x/v2/reply",
            {
                "type": 1,  # 视频类型
                "oid": aid,
                "pn": page,
                "ps": page_size,
                "sort": 2,  # 按热度排序
            }
        )
        client.close()
        
        replies = comments_data.get("replies") or []
        total = comments_data.get("page", {}).get("count", 0)
        
        comments = []
        for reply in replies:
            member = reply.get("member", {})
            comments.append({
                "id": reply.get("rpid"),
                "content": reply.get("content", {}).get("message", ""),
                "username": member.get("uname", ""),
                "avatar": member.get("avatar", ""),
                "like_count": reply.get("like", 0),
                "reply_count": reply.get("rcount", 0),
                "created_at": reply.get("ctime", 0),
            })
        
        return {
            "comments": comments,
            "total": total,
            "page": page,
            "has_more": page * page_size < total,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评论失败: {e}")
