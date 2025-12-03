"""
任务调度器
基于APScheduler实现定时任务
"""

from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from packages.config import get_config
from packages.logging import get_logger

from .jobs import job_scan_folders, job_process_videos, job_retry_failed, job_cleanup_audio

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度器"""

    def __init__(self, blocking: bool = False):
        """
        初始化调度器
        
        Args:
            blocking: 是否使用阻塞模式（True用于独立进程）
        """
        scheduler_class = BlockingScheduler if blocking else BackgroundScheduler
        self.scheduler = scheduler_class(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,       # 合并错过的任务
                "max_instances": 1,     # 同一任务最多1个实例
                "misfire_grace_time": 60,  # 容错时间60秒
            },
        )
        self._setup_listeners()

    def _setup_listeners(self):
        """设置事件监听器"""
        def on_job_executed(event):
            logger.info(
                "job_executed",
                job_id=event.job_id,
                scheduled_time=str(event.scheduled_run_time),
            )

        def on_job_error(event):
            logger.error(
                "job_error",
                job_id=event.job_id,
                exception=str(event.exception),
            )

        self.scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    def add_scan_job(
        self,
        interval_minutes: int = 5,
        tenant_slug: str = "default",
        sessdata: Optional[str] = None,
    ):
        """
        添加收藏夹扫描任务
        
        Args:
            interval_minutes: 扫描间隔（分钟）
            tenant_slug: 租户标识
            sessdata: B站cookie
        """
        config = get_config()
        sessdata = sessdata or config.bilibili.sessdata

        self.scheduler.add_job(
            job_scan_folders,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=f"scan_folders_{tenant_slug}",
            name=f"扫描收藏夹 ({tenant_slug})",
            kwargs={"tenant_slug": tenant_slug, "sessdata": sessdata},
            replace_existing=True,
        )

        logger.info(
            "job_added",
            job="scan_folders",
            interval=f"{interval_minutes}min",
            tenant=tenant_slug,
        )

    def add_process_job(
        self,
        interval_minutes: int = 10,
        tenant_slug: str = "default",
        limit: int = 3,
        sessdata: Optional[str] = None,
    ):
        """
        添加视频处理任务
        
        Args:
            interval_minutes: 处理间隔（分钟）
            tenant_slug: 租户标识
            limit: 每次处理数量
            sessdata: B站cookie
        """
        config = get_config()
        sessdata = sessdata or config.bilibili.sessdata

        self.scheduler.add_job(
            job_process_videos,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=f"process_videos_{tenant_slug}",
            name=f"处理视频 ({tenant_slug})",
            kwargs={
                "tenant_slug": tenant_slug,
                "limit": limit,
                "sessdata": sessdata,
            },
            replace_existing=True,
        )

        logger.info(
            "job_added",
            job="process_videos",
            interval=f"{interval_minutes}min",
            limit=limit,
        )

    def add_retry_job(
        self,
        cron_hour: int = 3,
        tenant_slug: str = "default",
    ):
        """
        添加失败重试任务（每天凌晨执行）
        
        Args:
            cron_hour: 执行小时（0-23）
            tenant_slug: 租户标识
        """
        self.scheduler.add_job(
            job_retry_failed,
            trigger=CronTrigger(hour=cron_hour, minute=0),
            id=f"retry_failed_{tenant_slug}",
            name=f"重试失败任务 ({tenant_slug})",
            kwargs={"tenant_slug": tenant_slug},
            replace_existing=True,
        )

        logger.info("job_added", job="retry_failed", cron=f"{cron_hour}:00")

    def add_cleanup_job(
        self,
        cron_hour: int = 4,
        retention_days: int = 1,
    ):
        """
        添加音频清理任务（每天凌晨执行）
        
        Args:
            cron_hour: 执行小时（0-23）
            retention_days: 保留天数
        """
        self.scheduler.add_job(
            job_cleanup_audio,
            trigger=CronTrigger(hour=cron_hour, minute=0),
            id="cleanup_audio",
            name="清理音频文件",
            kwargs={"retention_days": retention_days},
            replace_existing=True,
        )

        logger.info("job_added", job="cleanup_audio", cron=f"{cron_hour}:00", retention_days=retention_days)

    def setup_default_jobs(self, sessdata: Optional[str] = None):
        """设置默认任务集"""
        self.add_scan_job(interval_minutes=5, sessdata=sessdata)
        self.add_process_job(interval_minutes=10, limit=3, sessdata=sessdata)
        self.add_retry_job(cron_hour=3)
        self.add_cleanup_job(cron_hour=4, retention_days=1)

    def start(self):
        """启动调度器"""
        logger.info("scheduler_starting")
        self.scheduler.start()
        logger.info("scheduler_started", jobs=len(self.scheduler.get_jobs()))

    def shutdown(self, wait: bool = True):
        """停止调度器"""
        logger.info("scheduler_stopping")
        self.scheduler.shutdown(wait=wait)
        logger.info("scheduler_stopped")

    def list_jobs(self):
        """列出所有任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs

    def run_job_now(self, job_id: str):
        """立即执行指定任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            job.func(**job.kwargs)
            logger.info("job_run_manually", job_id=job_id)
        else:
            logger.warning("job_not_found", job_id=job_id)
