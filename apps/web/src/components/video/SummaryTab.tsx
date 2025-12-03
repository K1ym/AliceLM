"use client"

import { Sparkles, CheckCircle2 } from "lucide-react"
import type { VideoDetail } from "@/lib/api"

interface SummaryTabProps {
  video: VideoDetail
  processingStatus: string | null
}

export function SummaryTab({ video, processingStatus }: SummaryTabProps) {
  return (
    <div className="space-y-6">
      {processingStatus === "done" && video.key_points && video.key_points.length > 0 && (
        <div className="flex items-center gap-2 text-green-600 text-sm mb-2">
          <CheckCircle2 size={16} />
          <span>AI分析完成</span>
        </div>
      )}

      <div className="bg-white p-5 rounded-2xl border border-neutral-100 shadow-sm">
        <h4 className="font-medium text-neutral-900 mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-amber-500" /> 核心要点
        </h4>
        {video.key_points && video.key_points.length > 0 ? (
          <ul className="space-y-3">
            {video.key_points.map((point, i) => (
              <li key={i} className="flex gap-3 text-sm text-neutral-600 leading-relaxed">
                <span className="shrink-0 w-5 h-5 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-bold text-neutral-500">
                  {i + 1}
                </span>
                {point}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-400">
            {processingStatus !== "done" ? "处理中，稍后查看..." : "暂无要点"}
          </p>
        )}
      </div>

      {video.concepts && video.concepts.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-3">
            核心概念
          </h4>
          <div className="flex flex-wrap gap-2">
            {video.concepts.map((concept) => (
              <span
                key={concept}
                className="px-3 py-1 bg-white border border-neutral-200 rounded-lg text-xs font-medium text-neutral-600 hover:border-neutral-400 cursor-pointer transition-colors"
              >
                {concept}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
