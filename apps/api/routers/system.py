"""
系统管理路由
数据清理、存储统计等
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.db import User, Video, VideoStatus
from packages.logging import get_logger

from ..deps import get_db, get_current_user

router = APIRouter()
logger = get_logger(__name__)


class StorageStats(BaseModel):
    """存储统计"""
    total_videos: int
    processed_videos: int
    pending_videos: int
    failed_videos: int
    audio_files_count: int
    audio_files_size_mb: float
    download_files_size_mb: float
    transcript_files_size_mb: float
    total_size_mb: float


class CleanupResult(BaseModel):
    """清理结果"""
    cleaned_count: int
    freed_mb: float


@router.get("/storage", response_model=StorageStats)
async def get_storage_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取存储统计信息"""
    
    # 视频统计
    total = db.query(Video).filter(Video.tenant_id == user.tenant_id).count()
    processed = db.query(Video).filter(
        Video.tenant_id == user.tenant_id,
        Video.status == VideoStatus.DONE.value,
    ).count()
    pending = db.query(Video).filter(
        Video.tenant_id == user.tenant_id,
        Video.status == VideoStatus.PENDING.value,
    ).count()
    failed = db.query(Video).filter(
        Video.tenant_id == user.tenant_id,
        Video.status == VideoStatus.FAILED.value,
    ).count()
    
    # 文件统计
    def dir_size_mb(path: Path) -> tuple[int, float]:
        if not path.exists():
            return 0, 0.0
        files = list(path.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        total_bytes = sum(f.stat().st_size for f in files if f.is_file())
        return file_count, total_bytes / (1024 * 1024)
    
    audio_count, audio_mb = dir_size_mb(Path("data/audio"))
    _, download_mb = dir_size_mb(Path("data/downloads"))
    _, transcript_mb = dir_size_mb(Path("data/transcripts"))
    
    return StorageStats(
        total_videos=total,
        processed_videos=processed,
        pending_videos=pending,
        failed_videos=failed,
        audio_files_count=audio_count,
        audio_files_size_mb=round(audio_mb, 2),
        download_files_size_mb=round(download_mb, 2),
        transcript_files_size_mb=round(transcript_mb, 2),
        total_size_mb=round(audio_mb + download_mb + transcript_mb, 2),
    )


@router.post("/cleanup", response_model=CleanupResult)
async def cleanup_audio(
    retention_days: int = 1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    手动清理已处理视频的音频文件
    
    Args:
        retention_days: 保留天数，默认1天
    """
    from services.scheduler.jobs import job_cleanup_audio
    
    logger.info("manual_cleanup_triggered", user_id=user.id, retention_days=retention_days)
    
    result = job_cleanup_audio(retention_days=retention_days)
    
    return CleanupResult(
        cleaned_count=result["cleaned"],
        freed_mb=result["freed_mb"],
    )
