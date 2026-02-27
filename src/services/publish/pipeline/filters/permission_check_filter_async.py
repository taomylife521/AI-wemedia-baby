"""
权限检查过滤器（异步版本）
文件路径：src/business/publish_pipeline/filters/permission_check_filter_async.py
功能：检查用户发布权限（异步）
"""

from typing import Optional
from src.infrastructure.common.pipeline.base_filter import BaseFilter, PublishContext
from src.services.subscription.permission_controller_async import PermissionControllerAsync as PermissionController
import logging

logger = logging.getLogger(__name__)


class PermissionCheckFilterAsync(BaseFilter):
    """权限检查过滤器（异步版本）"""
    
    def __init__(self, permission_controller: PermissionController):
        """初始化权限检查过滤器
        
        Args:
            permission_controller: 权限控制器实例
        """
        super().__init__()
        self.permission_controller = permission_controller
    
    async def process(self, context: PublishContext) -> bool:
        """检查发布权限（异步）
        
        Args:
            context: 发布上下文
        
        Returns:
            如果有权限返回True，否则返回False
        """
        try:
            # 检查订阅状态
            if not self.permission_controller.check_publish_permission(context.user_id):
                self.set_error("用户无发布权限，请检查订阅状态")
                return False
            
            # 检查试用次数（如果是试用用户）
            if not self.permission_controller.check_trial_count(context.user_id):
                self.set_error("试用次数已用完，请购买订阅")
                return False
            
            self.logger.info(f"权限检查通过: 用户ID={context.user_id}")
            return True
            
        except Exception as e:
            self.set_error(f"权限检查失败: {str(e)}")
            self.logger.error(self.get_error(), exc_info=True)
            return False

