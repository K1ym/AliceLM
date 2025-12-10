/**
 * 知识图谱 API
 */

import { client } from "./client"

// 类型定义
export interface GraphNode {
  id: string
  label: string
  type: "concept" | "video"
  size?: number
  metadata?: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    total_concepts: number
    total_videos: number
    total_edges: number
  }
}

export interface ConceptVideo {
  id: number
  source_type: string
  source_id: string
  bvid?: string  // 兼容字段
  title: string
  author: string
}

export interface RelatedConcept {
  concept: string
  weight: number
  videos_count: number
}

export interface LearningStats {
  total_videos: number
  total_duration: number
  completed_videos: number
  concepts_learned: number
  videos_by_day: Record<string, number>
  top_authors: Array<{ author: string; count: number }>
}

export interface WeeklyReport {
  week_start: string
  week_end: string
  highlights: string[]
  stats: {
    total_videos: number
    total_duration: number
    concepts_learned: number
  }
  recommendations: string[]
}

export interface ReviewSuggestion {
  video_id: number
  source_type: string
  source_id: string
  bvid?: string  // 兼容字段
  title: string
  concepts: string[]
  last_viewed: string
  priority: number
}

// API 方法
export const knowledgeApi = {
  /**
   * 获取知识图谱
   */
  async getGraph() {
    return client.get<KnowledgeGraph>("/knowledge/graph")
  },

  /**
   * 获取概念关联的视频
   */
  async getConceptVideos(concept: string) {
    return client.get<ConceptVideo[]>(`/knowledge/concepts/${encodeURIComponent(concept)}/videos`)
  },

  /**
   * 获取相关概念
   */
  async getRelatedConcepts(concept: string, limit = 10) {
    return client.get<RelatedConcept[]>(
      `/knowledge/concepts/${encodeURIComponent(concept)}/related`,
      { params: { limit } }
    )
  },

  /**
   * 获取学习统计
   */
  async getLearningStats(days = 7) {
    return client.get<LearningStats>("/knowledge/learning/stats", { params: { days } })
  },

  /**
   * 获取周报
   */
  async getWeeklyReport() {
    return client.get<WeeklyReport>("/knowledge/learning/weekly-report")
  },

  /**
   * 获取复习建议
   */
  async getReviewSuggestions(limit = 5) {
    return client.get<ReviewSuggestion[]>("/knowledge/learning/review-suggestions", { params: { limit } })
  },
}
