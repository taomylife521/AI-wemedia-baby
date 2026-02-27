"""
配置中心模块（优化版）
文件路径：src/core/common/config/config_center.py
功能：统一管理所有配置文件，支持本地+远程配置、热更新、配置回滚
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import logging
from datetime import datetime
import hashlib
import asyncio

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.infrastructure.network.http_client import AsyncHttpClient
from src.infrastructure.storage.file_storage import AsyncFileStorage

logger = logging.getLogger(__name__)


class ConfigVersionManager:
    """配置版本管理器
    
    管理配置的版本历史，支持配置回滚。
    """
    
    def __init__(self, max_versions: int = 5):
        """初始化配置版本管理器
        
        Args:
            max_versions: 保留的最大版本数
        """
        self.max_versions = max_versions
        self.versions: Dict[str, List[Dict[str, Any]]] = {}  # config_key -> [versions]
    
    def save_version(self, config_key: str, config_data: Dict[str, Any]) -> int:
        """保存配置版本
        
        Args:
            config_key: 配置键
            config_data: 配置数据
        
        Returns:
            版本号
        """
        if config_key not in self.versions:
            self.versions[config_key] = []
        
        version = {
            'version': len(self.versions[config_key]) + 1,
            'timestamp': datetime.now().isoformat(),
            'data': config_data.copy(),
            'hash': self._calculate_hash(config_data)
        }
        
        self.versions[config_key].append(version)
        
        # 只保留最近max_versions个版本
        if len(self.versions[config_key]) > self.max_versions:
            self.versions[config_key] = self.versions[config_key][-self.max_versions:]
        
        return version['version']
    
    def get_version(self, config_key: str, version: int) -> Optional[Dict[str, Any]]:
        """获取指定版本的配置
        
        Args:
            config_key: 配置键
            version: 版本号
        
        Returns:
            配置数据，如果版本不存在返回None
        """
        if config_key not in self.versions:
            return None
        
        for v in self.versions[config_key]:
            if v['version'] == version:
                return v['data']
        
        return None
    
    def get_latest_version(self, config_key: str) -> Optional[Dict[str, Any]]:
        """获取最新版本的配置
        
        Args:
            config_key: 配置键
        
        Returns:
            最新配置数据，如果不存在返回None
        """
        if config_key not in self.versions or not self.versions[config_key]:
            return None
        
        return self.versions[config_key][-1]['data']
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算配置数据的哈希值
        
        Args:
            data: 配置数据
        
        Returns:
            哈希值
        """
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变化处理器"""
    
    def __init__(self, callback: Callable[[str], None]):
        """初始化处理器
        
        Args:
            callback: 文件变化时的回调函数
        """
        self.callback = callback
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory:
            self.callback(event.src_path)


class ConfigCenter:
    """配置中心 - 统一管理所有配置文件（优化版）
    
    支持：
    - 本地配置（JSON/YAML）
    - 远程配置（HTTP API）
    - 热更新（文件监控+轮询）
    - 配置回滚（保留最近5个版本）
    - 分类管理（支持点号分隔的配置路径）
    """
    
    def __init__(
        self,
        config_dir: str = "config",
        remote_config_url: Optional[str] = None,
        poll_interval: int = 60
    ):
        """初始化配置中心
        
        Args:
            config_dir: 配置目录路径
            remote_config_url: 远程配置URL（可选）
            poll_interval: 轮询远程配置的间隔（秒）
        """
        self.config_dir = Path(config_dir)
        self.remote_config_url = remote_config_url
        self.poll_interval = poll_interval
        
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._version_manager = ConfigVersionManager(max_versions=5)
        self._change_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        self._http_client = AsyncHttpClient()
        self._file_storage = AsyncFileStorage(str(self.config_dir))
        
        # 获取当前事件循环
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
            logger.warning("ConfigCenter initialized without running event loop")
        
        # 文件监控
        self._observer: Optional[Observer] = None
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务控制
        self._load_task = None
        self._poll_task = None

        # 注意：不在此处自动启动加载，应在 initialize() 中显式调用并等待
        # 这样可以确保在使用配置前已完成加载
        # self._load_task = asyncio.create_task(self._load_all_configs())
        
        # 启动文件监控
        self._start_file_watcher()
        
        # 启动远程配置轮询
        if self.remote_config_url:
            asyncio.create_task(self._poll_remote_config())
    
    async def _load_all_configs(self) -> None:
        """加载所有配置（异步）"""
        try:
            await self._load_local_configs()
            if self.remote_config_url:
                await self._load_remote_configs()
        except Exception as e:
            logger.error(f"加载配置失败: {e}", exc_info=True)
    
    async def initialize(self) -> None:
        """初始化配置中心（异步）"""
        # 加载配置
        if self._load_task is None:
            import asyncio
            self._load_task = asyncio.create_task(self._load_all_configs())
            await self._load_task
        
        # 启动远程配置轮询
        if self.remote_config_url and self._poll_task is None:
            import asyncio
            self._poll_task = asyncio.create_task(self._poll_remote_config())
    
    async def _load_local_configs(self) -> None:
        """加载本地配置（异步）"""
        config_files = [
            ("app_config", "app_config.json"),
            ("ui_config", "ui/ui_config.json"),
            ("cache_config", "cache/cache_config.json"),
        ]
        
        for config_key, config_file in config_files:
            # AsyncFileStorage 已经配置了 base_path，所以这里不需要拼接 config_dir
            # 使用相对路径，AsyncFileStorage 会自动处理
            config_path = config_file
            if await self._file_storage.file_exists(str(config_path)):
                try:
                    content = await self._file_storage.read_file(str(config_path), "r")
                    config_data = json.loads(content)
                    self._configs[config_key] = config_data
                    # 保存版本
                    self._version_manager.save_version(config_key, config_data)
                    logger.debug(f"加载本地配置成功: {config_key}")
                except Exception as e:
                    logger.error(f"加载本地配置失败: {config_key}, 错误: {e}", exc_info=True)
    
    async def _load_remote_configs(self) -> None:
        """加载远程配置（异步）"""
        try:
            response = await self._http_client.get(self.remote_config_url)
            if isinstance(response, dict):
                for key, value in response.items():
                    self._configs[key] = value
                    # 保存版本
                    self._version_manager.save_version(key, value)
                logger.debug("加载远程配置成功")
        except Exception as e:
            logger.error(f"加载远程配置失败: {e}", exc_info=True)
    
    def _start_file_watcher(self) -> None:
        """启动文件监控"""
        try:
            self._observer = Observer()
            handler = ConfigFileHandler(self._on_config_file_changed)
            self._observer.schedule(handler, str(self.config_dir), recursive=True)
            self._observer.start()
            logger.debug("配置文件监控已启动")
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}", exc_info=True)
    
    def _on_config_file_changed(self, file_path: str) -> None:
        """配置文件变化回调
        
        Args:
            file_path: 变化的文件路径
        """
        # 确定配置键
        config_key = None
        if file_path.endswith("app_config.json"):
            config_key = "app_config"
        elif file_path.endswith("ui_config.json"):
            config_key = "ui_config"
        elif file_path.endswith("cache_config.json"):
            config_key = "cache_config"
        
        if config_key and hasattr(self, '_loop') and self._loop:
            # 异步重新加载配置 (跨线程)
            # 确保传递绝对路径，避免 AsyncFileStorage 重复拼接 base_path
            abs_file_path = str(Path(file_path).resolve())
            asyncio.run_coroutine_threadsafe(
                self._reload_config(config_key, abs_file_path),
                self._loop
            )
    
    async def _reload_config(self, config_key: str, file_path: str) -> None:
        """重新加载配置（异步）
        
        Args:
            config_key: 配置键
            file_path: 配置文件路径
        """
        try:
            content = await self._file_storage.read_file(file_path, "r")
            config_data = json.loads(content)
            old_data = self._configs.get(config_key)
            self._configs[config_key] = config_data
            # 保存版本
            self._version_manager.save_version(config_key, config_data)
            
            # 通知变化
            for callback in self._change_callbacks:
                try:
                    callback(config_key, config_data)
                except Exception as e:
                    logger.error(f"执行配置变化回调失败: {e}", exc_info=True)
            
            logger.info(f"配置热更新成功: {config_key}")
        except Exception as e:
            logger.error(f"重新加载配置失败: {config_key}, 错误: {e}", exc_info=True)
    
    async def _poll_remote_config(self) -> None:
        """轮询远程配置（异步）"""
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._load_remote_configs()
            except Exception as e:
                logger.error(f"轮询远程配置失败: {e}", exc_info=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持分类管理，如storage.db_path）
        
        Args:
            key: 配置键，支持点号分隔（如storage.db_path）
            default: 默认值
        
        Returns:
            配置值，如果不存在返回默认值
        """
        keys = key.split('.')
        value = self._configs
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_app_config(self) -> Dict[str, Any]:
        """获取应用配置
        
        Returns:
            应用配置字典
        """
        return self._configs.get("app_config", {})
    
    def get_platform_config(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """获取平台配置
        
        Args:
            platform_name: 平台名称
        
        Returns:
            平台配置字典，如果不存在返回None
        """
        return self._configs.get(f"platform_{platform_name}")
    
    async def update(self, key: str, value: Any) -> None:
        """更新配置值（异步）
        
        Args:
            key: 配置键
            value: 配置值
        """
        # 保存旧版本
        old_data = self._configs.get(key, {}).copy()
        self._version_manager.save_version(key, old_data)
        
        # 更新配置
        self._configs[key] = value
        
        # 保存到文件
        config_file = f"{key}.json"
        if key == "app_config":
            config_path = config_file
        elif key == "ui_config":
            config_path = f"ui/{config_file}"
        elif key == "cache_config":
            config_path = f"cache/{config_file}"
        else:
            config_path = config_file
        
        content = json.dumps(value, indent=2, ensure_ascii=False)
        await self._file_storage.write_file(str(config_path), content, "w")
        
        logger.info(f"配置更新成功: {key}")
    
    async def rollback(self, config_key: str, version: int) -> bool:
        """回滚到指定版本（异步）
        
        Args:
            config_key: 配置键
            version: 版本号
        
        Returns:
            如果回滚成功返回True，否则返回False
        """
        config_data = self._version_manager.get_version(config_key, version)
        if config_data is None:
            logger.warning(f"配置版本不存在: {config_key}, version={version}")
            return False
        
        await self.update(config_key, config_data)
        logger.info(f"配置回滚成功: {config_key}, version={version}")
        return True
    
    def watch_changes(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """监听配置变化
        
        Args:
            callback: 配置变化回调函数 (config_key, config_data) -> None
        """
        self._change_callbacks.append(callback)
    
    async def reload(self) -> None:
        """重新加载所有配置（异步）"""
        await self._load_all_configs()
        logger.info("重新加载所有配置完成")
    
    def close(self) -> None:
        """关闭配置中心"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        # 关闭HTTP客户端（同步方式，因为可能没有运行的事件循环）
        if self._http_client:
            try:
                # 尝试获取运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    # 如果事件循环正在运行，创建任务（但不等待完成，因为可能阻塞）
                    # 注意：这可能会导致资源清理不完整，但避免阻塞关闭流程
                    asyncio.create_task(self._http_client.close())
                except RuntimeError:
                    # 没有运行的事件循环，创建新的事件循环并运行
                    try:
                        asyncio.run(self._http_client.close())
                    except Exception as e:
                        logger.warning(f"关闭HTTP客户端失败: {e}")
            except Exception as e:
                logger.warning(f"关闭HTTP客户端失败: {e}")

