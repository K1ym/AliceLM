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


SYSTEM_PROMPT = f"""你是一个专业的内容分类助手。根据视频标题和摘要，为视频打标签和分类。

可选分类: {", ".join(CATEGORIES)}

请严格按照以下JSON格式输出：
{{
    "category": "主分类（从可选分类中选择）",
    "tags": ["标签1", "标签2", "标签3"],
    "concepts": ["概念1", "概念2"]
}}

要求：
1. category: 从可选分类中选择最匹配的一个
2. tags: 2-5个标签，用于描述视频内容主题
3. concepts: 视频中的核心概念或专业术语（1-3个）

只输出JSON，不要有其他内容。"""


class Tagger:
    """标签分类器"""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        初始化标签分类器
        
        Args:
            llm_manager: LLM管理器实例
        """
        self.llm = llm_manager or LLMManager()

    def analyze(
        self,
        title: str,
        summary: Optional[str] = None,
        transcript_preview: Optional[str] = None,
    ) -> TagResult:
        """
        分析并生成标签
        
        Args:
            title: 视频标题
            summary: 摘要（可选）
            transcript_preview: 转写预览（可选）
            
        Returns:
            TagResult对象
        """
        content = f"标题：{title}"
        if summary:
            content += f"\n\n摘要：{summary}"
        if transcript_preview:
            content += f"\n\n内容预览：{transcript_preview[:1000]}"

        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=content),
        ]

        logger.info("tagging", title=title)

        try:
            response = self.llm.chat(messages, temperature=0.2)
            result = self._parse_response(response.content)
            
            logger.info(
                "tagging_complete",
                title=title,
                category=result.category,
                tags=result.tags,
            )

            return result

        except Exception as e:
            logger.error("tagging_failed", title=title, error=str(e))
            # 返回默认结果
            return TagResult(
                tags=[],
                category="其他",
                concepts=[],
                confidence=0.0,
            )

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

        response = self.llm.complete(
            prompt,
            system_prompt="你是一个专业的概念提取助手。",
            temperature=0.2,
        )
        
        # 解析结果
        concepts = []
        for line in response.strip().split("\n"):
            line = line.strip().strip("-").strip("•").strip()
            if line and len(line) < 50:
                concepts.append(line)
        
        return concepts[:max_concepts]
