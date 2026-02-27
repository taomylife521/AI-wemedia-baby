"""
账号管理页面
文件路径：src/ui/pages/account/view.py
功能：账号管理页面，包含账号列表、添加、删除、登录等功能
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QDialog, QCheckBox, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QUrl, QTimer, QEvent, QSize
from PySide6.QtGui import QFont, QColor
import logging

from qfluentwidgets import (
    FluentIcon, SubtitleLabel, CardWidget, PrimaryPushButton, 
    PushButton, BodyLabel, TitleLabel, CaptionLabel, TableWidget,
    SearchLineEdit, ComboBox, IconWidget, InfoBar, InfoBarPosition,
    TransparentToolButton, CheckBox, MessageBox, MessageBoxBase,
    FlowLayout
)
FLUENT_WIDGETS_AVAILABLE = True # Keep for compatibility if other modules check it, or better remove it? 
# Let's remove the flag usage in this file.

from ..base_page import BasePage
from .components import AccountTableWidget
from .components import AccountTableWidget
from .menus import AccountContextMenu
from .dialogs.set_group_dialog import SetGroupDialog # Import check
from .services import AccountValidatorService, AccountOperationsService
from src.services.browser import PlaywrightBrowserService
from src.infrastructure.common.di.service_locator import ServiceLocator
from src.infrastructure.common.config.config_center import ConfigCenter

logger = logging.getLogger(__name__)

from src.plugins.core.plugin_manager import PluginManager
from config.feature_flags import USE_PLUGIN_SYSTEM

class AccountPage(BasePage):
    """账号管理页面"""
    
    def __init__(self, parent=None):
        super().__init__("账号管理", parent, enable_scroll=True)
        self.account_manager = None
        self.user_id = 1  # 默认用户ID，实际应该从登录状态获取
        self._active_workers = []  # 保存所有活动的AsyncWorker引用，防止被垃圾回收
        self._init_services()
        self._setup_content()
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.services.account.account_manager_async import AccountManagerAsync
            from src.infrastructure.common.event.event_bus import EventBus
            
            service_locator = ServiceLocator()
            event_bus = service_locator.get(EventBus)
            
            # 创建账号管理器（已迁移为 Repository 模式）
            self.account_manager = AccountManagerAsync(
                user_id=self.user_id,
                event_bus=event_bus
            )
            
            # 初始化账号组服务（待迁移为 AccountGroupRepositoryAsync）
            from src.services.account.account_group_service import AccountGroupService
            self.group_service = AccountGroupService(event_bus=event_bus)
            
            logger.info("账号管理器初始化成功（异步版本）")
        except Exception as e:
            logger.error(f"初始化账号管理器失败: {e}", exc_info=True)
    
    def _setup_content(self):
        """设置内容"""
        # ThemeManager 已接管样式加载，无需手动加载

        # 导入新组件
        from ...components.statistics_card import StatisticsCard
        
        # 0. 顶部统计区域
        stats_layout = FlowLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setHorizontalSpacing(16)
        stats_layout.setVerticalSpacing(16)
        
        self.stats_total = StatisticsCard("账号总数", "0", "已绑定账号", FluentIcon.PEOPLE, self)
        self.stats_total.setMinimumWidth(200)
        
        self.stats_online = StatisticsCard("在线账号", "0", "状态正常", FluentIcon.ACCEPT, self)
        self.stats_online.setMinimumWidth(200)
        
        self.stats_offline = StatisticsCard("离线账号", "0", "需要重新登录", FluentIcon.INFO, self) 
        self.stats_offline.setMinimumWidth(200)
        
        stats_layout.addWidget(self.stats_total)
        stats_layout.addWidget(self.stats_online)
        stats_layout.addWidget(self.stats_offline)
        
        self.content_layout.addLayout(stats_layout)

        from PySide6.QtWidgets import QSizePolicy
        
        # 1. 操作栏（使用 CardWidget 包裹，看起来更统一）
        header_card = CardWidget(self)
        header_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # header_card.setFixedHeight(80) # Removed fixed height
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)
        
        # 左侧：核心操作按钮组
        actions_group = QHBoxLayout()
        actions_group.setSpacing(8)
        
        self.btn_add = PrimaryPushButton(FluentIcon.ADD, "添加账号", self)
        self.btn_refresh = PushButton(FluentIcon.SYNC, "刷新登录状态", self)
        self.btn_delete = PushButton(FluentIcon.DELETE, "删除账号", self)
        
        self.btn_add.clicked.connect(self._on_add_account)
        self.btn_refresh.clicked.connect(self._on_refresh)
        self.btn_delete.clicked.connect(self._on_delete_account)
        
        # 从 ServiceLocator 获取全局 Playwright 服务（已在 main.py 中用 AccountManagerAsync 初始化）
        from src.infrastructure.common.di.service_locator import ServiceLocator
        self.playwright_service = ServiceLocator().get(PlaywrightBrowserService)
        
        # 连接服务全局信号
        self.playwright_service.message_signal.connect(self._show_service_message)
        self.playwright_service.browser_launched.connect(self._on_browser_launched)
        
        # 初始化验证服务
        self.validator_service = AccountValidatorService(self.account_manager, self)
        self.validator_service.started.connect(self._on_verification_started)
        self.validator_service.progress.connect(self._on_verification_progress)
        self.validator_service.finished.connect(self._on_verification_finished)
        self.validator_service.error.connect(self._on_verification_error)
        
        # 初始化操作服务
        self.operations_service = AccountOperationsService(self.account_manager, self)
        self.operations_service.account_added.connect(self._on_account_added)
        self.operations_service.batch_delete_finished.connect(self._on_batch_deleted)
        self.operations_service.account_updated.connect(self._on_account_updated)
        
        # 将按钮添加到操作组
        actions_group.addWidget(self.btn_add)
        actions_group.addWidget(self.btn_refresh)
        actions_group.addWidget(self.btn_delete)
        
        header_layout.addLayout(actions_group)
        header_layout.addStretch()
        
        # 右侧：搜索和筛选
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("搜索账号...")
        self.search_box.setMinimumWidth(150)
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_box.textChanged.connect(self._filter_accounts)
        
        self.platform_filter = ComboBox(self)
        self.platform_filter.addItems(["全部平台", "抖音", "快手", "小红书", "视频号"])
        self.platform_filter.setMinimumWidth(120)
        self.platform_filter.currentIndexChanged.connect(self._filter_accounts)
        
        header_layout.addWidget(self.search_box, 0, Qt.AlignVCenter)
        header_layout.addWidget(self.platform_filter, 0, Qt.AlignVCenter)
        
        self.content_layout.addWidget(header_card)
        
        # 保存按钮引用以便响应式处理
        self._action_buttons = [self.btn_add, self.btn_refresh, self.btn_delete]
        
        # 2. 账号表格区域 (使用 StackedWidget 实现骨架屏切换)
        from PySide6.QtWidgets import QStackedWidget
        from ...components.skeleton import SkeletonTable
        
        self.table_stack = QStackedWidget(self)
        
        # 真实表格 (Index 0)
        self.account_table_widget = AccountTableWidget(self)
        self.account_table_widget.context_menu_requested.connect(self._on_context_menu)
        self.account_table_widget.switch_account_requested.connect(self._on_switch_account)
        # 连接双击信号，实现双击打开浏览器
        self.account_table_widget.account_double_clicked.connect(self._on_switch_account)
        self.table_stack.addWidget(self.account_table_widget)
        
        # 骨架屏 (Index 1)
        self.skeleton_table = SkeletonTable(rows=8, columns=5, parent=self)
        self.table_stack.addWidget(self.skeleton_table)
        
        self.content_layout.addWidget(self.table_stack, 1)  # stretch=1
        
        # 3. 加载账号数据
        self._load_accounts()

    def _show_service_message(self, level, title, content):
        """显示来自服务的消息"""
        if level == "info":
            InfoBar.info(title=title, content=content, parent=self)
        elif level == "success":
            InfoBar.success(title=title, content=content, parent=self)
        elif level == "warning":
            InfoBar.warning(title=title, content=content, parent=self)
        elif level == "error":
            InfoBar.error(title=title, content=content, parent=self)

    def _on_browser_launched(self, account_id, platform_username, platform, is_new_account):
        """浏览器启动成功，显示控制对话框"""
        # 如果是已有账号打开，不显示控制弹窗，后台静默运行
        if not is_new_account:
            return

        from src.ui.dialogs.browser_control_dialog import BrowserControlDialog
        from shiboken6 import isValid
        
        dialog = BrowserControlDialog(self, platform_username, platform, is_new_account)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        
        # 连接对话框操作 -> 服务逻辑
        dialog.close_browser_clicked.connect(lambda: asyncio.create_task(self.playwright_service.close_browser(account_id)))
        
        if is_new_account:
            dialog.manual_save_clicked.connect(lambda: asyncio.create_task(self.playwright_service.handle_save_new_account(account_id, platform)))
            # 存活检查逻辑：确保回调执行时对话框未被销毁
            def safe_update_status(_, msg):
                if isValid(dialog) and dialog.isVisible():
                    dialog.update_status(msg)
            
            def safe_accept(_):
                if isValid(dialog) and dialog.isVisible():
                    dialog.accept()

            self.playwright_service.status_updated.connect(safe_update_status)
            self.playwright_service.account_saved.connect(safe_accept)
        else:
            dialog.manual_update_clicked.connect(lambda: asyncio.create_task(self.playwright_service.update_account_from_browser(account_id, platform_username, platform)))
            
        # 浏览器关闭信号 -> 关闭对话框
        def safe_close(closed_id):
            if closed_id == account_id and isValid(dialog) and dialog.isVisible():
                dialog.close()
                
        self.playwright_service.browser_closed.connect(safe_close)
        
        dialog.show()
        # 保存实例引用
        setattr(self, f"_dialog_{account_id}", dialog) 
        dialog.finished.connect(lambda: delattr(self, f"_dialog_{account_id}") if hasattr(self, f"_dialog_{account_id}") else None)

    def resizeEvent(self, event):
        """窗口大小改变时，自适应调整 UI"""
        super().resizeEvent(event)
        
        # 响应式：当宽度小于 800px 时，隐藏按钮文字
        is_small = self.width() < 800
        for btn in getattr(self, '_action_buttons', []):
            if hasattr(btn, 'setText'):
                # 简单处理：如果宽度小，且不是只显示图标模式，可以考虑隐藏文字
                # 但 Fluent 按钮通常支持文字配合图标
                # 这里仅作为扩展示例，保持默认行为
                pass

    def _load_accounts(self):
        """加载账号列表"""
        if not self.account_manager:
            return
            
        try:
            import inspect
            import asyncio
            
            # 显示骨架屏
            if hasattr(self, 'table_stack'):
                self.table_stack.setCurrentIndex(1)
            
            # 定义一个内部协程函数来获取数据并直接更新 UI，避免跨线程
            async def _do_fetch_and_update():
                try:
                    # 1. 创建任务
                    # 获取账号任务
                    if inspect.iscoroutinefunction(self.account_manager.get_accounts):
                        accounts_task = self.account_manager.get_accounts()
                    else:
                        # 如果不是协程，包装成协程
                        async def _sync_wrapper():
                            return self.account_manager.get_accounts()
                        accounts_task = _sync_wrapper()
                    
                    # 获取分组任务
                    groups_task = None
                    if hasattr(self, 'group_service') and self.group_service:
                        groups_task = self.group_service.get_groups(self.user_id)
                    
                    # 2. 等待结果
                    if groups_task:
                        accounts, groups = await asyncio.gather(accounts_task, groups_task)
                    else:
                        accounts = await accounts_task
                        groups = []
                    
                    # 3. 建立 group_id -> group_name 映射
                    group_map = {g['id']: g['group_name'] for g in groups}
                    
                    # 4. 合并数据
                    result = []
                    for account in accounts:
                        # account 已经是 dict
                        acc_dict = account.copy() if hasattr(account, 'copy') else dict(account)
                        group_id = acc_dict.get('group_id')
                        if group_id:
                            acc_dict['group_name'] = group_map.get(group_id)
                        result.append(acc_dict)
                        
                    # 5. 更新UI (因为处于 qasync 主事件循环，完全可以安全操作UI)
                    if hasattr(self, 'table_stack'):
                        self.table_stack.setCurrentIndex(0)
                        
                    if result:
                        self.account_table_widget.load_accounts(result)
                        # 更新统计
                        total = len(result)
                        online = sum(1 for a in result if a.get('login_status') == 'online')
                        offline = total - online
                        self.stats_total.set_value(str(total))
                        self.stats_online.set_value(str(online))
                        self.stats_offline.set_value(str(offline))
                    else:
                        self.account_table_widget.load_accounts([])
                        self.stats_total.set_value("0")
                        self.stats_online.set_value("0")
                        self.stats_offline.set_value("0")
                except Exception as e:
                    logger.error(f"加载账号内部流程失败: {e}", exc_info=True)
                    if hasattr(self, 'table_stack'):
                        self.table_stack.setCurrentIndex(0)

            # 让主线程事件循环直接执行协程
            asyncio.create_task(_do_fetch_and_update())
                
        except Exception as e:
            logger.error(f"加载账号触发失败: {e}", exc_info=True)

    def _remove_worker(self, worker):
        """从活动worker列表移除"""
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    def _filter_accounts(self):
        """根据搜索框和平台筛选过滤账号"""
        keyword = self.search_box.text().strip()
        platform_index = self.platform_filter.currentIndex()
        platform_map = {0: None, 1: 'douyin', 2: 'kuaishou', 3: 'xiaohongshu', 4: 'wechat_video'}
        platform = platform_map.get(platform_index)
        
        self.account_table_widget.filter_accounts(keyword, platform)

    def _on_context_menu(self, account_data, global_pos):
        """显示右键菜单"""
        # 优化: 复用菜单管理器实例，避免每次重建引起卡顿
        if not hasattr(self, 'context_menu_manager') or self.context_menu_manager is None:
            self.context_menu_manager = AccountContextMenu(self)
        
        callbacks = {
            'on_switch': lambda acc_id: self._on_switch_account(acc_id),
            'on_update': lambda acc_id, uname, plat: self._on_update_account_manually(acc_id, uname, plat),
            'on_fingerprint': lambda acc_id, uname, plat: self._show_fingerprint(acc_id, uname, plat),
            'on_delete': lambda acc_id: self._delete_single_account(account_data),
            'on_set_group': lambda acc_id: self._on_set_account_group(acc_id, account_data),
            'on_copy_name': lambda name: QApplication.clipboard().setText(name),
            'on_refresh_status': lambda acc_id: self._refresh_single_account_status(acc_id)
        }
        
        self.context_menu_manager.show_menu(
            global_pos,
            account_data.get('id'),
            account_data.get('platform_username'),
            account_data.get('platform'),
            callbacks
        )

    def _on_set_account_group(self, account_id, account_data):
        """设置账号分组"""
        if not hasattr(self, 'group_service') or not self.group_service:
            self._show_error("账号组服务未初始化")
            return
            
        try:
            from src.ui.utils.async_helper import AsyncWorker
            import asyncio
            from .dialogs.set_group_dialog import SetGroupDialog
            
            # 1.获取所有分组
            async def get_groups_and_show():
                groups = await self.group_service.get_groups(self.user_id)
                return groups
                
            def on_groups_loaded(groups):
                # 显示对话框
                current_group_id = account_data.get('group_id')
                dialog = SetGroupDialog(self, current_group_id, groups)
                
                if dialog.exec():
                    new_group_id = dialog.selected_group_id
                    
                    # 2. 更新分组
                    async def update_group():
                        if new_group_id:
                            await self.group_service.add_account_to_group(new_group_id, account_id)
                        else:
                            # 如果选择了未分类，但账号之前有分组，则移除
                            # 需要先获取账号当前所属分组，或者 service 提供 remove_from_group
                            # 假设 remove_account_from_group 需要 account_id
                            await self.group_service.remove_account_from_group(account_id)
                            
                    def on_updated(_):
                        self._show_success("账号分组已更新")
                        self._load_accounts() # 刷新列表
                        self._remove_worker(update_worker)
                        
                    def on_update_error(e):
                        self._show_error(f"更新分组失败: {e}")
                        self._remove_worker(update_worker)
                        
                    update_worker = AsyncWorker(update_group)
                    update_worker.finished.connect(on_updated)
                    update_worker.error.connect(on_update_error)
                    self._active_workers.append(update_worker)
                    update_worker.start()
                    
                self._remove_worker(load_worker)

            def on_load_error(e):
                self._show_error(f"获取分组列表失败: {e}")
                self._remove_worker(load_worker)
                
            load_worker = AsyncWorker(get_groups_and_show)
            load_worker.finished.connect(on_groups_loaded)
            load_worker.error.connect(on_load_error)
            self._active_workers.append(load_worker)
            load_worker.start()
            
        except Exception as e:
            logger.error(f"设置分组流程出错: {e}", exc_info=True)
            self._show_error(f"操作失败: {e}")

    def _show_fingerprint(self, account_id, platform_username, platform):
        """显示浏览器指纹信息"""
        try:
            from src.infrastructure.browser.profile_manager import ProfileManager
            from .dialogs.fingerprint_dialog import FingerprintDialog
            
            # 初始化 ProfileManager
            pm = ProfileManager(
                account_id=str(account_id), 
                platform=platform, 
                account_name=platform_username
            )
            
            # 获取指纹配置
            fingerprint = pm.get_fingerprint()
            
            # 显示对话框
            dialog = FingerprintDialog(platform_username, platform, fingerprint, self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"显示指纹信息失败: {e}", exc_info=True)
            self._show_error(f"查看指纹失败: {str(e)}")

    def _delete_single_account(self, account_data):
        """删除单个账号"""
        accounts_to_delete = [{
            'id': account_data.get('id'),
            'username': account_data.get('platform_username')
        }]
        self.operations_service.delete_accounts(accounts_to_delete, True)


    def _on_add_account(self):
        """添加账号按钮点击"""
        try:
            from src.ui.account.add_account_dialog import AddAccountDialog
            
            dialog = AddAccountDialog(self)
            result = dialog.show()
            
            if not result:
                return
            
            platform_username = result['platform_username']
            platform = result['platform']
            platform_url = result['platform_url']
            platform_name = result.get('platform_name', '')
            
            # 使用 ServiceLocator 获取配置...
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.infrastructure.common.config.config_center import ConfigCenter
            
            browser_scheme = "playwright" # 默认纯净方案
            try:
                config_center = ServiceLocator().get(ConfigCenter)
                if config_center:
                    app_config = config_center.get_app_config()
                    if app_config:
                        browser_scheme = app_config.get("browser_scheme", "playwright")
            except Exception:
                browser_scheme = "playwright" # 如果获取配置失败，也默认纯净方案
            
            if browser_scheme in ["playwright", "undetected_playwright", "pure"]:
                # 纯净方案：使用 PlaywrightBrowserService
                if hasattr(self, 'playwright_service'):
                    import asyncio
                    # 定义保存回调 (Adapter)
                    # 定义保存回调 (Adapter)
                    async def save_callback(nickname, platform, cookies, profile_folder_name=None):
                         # 调用 Operations Service 添加账号 (它会处理信号和UI刷新)
                         self.operations_service.add_account(nickname, platform, cookies, profile_folder_name)
                         
                    asyncio.create_task(self.playwright_service.open_new_account_window(
                        platform=platform,
                        platform_url=platform_url,
                        on_save_callback=save_callback
                    ))
                else:
                    QMessageBox.warning(self, "错误", "PlaywrightService 未初始化")
            else:
                # 混合方案：使用 BrowserLoginDialog
                from .dialogs.browser_login_dialog import BrowserLoginDialog
                
                login_dialog = BrowserLoginDialog(
                    account_name=platform_username,
                    platform_name=platform_name,
                    platform_url=platform_url,
                    parent=self
                )
                
                if login_dialog.exec():
                    cookies = login_dialog.get_cookies()
                    if cookies:
                        logger.info(f"登录成功，获取到Cookies，准备保存账号: {platform_username}")
                        if hasattr(self, 'operations_service'):
                            self.operations_service.add_account(platform_username, platform, cookies)
                        else:
                            logger.error("AccountOperationsService not initialized")
                            QMessageBox.warning(self, "错误", "服务未初始化，无法保存账号")
            
        except Exception as e:
            logger.error(f"添加账号失败: {e}", exc_info=True)
            InfoBar.error(
                title='错误',
                content=f"添加账号失败：{str(e)}",
                parent=self
            )
    
    

    
    # _on_update_account_manually (manual implementation) removed - delegates to service in later definition

    # _switch_to_browser_and_load removed (unused)
    
    def _switch_to_browser_and_load_with_cookie(
        self,
        account_id: int,
        platform_username: str,
        platform: str,
        platform_url: str,
        platform_name: str,
        profile_folder_name: str = None
    ):
        """切换到浏览器页面并加载账号Cookie"""
        logger.info(f"开始切换到浏览器页面: {platform_username}")
        
        try:
            main_window = self.window()
            if not main_window:
                return

            # 1. 导航 (Lazy Load)
            if hasattr(main_window, 'navigate_to'):
                main_window.navigate_to("browser_page")

            # 2. 获取实例
            browser_page = getattr(main_window, 'browser_page', None)
            if not browser_page:
                logger.error("无法获取 BrowserPage 实例")
                return

            # 3. 确保初始化
            if hasattr(browser_page, 'is_initialized') and not browser_page.is_initialized():
                browser_page._ensure_initialized()
                # Removed QApplication.processEvents() - risky and unnecessary if logic is correct

            # 4. 加载 Cookie (延迟 100ms 以配合页面切换动画 80ms)
            QTimer.singleShot(100, lambda: browser_page.load_account_with_cookie(
                account_id, 
                platform_username=platform_username, 
                platform=platform, 
                platform_url=platform_url,
                profile_folder_name=profile_folder_name
            ))
            
            # 5. 静默刷新状态 (延迟 10秒，让浏览器先加载完，且不影响用户操作)
            # 使用 aiohttp 协议检测，不干扰浏览器
            QTimer.singleShot(10000, lambda: self._silent_refresh_status(account_id))
            
        except Exception as e:
            logger.error(f"切换浏览器页面失败: {e}", exc_info=True)
    def _on_account_added(self, account_id: int, account_name: str):
        """账号添加成功回调"""
        logger.info(f"账号添加成功: {account_name}, ID: {account_id}")
        self._load_accounts()
        self._show_service_message("success", "账号添加成功", f"账号 {account_name} 添加成功")
        
    def _on_account_updated(self, account_id: int, update_type: str):
        """账号更新回调（来自EventBus）"""
        logger.info(f"收到账号更新通知: ID={account_id}, Type={update_type}")
        # 刷新列表
        self._load_accounts()
        
        # 如果是状态更新，且之前可能有静默刷新任务，这里其实已经不需要做什么了
        # 列表刷新后，状态应该变成最新（在线）
        
    def _silent_refresh_status(self, account_id: int):
        """静默刷新单个账号状态（不显示加载条）"""
        if not self.account_manager:
            return
        
        logger.info(f"触发静默状态刷新: {account_id}")
        # 使用服务层的新接口，静默验证
        self.validator_service.start_verify_by_ids([account_id], silent=True)

    def _refresh_single_account_status(self, account_id: int):
        """刷新单个账号状态"""
        if not self.account_manager:
            return
            
        # 使用服务层的新接口，直接通过ID验证
        self.validator_service.start_verify_by_ids([account_id])

    def _on_refresh(self):
        """刷新账号列表（验证Cookie有效性）"""
        if not self.account_manager:
            return
            
        # 使用服务层的新接口，验证所有账号
        self.validator_service.start_verify_all()

    def _on_verification_started(self, total):
        """验证开始"""
        self.progress_dialog = QProgressDialog("正在验证账号状态...", "取消", 0, total, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setWindowTitle("同步账号状态")
        self.progress_dialog.resize(400, 150)
        
        # 连接取消按钮
        self.progress_dialog.canceled.connect(self.validator_service.cancel)
        
        self.progress_dialog.show()

    def _on_verification_progress(self, current, total, data):
        """验证进度 - 逐条实时更新 UI"""
        # 更新进度条
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(current)
        
        # 逐条实时更新表格中该账号的状态
        if data:
            account_id, result = data
            if account_id and result:
                is_online = result.get('is_logged_in', False)
                new_status = 'online' if is_online else 'offline'
                error_msg = result.get('error', '')
                username = result.get('username', '')
                
                # 实时更新表格行的状态图标
                if hasattr(self, 'account_table_widget'):
                    self.account_table_widget.update_account_status(
                        account_id, new_status, error_msg
                    )

    def _on_verification_finished(self, results):
        """验证完成"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # 直接从验证结果更新统计卡片（不重载表格，否则会清除离线原因提示）
        if results and isinstance(results, dict):
            online_count = sum(1 for r in results.values() if r.get('is_logged_in'))
            offline_count = len(results) - online_count
            total = self.account_table_widget.table.rowCount() if hasattr(self, 'account_table_widget') else online_count + offline_count
            
            if hasattr(self, 'stats_total'):
                self.stats_total.set_value(str(total))
            if hasattr(self, 'stats_online'):
                self.stats_online.set_value(str(online_count))
            if hasattr(self, 'stats_offline'):
                self.stats_offline.set_value(str(offline_count))
            
            self._show_success(f"验证完成：{online_count} 在线，{offline_count} 离线")
        else:
            self._show_success("账号状态已同步")

    def _on_verification_error(self, error):
        """验证出错"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        self._load_accounts()
        self._show_warning(f"验证过程出现错误: {error}")

    def _show_info(self, content):
        InfoBar.info(title='提示', content=content, parent=self)

    def _show_success(self, content):
        InfoBar.success(title='成功', content=content, parent=self)
            
    def _show_error(self, content):
        InfoBar.error(title='错误', content=content, parent=self)
            
    def _show_warning(self, content):
        InfoBar.warning(title='警告', content=content, parent=self)

    def _batch_sync_nicknames(self, accounts, progress_dialog, parent_worker):
        """批量深度同步昵称 (Headless Browser)"""
        logger.info(f"开始批量深度同步昵称，共 {len(accounts)} 个账号")
        
        # 使用 AsyncWorker 执行耗时操作
        from src.ui.utils.async_helper import AsyncWorker
        
        def run_sync_task():
            import asyncio
            from src.infrastructure.browser.browser_factory import BrowserFactory
            from src.infrastructure.plugins.builtin_plugins.douyin_plugin import DouyinPlugin
            
            # 获取事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def process_single(account):
                account_name = account.get('account_name')
                account_id = account.get('id')
                logger.info(f"正在同步账号昵称: {account_name}")
                
                browser_manager = None
                try:
                    # 1. 启动 Headless 浏览器
                    # 使用正确的参数初始化 BrowserFactory
                    browser_manager = BrowserFactory.get_browser_service(
                        account_id=account_id,
                        platform=account.get('platform', 'douyin'),
                        platform_username=account.get('platform_username', account_name)
                    )
                    context = await browser_manager.launch(headless=True)
                    if not context:
                        logger.error(f"启动浏览器失败: {account_name}")
                        return False
                    
                    page = await context.new_page()
                    
                    # 2. 访问创作者中心
                    await page.goto("https://creator.douyin.com/creator-micro/home")
                    try:
                        await page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        pass
                    
                    # 3. 提取昵称 (使用插件逻辑)
                    plugin = DouyinPlugin()
                    await plugin.initialize()
                    nickname = await plugin.get_nickname(page)
                    
                    if nickname:
                        logger.info(f"成功提取到昵称: {nickname}")
                        # 4. 更新数据库
                        await self.account_manager.data_storage.update_platform_username(account_id, nickname)
                        sync_worker.progress.emit(1, 1, (account_id, nickname)) # 发射进度信号
                        return True
                    else:
                        logger.warning(f"未能提取到昵称: {account_name}")
                        return False
                        
                except Exception as e:
                    logger.error(f"同步昵称失败 {account_name}: {e}")
                    return False
                finally:
                    if browser_manager:
                        await browser_manager.close()

            # 串行执行，避免并发启动多个浏览器导致资源耗尽
            async def run_loop():
                for i, account in enumerate(accounts):
                    # 通知进度 (当前索引, 总数, 正在处理的账号名)
                    sync_worker.progress.emit(i, len(accounts), account.get('account_name'))
                    await process_single(account)
            
            loop.run_until_complete(run_loop())
            return len(accounts)

        sync_worker = AsyncWorker(run_sync_task)
        
        def on_sync_progress(current, total, data):
            if isinstance(data, str):
                # 正在处理某个账号
                progress_dialog.setLabelText(f"正在深度同步昵称 ({current + 1}/{total}):\n{data}...")
            elif isinstance(data, tuple):
                # 单个完成 (id, nickname)
                pass

        sync_worker.progress.connect(on_sync_progress)
        
        def on_sync_finished(result):
            progress_dialog.close()
            self._load_accounts()
            
            InfoBar.success(
                title='深度同步完成',
                content=f'已完成 {result} 个账号的昵称同步',
                parent=self
            )
            
            self._remove_worker(sync_worker)
            # 清理父worker
            if parent_worker:
                self._remove_worker(parent_worker)

        sync_worker.finished.connect(on_sync_finished)
        
        def on_sync_error(e):
            logger.error(f"深度同步任务失败: {e}", exc_info=True)
            progress_dialog.close()
            InfoBar.warning(title="部分同步失败", content=f"同步过程中发生错误: {e}", parent=self)
            self._remove_worker(sync_worker)
            if parent_worker:
                self._remove_worker(parent_worker)

        sync_worker.error.connect(on_sync_error)
        
        self._active_workers.append(sync_worker)
        sync_worker.start()
    
    def _on_delete_account(self):
        """批量删除账号"""
        selected_rows = self.account_table_widget.table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        logger.info(f"点击删除按钮，选中 {len(selected_rows)} 行")
        
        # 收集选中账号的信息
        accounts_to_delete = []
        for index in selected_rows:
            row = index.row()
            # 获取账号信息 (从第1列 - 昵称)
            account_item = self.account_table_widget.table.item(row, 1)
            if account_item:
                account_id = account_item.data(Qt.ItemDataRole.UserRole)
                account_username = account_item.text()
                
                accounts_to_delete.append({
                    'id': account_id,
                    'username': account_username
                })
        
        if not accounts_to_delete:
            return

        def run_delete(delete_cookie_val):
             self.operations_service.delete_accounts(accounts_to_delete, delete_cookie_val)

        
        count = len(accounts_to_delete)
        confirm_text = f"确定要删除选中的 {count} 个账号吗？" if count > 1 else f"确定要删除账号「{accounts_to_delete[0]['username']}」吗？"
        
        if True: # Always use Fluent Widgets
            msg_box = MessageBoxBase(self)
            msg_box.setWindowTitle("删除账号")
            title_label = SubtitleLabel("确认删除", msg_box)
            msg_box.viewLayout.addWidget(title_label)
            
            content_label = BodyLabel(confirm_text, msg_box)
            msg_box.viewLayout.addWidget(content_label)
            
            cb_delete_cookie = CheckBox("同时删除Cookie和发布记录", msg_box)
            cb_delete_cookie.setChecked(True)  # 默认勾选
            msg_box.viewLayout.addWidget(cb_delete_cookie)
            
            msg_box.yesButton.setText("删除")
            msg_box.cancelButton.setText("取消")
            
            if msg_box.exec():
                run_delete(cb_delete_cookie.isChecked())

    # _execute_batch_delete removed (moved to service)


    def _on_batch_deleted(self, count):
        """批量删除完成回调"""
        self._load_accounts()
        msg = f"成功删除 {count} 个账号"
        msg = f"成功删除 {count} 个账号"
        InfoBar.success(title="操作成功", content=msg, parent=self)
    
    def _on_cookie_cleared(self, success: bool, platform_username: str):
        """Cookie清理完成回调"""
        # ... logic if needed, but we merged it into delete
        pass
    
    
    
    
    def _open_playwright_browser_for_account(self, account_id: int):
        """使用 Playwright 服务打开浏览器（复用模块化方法）"""
        if hasattr(self, 'playwright_service'):
            import asyncio
            asyncio.create_task(self.playwright_service.open_browser_for_db_account(account_id))
        else:
            logger.error("Playwright service not initialized")
            InfoBar.error(title="错误", content="浏览器服务未初始化", parent=self)

    def _on_update_account_manually(self, account_id: int, platform_username: str, platform: str):
        """使用 Playwright 服务手动更新账号"""
        if hasattr(self, 'playwright_service'):
            import asyncio
            asyncio.create_task(self.playwright_service.update_account_from_browser(
                account_id, platform_username, platform
            ))
        else:
            logger.error("Playwright service not initialized")
            InfoBar.error(title="错误", content="浏览器服务未初始化", parent=self)

    def _get_cookie_domain(self, platform: str) -> str:
        """获取平台的Cookie域名
        
        Args:
            platform: 平台ID
        
        Returns:
            Cookie域名
        """
        domain_map = {
            'douyin': '.douyin.com',
            'kuaishou': '.kuaishou.com',
            'wechat_video': '.weixin.qq.com',
            'xiaohongshu': '.xiaohongshu.com'
        }
        return domain_map.get(platform, '')
    
    def _on_switch_account(self, account_id: int):
        """切换账号并打开浏览器（复用模块化方法 open_browser_for_db_account）
        
        Args:
            account_id: 数据库账号ID
        """
        try:
            logger.info(f"双击打开浏览器: account_id={account_id}")
            self._open_playwright_browser_for_account(account_id)
        except Exception as e:
            logger.error(f"打开浏览器失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"打开浏览器失败：{str(e)}")
    
    def closeEvent(self, event: QEvent) -> None:
        """页面关闭事件，等待所有AsyncWorker完成"""
        # 等待所有worker完成
        for worker in self._active_workers[:]:
            if worker.isRunning():
                worker.wait(3000)  # 等待最多3秒
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(1000)
        
        super().closeEvent(event)

