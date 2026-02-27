"""
用户认证模块（异步版本）
文件路径：src/services/auth/user_auth_async.py
功能：处理用户登录、注册、密码重置等（异步）
已迁移：使用 UserRepositoryAsync 替代 AsyncDataStorage
"""

from typing import Optional, Dict, Any
import logging

from src.domain.repositories.user_repository_async import UserRepositoryAsync

logger = logging.getLogger(__name__)


class UserAuthAsync:
    """用户认证服务（异步版本）
    
    使用 UserRepositoryAsync 进行数据访问，已完成从 AsyncDataStorage 的迁移。
    """
    
    def __init__(
        self,
        user_repository: Optional[UserRepositoryAsync] = None
    ):
        """初始化用户认证服务
        
        Args:
            user_repository: 用户仓储（可选，默认自动创建）
        """
        # 使用 UserRepositoryAsync 替代 AsyncDataStorage
        self.user_repository = user_repository or UserRepositoryAsync()
        self.logger = logging.getLogger(__name__)
    
    async def register(
        self,
        username: str,
        password: str,
        email: str
    ) -> int:
        """用户注册（异步）
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱
        
        Returns:
            新创建的用户ID
        
        Raises:
            ValueError: 用户名已存在
        """
        # 通过 UserRepositoryAsync 创建用户（内部已处理密码哈希和重复检查）
        return await self.user_repository.create_user(
            username=username,
            password=password,
            email=email
        )
    
    async def login(
        self,
        username: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """用户登录（异步）
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            用户信息字典，如果登录失败返回None
        """
        # 通过 UserRepositoryAsync 验证密码
        if await self.user_repository.verify_password(username, password):
            # 获取用户信息
            user = await self.user_repository.get_by_username(username)
            if user:
                # 更新最后登录时间
                await self.user_repository.update_last_login(user['id'])
                return user
        return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户信息字典，如果不存在返回None
        """
        # 通过 UserRepositoryAsync 获取用户
        return await self.user_repository.get_by_id(user_id)
    
    async def reset(self, username: str, email: str, new_password: str) -> bool:
        """重置用户密码（异步）
        
        Args:
            username: 用户名
            email: 注册邮箱
            new_password: 新密码
            
        Returns:
            是否成功
        """
        # 通过 UserRepositoryAsync 获取用户并验证邮箱
        user = await self.user_repository.get_by_username(username)
        if not user or user.get('email') != email:
            return False
            
        # 通过 UserRepositoryAsync 更新密码
        return await self.user_repository.update_password(username, new_password)
