"""
Bilibili API 客户端
封装B站API调用，支持收藏夹、合集、追番等扫描
"""

import re
from dataclasses import dataclass
from typing import List, Optional

import httpx

from packages.config import get_config
from packages.logging import get_logger

logger = get_logger(__name__)

# API端点
API_FAVLIST = "https://api.bilibili.com/x/v3/fav/resource/list"
API_FAVLIST_ALL = "https://api.bilibili.com/x/v3/fav/folder/created/list-all"
API_FAVLIST_COLLECTED = "https://api.bilibili.com/x/v3/fav/folder/collected/list"
API_BANGUMI = "https://api.bilibili.com/x/space/bangumi/follow/list"
API_SEASON = "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
}


@dataclass
class VideoInfo:
    """视频信息"""
    bvid: str
    title: str
    author: str
    duration: int
    cover_url: Optional[str] = None
    view_count: Optional[int] = None
    aid: Optional[int] = None


@dataclass
class FolderInfo:
    """收藏夹信息"""
    id: str
    title: str
    owner: str
    owner_mid: str
    media_count: int
    folder_type: str = "favlist"  # favlist / season


class BilibiliClient:
    """Bilibili API客户端"""

    def __init__(self, sessdata: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            sessdata: B站登录cookie，用于访问私有内容
        """
        config = get_config()
        self.sessdata = sessdata or config.bilibili.sessdata
        self.client = httpx.Client(
            headers=HEADERS,
            cookies={"SESSDATA": self.sessdata} if self.sessdata else {},
            timeout=30.0,
        )

    def close(self):
        """关闭客户端"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ========== 工具方法 ==========

    @staticmethod
    def extract_media_id(url_or_id: str) -> str:
        """从URL或直接ID中提取media_id"""
        match = re.search(r'fid=(\d+)', url_or_id)
        if match:
            return match.group(1)
        if url_or_id.isdigit():
            return url_or_id
        raise ValueError(f"无法解析收藏夹ID: {url_or_id}")

    @staticmethod
    def extract_user_id(url_or_id: str) -> str:
        """从URL或直接ID中提取用户ID"""
        match = re.search(r'space\.bilibili\.com/(\d+)', url_or_id)
        if match:
            return match.group(1)
        if url_or_id.isdigit():
            return url_or_id
        raise ValueError(f"无法解析用户ID: {url_or_id}")

    def _request(self, url: str, params: dict) -> dict:
        """发送请求并检查响应"""
        resp = self.client.get(url, params=params)
        data = resp.json()
        
        if data["code"] != 0:
            logger.error("bilibili_api_error", url=url, code=data["code"], message=data.get("message"))
            raise Exception(f"API错误: {data['message']}")
        
        return data["data"]

    # ========== 收藏夹相关 ==========

    def fetch_favlist(self, media_id: str) -> tuple[FolderInfo, List[VideoInfo]]:
        """
        获取收藏夹信息和视频列表
        
        Args:
            media_id: 收藏夹ID
            
        Returns:
            (收藏夹信息, 视频列表)
        """
        all_videos = []
        page = 1
        page_size = 20
        folder_info = None

        while True:
            params = {"media_id": media_id, "pn": page, "ps": page_size}
            data = self._request(API_FAVLIST, params)

            if folder_info is None:
                info = data["info"]
                folder_info = FolderInfo(
                    id=str(info["id"]),
                    title=info["title"],
                    owner=info["upper"]["name"],
                    owner_mid=str(info["upper"]["mid"]),
                    media_count=info["media_count"],
                    folder_type="favlist",
                )

            medias = data.get("medias") or []
            for m in medias:
                all_videos.append(VideoInfo(
                    bvid=m["bvid"],
                    title=m["title"],
                    author=m["upper"]["name"],
                    duration=m["duration"],
                    cover_url=m.get("cover"),
                    view_count=m["cnt_info"]["play"],
                ))

            if not data.get("has_more"):
                break
            page += 1

        logger.info("fetched_favlist", folder_id=media_id, video_count=len(all_videos))
        return folder_info, all_videos

    def fetch_user_favlists(self, user_id: str) -> List[FolderInfo]:
        """
        获取用户创建的所有收藏夹列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            收藏夹列表
        """
        params = {"up_mid": user_id}
        data = self._request(API_FAVLIST_ALL, params)

        folders = data.get("list") or []
        result = [
            FolderInfo(
                id=str(f["id"]),
                title=f["title"],
                owner="",
                owner_mid=user_id,
                media_count=f["media_count"],
                folder_type="favlist",
            )
            for f in folders
        ]

        logger.info("fetched_user_favlists", user_id=user_id, folder_count=len(result))
        return result

    def fetch_collected_favlists(self, user_id: str) -> tuple[List[FolderInfo], List[FolderInfo]]:
        """
        获取用户订阅的收藏夹和合集
        
        Args:
            user_id: 用户ID
            
        Returns:
            (订阅的收藏夹列表, 订阅的合集列表)
        """
        all_items = []
        page = 1

        while True:
            params = {"up_mid": user_id, "pn": page, "ps": 20, "platform": "web"}
            data = self._request(API_FAVLIST_COLLECTED, params)

            items = data.get("list") or []
            if not items:
                break
            all_items.extend(items)

            if not data.get("has_more", False):
                break
            page += 1

        # 分离收藏夹(type=11)和合集(type=21)
        folders = [
            FolderInfo(
                id=str(f["id"]),
                title=f["title"],
                owner=f["upper"]["name"],
                owner_mid=str(f["upper"]["mid"]),
                media_count=f["media_count"],
                folder_type="favlist",
            )
            for f in all_items if f.get("type") == 11
        ]

        seasons = [
            FolderInfo(
                id=str(s["id"]),
                title=s["title"],
                owner=s["upper"]["name"],
                owner_mid=str(s["upper"]["mid"]),
                media_count=s["media_count"],
                folder_type="season",
            )
            for s in all_items if s.get("type") == 21
        ]

        logger.info("fetched_collected", user_id=user_id, folders=len(folders), seasons=len(seasons))
        return folders, seasons

    # ========== 合集相关 ==========

    def fetch_season(self, season_id: str, mid: str = "") -> tuple[FolderInfo, List[VideoInfo]]:
        """
        获取合集内的视频列表
        
        Args:
            season_id: 合集ID
            mid: UP主ID（可选）
            
        Returns:
            (合集信息, 视频列表)
        """
        all_videos = []
        page = 1
        page_size = 100
        season_name = ""
        season_owner = ""

        while True:
            params = {"season_id": season_id, "page_num": page, "page_size": page_size}
            if mid:
                params["mid"] = mid

            data = self._request(API_SEASON, params)

            # 第一页时获取合集元信息
            if page == 1:
                meta = data.get("meta", {})
                season_name = meta.get("name", f"合集{season_id}")
                season_owner = meta.get("upper", {}).get("name", "")

            archives = data.get("archives") or []
            if not archives:
                break

            for v in archives:
                all_videos.append(VideoInfo(
                    bvid=v["bvid"],
                    title=v["title"],
                    author=season_owner,
                    duration=v["duration"],
                    cover_url=v.get("pic"),
                    view_count=v["stat"]["view"],
                    aid=v["aid"],
                ))

            # 检查是否还有更多
            total = len(data.get("aids") or [])
            if len(all_videos) >= total:
                break
            page += 1

        folder_info = FolderInfo(
            id=season_id,
            title=season_name,
            owner=season_owner,
            owner_mid=mid,
            media_count=len(all_videos),
            folder_type="season",
        )

        logger.info("fetched_season", season_id=season_id, name=season_name, video_count=len(all_videos))
        return folder_info, all_videos

    # ========== 追番相关 ==========

    def fetch_bangumi(self, user_id: str, is_drama: bool = False) -> List[dict]:
        """
        获取用户追番/追剧列表
        
        Args:
            user_id: 用户ID
            is_drama: True=追剧, False=追番
            
        Returns:
            番剧列表
        """
        all_items = []
        page = 1

        while True:
            params = {
                "vmid": user_id,
                "pn": page,
                "ps": 30,
                "type": 2 if is_drama else 1,
            }
            data = self._request(API_BANGUMI, params)

            items = data.get("list") or []
            if not items:
                break
            all_items.extend(items)

            total = data.get("total", 0)
            if len(all_items) >= total:
                break
            page += 1

        logger.info("fetched_bangumi", user_id=user_id, is_drama=is_drama, count=len(all_items))
        return all_items

    # ========== 便捷方法 ==========

    def get_all_bvids_from_user(self, user_id: str) -> dict[str, List[str]]:
        """
        获取用户所有收藏夹的BV号，按收藏夹分类
        
        Args:
            user_id: 用户ID
            
        Returns:
            {收藏夹名: [bvid列表]}
        """
        folders = self.fetch_user_favlists(user_id)
        result = {}

        for folder in folders:
            if folder.media_count == 0:
                continue
            _, videos = self.fetch_favlist(folder.id)
            result[folder.title] = [v.bvid for v in videos]

        return result
