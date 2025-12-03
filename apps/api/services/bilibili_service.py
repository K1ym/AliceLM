"""B站相关服务"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from packages.config import get_config
from packages.db import User
from packages.logging import get_logger

from ..repositories import UserRepository

logger = get_logger(__name__)
config = get_config()

BILIBILI_QRCODE_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
BILIBILI_QRCODE_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
BILIBILI_NAV = "https://api.bilibili.com/x/web-interface/nav"

BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


def _get_cipher() -> Fernet:
    key = hashlib.sha256(config.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_sessdata(sessdata: str) -> str:
    """加密SESSDATA"""
    return _get_cipher().encrypt(sessdata.encode()).decode()


def decrypt_sessdata(encrypted: Optional[str]) -> Optional[str]:
    """解密SESSDATA"""
    if not encrypted:
        return None
    try:
        return _get_cipher().decrypt(encrypted.encode()).decode()
    except Exception:  # pylint: disable=broad-except
        return None


async def verify_bilibili_session(sessdata: str) -> dict:
    """验证B站会话是否有效，并获取用户信息"""
    cookies = {"SESSDATA": sessdata}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                BILIBILI_NAV,
                headers=BILIBILI_HEADERS,
                cookies=cookies,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
                user_data = data["data"]
                return {
                    "valid": True,
                    "username": user_data.get("uname", ""),
                    "is_vip": user_data.get("vipStatus", 0) == 1,
                }
            return {"valid": False, "username": "", "is_vip": False}
        except Exception:  # pylint: disable=broad-except
            return {"valid": False, "username": "", "is_vip": False}


class BilibiliService:
    """B站账号与收藏夹业务"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def generate_qrcode(self) -> Tuple[str, str]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(BILIBILI_QRCODE_GENERATE, headers=BILIBILI_HEADERS, timeout=10)
            if resp.status_code != 200:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "B站API返回错误状态")
            data = resp.json()
            if data.get("code") != 0:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "B站API调用失败")
            return data["data"]["url"], data["data"]["qrcode_key"]

    async def poll_qrcode(self, user: User, qrcode_key: str) -> Tuple[str, str]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                BILIBILI_QRCODE_POLL,
                params={"qrcode_key": qrcode_key},
                headers=BILIBILI_HEADERS,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "B站API调用失败")

            inner_code = data["data"]["code"]
            if inner_code == 86101:
                return "waiting", "等待扫描"
            if inner_code == 86090:
                return "scanned", "已扫描，请在手机上确认"
            if inner_code == 86038:
                return "expired", "二维码已失效"
            if inner_code != 0:
                return "error", data["data"].get("message", "未知错误")

            url = data["data"]["url"]
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            sessdata = params.get("SESSDATA", [None])[0]
            dede_user_id = params.get("DedeUserID", [None])[0]
            if not (sessdata and dede_user_id):
                return "error", "获取登录信息失败"

            self.user_repo.update_bilibili_bind(user, dede_user_id, encrypt_sessdata(sessdata))
            return "confirmed", f"绑定成功，B站UID: {dede_user_id}"

    async def get_bind_status(self, user: User) -> dict:
        if not user.bilibili_uid or not user.bilibili_sessdata:
            return {"is_bound": False}
        sessdata = decrypt_sessdata(user.bilibili_sessdata)
        if not sessdata:
            return {
                "is_bound": True,
                "bilibili_uid": user.bilibili_uid,
                "is_expired": True,
            }
        session_info = await verify_bilibili_session(sessdata)
        return {
            "is_bound": True,
            "bilibili_uid": user.bilibili_uid,
            "username": session_info.get("username"),
            "is_vip": session_info.get("is_vip", False),
            "is_expired": not session_info.get("valid", False),
        }

    def unbind(self, user: User) -> None:
        self.user_repo.clear_bilibili_bind(user)

    async def get_user_folders(self, user: User) -> tuple:
        sessdata = self._require_valid_session(user)
        from services.watcher import BilibiliClient

        try:
            client = BilibiliClient(sessdata)
            created_folders = client.fetch_user_favlists(user.bilibili_uid)
            collected_folders, collected_seasons = client.fetch_collected_favlists(user.bilibili_uid)
            client.close()
            return created_folders, collected_folders, collected_seasons
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, f"获取B站收藏夹失败: {exc}"
            ) from exc

    async def get_folder_detail(self, user: User, folder_type: str, folder_id: str) -> tuple:
        sessdata = self._require_valid_session(user)
        from services.watcher import BilibiliClient

        try:
            client = BilibiliClient(sessdata)
            if folder_type == "season":
                folder_info, videos = client.fetch_season(folder_id, user.bilibili_uid)
            else:
                folder_info, videos = client.fetch_favlist(folder_id)
            client.close()
            return folder_info, videos
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, f"获取视频列表失败: {exc}"
            ) from exc

    def _require_valid_session(self, user: User) -> str:
        if not user.bilibili_uid or not user.bilibili_sessdata:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先绑定B站账号")
        sessdata = decrypt_sessdata(user.bilibili_sessdata)
        if not sessdata:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "B站登录已过期，请重新绑定")
        return sessdata


def get_user_sessdata(user: User) -> Optional[str]:
    """供其它服务使用的解密接口"""
    return decrypt_sessdata(user.bilibili_sessdata)
