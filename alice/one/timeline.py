"""
TimelineService - 统一时间线服务

职责：
- 统一所有时间线事件的写入入口
- 提供事件查询和聚合
- 为 ContextAssembler 提供用户历史上下文
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session


@dataclass
class TimelineEventDTO:
    """时间线事件 DTO"""
    id: Optional[int]
    tenant_id: int
    user_id: Optional[int]
    event_type: str
    scene: str
    video_id: Optional[int]
    conversation_id: Optional[int]
    title: Optional[str]
    context: Optional[Dict[str, Any]]
    created_at: datetime


class TimelineService:
    """
    统一时间线服务
    
    所有事件写入都应该通过这个服务，而不是直接操作数据库。
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def append_event(
        self,
        tenant_id: int,
        event_type: str,
        scene: str,
        user_id: Optional[int] = None,
        video_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TimelineEventDTO:
        """
        追加时间线事件
        
        Args:
            tenant_id: 租户 ID
            event_type: 事件类型（EventType 枚举值）
            scene: 场景类型（SceneType 枚举值）
            user_id: 用户 ID（可选）
            video_id: 关联视频 ID（可选）
            conversation_id: 关联对话 ID（可选）
            title: 事件简述（可选）
            context: 详细上下文（可选，JSON 格式）
            
        Returns:
            创建的事件 DTO
        """
        # 延迟导入避免循环依赖
        from packages.db.models import TimelineEvent, EventType, SceneType
        
        event = TimelineEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=EventType(event_type),
            scene=SceneType(scene),
            video_id=video_id,
            conversation_id=conversation_id,
            title=title,
            context=json.dumps(context, ensure_ascii=False) if context else None,
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        return self._to_dto(event)
    
    async def list_events(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        scenes: Optional[List[str]] = None,
        video_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TimelineEventDTO]:
        """
        查询时间线事件
        
        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID（可选）
            event_types: 事件类型过滤（可选）
            scenes: 场景过滤（可选）
            video_id: 视频 ID 过滤（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            事件 DTO 列表
        """
        from packages.db.models import TimelineEvent, EventType, SceneType
        
        conditions = [TimelineEvent.tenant_id == tenant_id]
        
        if user_id is not None:
            conditions.append(TimelineEvent.user_id == user_id)
        
        if event_types:
            conditions.append(TimelineEvent.event_type.in_([EventType(t) for t in event_types]))
        
        if scenes:
            conditions.append(TimelineEvent.scene.in_([SceneType(s) for s in scenes]))
        
        if video_id is not None:
            conditions.append(TimelineEvent.video_id == video_id)
        
        if start_time:
            conditions.append(TimelineEvent.created_at >= start_time)
        
        if end_time:
            conditions.append(TimelineEvent.created_at <= end_time)
        
        stmt = (
            select(TimelineEvent)
            .where(and_(*conditions))
            .order_by(desc(TimelineEvent.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = self.db.execute(stmt)
        events = result.scalars().all()
        
        return [self._to_dto(e) for e in events]
    
    async def get_recent_summary(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取最近时间线摘要
        
        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID（可选）
            days: 统计天数
            
        Returns:
            摘要信息
        """
        from packages.db.models import TimelineEvent
        
        start_time = datetime.utcnow() - timedelta(days=days)
        
        conditions = [
            TimelineEvent.tenant_id == tenant_id,
            TimelineEvent.created_at >= start_time,
        ]
        if user_id is not None:
            conditions.append(TimelineEvent.user_id == user_id)
        
        stmt = select(TimelineEvent).where(and_(*conditions))
        result = self.db.execute(stmt)
        events = result.scalars().all()
        
        # 统计各类事件数量
        event_counts: Dict[str, int] = {}
        for event in events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # 获取最近事件
        recent_events = sorted(events, key=lambda e: e.created_at, reverse=True)[:10]
        
        return {
            "period_days": days,
            "total_events": len(events),
            "event_counts": event_counts,
            "recent_events": [
                {
                    "type": e.event_type.value,
                    "scene": e.scene.value,
                    "title": e.title,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_events
            ],
        }
    
    def _to_dto(self, event) -> TimelineEventDTO:
        """将 ORM 对象转换为 DTO"""
        return TimelineEventDTO(
            id=event.id,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            event_type=event.event_type.value,
            scene=event.scene.value,
            video_id=event.video_id,
            conversation_id=event.conversation_id,
            title=event.title,
            context=json.loads(event.context) if event.context else None,
            created_at=event.created_at,
        )


# 便捷函数，用于在各处快速记录事件
async def record_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    scene: str,
    **kwargs
) -> TimelineEventDTO:
    """
    快速记录时间线事件
    
    用法：
        await record_event(
            db, tenant_id=1,
            event_type="video_processed",
            scene="system",
            video_id=123,
            title="视频处理完成",
        )
    """
    service = TimelineService(db)
    return await service.append_event(
        tenant_id=tenant_id,
        event_type=event_type,
        scene=scene,
        **kwargs
    )
