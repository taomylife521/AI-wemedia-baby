"""
浏览器页面
文件路径：src/ui/pages/browser_page.py
功能：多标签页浏览器页面，支持多账号同时打开、Cookie隔离
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox, QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QFont, QColor, QShowEvent
import logging

from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, BodyLabel, LineEdit,
    SubtitleLabel, CaptionLabel, TransparentToolButton, FluentIcon as FI
)
FLUENT_WIDGETS_AVAILABLE = True

from .base_page import BasePage
from src.ui.components import BrowserTab, BrowserTabBar

logger = logging.getLogger(__name__)


class EmptyBrowserWidget(QWidget):
    """空白浏览器提示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_style()

    def _update_style(self):
        # 已由全局 QSS 接管
        pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 图标
        icon_label = QLabel("🌐", self)
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 标题
        # 标题
        title = SubtitleLabel("欢迎使用多账号浏览器", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 提示
        hint = CaptionLabel("在账号管理中双击账号，即可在此打开对应平台", self)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)


class BrowserPage(BasePage):
    """多标签页浏览器页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化浏览器页面（立即初始化UI）"""
        super().__init__("浏览器", parent)
        
        # 标签页管理
        self.tabs: Dict[int, BrowserTab] = {}
        self.next_tab_id = 1
        self.current_tab_id: Optional[int] = None
        
        # 账号管理器
        self.account_manager = None
        
        # UI组件（立即初始化）
        self.tab_bar: Optional[BrowserTabBar] = None
        self.stacked_widget: Optional[QStackedWidget] = None
        self.empty_widget: Optional[EmptyBrowserWidget] = None
        self.url_edit: Optional[QLineEdit] = None
        self.status_label: Optional[QLabel] = None
        self.progress_label: Optional[QLabel] = None
        self.btn_back: Optional[QPushButton] = None
        self.btn_forward: Optional[QPushButton] = None
        self.btn_refresh: Optional[QPushButton] = None
        self.btn_home: Optional[QPushButton] = None
        
        # 初始化状态标记
        self._is_initialized = False
        self._is_dark = None # 跟踪主题状态
        
    # def paintEvent(self, event):
    #     """绘制事件，用于检测主题变化"""
    #     super().paintEvent(event)
    #     if self._is_initialized:
    #         pass # 主题由 ThemeManager 自动管理
    
    def _init_services(self):
        """初始化服务（轻量级，不创建UI组件）"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.services.account.account_manager_async import AccountManagerAsync
            from src.infrastructure.common.event.event_bus import EventBus
            
            service_locator = ServiceLocator()
            event_bus = service_locator.get(EventBus)
            
            # 创建账号管理器（已迁移为 Repository 模式）
            self.account_manager = AccountManagerAsync(
                user_id=1,
                event_bus=event_bus
            )
            logger.info("浏览器页面：账号管理器初始化成功（异步版本）")
        except Exception as e:
            logger.error(f"浏览器页面：初始化账号管理器失败: {e}", exc_info=True)
    
    def _ensure_initialized(self):
        """确保UI组件已初始化（在主窗口显示后立即调用）"""
        if self._is_initialized:
            return
        
        import time
        init_start_time = time.time()
        logger.info(f"[初始化] 浏览器页面：开始初始化UI组件 (时间戳: {init_start_time:.3f})")
        
        # 禁用更新，避免初始化过程中的闪动
        self.setUpdatesEnabled(False)
        try:
            self._setup_content()
            self._apply_styles()
            self._is_initialized = True
            
            # 初始化完成后，如果有标签页则显示标签页，否则显示空白提示
            # 注意：不在这里强制设置，让后续的标签创建流程来决定显示什么
            # 这样可以避免从empty_widget到tab的切换闪烁
            
            init_end_time = time.time()
            init_duration = (init_end_time - init_start_time) * 1000
            logger.info(f"[初始化] 浏览器页面：UI组件初始化完成 (耗时: {init_duration:.2f}ms)")
        finally:
            # 重新启用更新
            self.setUpdatesEnabled(True)
    
    def is_initialized(self) -> bool:
        """检查UI是否已初始化完成
        
        Returns:
            bool: 如果UI已初始化返回True
        """
        return self._is_initialized
    
    def showEvent(self, event: QShowEvent):
        """页面显示事件，确保UI已初始化"""
        # 如果还未初始化，立即初始化（主窗口显示后会触发）
        if not self._is_initialized:
            self._ensure_initialized()
        super().showEvent(event)
    
    def _setup_content(self):
        """设置内容"""
        try:
            # 彻底移除边距，让标签页直接贴在顶部
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(0)
            
            # 1. 创建标签栏（移到最上方）
            self.tab_bar = BrowserTabBar(self)
            self.tab_bar.tab_clicked.connect(self._on_tab_clicked)
            self.tab_bar.tab_close_requested.connect(self._on_tab_close_requested)
            self.tab_bar.new_tab_requested.connect(self._on_new_tab_requested)
            self.content_layout.addWidget(self.tab_bar)
            
            # 2. 创建内容区域容器（中间区域）
            content_container = QWidget(self)
            content_container.setObjectName("browserContentContainer")
            content_layout = QVBoxLayout(content_container)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)
            
            # 标签页容器
            self.stacked_widget = QStackedWidget(content_container)
            self.stacked_widget.setObjectName("browserStackedWidget")
            
            # 空白提示
            self.empty_widget = EmptyBrowserWidget(self.stacked_widget)
            self.empty_widget.setObjectName("browserEmptyWidget")
            self.stacked_widget.addWidget(self.empty_widget)
            
            # 默认显示空白提示（但如果在初始化过程中立即创建标签页，这个设置会被覆盖）
            # 为了减少闪烁，我们不在初始化时强制显示，让后续流程决定
            self.stacked_widget.setCurrentWidget(self.empty_widget)
            
            content_layout.addWidget(self.stacked_widget)
            self.content_layout.addWidget(content_container, stretch=1)
            
            # 3. 创建工具栏（地址栏，移到下方）
            toolbar_widget = self._create_toolbar()
            self.content_layout.addWidget(toolbar_widget)
            
            # 4. 创建状态栏（最下方）
            status_widget = self._create_status_bar()
            self.content_layout.addWidget(status_widget)
            
            # 组件默认就是可见的，不需要显式调用show()
            logger.info("浏览器页面布局优化完成：标签页置顶，地址栏移至底部")
        except Exception as e:
            logger.error(f"浏览器页面布局优化失败: {e}", exc_info=True)
            error_label = QLabel(f"浏览器布局优化失败：{str(e)}", self)
            self.content_layout.addWidget(error_label)
    
    def _setup_toolbar(self):
        # ... logic moved to _create_toolbar ...
        pass

    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QFrame(self)
        toolbar.setObjectName("browserToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(8)
        
        # 使用 Fluent Widgets 的 TransparentToolButton
        # 已在文件头部导入
        pass
        
        # 后退按钮
        self.btn_back = TransparentToolButton(FI.LEFT_ARROW, toolbar)
        self.btn_back.setFixedSize(32, 32)
        self.btn_back.setToolTip("后退")
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.setEnabled(False)
        toolbar_layout.addWidget(self.btn_back)
        
        # 前进按钮
        self.btn_forward = TransparentToolButton(FI.RIGHT_ARROW, toolbar)
        self.btn_forward.setFixedSize(32, 32)
        self.btn_forward.setToolTip("前进")
        self.btn_forward.clicked.connect(self._on_forward)
        self.btn_forward.setEnabled(False)
        toolbar_layout.addWidget(self.btn_forward)
        
        # 刷新按钮
        self.btn_refresh = TransparentToolButton(FI.SYNC, toolbar)
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.setToolTip("刷新")
        self.btn_refresh.clicked.connect(self._on_refresh)
        toolbar_layout.addWidget(self.btn_refresh)
        
        # 主页按钮
        self.btn_home = TransparentToolButton(FI.HOME, toolbar)
        self.btn_home.setFixedSize(32, 32)
        self.btn_home.setToolTip("主页")
        self.btn_home.clicked.connect(self._on_home)
        toolbar_layout.addWidget(self.btn_home)
        
        # 地址栏
        self.url_edit = QLineEdit(toolbar)
        self.url_edit.setPlaceholderText("输入网址...")
        self.url_edit.setObjectName("urlEdit")
        self.url_edit.returnPressed.connect(self._on_url_entered)
        toolbar_layout.addWidget(self.url_edit, stretch=1)
        
        return toolbar

    def _apply_styles(self):
        """应用样式 - 已废弃，由 ThemeManager 接管"""
        pass
    
    def _on_back(self):
        if self.current_tab_id and self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].back()
            QTimer.singleShot(100, self._batch_update_ui)
    
    def _on_forward(self):
        if self.current_tab_id and self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].forward()
            QTimer.singleShot(100, self._batch_update_ui)
    
    def _on_refresh(self):
        if self.current_tab_id and self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].reload()
    
    def _on_home(self):
        if self.current_tab_id and self.current_tab_id in self.tabs:
            tab = self.tabs[self.current_tab_id]
            platform_urls = {
                'douyin': 'https://creator.douyin.com/',
                'kuaishou': 'https://cp.kuaishou.com/',
                'xiaohongshu': 'https://creator.xiaohongshu.com/',
                'wechat_video': 'https://channels.weixin.qq.com/'
            }
            url = platform_urls.get(tab.platform, 'https://www.baidu.com')
            tab.load_url(url)
    
    def _on_url_entered(self):
        url = self.url_edit.text().strip()
        if not url:
            return
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if self.current_tab_id and self.current_tab_id in self.tabs:
            self.tabs[self.current_tab_id].load_url(url)
    
    def _on_tab_clicked(self, tab_id: int):
        self._switch_to_tab(tab_id)
    
    def _on_tab_close_requested(self, tab_id: int):
        self._close_tab(tab_id)
    
    def _on_new_tab_requested(self):
        # 新建空白标签暂不支持，需要通过账号管理双击账号
        pass
    
    def _switch_to_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        
        import time
        switch_start = time.time()
        logger.info(f"[标签切换] 开始切换到标签: {tab_id} ({self.tabs[tab_id].account_name}) (时间戳: {switch_start:.3f})")
        
        tab = self.tabs[tab_id]
        index = self.stacked_widget.indexOf(tab)
        
        if index >= 0:
            # 直接切换，不需要额外的show/setVisible调用
            self.stacked_widget.setCurrentIndex(index)
            logger.info(f"[标签切换] StackedWidget已切换到索引: {index}")
        
        self.current_tab_id = tab_id
        
        if self.tab_bar:
            self.tab_bar.set_active_tab(tab_id)
            logger.info(f"[标签切换] 标签栏已激活标签: {tab_id}")
        
        # 批量更新UI（避免频繁更新）
        self._batch_update_ui()
        
        # 预加载标签页（如果浏览器组件未就绪）
        if not tab._is_browser_ready:
            logger.info(f"[标签切换] 浏览器组件未就绪，开始预加载")
            self._preload_tab(tab_id)
        
        switch_end = time.time()
        switch_duration = (switch_end - switch_start) * 1000
        logger.info(f"[标签切换] 切换到标签完成 (耗时: {switch_duration:.2f}ms)")
    
    def _preload_tab(self, tab_id: int):
        """预加载标签页的Cookie（后台异步）
        
        Args:
            tab_id: 标签页ID
        """
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        
        def preload_cookie():
            """预加载Cookie"""
            try:
                if tab_id not in self.tabs:
                    return
                
                if self.account_manager and hasattr(self.account_manager, 'cookie_manager'):
                    try:
                        logger.info(f"[预加载] 开始预加载Cookie: {tab.account_name}")
                        cookie_data = self.account_manager.cookie_manager.load_cookie(
                            tab.account_name, tab.platform
                        )
                        if cookie_data:
                            cookie_list = self._convert_cookie_data(cookie_data, tab.platform)
                            if cookie_list:
                                # 确保浏览器组件已创建
                                tab._ensure_browser_ready()
                                result = tab.inject_cookie(cookie_list)
                                if result:
                                    logger.info(f"[预加载] 标签 [{tab.account_name}] Cookie预加载成功")
                                else:
                                    logger.warning(f"[预加载] 标签 [{tab.account_name}] Cookie预加载失败")
                    except Exception as e:
                        logger.warning(f"[预加载] Cookie预加载失败: {e}")
            except Exception as e:
                logger.error(f"[预加载] 预加载异常: {e}", exc_info=True)
        
        # 异步预加载Cookie
        QTimer.singleShot(0, preload_cookie)
    
    def _close_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        
        # 从堆叠窗口移除
        self.stacked_widget.removeWidget(tab)
        
        # 清理资源
        tab.cleanup()
        
        # 移除
        del self.tabs[tab_id]
        
        if self.tab_bar:
            self.tab_bar.remove_tab(tab_id)
        
        # 切换到其他标签或显示空白页
        if self.current_tab_id == tab_id:
            if self.tabs:
                next_tab_id = next(iter(self.tabs.keys()))
                self._switch_to_tab(next_tab_id)
            else:
                self.current_tab_id = None
                self.stacked_widget.setCurrentWidget(self.empty_widget)
                self._batch_update_ui()
        
        logger.info(f"关闭标签: {tab_id}")
    
    def _batch_update_ui(self):
        """批量更新UI（避免频繁更新造成卡顿）"""
        # 使用QTimer.singleShot(0, ...) 在下一个事件循环中批量更新
        if not hasattr(self, '_ui_update_timer') or not self._ui_update_timer:
            self._ui_update_timer = QTimer()
            self._ui_update_timer.setSingleShot(True)
            self._ui_update_timer.timeout.connect(self._do_update_ui)
        
        # 如果定时器已经在运行，不重复启动
        if not self._ui_update_timer.isActive():
            self._ui_update_timer.start(0)
    
    def _do_update_ui(self):
        """执行UI更新（批量更新）"""
        self._update_toolbar()
        self._update_status_bar()
        self._update_navigation_buttons()
    
    def _update_toolbar(self):
        if not self.current_tab_id or self.current_tab_id not in self.tabs:
            if self.url_edit:
                self.url_edit.setText("")
            return
        
        tab = self.tabs[self.current_tab_id]
        current_url = tab.get_current_url()
        
        if self.url_edit:
            self.url_edit.setText(current_url)
    
    def _update_status_bar(self):
        if not self.current_tab_id or self.current_tab_id not in self.tabs:
            if self.status_label:
                self.status_label.setText("就绪 - 请从账号管理双击账号打开")
            if self.progress_label:
                self.progress_label.setText("")
            return
        
        tab = self.tabs[self.current_tab_id]
        account_info = f"账号: {tab.account_name} | 平台: {tab.platform}"
        
        if self.status_label:
            self.status_label.setText(account_info)
    
    def _update_navigation_buttons(self):
        if not self.current_tab_id or self.current_tab_id not in self.tabs:
            if self.btn_back:
                self.btn_back.setEnabled(False)
            if self.btn_forward:
                self.btn_forward.setEnabled(False)
            return
        
        tab = self.tabs[self.current_tab_id]
        
        if self.btn_back:
            self.btn_back.setEnabled(tab.can_go_back())
        if self.btn_forward:
            self.btn_forward.setEnabled(tab.can_go_forward())
    
    def load_account_with_cookie(
        self,
        account_id: int,
        platform_username: str,
        platform: str,
        platform_url: str,
        profile_folder_name: str = None
    ):
        """加载账号并打开平台URL
        
        Args:
            account_id: 账号ID
            platform_username: 平台昵称（代替已删除的备注名）
            platform: 平台ID
            platform_url: 平台URL
        """
        # UI应该已经初始化（主窗口显示时已初始化）
        # 如果还未初始化（异常情况），立即初始化
        if not self._is_initialized:
            logger.warning("[BrowserPage] UI未初始化（异常情况），立即初始化...")
            self._ensure_initialized()
        
        logger.info(f"[BrowserPage] load_account_with_cookie 调用开始")
        logger.info(f"  - account_id: {account_id}")
        logger.info(f"  - platform_username: {platform_username}")
        logger.info(f"  - platform: {platform}")
        logger.info(f"  - platform_url: {platform_url}")
        
        # 验证参数
        if not account_id or not platform_username or not platform or not platform_url:
            logger.error(f"参数验证失败: account_id={account_id}, platform_username={platform_username}, platform={platform}, url={platform_url}")
            QMessageBox.warning(self, "错误", "账号信息不完整")
            return
        
        # 获取账号昵称（platform_username），优先使用昵称作为标签名称
        tab_display_name = platform_username
        if self.account_manager:
            # 检查是否是异步管理器
            from ...business.account.account_manager_async import AccountManagerAsync
            if isinstance(self.account_manager, AccountManagerAsync):
                # 异步管理器，使用AsyncWorker获取账号信息
                from ..utils.async_helper import AsyncWorker
                
                async def get_account_async():
                    return await self.account_manager.get_account_by_id(account_id)
                
                def on_account_loaded(account_info):
                    final_display_name = platform_username
                    if account_info and account_info.get('platform_username'):
                        final_display_name = account_info['platform_username']
                        logger.info(f"使用账号昵称作为标签名称: {final_display_name}")
                    else:
                        logger.info(f"账号未设置昵称，使用传入昵称: {platform_username}")
                    # 继续创建标签
                    self._create_tab_with_account(account_id, platform_username, platform, platform_url, final_display_name, profile_folder_name)
                
                def on_error(error):
                    logger.warning(f"获取账号信息失败: {error}，使用账号名称: {platform_username}")
                    # 即使失败也继续创建标签
                    self._create_tab_with_account(account_id, platform_username, platform, platform_url, platform_username, profile_folder_name)
                
                worker = AsyncWorker(get_account_async)
                worker.finished.connect(on_account_loaded)
                worker.error.connect(on_error)
                worker.setParent(self)
                worker.start()
                return  # 等待异步回调
            else:
                # 同步管理器，直接调用
                try:
                    account_info = self.account_manager.get_account_by_id(account_id)
                    if account_info and account_info.get('platform_username'):
                        tab_display_name = account_info['platform_username']
                        logger.info(f"使用账号昵称作为标签名称: {tab_display_name}")
                    else:
                        logger.info(f"账号未设置昵称，使用账号名称: {platform_username}")
                except Exception as e:
                    logger.warning(f"获取账号信息失败: {e}，使用账号名称: {platform_username}")
        
        # 继续创建标签
        self._create_tab_with_account(account_id, platform_username, platform, platform_url, tab_display_name, profile_folder_name)
    
    def _create_tab_with_account(
        self,
        account_id: int,
        platform_username: str,
        platform: str,
        platform_url: str,
        tab_display_name: str,
        profile_folder_name: str = None
    ):
        """创建标签（内部方法，在获取账号信息后调用）"""
        # 检查是否已有该账号的标签
        logger.info(f"检查是否已有账号标签，当前标签数: {len(self.tabs)}")
        for tab_id, tab in self.tabs.items():
            if tab.account_id == account_id:
                logger.info(f"账号 {platform_username} 已有标签 {tab_id}，切换并刷新")
                self._switch_to_tab(tab_id)
                # 更新标签名称（如果昵称已更新）
                if self.tab_bar:
                    self.tab_bar.update_tab_name(tab_id, tab_display_name)
                logger.info(f"切换到标签 {tab_id}，开始加载URL: {platform_url}")
                tab.load_url(platform_url)
                return
        
        # 创建新标签
        import time
        tab_creation_start = time.time()
        tab_id = self.next_tab_id
        self.next_tab_id += 1
        logger.info(f"[标签创建] 开始创建新标签，tab_id: {tab_id} (时间戳: {tab_creation_start:.3f})")
        
        try:
            # 验证组件是否就绪
            if not self.stacked_widget:
                logger.error("[标签创建] stacked_widget未初始化")
                QMessageBox.warning(self, "错误", "浏览器组件未初始化")
                return
            
            # 禁用更新，避免创建过程中的闪动
            self.setUpdatesEnabled(False)
            try:
                # 创建标签页
                tab_create_start = time.time()
                logger.info(f"[标签创建] 开始创建BrowserTab实例")
                tab = BrowserTab(
                    account_id=account_id,
                    account_name=platform_username,
                    platform=platform,
                    parent=self
                )
                tab_create_end = time.time()
                logger.info(f"[标签创建] BrowserTab实例创建成功 (耗时: {(tab_create_end - tab_create_start) * 1000:.2f}ms)")
                
                # 连接信号
                logger.info(f"[标签创建] 连接BrowserTab信号")
                tab.url_changed.connect(lambda url: self._on_tab_url_changed(tab_id, url))
                tab.title_changed.connect(lambda title: self._on_tab_title_changed(tab_id, title))
                tab.load_progress.connect(lambda progress: self._on_tab_load_progress(tab_id, progress))
                tab.load_finished.connect(lambda success: self._on_tab_load_finished(tab_id, success))
                tab.cookies_updated.connect(lambda cookies: self._on_tab_cookies_updated(tab_id, cookies))
                logger.info(f"[标签创建] 信号连接完成")
                
                # 添加到堆叠窗口（在禁用更新的情况下）
                logger.info(f"[标签创建] 添加标签到stacked_widget")
                self.stacked_widget.addWidget(tab)
                tab_index = self.stacked_widget.indexOf(tab)
                logger.info(f"[标签创建] 标签已添加到stacked_widget，索引: {tab_index}")
                
                # 保存标签
                self.tabs[tab_id] = tab
                logger.info(f"[标签创建] 标签已保存到tabs字典，当前标签数: {len(self.tabs)}")
                
                # 添加到标签栏（使用昵称或账号名称）
                if self.tab_bar:
                    logger.info(f"[标签创建] 添加标签到标签栏，显示名称: {tab_display_name}")
                    self.tab_bar.add_tab(tab_id, tab_display_name, set_active=True)
                    logger.info(f"[标签创建] 标签已添加到标签栏")
                else:
                    logger.warning("[标签创建] 标签栏未初始化")
                
                # 存储标签显示名称，用于后续更新
                if not hasattr(self, '_tab_display_names'):
                    self._tab_display_names = {}
                self._tab_display_names[tab_id] = tab_display_name
                
                # 直接切换到新标签（在禁用更新的情况下，避免中间状态）
                logger.info(f"[标签创建] 切换到新标签 {tab_id}")
                self._switch_to_tab(tab_id)
                logger.info(f"[标签创建] 标签切换完成")
                
            finally:
                # 重新启用更新
                self.setUpdatesEnabled(True)
            
            tab_creation_end = time.time()
            tab_creation_duration = (tab_creation_end - tab_creation_start) * 1000
            logger.info(f"[标签创建] 标签创建流程完成 (总耗时: {tab_creation_duration:.2f}ms)")
            
            # 异步加载Cookie和URL（智能等待，不使用固定延迟）
            self._load_cookie_and_url_async(tab_id, platform_username, platform, platform_url, profile_folder_name)
            
        except Exception as e:
            logger.error(f"创建标签页失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"打开账号失败：{str(e)}")
    
    def _load_cookie_and_url_async(self, tab_id: int, platform_username: str, platform: str, platform_url: str, profile_folder_name: str = None):
        """异步加载Cookie和URL（智能等待）
        
        Args:
            tab_id: 标签页ID
            platform_username: 账号名称
            platform: 平台ID
            platform_url: 平台URL
        """
        def load_cookie():
            """异步加载Cookie"""
            try:
                logger.info(f"[异步加载] 开始加载Cookie: {platform_username}")
                
                # 验证标签页是否仍然存在
                if tab_id not in self.tabs:
                    logger.error(f"标签 {tab_id} 不存在，无法加载Cookie")
                    return
                
                tab = self.tabs[tab_id]
                
                # 加载Cookie
                if self.account_manager and hasattr(self.account_manager, 'cookie_manager'):
                    try:
                        cookie_data = self.account_manager.cookie_manager.load_cookie(
                            platform_username, platform, profile_folder_name
                        )
                        if cookie_data:
                            logger.info(f"Cookie数据加载成功，开始转换格式")
                            cookie_list = self._convert_cookie_data(cookie_data, platform)
                            if cookie_list:
                                logger.info(f"Cookie格式转换成功，共 {len(cookie_list)} 个Cookie")
                                # 确保浏览器组件已创建
                                tab._ensure_browser_ready()
                                result = tab.inject_cookie(cookie_list)
                                if result:
                                    logger.info(f"标签 [{platform_username}] 注入Cookie成功: {len(cookie_list)}个")
                                else:
                                    logger.warning(f"标签 [{platform_username}] 注入Cookie失败")
                            else:
                                logger.warning(f"Cookie列表为空")
                        else:
                            logger.warning(f"未找到Cookie数据")
                    except Exception as e:
                        logger.warning(f"加载Cookie失败: {e}", exc_info=True)
                else:
                    logger.warning(f"账号管理器或Cookie管理器不可用")
            except Exception as e:
                logger.error(f"异步加载Cookie失败: {e}", exc_info=True)
        
        def load_url():
            """加载URL（在浏览器组件就绪后）"""
            import time
            url_load_start = time.time()
            try:
                logger.info(f"[URL加载] 开始加载URL: {platform_username} (时间戳: {url_load_start:.3f})")
                
                # 验证标签页是否仍然存在
                if tab_id not in self.tabs:
                    logger.error(f"[URL加载] 标签 {tab_id} 不存在，无法加载URL")
                    return
                
                tab = self.tabs[tab_id]
                
                # 确保当前标签页是活动的（如果还没有切换）
                if self.stacked_widget:
                    tab_index = self.stacked_widget.indexOf(tab)
                    if tab_index >= 0 and self.stacked_widget.currentIndex() != tab_index:
                        logger.info(f"[URL加载] 确保标签页是活动的，切换到索引: {tab_index}")
                        self.stacked_widget.setCurrentIndex(tab_index)
                
                # 加载URL（这会触发浏览器组件的懒加载）
                logger.info(f"[URL加载] 标签 [{platform_username}] 开始加载URL: {platform_url}")
                tab.load_url(platform_url)
                url_load_end = time.time()
                url_load_duration = (url_load_end - url_load_start) * 1000
                logger.info(f"[URL加载] URL加载命令已发送 (耗时: {url_load_duration:.2f}ms)")
                
            except Exception as e:
                logger.error(f"[URL加载] 加载URL失败: {e}", exc_info=True)
                QMessageBox.warning(self, "错误", f"加载页面失败：{str(e)}")
        
        # 使用QTimer.singleShot(0, ...) 异步执行，不阻塞UI
        # 先加载URL（触发浏览器组件创建），然后异步加载Cookie
        QTimer.singleShot(0, load_url)
        QTimer.singleShot(50, load_cookie)  # 50ms后加载Cookie，给浏览器组件一点初始化时间
    
    def _convert_cookie_data(self, cookie_data, platform: str):
        """转换Cookie数据格式"""
        cookie_list = []
        
        def get_cookie_domain(platform: str) -> str:
            domain_map = {
                'douyin': '.douyin.com',
                'kuaishou': '.kuaishou.com',
                'wechat_video': '.weixin.qq.com',
                'xiaohongshu': '.xiaohongshu.com'
            }
            return domain_map.get(platform, '')
        
        if isinstance(cookie_data, dict):
            first_key = next(iter(cookie_data.keys())) if cookie_data else None
            if first_key and isinstance(cookie_data[first_key], str):
                for name, value in cookie_data.items():
                    cookie_dict = {
                        'name': name,
                        'value': value,
                        'domain': get_cookie_domain(platform),
                        'path': '/',
                        'secure': True,
                        'httpOnly': False
                    }
                    cookie_list.append(cookie_dict)
            elif first_key and isinstance(cookie_data[first_key], dict):
                for key, cookie_info in cookie_data.items():
                    if isinstance(cookie_info, dict) and 'name' in cookie_info:
                        cookie_list.append(cookie_info)
                    else:
                        cookie_dict = {
                            'name': key,
                            'value': str(cookie_info) if not isinstance(cookie_info, dict) else cookie_info.get('value', ''),
                            'domain': get_cookie_domain(platform),
                            'path': '/',
                            'secure': True,
                            'httpOnly': False
                        }
                        cookie_list.append(cookie_dict)
        elif isinstance(cookie_data, list):
            cookie_list = cookie_data
        
        return cookie_list
    
    def _on_tab_url_changed(self, tab_id: int, url: QUrl):
        if tab_id == self.current_tab_id:
            self._batch_update_ui()
    
    def _on_tab_title_changed(self, tab_id: int, title: str):
        """标签页标题变化时的处理"""
        if tab_id == self.current_tab_id:
            self._update_status_bar()
        # 不更新标签栏名称，保持显示账号昵称或账号名称
        # 标签栏显示的是账号昵称，不是页面标题
    
    def _on_tab_load_progress(self, tab_id: int, progress: int):
        if tab_id == self.current_tab_id and self.progress_label:
            if progress < 100:
                self.progress_label.setText(f"加载中 {progress}%")
            else:
                self.progress_label.setText("")
    
    def _on_tab_load_finished(self, tab_id: int, success: bool):
        if tab_id == self.current_tab_id:
            if self.progress_label:
                self.progress_label.setText("" if success else "加载失败")
            self._batch_update_ui()
            
            if success:
                logger.info(f"标签 {tab_id} 加载完成")
            else:
                logger.warning(f"标签 {tab_id} 加载失败")

    def _on_tab_cookies_updated(self, tab_id: int, cookies: list):
        """Cookie更新回调 (自动同步到存储)"""
        if tab_id not in self.tabs:
            return
            
        tab = self.tabs[tab_id]
        account_id = tab.account_id
        
        # 使用AsyncWorker异步更新，不阻塞UI
        from ..utils.async_helper import AsyncWorker
        
        async def do_update():
            if self.account_manager:
                try:
                    await self.account_manager.update_cookie(account_id, cookies)
                    logger.debug(f"标签 {tab_id} Cookie已自动同步 (数量: {len(cookies)})")
                except Exception as e:
                    logger.warning(f"标签 {tab_id} Cookie同步失败: {e}")
        
        worker = AsyncWorker(do_update)
        worker.setParent(self)
        worker.start()
