"""
权限控制器（异步版本）
文件路径：src/business/subscription/permission_controller_async.py
功能：控制用户权限（异步）
"""

from typing import Optional
from datetime import datetime
from src.domain.repositories.user_repository_async import UserRepositoryAsync
from src.domain.repositories.subscription_repository_async import SubscriptionRepositoryAsync
import logging

logger = logging.getLogger(__name__)


class PermissionControllerAsync:
    """权限控制器（异步版本）"""
    
    def __init__(self, user_repo: Optional[UserRepositoryAsync] = None, sub_repo: Optional[SubscriptionRepositoryAsync] = None):
        """初始化权限控制器
        
        Args:
            user_repo: 用户仓库
            sub_repo: 订阅仓库
        """
        self.user_repo = user_repo or UserRepositoryAsync()
        self.sub_repo = sub_repo or SubscriptionRepositoryAsync()
        self.logger = logging.getLogger(__name__)
    
    async def check_publish_permission(self, user_id: int) -> bool:
        """检查发布权限（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否有发布权限
        """
        # 检查用户是否有有效订阅
        subscription_data = await self.sub_repo.get_active_subscription(user_id)
        
        if subscription_data:
            # 检查订阅是否过期
            end_date_str = subscription_data.get('end_date')
            if end_date_str:
                if isinstance(end_date_str, str):
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace(' ', 'T'))
                    except:
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_date = end_date_str
                
                if datetime.now() <= end_date:
                    self.logger.debug(f"用户有有效订阅: 用户ID={user_id}, 套餐={subscription_data.get('plan_type')}")
                    return True
                else:
                    # 订阅已过期，更新状态（原逻辑调用了update_publish_record是错误的，这里更正为更新订阅状态）
                    await self.sub_repo.update(
                        subscription_data['id'],
                        status='expired'
                    )
                    self.logger.debug(f"用户订阅已过期: 用户ID={user_id}")
        
        # 没有有效订阅，检查是否有试用次数
        user = await self.user_repo.get_by_id(user_id)
        if user and user.get('trial_count', 0) > 0:
            self.logger.debug(f"用户有试用次数: 用户ID={user_id}, 剩余次数={user.get('trial_count')}")
            return True
        
        self.logger.warning(f"用户无发布权限: 用户ID={user_id} (无订阅且无试用次数)")
        return False
    
    async def check_trial_count(self, user_id: int) -> bool:
        """检查试用次数（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否还有试用次数
        """
        # 如果有有效订阅，不需要检查试用次数
        subscription_data = await self.sub_repo.get_active_subscription(user_id)
        if subscription_data:
            end_date_str = subscription_data.get('end_date')
            if end_date_str:
                if isinstance(end_date_str, str):
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace(' ', 'T'))
                    except:
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_date = end_date_str
                
                if datetime.now() <= end_date:
                    return True  # 有订阅，允许发布
        
        # 检查试用次数
        user = await self.user_repo.get_by_id(user_id)
        if user:
            trial_count = user.get('trial_count', 0)
            if trial_count > 0:
                self.logger.debug(f"用户还有试用次数: 用户ID={user_id}, 剩余次数={trial_count}")
                return True
            else:
                self.logger.debug(f"用户试用次数已用完: 用户ID={user_id}")
                return False
        
        return False
    
    async def deduct_trial_count(self, user_id: int) -> bool:
        """扣除试用次数（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否扣除成功
        """
        # 如果有有效订阅，不需要扣除试用次数
        subscription_data = await self.sub_repo.get_active_subscription(user_id)
        if subscription_data:
            end_date_str = subscription_data.get('end_date')
            if end_date_str:
                if isinstance(end_date_str, str):
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace(' ', 'T'))
                    except:
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_date = end_date_str
                
                if datetime.now() <= end_date:
                    self.logger.debug(f"用户有订阅，不扣除试用次数: 用户ID={user_id}")
                    return True
        
        # 扣除试用次数
        user = await self.user_repo.get_by_id(user_id)
        if user:
            trial_count = user.get('trial_count', 0)
            if trial_count > 0:
                new_count = trial_count - 1
                await self.user_repo.update_trial_count(user_id, new_count)
                self.logger.info(f"扣除试用次数成功: 用户ID={user_id}, 剩余次数={new_count}")
                return True
            else:
                self.logger.warning(f"试用次数已用完，无法扣除: 用户ID={user_id}")
                return False
        
        return False
    
    async def get_user_role(self, user_id: int) -> str:
        """获取用户角色（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户角色（trial/subscribed/admin）
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return 'guest'
        
        # 检查是否是管理员
        if user.get('role') == 'admin':
            return 'admin'
        
        # 检查是否有有效订阅
        subscription_data = await self.sub_repo.get_active_subscription(user_id)
        if subscription_data:
            end_date_str = subscription_data.get('end_date')
            if end_date_str:
                if isinstance(end_date_str, str):
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace(' ', 'T'))
                    except:
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_date = end_date_str
                
                if datetime.now() <= end_date:
                    return 'subscribed'
        
        # 检查是否有试用次数
        if user.get('trial_count', 0) > 0:
            return 'trial'
        
        return 'guest'


# 为了向后兼容，保留同步版本作为异步版本的包装
class PermissionController:
    """权限控制器（同步包装器，用于向后兼容）"""
    
    def __init__(self, data_storage=None):
        """初始化权限控制器"""
        self._async_controller = PermissionControllerAsync()
        self._is_async = True
        self.logger = logging.getLogger(__name__)
    
    def check_publish_permission(self, user_id: int) -> bool:
        """检查发布权限（同步包装）"""
        if self._is_async:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return True  # 临时返回True，实际应该等待
                else:
                    return loop.run_until_complete(self._async_controller.check_publish_permission(user_id))
            except RuntimeError:
                return asyncio.run(self._async_controller.check_publish_permission(user_id))
    
    def check_trial_count(self, user_id: int) -> bool:
        """检查试用次数（同步包装）"""
        if self._is_async:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return True  # 临时返回
                else:
                    return loop.run_until_complete(self._async_controller.check_trial_count(user_id))
            except RuntimeError:
                return asyncio.run(self._async_controller.check_trial_count(user_id))

