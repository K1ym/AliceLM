"""
Alice Eval 模块

提供 Agent 评估基础设施：
- EvalCase: 单个测试用例
- EvalSuite: 测试套件
- EvalResult: 评估结果
- EvalRunner: 评估执行器
"""

from .models import EvalCase, EvalSuite, EvalResult
from .runner import EvalRunner
from .scorers import SimpleScorer, LLMScorer

__all__ = [
    "EvalCase",
    "EvalSuite", 
    "EvalResult",
    "EvalRunner",
    "SimpleScorer",
    "LLMScorer",
]
