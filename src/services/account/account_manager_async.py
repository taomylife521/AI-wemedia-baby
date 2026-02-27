"""
账号管理模块（异步版本）
文件路径：src/services/account/account_manager_async.py
功能：管理平台账号的添加、删除、切换、状态验证等（异步版本）
已迁移：使用 AccountRepositoryAsync 替代 AsyncDataStorage
"""

from typing import List, Optional, Dict, Any
import logging
import os
import asyncio

from src.infrastructure.common.event.event_bus import EventBus
from src.infrastructure.common.event.events import AccountAddedEvent, AccountRemovedEvent
from src.infrastructure.common.di.service_locator import ServiceLocator
from src.services.account.cookie_manager import CookieManager
from src.domain.repositories.account_repository_async import AccountRepositoryAsync
from src.utils.file_utils import ensure_directory_exists
from src.utils.date_utils import get_current_datetime_str
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)


class AccountManagerAsync:
    """账号管理器（异步版本）- 负责平台账号的管理
    
    使用 Repository 模式分离数据访问逻辑，所有操作都是异步的。
    """
    
    def __init__(
        self,
        user_id: int,
        event_bus: Optional[EventBus] = None
    ):
        """初始化账号管理器
        
        Args:
            user_id: 用户ID
            event_bus: 事件总线（可选，默认从ServiceLocator获取）
        """
        self.user_id = user_id
        self.service_locator = ServiceLocator()
        self.event_bus = event_bus or self.service_locator.get(EventBus)
        
        # 使用 AccountRepositoryAsync 进行数据访问（已完成从 AsyncDataStorage 迁移）
        self.account_repository = AccountRepositoryAsync()
        self.cookie_manager = CookieManager(user_id)
        self.current_account: Optional[Dict[str, Any]] = None
        self.verifier = None  # 延迟初始化，避免循环导入
        self.logger = logging.getLogger(__name__)
    
    async def add_account(
        self,
        platform: str,
        platform_username: str,
        browser: Optional[Any] = None,  # QWebEngineBrowser
        cookie_data: Optional[Dict[str, Any]] = None,
        profile_folder_name: Optional[str] = None
    ) -> int:
        """添加平台账号（异步）
        
        Args:
            platform: 平台名称（douyin/kuaishou/xiaohongshu）
            platform_username: 平台账号昵称（必需）
            browser: 浏览器实例（可选，用于提取Cookie）
            cookie_data: Cookie数据（可选，如果提供则直接使用）
            profile_folder_name: 账号数据文件夹名称(UUID/TempName)，如有则优先使用
        
        Returns:
            新创建的账号ID
        
        Raises:
            ValueError: 账号昵称已存在或参数无效
        """
        # 验证账号昵称唯一性（使用 Repository）
        if await self.account_repository.exists(self.user_id, platform_username, platform):
            raise ValueError(f"账号昵称已存在: {platform_username}")
        
        # 创建账号文件夹（统一使用账号中心结构）
        # data/{platform}/{profile_folder_name or account_name}/workspace
        # 这里的 profile_folder_name 通常是由 PlaywrightService 生成的临时目录名(如 temp_new_xxx)
        # 我们直接将其作为永久目录，不再重命名
        account_root = PathManager.get_platform_account_dir(platform, platform_username, profile_folder_name)
        workspace_dir = account_root / "workspace"
        
        # 确保工作区及子目录存在
        ensure_directory_exists(str(workspace_dir))
        ensure_directory_exists(str(workspace_dir / "media"))
        ensure_directory_exists(str(workspace_dir / "logs"))
        ensure_directory_exists(str(workspace_dir / "temp"))
        ensure_directory_exists(str(workspace_dir / "media" / "pending")) # 待发布
        ensure_directory_exists(str(workspace_dir / "media" / "published")) # 已发布
        
        self.logger.info(f"创建账号工作目录: {workspace_dir} (Profile: {profile_folder_name or 'Legacy'})")
        
        # 处理Cookie
        cookie_path = ""
        if cookie_data:
            # 如果提供了Cookie数据，直接保存
            cookie_path = self.cookie_manager.save_cookie(
                platform_username,
                platform,
                cookie_data,
                profile_folder_name
            )
            self.logger.info(f"保存Cookie成功: {cookie_path}")
        elif browser:
            # 如果提供了浏览器实例，提取Cookie
            try:
                cookies = browser.extract_cookies_dict()
                if cookies:
                    cookie_path = self.cookie_manager.save_cookie(
                        platform_username,
                        platform,
                        cookies,
                        profile_folder_name
                    )
                    self.logger.info(f"提取并保存Cookie成功: {cookie_path}")
            except Exception as e:
                self.logger.warning(f"提取Cookie失败: {e}")
        
        # 创建账号记录（通过 Repository）
        account_id = await self.account_repository.create(
            user_id=self.user_id,
            platform=platform,
            platform_username=platform_username,
            cookie_path=cookie_path,
            profile_folder_name=profile_folder_name
        )
        
        # 如果有 Cookie，更新账号状态为在线
        if cookie_path:
            await self.account_repository.update_status(
                account_id=account_id,
                login_status='online',
                last_login_at=get_current_datetime_str()
            )
        
        # 发布事件（异步）
        if self.event_bus:
            event = AccountAddedEvent(
                user_id=self.user_id,
                platform_username=platform_username,
                platform=platform
            )
            await self.event_bus.publish(event)
        
        self.logger.info(
            f"添加账号成功: {platform_username}, 平台: {platform}, ID: {account_id}"
        )
        
        return account_id
    
    async def get_accounts(
        self,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取账号列表（异步）
        
        Args:
            platform: 平台名称（可选，如果指定则只返回该平台的账号）
        
        Returns:
            账号列表
        """
        # 使用 Repository 获取账号列表
        return await self.account_repository.find_all(
            user_id=self.user_id,
            platform=platform
        )
    
    async def get_account_by_id(
        self,
        account_id: int
    ) -> Optional[Dict[str, Any]]:
        """根据账号ID获取账号信息（异步）
        
        Args:
            account_id: 账号ID
        
        Returns:
            账号信息字典，如果不存在返回None
        """
        # 使用 Repository 查找账号
        return await self.account_repository.find_by_id(
            user_id=self.user_id,
            account_id=account_id
        )
    
    async def switch_account(self, account_id: int) -> bool:
        """切换当前账号（异步）
        
        Args:
            account_id: 账号ID
        
        Returns:
            如果切换成功返回True，否则返回False
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            self.logger.warning(f"账号不存在: ID {account_id}")
            return False
        
        self.current_account = account
        self.logger.info(
            f"切换账号成功: {account['platform_username']}, 平台: {account['platform']}"
        )
        return True
    
    def get_current_account(self) -> Optional[Dict[str, Any]]:
        """获取当前账号
        
        Returns:
            当前账号信息，如果未设置返回None
        """
        return self.current_account
    
    async def verify_account_status(
        self,
        account_id: int,
        browser: Optional[Any] = None
    ) -> bool:
        """验证账号状态（检查Cookie是否有效）（异步）
        
        Args:
            account_id: 账号ID
            browser: 浏览器实例（可选，用于验证）
        
        Returns:
            如果账号有效返回True，否则返回False
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            return False
        
        # 检查Cookie文件是否存在
        # 优先使用数据库中存储的路径（最准确）
        cookie_path = account.get('cookie_path')
        is_valid = False
        
        if cookie_path and os.path.exists(cookie_path):
             is_valid = True
        # 如果数据库没有路径（旧数据），或者路径不存在（可能移动了），尝试根据规则重新查找
        elif self.cookie_manager.cookie_exists(
            account['platform_username'],
            account['platform']
        ):
             is_valid = True
             
        if not is_valid:
            self.logger.warning(
                f"Cookie文件不存在: {account['platform_username']}, "
                f"平台: {account['platform']}, 记录路径: {cookie_path}"
            )
            await self.account_repository.update_status(
                account_id=account_id,
                login_status='offline'
            )
            return False
        
        # 如果提供了浏览器，可以进一步验证Cookie有效性
        # 这里简化处理，只检查文件是否存在
        await self.account_repository.update_status(
            account_id=account_id,
            login_status='online'
        )
        return True
    
    async def verify_all_accounts_status(self) -> None:
        """验证所有账号的状态（异步）
        
        使用 AccountVerifier 通过 HTTP 请求批量验证账号状态。
        """
        try:
            # 延迟导入并初始化验证器
            if not self.verifier:
                from .account_verifier import AccountVerifier
                self.verifier = AccountVerifier(self)
                
            accounts = await self.get_accounts()
            if not accounts:
                return

            self.logger.info("开始执行 HTTP 批量验证...")
            
            # 使用验证器进行批量验证
            # 验证结果会自动通过 data_storage 更新到数据库
            await self.verifier.verify_accounts_batch(accounts)
            
            self.logger.info(f"已完成所有账号的 HTTP 状态验证（共 {len(accounts)} 个）")
            
        except Exception as e:
            self.logger.error(f"验证所有账号状态失败: {e}", exc_info=True)

    
    async def delete_account(
        self,
        account_id: int,
        delete_cookie: bool = False,
        delete_records: bool = False
    ) -> bool:
        """删除账号(异步)
        
        Args:
            account_id: 账号ID
            delete_cookie: 是否同时删除Cookie文件和浏览器数据
            delete_records: 是否同时删除发布记录
        
        Returns:
            如果删除成功返回True,否则返回False
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            self.logger.warning(f"账号不存在: ID {account_id}")
            return False
        
        account_username = account['platform_username']
        platform = account['platform']
        
        # 删除Cookie文件和浏览器数据
        if delete_cookie:
            # 1. 删除加密的Cookie备份文件
            self.cookie_manager.delete_cookie(
                account_username, 
                platform,
                account.get('profile_folder_name')
            )
            
            # 2. 删除整个账号数据目录(包含browser、workspace等所有数据)
            try:
                import shutil
                from pathlib import Path
                
                # 构建账号数据目录路径
                # 路径格式: AppData/data/{platform}/{profile_folder_name or platform_username}
                profile_folder = account.get('profile_folder_name')
                account_dir = PathManager.get_platform_account_dir(platform, account_username, profile_folder)
                
                if account_dir.exists():
                    self.logger.info(f"删除账号数据目录: {account_dir}")
                    shutil.rmtree(account_dir, ignore_errors=True)
                    self.logger.info(f"账号数据目录已删除: {account_dir}")
                else:
                    self.logger.info(f"账号数据目录不存在,无需删除: {account_dir}")
                    
            except Exception as e:
                self.logger.error(f"删除账号数据目录失败: {e}", exc_info=True)
        
        # 删除发布记录(如果需要)
        if delete_records:
            # 注意:这里需要实现删除发布记录的功能
            # 暂时只记录日志
            self.logger.info(f"删除发布记录: 账号={account_username}")
        
        # 删除数据库记录(使用 Repository)
        await self.account_repository.delete(account_id)
        
        # 发布事件(异步)
        if self.event_bus:
            event = AccountRemovedEvent(
                user_id=self.user_id,
                platform_username=account_username,
                platform=platform
            )
            await self.event_bus.publish(event)
        
        # 如果删除的是当前账号,清空当前账号
        if self.current_account and self.current_account['id'] == account_id:
            self.current_account = None
        
        self.logger.info(f"删除账号成功: {account_username}, 平台: {platform}")
        return True
    
    async def update_platform_username(
        self,
        account_id: int,
        platform_username: str
    ) -> bool:
        """更新平台用户名（异步）
        
        Args:
            account_id: 账号ID
            platform_username: 平台用户名
            
        Returns:
            如果更新成功返回True，否则返回False
        """
        try:
            # 使用 Repository 更新平台用户名
            success = await self.account_repository.update_platform_username(
                account_id=account_id,
                platform_username=platform_username
            )
            if success:
                self.logger.info(
                    f"更新平台用户名成功: 账号ID={account_id}, 用户名={platform_username}"
                )
                
                # 发布更新事件
                if self.event_bus:
                    from src.infrastructure.common.event.events import AccountUpdatedEvent
                    event = AccountUpdatedEvent(
                        user_id=self.user_id,
                        account_id=account_id,
                        update_type='nickname'
                    )
                    await self.event_bus.publish(event)
                    
            return success
        except Exception as e:
            self.logger.error(f"更新平台用户名失败: {e}")
            return False
    
    async def clear_cookie(self, account_id: int) -> bool:
        """清理Cookie（删除Cookie文件，需要重新登录）（异步）
        
        Args:
            account_id: 账号ID
        
        Returns:
            如果清理成功返回True，否则返回False
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            return False
        
        # 删除Cookie文件
        success = self.cookie_manager.delete_cookie(
            account['platform_username'],
            account['platform'],
            account.get('profile_folder_name')
        )
        
        if success:
            # 更新账号状态
            await self.account_repository.update_status(
                account_id=account_id,
                login_status='offline'
            )
            self.logger.info(
                f"清理Cookie成功: {account['platform_username']}, "
                f"平台: {account['platform']}"
            )
        
        return success
    
    async def update_cookie(
        self,
        account_id: int,
        cookie_data: Dict[str, Any]
    ) -> bool:
        """更新账号Cookie（异步）
        
        Args:
            account_id: 账号ID
            cookie_data: Cookie数据
        
        Returns:
            如果更新成功返回True，否则返回False
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            return False
        
        try:
            cookie_path = self.cookie_manager.save_cookie(
                account['platform_username'],
                account['platform'],
                cookie_data,
                account.get('profile_folder_name')
            )
            
            # 更新账号状态
            await self.account_repository.update_status(
                account_id=account_id,
                login_status='online',
                last_login_at=get_current_datetime_str()
            )
            
            # 发布更新事件
            if self.event_bus:
                from src.infrastructure.common.event.events import AccountUpdatedEvent
                event = AccountUpdatedEvent(
                    user_id=self.user_id,
                    account_id=account_id,
                    update_type='status' # cookie 更新意味着状态更新为 online
                )
                await self.event_bus.publish(event)

            
            self.logger.info(f"更新Cookie成功: {cookie_path}")
            return True
        except Exception as e:
            self.logger.error(f"更新Cookie失败: {e}")
            return False
    
    async def load_account_cookie(
        self,
        account_id: int
    ) -> Optional[Dict[str, Any]]:
        """加载账号Cookie（异步）
        
        Args:
            account_id: 账号ID
        
        Returns:
            Cookie数据，如果不存在返回None
        """
        account = await self.get_account_by_id(account_id)
        if not account:
            return None
        
        return self.cookie_manager.load_cookie(
            account['platform_username'],
            account['platform'],
            account.get('profile_folder_name')
        )
