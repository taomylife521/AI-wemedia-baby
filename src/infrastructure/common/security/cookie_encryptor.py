"""
Cookie加密器
文件路径：src/infrastructure/common/security/cookie_encryptor.py
功能：提供密码哈希和Cookie加密功能 (从 legacy 迁移)
"""

import os
import json
import bcrypt
from cryptography.fernet import Fernet
from typing import Optional
import logging

import keyring
import base64
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """使用bcrypt哈希密码
    
    Args:
        password: 明文密码
    
    Returns:
        密码哈希字符串
    """
    # 生成盐并哈希密码
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码
    
    Args:
        password: 明文密码
        password_hash: 密码哈希字符串
    
    Returns:
        如果密码匹配返回True，否则返回False
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def generate_encryption_key() -> bytes:
    """生成Fernet加密密钥
    
    Returns:
        加密密钥（bytes）
    """
    return Fernet.generate_key()


def load_encryption_key(user_id: int) -> Optional[bytes]:
    """加载用户的加密密钥 (从系统 Keyring)
    
    Args:
        user_id: 用户ID
    
    Returns:
        加密密钥（bytes），如果不存在返回None
    """
    try:
        service_name = "WeMediaBaby"
        username = f"key_{user_id}"
        
        # 从系统凭据管理器获取
        key_b64 = keyring.get_password(service_name, username)
        
        if key_b64:
            return base64.b64decode(key_b64)
        return None
    except Exception as e:
        logger.error(f"加载加密密钥失败: {e}")
        return None


def save_encryption_key(user_id: int, key: bytes) -> None:
    """保存用户的加密密钥 (到系统 Keyring)
    
    Args:
        user_id: 用户ID
        key: 加密密钥（bytes）
    """
    try:
        service_name = "WeMediaBaby"
        username = f"key_{user_id}"
        
        # 转换为 base64 存储
        key_b64 = base64.b64encode(key).decode('utf-8')
        
        # 存入系统凭据管理器
        keyring.set_password(service_name, username, key_b64)
        logger.info(f"加密密钥已保存到系统 Keyring: {username}")
        
    except Exception as e:
        logger.error(f"保存加密密钥失败: {e}")
        raise


def ensure_user_key_exists(user_id: int) -> bytes:
    """确保用户的加密密钥存在，如果不存在则创建
    
    Args:
        user_id: 用户ID
    
    Returns:
        加密密钥（bytes）
    """
    key = load_encryption_key(user_id)
    
    if key is None:
        key = generate_encryption_key()
        save_encryption_key(user_id, key)
    
    return key


class CookieEncryptor:
    """Cookie加密器
    
    功能：
    - 使用Fernet对称加密Cookie数据
    - 每个用户使用独立的加密密钥
    """
    
    def __init__(self, user_id: int):
        """初始化Cookie加密器
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.key = ensure_user_key_exists(user_id)
        self.fernet = Fernet(self.key)
    
    def encrypt_cookie(self, cookie_data: dict) -> bytes:
        """加密Cookie数据
        
        Args:
            cookie_data: Cookie数据（字典）
        
        Returns:
            加密后的数据（bytes）
        """
        cookie_json = json.dumps(cookie_data, ensure_ascii=False)
        encrypted_data = self.fernet.encrypt(cookie_json.encode('utf-8'))
        return encrypted_data
    
    def decrypt_cookie(self, encrypted_data: bytes) -> Optional[dict]:
        """解密Cookie数据
        
        Args:
            encrypted_data: 加密后的数据（bytes）
        
        Returns:
            Cookie数据（字典），如果解密失败返回None
        """
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data)
            cookie_data = json.loads(decrypted_data.decode('utf-8'))
            return cookie_data
        except Exception as e:
            logger.error(f"Cookie解密失败: {e}")
            return None
    
    def save_cookie(
        self,
        platform_username: str,
        platform: str,
        cookie_data: dict,
        profile_folder_name: Optional[str] = None
    ) -> str:
        """保存Cookie（加密）
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            cookie_data: Cookie数据（字典）
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            Cookie文件路径
        """
        # 加密Cookie数据
        encrypted_data = self.encrypt_cookie(cookie_data)
        
        # 保存到文件
        # 新路径: data/{platform}/{profile_folder_name or platform_username}/backup.encrypted
        from src.infrastructure.common.path_manager import PathManager
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        cookie_file = str(account_root / "backup.encrypted")
        
        try:
            with open(cookie_file, 'wb') as f:
                f.write(encrypted_data)
            return cookie_file
        except OSError as e:
            logger.error(f"保存Cookie失败: {e}")
            raise
    
    def load_cookie(
        self,
        platform_username: str,
        platform: str,
        profile_folder_name: Optional[str] = None
    ) -> Optional[dict]:
        """加载Cookie（解密）
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            Cookie数据（字典），如果文件不存在或解密失败返回None
        """
        from src.infrastructure.common.path_manager import PathManager
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        cookie_file = str(account_root / "backup.encrypted")
        
        if not os.path.exists(cookie_file):
            return None
        
        try:
            with open(cookie_file, 'rb') as f:
                encrypted_data = f.read()
            
            return self.decrypt_cookie(encrypted_data)
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return None
