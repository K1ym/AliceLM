/**
 * API 模块统一导出
 * 
 * 使用方式：
 * import { videosApi, authApi, Video } from "@/lib/api"
 */

// 客户端
export { client } from "./client"
export { client as default } from "./client"

// API 模块
export { authApi } from "./auth"
export { videosApi, importApi } from "./videos"
export { conversationsApi } from "./conversations"
export { configApi } from "./config"
export { bilibiliApi } from "./bilibili"
export { foldersApi } from "./folders"
export { systemApi, qaApi, suggestionsApi } from "./system"
export { knowledgeApi } from "./knowledge"

// 类型导出
export type {
  // 通用
  PaginatedResponse,
  // 认证
  UserInfo,
  // 视频
  Video,
  VideoDetail,
  VideoProcessStatus,
  VideoComment,
  CommentsResponse,
  QueueVideo,
  ProcessingQueue,
  Stats,
  TagStats,
  VideoImportRequest,
  VideoImportResponse,
  // 文件夹
  Folder,
  // 对话
  Conversation,
  Message,
  ConversationDetail,
  StreamEvent,
  // 配置
  ASRConfig,
  LLMConfig,
  ASRConfigResponse,
  LLMConfigResponse,
  ModelInfo,
  LLMEndpoint,
  ModelTaskConfig,
  ModelTasksConfig,
  ConfigResponse,
  ASRProvider,
  ASRProvidersResponse,
  LLMProvider,
  LLMProvidersResponse,
  PromptsResponse,
  LLMModel,
  // B站
  BilibiliQRCode,
  BilibiliQRCodeStatus,
  BilibiliBindStatus,
  BilibiliFolderInfo,
  BilibiliFoldersResponse,
  BilibiliVideoInfo,
  BilibiliFolderDetailResponse,
  // 系统
  StorageStats,
  CleanupResult,
  Suggestion,
  SuggestionsResponse,
} from "./types"
