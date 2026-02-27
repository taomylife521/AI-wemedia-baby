"""
媒体文件 Repository（异步版本）- 基于 Tortoise ORM
功能：封装媒体文件相关的数据访问操作
"""

from typing import Optional, List, Dict, Any
import logging

from .base_repository_async import BaseRepositoryAsync
from src.infrastructure.storage.orm_models.media_file import MediaFile
from src.infrastructure.storage.retry import retry_on_locked

logger = logging.getLogger(__name__)


class MediaFileRepositoryAsync(BaseRepositoryAsync):
    """媒体文件 Repository（异步版本）- 基于 Tortoise ORM

    封装 media_files 表的所有数据访问操作。
    """

    model_class = MediaFile

    @retry_on_locked()
    async def add_file(
        self,
        user_id: int,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        duration: Optional[float] = None,
        resolution: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        has_script: bool = False,
        script_path: Optional[str] = None,
    ) -> int:
        """添加媒体文件记录

        Args:
            user_id: 用户ID
            file_path ~ script_path: 文件元数据字段

        Returns:
            新创建的文件记录ID
        """
        try:
            media = await MediaFile.create(
                user_id=user_id,
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                duration=duration,
                resolution=resolution,
                width=width,
                height=height,
                has_script=has_script,
                script_path=script_path,
            )
            self.logger.info(f"添加媒体文件记录成功: {file_name}, ID: {media.id}")
            return media.id
        except Exception as e:
            self.handle_error(e, "add_file")
            raise

    async def find_files(
        self,
        user_id: int,
        file_type: Optional[str] = None,
        search_keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取媒体文件列表

        Args:
            user_id: 用户ID
            file_type: 文件类型过滤（video/image，可选）
            search_keyword: 搜索关键词（在文件名中搜索，可选）

        Returns:
            媒体文件列表
        """
        try:
            filters = {"user_id": user_id}
            if file_type:
                filters["file_type"] = file_type
            if search_keyword:
                filters["file_name__icontains"] = search_keyword

            files = await (
                MediaFile.filter(**filters)
                .order_by("-created_at")
                .all()
            )
            return [self._to_dict(f) for f in files]
        except Exception as e:
            self.handle_error(e, "find_files")
            return []

    async def find_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """根据文件路径获取媒体文件记录

        Args:
            file_path: 文件路径

        Returns:
            媒体文件记录字典，不存在返回 None
        """
        media = await MediaFile.get_or_none(file_path=file_path)
        return self._to_dict(media) if media else None

    async def find_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """根据文件ID获取媒体文件记录

        Args:
            file_id: 文件ID

        Returns:
            媒体文件记录字典，不存在返回 None
        """
        media = await MediaFile.get_or_none(id=file_id)
        return self._to_dict(media) if media else None

    @retry_on_locked()
    async def delete_file(self, file_id: int) -> bool:
        """删除媒体文件记录

        Args:
            file_id: 文件记录ID

        Returns:
            删除成功返回 True
        """
        try:
            deleted = await MediaFile.filter(id=file_id).delete()
            if deleted:
                self.logger.info(f"删除媒体文件记录成功: ID {file_id}")
            return deleted > 0
        except Exception as e:
            self.handle_error(e, "delete_file")
            return False

    @retry_on_locked()
    async def update_file(
        self,
        file_id: int,
        **kwargs
    ) -> bool:
        """更新媒体文件元数据

        Args:
            file_id: 文件记录ID
            **kwargs: 需要更新的字段，如 duration, resolution, width, height, file_size 等
            
        Returns:
            更新成功返回 True
        """
        try:
            from datetime import datetime
            kwargs["updated_at"] = datetime.now()
            updated = await MediaFile.filter(id=file_id).update(**kwargs)
            if updated:
                self.logger.info(f"更新媒体文件记录成功: ID {file_id}, 更新字段: {list(kwargs.keys())}")
            return updated > 0
        except Exception as e:
            self.handle_error(e, "update_file")
            return False

    @staticmethod
    def _to_dict(media: MediaFile) -> Dict[str, Any]:
        """将 ORM 模型实例转换为字典（兼容旧格式）"""
        return {
            "id": media.id,
            "user_id": media.user_id,
            "file_path": media.file_path,
            "file_name": media.file_name,
            "file_type": media.file_type,
            "file_size": media.file_size,
            "duration": media.duration,
            "resolution": media.resolution,
            "width": media.width,
            "height": media.height,
            "has_script": media.has_script,
            "script_path": media.script_path,
            "created_at": media.created_at.isoformat() if media.created_at else None,
            "updated_at": media.updated_at.isoformat() if media.updated_at else None,
        }
