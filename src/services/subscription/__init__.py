"""
订阅付费业务逻辑模块
"""

# 异步版本 (新架构)
from .permission_controller_async import PermissionControllerAsync
from .subscription_manager_async import SubscriptionManagerAsync
from .payment_handler_async import PaymentHandlerAsync

# 兼容性别名
PermissionController = PermissionControllerAsync
SubscriptionManager = SubscriptionManagerAsync
PaymentHandler = PaymentHandlerAsync

__all__ = [
    'PermissionControllerAsync',
    'SubscriptionManagerAsync',
    'PaymentHandlerAsync',
    'PermissionController',
    'SubscriptionManager',
    'PaymentHandler'
]
