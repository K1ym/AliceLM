"""收藏夹服务"""

from typing import List, Tuple

from fastapi import HTTPException, status

from packages.config import get_config
from packages.db import Tenant, User, WatchedFolder
from packages.logging import get_logger

from ..schemas import FolderCreate
from ..repositories.folder_repo import FolderRepository
from ..repositories.video_repo import VideoRepository
from .bilibili_service import decrypt_sessdata

logger = get_logger(__name__)
config = get_config()


class FolderService:
    """收藏夹业务逻辑"""

    def __init__(
        self,
        folder_repo: FolderRepository,
        video_repo: VideoRepository,
    ):
        self.folder_repo = folder_repo
        self.video_repo = video_repo

    def list_folders(self, tenant_id: int) -> List[Tuple[WatchedFolder, int]]:
        folders = self.folder_repo.list_by_tenant(tenant_id)
        result = []
        for folder in folders:
            video_count = self.video_repo.count_by_tenant(
                tenant_id,
                folder_id=folder.id,
            )
            result.append((folder, video_count))
        return result

    def _resolve_sessdata(self, user: User) -> str:
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
        return sessdata

    def add_folder(
        self,
        tenant: Tenant,
        user: User,
        request: FolderCreate,
    ) -> Tuple[WatchedFolder, int]:
        from services.watcher import BilibiliClient, FolderScanner

        existing = self.folder_repo.get_by_folder_id(tenant.id, request.folder_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="收藏夹已存在",
            )

        sessdata = self._resolve_sessdata(user)
        client = BilibiliClient(sessdata)
        try:
            if request.folder_type == "season":
                info, _ = client.fetch_season(request.folder_id)
            else:
                info, _ = client.fetch_favlist(request.folder_id)
            name = info.title
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"获取收藏夹信息失败: {exc}",
            ) from exc
        finally:
            client.close()

        folder = self.folder_repo.create(
            tenant_id=tenant.id,
            folder_id=request.folder_id,
            folder_type=request.folder_type,
            name=name,
            is_active=True,
        )

        video_count = 0
        if request.import_existing:
            scanner = FolderScanner(tenant.id, sessdata)
            try:
                new_videos = scanner.scan_folder(folder, self.folder_repo.db)
                video_count = len(new_videos)
                logger.info(
                    "folder_initial_scan_success",
                    folder_id=folder.folder_id,
                    video_count=video_count,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "folder_initial_scan_failed",
                    folder_id=folder.folder_id,
                    error=str(exc),
                )
            finally:
                scanner.close()

        return folder, video_count

    def delete_folder(self, tenant_id: int, folder_id: int) -> bool:
        folder = self.folder_repo.get_by_id(folder_id, tenant_id)
        if not folder:
            return False
        return self.folder_repo.delete(folder_id)

    def toggle_folder(self, tenant_id: int, folder_id: int) -> WatchedFolder:
        folder = self.folder_repo.get_by_id(folder_id, tenant_id)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏夹不存在",
            )
        return self.folder_repo.toggle_active(folder)

    def scan_folder(
        self,
        tenant: Tenant,
        user: User,
        folder_id: int,
    ) -> int:
        from services.watcher import FolderScanner

        folder = self.folder_repo.get_by_id(folder_id, tenant.id)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏夹不存在",
            )

        sessdata = self._resolve_sessdata(user)
        scanner = FolderScanner(tenant.id, sessdata)
        try:
            new_videos = scanner.scan_folder(folder, self.folder_repo.db)
            return len(new_videos)
        finally:
            scanner.close()
