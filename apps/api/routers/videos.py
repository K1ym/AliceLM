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

from ..deps import get_db, get_current_user, get_current_tenant
from ..schemas import (
    VideoSummary,
    VideoDetail,
    VideoTranscript,
    PaginatedResponse,
)

router = APIRouter()


# ========== 视频导入 ==========

class VideoImportRequest(BaseModel):
    """视频导入请求"""
    url: str = Field(..., description="B站视频URL或BV号")
    auto_process: bool = Field(default=True, description="是否自动处理")


class VideoImportResponse(BaseModel):
    """视频导入响应"""
    id: int
    bvid: str
    title: str
    status: str
    message: str


@router.post("", response_model=VideoImportResponse)
async def import_video(
    request: VideoImportRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    导入B站视频
    
    支持URL格式:
    - https://www.bilibili.com/video/BV1xx411c7mD
    - https://b23.tv/xxxxx (短链接)
    - BV1xx411c7mD
    - 包含BV号的任意文本
    """
    import re
    import httpx
    
    url_or_text = request.url.strip()
    
    # 如果包含b23.tv短链接，先解析真实URL
    b23_match = re.search(r'https?://b23\.tv/([a-zA-Z0-9]+)', url_or_text)
    if b23_match:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.head(f"https://b23.tv/{b23_match.group(1)}")
                url_or_text = str(resp.url)
        except Exception as e:
            logger.warning("b23_redirect_failed", error=str(e))
    
    # 解析BV号
    bvid_match = re.search(r'(BV[a-zA-Z0-9]+)', url_or_text)
    if not bvid_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的B站视频URL或BV号",
        )
    
    bvid = bvid_match.group(1)
    
    # 检查是否已存在
    existing = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.bvid == bvid)
        .first()
    )
    
    if existing:
        return VideoImportResponse(
            id=existing.id,
            bvid=existing.bvid,
            title=existing.title,
            status=existing.status,
            message="视频已存在",
        )
    
    # 获取视频信息（使用BilibiliClient复用已有逻辑）
    try:
        from services.watcher import BilibiliClient
        
        client = BilibiliClient()
        # 使用B站API获取视频详情
        info = client._request(
            "https://api.bilibili.com/x/web-interface/view",
            {"bvid": bvid}
        )
        client.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取视频信息失败: {e}",
        )
    
    # 创建视频记录
    video = Video(
        tenant_id=tenant.id,
        bvid=bvid,
        title=info.get("title", bvid),
        author=info.get("owner", {}).get("name", ""),
        duration=info.get("duration", 0),
        cover_url=info.get("pic"),
        source_url=f"https://www.bilibili.com/video/{bvid}",
        status=VideoStatus.PENDING.value if request.auto_process else VideoStatus.PENDING.value,
    )
    
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return VideoImportResponse(
        id=video.id,
        bvid=video.bvid,
        title=video.title,
        status=video.status,
        message="已加入处理队列" if request.auto_process else "已添加，等待手动处理",
    )


@router.post("/batch")
async def import_videos_batch(
    urls: List[str],
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    批量导入视频
    
    最多支持20个URL
    """
    if len(urls) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次最多导入20个视频",
        )
    
    results = []
    for url in urls:
        try:
            result = await import_video(
                VideoImportRequest(url=url),
                tenant=tenant,
                db=db,
            )
            results.append({"url": url, "success": True, "data": result})
        except HTTPException as e:
            results.append({"url": url, "success": False, "error": e.detail})
    
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
    db: Session = Depends(get_db),
):
    """
    获取视频列表
    
    支持分页、状态过滤、收藏夹过滤、标题搜索
    """
    query = db.query(Video).filter(Video.tenant_id == tenant.id)
    
    # 状态过滤
    if status_filter:
        try:
            status_enum = VideoStatus(status_filter)
            query = query.filter(Video.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态: {status_filter}",
            )
    
    # 收藏夹过滤
    if folder_id:
        query = query.filter(Video.watched_folder_id == folder_id)
    
    # 标题搜索
    if search:
        query = query.filter(Video.title.ilike(f"%{search}%"))
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    videos = (
        query
        .order_by(Video.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    # 转换为响应格式
    items = [
        VideoSummary(
            id=v.id,
            bvid=v.bvid,
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
    db: Session = Depends(get_db),
):
    """获取处理队列"""
    videos = (
        db.query(Video)
        .filter(
            Video.tenant_id == tenant.id,
            Video.status.in_([
                VideoStatus.PENDING.value,
                VideoStatus.DOWNLOADING.value,
                VideoStatus.TRANSCRIBING.value,
                VideoStatus.ANALYZING.value,
            ])
        )
        .order_by(Video.created_at.asc())
        .all()
    )
    
    failed = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.FAILED.value)
        .order_by(Video.created_at.desc())
        .limit(10)
        .all()
    )
    
    done = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.DONE.value)
        .order_by(Video.processed_at.desc())
        .limit(5)
        .all()
    )
    
    def video_to_dict(v):
        return {
            "id": v.id,
            "bvid": v.bvid,
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
        "queue": [video_to_dict(v) for v in videos],
        "failed": [video_to_dict(v) for v in failed],
        "recent_done": [video_to_dict(v) for v in done],
        "queue_count": len(videos),
        "failed_count": len(failed),
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
    db: Session = Depends(get_db),
):
    """获取视频详情"""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在",
        )
    
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
        bvid=video.bvid,
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
    db: Session = Depends(get_db),
):
    """获取视频转写文本"""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在",
        )
    
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
        bvid=video.bvid,
        title=video.title,
        transcript=transcript,
        segments=segments,
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """删除视频"""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在",
        )
    
    db.delete(video)
    db.commit()
    
    return {"message": "已删除", "video_id": video_id}


@router.post("/{video_id}/reprocess")
async def reprocess_video(
    video_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """重新处理视频"""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在",
        )
    
    # 重置状态
    video.status = VideoStatus.PENDING.value
    video.error_message = None
    db.commit()
    
    return {"message": "已加入处理队列", "video_id": video_id}


@router.get("/stats/summary")
async def get_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """获取视频统计"""
    total = db.query(Video).filter(Video.tenant_id == tenant.id).count()
    
    done = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.DONE.value)
        .count()
    )
    
    pending = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.PENDING.value)
        .count()
    )
    
    failed = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.FAILED.value)
        .count()
    )
    
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "failed": failed,
        "processing": total - done - pending - failed,
    }


@router.get("/stats/tags")
async def get_top_tags(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    limit: int = Query(default=5, ge=1, le=20),
):
    """
    获取Top标签统计
    
    从已处理视频的key_points/concepts字段聚合标签
    """
    from collections import Counter
    
    videos = (
        db.query(Video)
        .filter(Video.tenant_id == tenant.id, Video.status == VideoStatus.DONE.value)
        .all()
    )
    
    tag_counter: Counter = Counter()
    
    for video in videos:
        # 解析concepts字段（JSON数组）
        if video.concepts:
            try:
                concepts = json.loads(video.concepts)
                if isinstance(concepts, list):
                    for concept in concepts:
                        if isinstance(concept, str) and concept.strip():
                            tag_counter[concept.strip()] += 1
            except json.JSONDecodeError:
                pass
    
    # 获取Top N标签
    top_tags = tag_counter.most_common(limit)
    
    return {
        "tags": [{"name": name, "count": count} for name, count in top_tags],
        "total_videos": len(videos),
    }


# ========== 立即处理视频 ==========

@router.post("/{video_id}/process")
async def process_video_now(
    video_id: int,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    立即开始处理视频（异步后台任务）
    
    用于导入后立即触发处理，而不是等待定时任务
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
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
    db: Session = Depends(get_db),
):
    """
    获取视频处理状态
    
    用于前端轮询进度
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
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
    db: Session = Depends(get_db),
):
    """
    取消视频处理
    
    将状态重置为pending，或者删除视频
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    # 只能取消pending或processing状态的任务
    if video.status == VideoStatus.DONE.value:
        return {"message": "视频已处理完成，无法取消", "status": video.status}
    
    # 重置为pending状态（如果用户想重新处理可以再触发）
    old_status = video.status
    video.status = VideoStatus.PENDING.value
    video.error_message = None
    db.commit()
    
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
    db: Session = Depends(get_db),
):
    """
    从队列中移除视频（删除视频记录）
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    # 只能删除pending或failed状态的任务
    if video.status not in [VideoStatus.PENDING.value, VideoStatus.FAILED.value]:
        raise HTTPException(
            status_code=400, 
            detail=f"只能删除等待中或失败的任务，当前状态: {video.status}"
        )
    
    db.delete(video)
    db.commit()
    
    return {"message": "已从队列移除", "video_id": video_id}


# ========== 获取B站评论 ==========

@router.get("/{video_id}/comments")
async def get_video_comments(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    获取视频的B站评论
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.tenant_id == tenant.id)
        .first()
    )
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    try:
        from services.watcher import BilibiliClient
        
        client = BilibiliClient()
        # 获取视频aid
        info = client._request(
            "https://api.bilibili.com/x/web-interface/view",
            {"bvid": video.bvid}
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
