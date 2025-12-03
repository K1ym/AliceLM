"""
知识图谱服务
P4-04: 知识图谱数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict

from sqlalchemy.orm import Session
import json

from packages.db import Video
from packages.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConceptNode:
    """概念节点"""
    id: str
    name: str
    category: str = "concept"
    video_count: int = 0
    video_ids: Set[int] = field(default_factory=set)


@dataclass
class VideoNode:
    """视频节点"""
    id: int
    title: str
    bvid: str
    concepts: List[str] = field(default_factory=list)


@dataclass
class Edge:
    """边"""
    source: str
    target: str
    weight: float = 1.0
    relation: str = "contains"


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    concept_nodes: Dict[str, ConceptNode]
    video_nodes: Dict[int, VideoNode]
    edges: List[Edge]
    
    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "nodes": [
                {"id": f"concept:{c.id}", "name": c.name, "type": "concept", "count": c.video_count}
                for c in self.concept_nodes.values()
            ] + [
                {"id": f"video:{v.id}", "name": v.title, "type": "video", "bvid": v.bvid}
                for v in self.video_nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target, "weight": e.weight, "relation": e.relation}
                for e in self.edges
            ],
            "stats": {
                "concepts": len(self.concept_nodes),
                "videos": len(self.video_nodes),
                "edges": len(self.edges),
            }
        }


class KnowledgeGraphService:
    """知识图谱服务"""

    def __init__(self, db: Session):
        self.db = db

    def build_graph(self, tenant_id: int) -> KnowledgeGraph:
        """
        构建租户的知识图谱
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            知识图谱对象
        """
        # 获取所有已完成的视频
        videos = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.status == "done",
            )
            .all()
        )

        concept_nodes: Dict[str, ConceptNode] = {}
        video_nodes: Dict[int, VideoNode] = {}
        edges: List[Edge] = []

        # 构建节点
        for video in videos:
            # 解析概念
            concepts = []
            try:
                concepts = json.loads(video.concepts or "[]")
            except json.JSONDecodeError:
                pass

            # 视频节点
            video_node = VideoNode(
                id=video.id,
                title=video.title,
                bvid=video.bvid,
                concepts=concepts,
            )
            video_nodes[video.id] = video_node

            # 概念节点和边
            for concept in concepts:
                concept_id = concept.lower().replace(" ", "_")

                if concept_id not in concept_nodes:
                    concept_nodes[concept_id] = ConceptNode(
                        id=concept_id,
                        name=concept,
                    )

                concept_nodes[concept_id].video_count += 1
                concept_nodes[concept_id].video_ids.add(video.id)

                # 视频->概念边
                edges.append(Edge(
                    source=f"video:{video.id}",
                    target=f"concept:{concept_id}",
                    relation="contains",
                ))

        # 概念间边（共现关系）
        concept_cooccurrence = self._compute_cooccurrence(video_nodes)
        for (c1, c2), weight in concept_cooccurrence.items():
            if weight >= 2:  # 至少共现2次
                edges.append(Edge(
                    source=f"concept:{c1}",
                    target=f"concept:{c2}",
                    weight=weight,
                    relation="cooccurs",
                ))

        logger.info(
            "knowledge_graph_built",
            tenant_id=tenant_id,
            concepts=len(concept_nodes),
            videos=len(video_nodes),
            edges=len(edges),
        )

        return KnowledgeGraph(
            concept_nodes=concept_nodes,
            video_nodes=video_nodes,
            edges=edges,
        )

    def _compute_cooccurrence(
        self,
        video_nodes: Dict[int, VideoNode],
    ) -> Dict[tuple, int]:
        """计算概念共现次数"""
        cooccurrence: Dict[tuple, int] = defaultdict(int)

        for video in video_nodes.values():
            concepts = [c.lower().replace(" ", "_") for c in video.concepts]

            # 两两组合
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i + 1:]:
                    key = tuple(sorted([c1, c2]))
                    cooccurrence[key] += 1

        return cooccurrence

    def get_concept_videos(
        self,
        tenant_id: int,
        concept: str,
    ) -> List[Video]:
        """获取包含某概念的所有视频"""
        videos = (
            self.db.query(Video)
            .filter(
                Video.tenant_id == tenant_id,
                Video.status == "done",
                Video.concepts.ilike(f"%{concept}%"),
            )
            .all()
        )
        return videos

    def get_related_concepts(
        self,
        tenant_id: int,
        concept: str,
        limit: int = 10,
    ) -> List[Dict]:
        """获取相关概念"""
        graph = self.build_graph(tenant_id)
        concept_id = concept.lower().replace(" ", "_")

        if concept_id not in graph.concept_nodes:
            return []

        # 找共现的概念
        related = defaultdict(int)
        for edge in graph.edges:
            if edge.relation == "cooccurs":
                if edge.source == f"concept:{concept_id}":
                    target_id = edge.target.replace("concept:", "")
                    related[target_id] = edge.weight
                elif edge.target == f"concept:{concept_id}":
                    source_id = edge.source.replace("concept:", "")
                    related[source_id] = edge.weight

        # 排序
        sorted_related = sorted(related.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "concept": graph.concept_nodes[cid].name if cid in graph.concept_nodes else cid,
                "weight": w,
            }
            for cid, w in sorted_related[:limit]
        ]
