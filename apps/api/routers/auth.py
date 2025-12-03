"""
认证路由
P3-04: JWT认证
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
import bcrypt
from sqlalchemy.orm import Session

from packages.config import get_config
from packages.db import User, Tenant

from ..deps import get_db, get_current_user
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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8')[:72], 
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """哈希密码"""
    return bcrypt.hashpw(
        password.encode('utf-8')[:72], 
        bcrypt.gensalt()
    ).decode('utf-8')


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    用户登录
    
    返回JWT Token用于后续API调用
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    
    # 开发模式下允许空密码登录
    if config.debug and not user.password_hash:
        pass
    elif not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    
    access_token = create_access_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    用户注册
    
    创建新用户和个人租户，返回JWT Token
    """
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )
    
    # 创建个人租户
    tenant = Tenant(
        name=f"{request.username}的空间",
        slug=f"user-{request.email.split('@')[0]}-{datetime.utcnow().timestamp():.0f}",
    )
    db.add(tenant)
    db.flush()
    
    # 创建用户
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        username=request.username,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    
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
