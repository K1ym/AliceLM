"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { Play, Clock, MoreHorizontal, Loader2, AlertCircle } from "lucide-react";
import type { Video } from "@/types/home";

interface VideoCardProps {
  video: Video;
  layout?: "grid" | "compact";
}

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

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  if (diffDays < 7) return `${diffDays}天前`;
  return date.toLocaleDateString("zh-CN");
}

export function VideoCard({ video, layout = "grid" }: VideoCardProps) {
  const StatusIndicator = () => {
    switch (video.status) {
      case "downloading":
      case "transcribing":
      case "analyzing":
        return (
          <div className="absolute top-2 right-2 bg-neutral-900/80 backdrop-blur-sm text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>
              {video.status === "downloading" && "下载中"}
              {video.status === "transcribing" && "转写中"}
              {video.status === "analyzing" && "分析中"}
            </span>
          </div>
        );
      case "failed":
        return (
          <div className="absolute top-2 right-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            <span>失败</span>
          </div>
        );
      default:
        return null;
    }
  };

  if (layout === "compact") {
    return (
      <Link
        href={`/home/video/${video.id}`}
        className="group flex gap-3 p-2 rounded-xl hover:bg-neutral-100 cursor-pointer transition-colors duration-200 items-center"
      >
        <div className="relative w-24 h-16 shrink-0 rounded-lg overflow-hidden bg-neutral-200">
          {video.cover_url ? (
            <Image
              src={video.cover_url}
              alt={video.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full bg-neutral-200" />
          )}
          {(video.status === "downloading" || video.status === "transcribing" || video.status === "analyzing") && (
            <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-neutral-900 truncate">
            {video.title}
          </h4>
          <p className="text-xs text-neutral-500 mt-0.5">
            {video.author} | {formatDuration(video.duration)}
          </p>
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/home/video/${video.id}`}
      className="group bg-white rounded-2xl border border-neutral-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 cursor-pointer overflow-hidden flex flex-col h-full"
    >
      {/* Thumbnail Area */}
      <div className="relative aspect-video bg-neutral-100 overflow-hidden">
        {video.cover_url ? (
          <Image
            src={video.cover_url}
            alt={video.title}
            fill
            className={`object-cover transition-transform duration-700 ${
              video.status !== "done"
                ? "opacity-80 scale-105"
                : "group-hover:scale-105"
            }`}
          />
        ) : (
          <div className="w-full h-full bg-neutral-200" />
        )}

        <StatusIndicator />

        {/* Duration Badge */}
        <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-md text-white text-[10px] px-1.5 py-0.5 rounded font-medium tracking-wide">
          {formatDuration(video.duration)}
        </div>

        {/* Hover Play Overlay */}
        {video.status === "done" && (
          <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
            <div className="w-10 h-10 bg-white/90 rounded-full flex items-center justify-center shadow-lg transform scale-90 group-hover:scale-100 transition-transform">
              <Play className="w-4 h-4 text-neutral-900 ml-0.5" fill="currentColor" />
            </div>
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex justify-between items-start gap-2">
          <h3 className="text-base font-medium text-neutral-900 leading-snug line-clamp-2 group-hover:text-blue-600 transition-colors">
            {video.title}
          </h3>
          <button 
            onClick={(e) => e.preventDefault()}
            className="text-neutral-400 hover:text-neutral-900 transition-colors"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-auto pt-3 flex items-center justify-between text-xs text-neutral-500">
          <span className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-full bg-neutral-200 flex items-center justify-center text-[10px] font-bold text-neutral-600">
              {video.author.charAt(0)}
            </div>
            {video.author}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatTimeAgo(video.created_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

export default VideoCard;
