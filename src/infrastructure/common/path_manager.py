"""
路径管理器
文件路径：src/infrastructure/common/path_manager.py
功能：统一管理应用路径，区分程序资源目录（只读）和用户数据目录（可写）
"""

import os
import sys
from pathlib import Path
from typing import Optional

class PathManager:
    """路径管理器 - 统一管理应用路径"""
    
    _app_name = "WeMediaBaby"
    _app_data_dir: Optional[Path] = None
    _resource_dir: Optional[Path] = None
    
    @classmethod
    def get_resource_dir(cls) -> Path:
        """获取资源目录（只读，安装目录）"""
        if cls._resource_dir is None:
            if getattr(sys, 'frozen', False):
                # 打包环境 (PyInstaller / Nuitka)
                cls._resource_dir = Path(sys.executable).parent
            else:
                # 开发环境 (假设是在 main.py 所在的根目录运行)
                # 使用 main.py 的绝对路径来确定项目根目录
                # 这里假设 main.py 在项目根目录，或者通过 cwd 判断
                cls._resource_dir = Path(os.getcwd())
        return cls._resource_dir

    @classmethod
    def get_app_data_dir(cls) -> Path:
        """获取用户数据目录（可写，AppData）"""
        if cls._app_data_dir is None:
            if sys.platform == 'win32':
                # Windows: %LOCALAPPDATA%\WeMediaBaby
                # 明确只使用 LOCALAPPDATA，避免数据存储到 Roaming
                local_app_data = os.environ.get('LOCALAPPDATA')
                if not local_app_data:
                     # 极端回退：如果获取不到环境变量，使用用户目录下的 AppData/Local
                    local_app_data = os.path.expanduser('~\\AppData\\Local')
                base_path = Path(local_app_data)
            elif sys.platform == 'darwin':
                # macOS: ~/Library/Application Support/WeMediaBaby
                base_path = Path(os.path.expanduser('~/Library/Application Support'))
            else:
                # Linux: ~/.local/share/WeMediaBaby
                base_path = Path(os.path.expanduser('~/.local/share'))
            
            cls._app_data_dir = base_path / cls._app_name
            # 确保基础目录存在
            cls._app_data_dir.mkdir(parents=True, exist_ok=True)
            
        return cls._app_data_dir

    @classmethod
    def get_db_path(cls) -> Path:
        """获取数据库路径"""
        return cls.get_app_data_dir() / "data" / "database.db"
        
    @classmethod
    def get_log_dir(cls) -> Path:
        """获取日志目录"""
        dir_path = cls.get_app_data_dir() / "logs"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
        
    @classmethod
    def get_config_dir(cls) -> Path:
        """获取配置目录"""
        dir_path = cls.get_app_data_dir() / "config"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @classmethod
    def get_cache_dir(cls) -> Path:
        """获取缓存目录"""
        dir_path = cls.get_app_data_dir() / "cache"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @classmethod
    def get_platform_account_dir(cls, platform: str, platform_username: str, profile_folder_name: Optional[str] = None) -> Path:
        """获取平台账号根目录
        
        Args:
            platform: 平台名称 (如 douyin)
            platform_username: 平台用户名 (唯一标识，用于Legacy或无profile_folder时)
            profile_folder_name: 实际文件夹名称 (UUID/TempName)，如有则优先使用
            
        Returns:
            Path: data/{platform}/{profile_folder_name or platform_username}
            
        Note:
            此方法只返回路径,不会自动创建目录。调用者需要自行创建所需目录。
        """
        # 优先使用 profile_folder_name (不可变ID)，否则回退到用户名
        folder_name = profile_folder_name if profile_folder_name else platform_username
        
        dir_path = cls.get_app_data_dir() / "data" / platform / folder_name
        # 移除自动创建逻辑,避免创建不必要的目录
        # dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
