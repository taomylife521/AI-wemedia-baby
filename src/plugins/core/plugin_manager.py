import importlib
import logging
from pathlib import Path
from typing import Dict, Optional, List, Type

from .interfaces.login_plugin import LoginPluginInterface
from .interfaces.publish_plugin import PublishPluginInterface

logger = logging.getLogger(__name__)

class PluginManager:
    """
    插件管理器 - 负责动态加载和管理平台插件
    支持社区插件 (community/) 和专业插件 (pro/platforms/)
    """

    # 插件目录定义
    COMMUNITY_DIR = Path(__file__).parent.parent / "community"
    PRO_PLUGINS_DIR = Path(__file__).parent.parent / "pro"

    # 插件缓存 {platform_id: PluginInstance}
    _login_plugins: Dict[str, LoginPluginInterface] = {}
    _publish_plugins: Dict[str, PublishPluginInterface] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """初始化插件系统，扫描并加载所有插件"""
        if cls._initialized:
            return

        logger.debug("正在初始化插件系统...")
        
        # 1. 加载社区插件
        cls._load_plugins_from_dir(cls.COMMUNITY_DIR, "src.plugins.community")
        
        # 2. 加载专业版插件 (如果存在)
        if cls.PRO_PLUGINS_DIR.exists():
            logger.debug(f"发现专业版插件目录: {cls.PRO_PLUGINS_DIR}")
            cls._load_plugins_from_dir(cls.PRO_PLUGINS_DIR, "src.plugins.pro")
        else:
            logger.debug("专业版插件目录不存在，跳过加载")

        cls._initialized = True
        logger.debug(f"插件初始化完成. 登录插件: {list(cls._login_plugins.keys())}, 发布插件: {list(cls._publish_plugins.keys())}")

    @classmethod
    def _load_plugins_from_dir(cls, plugins_dir: Path, base_package: str):
        """从指定目录加载插件"""
        if not plugins_dir.exists():
            logger.warning(f"插件目录不存在: {plugins_dir}")
            return

        for plugin_dir in plugins_dir.iterdir():
            # 跳过非目录和特殊目录
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_") or plugin_dir.name == "interfaces":
                continue

            platform_id = plugin_dir.name
            
            # 1. 尝试加载登录插件
            cls._load_plugin_module(
                plugin_dir / "login_plugin.py",
                f"{base_package}.{platform_id}.login_plugin",
                LoginPluginInterface,
                cls._login_plugins
            )
            
            # 2. 尝试加载发布插件
            cls._load_plugin_module(
                plugin_dir / "publish_plugin.py",
                f"{base_package}.{platform_id}.publish_plugin",
                PublishPluginInterface,
                cls._publish_plugins
            )

    @classmethod
    def _load_plugin_module(
        cls, 
        file_path: Path, 
        module_name: str, 
        interface_class: Type, 
        storage_dict: Dict
    ):
        """加载单个插件模块"""
        if not file_path.exists():
            return

        try:
            module = importlib.import_module(module_name)
            
            # 扫描模块中的类
            for attr_name in dir(module):
                attr_value = getattr(module, attr_name)
                
                # 检查是否是接口的实现类 (排除接口本身)
                if (isinstance(attr_value, type) and 
                    issubclass(attr_value, interface_class) and 
                    attr_value is not interface_class):
                    
                    # 实例化并注册
                    try:
                        instance = attr_value()
                        plugin_pid = instance.platform_id
                        
                        # 简单的冲突检查
                        if plugin_pid in storage_dict:
                            logger.warning(f"插件冲突: {plugin_pid} 已存在，正在被 {module_name} 覆盖")
                            
                        storage_dict[plugin_pid] = instance
                        logger.debug(f"已加载插件: {attr_name} ({plugin_pid})")
                    except Exception as e:
                        logger.error(f"实例化插件 {attr_name} 失败: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"加载模块 {module_name} 失败: {e}", exc_info=True)

    @classmethod
    def get_login_plugin(cls, platform_id: str) -> Optional[LoginPluginInterface]:
        """获取登录插件"""
        cls.initialize()
        return cls._login_plugins.get(platform_id)

    @classmethod
    def get_publish_plugin(cls, platform_id: str) -> Optional[PublishPluginInterface]:
        """获取发布插件"""
        cls.initialize()
        return cls._publish_plugins.get(platform_id)

    @classmethod
    def get_available_platforms(cls) -> List[str]:
        """获取所有可用平台ID列表"""
        cls.initialize()
        # 以登录插件为准，因为发布通常依赖登录
        return sorted(list(cls._login_plugins.keys()))
