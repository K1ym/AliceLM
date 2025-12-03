"""
B站账号绑定路由
实现二维码扫码绑定B站账号，支持加密存储和过期检测
"""

import base64
import hashlib
from typing import Optional
from urllib.parse import urlparse, parse_qs

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from packages.config import get_config
from packages.db import User

from ..deps import get_db, get_current_user

router = APIRouter()
config = get_config()

# B站API地址
BILIBILI_QRCODE_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
BILIBILI_QRCODE_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
BILIBILI_NAV = "https://api.bilibili.com/x/web-interface/nav"

# 加密密钥（基于secret_key派生）
def get_cipher():
    """获取加密器"""
    key = hashlib.sha256(config.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_sessdata(sessdata: str) -> str:
    """加密SESSDATA"""
    cipher = get_cipher()
    return cipher.encrypt(sessdata.encode()).decode()


def decrypt_sessdata(encrypted: str) -> Optional[str]:
    """解密SESSDATA"""
    if not encrypted:
        return None
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted.encode()).decode()
    except Exception:
        return None


# 公共请求头
BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


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
):
    """
    生成B站登录二维码
    
    返回二维码URL和key，前端用URL生成二维码图片
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(BILIBILI_QRCODE_GENERATE, headers=BILIBILI_HEADERS, timeout=10)
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"B站API返回错误状态: {resp.status_code}",
                )
            
            data = resp.json()
            
            if data.get("code") != 0:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"B站API调用失败: {data.get('message', '未知错误')}",
                )
            
            return QRCodeResponse(
                url=data["data"]["url"],
                qrcode_key=data["data"]["qrcode_key"],
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"无法连接B站服务器: {str(e)}",
            )


@router.get("/qrcode/poll", response_model=QRCodeStatusResponse)
async def poll_qrcode(
    qrcode_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    轮询二维码扫描状态
    
    状态码：
    - 86101: 未扫描
    - 86090: 已扫描未确认
    - 86038: 二维码已失效
    - 0: 登录成功
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                BILIBILI_QRCODE_POLL,
                params={"qrcode_key": qrcode_key},
                headers=BILIBILI_HEADERS,
                timeout=10,
            )
            data = resp.json()
            
            if data.get("code") != 0:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="B站API调用失败",
                )
            
            inner_code = data["data"]["code"]
            
            if inner_code == 86101:
                return QRCodeStatusResponse(status="waiting", message="等待扫描")
            
            elif inner_code == 86090:
                return QRCodeStatusResponse(status="scanned", message="已扫描，请在手机上确认")
            
            elif inner_code == 86038:
                return QRCodeStatusResponse(status="expired", message="二维码已失效")
            
            elif inner_code == 0:
                # 登录成功，从URL中提取cookie信息
                url = data["data"]["url"]
                refresh_token = data["data"].get("refresh_token", "")
                
                # 解析URL获取参数
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                # 提取关键信息
                sessdata = params.get("SESSDATA", [None])[0]
                dede_user_id = params.get("DedeUserID", [None])[0]
                
                if sessdata and dede_user_id:
                    # 加密存储SESSDATA
                    encrypted_sessdata = encrypt_sessdata(sessdata)
                    
                    # 更新用户的B站绑定信息
                    user.bilibili_uid = dede_user_id
                    user.bilibili_sessdata = encrypted_sessdata
                    db.commit()
                    
                    return QRCodeStatusResponse(
                        status="confirmed",
                        message=f"绑定成功，B站UID: {dede_user_id}",
                    )
                else:
                    return QRCodeStatusResponse(
                        status="error",
                        message="获取登录信息失败",
                    )
            
            else:
                return QRCodeStatusResponse(
                    status="error",
                    message=data["data"].get("message", "未知错误"),
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="无法连接B站服务器",
            )


async def verify_bilibili_session(sessdata: str) -> dict:
    """
    验证B站会话是否有效，并获取用户信息
    
    返回: {valid: bool, username: str, is_vip: bool}
    """
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
        except Exception:
            return {"valid": False, "username": "", "is_vip": False}


@router.get("/status", response_model=BilibiliBindStatus)
async def get_bind_status(
    user: User = Depends(get_current_user),
):
    """获取B站绑定状态，包含过期检测"""
    if not user.bilibili_uid or not user.bilibili_sessdata:
        return BilibiliBindStatus(is_bound=False)
    
    # 解密SESSDATA
    sessdata = decrypt_sessdata(user.bilibili_sessdata)
    if not sessdata:
        return BilibiliBindStatus(
            is_bound=True,
            bilibili_uid=user.bilibili_uid,
            is_expired=True,
        )
    
    # 验证会话是否有效
    session_info = await verify_bilibili_session(sessdata)
    
    return BilibiliBindStatus(
        is_bound=True,
        bilibili_uid=user.bilibili_uid,
        username=session_info.get("username"),
        is_vip=session_info.get("is_vip", False),
        is_expired=not session_info.get("valid", False),
    )


@router.delete("/unbind")
async def unbind_bilibili(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解绑B站账号"""
    user.bilibili_uid = None
    user.bilibili_sessdata = None
    db.commit()
    
    return {"message": "解绑成功"}


def get_user_sessdata(user: User) -> Optional[str]:
    """
    获取用户的B站SESSDATA（解密后）
    供内部服务调用，如视频下载
    """
    if not user.bilibili_sessdata:
        return None
    return decrypt_sessdata(user.bilibili_sessdata)


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
):
    """
    获取用户B站账号的收藏夹列表
    
    包括：自己创建的收藏夹、订阅的收藏夹、订阅的合集
    """
    if not user.bilibili_uid or not user.bilibili_sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先绑定B站账号",
        )
    
    sessdata = decrypt_sessdata(user.bilibili_sessdata)
    if not sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="B站登录已过期，请重新绑定",
        )
    
    from services.watcher import BilibiliClient
    
    try:
        client = BilibiliClient(sessdata)
        
        # 获取自己创建的收藏夹
        created_folders = client.fetch_user_favlists(user.bilibili_uid)
        
        # 获取订阅的收藏夹和合集
        collected_folders, collected_seasons = client.fetch_collected_favlists(user.bilibili_uid)
        
        client.close()
        
        return BilibiliFoldersResponse(
            created=[
                BilibiliFolderInfo(
                    id=f.id,
                    title=f.title,
                    media_count=f.media_count,
                    folder_type="favlist",
                )
                for f in created_folders
            ],
            collected_folders=[
                BilibiliFolderInfo(
                    id=f.id,
                    title=f.title,
                    media_count=f.media_count,
                    folder_type="favlist",
                )
                for f in collected_folders
            ],
            collected_seasons=[
                BilibiliFolderInfo(
                    id=s.id,
                    title=s.title,
                    media_count=s.media_count,
                    folder_type="season",
                )
                for s in collected_seasons
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"获取B站收藏夹失败: {str(e)}",
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
):
    """
    获取收藏夹/合集的视频列表
    
    folder_type: favlist 或 season
    folder_id: 收藏夹或合集ID
    """
    if not user.bilibili_uid or not user.bilibili_sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先绑定B站账号",
        )
    
    sessdata = decrypt_sessdata(user.bilibili_sessdata)
    if not sessdata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="B站登录已过期，请重新绑定",
        )
    
    from services.watcher import BilibiliClient
    
    try:
        client = BilibiliClient(sessdata)
        
        if folder_type == "season":
            folder_info, videos = client.fetch_season(folder_id, user.bilibili_uid)
        else:
            folder_info, videos = client.fetch_favlist(folder_id)
        
        client.close()
        
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"获取视频列表失败: {str(e)}",
        )
