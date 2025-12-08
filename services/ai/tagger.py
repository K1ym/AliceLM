"""
自动标签分类服务
P2-11: 自动标签分类
P2-12: 关键概念提取
"""

import json
from dataclasses import dataclass
from typing import List, Optional

from packages.logging import get_logger

from .llm import LLMManager, Message

logger = get_logger(__name__)


@dataclass
class TagResult:
    """标签结果"""
    tags: List[str]           # 推荐标签
    category: str             # 主分类
    concepts: List[str]       # 关键概念
    confidence: float = 1.0   # 置信度


# 预定义分类
CATEGORIES = [
    "科技", "编程", "AI/机器学习", "设计",
    "财经", "投资", "创业",
    "生活", "健康", "美食", "旅行",
    "学习", "语言", "考试",
    "娱乐", "游戏", "动漫", "音乐",
    "人文", "历史", "心理",
    "其他",
]


# 回退 prompt
_FALLBACK_TAGGER_PROMPT = f"""你是一个专业的内容分类助手。根据视频标题和摘要，为视频打标签和分类。

可选分类: {", ".join(CATEGORIES)}

请严格按照以下JSON格式输出：
{{
    "category": "主分类（从可选分类中选择）",
    "tags": ["标签1", "标签2", "标签3"],
    "concepts": ["概念1", "概念2"]
}}

只输出JSON。"""


def _get_tagger_prompt() -> str:
    """获取标签 prompt（通过 ControlPlane）"""
    try:
        from alice.control_plane import get_control_plane
        cp = get_control_plane()
        prompt = cp.get_prompt_sync("tagger")
        if prompt:
            return prompt
    except Exception:
        pass
    
    return _FALLBACK_TAGGER_PROMPT


def _get_tagger_concepts_prompt() -> str:
    """获取概念提取 prompt"""
    try:
        from alice.control_plane import get_control_plane
        cp = get_control_plane()
        prompt = cp.get_prompt_sync("tagger_concepts")
        if prompt:
            return prompt
    except Exception:
        pass
    
    return "你是一个专业的概念提取助手。"


class Tagger:
    """标签分类器"""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        初始化标签分类器
        
        Args:
            llm_manager: LLM管理器实例（如果不提供，从 ControlPlane 获取）
        """
        if llm_manager is not None:
            self.llm = llm_manager
        else:
            # 从 ControlPlane 获取带缓存的 LLM
            try:
                from alice.control_plane import get_control_plane
                cp = get_control_plane()
                self.llm = cp.create_llm_for_task_sync("tagger")
            except Exception:
                # 回退到默认
                self.llm = LLMManager()

    def analyze(
        self,
        title: str,
        summary: Optional[str] = None,
        transcript_preview: Optional[str] = None,
    ) -> TagResult:
        """同步分析并生成标签"""
        content = f"标题：{title}"
        if summary:
            content += f"\n\n摘要：{summary}"
        if transcript_preview:
            content += f"\n\n内容预览：{transcript_preview[:1000]}"
        
        system_prompt = _get_tagger_prompt()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=content),
        ]

        logger.info("tagging", title=title)

        try:
            response = self.llm.chat(messages, temperature=0.2)
            result = self._parse_response(response.content)
            logger.info("tagging_complete", title=title, category=result.category)
            return result
        except Exception as e:
            logger.error("tagging_failed", title=title, error=str(e))
            return TagResult(tags=[], category="其他", concepts=[], confidence=0.0)

    async def analyze_async(
        self,
        title: str,
        summary: Optional[str] = None,
        transcript_preview: Optional[str] = None,
    ) -> TagResult:
        """异步分析并生成标签"""
        content = f"标题：{title}"
        if summary:
            content += f"\n\n摘要：{summary}"
        if transcript_preview:
            content += f"\n\n内容预览：{transcript_preview[:1000]}"
        
        system_prompt = _get_tagger_prompt()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=content),
        ]

        logger.info("tagging_async", title=title)

        try:
            response = await self.llm.chat_async(messages, temperature=0.2)
            result = self._parse_response(response.content)
            logger.info("tagging_async_complete", title=title, category=result.category)
            return result
        except Exception as e:
            logger.error("tagging_async_failed", title=title, error=str(e))
            return TagResult(tags=[], category="其他", concepts=[], confidence=0.0)

    def _parse_response(self, content: str) -> TagResult:
        """解析LLM响应"""
        content = content.strip()
        
        # 处理markdown代码块
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"无法解析响应: {content[:200]}")

        # 验证分类
        category = data.get("category", "其他")
        if category not in CATEGORIES:
            category = "其他"

        return TagResult(
            tags=data.get("tags", [])[:5],
            category=category,
            concepts=data.get("concepts", [])[:3],
            confidence=1.0,
        )

    def extract_concepts(self, transcript: str, max_concepts: int = 5) -> List[str]:
        """
        从转写文本中提取关键概念
        
        Args:
            transcript: 转写文本
            max_concepts: 最大概念数
            
        Returns:
            概念列表
        """
        prompt = f"""从以下内容中提取 {max_concepts} 个最重要的专业术语或核心概念。
只输出概念列表，每行一个，不要编号。

内容：
{transcript[:5000]}

概念："""
        
        # 从 ControlPlane 获取 prompt
        system_prompt = _get_tagger_concepts_prompt()

        response = self.llm.complete(
            prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )
        
        # 解析结果
        concepts = []
        for line in response.strip().split("\n"):
            line = line.strip().strip("-").strip("•").strip()
            if line and len(line) < 50:
                concepts.append(line)
        
        return concepts[:max_concepts]
