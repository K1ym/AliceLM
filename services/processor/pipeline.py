"""
视频处理管道
编排：下载 → 提取音频 → 转写 → 保存
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from packages.db import Video, VideoStatus
from packages.logging import get_logger
from services.asr import ASRManager, TranscriptResult, create_api_asr

from .audio import AudioProcessor
from .downloader import VideoDownloader

logger = get_logger(__name__)


class VideoPipeline:
    """视频处理管道"""

    def __init__(
        self,
        video_dir: str = "data/videos",
        audio_dir: str = "data/audio",
        transcript_dir: str = "data/transcripts",
        sessdata: Optional[str] = None,
        notify: bool = True,
    ):
        self.downloader = VideoDownloader(video_dir)
        self.audio_processor = AudioProcessor(audio_dir)
        self.asr_manager = ASRManager()
        self.transcript_dir = Path(transcript_dir)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.sessdata = sessdata
        
        # 通知器
        from services.notifier import WeChatWorkNotifier
        self.notifier = WeChatWorkNotifier() if notify else None

    def _get_asr_provider(self, db: Session, user_id: int):
        """
        获取ASR提供者
        优先使用用户配置的API ASR，否则使用本地ASR
        """
        from apps.api.routers.config import get_task_llm_config
        
        # 获取用户配置的ASR任务模型
        asr_config = get_task_llm_config(db, user_id, "asr")
        
        if asr_config.get("api_key") and asr_config.get("base_url") and asr_config.get("model"):
            logger.info(
                "using_api_asr",
                user_id=user_id,
                model=asr_config["model"],
                base_url=asr_config["base_url"],
            )
            return create_api_asr(
                base_url=asr_config["base_url"],
                api_key=asr_config["api_key"],
                model=asr_config["model"],
            )
        
        # 回退到本地ASR
        logger.info("using_local_asr", user_id=user_id)
        return self.asr_manager
    
    def _get_summarizer(self, db: Session, user_id: int):
        """获取摘要分析器，使用用户配置的模型"""
        from apps.api.routers.config import get_task_llm_config
        from services.ai import Summarizer
        from services.ai.llm import create_llm_from_config
        
        # 获取用户配置的summary任务模型
        llm_config = get_task_llm_config(db, user_id, "summary")
        
        if llm_config.get("api_key") and llm_config.get("base_url"):
            llm = create_llm_from_config(
                base_url=llm_config["base_url"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
            )
            logger.info("using_user_summary_model", model=llm_config["model"])
            return Summarizer(llm_manager=llm)
        
        return Summarizer()

    def process(self, video: Video, db: Session, user_id: Optional[int] = None) -> Video:
        """
        处理单个视频
        
        Args:
            video: Video对象
            db: 数据库会话
            user_id: 用户ID（用于获取用户配置的模型）
            
        Returns:
            更新后的Video对象
        """
        # 获取用户ID（如果没传入，从tenant获取默认用户）
        if user_id is None:
            from packages.db import User
            user = db.query(User).filter(User.tenant_id == video.tenant_id).first()
            user_id = user.id if user else None
        
        try:
            # Step 1: 下载音频（优先BBDown，可获取AI字幕）
            video.status = VideoStatus.DOWNLOADING.value
            db.commit()
            
            logger.info("pipeline_step", step="download", bvid=video.bvid)
            
            ai_subtitle = None
            audio_path = None
            
            # 尝试使用BBDown下载音频+AI字幕
            try:
                from services.downloader import get_bbdown_service, DownloadMode
                bbdown = get_bbdown_service()
                if bbdown.bbdown_path:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            bbdown.download_video(video.bvid, mode=DownloadMode.AUDIO, with_subtitle=True)
                        )
                        if result.success and result.file_path:
                            audio_path = result.file_path
                            if result.subtitle_path and result.subtitle_path.exists():
                                ai_subtitle = result.subtitle_path.read_text(encoding="utf-8")
                                logger.info("ai_subtitle_found", bvid=video.bvid)
                            logger.info("bbdown_download_success", bvid=video.bvid)
                    finally:
                        loop.close()
            except Exception as e:
                logger.warning("bbdown_failed", bvid=video.bvid, error=str(e))
            
            # 回退到yt-dlp
            if audio_path is None:
                logger.info("fallback_to_ytdlp", bvid=video.bvid)
                video_path = self.downloader.download_bilibili(video.bvid, self.sessdata)
                video.video_path = str(video_path)
                db.commit()
                
                # 提取音频
                logger.info("pipeline_step", step="extract_audio", bvid=video.bvid)
                audio_path = self.audio_processor.extract_audio(video_path, video.bvid)
                
                # 删除原视频文件
                try:
                    if video_path.exists():
                        video_path.unlink()
                        logger.info("video_file_deleted", bvid=video.bvid, path=str(video_path))
                    video.video_path = None
                    db.commit()
                except Exception as e:
                    logger.warning("video_delete_failed", bvid=video.bvid, error=str(e))
            
            video.audio_path = str(audio_path)
            db.commit()

            # Step 2: 转写
            video.status = VideoStatus.TRANSCRIBING.value
            db.commit()
            
            logger.info("pipeline_step", step="transcribe", bvid=video.bvid)
            
            # 如果有AI字幕，直接使用（跳过ASR）
            if ai_subtitle:
                logger.info("using_ai_subtitle", bvid=video.bvid)
                from services.asr import TranscriptResult, TranscriptSegment
                result = TranscriptResult(
                    text=ai_subtitle,
                    language="zh",
                    duration=video.duration or 0,
                    segments=[TranscriptSegment(start=0, end=video.duration or 0, text=ai_subtitle)],
                )
            else:
                # 使用ASR转写
                if user_id:
                    asr_provider = self._get_asr_provider(db, user_id)
                    result = asr_provider.transcribe(str(audio_path))
                else:
                    result = self.asr_manager.transcribe(str(audio_path))
            
            # 保存转写结果
            transcript_path = self._save_transcript(video.bvid, result)
            video.transcript_path = str(transcript_path)
            db.commit()

            # Step 4: AI分析（使用用户配置的摘要模型）
            video.status = VideoStatus.ANALYZING.value
            db.commit()
            
            try:
                logger.info("pipeline_step", step="analyze", bvid=video.bvid)
                summarizer = self._get_summarizer(db, user_id) if user_id else None
                if summarizer is None:
                    from services.ai import Summarizer
                    summarizer = Summarizer()
                    
                analysis = summarizer.analyze(
                    transcript=result.text,
                    title=video.title,
                    author=video.author,
                    duration=video.duration or 0,
                )
                
                video.summary = analysis.summary
                video.key_points = json.dumps(analysis.key_points, ensure_ascii=False)
                video.concepts = json.dumps(analysis.concepts, ensure_ascii=False)
                db.commit()
                
                logger.info(
                    "analysis_complete",
                    bvid=video.bvid,
                    summary_length=len(analysis.summary),
                )
            except Exception as e:
                # AI分析失败不阻塞流程
                logger.warning("analysis_skipped", bvid=video.bvid, error=str(e))

            # Step 5: 向量化（索引到知识库）
            video.status = VideoStatus.INDEXING.value
            db.commit()
            
            try:
                logger.info("pipeline_step", step="indexing", bvid=video.bvid)
                self._index_to_rag(video, result.text, db, user_id)
            except Exception as e:
                # 向量化失败不阻塞流程
                logger.warning("indexing_skipped", bvid=video.bvid, error=str(e))

            # Step 6: 完成
            video.status = VideoStatus.DONE.value
            video.processed_at = datetime.utcnow()
            db.commit()

            logger.info(
                "pipeline_complete",
                bvid=video.bvid,
                text_length=len(result.text),
            )

            # Step 6: 发送通知（增强版，带摘要）
            if self.notifier and self.notifier.is_configured():
                # 优先使用摘要，否则用转写预览
                notify_content = video.summary or result.text[:200]
                self.notifier.send_video_complete(
                    bvid=video.bvid,
                    title=video.title,
                    transcript_preview=notify_content,
                )

            return video

        except Exception as e:
            video.status = VideoStatus.FAILED.value
            video.error_message = str(e)
            video.retry_count += 1
            db.commit()
            
            logger.error("pipeline_failed", bvid=video.bvid, error=str(e))
            
            # 发送失败通知
            if self.notifier and self.notifier.is_configured():
                self.notifier.send_error(
                    bvid=video.bvid,
                    title=video.title,
                    error=str(e),
                )
            
            raise

    def _index_to_rag(self, video: Video, transcript: str, db: Session, user_id: int = None):
        """
        索引视频到向量知识库
        
        Args:
            video: 视频对象
            transcript: 转写文本
            db: 数据库会话
            user_id: 用户ID（用于获取用户配置的 embedding）
        """
        from services.ai.rag import RAGService, get_rag_client
        
        # 获取 RAG 客户端（带用户配置）
        client = get_rag_client(user_id=user_id)
        rag_service = RAGService(client=client)
        
        # 索引视频
        doc_id = rag_service.index_video(
            tenant_id=video.tenant_id,
            video=video,
            transcript=transcript,
        )
        
        logger.info(
            "video_indexed",
            video_id=video.id,
            bvid=video.bvid,
            doc_id=doc_id,
        )

    def _save_transcript(self, bvid: str, result: TranscriptResult) -> Path:
        """保存转写结果"""
        # 保存纯文本
        txt_path = self.transcript_dir / f"{bvid}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.text)

        # 保存带时间戳的JSON
        json_path = self.transcript_dir / f"{bvid}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "text": result.text,
                    "language": result.language,
                    "duration": result.duration,
                    "segments": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                        }
                        for seg in result.segments
                    ],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info("transcript_saved", bvid=bvid, path=str(txt_path))
        return txt_path

    def process_pending(self, db: Session, tenant_id: int, limit: int = 10) -> list:
        """
        处理待处理的视频
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            limit: 最大处理数量
            
        Returns:
            处理的视频列表
        """
        videos = (
            db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.status == VideoStatus.PENDING,
            )
            .limit(limit)
            .all()
        )

        processed = []
        for video in videos:
            try:
                self.process(video, db)
                processed.append(video)
            except Exception as e:
                logger.error("process_video_failed", bvid=video.bvid, error=str(e))
                continue

        return processed
