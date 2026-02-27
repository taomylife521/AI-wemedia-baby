"""
Cookie管理模块
文件路径：src/business/account/cookie_manager.py
功能：提供Cookie的加密存储和加载功能
"""

from typing import Optional, Dict, Any
import logging

from src.infrastructure.common.security.cookie_encryptor import CookieEncryptor

logger = logging.getLogger(__name__)


class CookieManager:
    """Cookie管理器 - 负责Cookie的加密存储和加载"""
    
    def __init__(self, user_id: int):
        """初始化Cookie管理器
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.encryptor = CookieEncryptor(user_id)
        self.logger = logging.getLogger(__name__)
    
    def save_cookie(
        self,
        platform_username: str,
        platform: str,
        cookie_data: Dict[str, Any],
        profile_folder_name: Optional[str] = None
    ) -> str:
        """保存Cookie（加密）
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            cookie_data: Cookie数据（字典或列表）
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            Cookie文件路径
        
        Raises:
            ValueError: 账号名称或平台名称无效
            OSError: 文件保存失败
        """
        if not platform_username or not platform:
            raise ValueError("平台用户名和平台名称不能为空")
        
        try:
            cookie_path = self.encryptor.save_cookie(
                platform_username,
                platform,
                cookie_data,
                profile_folder_name
            )
            self.logger.info(
                f"保存Cookie成功: 账号={platform_username}, 平台={platform}, "
                f"路径={cookie_path}"
            )
            return cookie_path
        except Exception as e:
            self.logger.error(f"保存Cookie失败: {e}")
            raise
    
    def load_cookie(
        self,
        platform_username: str,
        platform: str,
        profile_folder_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """加载Cookie（解密）
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            Cookie数据（字典），如果文件不存在或解密失败返回None
        """
        if not platform_username or not platform:
            self.logger.warning("平台用户名或平台名称为空")
            return None
        
        try:
            cookie_data = self.encryptor.load_cookie(platform_username, platform, profile_folder_name)
            if cookie_data:
                self.logger.info(
                    f"加载Cookie成功: 账号={platform_username}, 平台={platform}"
                )
            else:
                self.logger.warning(
                    f"Cookie文件不存在: 账号={platform_username}, 平台={platform}"
                )
            return cookie_data
        except Exception as e:
            self.logger.error(f"加载Cookie失败: {e}")
            return None
    
    def delete_cookie(
        self,
        platform_username: str,
        platform: str,
        profile_folder_name: Optional[str] = None
    ) -> bool:
        """删除Cookie文件（备份）
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            如果删除成功返回True，否则返回False
        """
        import os
        from src.infrastructure.common.path_manager import PathManager
        
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        cookie_file = str(account_root / "backup.encrypted")
        
        if not os.path.exists(cookie_file):
            self.logger.warning(f"Cookie文件不存在: {cookie_file}")
            return False
        
        try:
            os.remove(cookie_file)
            self.logger.info(f"删除Cookie成功: {cookie_file}")
            return True
        except Exception as e:
            self.logger.error(f"删除Cookie失败: {e}")
            return False
    
    def cookie_exists(
        self,
        platform_username: str,
        platform: str,
        profile_folder_name: Optional[str] = None
    ) -> bool:
        """检查Cookie文件是否存在
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            如果文件存在返回True，否则返回False
        """
        import os
        from src.infrastructure.common.path_manager import PathManager
        
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        cookie_file = str(account_root / "backup.encrypted")
        return os.path.exists(cookie_file)
    
    def get_cookie_path(
        self,
        platform_username: str,
        platform: str,
        profile_folder_name: Optional[str] = None
    ) -> str:
        """获取Cookie文件路径
        
        Args:
            platform_username: 平台用户名
            platform: 平台名称
            profile_folder_name: 账号数据文件夹名称
        
        Returns:
            Cookie文件路径
        """
        from src.infrastructure.common.path_manager import PathManager
        
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        return str(account_root / "backup.encrypted")

