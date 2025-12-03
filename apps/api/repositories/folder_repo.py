"""收藏夹仓储"""

from typing import List, Optional

from sqlalchemy.orm import Session

from packages.db import WatchedFolder

from .base import BaseRepository


class FolderRepository(BaseRepository[WatchedFolder]):
    """收藏夹仓储类"""

    def __init__(self, db: Session):
        super().__init__(db, WatchedFolder)

    def list_by_tenant(self, tenant_id: int) -> List[WatchedFolder]:
        return (
            self.db.query(WatchedFolder)
            .filter(WatchedFolder.tenant_id == tenant_id)
            .order_by(WatchedFolder.id.desc())
            .all()
        )

    def get_by_id(self, folder_id: int, tenant_id: int) -> Optional[WatchedFolder]:
        return (
            self.db.query(WatchedFolder)
            .filter(WatchedFolder.id == folder_id, WatchedFolder.tenant_id == tenant_id)
            .first()
        )

    def get_by_folder_id(self, tenant_id: int, folder_id: str) -> Optional[WatchedFolder]:
        return (
            self.db.query(WatchedFolder)
            .filter(WatchedFolder.tenant_id == tenant_id, WatchedFolder.folder_id == folder_id)
            .first()
        )

    def toggle_active(self, folder: WatchedFolder) -> WatchedFolder:
        folder.is_active = not folder.is_active
        self.db.commit()
        self.db.refresh(folder)
        return folder
