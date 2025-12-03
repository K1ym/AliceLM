"""
认证路由
P3-04: JWT认证
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from packages.config import get_config
from packages.db import User, Tenant

from ..deps import get_current_user, get_auth_service, get_db
from ..services import AuthService
from ..services.auth_service import hash_password, verify_password
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserInfo, UpdateProfileRequest, ChangePasswordRequest

router = APIRouter()
config = get_config()

# Token有效期
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT Token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    payload = {
        "sub": str(user_id),  # JWT规范要求sub为字符串
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(payload, config.secret_key, algorithm="HS256")


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    """用户登录"""
    user = service.authenticate(request.email, request.password, debug_mode=config.debug)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "邮箱或密码错误")
    
    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    """用户注册"""
    if service.email_exists(request.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该邮箱已被注册")
    
    user, _ = service.register(request.email, request.username, request.password)
    access_token = create_access_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return user


@router.post("/logout")
async def logout():
    """
    登出
    
    客户端应删除本地存储的Token
    """
    return {"message": "已登出"}


@router.put("/profile", response_model=UserInfo)
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新个人信息"""
    if request.username is not None:
        user.username = request.username
    
    db.commit()
    db.refresh(user)
    return user


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    # 验证当前密码
    if not user.password_hash or not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )
    
    # 更新密码
    user.password_hash = hash_password(request.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}
