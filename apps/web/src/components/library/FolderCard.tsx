"use client"

import { Plus, Loader2 } from "lucide-react"
import type { BilibiliFolderInfo } from "@/lib/api"

interface FolderCardProps {
  folder: BilibiliFolderInfo
  onAdd: (folder: BilibiliFolderInfo) => void
  onOpen: (folder: BilibiliFolderInfo) => void
  adding: boolean
}

export function FolderCard({ folder, onAdd, onOpen, adding }: FolderCardProps) {
  return (
    <div
      className="bg-white border border-neutral-100 rounded-xl p-4 hover:border-neutral-300 hover:shadow-sm transition-all cursor-pointer"
      onClick={() => onOpen(folder)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-neutral-900 truncate">{folder.title}</h4>
          <p className="text-sm text-neutral-500 mt-1">
            {folder.media_count} 个视频
            {folder.folder_type === "season" && (
              <span className="ml-2 text-xs bg-pink-100 text-pink-600 px-1.5 py-0.5 rounded">
                合集
              </span>
            )}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAdd(folder)
          }}
          disabled={adding}
          className="flex-shrink-0 px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {adding ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Plus className="w-4 h-4" />
              添加
            </>
          )}
        </button>
      </div>
    </div>
  )
}
