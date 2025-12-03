/**
 * 视频 API
 */

import { client } from "./client"
import type {
  Video,
  VideoDetail,
  VideoProcessStatus,
  CommentsResponse,
  ProcessingQueue,
  PaginatedResponse,
  Stats,
  TagStats,
  VideoImportRequest,
  VideoImportResponse,
} from "./types"

export const videosApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; search?: string }) =>
    client.get<PaginatedResponse<Video>>("/videos", { params }),
  
  get: (id: number) => client.get<VideoDetail>(`/videos/${id}`),
  
  getTranscript: (id: number) => client.get(`/videos/${id}/transcript`),
  
  delete: (id: number) => client.delete(`/videos/${id}`),
  
  reprocess: (id: number) => client.post(`/videos/${id}/reprocess`),
  
  stats: () => client.get<Stats>("/videos/stats/summary"),
  
  topTags: (limit?: number) => 
    client.get<TagStats>("/videos/stats/tags", { params: { limit } }),
  
  processNow: (id: number) => client.post(`/videos/${id}/process`),
  
  getStatus: (id: number) => client.get<VideoProcessStatus>(`/videos/${id}/status`),
  
  getComments: (id: number, page?: number) =>
    client.get<CommentsResponse>(`/videos/${id}/comments`, { params: { page } }),
  
  getQueue: () => client.get<ProcessingQueue>("/videos/queue/list"),
  
  cancelProcess: (id: number) => client.post(`/videos/${id}/cancel`),
  
  removeFromQueue: (id: number) => client.delete(`/videos/${id}/queue`),
}

export const importApi = {
  single: (request: VideoImportRequest) =>
    client.post<VideoImportResponse>("/videos", request),
  
  batch: (urls: string[]) =>
    client.post("/videos/batch", urls),
  
  // 导入并立即处理
  singleAndProcess: async (url: string): Promise<VideoImportResponse> => {
    const res = await client.post<VideoImportResponse>("/videos", { 
      url, 
      auto_process: true 
    })
    if (res.data && res.data.status === "pending") {
      await videosApi.processNow(res.data.id)
    }
    return res.data as VideoImportResponse
  },
}
