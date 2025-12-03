/**
 * 系统 API
 */

import { client } from "./client"
import type { StorageStats, CleanupResult, SuggestionsResponse } from "./types"

export const systemApi = {
  getStorage: () => client.get<StorageStats>("/system/storage"),
  
  cleanup: (retention_days: number = 1) =>
    client.post<CleanupResult>(`/system/cleanup?retention_days=${retention_days}`),
}

export const qaApi = {
  ask: (question: string, video_ids?: number[]) =>
    client.post("/qa/ask", { question, video_ids }),
  
  search: (query: string, top_k?: number) =>
    client.post("/qa/search", { query, top_k }),
  
  summarize: (video_id: number) =>
    client.post(`/qa/summarize?video_id=${video_id}`),
}

export const suggestionsApi = {
  get: () => client.get<SuggestionsResponse>("/suggestions"),
}
