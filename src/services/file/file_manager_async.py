"""
文件管理模块（异步版本）
文件路径：src/business/file/file_manager_async.py
功能：管理媒体文件的添加、删除、元数据提取等（异步版本）
"""

from typing import List, Optional, Dict, Any, Callable
import logging
import os
import asyncio
from pathlib import Path
from datetime import datetime

from src.domain.repositories.media_file_repository_async import MediaFileRepositoryAsync
from src.infrastructure.storage.file_storage import AsyncFileStorage
from src.infrastructure.common.event.event_bus import EventBus
from src.infrastructure.common.di.service_locator import ServiceLocator
from src.utils.date_utils import get_current_datetime_str
from src.utils.file_utils import ensure_directory_exists, format_file_size

logger = logging.getLogger(__name__)


class FileManagerAsync:
    """文件管理器（异步版本）- 负责媒体文件的管理
    
    所有I/O操作都是异步的，提高响应性。
    """
    
    def __init__(
        self,
        user_id: int,
        media_file_repository: Optional[MediaFileRepositoryAsync] = None,
        file_storage: Optional[AsyncFileStorage] = None,
        event_bus: Optional[EventBus] = None
    ):
        """初始化文件管理器
        
        Args:
            user_id: 用户ID
            media_file_repository: 异步媒体文件仓储服务（可选，默认从ServiceLocator获取）
            file_storage: 异步文件存储服务（可选，默认从ServiceLocator获取）
            event_bus: 事件总线（可选，默认从ServiceLocator获取）
        """
        self.user_id = user_id
        self.service_locator = ServiceLocator()
        
        self.media_file_repo = media_file_repository or self.service_locator.get(MediaFileRepositoryAsync)
        self.file_storage = file_storage or self.service_locator.get(AsyncFileStorage)
        self.event_bus = event_bus or self.service_locator.get(EventBus)
        
        self.logger = logging.getLogger(__name__)
        
        # 支持的视频格式
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        # 支持的图片格式
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    async def add_file(self, file_path: str) -> Dict[str, Any]:
        """添加单个文件（异步）
        
        Args:
            file_path: 文件路径
        
        Returns:
            添加结果字典 {'success': bool, 'file_id': int, 'message': str}
        """
        try:
            path = Path(file_path)
            
            # 验证文件存在
            if not path.exists():
                return {
                    'success': False,
                    'file_id': None,
                    'message': f'文件不存在: {file_path}'
                }
            
            # 验证格式
            suffix = path.suffix.lower()
            if suffix not in self.supported_video_formats and suffix not in self.supported_image_formats:
                return {
                    'success': False,
                    'file_id': None,
                    'message': f'不支持的文件格式: {suffix}'
                }
            
            # 获取文件信息
            file_stat = path.stat()
            file_name = path.name
            file_size = file_stat.st_size
            file_type = 'video' if suffix in self.supported_video_formats else 'image'
            
            # 提取元数据（异步）
            metadata = await self._extract_metadata(file_path, file_type)
            
            # 保存到数据库
            file_id = await self.media_file_repo.add_file(
                user_id=self.user_id,
                file_path=str(path.absolute()),
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                duration=metadata.get('duration'),
                width=metadata.get('width'),
                height=metadata.get('height'),
                resolution=metadata.get('resolution')
            )
            
            self.logger.info(f"添加文件成功: {file_name}, ID: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'message': '添加成功'
            }
            
        except Exception as e:
            self.logger.error(f"添加文件失败: {e}", exc_info=True)
            return {
                'success': False,
                'file_id': None,
                'message': str(e)
            }
    
    async def add_folder(self, folder_path: str) -> Dict[str, Any]:
        """添加文件夹中的所有媒体文件（异步）
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            添加结果字典 {'success': bool, 'results': list, 'message': str}
        """
        try:
            path = Path(folder_path)
            
            if not path.is_dir():
                return {
                    'success': False,
                    'results': [],
                    'message': f'路径不是文件夹: {folder_path}'
                }
            
            results = []
            all_formats = self.supported_video_formats | self.supported_image_formats
            
            # 遍历文件夹
            for file_path in path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in all_formats:
                    result = await self.add_file(str(file_path))
                    results.append({
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        **result
                    })
            
            success_count = sum(1 for r in results if r.get('success'))
            
            return {
                'success': True,
                'results': results,
                'message': f'添加完成，成功: {success_count}, 失败: {len(results) - success_count}'
            }
            
        except Exception as e:
            self.logger.error(f"添加文件夹失败: {e}", exc_info=True)
            return {
                'success': False,
                'results': [],
                'message': str(e)
            }
    
    async def get_files(
        self,
        search_keyword: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取文件列表（异步）
        
        Args:
            search_keyword: 搜索关键词（可选）
            file_type: 文件类型过滤（video/image）
        
        Returns:
            文件列表
        """
        try:
            files = await self.media_file_repo.find_files(
                user_id=self.user_id,
                file_type=file_type,
                search_keyword=search_keyword
            )
            return files
        except Exception as e:
            self.logger.error(f"获取文件列表失败: {e}", exc_info=True)
            return []
    
    async def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取文件信息（异步）
        
        Args:
            file_id: 文件ID
        
        Returns:
            文件信息，如果不存在返回None
        """
        try:
            # 获取文件信息
            file_info = await self.media_file_repo.find_by_id(file_id)
            return file_info
        except Exception as e:
            self.logger.error(f"获取文件失败: {e}", exc_info=True)
            return None
    
    async def delete_file(self, file_id: int, delete_physical: bool = False) -> bool:
        """删除文件（异步）
        
        Args:
            file_id: 文件ID
            delete_physical: 是否删除物理文件
        
        Returns:
            如果删除成功返回True
        """
        try:
            # 1. 获取文件信息
            file_info = await self.media_file_repo.find_by_id(file_id)
            if not file_info:
                return False
            
            # 2. 从数据库删除记录
            success = await self.media_file_repo.delete_file(file_id)
            
            # 3. 如果需要，删除物理文件
            if success and delete_physical:
                file_path = file_info.get('file_path')
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.info(f"删除物理文件: {file_path}")
            
            if success:
                self.logger.info(f"删除文件成功: ID={file_id}")
            else:
                self.logger.warning(f"删除文件失败: ID={file_id}, 数据库操作未成功")
            return success
            
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}", exc_info=True)
            return False
    
    async def refresh_file_metadata(self, file_id: int) -> bool:
        """刷新文件元数据（异步）
        
        Args:
            file_id: 文件ID
        
        Returns:
            如果刷新成功返回True
        """
        try:
            # 1. 获取文件信息
            file_info = await self.media_file_repo.find_by_id(file_id)
            if not file_info:
                return False
            
            file_path = file_info.get('file_path')
            file_type = file_info.get('file_type')
            
            # 2. 检查物理文件是否存在
            if not file_path or not os.path.exists(file_path):
                self.logger.warning(f"刷新元数据失败: 文件路径不存在或无效: {file_path} (ID: {file_id})")
                return False
            
            # 3. 提取元数据
            metadata = await self._extract_metadata(file_path, file_type)
            
            # 4. 更新数据库
            if metadata:
                update_data = {
                    "file_id": file_id,
                    "duration": metadata.get('duration'),
                    "resolution": metadata.get('resolution'),
                    "width": metadata.get('width'),
                    "height": metadata.get('height')
                }
                await self.media_file_repo.update_file(**update_data)
                self.logger.info(f"刷新元数据成功: ID={file_id}")
                return True
                
            self.logger.warning(f"刷新元数据失败: 未能提取到有效元数据 (ID: {file_id})")
            return False
            
        except Exception as e:
            self.logger.error(f"刷新元数据失败: {e}", exc_info=True)
            return False
    
    async def refresh_all_files(
        self,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """刷新所有文件的元数据（异步）
        
        Args:
            progress_callback: 进度回调函数 (message, current, total)
        
        Returns:
            刷新结果
        """
        try:
            files = await self.get_files()
            total = len(files)
            refreshed_count = 0
            failed_count = 0
            
            for i, file_info in enumerate(files):
                file_id = file_info.get('id')
                
                if progress_callback:
                    progress_callback(
                        f"刷新: {file_info.get('file_name', '')}",
                        i + 1,
                        total
                    )
                
                if await self.refresh_file_metadata(file_id):
                    refreshed_count += 1
                else:
                    failed_count += 1
            
            return {
                'success': True,
                'refreshed_count': refreshed_count,
                'failed_count': failed_count,
                'message': f'刷新完成，成功: {refreshed_count}, 失败: {failed_count}'
            }
            
        except Exception as e:
            self.logger.error(f"刷新所有文件失败: {e}", exc_info=True)
            return {
                'success': False,
                'refreshed_count': 0,
                'failed_count': 0,
                'message': str(e)
            }
    
    async def _extract_metadata(
        self,
        file_path: str,
        file_type: str
    ) -> Dict[str, Any]:
        """提取文件元数据（异步）
        
        使用 asyncio.to_thread 将同步的 ffprobe 调用包装为异步
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
        
        Returns:
            元数据字典
        """
        try:
            # 在线程池中执行同步的元数据提取
            metadata = await asyncio.to_thread(
                self._extract_metadata_sync,
                file_path,
                file_type
            )
            return metadata
        except Exception as e:
            self.logger.warning(f"提取元数据失败: {e}")
            return {}
    
    def _extract_metadata_sync(
        self,
        file_path: str,
        file_type: str
    ) -> Dict[str, Any]:
        """同步提取文件元数据（内部方法）
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
        
        Returns:
            元数据字典
        """
        try:
            from src.utils.video_metadata import get_video_metadata
            
            if file_type == 'video':
                metadata = get_video_metadata(file_path)
                return {
                    'duration': metadata.get('duration'),
                    'width': metadata.get('width'),
                    'height': metadata.get('height'),
                    'resolution': f"{metadata.get('width', 0)}x{metadata.get('height', 0)}"
                }
            elif file_type == 'image':
                # 对于图片，使用 PIL 提取尺寸
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        width, height = img.size
                        return {
                            'width': width,
                            'height': height,
                            'resolution': f"{width}x{height}"
                        }
                except ImportError:
                    return {}
            return {}
        except Exception as e:
            self.logger.warning(f"提取元数据失败: {e}")
            return {}
