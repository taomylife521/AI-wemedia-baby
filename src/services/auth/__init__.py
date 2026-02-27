"""
用户认证业务模块
"""

# 异步版本 (新架构)
from .user_auth_async import UserAuthAsync

# 兼容性别名
UserAuth = UserAuthAsync

__all__ = ['UserAuthAsync', 'UserAuth']
