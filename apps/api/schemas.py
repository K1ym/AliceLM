"""
API数据模型
Pydantic Schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ========== 通用 ==========

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int
    pages: int
    items: List


# ========== 认证 ==========

class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    username: str = Field(..., min_length=2, max_length=50)





class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    email: str
    username: str
    tenant_id: int
    
    model_config = ConfigDict(from_attributes=True)


class UpdateProfileRequest(BaseModel):
    """更新个人信息"""
    username: Optional[str] = Field(None, min_length=2, max_length=50)


class ChangePasswordRequest(BaseModel):
    """修改密码"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


# ========== 视频 ==========

class VideoBase(BaseModel):
    """视频基础信息"""
    source_type: str = "bilibili"
    source_id: str
    title: str
    author: Optional[str] = None
    duration: Optional[int] = None
    cover_url: Optional[str] = None


class VideoCreate(VideoBase):
    """创建视频"""
    folder_id: Optional[int] = None


class VideoSummary(VideoBase):
    """视频列表项"""
    id: int
    status: str
    summary: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class VideoDetail(VideoSummary):
    """视频详情"""
    transcript_path: Optional[str] = None
    key_points: Optional[List[str]] = None
    concepts: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    error_message: Optional[str] = None


class VideoTranscript(BaseModel):
    """视频转写文本"""
    source_type: str
    source_id: str
    title: str
    transcript: str
    segments: Optional[List[dict]] = None


# ========== 收藏夹 ==========

class FolderBase(BaseModel):
    """收藏夹基础"""
    folder_id: str
    folder_type: str
    name: str


class FolderCreate(BaseModel):
    """添加收藏夹"""
    folder_id: str
    folder_type: str = "favlist"
    import_existing: bool = True  # 是否导入历史视频


class FolderInfo(FolderBase):
    """收藏夹信息"""
    id: int
    is_active: bool
    video_count: int = 0
    last_scan_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========== 问答 ==========

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=1000)
    video_ids: Optional[List[int]] = None


class QASource(BaseModel):
    """问答来源"""
    video_id: int
    title: str
    relevance: float


class QAResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: List[QASource]
    conversation_id: Optional[str] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    """搜索结果"""
    video_id: int
    title: str
    content: str
    score: float
