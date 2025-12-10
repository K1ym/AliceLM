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
from alice.errors import AliceError, NetworkError
from services.asr import ASRManager, TranscriptResult, create_api_asr

# 控制平面
from alice.control_plane import get_control_plane

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
        使用控制平面获取 ASR 模型配置
        """
        cp = get_control_plane()
        
        # 同步获取 ASR 模型配置
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            resolved = loop.run_until_complete(
                cp.resolve_model("asr", user_id=user_id)
            )
        finally:
            loop.close()
        
        if resolved.api_key and resolved.base_url:
            logger.info(
                "using_api_asr",
                user_id=user_id,
                model=resolved.model,
                base_url=resolved.base_url,
            )
            return create_api_asr(
                base_url=resolved.base_url,
                api_key=resolved.api_key,
                model=resolved.model,
            )
        
        # 回退到本地ASR
        logger.info("using_local_asr", user_id=user_id)
        return self.asr_manager
    
    def _get_summarizer(self, db: Session, user_id: int):
        """获取摘要分析器，使用控制平面获取模型配置"""
        from services.ai import Summarizer
        
        cp = get_control_plane()
        llm = cp.create_llm_for_task_sync("summary", user_id=user_id)
        
        logger.info("using_summary_model_from_control_plane", user_id=user_id)
        return Summarizer(llm_manager=llm)

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
            
            logger.info("pipeline_step", step="download", source_type=video.source_type, source_id=video.source_id)

            ai_subtitle = None
            audio_path = None

            # 使用统一下载器接口
            try:
                from services.downloader import get_downloader, DownloadMode
                import asyncio

                downloader = get_downloader(video.source_type)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        downloader.download(video.source_id, mode=DownloadMode.AUDIO)
                    )
                    if result.success and result.file_path:
                        audio_path = result.file_path
                        if result.subtitle_content:
                            ai_subtitle = result.subtitle_content
                            logger.info("subtitle_found", source_id=video.source_id)
                        logger.info("download_success", source_type=video.source_type, source_id=video.source_id)
                finally:
                    loop.close()
            except (NetworkError, OSError, IOError) as e:
                logger.error("download_failed", source_id=video.source_id, error=str(e), exc_info=True)
            except Exception as e:
                logger.exception("download_failed_unexpected", source_id=video.source_id)

            # 如果统一下载器失败，回退到旧逻辑（仅 bilibili）
            if audio_path is None and video.source_type == "bilibili":
                logger.info("fallback_to_legacy", source_id=video.source_id)
                video_path = self.downloader.download_bilibili(video.source_id, self.sessdata)
                video.video_path = str(video_path)
                db.commit()

                # 提取音频
                logger.info("pipeline_step", step="extract_audio", source_id=video.source_id)
                audio_path = self.audio_processor.extract_audio(video_path, video.source_id)
                
                # 删除原视频文件
                try:
                    if video_path.exists():
                        video_path.unlink()
                        logger.info("video_file_deleted", source_id=video.source_id, path=str(video_path))
                    video.video_path = None
                    db.commit()
                except (OSError, IOError) as e:
                    logger.error("video_delete_failed", source_id=video.source_id, error=str(e), exc_info=True)
                except Exception:
                    logger.exception("video_delete_failed_unexpected", source_id=video.source_id)
            
            video.audio_path = str(audio_path)
            db.commit()

            # Step 2: 转写
            video.status = VideoStatus.TRANSCRIBING.value
            db.commit()
            
            logger.info("pipeline_step", step="transcribe", source_id=video.source_id)
            
            # 如果有AI字幕，直接使用（跳过ASR）
            if ai_subtitle:
                logger.info("using_ai_subtitle", source_id=video.source_id)
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
            transcript_path = self._save_transcript(video.source_id, result)
            video.transcript_path = str(transcript_path)
            db.commit()

            # Step 4: AI分析（使用用户配置的摘要模型）
            video.status = VideoStatus.ANALYZING.value
            db.commit()
            
            try:
                logger.info("pipeline_step", step="analyze", source_id=video.source_id)
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
                    source_id=video.source_id,
                    summary_length=len(analysis.summary),
                )
            except NetworkError as e:
                # AI分析失败不阻塞流程
                logger.error("analysis_skipped_network", source_id=video.source_id, error=str(e), exc_info=True)
            except Exception as e:
                # AI分析失败不阻塞流程
                logger.exception("analysis_skipped_unexpected", source_id=video.source_id)

            # Step 5: 向量化（索引到知识库）
            video.status = VideoStatus.INDEXING.value
            db.commit()
            
            try:
                logger.info("pipeline_step", step="indexing", source_id=video.source_id)
                self._index_to_rag(video, result.text, db, user_id)
            except NetworkError as e:
                # 向量化失败不阻塞流程
                logger.error("indexing_skipped_network", source_id=video.source_id, error=str(e), exc_info=True)
            except Exception as e:
                # 向量化失败不阻塞流程
                logger.exception("indexing_skipped_unexpected", source_id=video.source_id)

            # Step 6: 完成
            video.status = VideoStatus.DONE.value
            video.processed_at = datetime.utcnow()
            db.commit()

            logger.info(
                "pipeline_complete",
                source_id=video.source_id,
                text_length=len(result.text),
            )

            # Step 6: 发送通知（增强版，带摘要）
            if self.notifier and self.notifier.is_configured():
                # 优先使用摘要，否则用转写预览
                notify_content = video.summary or result.text[:200]
                self.notifier.send_video_complete(
                    source_id=video.source_id,
                    title=video.title,
                    transcript_preview=notify_content,
                )

            return video

        except Exception as e:
            video.status = VideoStatus.FAILED.value
            video.error_message = str(e)
            video.retry_count += 1
            db.commit()
            
            logger.exception("pipeline_failed", source_id=video.source_id, error=str(e))
            
            # 发送失败通知
            if self.notifier and self.notifier.is_configured():
                self.notifier.send_error(
                    source_id=video.source_id,
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
        from alice.rag import RAGService, get_rag_client
        
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
            source_id=video.source_id,
            doc_id=doc_id,
        )

    def _save_transcript(self, source_id: str, result: TranscriptResult) -> Path:
        """保存转写结果"""
        # 保存纯文本
        txt_path = self.transcript_dir / f"{source_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.text)

        # 保存带时间戳的JSON
        json_path = self.transcript_dir / f"{source_id}.json"
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

        logger.info("transcript_saved", source_id=source_id, path=str(txt_path))
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
                logger.exception("process_video_failed", source_id=video.source_id)
                video.status = VideoStatus.FAILED.value
                video.error_message = str(e)
                db.commit()
                continue

        return processed
