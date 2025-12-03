"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, FileText, Sparkles, MessageSquare, ExternalLink, Loader2, AlertCircle } from "lucide-react";
import { videosApi, VideoDetail, VideoComment } from "@/lib/api";
import { TabButton, SummaryTab, TranscriptTab, CommentsTab } from "@/components/video";
import type { TranscriptSegment } from "@/types/home";

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins >= 60) {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return `${hours}:${remainingMins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function VideoDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [comments, setComments] = useState<VideoComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [hasMoreComments, setHasMoreComments] = useState(false);
  const [commentsPage, setCommentsPage] = useState(1);
  const [activeTab, setActiveTab] = useState<"summary" | "transcript" | "comments">("summary");
  const [loading, setLoading] = useState(true);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (id) {
      loadVideo(Number(id));
    }
  }, [id]);

  async function loadVideo(videoId: number) {
    try {
      const res = await videosApi.get(videoId);
      if (res.data) {
        setVideo(res.data);
        setProcessingStatus(res.data.status);
        
        // 如果正在处理中，开始轮询状态
        if (res.data.status !== 'done' && res.data.status !== 'failed') {
          startPolling(videoId);
        }
      }
      // Load transcript
      try {
        const transcriptRes = await videosApi.getTranscript(videoId);
        if (transcriptRes.data?.segments) {
          setTranscript(transcriptRes.data.segments);
        }
      } catch {
        // 转写可能还没完成
      }
    } catch {
      // Video not found
    } finally {
      setLoading(false);
    }
  }

  // 轮询处理状态
  const startPolling = useCallback((videoId: number) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const statusRes = await videosApi.getStatus(videoId);
        if (statusRes.data) {
          setProcessingStatus(statusRes.data.status);
          
          // 处理完成或失败，停止轮询并刷新数据
          if (statusRes.data.status === 'done' || statusRes.data.status === 'failed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            // 刷新视频数据
            loadVideo(videoId);
          }
        }
      } catch {
        // ignore
      }
    }, 3000); // 每3秒轮询一次
  }, []);

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // 加载评论
  async function loadComments(videoId: number, page: number = 1) {
    setCommentsLoading(true);
    try {
      const res = await videosApi.getComments(videoId, page);
      if (res.data) {
        if (page === 1) {
          setComments(res.data.comments);
        } else {
          setComments(prev => [...prev, ...res.data!.comments]);
        }
        setHasMoreComments(res.data.has_more);
        setCommentsPage(page);
      }
    } catch {
      // ignore
    } finally {
      setCommentsLoading(false);
    }
  }

  // 切换到评论tab时加载
  useEffect(() => {
    if (activeTab === 'comments' && video && comments.length === 0) {
      loadComments(video.id);
    }
  }, [activeTab, video]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <p className="text-neutral-500 mb-4">视频未找到</p>
        <button
          onClick={() => router.back()}
          className="text-sm text-neutral-600 hover:text-neutral-900"
        >
          返回
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col md:flex-row overflow-hidden bg-white">
      {/* Left: Player & Info */}
      <div className="flex-1 overflow-y-auto md:border-r border-neutral-100">
        <div className="sticky top-0 bg-white z-10 border-b border-neutral-100 px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-neutral-100 rounded-lg text-neutral-500"
          >
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-lg font-medium text-neutral-900 truncate">
            {video.title}
          </h1>
        </div>

        {/* Player - Bilibili Embed */}
        <div className="aspect-video bg-black w-full relative">
          <iframe
            src={`//player.bilibili.com/player.html?bvid=${video.bvid}&autoplay=0`}
            className="w-full h-full"
            allowFullScreen
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        </div>

        {/* Metadata */}
        <div className="p-6 md:p-8 space-y-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-neutral-900 mb-2">
                {video.title}
              </h2>
              <div className="flex items-center gap-4 text-sm text-neutral-500">
                <span className="font-medium text-neutral-900">{video.author}</span>
                <span>|</span>
                <span>{formatDuration(video.duration || 0)}</span>
              </div>
            </div>
            <div className="flex gap-2 items-center">
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium border ${
                  video.status === "done"
                    ? "bg-green-50 text-green-700 border-green-200"
                    : video.status === "failed"
                    ? "bg-red-50 text-red-700 border-red-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                }`}
              >
                {video.status === "done" ? "已完成" : video.status === "failed" ? "失败" : video.status}
              </span>
              {(video.status === "pending" || video.status === "failed") && (
                <button
                  onClick={async () => {
                    try {
                      await videosApi.processNow(video.id);
                      setProcessingStatus("downloading");
                      startPolling(video.id);
                    } catch (e) {
                      console.error("Process failed:", e);
                    }
                  }}
                  className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-full hover:bg-blue-700 transition-colors"
                >
                  开始处理
                </button>
              )}
            </div>
          </div>

          <div className="h-px bg-neutral-100 w-full" />

          <div>
            <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-3">
              简介
            </h3>
            <p className="text-neutral-600 leading-relaxed font-light">
              {video.summary || "暂无描述"}
            </p>
          </div>

          {/* Open in Bilibili */}
          <a
            href={`https://www.bilibili.com/video/${video.bvid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
          >
            <ExternalLink size={14} />
            在B站打开
          </a>
        </div>
      </div>

      {/* Right: Knowledge Tabs */}
      <div className="w-full md:w-[450px] flex flex-col bg-neutral-50 h-[50vh] md:h-full border-t md:border-t-0 border-neutral-200">
        {/* Tab Header */}
        <div className="flex border-b border-neutral-200 bg-white">
          <TabButton
            active={activeTab === "summary"}
            onClick={() => setActiveTab("summary")}
            icon={Sparkles}
            label="摘要"
          />
          <TabButton
            active={activeTab === "transcript"}
            onClick={() => setActiveTab("transcript")}
            icon={FileText}
            label="转写"
          />
          <TabButton
            active={activeTab === "comments"}
            onClick={() => setActiveTab("comments")}
            icon={MessageSquare}
            label="评论"
          />
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* 处理状态提示 */}
          {processingStatus && processingStatus !== 'done' && (
            <div className={`mb-4 p-4 rounded-xl flex items-center gap-3 ${
              processingStatus === 'failed' 
                ? 'bg-red-50 border border-red-100' 
                : 'bg-blue-50 border border-blue-100'
            }`}>
              {processingStatus === 'failed' ? (
                <AlertCircle size={20} className="text-red-500" />
              ) : (
                <Loader2 size={20} className="animate-spin text-blue-500" />
              )}
              <div className="flex-1">
                <p className={`text-sm font-medium ${processingStatus === 'failed' ? 'text-red-700' : 'text-blue-700'}`}>
                  {processingStatus === 'pending' && '等待处理...'}
                  {processingStatus === 'downloading' && '正在下载视频...'}
                  {processingStatus === 'transcribing' && '正在转写中...'}
                  {processingStatus === 'analyzing' && '正在AI分析...'}
                  {processingStatus === 'failed' && '处理失败'}
                </p>
                {processingStatus !== 'failed' && (
                  <p className="text-xs text-blue-600 mt-0.5">处理完成后会自动刷新</p>
                )}
              </div>
            </div>
          )}

          {activeTab === "summary" && (
            <SummaryTab video={video} processingStatus={processingStatus} />
          )}

          {activeTab === "transcript" && (
            <TranscriptTab transcript={transcript} processingStatus={processingStatus} />
          )}

          {activeTab === "comments" && (
            <CommentsTab
              comments={comments}
              commentsLoading={commentsLoading}
              hasMoreComments={hasMoreComments}
              onLoadMore={() => video && loadComments(video.id, commentsPage + 1)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

