"use client"

import { Plus, Loader2, Play } from "lucide-react"
import type { BilibiliVideoInfo } from "@/lib/api"

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

interface BilibiliVideoCardProps {
  video: BilibiliVideoInfo
  onImport: (sourceId: string) => void
  importing: boolean
}

export function BilibiliVideoCard({ video, onImport, importing }: BilibiliVideoCardProps) {
  return (
    <div className="bg-white border border-neutral-100 rounded-xl overflow-hidden hover:border-neutral-200 transition-colors">
      <div className="flex gap-4 p-4">
        {/* 封面 */}
        <div className="flex-shrink-0 w-40 aspect-video bg-neutral-100 rounded-lg overflow-hidden relative">
          {video.cover_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={video.cover_url.replace(/^http:/, "https:")}
              alt={video.title}
              className="w-full h-full object-cover"
              referrerPolicy="no-referrer"
              loading="lazy"
              onError={(e) => {
                const target = e.currentTarget
                target.style.display = "none"
                const fallback = target.nextElementSibling as HTMLElement
                if (fallback) fallback.style.display = "flex"
              }}
            />
          ) : null}
          <div
            className="w-full h-full items-center justify-center absolute inset-0"
            style={{ display: video.cover_url ? "none" : "flex" }}
          >
            <Play className="w-8 h-8 text-neutral-300" />
          </div>
          <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/70 text-white text-xs rounded z-10">
            {formatDuration(video.duration)}
          </div>
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0 flex flex-col">
          <h4 className="font-medium text-neutral-900 line-clamp-2">{video.title}</h4>
          <p className="text-sm text-neutral-500 mt-1">{video.author}</p>
          {video.view_count !== null && (
            <p className="text-xs text-neutral-400 mt-1">
              {video.view_count >= 10000
                ? `${(video.view_count / 10000).toFixed(1)}万播放`
                : `${video.view_count}播放`}
            </p>
          )}
          <div className="mt-auto pt-3 flex items-center gap-2">
            <a
              href={`https://www.bilibili.com/video/${video.source_id || video.bvid}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-neutral-500 hover:text-neutral-900"
            >
              {video.source_id || video.bvid}
            </a>
            <button
              onClick={() => onImport(video.source_id || video.bvid || "")}
              disabled={importing}
              className="ml-auto px-3 py-1.5 bg-pink-500 text-white rounded-lg text-sm font-medium hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              {importing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  导入
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
