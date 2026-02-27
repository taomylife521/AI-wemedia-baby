"""
账号验证器模块
文件路径：src/business/account/account_verifier.py
功能：批量验证账号Cookie有效性，支持异步HTTP请求验证

重要更新 (2026-01-21):
    已从 requests 同步库迁移到 aiohttp 异步库，
    与 qasync 统一事件循环架构保持一致。
"""

from typing import Dict, List, Optional, Any, Callable
import logging
import asyncio
import aiohttp
import inspect
import random

logger = logging.getLogger(__name__)


class AccountVerifier:
    """账号验证器 - 支持异步批量高效验证"""
    
    def __init__(self, account_manager, max_workers: int = 5):
        """
        初始化账号验证器
        
        Args:
            account_manager: 账号管理器实例
            max_workers: 最大并发数，默认5（避免被限流）
        """
        self.account_manager = account_manager
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
    
    async def close(self):
        """关闭 aiohttp 会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def verify_account_by_http(
        self, 
        account_id: int, 
        account_name: str,
        platform: str,
        cookies: Dict[str, str],
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        通过插件系统验证账号Cookie有效性（异步版本）
        
        Args:
            account_id: 账号ID
            account_name: 账号名称
            platform: 平台ID
            cookies: Cookie字典
            
        Returns:
            验证结果
        """
        result = {
            'account_id': account_id,
            'account_name': account_name,
            'platform': platform,
            'is_valid': False,
            'is_logged_in': False,
            'username': None,
            'error': None,
            'method': 'http_plugin',
            'status_code': None
        }
        
        try:
            # 1. 获取对应的登录插件
            from src.plugins.core.plugin_manager import PluginManager
            plugin = PluginManager.get_login_plugin(platform)
            
            if not plugin:
                result['error'] = f'不支持的平台或插件缺失: {platform}'
                return result
            
            # 2. 准备验证上下文
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.plugins.core.interfaces.login_plugin import AccountVerificationContext
            
            context = AccountVerificationContext(
                account_id=account_id,
                account_name=account_name,
                platform=platform,
                cookies=cookies,
                user_agent=user_agent,
                http_session=await self._get_session(),
                service_locator=ServiceLocator()
            )
            
            # 3. 调用插件的统一验证接口，并加上超时保护（15秒硬超时）
            try:
                login_result = await asyncio.wait_for(
                    plugin.verify_account_status(context),
                    timeout=15
                )
            except asyncio.TimeoutError:
                result['error'] = '插件验证超时（15秒无响应）'
                result['is_valid'] = False
                self.logger.warning(f"账号 {account_name} (ID: {account_id}, 平台: {platform}) 插件验证超时")
                return result
            
            # 4. 转换插件结果为验证结果
            result['is_valid'] = login_result.is_valid
            result['is_logged_in'] = login_result.success
            result['username'] = login_result.nickname
            result['error'] = login_result.error_message
            
            if login_result.success:
                self.logger.info(f"账号 {account_name} (ID: {account_id}, 平台: {platform}) 通过插件验证有效")
            else:
                self.logger.warning(f"账号 {account_name} (ID: {account_id}, 平台: {platform}) 插件验证失效: {login_result.error_message}")
                
        except Exception as e:
            result['error'] = f'插件验证异常: {str(e)}'
            result['is_valid'] = False
            self.logger.error(f"验证账号 {account_name} (ID: {account_id}) 插件执行异常: {e}", exc_info=True)
        
        return result
    
    async def verify_accounts_batch(
        self, 
        accounts: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, int, Dict[str, Any]], None]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        批量验证账号（异步并发）
        
        Args:
            accounts: 账号信息列表 (Dict)
            progress_callback: 进度回调函数 (current, total, account_id, result)
            
        Returns:
            验证结果字典 {account_id: result}
        """
        results = {}
        total = len(accounts)
        completed = [0]  # 使用列表以便在闭包中修改
        
        # 按平台分组账号
        from collections import defaultdict
        platform_groups = defaultdict(list)
        for account in accounts:
            platform = account.get('platform', 'unknown')
            platform_groups[platform].append(account)
        
        self.logger.info(f"开始按平台分组批量验证 {total} 个账号，共 {len(platform_groups)} 个平台")
        for p, accs in platform_groups.items():
            self.logger.info(f"  平台 {p}: {len(accs)} 个账号")
        
        # 每个平台独立的信号量（限制同一平台最多 3 个并发，避免被限流）
        per_platform_concurrency = min(3, self.max_workers)
        
        async def verify_single_account(account: Dict[str, Any], platform_sem: asyncio.Semaphore) -> Dict[str, Any]:
            """验证单个账号（受平台级信号量控制）"""
            async with platform_sem:
                # 添加短随机延迟，避免并发过高
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                account_id = account.get('id')
                # 获取账号名称（文件夹名），数据库字段通常是 platform_username
                account_name = account.get('platform_username') or account.get('account_name', '')
                
                result = {
                    'account_id': account_id if account_id else -1,
                    'account_name': account_name,
                    'platform': account.get('platform', ''),
                    'is_valid': False,
                    'is_logged_in': False,
                    'username': None,
                    'error': None,
                    'method': 'check'
                }
                
                if not account_id:
                    self.logger.warning(f"账号信息缺失ID: {account}")
                    result['error'] = '账号ID缺失'
                else:
                    # 加载Cookie
                    try:
                        cookies = self.account_manager.cookie_manager.load_cookie(
                            account_name,
                            account.get('platform', ''),
                            account.get('profile_folder_name')  # 传递 UUID 目录名
                        )
                    except Exception as e:
                        self.logger.error(f"加载账号 {account_id} Cookie失败: {e}")
                        cookies = None
                    
                    if not cookies:
                        result['error'] = 'Cookie文件不存在'
                        result['method'] = 'file_check'
                    else:
                        # 转换为字典格式
                        if isinstance(cookies, dict):
                            cookie_dict = cookies
                        elif isinstance(cookies, list):
                            cookie_dict = {
                                c.get('name'): c.get('value') 
                                for c in cookies 
                                if isinstance(c, dict) and c.get('name') and c.get('value')
                            }
                        else:
                            cookie_dict = {}
                        
                        if not cookie_dict:
                            result['error'] = 'Cookie格式错误'
                            result['method'] = 'file_check'
                        else:
                            # 执行HTTP验证
                            try:
                                result = await self.verify_account_by_http(
                                    account_id,
                                    account.get('account_name', ''),
                                    account.get('platform', ''),
                                    cookie_dict,
                                    user_agent=account.get('user_agent')
                                )
                            except Exception as e:
                                result['error'] = f'验证异常: {str(e)}'
                                result['is_valid'] = False
                                result['is_logged_in'] = False
                                result['method'] = 'http'
                                self.logger.error(f"验证账号 {account_id} 异常: {e}", exc_info=True)
                
                # 统一更新数据库状态（使用 Repository 模式）
                if account_id and account_id != -1:
                    try:
                        from src.domain.repositories.account_repository_async import AccountRepositoryAsync
                        account_repo = AccountRepositoryAsync()
                        status = 'online' if result.get('is_logged_in') else 'offline'
                        await account_repo.update_status(account_id, status)
                        
                        # 如果有用户名且有效，也更新
                        username = result.get('username')
                        if status == 'online' and username:
                            await account_repo.update_platform_username(account_id, username)
                    except Exception as db_e:
                        self.logger.error(f"后台更新账号 {account_id} 状态失败: {db_e}")

                completed[0] += 1
                if progress_callback:
                    progress_callback(completed[0], total, account_id, result)
                return result
        
        # 为每个平台创建独立的信号量，并行调度所有平台的任务
        all_tasks = []
        for platform, group_accounts in platform_groups.items():
            platform_sem = asyncio.Semaphore(per_platform_concurrency)
            for account in group_accounts:
                all_tasks.append(verify_single_account(account, platform_sem))
        
        # 并发执行所有验证任务
        task_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # 整理结果
        all_accounts_flat = []
        for group_accounts in platform_groups.values():
            all_accounts_flat.extend(group_accounts)
        
        for i, account in enumerate(all_accounts_flat):
            account_id = account.get('id')
            result = task_results[i]
            if isinstance(result, Exception):
                results[account_id] = {
                    'account_id': account_id,
                    'is_valid': False,
                    'is_logged_in': False,
                    'error': f'验证异常: {str(result)}',
                    'method': 'http'
                }
            else:
                if result:
                    results[account_id] = result
        
        # 关闭会话
        await self.close()
        
        self.logger.info(f"批量验证完成，共验证 {len(results)} 个账号")
        return results
