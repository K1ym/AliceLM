"""
定时任务定义
"""

from datetime import datetime
from typing import Optional

from packages.config import get_config
from packages.db import get_db_context, Tenant, Video, VideoStatus
from packages.logging import get_logger
from services.processor import VideoPipeline
from services.watcher import FolderScanner

logger = get_logger(__name__)


def job_scan_folders(tenant_slug: str = "default", sessdata: Optional[str] = None):
    """
    扫描收藏夹任务
    - 检查所有监控的收藏夹
    - 发现新视频入库
    """
    config = get_config()
    sessdata = sessdata or config.bilibili.sessdata

    logger.info("job_start", job="scan_folders", tenant=tenant_slug)

    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            logger.error("tenant_not_found", tenant=tenant_slug)
            return

        scanner = FolderScanner(db, tenant.id, sessdata)
        new_videos = scanner.scan_all()

        logger.info(
            "job_complete",
            job="scan_folders",
            tenant=tenant_slug,
            new_videos=len(new_videos),
        )

        return new_videos


def job_process_videos(
    tenant_slug: str = "default",
    limit: int = 5,
    sessdata: Optional[str] = None,
):
    """
    处理视频任务
    - 下载待处理视频
    - 提取音频
    - ASR转写
    """
    config = get_config()
    sessdata = sessdata or config.bilibili.sessdata

    logger.info("job_start", job="process_videos", tenant=tenant_slug, limit=limit)

    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            logger.error("tenant_not_found", tenant=tenant_slug)
            return

        pipeline = VideoPipeline(sessdata=sessdata)
        processed = pipeline.process_pending(db, tenant.id, limit=limit)

        logger.info(
            "job_complete",
            job="process_videos",
            tenant=tenant_slug,
            processed=len(processed),
        )

        return processed


def job_retry_failed(tenant_slug: str = "default", max_retries: int = 3):
    """
    重试失败任务
    - 重置符合条件的失败任务为PENDING
    """
    logger.info("job_start", job="retry_failed", tenant=tenant_slug)

    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            return

        # 查找可重试的失败任务
        failed_videos = (
            db.query(Video)
            .filter(
                Video.tenant_id == tenant.id,
                Video.status == VideoStatus.FAILED,
                Video.retry_count < max_retries,
            )
            .all()
        )

        reset_count = 0
        for video in failed_videos:
            video.status = VideoStatus.PENDING
            video.error_message = None
            reset_count += 1

        db.commit()

        logger.info(
            "job_complete",
            job="retry_failed",
            tenant=tenant_slug,
            reset_count=reset_count,
        )

        return reset_count


def job_cleanup_audio(retention_days: int = 1):
    """
    清理已处理视频的音频文件
    - 删除处理完成超过retention_days天的音频
    - 只清理状态为done的视频
    - 更新数据库中的audio_path为null
    """
    from pathlib import Path
    from datetime import timedelta
    
    logger.info("job_start", job="cleanup_audio", retention_days=retention_days)
    
    cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
    cleaned_count = 0
    freed_bytes = 0
    
    with get_db_context() as db:
        # 查找已处理且超过保留期的视频
        videos = (
            db.query(Video)
            .filter(
                Video.status == VideoStatus.DONE.value,
                Video.processed_at < cutoff_time,
                Video.audio_path.isnot(None),
            )
            .all()
        )
        
        for video in videos:
            audio_path = Path(video.audio_path)
            
            # 删除音频文件
            if audio_path.exists():
                try:
                    file_size = audio_path.stat().st_size
                    audio_path.unlink()
                    freed_bytes += file_size
                    logger.info("audio_deleted", bvid=video.bvid, path=str(audio_path))
                except Exception as e:
                    logger.warning("audio_delete_failed", bvid=video.bvid, error=str(e))
                    continue
            
            # 清理下载目录中的源文件
            for base_dir in ["data/downloads", "data/videos"]:
                target_dir = Path(base_dir) / video.bvid
                if target_dir.exists():
                    try:
                        import shutil
                        dir_size = sum(f.stat().st_size for f in target_dir.rglob("*") if f.is_file())
                        shutil.rmtree(target_dir)
                        freed_bytes += dir_size
                        logger.info("dir_deleted", bvid=video.bvid, path=base_dir)
                    except Exception as e:
                        logger.warning("dir_delete_failed", bvid=video.bvid, path=base_dir, error=str(e))
            
            # 更新数据库
            video.audio_path = None
            cleaned_count += 1
        
        db.commit()
    
    freed_mb = freed_bytes / (1024 * 1024)
    logger.info(
        "job_complete",
        job="cleanup_audio",
        cleaned_count=cleaned_count,
        freed_mb=round(freed_mb, 2),
    )
    
    return {"cleaned": cleaned_count, "freed_mb": round(freed_mb, 2)}
