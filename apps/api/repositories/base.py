"""
基础仓储类
提供通用的 CRUD 操作
"""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """基础仓储类"""
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    def get(self, id: int) -> Optional[ModelType]:
        """根据ID获取单条记录"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_ids(self, ids: List[int]) -> List[ModelType]:
        """根据ID列表获取多条记录"""
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()
    
    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        **filters
    ) -> List[ModelType]:
        """获取列表"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.offset(skip).limit(limit).all()
    
    def count(self, **filters) -> int:
        """统计数量"""
        query = self.db.query(func.count(self.model.id))
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.scalar() or 0
    
    def create(self, **data) -> ModelType:
        """创建记录"""
        instance = self.model(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def update(self, id: int, **data) -> Optional[ModelType]:
        """更新记录"""
        instance = self.get(id)
        if instance:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        instance = self.get(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False
