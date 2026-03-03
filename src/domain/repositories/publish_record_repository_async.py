"""
发布记录 Repository（异步版本）- 基于 Tortoise ORM
功能：封装发布记录相关的数据访问操作
"""

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from .base_repository_async import BaseRepositoryAsync
from src.infrastructure.storage.orm_models.publish_record import PublishRecord
from src.infrastructure.storage.retry import retry_on_locked
from src.utils.date_utils import format_schedule_time_st_str

logger = logging.getLogger(__name__)


class PublishRecordRepositoryAsync(BaseRepositoryAsync):
    """发布记录 Repository（异步版本）- 基于 Tortoise ORM

    封装 publish_records 表的所有数据访问操作。
    """

    model_class = PublishRecord

    @retry_on_locked()
    async def create(
        self,
        user_id: int,
        platform_username: str,
        platform: str,
        file_path: str,
        file_type: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        cover_path: Optional[str] = None,
        poi_info: Optional[str] = None,
        micro_app_info: Optional[str] = None,
        goods_info: Optional[str] = None,
        anchor_info: Optional[str] = None,
        privacy_settings: Optional[str] = None,
        scheduled_publish_time: Optional[str] = None,
    ) -> int:
        """创建发布记录

        Args:
            user_id: 用户ID
            platform_username: 平台昵称
            platform: 平台名称
            file_path: 文件路径
            file_type: 文件类型（video/image）
            title ~ scheduled_publish_time: 可选的发布内容字段

        Returns:
            新创建的记录ID
        """
        try:
            record = await PublishRecord.create(
                user_id=user_id,
                platform_username=platform_username,
                platform=platform,
                file_path=file_path,
                file_type=file_type,
                title=title,
                description=description,
                tags=tags,
                cover_path=cover_path,
                poi_info=poi_info,
                micro_app_info=micro_app_info,
                goods_info=goods_info,
                anchor_info=anchor_info,
                privacy_settings=privacy_settings,
                scheduled_publish_time=scheduled_publish_time,
                status="pending",
            )
            return record.id
        except Exception as e:
            self.handle_error(e, "create")
            raise

    @retry_on_locked()
    async def update_status(
        self,
        record_id: int,
        status: str,
        publish_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """更新发布记录状态

        Args:
            record_id: 记录ID
            status: 状态（pending/running/success/failed）
            publish_url: 发布URL（可选）
            error_message: 错误信息（可选）

        Returns:
            是否成功
        """
        try:
            update_data = {"status": status}
            if publish_url is not None:
                update_data["publish_url"] = publish_url
            if error_message is not None:
                update_data["error_message"] = error_message

            updated = await PublishRecord.filter(id=record_id).update(**update_data)
            return updated > 0
        except Exception as e:
            self.handle_error(e, "update_status")
            return False

    @retry_on_locked()
    async def update_content(
        self,
        record_id: int,
        **kwargs,
    ) -> bool:
        """更新发布记录内容（用于编辑）

        Args:
            record_id: 记录ID
            **kwargs: 要更新的字段（如 title, description, tags 等）

        Returns:
            是否成功
        """
        try:
            kwargs["updated_at"] = datetime.now()
            updated = await PublishRecord.filter(id=record_id).update(**kwargs)
            return updated > 0
        except Exception as e:
            self.handle_error(e, "update_content")
            return False

    @retry_on_locked()
    async def delete_batch(self, record_ids: List[int]) -> bool:
        """批量删除发布记录

        Args:
            record_ids: 记录ID列表

        Returns:
            删除是否成功
        """
        if not record_ids:
            return True
        try:
            deleted = await PublishRecord.filter(id__in=record_ids).delete()
            self.logger.info(f"批量删除发布记录成功: {deleted} 条")
            return deleted > 0
        except Exception as e:
            self.handle_error(e, "delete_batch")
            return False

    async def find_records(
        self,
        user_id: int,
        platform_username: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取发布记录列表

        Args:
            user_id: 用户ID
            platform_username: 平台账号昵称（可选）
            platform: 平台名称（可选）
            status: 状态（可选）
            limit: 返回记录数限制

        Returns:
            发布记录列表
        """
        try:
            filters = {"user_id": user_id}
            if platform_username:
                filters["platform_username"] = platform_username
            if platform:
                filters["platform"] = platform
            if status:
                filters["status"] = status

            records = await (
                PublishRecord.filter(**filters)
                .order_by("-created_at")
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in records]
        except Exception as e:
            self.handle_error(e, "find_records")
            return []

    async def find_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取发布记录

        Args:
            record_id: 记录ID

        Returns:
            发布记录字典，不存在返回 None
        """
        record = await PublishRecord.get_or_none(id=record_id)
        return self._to_dict(record) if record else None

    @staticmethod
    def _to_dict(record: PublishRecord) -> Dict[str, Any]:
        """将 ORM 模型实例转换为字典（兼容旧格式）"""
        return {
            "id": record.id,
            "user_id": record.user_id,
            "platform_username": record.platform_username,
            "platform": record.platform,
            "file_path": record.file_path,
            "file_type": record.file_type,
            "title": record.title,
            "description": record.description,
            "tags": record.tags,
            "cover_path": record.cover_path,
            "poi_info": record.poi_info,
            "micro_app_info": record.micro_app_info,
            "goods_info": record.goods_info,
            "anchor_info": record.anchor_info,
            "privacy_settings": record.privacy_settings,
            "scheduled_publish_time": format_schedule_time_st_str(record.scheduled_publish_time),
            "status": record.status,
            "error_message": record.error_message,
            "publish_url": record.publish_url,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
