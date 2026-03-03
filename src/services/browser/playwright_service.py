# -*- coding: utf-8 -*-
"""
Playwright 浏览器服务
文件路径：src/services/browser/playwright_service.py
功能：管理 Playwright 浏览器实例，提供纯逻辑的浏览器控制服务，不包含UI代码
"""

import asyncio
import logging
import json
from typing import Dict, Optional, Union, Callable, Any

from PySide6.QtCore import QObject, Signal

from src.infrastructure.browser.browser_factory import BrowserFactory
from src.plugins.core.plugin_manager import PluginManager
from config.feature_flags import USE_PLUGIN_SYSTEM

logger = logging.getLogger(__name__)


class PlaywrightBrowserService(QObject):
    """Playwright 浏览器服务 (Logic Only)
    
    负责底层浏览器生命周期管理、Cookie提取、自动化操作。
    通过信号与UI层通信。
    """
    
    # === Signals ===
    # 状态更新信号: (account_id, message)
    status_updated = Signal(str, str)
    
    # 消息提示信号: (level, title, message) level: info, success, warning, error
    message_signal = Signal(str, str, str)
    
    # 浏览器启动成功: (account_id, platform_username, platform, is_new)
    browser_launched = Signal(str, str, str, bool)
    
    # 浏览器已关闭: (account_id)
    browser_closed = Signal(str)
    
    # 检测到登录: (account_id, platform)
    login_detected = Signal(str, str)
    
    # 账号信息已保存/更新: (account_id)
    account_saved = Signal(str)
    
    # 账号昵称更新: (account_id, new_nickname)
    account_nickname_updated = Signal(str, str)

    def __init__(self, account_manager):
        super().__init__()
        self.account_manager = account_manager
        self.pw_browser_instance = None
        self._active_browsers = {}  # account_id -> browser_instance
        
        # 临时状态存储
        self._current_save_callback = None
        self._current_temp_name = None
        self._pending_rename_target = None
        
        # 监听任务引用，防止被回收
        self._monitor_tasks = {}

    async def verify_account_headless(self, account_id: str, platform: str) -> Dict[str, Any]:
        """无头模式验证账号状态"""
        logger.info(f"启动无头验证: {account_id} ({platform})")
        context = None
        browser_service = None
        try:
            # 1. 获取账号信息
            account = None
            if self.account_manager and str(account_id).isdigit():
                try:
                    account = await self.account_manager.get_account_by_id(int(account_id))
                except Exception:
                    pass
            
            platform_username = account.get('platform_username', f"user_{account_id}") if account else f"user_{account_id}"
            profile_folder_name = account.get('profile_folder_name') if account else None
            
            # 2. 启动浏览器 (Headless)
            browser_service = BrowserFactory.get_browser_service(
                account_id=str(account_id),
                platform=platform,
                platform_username=platform_username,
                profile_folder_name=profile_folder_name
            )
            
            context = await browser_service.launch(headless=True)
            if not context:
                raise Exception("无法启动浏览器上下文")
                
            # 3. 注入 Cookie
            if self.account_manager:
                try:
                    cookies = await self.account_manager.load_account_cookie(account_id)
                    if cookies:
                        pw_cookies = self._normalize_cookies_for_playwright(cookies, platform)
                        if pw_cookies:
                            await context.add_cookies(pw_cookies)
                except Exception as e:
                    logger.warning(f"加载Cookie失败: {e}")
            
            # 4. 验证逻辑
            success = await self._check_login_status(context, platform)
            nickname = None
            new_cookies = None
            
            if success:
                logger.info(f"无头验证成功: {account_id}")
                try:
                    new_pw_cookies = await context.cookies()
                    new_cookies = {c['name']: c['value'] for c in new_pw_cookies}
                    nickname = await self._extract_nickname(context, platform, new_cookies)
                    
                    if self.account_manager:
                         acc_id_int = int(account_id)
                         if new_cookies:
                             await self.account_manager.update_cookie(acc_id_int, new_cookies)
                         if nickname and nickname != platform_username:
                             await self.account_manager.update_platform_username(acc_id_int, nickname)
                             self.account_nickname_updated.emit(str(account_id), nickname)
                except Exception as db_e:
                    logger.warning(f"无头验证更新数据库失败: {db_e}")
            else:
                logger.warning(f"无头验证失败: {account_id}")
            
            return {
                'success': success,
                'nickname': nickname,
                'cookies': new_cookies,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"无头验证异常: {e}", exc_info=True)
            return {
                'success': False,
                'nickname': None,
                'cookies': None,
                'error': str(e)
            }
        finally:
            if browser_service:
                try:
                    if hasattr(browser_service, 'close'):
                        await browser_service.close()
                    elif hasattr(browser_service, 'stop'):
                        await browser_service.stop()
                except Exception as close_e:
                    logger.warning(f"无头浏览关闭异常: {close_e}")
    
    def get_browser_context_by_account(self, account_id: str) -> Optional[Any]:
        """获取指定账号已打开的浏览器上下文
        
        Args:
            account_id: 账号唯一标识 (字符串格式)
            
        Returns:
            若浏览器存在，则返回对应的 SimpleBrowserWrapper，包含 context 和 page；否则返回 None
        """
        browser = self._active_browsers.get(str(account_id))
        if browser:
            return browser
        return None
    
    async def open_browser_for_db_account(
        self, account_id: int, headless: Optional[bool] = None
    ) -> Optional['SimpleBrowserWrapper']:
        """根据数据库账号ID打开浏览器（模块化方法，供账号库和发布执行器复用）
        
        完整流程：查询账号信息 → 获取平台URL → 启动浏览器 → 注入Cookie → 导航
        
        Args:
            account_id: 数据库中的账号ID（整数）
            headless: 是否无头模式。None 时默认 False（显示窗口）；发布流程传入与「显示浏览器」勾选一致
            
        Returns:
            浏览器包装实例 SimpleBrowserWrapper，失败时返回 None
        """
        if headless is None:
            headless = False  # 账号页等调用不传时默认显示浏览器
        # 1. 查询账号详情
        account = await self.account_manager.get_account_by_id(account_id)
        if not account:
            raise ValueError(f"账号ID {account_id} 在数据库中不存在")
        
        platform_username = account.get('platform_username', '')
        platform = account.get('platform', '')
        profile_folder_name = account.get('profile_folder_name')
        
        logger.info(f"模块化开浏览器: account_id={account_id}, 用户名={platform_username}, 平台={platform}, headless={headless}")
        
        # 2. 获取平台 URL
        platform_url = self._get_platform_url(platform)
        
        # 3. 调用已有方法打开浏览器（传入 headless 供发布流程「显示浏览器」勾选生效）
        await self.open_browser_for_account(
            account_id=account_id,
            platform_username=platform_username,
            platform=platform,
            platform_url=platform_url,
            profile_folder_name=profile_folder_name,
            headless=headless,
        )
        
        # 4. 返回浏览器 wrapper
        return self.get_browser_context_by_account(str(account_id))

    def _get_platform_url(self, platform: str) -> str:
        """获取平台创作者页面 URL（优先插件，降级硬编码）
        
        Args:
            platform: 平台标识
            
        Returns:
            平台 URL
        """
        # 1. 优先从登录插件获取
        try:
            plugin = PluginManager.get_login_plugin(platform)
            if plugin and hasattr(plugin, 'login_url') and plugin.login_url:
                return plugin.login_url
        except Exception as e:
            logger.debug(f"从插件获取平台URL失败: {e}")
        
        # 2. 降级到硬编码配置
        platform_urls = {
            'douyin': 'https://creator.douyin.com/',
            'xiaohongshu': 'https://creator.xiaohongshu.com/',
            'kuaishou': 'https://cp.kuaishou.com/',
            'wechat_video': 'https://channels.weixin.qq.com/',
        }
        return platform_urls.get(platform, 'about:blank')

    async def open_browser_for_account(
        self,
        account_id: Union[int, str],
        platform_username: str,
        platform: str,
        platform_url: str,
        profile_folder_name: Optional[str] = None,
        headless: bool = False,
    ):
        """为已存在的账号打开 Playwright 浏览器"""
        await self._open_browser_base(
            account_id=str(account_id),
            platform_username=platform_username,
            platform=platform,
            platform_url=platform_url,
            inject_cookies=True,
            is_new_account=False,
            profile_folder_name=profile_folder_name,
            headless=headless,
        )

    async def open_new_account_window(
        self,
        platform: str,
        platform_url: str,
        on_save_callback: Callable[[str, str, Dict, str], Any],
        fingerprint_config: Optional[Dict[str, Any]] = None
    ):
        """打开新账号登录窗口"""
        import uuid
        import time
        
        # 统一使用正式的 profile_{UUID} 格式作为系统标识符
        # 这种格式在磁盘上更整洁，且不带有“临时(temp)”属性的心理暗示
        timestamp = int(time.time() * 1000)
        profile_id = f"profile_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"🚀 [V9] 开启新账号流程: platform={platform}, 统一ID={profile_id}")
        
        self._current_save_callback = on_save_callback
        self._current_temp_name = profile_id
        self._save_completed = False # 标记是否完成保存
        
        await self._open_browser_base(
            account_id=profile_id, # 统一使用 profile_id
            platform_username=profile_id,
            platform=platform,
            platform_url=platform_url,
            inject_cookies=False,
            is_new_account=True,
            fingerprint_config=fingerprint_config,
            profile_folder_name=profile_id
        )


    async def _open_browser_base(
        self,
        account_id: str,
        platform_username: str,
        platform: str,
        platform_url: str,
        inject_cookies: bool,
        is_new_account: bool,
        fingerprint_config: Optional[Dict[str, Any]] = None,
        profile_folder_name: Optional[str] = None,
        headless: bool = False,
    ):
        try:
            logger.info(f"正在启动 Playwright 浏览器 for {platform_username}... (headless={headless})")
            
            # 1. 启动浏览器（headless 由发布页「显示浏览器」勾选或账号页默认显示决定）
            browser_service = BrowserFactory.get_browser_service(
                account_id=account_id,
                platform=platform,
                platform_username=platform_username,
                fingerprint_config=fingerprint_config,
                profile_folder_name=profile_folder_name
            )
            
            context = await browser_service.launch(headless=headless)
            if not context:
                raise Exception("无法启动浏览器服务")
            
            # 2. 注入 Cookie
            if inject_cookies and self.account_manager:
                cookies = await self.account_manager.load_account_cookie(account_id)
                if cookies:
                    pw_cookies = self._normalize_cookies_for_playwright(cookies, platform)
                    if pw_cookies:
                        try:
                            await context.add_cookies(pw_cookies)
                            logger.info(f"已注入数据库 Cookie: {len(pw_cookies)} 个")
                        except Exception as e:
                            logger.warning(f"注入 Cookie 失败: {e}")
            
            # 3. 导航
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(platform_url)
            
            # 4. 保存实例
            self.pw_browser_instance = SimpleBrowserWrapper(browser_service, context, page)
            self._active_browsers[account_id] = self.pw_browser_instance
            logger.info(f"✓ 浏览器实例已存储: account_id={account_id}, total_browsers={len(self._active_browsers)}")
            
            # 5. 发送启动成功信号 -> UI层响应此信号来弹出 Dialog
            self.browser_launched.emit(account_id, platform_username, platform, is_new_account)
            
            # 6. 启动对应的监听任务
            if is_new_account:
                task = asyncio.create_task(self._monitor_new_account_login(account_id, platform))
                self._monitor_tasks[account_id] = task
            else:
                task = asyncio.create_task(self._monitor_existing_account_update(account_id, platform_username, platform))
                self._monitor_tasks[account_id] = task
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}", exc_info=True)
            self.message_signal.emit("error", "启动失败", str(e))

    async def close_browser(self, account_id: str):
        """关闭浏览器逻辑"""
        logger.info(f"正在关闭浏览器: {account_id}")
        
        # 1. 停止监听任务
        if account_id in self._monitor_tasks:
            self._monitor_tasks[account_id].cancel()
            del self._monitor_tasks[account_id]
            logger.debug(f"已取消监听任务: {account_id}")
        
        # 2. 关闭浏览器
        logger.info(f"当前活跃浏览器: {list(self._active_browsers.keys())}")
        browser = self._active_browsers.pop(account_id, None)
        logger.info(f"从字典中获取浏览器: browser={'找到' if browser else '未找到'}")
        if not browser and self.pw_browser_instance:
             # Fallback for temp instance
             browser = self.pw_browser_instance
             self.pw_browser_instance = None
             logger.info(f"使用 fallback 浏览器实例: {account_id}")
             
        try:
            if browser:
                # [关键变更] 在关闭前强制同步一次最新状态 (Cookie/LocalStorage)
                # 只有在 browser 实例还在且上下文未关闭时才有效
                try:
                    logger.info(f"关闭前执行状态同步: {account_id}")
                    # 这里的 platform/username 参数可能需要从 cache 或 browser 对象中获取
                    # 但 update_account_from_browser 其实主要依赖 context，参数主要用于日志或更新 DB
                    # 我们尝试从 self._active_browsers 或 external storage 获取更多上下文？
                    # 简单起见，我们假设 update_account_from_browser 能处理，或者我们把参数传进去
                    # 由于 close_browser 签名只有 account_id，我们需要看 update_account_from_browser 需要什么
                    # update_account_from_browser(self, account_id: str, platform_username: str, platform: str, silent=False)
                    
                    # 我们需要查找该 account_id 对应的 platform 和 username
                    # 这些信息没有直接存储在 PlaywrightService，但 AccountManager 有
                    # 或者我们可以从 browser.page.url 推断？
                    # 为了安全，我们只做 Cookie 提取，不需要更新 username (传空即可，或者 fetch from DB)
                    
                    # 实际上，我们可以重用 update_account_from_browser，传占位符，因为 update_cookie 只用 account_id
                    # update_platform_username 如果 username 不变也不会更新
                    
                    # 为了稳妥，先尝试获取 platform 和 username
                    if self.account_manager:
                        account = await self.account_manager.get_account_by_id(int(account_id)) if account_id.isdigit() else None
                        if account:
                            await self.update_account_from_browser(
                                account_id, 
                                account['platform_username'], 
                                account['platform'], 
                                silent=True
                            )
                        else:
                             # 如果是临时账号(profile_xxx)，可能查不到，或者就是为了保存新账号
                             # 新账号保存逻辑在 handle_save_new_account，这里主要针对已有账号
                            logger.info(f"账号ID {account_id} 未在数据库找到 (可能是新账号或临时ID)，跳过关闭前同步")
                except Exception as sync_e:
                    logger.warning(f"关闭前同步状态失败 (不影响关闭流程): {sync_e}")

                logger.info(f"准备释放浏览器资源: {account_id}")
                try:
                    # 给整个关闭过程设置一个总超时 5秒
                    await asyncio.wait_for(browser.close(), timeout=5.0)
                    logger.info(f"✓ 浏览器资源释放成功: {account_id}")
                except asyncio.TimeoutError:
                    logger.error(f"✗ 浏览器释放资源超时: {account_id}，可能仍有残留进程")
                except Exception as e:
                    logger.error(f"✗ 关闭浏览器实例失败: {e}", exc_info=True)
            else:
                logger.warning(f"未找到活跃浏览器实例: {account_id} (可能已手动关闭)")
        finally:
            # 3. 执行目录清理 (强制执行)
            # 即使释放资源超时或报错，也要尝试清理目录
            logger.info(f"执行最后的数据目录清理...")
            await asyncio.sleep(0.5)
            await self._handle_directory_cleanup(account_id)
        
        # 4. 发送关闭信号
        self.browser_closed.emit(account_id)
        logger.info(f"🎯 已发送浏览器关闭确认信号: {account_id}")

    async def shutdown(self):
        """应用退出时关闭所有活跃浏览器，避免残留进程。
        使用短超时快速收尾，不做状态同步与目录清理。
        """
        logger.info("PlaywrightBrowserService 开始 shutdown，关闭所有活跃浏览器...")
        # 1. 取消所有监听任务
        for account_id, task in list(self._monitor_tasks.items()):
            try:
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            except Exception:
                pass
        self._monitor_tasks.clear()

        # 2. 关闭所有 _active_browsers 中的浏览器（短超时，不阻塞退出）
        account_ids = list(self._active_browsers.keys())
        for account_id in account_ids:
            browser = self._active_browsers.pop(account_id, None)
            if not browser:
                continue
            try:
                await asyncio.wait_for(browser.close(), timeout=2.0)
                logger.info(f"shutdown: 已关闭浏览器 account_id={account_id}")
            except asyncio.TimeoutError:
                logger.warning(f"shutdown: 关闭 account_id={account_id} 超时，继续退出")
            except Exception as e:
                logger.warning(f"shutdown: 关闭 account_id={account_id} 异常: {e}")

        # 3. 关闭临时实例 pw_browser_instance
        if self.pw_browser_instance:
            try:
                await asyncio.wait_for(self.pw_browser_instance.close(), timeout=2.0)
            except (asyncio.TimeoutError, Exception):
                pass
            self.pw_browser_instance = None

        logger.info("PlaywrightBrowserService shutdown 完成")

    async def _handle_directory_cleanup(self, account_id: str):
        """处理目录清理"""
        # 同时支持旧的 temp_add_ 和统一后的 profile_ 前缀
        if isinstance(account_id, str) and (account_id.startswith("temp_add_") or account_id.startswith("profile_")):
            temp_name = self._current_temp_name
            
            # 如果保存已完成，直接返回，保留目录
            if self._save_completed:
                logger.info(f"账号已保存，保留数据目录作为永久档案: {temp_name}")
                self._current_temp_name = None
                return

            # 未保存则清理 (用户取消操作)
            logger.info(f"账号未保存，准备清理临时目录: {temp_name}")
            
            if temp_name:
                try:
                    import shutil
                    from src.infrastructure.common.path_manager import PathManager
                    
                    data_dir = PathManager.get_app_data_dir() / "data"
                    
                    if data_dir.exists():
                        # 遍历找到对应的临时目录（虽然我们知道是 temp_name，但为了安全在 data 下找）
                        for platform_dir in data_dir.iterdir():
                            if platform_dir.is_dir():
                                temp_dir = platform_dir / temp_name
                                if temp_dir.exists():
                                    try:
                                        # 强制清理
                                        shutil.rmtree(temp_dir, ignore_errors=True)
                                        logger.info(f"已清理废弃的临时目录: {temp_dir}")
                                    except Exception as ex:
                                        logger.warning(f"清理临时目录失败: {ex}")
                                    break
                except Exception as e:
                    logger.error(f"目录清理异常: {e}", exc_info=True)
                
                self._current_temp_name = None

    # === 业务逻辑 ===
    async def _monitor_new_account_login(self, account_id: str, platform: str):
        """监听新账号登录"""
        logger.info(f"开始监听登录: {account_id}")
        retry_count = 0
        while retry_count < 300:
            if not self.pw_browser_instance:
                break
            
            try:
                context = self.pw_browser_instance.context
                if await self._check_login_status(context, platform):
                    logger.info("检测到登录成功")
                    self.status_updated.emit(account_id, "检测到登录成功！\n正在自动提取账号信息...")
                    self.login_detected.emit(account_id, platform)
                    
                    await asyncio.sleep(2)
                    await self.handle_save_new_account(account_id, platform)
                    return
            except Exception:
                pass
            
            await asyncio.sleep(3)
            retry_count += 1

    async def handle_save_new_account(self, temp_id: str, platform: str):
        """执行保存逻辑 (提取 -> 回调 -> 标记完成)"""
        try:
            if not self.pw_browser_instance:
                 self.message_signal.emit("warning", "警告", "浏览器未连接")
                 return
            
            self.message_signal.emit("info", "提示", "正在提取账号信息...")
            context = self.pw_browser_instance.context
            
            cookies = await context.cookies()
            if not cookies:
                await asyncio.sleep(1)
                cookies = await context.cookies()
            if not cookies:
                raise Exception("未提取到 Cookie")
                
            cookie_dict = {c['name']: c['value'] for c in cookies}
            nickname = await self._extract_nickname(context, platform, cookie_dict)
            
            if not nickname:
                nickname = f"新账号_{platform}"
                logger.warning("未提取到昵称，使用默认值")
            
            # 调用回调
            # 注意：这是核心变更，我们将 profile_folder_name (即当前的 temp_name) 传回给 UI
            if self._current_save_callback:
                if asyncio.iscoroutinefunction(self._current_save_callback):
                    await self._current_save_callback(nickname, platform, cookie_dict, self._current_temp_name)
                else:
                    self._current_save_callback(nickname, platform, cookie_dict, self._current_temp_name)
                
                # 标记保存成功，这就阻止了 _handle_directory_cleanup 删除目录
                self._save_completed = True
                
            self.message_signal.emit("success", "保存成功", f"账号 {nickname} 已保存！\n无需重命名，安全退出。")
            self.account_saved.emit(temp_id)
            
        except Exception as e:
            logger.error(f"保存失败: {e}", exc_info=True)
            self.message_signal.emit("error", "保存回调失败", str(e))
        finally:
            # 无论成功或失败，都要关闭浏览器
            try:
                await asyncio.sleep(1.5)
                await self.close_browser(temp_id)
            except Exception as close_error:
                logger.error(f"关闭浏览器失败: {close_error}", exc_info=True)

    async def update_account_from_browser(self, account_id: str, platform_username: str, platform: str, silent=False):
        """更新已有账号信息"""
        try:
            # 优先根据 account_id 拿到对应的浏览器包装实例
            browser_wrapper = self.get_browser_context_by_account(str(account_id))
            # Fallback 兼容单例逻辑
            if not browser_wrapper:
                browser_wrapper = self.pw_browser_instance
                
            if not browser_wrapper:
                if not silent:
                    self.message_signal.emit("warning", "提示", "该账号的浏览器未连接或未打开，无法提取信息")
                return
            
            if not silent:
                self.message_signal.emit("info", "提示", "正在更新信息...")
                
            context = browser_wrapper.context
            
            # 1. 更新 Cookie
            cookies = await context.cookies()
            if cookies and self.account_manager:
                cookie_dict = {c['name']: c['value'] for c in cookies}
                # 确保 account_id 是 int
                try:
                    acc_id_int = int(account_id)
                    await self.account_manager.update_cookie(acc_id_int, cookie_dict)
                except ValueError:
                    logger.warning(f"account_id 不是有效整数: {account_id}, 跳过 Cookie 更新")
                
            # 2. 更新昵称
            nickname = await self._extract_nickname(context, platform, {})
            if nickname and self.account_manager and nickname != platform_username:
                 try:
                    acc_id_int = int(account_id)
                    await self.account_manager.update_platform_username(acc_id_int, nickname)
                    logger.info(f"更新账号昵称: {platform_username} -> {nickname}")
                    self.account_nickname_updated.emit(str(account_id), nickname)
                 except ValueError:
                     pass
            
            if not silent:
                self.message_signal.emit("success", "成功", "账号信息已从浏览器成功更新")
                
        except Exception as e:
            err_msg = str(e)
            if "Target page, context or browser has been closed" in err_msg:
                err_msg = "浏览器或页面已关闭，无法从当前实例提取状态"
                # 安全清理失效实例
                self._active_browsers.pop(str(account_id), None)
                if self.pw_browser_instance == browser_wrapper:
                    self.pw_browser_instance = None
                    
            if not silent:
                self.message_signal.emit("error", "失败", err_msg)

    async def _monitor_existing_account_update(self, account_id, username, platform):
        """监听现有账号更新 (单次静默更新)"""
        logger.info(f"启动已有账号静默更新任务: {username}, 等待页面加载...")
        
        # 等待页面加载 (10秒)
        # 我们不需要循环，只需要在用户打开浏览器一段时间后，静默同步一次状态即可
        # 这样既不会打扰用户，也能保证数据相对较新
        await asyncio.sleep(10)
        
        if not self.pw_browser_instance:
            logger.info("浏览器已关闭，取消静默更新")
            return
            
        logger.info(f"执行单次静默更新: {username}")
        await self.update_account_from_browser(account_id, username, platform, silent=True)
        logger.info(f"单次静默更新完成: {username}，任务结束 (浏览器保持开启)")

    async def _check_login_status(self, context, platform) -> bool:
        """检查登录状态"""
        try:
            # Check Cookies first
            cookies = await context.cookies()
            if not cookies: return False
            
            if USE_PLUGIN_SYSTEM:
                plugin = PluginManager.get_login_plugin(platform)
                if plugin:
                    return await plugin.check_login_status(context)
            return False
        except Exception:
            return False

    async def _extract_nickname(self, context, platform, cookies) -> Optional[str]:
        if USE_PLUGIN_SYSTEM:
            plugin = PluginManager.get_login_plugin(platform)
            if plugin:
                try:
                    res = await plugin.extract_user_info(context)
                    if res.nickname: return res.nickname
                except Exception:
                    pass
        return None

    def _normalize_cookies_for_playwright(self, raw_cookies, platform):
        # Playwright need [{'name', 'value', 'domain', 'path'}]
        # 我们数据库存的是 dict {name: value}
        # 需要补全 domain 和 path
        
        pw_cookies = []
        domain = ".douyin.com" if platform == 'douyin' else ".kuaishou.com"
        
        # 简单做个映射，如果是其他平台，可能需要更精确的 domain
        if platform == 'xiaohongshu':
            domain = ".xiaohongshu.com"
        elif platform == 'wechat_video':
            domain = ".channels.weixin.qq.com"  # 这是一个子域，可能不够? 应该 .weixin.qq.com?
            # 视频号的主域是 channels.weixin.qq.com
            # Cookie 很多是 qq.com 的
            # 简单起见，如果 platform 是 wechat_video，我们尝试 .weixin.qq.com ?
            # 或者就在这里写死一些通用 domain
            # 更好的做法是：存的时候就存 domain，现在取出来如果是 dict 就只能 blind guess
            domain = ".weixin.qq.com"

        if isinstance(raw_cookies, dict):
            for k, v in raw_cookies.items():
                pw_cookies.append({'name': k, 'value': v, 'domain': domain, 'path': '/'})
        elif isinstance(raw_cookies, list):
             for c in raw_cookies:
                pw_cookies.append({
                    'name': c.get('name'),
                    'value': c.get('value'),
                    'domain': c.get('domain', domain),
                    'path': c.get('path', '/')
                })
        return pw_cookies

class SimpleBrowserWrapper:
    """浏览器包装类，封装浏览器服务、上下文和页面实例"""
    def __init__(self, service, context, page):
        self.service = service
        self.browser_manager = service  # 兼容发布执行器等调用方
        self.context = context
        self.page = page
    async def close(self):
        if hasattr(self.service, 'close'): await self.service.close()
        elif hasattr(self.service, 'stop'): await self.service.stop()
