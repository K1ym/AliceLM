"""
视频处理队列
支持多视频并行处理
"""

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from packages.logging import get_logger
from alice.errors import AliceError, NetworkError

logger = get_logger(__name__)

# 最大并行处理视频数
MAX_PARALLEL_VIDEOS = 2


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingTask:
    video_id: int
    user_id: int
    status: TaskStatus
    future: Optional[Future] = None
    error: Optional[str] = None


class VideoProcessingQueue:
    """
    视频处理队列管理器
    
    单例模式，全局共享一个队列
    支持：
    - 最多 N 个视频并行处理
    - 任务取消
    - 状态查询
    """
    
    _instance: Optional["VideoProcessingQueue"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_PARALLEL_VIDEOS,
            thread_name_prefix="video_processor",
        )
        self._tasks: Dict[int, ProcessingTask] = {}
        self._tasks_lock = threading.Lock()
        self._initialized = True
        
        logger.info("video_queue_initialized", max_parallel=MAX_PARALLEL_VIDEOS)
    
    def submit(self, video_id: int, user_id: int) -> bool:
        """
        提交视频处理任务
        
        Returns:
            True 如果成功提交，False 如果已在处理中
        """
        with self._tasks_lock:
            # 检查是否已在处理
            if video_id in self._tasks:
                existing = self._tasks[video_id]
                if existing.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
                    logger.warning("video_already_processing", video_id=video_id)
                    return False
            
            # 创建任务
            task = ProcessingTask(
                video_id=video_id,
                user_id=user_id,
                status=TaskStatus.QUEUED,
            )
            self._tasks[video_id] = task
        
        # 提交到线程池
        future = self._executor.submit(self._process_video, video_id, user_id)
        future.add_done_callback(lambda f: self._on_task_complete(video_id, f))
        
        with self._tasks_lock:
            if video_id in self._tasks:
                self._tasks[video_id].future = future
                self._tasks[video_id].status = TaskStatus.RUNNING
        
        logger.info("video_task_submitted", video_id=video_id, user_id=user_id)
        return True
    
    def _process_video(self, video_id: int, user_id: int):
        """执行视频处理"""
        from packages.db import get_db_context, Video
        from services.processor import VideoPipeline
        from packages.config import get_config
        
        logger.info("video_processing_started", video_id=video_id, user_id=user_id)
        
        try:
            config = get_config()
            with get_db_context() as db:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    pipeline = VideoPipeline(sessdata=config.bilibili.sessdata)
                    pipeline.process(video, db, user_id=user_id)
                    logger.info("video_processing_completed", video_id=video_id)
                else:
                    raise ValueError(f"Video {video_id} not found")
        except (NetworkError, OSError, IOError) as e:
            logger.error("video_processing_failed_network", video_id=video_id, error=str(e), exc_info=True)
            raise
        except Exception as e:
            logger.exception("video_processing_failed_unexpected", video_id=video_id)
            raise
    
    def _on_task_complete(self, video_id: int, future: Future):
        """任务完成回调"""
        with self._tasks_lock:
            if video_id not in self._tasks:
                return
            
            task = self._tasks[video_id]
            
            if future.cancelled():
                task.status = TaskStatus.CANCELLED
            elif future.exception():
                task.status = TaskStatus.FAILED
                task.error = str(future.exception())
            else:
                task.status = TaskStatus.COMPLETED
    
    def cancel(self, video_id: int) -> bool:
        """
        取消视频处理任务
        
        Returns:
            True 如果成功取消，False 如果无法取消
        """
        with self._tasks_lock:
            if video_id not in self._tasks:
                return False
            
            task = self._tasks[video_id]
            if task.future and not task.future.done():
                cancelled = task.future.cancel()
                if cancelled:
                    task.status = TaskStatus.CANCELLED
                    logger.info("video_task_cancelled", video_id=video_id)
                return cancelled
            
            return False
    
    def get_status(self, video_id: int) -> Optional[TaskStatus]:
        """获取任务状态"""
        with self._tasks_lock:
            if video_id in self._tasks:
                return self._tasks[video_id].status
            return None
    
    def get_queue_info(self) -> dict:
        """获取队列信息"""
        with self._tasks_lock:
            running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
            queued = sum(1 for t in self._tasks.values() if t.status == TaskStatus.QUEUED)
            
            return {
                "max_parallel": MAX_PARALLEL_VIDEOS,
                "running": running,
                "queued": queued,
                "total_tasks": len(self._tasks),
            }
    
    def shutdown(self, wait: bool = True):
        """关闭队列"""
        logger.info("video_queue_shutdown", wait=wait)
        self._executor.shutdown(wait=wait)


# 全局队列实例
_queue: Optional[VideoProcessingQueue] = None


def get_video_queue() -> VideoProcessingQueue:
    """获取视频处理队列单例"""
    global _queue
    if _queue is None:
        _queue = VideoProcessingQueue()
    return _queue
