"""
通用加密工具

用于加密存储敏感数据（API Key、凭证等）
"""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from packages.config import get_config


def _get_cipher() -> Fernet:
    """获取加密器实例"""
    config = get_config()
    key = hashlib.sha256(config.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(value: str) -> str:
    """加密字符串值"""
    if not value:
        return ""
    return _get_cipher().encrypt(value.encode()).decode()


def decrypt_value(encrypted: Optional[str]) -> Optional[str]:
    """解密字符串值"""
    if not encrypted:
        return None
    try:
        return _get_cipher().decrypt(encrypted.encode()).decode()
    except Exception:
        # 解密失败，可能是未加密的旧数据
        return encrypted


def is_encrypted(value: str) -> bool:
    """检查值是否已加密（Fernet 格式）"""
    if not value:
        return False
    try:
        # Fernet token 是 base64 编码，以 gAAAAA 开头
        return value.startswith("gAAAAA")
    except Exception:
        return False
