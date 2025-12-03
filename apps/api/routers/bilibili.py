"""B站账号绑定路由"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from packages.db import User

from ..deps import get_current_user, get_bilibili_service
from ..services import BilibiliService
from ..services.bilibili_service import decrypt_sessdata, get_user_sessdata

router = APIRouter()


class QRCodeResponse(BaseModel):
    """二维码响应"""
    url: str
    qrcode_key: str


class QRCodeStatusResponse(BaseModel):
    """二维码状态响应"""
    status: str  # waiting, scanned, confirmed, expired, error
    message: str


class BilibiliBindStatus(BaseModel):
    """B站绑定状态"""
    is_bound: bool
    bilibili_uid: Optional[str] = None
    username: Optional[str] = None
    is_vip: bool = False
    is_expired: bool = False


@router.get("/qrcode", response_model=QRCodeResponse)
async def generate_qrcode(
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """生成B站登录二维码"""
    url, qrcode_key = await service.generate_qrcode()
    return QRCodeResponse(url=url, qrcode_key=qrcode_key)


@router.get("/qrcode/poll", response_model=QRCodeStatusResponse)
async def poll_qrcode(
    qrcode_key: str,
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """轮询二维码扫描状态"""
    status_code, message = await service.poll_qrcode(user, qrcode_key)
    return QRCodeStatusResponse(status=status_code, message=message)


@router.get("/status", response_model=BilibiliBindStatus)
async def get_bind_status(
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """获取B站绑定状态"""
    info = await service.get_bind_status(user)
    return BilibiliBindStatus(**info)


@router.delete("/unbind")
async def unbind_bilibili(
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """解绑B站账号"""
    service.unbind(user)
    return {"message": "解绑成功"}


# ========== B站收藏夹相关API ==========

class BilibiliFolderInfo(BaseModel):
    """B站收藏夹信息"""
    id: str
    title: str
    media_count: int
    folder_type: str  # favlist / season


class BilibiliFoldersResponse(BaseModel):
    """B站收藏夹列表响应"""
    created: list[BilibiliFolderInfo]  # 自己创建的收藏夹
    collected_folders: list[BilibiliFolderInfo]  # 订阅的收藏夹
    collected_seasons: list[BilibiliFolderInfo]  # 订阅的合集


@router.get("/folders", response_model=BilibiliFoldersResponse)
async def get_bilibili_folders(
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """获取用户B站账号的收藏夹列表"""
    created, collected_folders, collected_seasons = await service.get_user_folders(user)
    return BilibiliFoldersResponse(
        created=[
            BilibiliFolderInfo(id=f.id, title=f.title, media_count=f.media_count, folder_type="favlist")
            for f in created
        ],
        collected_folders=[
            BilibiliFolderInfo(id=f.id, title=f.title, media_count=f.media_count, folder_type="favlist")
            for f in collected_folders
        ],
        collected_seasons=[
            BilibiliFolderInfo(id=s.id, title=s.title, media_count=s.media_count, folder_type="season")
            for s in collected_seasons
        ],
    )


class BilibiliVideoInfo(BaseModel):
    """B站视频信息"""
    bvid: str
    title: str
    author: str
    duration: int
    cover_url: Optional[str] = None
    view_count: Optional[int] = None


class BilibiliFolderDetailResponse(BaseModel):
    """收藏夹详情响应"""
    id: str
    title: str
    media_count: int
    folder_type: str
    videos: list[BilibiliVideoInfo]


@router.get("/folders/{folder_type}/{folder_id}", response_model=BilibiliFolderDetailResponse)
async def get_folder_videos(
    folder_type: str,
    folder_id: str,
    user: User = Depends(get_current_user),
    service: BilibiliService = Depends(get_bilibili_service),
):
    """获取收藏夹/合集的视频列表"""
    folder_info, videos = await service.get_folder_detail(user, folder_type, folder_id)
    return BilibiliFolderDetailResponse(
        id=folder_info.id,
        title=folder_info.title,
        media_count=folder_info.media_count,
        folder_type=folder_type,
        videos=[
            BilibiliVideoInfo(
                bvid=v.bvid,
                title=v.title,
                author=v.author,
                duration=v.duration,
                cover_url=v.cover_url,
                view_count=v.view_count,
            )
            for v in videos
        ],
    )
