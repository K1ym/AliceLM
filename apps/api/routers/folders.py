"""
收藏夹路由
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.config import get_config
from packages.db import WatchedFolder, Video, Tenant, User

from ..deps import get_db, get_current_tenant, get_current_user
from ..schemas import FolderCreate, FolderInfo

router = APIRouter()
config = get_config()


@router.get("", response_model=List[FolderInfo])
async def list_folders(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """获取监控的收藏夹列表"""
    folders = (
        db.query(WatchedFolder)
        .filter(WatchedFolder.tenant_id == tenant.id)
        .order_by(WatchedFolder.id.desc())
        .all()
    )
    
    result = []
    for f in folders:
        # 统计关联的视频数量
        video_count = (
            db.query(Video)
            .filter(Video.watched_folder_id == f.id)
            .count()
        )
        result.append(FolderInfo(
            id=f.id,
            folder_id=f.folder_id,
            folder_type=f.folder_type,
            name=f.name,
            is_active=f.is_active,
            video_count=video_count,
            last_scan_at=f.last_scan_at,
        ))
    
    return result


@router.post("", response_model=FolderInfo)
async def add_folder(
    request: FolderCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加监控收藏夹"""
    from services.watcher import BilibiliClient
    from .bilibili import decrypt_sessdata
    
    # 检查是否已存在
    existing = (
        db.query(WatchedFolder)
        .filter(
            WatchedFolder.tenant_id == tenant.id,
            WatchedFolder.folder_id == request.folder_id,
        )
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="收藏夹已存在",
        )
    
    # 获取用户绑定的B站sessdata，如果没有则使用配置
    sessdata = None
    if user.bilibili_sessdata:
        sessdata = decrypt_sessdata(user.bilibili_sessdata)
    if not sessdata:
        sessdata = config.bilibili.sessdata
    
    if not sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先绑定B站账号",
        )
    
    client = BilibiliClient(sessdata)
    
    try:
        if request.folder_type == "season":
            info, _ = client.fetch_season(request.folder_id)
        else:
            info, _ = client.fetch_favlist(request.folder_id)
        name = info.title
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取收藏夹信息失败: {e}",
        )
    
    # 创建记录
    folder = WatchedFolder(
        tenant_id=tenant.id,
        folder_id=request.folder_id,
        folder_type=request.folder_type,
        name=name,
        is_active=True,
    )
    
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
    video_count = 0
    
    # 如果需要导入历史视频，立即执行扫描
    if request.import_existing:
        from services.watcher import FolderScanner
        from packages.logging import get_logger
        logger = get_logger(__name__)
        
        scanner = FolderScanner(tenant.id, sessdata)
        try:
            new_videos = scanner.scan_folder(folder, db)
            video_count = len(new_videos)
            logger.info("folder_initial_scan_success", folder_id=folder.folder_id, video_count=video_count)
        except Exception as e:
            # 扫描失败不影响收藏夹添加，但记录日志
            logger.error("folder_initial_scan_failed", folder_id=folder.folder_id, error=str(e))
        finally:
            scanner.close()
    
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
    db: Session = Depends(get_db),
):
    """删除监控收藏夹"""
    folder = (
        db.query(WatchedFolder)
        .filter(WatchedFolder.id == folder_id, WatchedFolder.tenant_id == tenant.id)
        .first()
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )
    
    db.delete(folder)
    db.commit()
    
    return {"message": "已删除", "folder_id": folder_id}


@router.post("/{folder_id}/scan")
async def scan_folder(
    folder_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """立即扫描收藏夹"""
    from services.watcher import FolderScanner
    from .bilibili import decrypt_sessdata
    
    folder = (
        db.query(WatchedFolder)
        .filter(WatchedFolder.id == folder_id, WatchedFolder.tenant_id == tenant.id)
        .first()
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )
    
    # 获取用户绑定的B站sessdata
    sessdata = None
    if user.bilibili_sessdata:
        sessdata = decrypt_sessdata(user.bilibili_sessdata)
    if not sessdata:
        sessdata = config.bilibili.sessdata
    
    if not sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先绑定B站账号",
        )
    
    scanner = FolderScanner(tenant.id, sessdata)
    try:
        new_videos = scanner.scan_folder(folder, db)
    finally:
        scanner.close()
    
    return {
        "message": f"扫描完成，发现 {len(new_videos)} 个新视频",
        "new_count": len(new_videos),
    }


@router.patch("/{folder_id}/toggle")
async def toggle_folder(
    folder_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """切换收藏夹启用状态"""
    folder = (
        db.query(WatchedFolder)
        .filter(WatchedFolder.id == folder_id, WatchedFolder.tenant_id == tenant.id)
        .first()
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )
    
    folder.is_active = not folder.is_active
    db.commit()
    
    return {
        "folder_id": folder_id,
        "is_active": folder.is_active,
    }
