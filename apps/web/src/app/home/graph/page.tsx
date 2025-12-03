"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { Network, Sparkles, Video, Tag, Loader2, ZoomIn, ZoomOut, Maximize2, Info, X } from "lucide-react"
import { knowledgeApi, KnowledgeGraph, GraphNode, ConceptVideo, RelatedConcept } from "@/lib/api/knowledge"

export default function GraphPage() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [relatedVideos, setRelatedVideos] = useState<ConceptVideo[]>([])
  const [relatedConcepts, setRelatedConcepts] = useState<RelatedConcept[]>([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [zoom, setZoom] = useState(1)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadGraph()
  }, [])

  async function loadGraph() {
    try {
      setLoading(true)
      setError(null)
      const res = await knowledgeApi.getGraph()
      if (res.data) {
        setGraph(res.data)
      }
    } catch (e: any) {
      setError(e.message || "加载失败")
    } finally {
      setLoading(false)
    }
  }

  async function handleNodeClick(node: GraphNode) {
    setSelectedNode(node)
    if (node.type === "concept") {
      setLoadingDetails(true)
      try {
        const [videosRes, conceptsRes] = await Promise.all([
          knowledgeApi.getConceptVideos(node.label),
          knowledgeApi.getRelatedConcepts(node.label),
        ])
        setRelatedVideos(videosRes.data || [])
        setRelatedConcepts(conceptsRes.data || [])
      } catch {
        // ignore
      } finally {
        setLoadingDetails(false)
      }
    } else {
      setRelatedVideos([])
      setRelatedConcepts([])
    }
  }

  function closePanel() {
    setSelectedNode(null)
    setRelatedVideos([])
    setRelatedConcepts([])
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error}</p>
        <button
          onClick={loadGraph}
          className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm"
        >
          重试
        </button>
      </div>
    )
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-neutral-500">
        <Network className="w-16 h-16 text-neutral-300" />
        <p>暂无知识图谱数据</p>
        <p className="text-sm">处理更多视频后，知识图谱将自动生成</p>
      </div>
    )
  }

  // 分离概念节点和视频节点
  const conceptNodes = graph.nodes.filter(n => n.type === "concept")
  const videoNodes = graph.nodes.filter(n => n.type === "video")

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* 头部 */}
      <div className="flex items-center justify-between p-6 border-b border-neutral-100">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900 flex items-center gap-2">
            <Network className="w-5 h-5" />
            知识图谱
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            {graph.stats.total_concepts} 个概念 · {graph.stats.total_videos} 个视频 · {graph.stats.total_edges} 条关联
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom(z => Math.min(z + 0.2, 2))}
            className="p-2 rounded-lg hover:bg-neutral-100"
            title="放大"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}
            className="p-2 rounded-lg hover:bg-neutral-100"
            title="缩小"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-2 rounded-lg hover:bg-neutral-100"
            title="重置"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 主内容 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 图谱区域 */}
        <div 
          ref={containerRef}
          className="flex-1 overflow-auto p-6 bg-neutral-50"
        >
          <div 
            className="min-w-[800px] min-h-[600px] relative transition-transform"
            style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
          >
            {/* 概念节点 - 圆形布局 */}
            <div className="absolute inset-0">
              {conceptNodes.map((node, i) => {
                const angle = (i / conceptNodes.length) * 2 * Math.PI
                const radius = 250
                const x = 400 + radius * Math.cos(angle)
                const y = 300 + radius * Math.sin(angle)
                const size = Math.min(80, Math.max(40, (node.size || 1) * 10))
                
                return (
                  <button
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    className={`absolute transform -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center transition-all hover:scale-110 ${
                      selectedNode?.id === node.id
                        ? "ring-4 ring-blue-500 ring-offset-2"
                        : ""
                    }`}
                    style={{
                      left: x,
                      top: y,
                      width: size,
                      height: size,
                      backgroundColor: `hsl(${(i * 37) % 360}, 70%, 85%)`,
                    }}
                    title={node.label}
                  >
                    <span className="text-xs font-medium text-neutral-700 truncate max-w-[90%] px-1">
                      {node.label}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* 中心标签 */}
            <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
            </div>

            {/* 连接线（简化版，只显示部分） */}
            <svg className="absolute inset-0 pointer-events-none" style={{ width: "100%", height: "100%" }}>
              {graph.edges.slice(0, 50).map((edge, i) => {
                const sourceNode = conceptNodes.find(n => n.id === edge.source)
                const targetNode = conceptNodes.find(n => n.id === edge.target)
                if (!sourceNode || !targetNode) return null
                
                const sourceIndex = conceptNodes.indexOf(sourceNode)
                const targetIndex = conceptNodes.indexOf(targetNode)
                const radius = 250
                
                const x1 = 400 + radius * Math.cos((sourceIndex / conceptNodes.length) * 2 * Math.PI)
                const y1 = 300 + radius * Math.sin((sourceIndex / conceptNodes.length) * 2 * Math.PI)
                const x2 = 400 + radius * Math.cos((targetIndex / conceptNodes.length) * 2 * Math.PI)
                const y2 = 300 + radius * Math.sin((targetIndex / conceptNodes.length) * 2 * Math.PI)
                
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="rgba(0,0,0,0.1)"
                    strokeWidth={Math.max(1, edge.weight * 2)}
                  />
                )
              })}
            </svg>
          </div>
        </div>

        {/* 详情面板 */}
        {selectedNode && (
          <div className="w-80 border-l border-neutral-100 bg-white overflow-y-auto">
            <div className="p-4 border-b border-neutral-100 flex items-center justify-between">
              <h3 className="font-medium text-neutral-900 flex items-center gap-2">
                {selectedNode.type === "concept" ? (
                  <Tag className="w-4 h-4 text-blue-500" />
                ) : (
                  <Video className="w-4 h-4 text-green-500" />
                )}
                {selectedNode.label}
              </h3>
              <button onClick={closePanel} className="p-1 hover:bg-neutral-100 rounded">
                <X className="w-4 h-4" />
              </button>
            </div>

            {loadingDetails ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
              </div>
            ) : (
              <div className="p-4 space-y-6">
                {/* 相关视频 */}
                {relatedVideos.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-neutral-700 mb-3">相关视频</h4>
                    <div className="space-y-2">
                      {relatedVideos.map(video => (
                        <a
                          key={video.id}
                          href={`/home/video/${video.id}`}
                          className="block p-3 rounded-lg bg-neutral-50 hover:bg-neutral-100 transition-colors"
                        >
                          <p className="text-sm font-medium text-neutral-900 line-clamp-2">
                            {video.title}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">{video.author}</p>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* 相关概念 */}
                {relatedConcepts.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-neutral-700 mb-3">相关概念</h4>
                    <div className="flex flex-wrap gap-2">
                      {relatedConcepts.map(concept => (
                        <button
                          key={concept.concept}
                          onClick={() => {
                            const node = graph.nodes.find(n => n.label === concept.concept)
                            if (node) handleNodeClick(node)
                          }}
                          className="px-3 py-1.5 rounded-full bg-neutral-100 text-sm text-neutral-700 hover:bg-neutral-200 transition-colors"
                        >
                          {concept.concept}
                          <span className="ml-1 text-neutral-400">({concept.videos_count})</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {relatedVideos.length === 0 && relatedConcepts.length === 0 && (
                  <div className="text-center py-8 text-neutral-400">
                    <Info className="w-8 h-8 mx-auto mb-2" />
                    <p className="text-sm">暂无详细信息</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
