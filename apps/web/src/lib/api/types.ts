/**
 * API 类型定义
 */

// ============== 通用 ==============

export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  pages: number
  items: T[]
}

// ============== 认证 ==============

export interface UserInfo {
  id: number
  email: string
  username: string
  tenant_id: number
}

// ============== 视频 ==============

export interface Video {
  id: number
  bvid: string
  title: string
  author: string | null
  duration: number | null
  cover_url: string | null
  status: string
  summary: string | null
  created_at: string
  processed_at: string | null
}

export interface VideoDetail extends Video {
  transcript_path: string | null
  key_points: string[] | null
  concepts: string[] | null
  tags: string[] | null
  error_message: string | null
}

export interface VideoProcessStatus {
  id: number
  status: string
  error_message: string | null
  has_transcript: boolean
  has_summary: boolean
}

export interface VideoComment {
  id: number
  content: string
  username: string
  avatar: string
  like_count: number
  reply_count: number
  created_at: number
}

export interface CommentsResponse {
  comments: VideoComment[]
  total: number
  page: number
  has_more: boolean
}

export interface QueueVideo {
  id: number
  bvid: string
  title: string
  status: string
  error_message: string | null
  created_at: string | null
  processed_at: string | null
}

export interface ProcessingQueue {
  queue: QueueVideo[]
  failed: QueueVideo[]
  recent_done: QueueVideo[]
  queue_count: number
  failed_count: number
}

export interface Stats {
  total: number
  done: number
  pending: number
  failed: number
  processing: number
}

export interface TagStats {
  tags: { name: string; count: number }[]
  total_videos: number
}

// ============== 导入 ==============

export interface VideoImportRequest {
  url: string
  auto_process?: boolean
}

export interface VideoImportResponse {
  id: number
  bvid: string
  title: string
  status: string
  message: string
}

// ============== 文件夹 ==============

export interface Folder {
  id: number
  folder_id: string
  folder_type: string
  name: string
  is_active: boolean
  video_count: number
  last_scan_at: string | null
}

// ============== 对话 ==============

export interface Conversation {
  id: number
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface Message {
  id: number
  role: "user" | "assistant" | "system"
  content: string
  sources: string | null
  created_at: string
}

export interface ConversationDetail extends Omit<Conversation, "message_count"> {
  messages: Message[]
}

export interface StreamEvent {
  type: "thinking" | "content" | "done" | "error"
  content?: string
  message_id?: number
  reasoning?: string
  error?: string
}

// ============== 配置 ==============

export interface ASRConfig {
  provider: string
  model_size: string
  device: string
  api_base_url?: string
  api_key?: string
  api_model?: string
}

export interface LLMConfig {
  provider: string
  model: string
  base_url?: string
  api_key?: string
  endpoint_id?: string
}

export interface ASRConfigResponse {
  provider: string
  model_size: string
  device: string
  api_base_url?: string
  has_api_key: boolean
  api_model?: string
}

export interface LLMConfigResponse {
  provider: string
  model: string
  base_url?: string
  has_api_key: boolean
  endpoint_id?: string
}

export interface ModelInfo {
  id: string
  name: string
  type: "chat" | "embedding" | "audio"
}

export interface LLMEndpoint {
  id: string
  name: string
  base_url: string
  has_api_key: boolean
  models: string[]
  models_with_type: ModelInfo[]
}

export interface ModelTaskConfig {
  endpoint_id?: string
  model: string
  provider?: string
  base_url?: string
}

export interface ModelTasksConfig {
  chat?: ModelTaskConfig
  summary?: ModelTaskConfig
  knowledge?: ModelTaskConfig
  mindmap?: ModelTaskConfig
  tagger?: ModelTaskConfig
  context_compress?: ModelTaskConfig
  asr?: ModelTaskConfig
  embedding?: ModelTaskConfig
}

export interface ConfigResponse {
  asr: ASRConfigResponse
  llm: LLMConfigResponse
  notify: {
    wechat_enabled: boolean
    webhook_url?: string
  }
  llm_endpoints: LLMEndpoint[]
  model_tasks: ModelTasksConfig
}

export interface ASRProvider {
  id: string
  name: string
  type: "local" | "api"
  description: string
  base_url?: string
  models?: string[]
}

export interface ASRProvidersResponse {
  providers: ASRProvider[]
  local_model_sizes: { id: string; name: string; vram: string; speed: string }[]
}

export interface LLMProvider {
  id: string
  name: string
  base_url: string
  default_models: string[]
}

export interface LLMProvidersResponse {
  providers: LLMProvider[]
}

export interface PromptsResponse {
  prompts: Record<string, string>
  defaults: Record<string, string>
  descriptions: Record<string, string>
  structured: string[]
  free: string[]
}

export interface LLMModel {
  id: string
  name: string
  owned_by?: string
}

// ============== B站 ==============

export interface BilibiliQRCode {
  url: string
  qrcode_key: string
}

export interface BilibiliQRCodeStatus {
  status: "waiting" | "scanned" | "confirmed" | "expired" | "error"
  message: string
}

export interface BilibiliBindStatus {
  is_bound: boolean
  bilibili_uid: string | null
  username: string | null
  is_vip: boolean
  is_expired: boolean
}

export interface BilibiliFolderInfo {
  id: string
  title: string
  media_count: number
  folder_type: "favlist" | "season"
}

export interface BilibiliFoldersResponse {
  created: BilibiliFolderInfo[]
  collected_folders: BilibiliFolderInfo[]
  collected_seasons: BilibiliFolderInfo[]
}

export interface BilibiliVideoInfo {
  bvid: string
  title: string
  author: string
  duration: number
  cover_url: string | null
  view_count: number | null
}

export interface BilibiliFolderDetailResponse {
  id: string
  title: string
  media_count: number
  folder_type: string
  videos: BilibiliVideoInfo[]
}

// ============== 系统 ==============

export interface StorageStats {
  total_videos: number
  processed_videos: number
  pending_videos: number
  failed_videos: number
  audio_files_count: number
  audio_files_size_mb: number
  download_files_size_mb: number
  transcript_files_size_mb: number
  total_size_mb: number
}

export interface CleanupResult {
  cleaned_count: number
  freed_mb: number
}

// ============== 建议 ==============

export interface Suggestion {
  text: string
  icon: string
  action: string
}

export interface SuggestionsResponse {
  suggestions: Suggestion[]
  context?: string
}
