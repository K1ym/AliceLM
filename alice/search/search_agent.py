"""
SearchAgentService - 深度 Web 搜索服务

职责：
- 多子查询生成 + 多路搜索 + 聚合回答
- 作为 deep_web_research Tool 的后端实现

内部流程：
1. QueryInterpreter: 理解/重写问题
2. QueryDecomposer: 生成子查询
3. SearchExecutor: 多路搜索
4. PageFetcher: 抓取正文（可选）
5. EvidenceAggregator: 去重+排序+聚合
6. AnswerSynthesizer: 综合回答
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .http_client import get_search_provider, SearchProvider, WebSearchResult

logger = logging.getLogger(__name__)


@dataclass
class SearchSource:
    """搜索来源"""
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    content: Optional[str] = None  # 解析后的正文（可选）
    score: Optional[float] = None  # 相关度/排序用


@dataclass
class SearchAgentResult:
    """搜索 Agent 结果"""
    query: str                      # 原始或重写后的查询
    sub_queries: List[str]          # 拆解出的子查询列表
    sources: List[SearchSource]     # 整理后的多源证据
    answer: str                     # 基于证据的综合回答


# ============================================================
# Prompt keys (从 ControlPlane 获取)
# ============================================================

QUERY_DECOMPOSE_PROMPT_KEY = "alice.search.query_decompose"
ANSWER_SYNTHESIS_PROMPT_KEY = "alice.search.answer_synthesis"


class SearchAgentService:
    """
    深度 Web 搜索服务
    
    实现多步搜索流程：查询理解 → 子查询拆解 → 多路搜索 → 聚合 → 回答
    """
    
    def __init__(self, search_provider: Optional[SearchProvider] = None):
        """
        Args:
            search_provider: 搜索提供者，默认从环境变量配置获取
        """
        self.search_provider = search_provider or get_search_provider()
    
    async def run(
        self, 
        query: str, 
        user_context: Optional[Dict[str, Any]] = None,
        max_steps: int = 4
    ) -> SearchAgentResult:
        """
        执行深度 Web 搜索
        
        Args:
            query: 用户问题
            user_context: 用户上下文（已知信息等）
            max_steps: 最大执行步数（预留，当前未使用）
            
        Returns:
            SearchAgentResult 包含综合答案和来源
        """
        logger.info(f"🔍 Starting deep web search for: {query[:50]}...")
        
        # Step 1: 规范化/理解问题
        normalized_query = await self._interpret_query(query, user_context)
        
        # Step 2: 生成子查询
        sub_queries = await self._decompose_query(normalized_query)
        logger.info(f"📋 Generated {len(sub_queries)} sub-queries: {sub_queries}")
        
        # Step 3: 对每个子查询执行搜索
        all_sources: List[SearchSource] = []
        for sub_q in sub_queries:
            sub_sources = await self._search_single_query(sub_q)
            all_sources.extend(sub_sources)
        logger.info(f"🌐 Fetched {len(all_sources)} total sources")
        
        # Step 4: 可选 - 抓取正文（当前跳过，只用 snippet）
        # enriched_sources = []
        # for src in all_sources:
        #     enriched_sources.append(await self._fetch_and_analyze(src))
        
        # Step 5: 聚合去重
        final_sources = self._aggregate_sources(all_sources)
        logger.info(f"📊 Aggregated to {len(final_sources)} unique sources")
        
        # Step 6: 综合回答
        answer = await self._synthesize_answer(normalized_query, final_sources)
        
        return SearchAgentResult(
            query=normalized_query,
            sub_queries=sub_queries,
            sources=final_sources,
            answer=answer,
        )
    
    async def _interpret_query(
        self, 
        query: str, 
        user_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        规范化/增强用户问题
        
        结合 user_context 对 query 做最小程度重写：
        - 补全省略信息（如时间范围）
        - 去除无关语气词
        """
        # 简单清理
        query = query.strip()
        
        # 移除常见语气词
        for phrase in ["请问", "帮我", "我想知道", "能告诉我"]:
            query = query.replace(phrase, "")
        
        query = query.strip()
        
        # 如果有时间相关上下文，可以补充
        if user_context and user_context.get("current_year"):
            # 检测是否需要时间限定
            time_keywords = ["最新", "近期", "最近", "现在", "当前"]
            if any(kw in query for kw in time_keywords):
                query = f"{query} {user_context['current_year']}"
        
        return query
    
    async def _decompose_query(
        self, 
        query: str, 
        max_sub_queries: int = 3
    ) -> List[str]:
        """
        将复杂问题拆解成 1~N 个子查询
        """
        # 简单规则：检测是否需要拆解
        decompose_keywords = ["对比", "区别", "和", "与", "历史", "发展", "原因", "影响"]
        
        need_decompose = any(kw in query for kw in decompose_keywords) and len(query) > 20
        
        if not need_decompose:
            return [query]
        
        # 使用 LLM 拆解
        try:
            from alice.control_plane import get_control_plane
            
            cp = get_control_plane()
            llm = cp.create_llm_for_task_sync("chat")
            prompt_template = cp.get_prompt_sync(QUERY_DECOMPOSE_PROMPT_KEY)
            prompt = prompt_template.format(query=query)
            response = llm.chat([{"role": "user", "content": prompt}])
            
            # 解析 JSON
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                sub_queries = json.loads(match.group())
                if isinstance(sub_queries, list) and len(sub_queries) > 0:
                    return sub_queries[:max_sub_queries]
        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
        
        # 降级：返回原查询
        return [query]
    
    async def _search_single_query(
        self, 
        query: str, 
        top_k: int = 5
    ) -> List[SearchSource]:
        """
        对单个子查询执行搜索
        """
        results = await self.search_provider.search(query, top_k=top_k)
        
        return [
            SearchSource(
                url=r.url,
                title=r.title,
                snippet=r.snippet,
                score=r.score,
            )
            for r in results
        ]
    
    async def _fetch_and_analyze(self, source: SearchSource) -> SearchSource:
        """
        抓取页面正文并分析（可选增强）
        
        当前返回原 source，后续可接入 readability / trafilatura
        """
        # TODO: 实现正文抓取
        # try:
        #     async with httpx.AsyncClient() as client:
        #         resp = await client.get(source.url, timeout=10)
        #         # 使用 readability 或 trafilatura 提取正文
        #         source.content = extract_content(resp.text)
        # except:
        #     pass
        return source
    
    def _aggregate_sources(
        self, 
        all_sources: List[SearchSource], 
        max_sources: int = 10
    ) -> List[SearchSource]:
        """
        合并多个子查询的结果：去重 + 排序 + 截断
        """
        # 按 URL 去重
        seen_urls = set()
        unique_sources = []
        
        for src in all_sources:
            if src.url not in seen_urls:
                seen_urls.add(src.url)
                unique_sources.append(src)
        
        # 按 score 排序（如果有）
        unique_sources.sort(
            key=lambda s: s.score if s.score is not None else 0,
            reverse=True
        )
        
        return unique_sources[:max_sources]
    
    async def _synthesize_answer(
        self,
        query: str,
        sources: List[SearchSource],
    ) -> str:
        """
        调用 LLM 生成综合回答
        """
        if not sources:
            return "抱歉，未找到相关搜索结果。"
        
        # 格式化来源
        sources_text = ""
        for i, src in enumerate(sources, 1):
            sources_text += f"[[{i}]] {src.title or 'Untitled'}\n"
            sources_text += f"    URL: {src.url}\n"
            sources_text += f"    摘要: {src.snippet or src.content or 'N/A'}\n\n"
        
        try:
            from alice.control_plane import get_control_plane
            
            cp = get_control_plane()
            llm = cp.create_llm_for_task_sync("chat")
            prompt_template = cp.get_prompt_sync(ANSWER_SYNTHESIS_PROMPT_KEY)
            prompt = prompt_template.format(
                query=query,
                sources=sources_text,
            )
            answer = llm.chat([{"role": "user", "content": prompt}])
            return answer
            
        except Exception as e:
            logger.error(f"Answer synthesis failed: {e}")
            # 降级：返回来源摘要
            return f"搜索找到 {len(sources)} 个相关结果，但无法生成综合回答。\n\n{sources_text}"
