"use client"

import { Clock } from "lucide-react"
import type { TranscriptSegment } from "@/types/home"

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
}

interface TranscriptTabProps {
  transcript: TranscriptSegment[]
  processingStatus: string | null
}

export function TranscriptTab({ transcript, processingStatus }: TranscriptTabProps) {
  if (transcript.length === 0) {
    return (
      <div className="text-center text-neutral-400 py-10">
        <Clock size={32} className="mx-auto mb-2 opacity-50" />
        {processingStatus === "done" ? "暂无转写内容" : "转写处理中..."}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {transcript.map((t, idx) => (
        <div
          key={t.id ?? idx}
          className="group flex gap-4 p-3 hover:bg-white hover:shadow-sm rounded-xl transition-all cursor-pointer"
        >
          <span className="text-xs font-mono text-neutral-400 pt-1 group-hover:text-blue-600">
            {formatTime(t.start)}
          </span>
          <p className="text-sm text-neutral-600 leading-relaxed group-hover:text-neutral-900">
            {t.text}
          </p>
        </div>
      ))}
    </div>
  )
}
