

import logging
from typing import Optional, Dict, Any
from src.infrastructure.common.config.config_center import ConfigCenter
from .browser_manager import UndetectedBrowserManager
from .process_supervisor import ProcessSupervisor

logger = logging.getLogger(__name__)


class BrowserFactory:
    """浏览器工厂
    
    根据配置返回对应的浏览器管理器实例。
    每个账号对应一个独立的管理器实例。
    """
    
    _initialized: bool = False
    
    @classmethod
    def _ensure_initialized(cls):
        """确保 ProcessSupervisor 已初始化"""
        if not cls._initialized:
            ProcessSupervisor.initialize()
            cls._initialized = True
    
    @staticmethod
    def get_browser_service(
        account_id: str, 
        platform: str = "", 
        platform_username: str = "",
        fingerprint_config: Optional[dict] = None,  # 新增参数,使用小写dict
        profile_folder_name: Optional[str] = None
    ) -> UndetectedBrowserManager:
        """获取浏览器服务实例
        
        Args:
            account_id: 账号唯一标识
            platform: 平台名称 (如 douyin)
            platform_username: 平台用户名
            fingerprint_config: 指纹配置,None则随机生成
            profile_folder_name: 持久化环境名称
        
        Returns:
            UndetectedBrowserManager 实例
        """
        BrowserFactory._ensure_initialized()
        
        config_center = ConfigCenter()
        app_config = config_center.get_app_config()
        scheme = app_config.get("browser_scheme", "playwright")
        
        logger.info(f"浏览器工厂: scheme={scheme}, account={platform_username}, platform={platform}")
        
        # 统一使用 UndetectedBrowserManager
        return UndetectedBrowserManager(
            account_id, 
            platform, 
            platform_username,
            fingerprint_config=fingerprint_config,  # 传递指纹配置
            profile_folder_name=profile_folder_name
        )
    
    @staticmethod
    def get_browser_manager(account_id: str) -> UndetectedBrowserManager:
        """获取浏览器管理器 (get_browser_service 的别名)
        
        Args:
            account_id: 账号唯一标识
            
        Returns:
            UndetectedBrowserManager 实例
        """
        return BrowserFactory.get_browser_service(account_id)

