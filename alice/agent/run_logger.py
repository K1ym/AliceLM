"""
Agent Run Logger

记录和持久化 Agent 执行日志，用于 Console 观测和调试
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from alice.agent.types import AgentTask, AgentResult, AgentStep, ToolTrace

logger = logging.getLogger(__name__)


@dataclass
class AgentRunLog:
    """
    Agent 执行日志
    
    记录一次 Agent 执行的完整信息
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    user_id: Optional[str] = None
    scene: str = "chat"
    query: str = ""
    
    # 执行结果
    answer: str = ""
    success: bool = True
    error: Optional[str] = None
    
    # 执行详情
    strategy: Optional[str] = None
    steps: List[Dict] = field(default_factory=list)
    tool_traces: List[Dict] = field(default_factory=list)
    citations: List[Dict] = field(default_factory=list)
    
    # 时间
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    duration_ms: int = 0
    
    # 元数据
    extra_context: Dict[str, Any] = field(default_factory=dict)


class AgentRunLogger:
    """
    Agent 执行日志记录器
    
    支持内存和文件两种存储方式
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_memory_logs: int = 100,
    ):
        """
        Args:
            storage_path: 日志存储路径，None 表示只存内存
            max_memory_logs: 内存中保留的最大日志数
        """
        self.storage_path = storage_path
        self.max_memory_logs = max_memory_logs
        self._memory_logs: List[AgentRunLog] = []
    
    def log_run(self, task: AgentTask, result: AgentResult, duration_ms: int = 0) -> AgentRunLog:
        """
        记录一次 Agent 执行
        
        Args:
            task: Agent 任务
            result: Agent 结果
            duration_ms: 执行时间（毫秒）
            
        Returns:
            AgentRunLog
        """
        run_log = AgentRunLog(
            tenant_id=task.tenant_id,
            user_id=task.user_id,
            scene=task.scene.value if hasattr(task.scene, 'value') else str(task.scene),
            query=task.query,
            answer=result.answer,
            success=not bool(result.steps and any(s.error for s in result.steps)),
            strategy=task.scene.value if hasattr(task.scene, 'value') else str(task.scene),
            steps=[self._serialize_step(s) for s in result.steps],
            tool_traces=[self._serialize_trace(t) for t in result.tool_traces],
            citations=[asdict(c) if hasattr(c, '__dataclass_fields__') else dict(c) for c in result.citations],
            duration_ms=duration_ms,
            finished_at=datetime.utcnow(),
            extra_context=task.extra_context or {},
        )
        
        # 存储
        self._store_log(run_log)
        
        logger.info(
            f"AgentRun logged: id={run_log.id}, scene={run_log.scene}, "
            f"duration={run_log.duration_ms}ms, success={run_log.success}"
        )
        
        return run_log
    
    def _serialize_step(self, step: AgentStep) -> Dict:
        """序列化 AgentStep"""
        return {
            "step_idx": step.step_idx,
            "thought": step.thought,
            "tool_name": step.tool_name,
            "tool_args": step.tool_args,
            "observation": step.observation[:500] if step.observation else None,
            "error": step.error,
        }
    
    def _serialize_trace(self, trace: ToolTrace) -> Dict:
        """序列化 ToolTrace"""
        return {
            "tool_name": trace.tool_name,
            "args": trace.args,
            "result": str(trace.result)[:500] if trace.result else None,
            "error": trace.error,
            "duration_ms": trace.duration_ms,
        }
    
    def _store_log(self, run_log: AgentRunLog):
        """存储日志"""
        # 内存存储
        self._memory_logs.append(run_log)
        
        # 限制内存大小
        if len(self._memory_logs) > self.max_memory_logs:
            self._memory_logs = self._memory_logs[-self.max_memory_logs:]
        
        # 文件存储
        if self.storage_path:
            self._save_to_file(run_log)
    
    def _save_to_file(self, run_log: AgentRunLog):
        """保存日志到文件"""
        try:
            path = Path(self.storage_path)
            path.mkdir(parents=True, exist_ok=True)
            
            # 按日期组织
            date_str = run_log.started_at.strftime("%Y-%m-%d")
            log_file = path / f"agent_runs_{date_str}.jsonl"
            
            # 序列化
            log_data = asdict(run_log)
            log_data["started_at"] = run_log.started_at.isoformat()
            log_data["finished_at"] = run_log.finished_at.isoformat() if run_log.finished_at else None
            
            # 追加写入
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to save agent run log: {e}")
    
    def get_runs(
        self,
        tenant_id: Optional[str] = None,
        scene: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentRunLog]:
        """
        获取执行日志
        
        Args:
            tenant_id: 租户 ID 过滤
            scene: 场景过滤
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            AgentRunLog 列表
        """
        logs = self._memory_logs
        
        # 过滤
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        if scene:
            logs = [l for l in logs if l.scene == scene]
        
        # 倒序（最新的在前）
        logs = list(reversed(logs))
        
        # 分页
        return logs[offset:offset + limit]
    
    def get_run(self, run_id: str) -> Optional[AgentRunLog]:
        """获取单个执行日志"""
        for log in self._memory_logs:
            if log.id == run_id:
                return log
        return None
    
    def get_stats(self, tenant_id: Optional[str] = None) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        logs = self._memory_logs
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        
        if not logs:
            return {
                "total_runs": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
                "scenes": {},
            }
        
        success_count = sum(1 for l in logs if l.success)
        total_duration = sum(l.duration_ms for l in logs)
        
        scenes = {}
        for log in logs:
            scenes[log.scene] = scenes.get(log.scene, 0) + 1
        
        return {
            "total_runs": len(logs),
            "success_rate": success_count / len(logs),
            "avg_duration_ms": total_duration // len(logs) if logs else 0,
            "scenes": scenes,
        }


# 全局单例
_global_logger: Optional[AgentRunLogger] = None


def get_agent_run_logger() -> AgentRunLogger:
    """获取全局 AgentRunLogger"""
    global _global_logger
    if _global_logger is None:
        storage_path = os.environ.get("ALICE_AGENT_LOG_PATH", "data/agent_logs")
        _global_logger = AgentRunLogger(storage_path=storage_path)
    return _global_logger


def log_agent_run(task: AgentTask, result: AgentResult, duration_ms: int = 0) -> AgentRunLog:
    """便捷函数：记录 Agent 执行"""
    return get_agent_run_logger().log_run(task, result, duration_ms)
