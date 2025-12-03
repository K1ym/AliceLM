"""
收藏夹路由
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from packages.config import get_config
from packages.db import Tenant, User

from ..deps import get_current_tenant, get_current_user, get_folder_service
from ..schemas import FolderCreate, FolderInfo
from ..services import FolderService

router = APIRouter()
config = get_config()


@router.get("", response_model=List[FolderInfo])
async def list_folders(
    tenant: Tenant = Depends(get_current_tenant),
    service: FolderService = Depends(get_folder_service),
):
    """获取监控的收藏夹列表"""
    folders = service.list_folders(tenant.id)
    return [
        FolderInfo(
            id=folder.id,
            folder_id=folder.folder_id,
            folder_type=folder.folder_type,
            name=folder.name,
            is_active=folder.is_active,
            video_count=video_count,
            last_scan_at=folder.last_scan_at,
        )
        for folder, video_count in folders
    ]


@router.post("", response_model=FolderInfo)
async def add_folder(
    request: FolderCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service),
):
    """添加监控收藏夹"""
    folder, video_count = service.add_folder(tenant, user, request)
    return FolderInfo(
        id=folder.id,
        folder_id=folder.folder_id,
        folder_type=folder.folder_type,
        name=folder.name,
        is_active=folder.is_active,
        video_count=video_count,
        last_scan_at=folder.last_scan_at,
    )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: FolderService = Depends(get_folder_service),
):
    """删除监控收藏夹"""
    if not service.delete_folder(tenant.id, folder_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )
    return {"message": "已删除", "folder_id": folder_id}


@router.post("/{folder_id}/scan")
async def scan_folder(
    folder_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service),
):
    """立即扫描收藏夹"""
    new_count = service.scan_folder(tenant, user, folder_id)
    return {
        "message": f"扫描完成，发现 {new_count} 个新视频",
        "new_count": new_count,
    }


@router.patch("/{folder_id}/toggle")
async def toggle_folder(
    folder_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    service: FolderService = Depends(get_folder_service),
):
    """切换收藏夹启用状态"""
    folder = service.toggle_folder(tenant.id, folder_id)
    return {
        "folder_id": folder_id,
        "is_active": folder.is_active,
    }
