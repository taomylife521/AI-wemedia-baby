"""
自动更新模块 - 核心逻辑
文件路径：tools/updater/updater_core.py
功能：检查更新、下载新版本、执行更新流程

更新流程：
1. 主程序启动时检查版本
2. 发现新版本后下载更新包
3. 启动独立更新程序 (updater.exe)
4. 主程序退出
5. 更新程序替换文件
6. 更新程序启动新版主程序
"""

import os
import sys
import json
import hashlib
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """更新状态枚举"""
    CHECKING = "checking"           # 正在检查更新
    UP_TO_DATE = "up_to_date"      # 已是最新版本
    UPDATE_AVAILABLE = "update_available"  # 有可用更新
    DOWNLOADING = "downloading"     # 正在下载
    READY_TO_INSTALL = "ready_to_install"  # 准备安装
    INSTALLING = "installing"       # 正在安装
    FAILED = "failed"              # 更新失败


@dataclass
class VersionInfo:
    """版本信息"""
    version: str                    # 版本号 (如 "1.0.1")
    release_date: str               # 发布日期
    download_url: str               # 下载地址
    file_hash: str                  # 文件哈希 (SHA256)
    file_size: int                  # 文件大小 (bytes)
    changelog: str                  # 更新日志
    is_mandatory: bool = False      # 是否强制更新


@dataclass
class UpdateResult:
    """更新结果"""
    status: UpdateStatus
    message: str
    current_version: str
    latest_version: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class UpdaterCore:
    """自动更新核心模块
    
    负责检查更新、下载更新包、验证完整性
    """
    
    # 默认更新服务器配置
    DEFAULT_UPDATE_URL = "https://your-update-server.com/api/updates"
    DEFAULT_MANIFEST_FILE = "update_manifest.json"
    
    def __init__(
        self,
        current_version: str,
        update_url: Optional[str] = None,
        download_dir: Optional[str] = None
    ):
        """初始化更新模块
        
        Args:
            current_version: 当前应用版本
            update_url: 更新服务器 URL
            download_dir: 下载目录
        """
        self.current_version = current_version
        self.update_url = update_url or self.DEFAULT_UPDATE_URL
        self.download_dir = Path(download_dir or "temp/updates")
        self.logger = logging.getLogger(__name__)
        
        # 确保下载目录存在
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存的最新版本信息
        self._latest_version_info: Optional[VersionInfo] = None
    
    async def check_for_updates(self) -> UpdateResult:
        """检查是否有可用更新
        
        Returns:
            更新检查结果
        """
        try:
            self.logger.info(f"检查更新... 当前版本: {self.current_version}")
            
            # 获取最新版本信息
            version_info = await self._fetch_latest_version()
            
            if version_info is None:
                return UpdateResult(
                    status=UpdateStatus.UP_TO_DATE,
                    message="无法获取版本信息，跳过更新检查",
                    current_version=self.current_version
                )
            
            self._latest_version_info = version_info
            
            # 比较版本
            if self._is_newer_version(version_info.version):
                self.logger.info(f"发现新版本: {version_info.version}")
                return UpdateResult(
                    status=UpdateStatus.UPDATE_AVAILABLE,
                    message=f"发现新版本 {version_info.version}",
                    current_version=self.current_version,
                    latest_version=version_info.version,
                    details={
                        "release_date": version_info.release_date,
                        "changelog": version_info.changelog,
                        "file_size": version_info.file_size,
                        "is_mandatory": version_info.is_mandatory
                    }
                )
            else:
                return UpdateResult(
                    status=UpdateStatus.UP_TO_DATE,
                    message="已是最新版本",
                    current_version=self.current_version,
                    latest_version=version_info.version
                )
                
        except Exception as e:
            self.logger.error(f"检查更新失败: {e}", exc_info=True)
            return UpdateResult(
                status=UpdateStatus.FAILED,
                message=f"检查更新失败: {e}",
                current_version=self.current_version
            )
    
    async def download_update(
        self,
        progress_callback: Optional[callable] = None
    ) -> UpdateResult:
        """下载更新包
        
        Args:
            progress_callback: 进度回调函数 (downloaded_bytes, total_bytes)
        
        Returns:
            下载结果
        """
        if self._latest_version_info is None:
            return UpdateResult(
                status=UpdateStatus.FAILED,
                message="请先检查更新",
                current_version=self.current_version
            )
        
        try:
            import aiohttp
            
            version_info = self._latest_version_info
            download_path = self.download_dir / f"update_{version_info.version}.zip"
            
            self.logger.info(f"开始下载更新: {version_info.download_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(version_info.download_url) as response:
                    if response.status != 200:
                        return UpdateResult(
                            status=UpdateStatus.FAILED,
                            message=f"下载失败: HTTP {response.status}",
                            current_version=self.current_version
                        )
                    
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    with open(download_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback:
                                progress_callback(downloaded, total_size)
            
            # 验证文件哈希
            if not self._verify_file_hash(download_path, version_info.file_hash):
                download_path.unlink()
                return UpdateResult(
                    status=UpdateStatus.FAILED,
                    message="文件校验失败，可能下载不完整",
                    current_version=self.current_version
                )
            
            self.logger.info(f"更新包下载完成: {download_path}")
            
            return UpdateResult(
                status=UpdateStatus.READY_TO_INSTALL,
                message="更新包下载完成，准备安装",
                current_version=self.current_version,
                latest_version=version_info.version,
                details={"download_path": str(download_path)}
            )
            
        except Exception as e:
            self.logger.error(f"下载更新失败: {e}", exc_info=True)
            return UpdateResult(
                status=UpdateStatus.FAILED,
                message=f"下载失败: {e}",
                current_version=self.current_version
            )
    
    def launch_updater_and_exit(self, update_package_path: str) -> bool:
        """启动独立更新程序并退出主程序
        
        Args:
            update_package_path: 更新包路径
        
        Returns:
            是否成功启动更新程序
        """
        try:
            updater_path = self._get_updater_path()
            
            if not updater_path.exists():
                self.logger.error(f"更新程序不存在: {updater_path}")
                return False
            
            # 启动更新程序
            # 参数: --package <更新包路径> --app <主程序路径>
            app_path = str(Path(sys.executable).resolve())
            
            subprocess.Popen([
                str(updater_path),
                "--package", update_package_path,
                "--app", app_path,
                "--wait-pid", str(os.getpid())
            ], shell=True)
            
            self.logger.info("更新程序已启动，主程序即将退出")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动更新程序失败: {e}", exc_info=True)
            return False
    
    async def _fetch_latest_version(self) -> Optional[VersionInfo]:
        """从服务器获取最新版本信息"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.update_url}/latest",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        self.logger.warning(f"获取版本信息失败: HTTP {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    return VersionInfo(
                        version=data.get("version", "0.0.0"),
                        release_date=data.get("release_date", ""),
                        download_url=data.get("download_url", ""),
                        file_hash=data.get("file_hash", ""),
                        file_size=data.get("file_size", 0),
                        changelog=data.get("changelog", ""),
                        is_mandatory=data.get("is_mandatory", False)
                    )
                    
        except Exception as e:
            self.logger.error(f"获取版本信息异常: {e}")
            return None
    
    def _is_newer_version(self, latest_version: str) -> bool:
        """比较版本号
        
        Args:
            latest_version: 最新版本号
        
        Returns:
            如果最新版本更新，返回 True
        """
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            # 补齐版本号长度
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            
            return latest_parts > current_parts
            
        except ValueError:
            # 版本号格式错误，返回 False
            return False
    
    def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """验证文件哈希
        
        Args:
            file_path: 文件路径
            expected_hash: 预期的 SHA256 哈希值
        
        Returns:
            是否匹配
        """
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            
            actual_hash = sha256.hexdigest()
            return actual_hash.lower() == expected_hash.lower()
            
        except Exception as e:
            self.logger.error(f"验证文件哈希失败: {e}")
            return False
    
    def _get_updater_path(self) -> Path:
        """获取更新程序路径"""
        # 优先查找 tools/updater/updater.exe
        base_path = Path(__file__).parent
        
        if sys.platform == "win32":
            updater_name = "updater.exe"
        else:
            updater_name = "updater"
        
        return base_path / updater_name
    
    def get_local_manifest(self) -> Optional[Dict[str, Any]]:
        """获取本地版本清单"""
        manifest_path = self.download_dir / self.DEFAULT_MANIFEST_FILE
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"读取本地清单失败: {e}")
        
        return None
    
    def save_local_manifest(self, manifest: Dict[str, Any]):
        """保存本地版本清单"""
        manifest_path = self.download_dir / self.DEFAULT_MANIFEST_FILE
        
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存本地清单失败: {e}")


# 便捷函数
async def check_for_updates(current_version: str) -> UpdateResult:
    """检查更新的便捷函数
    
    Args:
        current_version: 当前版本
    
    Returns:
        更新结果
    """
    updater = UpdaterCore(current_version)
    return await updater.check_for_updates()


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="媒小宝更新检查工具")
    parser.add_argument("--version", default="1.0.0", help="当前版本号")
    parser.add_argument("--check", action="store_true", help="检查更新")
    
    args = parser.parse_args()
    
    async def main():
        updater = UpdaterCore(args.version)
        result = await updater.check_for_updates()
        print(f"状态: {result.status.value}")
        print(f"消息: {result.message}")
        if result.latest_version:
            print(f"最新版本: {result.latest_version}")
    
    asyncio.run(main())
