"""
Eval 数据模型

定义评估用例、套件和结果的数据结构
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from alice.agent.types import AgentResult


@dataclass
class EvalCase:
    """
    评估用例
    
    定义一个测试场景和预期结果
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scene: str = "chat"                          # chat/video/library/research/timeline
    query: str = ""                              # 用户问题
    expected_answer: Optional[str] = None        # 预期答案（用于对比打分）
    expected_keywords: List[str] = field(default_factory=list)  # 预期关键词
    expected_tool_calls: List[str] = field(default_factory=list)  # 预期调用的工具
    meta: Dict[str, Any] = field(default_factory=dict)  # 元数据（tags, 难度等）
    
    # 可选的上下文
    video_id: Optional[int] = None
    extra_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """
    评估结果
    
    记录单个用例的执行结果和评分
    """
    case_id: str
    success: bool                                # 是否成功执行
    score: float = 0.0                           # 评分 (0-1)
    answer: str = ""                             # Agent 的回答
    reasoning: Optional[str] = None              # 评分理由
    
    # 详细信息
    tools_called: List[str] = field(default_factory=list)  # 实际调用的工具
    keywords_matched: List[str] = field(default_factory=list)  # 匹配到的关键词
    execution_time_ms: int = 0                   # 执行时间
    error: Optional[str] = None                  # 错误信息
    
    # 原始结果（调试用）
    raw_agent_result: Optional[AgentResult] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvalSuite:
    """
    评估套件
    
    包含一组评估用例
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "default"
    description: str = ""
    cases: List[EvalCase] = field(default_factory=list)
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def from_dict_list(cls, name: str, cases_data: List[Dict]) -> "EvalSuite":
        """从字典列表创建 EvalSuite"""
        cases = [
            EvalCase(
                scene=c.get("scene", "chat"),
                query=c["query"],
                expected_answer=c.get("expected_answer"),
                expected_keywords=c.get("expected_keywords", []),
                expected_tool_calls=c.get("expected_tool_calls", []),
                meta=c.get("meta", {}),
                video_id=c.get("video_id"),
                extra_context=c.get("extra_context", {}),
            )
            for c in cases_data
        ]
        return cls(name=name, cases=cases)


@dataclass
class EvalSuiteResult:
    """
    套件评估结果汇总
    """
    suite_id: str
    suite_name: str
    results: List[EvalResult] = field(default_factory=list)
    
    # 统计信息
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    avg_score: float = 0.0
    total_time_ms: int = 0
    
    # 时间戳
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    
    def compute_stats(self):
        """计算统计信息"""
        self.total_cases = len(self.results)
        self.passed_cases = sum(1 for r in self.results if r.success and r.score >= 0.5)
        self.failed_cases = self.total_cases - self.passed_cases
        
        if self.results:
            self.avg_score = sum(r.score for r in self.results) / len(self.results)
            self.total_time_ms = sum(r.execution_time_ms for r in self.results)
        
        self.finished_at = datetime.utcnow()
