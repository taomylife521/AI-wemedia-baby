# -*- coding: utf-8 -*-
"""
账号验证服务
文件路径：src/ui/pages/account/services/account_validator.py
功能：负责账号状态的验证，包括Cookie有效性检查、指纹预加载等
"""

import logging
import inspect
import asyncio
from typing import List, Dict, Any, Callable, Optional
from PySide6.QtCore import QObject, Signal

from src.services.account.account_verifier import AccountVerifier
from src.infrastructure.browser.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

class AccountValidatorService(QObject):
    """账号验证服务"""
    
    # 信号定义
    started = Signal(int)  # total
    progress = Signal(int, int, object)  # current, total, result_data
    finished = Signal(object)  # results
    error = Signal(str)  # error_message

    def __init__(self, account_manager, parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self._current_task = None
        self._verifier = None

    def verify_accounts(self, accounts: List[Dict], silent: bool = False):
        """开始验证账号列表
        
        Args:
            accounts: 账号列表
            silent: 是否静默模式（不触发 started 信号，避免弹窗）
        """
        if not accounts:
            if not silent:
                self.error.emit("没有账号需要验证")
            else:
                logger.warning("verify_accounts: 没有账号需要验证 (silent)")
            return

        total = len(accounts)
        
        if not silent:
            self.started.emit(total)
        
        self._preload_fingerprints(accounts)
        
        async def run_verify():
            try:
                results = await self._run_verification_task(accounts)
                self.finished.emit(results)
            except asyncio.CancelledError:
                logger.warning("验证任务被取消")
                self.error.emit("验证已取消")
            except Exception as e:
                logger.error(f"验证任务出错: {e}", exc_info=True)
                self.error.emit(str(e))
            finally:
                self._current_task = None

        self._current_task = asyncio.create_task(run_verify())

    def start_verify_all(self):
        """开始验证所有账号"""
        self._start_fetching_and_verifying(self._fetch_all_accounts, silent=False)

    def start_verify_by_ids(self, account_ids: List[int], silent: bool = False):
        """开始验证指定ID的账号"""
        self._start_fetching_and_verifying(lambda: self._fetch_accounts_by_ids(account_ids), silent=silent)

    def _start_fetching_and_verifying(self, fetch_coro_func: Callable, silent: bool = False):
        """通用启动方法：先获取数据，再验证"""
        async def fetch_and_verify_wrapper():
            try:
                accounts = await fetch_coro_func()
                if not accounts:
                    self.finished.emit({})
                    return
                
                total = len(accounts)
                if not silent:
                    self.started.emit(total)
                
                self._preload_fingerprints(accounts)
                
                results = await self._run_verification_task(accounts)
                self.finished.emit(results)
            except asyncio.CancelledError:
                logger.warning("验证任务被取消")
                self.error.emit("验证已取消")
            except Exception as e:
                logger.error(f"获联或验证任务出错: {e}", exc_info=True)
                self.error.emit(str(e))
            finally:
                self._current_task = None

        self._current_task = asyncio.create_task(fetch_and_verify_wrapper())

    async def _fetch_all_accounts(self) -> List[Dict]:
        """获取所有账号"""
        if hasattr(self.account_manager, 'get_accounts'):
            res = self.account_manager.get_accounts()
            if inspect.isawaitable(res):
                return await res
            elif inspect.iscoroutinefunction(self.account_manager.get_accounts):
                return await self.account_manager.get_accounts()
            else:
                return res
        return []

    async def _fetch_accounts_by_ids(self, account_ids: List[int]) -> List[Dict]:
        """获取指定账号"""
        accounts = []
        for aid in account_ids:
            if hasattr(self.account_manager, 'get_account_by_id'):
                res = self.account_manager.get_account_by_id(aid)
                if inspect.isawaitable(res):
                    acc = await res
                elif inspect.iscoroutinefunction(self.account_manager.get_account_by_id):
                    acc = await self.account_manager.get_account_by_id(aid)
                else:
                    acc = res
                
                if acc:
                    accounts.append(acc)
        return accounts

    def _preload_fingerprints(self, accounts: List[Dict]):
        """预加载指纹 UA"""
        try:
            for acc in accounts:
                acc_name = acc.get('account_name')
                platform = acc.get('platform')
                platform_username = acc.get('platform_username')
                
                username_for_profile = platform_username if platform_username else acc_name
                
                if username_for_profile:
                    pm = ProfileManager(
                        account_id=acc.get('id'), 
                        platform=platform, 
                        platform_username=username_for_profile
                    )
                    fingerprint = pm.get_fingerprint()
                    if fingerprint:
                        acc['user_agent'] = fingerprint.get('user_agent')
        except Exception as e:
            logger.warning(f"预加载指纹信息失败: {e}")

    async def _run_verification_task(self, accounts):
        """异步验证任务逻辑"""
        self._verifier = AccountVerifier(self.account_manager, max_workers=3)
        
        def internal_callback(current, total, account_id, result):
            self.progress.emit(current, total, (account_id, result))
            
        try:
            return await self._verifier.verify_accounts_batch(accounts, internal_callback)
        finally:
            pass

    def cancel(self):
        """取消验证任务"""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._current_task = None
