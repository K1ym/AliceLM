"use client"

import { Loader2, MessageSquare, ThumbsUp, RefreshCw } from "lucide-react"
import type { VideoComment } from "@/lib/api"

function formatCommentTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days > 365) return `${Math.floor(days / 365)}年前`
  if (days > 30) return `${Math.floor(days / 30)}个月前`
  if (days > 0) return `${days}天前`
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours > 0) return `${hours}小时前`
  const mins = Math.floor(diff / (1000 * 60))
  return mins > 0 ? `${mins}分钟前` : "刚刚"
}

interface CommentsTabProps {
  comments: VideoComment[]
  commentsLoading: boolean
  hasMoreComments: boolean
  onLoadMore: () => void
}

export function CommentsTab({
  comments,
  commentsLoading,
  hasMoreComments,
  onLoadMore,
}: CommentsTabProps) {
  if (commentsLoading && comments.length === 0) {
    return (
      <div className="text-center py-10">
        <Loader2 className="w-6 h-6 animate-spin mx-auto text-neutral-400" />
        <p className="text-sm text-neutral-500 mt-2">加载评论中...</p>
      </div>
    )
  }

  if (comments.length === 0) {
    return (
      <div className="text-center text-neutral-400 py-10">
        <MessageSquare size={32} className="mx-auto mb-2 opacity-50" />
        暂无评论
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {comments.map((comment) => (
        <div key={comment.id} className="bg-white p-4 rounded-xl border border-neutral-100">
          <div className="flex items-start gap-3">
            <img
              src={comment.avatar}
              alt={comment.username}
              className="w-8 h-8 rounded-full bg-neutral-200"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-neutral-900">{comment.username}</span>
                <span className="text-xs text-neutral-400">
                  {formatCommentTime(comment.created_at)}
                </span>
              </div>
              <p className="text-sm text-neutral-600 mt-1 whitespace-pre-wrap">{comment.content}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-neutral-400">
                <span className="flex items-center gap-1">
                  <ThumbsUp size={12} />
                  {comment.like_count}
                </span>
                {comment.reply_count > 0 && <span>{comment.reply_count} 回复</span>}
              </div>
            </div>
          </div>
        </div>
      ))}
      {hasMoreComments && (
        <button
          onClick={onLoadMore}
          disabled={commentsLoading}
          className="w-full py-3 text-sm text-neutral-600 hover:text-neutral-900 flex items-center justify-center gap-2"
        >
          {commentsLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          加载更多
        </button>
      )}
    </div>
  )
}
