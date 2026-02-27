"""
功能开关配置
文件路径：config/feature_flags.py
功能：定义开源版与 Pro 版的功能开关，控制功能可用性
"""

from typing import Dict, Set
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# ============================================================
# 全局特性开关
# ============================================================

# 是否启用 v2.0 插件系统架构
# True: 优先使用 src/plugins/ 中的插件逻辑
# False: 强制使用旧版硬编码逻辑
USE_PLUGIN_SYSTEM = True


# ============================================================
# 功能开关定义
# ============================================================

class FeatureFlags:
    """功能开关管理器"""
    
    # 开源功能（Community Edition）- 默认启用
    COMMUNITY_FEATURES: Set[str] = {
        'douyin_login',              # 抖音账号登录
        'douyin_single_publish',     # 抖音单视频发布
        'local_file_manager',        # 本地文件管理
        'basic_ui',                  # 基础 UI 框架
        'browser_manager',           # 浏览器管理
    }
    
    # Pro 功能（需要许可证）- 默认禁用
    PRO_FEATURES: Set[str] = {
        'batch_publish',             # 批量发布
        'scheduled_publish',         # 定时发布
        'kuaishou_platform',         # 快手平台
        'xiaohongshu_platform',      # 小红书平台
        'wechat_video_platform',     # 视频号平台
        'user_auth',                 # 用户认证
        'subscription',              # 订阅管理
        'advanced_scheduler',        # 高级调度
        'checkpoint_resume',         # 断点续传
        'multi_account_batch',       # 多账号批量
    }
    
    # 开源平台列表
    OPEN_SOURCE_PLATFORMS: Set[str] = {'douyin'}
    
    # Pro 平台列表
    PRO_PLATFORMS: Set[str] = {'kuaishou', 'xiaohongshu', 'wechat_video'}
    
    # 运行时状态
    _pro_licensed: bool = False
    _license_key: str = ""
    
    @classmethod
    def is_feature_enabled(cls, feature: str) -> bool:
        """检查功能是否启用
        
        Args:
            feature: 功能名称
            
        Returns:
            True 如果功能可用
        """
        # 开源功能始终可用
        if feature in cls.COMMUNITY_FEATURES:
            return True
        
        # Pro 功能需要许可证
        if feature in cls.PRO_FEATURES:
            return cls._pro_licensed
        
        # 未知功能默认禁用
        logger.warning(f"未知功能: {feature}")
        return False
    
    @classmethod
    def is_platform_available(cls, platform: str) -> bool:
        """检查平台是否可用
        
        Args:
            platform: 平台ID
            
        Returns:
            True 如果平台可用
        """
        if platform in cls.OPEN_SOURCE_PLATFORMS:
            return True
        
        if platform in cls.PRO_PLATFORMS:
            return cls._pro_licensed
        
        return False
    
    @classmethod
    def get_available_platforms(cls) -> Set[str]:
        """获取当前可用的平台列表"""
        platforms = cls.OPEN_SOURCE_PLATFORMS.copy()
        if cls._pro_licensed:
            platforms.update(cls.PRO_PLATFORMS)
        return platforms
    
    @classmethod
    def activate_pro(cls, license_key: str) -> bool:
        """激活 Pro 版本
        
        Args:
            license_key: 许可证密钥
            
        Returns:
            True 如果激活成功
        """
        # TODO: 实现许可证验证逻辑
        # 这里只是占位符，实际需要服务端验证
        if license_key and len(license_key) > 0:
            cls._pro_licensed = True
            cls._license_key = license_key
            logger.info("Pro 版本已激活")
            return True
        return False
    
    @classmethod
    def is_pro_licensed(cls) -> bool:
        """检查是否为 Pro 版本"""
        return cls._pro_licensed
    
    @classmethod
    def get_edition_name(cls) -> str:
        """获取版本名称"""
        return "Pro Edition" if cls._pro_licensed else "Community Edition"


# ============================================================
# 功能装饰器
# ============================================================

class FeatureNotAvailableError(Exception):
    """功能不可用异常"""
    
    def __init__(self, feature: str, message: str = None):
        self.feature = feature
        self.message = message or f"功能 '{feature}' 需要 Pro 版本"
        super().__init__(self.message)


def require_feature(feature: str):
    """功能要求装饰器
    
    用法:
        @require_feature('batch_publish')
        def my_pro_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not FeatureFlags.is_feature_enabled(feature):
                raise FeatureNotAvailableError(feature)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_pro(func):
    """Pro 版本要求装饰器
    
    用法:
        @require_pro
        def my_pro_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not FeatureFlags.is_pro_licensed():
            raise FeatureNotAvailableError("pro", "此功能需要 Pro 版本")
        return func(*args, **kwargs)
    return wrapper


def require_platform(platform: str):
    """平台要求装饰器
    
    用法:
        @require_platform('kuaishou')
        def kuaishou_publish():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not FeatureFlags.is_platform_available(platform):
                raise FeatureNotAvailableError(
                    f"{platform}_platform",
                    f"平台 '{platform}' 需要 Pro 版本"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

def is_feature_enabled(feature: str) -> bool:
    """检查功能是否启用（便捷函数）"""
    return FeatureFlags.is_feature_enabled(feature)


def is_platform_available(platform: str) -> bool:
    """检查平台是否可用（便捷函数）"""
    return FeatureFlags.is_platform_available(platform)


def is_pro() -> bool:
    """检查是否为 Pro 版本（便捷函数）"""
    return FeatureFlags.is_pro_licensed()


def get_available_platforms() -> Set[str]:
    """获取可用平台列表（便捷函数）"""
    return FeatureFlags.get_available_platforms()
