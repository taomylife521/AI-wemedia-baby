"""
订阅管理器（异步版本）
文件路径：src/business/subscription/subscription_manager_async.py
功能：管理用户订阅（异步）
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.infrastructure.common.event.event_bus import EventBus
from src.infrastructure.common.di.service_locator import ServiceLocator
from src.services.subscription.subscription_service import SubscriptionService
from src.utils.date_utils import get_current_datetime_str
import logging

logger = logging.getLogger(__name__)


class SubscriptionManagerAsync:
    """订阅管理器（异步版本）"""
    
    def __init__(
        self,
        user_id: int,
        event_bus: Optional[EventBus] = None
    ):
        """初始化订阅管理器
        
        Args:
            user_id: 用户ID
            event_bus: 事件总线（可选，默认从ServiceLocator获取）
        """
        self.user_id = user_id
        self.service_locator = ServiceLocator()
        self.event_bus = event_bus or self.service_locator.get(EventBus)
        self.subscription_service = SubscriptionService()
        self.logger = logging.getLogger(__name__)
    
    def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """获取订阅套餐列表
        
        Returns:
            套餐列表
        """
        return [
            {
                'plan_type': 'trial',
                'name': '试用版',
                'price': 0,
                'duration_days': 7,
                'features': ['5次发布', '单账号'],
                'description': '免费试用7天，体验基本功能'
            },
            {
                'plan_type': 'monthly',
                'name': '月付版',
                'price': 29.9,
                'duration_days': 30,
                'features': ['无限发布', '3个账号', '批量发布'],
                'description': '适合个人创作者，月付更灵活'
            },
            {
                'plan_type': 'yearly',
                'name': '年付版',
                'price': 299,
                'duration_days': 365,
                'features': ['无限发布', '10个账号', '批量发布', '优先支持'],
                'description': '最划算，适合专业创作者'
            }
        ]
    
    async def get_user_subscription(self) -> Optional[Dict[str, Any]]:
        """获取用户订阅信息（异步）
        
        Returns:
            订阅信息，如果没有返回None
        """
        subscription = await self.subscription_service.get_user_subscription(self.user_id)
        if subscription:
            # 检查订阅是否过期
            if subscription.is_expired():
                # 自动更新为过期状态（如果需要）
                self.logger.info(f"用户订阅已过期: 用户ID={self.user_id}")
            return subscription.to_dict()
        return None
    
    async def create_subscription(
        self,
        plan_type: str,
        order_id: str,
        payment_method: str
    ) -> int:
        """创建订阅（异步）
        
        Args:
            plan_type: 套餐类型（trial/monthly/yearly）
            order_id: 订单ID
            payment_method: 支付方式
        
        Returns:
            新创建的订阅ID
        """
        plans = self.get_subscription_plans()
        plan = next((p for p in plans if p['plan_type'] == plan_type), None)
        
        if not plan:
            raise ValueError(f"无效的套餐类型: {plan_type}")
        
        subscription = await self.subscription_service.create_subscription(
            user_id=self.user_id,
            plan_type=plan_type,
            price=plan['price'],
            duration_days=plan['duration_days'],
            order_id=order_id
        )
        
        self.logger.info(f"创建订阅成功: 用户ID={self.user_id}, 套餐={plan_type}, ID={subscription.subscription_id}")
        return subscription.subscription_id
    
    async def check_subscription_active(self) -> bool:
        """检查订阅是否激活（异步）
        
        Returns:
            如果订阅激活返回True，否则返回False
        """
        return await self.subscription_service.check_subscription_active(self.user_id)

