"""
主窗口模块
文件路径：src/ui/main_window.py
功能：主窗口实现，使用 PySide6-Fluent-Widgets 的 FluentWindow 和 NavigationInterface
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QMainWindow, QStatusBar
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QEvent
import os
import qasync
from qasync import asyncSlot
from PySide6.QtCore import Slot

import logging

# 导入 PySide6-Fluent-Widgets
from qfluentwidgets import (
    FluentWindow, FluentIcon, setTheme, Theme, NavigationItemPosition,
    isDarkTheme, InfoBar, InfoBarPosition, StateToolTip, NavigationDisplayMode
)
FLUENT_WIDGETS_AVAILABLE = True

from src.ui.navigation_config import NavigationConfig
from src.ui.page_factory import PageFactory

# 定义功能开关 (保留用于 NavigationConfig 判断)
try:
    import src.pro_features.batch.pages.batch_publish_page
    BATCH_FEATURE_AVAILABLE = True
except ImportError:
    BATCH_FEATURE_AVAILABLE = False

try:
    import src.pro_features.data_center.pages.data_center_page
    DATA_CENTER_AVAILABLE = True
except ImportError:
    DATA_CENTER_AVAILABLE = False

try:
    import src.pro_features.interaction.pages.comment_page
    INTERACTION_FEATURE_AVAILABLE = True
except ImportError:
    INTERACTION_FEATURE_AVAILABLE = False

try:
    import src.ui.pages.subscription_page
    SUBSCRIPTION_PAGE_AVAILABLE = True
except ImportError:
    SUBSCRIPTION_PAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


# 根据可用性选择基类
if FLUENT_WIDGETS_AVAILABLE:
    _BaseWindow = FluentWindow
else:
    _BaseWindow = QMainWindow


class MainWindow(FluentWindow):
    """主窗口 - 继承 FluentWindow 实现现代化 Fluent Design 风格"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 初始化页面工厂
        self.page_factory = PageFactory()

        # 设置窗口图标 (优先使用 PNG)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        icon_png = os.path.join(project_root, "resources", "logo.png")
        icon_ico = os.path.join(project_root, "resources", "icons", "app.ico")
        
        if os.path.exists(icon_png):
            self.setWindowIcon(QIcon(icon_png))
            logger.debug(f"MainWindow 设置图标 (PNG): {icon_png}")
        elif os.path.exists(icon_ico):
            self.setWindowIcon(QIcon(icon_ico))
            logger.debug(f"MainWindow 设置图标 (ICO): {icon_ico}")
        else:
            logger.warning(f"MainWindow 未找到图标: {icon_png}")

        self._setup_ui()
        self._setup_navigation()
        self._setup_status_bar()
        self._init_services()
        logger.debug("主窗口初始化完成 (Lazy Loading Mode)")

    def _get_or_create_page(self, page_name: str):
        """按需获取或创建页面实例 (Factory Pattern + Lazy Loading)"""
        # 1. 检查是否已存在
        if hasattr(self, page_name):
            return getattr(self, page_name)
            
        # 2. 使用工厂创建
        try:
            logger.debug(f"正在惰性加载页面: {page_name} ...")
            page_instance = self.page_factory.create_page(page_name, self)
            
            if not page_instance:
                logger.error(f"页面创建失败: {page_name}")
                return None
            
            # 3. 挂载到 self
            setattr(self, page_name, page_instance)
            
            # 4. 添加到 StackedWidget (如果尚未添加)
            if hasattr(self, 'stackedWidget'):
                # 检查是否已经在 stack 中
                if self.stackedWidget.indexOf(page_instance) == -1:
                    self.stackedWidget.addWidget(page_instance)
                    
            logger.debug(f"页面加载完成: {page_name}")
            return page_instance
        except Exception as e:
            logger.error(f"加载页面异常 {page_name}: {e}", exc_info=True)
            return None
    
    def _init_services(self):
        """初始化服务和事件监听"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.infrastructure.common.event.event_bus import EventBus
            from src.infrastructure.common.event.events import PublishStartedEvent, TaskFailedEvent, PublishCompletedEvent
            
            service_locator = ServiceLocator()
            if service_locator.is_registered(EventBus):
                self.event_bus = service_locator.get(EventBus)
                self.event_bus.subscribe("PublishStartedEvent", self._on_publish_started)
                self.event_bus.subscribe("TaskFailedEvent", self._on_task_failed)
                self.event_bus.subscribe("PublishCompletedEvent", self._on_publish_completed)
                
                logger.debug("主窗口事件监听已注册")
        except Exception as e:
            logger.error(f"初始化主窗口服务失败: {e}")

    def _on_publish_started(self, event):
        """发布开始事件回调"""
        msg = f"正在发布: {getattr(event, 'account_name', '未知账号')}"
        self.show_status_message(msg)

    def _on_publish_completed(self, event):
        """发布完成事件回调"""
        msg = f"发布完成: {getattr(event, 'account_name', '未知账号')}"
        self.show_status_message(msg, 5000)

    def _on_task_failed(self, event):
        """任务失败事件回调"""
        msg = f"任务失败: {getattr(event, 'error', '未知错误')}"
        self.show_status_message(msg, 5000, is_error=True)

    def show_status_message(self, message: str, duration: int = 3000, is_error: bool = False):
        """显示状态信息 (线程安全)"""
        from PySide6.QtCore import QMetaObject, Q_ARG, Qt
        QMetaObject.invokeMethod(self, "_update_status_bar_impl", Qt.QueuedConnection,
                                 Q_ARG(str, message), Q_ARG(int, duration))
        
        if is_error and FLUENT_WIDGETS_AVAILABLE:
             QMetaObject.invokeMethod(self, "_show_error_bar", Qt.QueuedConnection,
                                      Q_ARG(str, message))

    # 定义为 Slot 供 invokeMethod 调用
    @Slot(str, int)
    def _update_status_bar_impl(self, message: str, duration: int):
        if hasattr(self, 'statusBar') and callable(self.statusBar) and self.statusBar():
            self.statusBar().showMessage(message, duration)
        
        # 用户要求移除顶部的蓝色消息状态弹窗功能
        # if self.window():
        #      StateToolTip(
        #          title="",
        #          content=message,
        #          parent=self.window()
        #      ).show()

    @Slot(str)
    def _show_error_bar(self, message: str):
        InfoBar.error(
            title='错误',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self
        )

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        
        # 窗口显示后，设置为最大化（只在首次显示时）
        if not hasattr(self, '_maximized_set'):
            self._maximized_set = True
            logger.debug("窗口显示完成")
        
        # 延迟初始化浏览器页面UI
        QTimer.singleShot(100, self._init_browser_page_ui)
        
        # 强制展开导航栏 (解决默认收起问题)
        QTimer.singleShot(50, lambda: self._force_nav_expand())
        
        # 延迟3秒预热浏览器服务 (Stage 1 Optimization)
        QTimer.singleShot(3000, self._warmup_browser_service)
    
    def _force_nav_expand(self):
        """强制展开导航栏 (安全调用)"""
        try:
            if not hasattr(self, 'navigationInterface'):
                return
                
            nav = self.navigationInterface
            
            # 方法1: 使用 expand() (推荐)
            if hasattr(nav, 'expand'):
                # useAni=False 禁用动画，立即展开
                nav.expand(useAni=False)
                logger.debug("已通过 expand() 强制展开导航栏")
                return
            
            # 方法2: 使用 setDisplayMode
            if hasattr(nav, 'setDisplayMode'):
                from qfluentwidgets import NavigationDisplayMode
                nav.setDisplayMode(NavigationDisplayMode.EXPAND)
                logger.debug("已通过 setDisplayMode() 强制展开导航栏")
                
        except Exception as e:
            logger.warning(f"强制展开导航栏失败: {e}")

    def closeEvent(self, event):
        """主窗口关闭事件"""
        logger.info("主窗口关闭事件触发，开始清理...")
        
        # 1. 清理子页面资源
        if hasattr(self, 'page_factory'):
            for page_name in self.page_factory.get_all_page_names():
                if hasattr(self, page_name):
                    page = getattr(self, page_name)
                    if hasattr(page, 'shutdown'):
                        try:
                            logger.info(f"正在关闭页面资源: {page_name}")
                            page.shutdown()
                        except Exception as e:
                            logger.error(f"关闭页面 {page_name} 失败: {e}")
                            
        # 2. 显式清理 NavigationInterface
        if hasattr(self, 'navigationInterface'):
            try:
                self.navigationInterface.disconnect()
                if hasattr(self, '_cleanup_flow_layouts'):
                    self._cleanup_flow_layouts(self.navigationInterface)
                self.navigationInterface.setParent(None)
                self.navigationInterface.deleteLater()
            except Exception:
                pass
                
        # 3. 全局清理 FlowLayout (包括主窗口自身)
        if hasattr(self, '_cleanup_flow_layouts'):
            self._cleanup_flow_layouts(self)
        
        # 4. 调用父类关闭事件
        try:
            super().closeEvent(event)
        except (RuntimeError, AttributeError):
            event.accept()
        except Exception:
            event.accept()
    
    def _init_browser_page_ui(self):
        """初始化浏览器页面UI（在主窗口显示后调用）"""
        try:
            if hasattr(self, 'browser_page') and self.browser_page:
                if not self.browser_page.is_initialized():
                    logger.info("主窗口显示后，开始初始化浏览器页面UI")
                    self.browser_page._ensure_initialized()
                    logger.info("浏览器页面UI初始化完成")
        except Exception as e:
            logger.error(f"初始化浏览器页面UI失败: {e}", exc_info=True)
            
    def _setup_status_bar(self):
        """设置状态栏"""
        if hasattr(self, 'statusBar') and callable(self.statusBar) and self.statusBar():
            try:
                from .components.status_bar import CustomStatusBar
                self.custom_status_bar = CustomStatusBar(self)
                # 手动定位
                self.custom_status_bar.resize(self.width(), 32)
                self.custom_status_bar.move(0, self.height() - 32)
                self.custom_status_bar.show()
                self.custom_status_bar.raise_()
            except Exception as e:
                logger.error(f"自定义状态栏加载失败: {e}", exc_info=True)
                self.statusBar().showMessage("系统就绪")
        elif FLUENT_WIDGETS_AVAILABLE:
            pass
        else:
            logger.info("当前窗口不支持状态栏，跳过设置")
    
    def _setup_ui(self) -> None:
        """设置UI"""
        self.setWindowTitle("媒小宝")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 768)
        
        # 将窗口居中显示
        from PySide6.QtGui import QScreen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
        
        setTheme(Theme.AUTO)
            # 注：页面切换动画优化移至 _optimize_page_transitions() 方法中

    def _jump_to_feature(self, target_page_name: str):
        """抢占式跳转：点击父级菜单时，直接更新导航栏选中态并切换页面"""
        try:
            # 1. 立即切换页面 (视觉响应优先)
            self.navigate_to(target_page_name)
            
            # 2. 异步展开对应的父级菜单 (避免卡顿)
            # 查找该页面所属的父级容器
            child_to_parent = NavigationConfig.get_child_to_parent_mapping()
            parent_key = child_to_parent.get(target_page_name)
            
            if parent_key:
                QTimer.singleShot(150, lambda: self._expand_nav_item(parent_key))
                
        except Exception as e:
            logger.error(f"跳转失败: {e}")

    def _expand_nav_item(self, object_name: str):
        """展开指定的导航项"""
        item = self._nav_items.get(object_name)
        if item and hasattr(item, 'setExpanded'):
             # 仅当未展开时才展开
            is_expanded = item.isExpanded
            if callable(is_expanded):
                is_expanded = is_expanded()
            
            if not is_expanded:
                item.setExpanded(True, ani=True)

    def _setup_navigation(self) -> None:
        """设置导航栏"""
        # 设置导航栏
        if hasattr(self, 'stackedWidget'):
            self.stackedWidget.currentChanged.connect(self._on_page_changed)
            
        # 尝试修复：关闭亚克力效果，可能会导致背景色差
        if hasattr(self.navigationInterface, 'setAcrylicEnabled'):
            self.navigationInterface.setAcrylicEnabled(False)
            logger.debug("已关闭导航栏亚克力效果以修复背景问题")
        
        # 启用手风琴模式 (Accordion)
        if hasattr(self.navigationInterface, 'setCollapsible'):
            self.navigationInterface.setCollapsible(True)
            logger.debug("已启用导航栏可折叠模式")
        
        # 启用返回顶部 (如果支持)
        if hasattr(self.navigationInterface, 'setReturnToStartPos'):
            self.navigationInterface.setReturnToStartPos(True)
            
        # 彻底移除蓝色选中指示器 - 三层攻击
        self._remove_indicators()

        # ---------------------------------------------------------------------
        # 1. 核心页面 (立即加载)
        # ---------------------------------------------------------------------
        self.workspace_page = self.page_factory.create_page("workspace_page", self)
        self.workspace_page.setObjectName("workspace_page")
        
        # ---------------------------------------------------------------------
        # 2. 构建导航菜单 (Dynamic Navigation Construction)
        # ---------------------------------------------------------------------
        
        # 存储导航项以便后续控制
        self._nav_items = {}
        
        # 获取导航配置列表
        nav_items_config = NavigationConfig.get_items(
            batch_feature=BATCH_FEATURE_AVAILABLE,
            data_center=DATA_CENTER_AVAILABLE,
            interaction=INTERACTION_FEATURE_AVAILABLE,
            subscription=SUBSCRIPTION_PAGE_AVAILABLE
        )
        
        # 递归添加导航项
        for item_conf in nav_items_config:
            self._add_nav_item(item_conf)

        self._setup_nav_width()
        self._setup_accordion_behavior()  # 设置手风琴效果
        self._disable_all_indicators()  # 确保所有导航项指示器被禁用
        self._optimize_page_transitions()  # 优化页面切换动画
        logger.debug("导航栏设置完成 (Config Driven)")

    def _remove_indicators(self):
        """移除导航栏指示器"""
        try:
            panel = getattr(self.navigationInterface, 'panel', None)
            if panel:
                # 1. 直接隐藏指示器 QWidget
                if hasattr(panel, 'indicator') and panel.indicator:
                    panel.indicator.hide()
                    panel.indicator.setMaximumSize(0, 0)
                
                # 2. 禁用指示器动画功能
                if hasattr(panel, 'setIndicatorAnimationEnabled'):
                    panel.setIndicatorAnimationEnabled(False)
                
                # 3. 遍历所有导航项，设置指示器颜色为透明
                from PySide6.QtWidgets import QWidget
                from PySide6.QtGui import QColor
                for item in panel.findChildren(QWidget):
                    if hasattr(item, 'setIndicatorColor'):
                        item.setIndicatorColor(QColor(0, 0, 0, 0), QColor(0, 0, 0, 0))
        except Exception as e:
            logger.warning(f"移除指示器失败: {e}")

    def _add_nav_item(self, conf: dict, parent_key: str = None):
        """递归添加导航项"""
        route_key = conf["route_key"]
        text = conf["text"]
        icon = conf["icon"]
        position = conf.get("position", NavigationItemPosition.TOP)
        selectable = conf.get("selectable", True)
        
        # 决定 onClick
        on_click = None
        if selectable and "children" not in conf: 
             on_click = lambda: self.navigate_to(route_key)
        elif "onClick" in conf:
             on_click = conf["onClick"]
        # [Fix] 即使不可选中，如果是父级容器，也需要响应点击以支持手风琴
        elif not selectable and "children" in conf:
            # 这里先给一个空 lambda，后续在 _setup_accordion_behavior 中会覆盖
            # 但 Fluent 可能会因为 selectable=False 而忽略点击，所以我们尝试强制允许点击但不选中
            pass

        # 添加 Item
        item_widget = None
        
        # 注意 workspace 是 addSubInterface，比较特殊
        if route_key == "workspace_page":
             # workspace_page 已经在前面实例化了
             item_widget = self.addSubInterface(
                 self.workspace_page, icon, text, position
             )
        else:
             item_widget = self.navigationInterface.addItem(
                 routeKey=route_key,
                 icon=icon,
                 text=text,
                 onClick=on_click,
                 selectable=selectable,
                 parentRouteKey=parent_key,
                 position=position
             )
        
        if item_widget:
            self._nav_items[route_key] = item_widget
            
            # 设置默认展开
            if conf.get("expanded", False) and hasattr(item_widget, 'setExpanded'):
                item_widget.setExpanded(True)

        # 处理子级
        if "children" in conf:
            for child in conf["children"]:
                self._add_nav_item(child, parent_key=route_key)
    
    def _setup_accordion_behavior(self):
        """为父级菜单设置手风琴行为：点击一个父级时收起其他父级，并自动导航到第一个子页面"""
        from qfluentwidgets.components.navigation import NavigationTreeWidget
        
        # 定义父级容器及其第一个子页面的映射
        self._parent_containers = NavigationConfig.get_accordion_mapping()
        
        # 统一的动画时长（毫秒）
        ANIMATION_DURATION = 100
        
        # 为每个父级容器连接点击信号，并设置统一的动画时长
        for container_key, first_child_key in self._parent_containers.items():
            container = self._nav_items.get(container_key)
            if container and isinstance(container, NavigationTreeWidget):
                # 设置统一的展开/收起动画时长
                if hasattr(container, 'expandAni'):
                    container.expandAni.setDuration(ANIMATION_DURATION)
                
                # 使用 lambda 闭包捕获当前的 key 值
                container.clicked.connect(
                    lambda checked, ck=container_key, fk=first_child_key: 
                        self._on_parent_clicked(ck, fk)
                )
        
        logger.debug(f"手风琴导航行为已设置，动画时长: {ANIMATION_DURATION}ms")
    
    def _on_parent_clicked(self, clicked_container_key: str, first_child_key: str):
        """处理父级容器点击：分层动画实现优雅过渡
        
        动画时序：
        1. 立即切换到新页面（新菜单的展开由 qfluentwidgets 自动触发，120ms）
        2. 延迟 150ms 后，收起其他展开的菜单（带动画，120ms）
        
        这样新菜单展开大约完成一半时，旧菜单开始收起，形成流畅的层次过渡。
        """
        from PySide6.QtCore import QTimer
        
        try:
            # 1. 立即切换到新页面（新菜单展开动画自动触发）
            self._smooth_navigate(first_child_key)
            
            # 2. 延迟 100ms 后，收起其他展开的菜单（形成层次感）
            QTimer.singleShot(100, lambda: self._collapse_other_menus(clicked_container_key))
            
        except Exception as e:
            logger.warning(f"处理父级菜单点击失败: {e}")
    
    def _collapse_other_menus(self, current_container_key: str):
        """延迟收起其他展开的菜单（带动画）"""
        from qfluentwidgets.components.navigation import NavigationTreeWidget
        
        try:
            for key in self._parent_containers.keys():
                if key != current_container_key:
                    container = self._nav_items.get(key)
                    if container and isinstance(container, NavigationTreeWidget) and container.isExpanded:
                        container.setExpanded(False, ani=True)  # 带动画收起
        except Exception as e:
            logger.debug(f"收起菜单时出错: {e}")
    
    def _smooth_navigate(self, page_name: str):
        """平滑导航到页面（使用优化后的页面切换动画）"""
        try:
            page = self._get_or_create_page(page_name)
            if page:
                # 使用短动画时长（80ms）+ 平滑缓动曲线
                if hasattr(self, 'stackedWidget') and hasattr(self.stackedWidget, 'view'):
                    from PySide6.QtCore import QEasingCurve
                    self.stackedWidget.view.setCurrentWidget(
                        page,
                        False,  # needPopOut
                        True,   # showNextWidgetDirectly
                        80,     # duration (快速切换)
                        QEasingCurve.OutCubic  # 平滑缓动
                    )
                else:
                    self.switchTo(page)
                
                # 更新导航栏高亮
                if hasattr(self, 'navigationInterface'):
                    self.navigationInterface.setCurrentItem(page_name)
                    
                logger.debug(f"平滑导航到: {page_name}")
        except Exception as e:
            logger.warning(f"平滑导航失败: {e}")
    
    def _setup_nav_width(self):
        """设置导航栏宽度"""
        try:
            if hasattr(self, 'navigationInterface'):
                nav = self.navigationInterface
                # 设置展开宽度
                if hasattr(nav, 'setExpandWidth'):
                    nav.setExpandWidth(200)
                    logger.debug("导航栏展开宽度已设置为 200px")
                # 设置默认展开模式
                if hasattr(nav, 'displayMode'):
                    nav.setDisplayMode(NavigationDisplayMode.EXPAND)
                    logger.debug("导航栏已设置为默认展开模式")
                
                # 连接显示模式变更信号
                if hasattr(nav, 'displayModeChanged'):
                    nav.displayModeChanged.connect(self._on_display_mode_changed)
                    logger.debug("已连接导航栏模式变更信号")
                    
        except Exception as e:
            logger.warning(f"设置导航栏宽度及模式失败: {e}")

    def _on_display_mode_changed(self, mode):
        """处理导航栏显示模式变更"""
        from qfluentwidgets import NavigationDisplayMode
        from qfluentwidgets.components.navigation import NavigationTreeWidget
        
        try:
            # 当导航栏收起到 Mini 模式时，折叠所有手风琴菜单
            if mode == NavigationDisplayMode.MINIMAL or mode == NavigationDisplayMode.COMPACT:
                # 折叠所有父级容器
                if hasattr(self, '_parent_containers'):
                    for container_key in self._parent_containers.keys():
                        container = self._nav_items.get(container_key)
                        if container and isinstance(container, NavigationTreeWidget):
                            is_expanded = container.isExpanded
                            if callable(is_expanded):
                                is_expanded = is_expanded()
                            if is_expanded:
                                container.setExpanded(False, ani=False)  # 无动画快速折叠
                    logger.debug("导航栏收起，已折叠所有手风琴菜单")
            
            # 强制刷新导航面板，解决收缩/展开时的文字残留或重叠问题
            if hasattr(self, 'navigationInterface'):
                self.navigationInterface.update()
                
                # 如果有 panel 对象，也可以尝试刷新它
                panel = getattr(self.navigationInterface, 'panel', None)
                if panel:
                    panel.update()
                    # 某些情况下 adjustSize 也能解决布局问题
                    # panel.adjustSize() # 移除此行，可能导致收起时布局异常

                    
            logger.debug(f"导航栏显示模式已变更: {mode}")
        except Exception as e:
            logger.warning(f"处理导航栏模式变更失败: {e}")
    
    def _optimize_page_transitions(self):
        """优化页面切换动画，使其更快速流畅"""
        try:
            if not hasattr(self, 'stackedWidget'):
                return
            
            sw = self.stackedWidget
            
            # FluentWindow 的 stackedWidget 是 StackedWidget 包装器
            # 真正的动画组件是 stackedWidget.view (PopUpAniStackedWidget)
            if hasattr(sw, 'view'):
                popup_widget = sw.view
                
            # 优化 PopUpAniStackedWidget 的动画参数
            if hasattr(popup_widget, 'aniInfos') and popup_widget.aniInfos:
                for info in popup_widget.aniInfos:
                    if hasattr(info, 'deltaY'):
                        info.deltaY = 20  # 减小滑动距离 (默认76)
                    if hasattr(info, 'deltaX'):
                        info.deltaX = 0   # 禁用水平滑动
                logger.debug(f"已优化页面动画参数: 滑动距离20px")
            
            # Monkey Patch StackedWidget.setCurrentWidget 逻辑已移除
            # 改为重写 MainWindow.switchTo 方法实现
            
        except Exception as e:
            logger.warning(f"优化页面切换动画失败: {e}")

    def switchTo(self, interface, popOut=False):
        """重写切换页面方法，支持自定义动画时长"""
        from PySide6.QtWidgets import QAbstractScrollArea
        if hasattr(self, 'stackedWidget'):
            # 先滚动到顶部
            if isinstance(interface, QAbstractScrollArea):
                interface.verticalScrollBar().setValue(0)
            
            # 直接调用内部 view 的 setCurrentWidget，支持 duration 参数
            # PopUpAniStackedWidget.setCurrentWidget(widget, needPopOut, showNextWidgetDirectly, duration, easing)
            if hasattr(self.stackedWidget, 'view'):
                from PySide6.QtCore import QEasingCurve
                self.stackedWidget.view.setCurrentWidget(
                    interface, 
                    popOut,  # needPopOut
                    False,   # showNextWidgetDirectly
                    80,      # duration (快速切换)
                    QEasingCurve.OutCubic  # easing
                )
            else:
                self.stackedWidget.setCurrentWidget(interface, popOut)
        else:
            super().switchTo(interface, popOut)
    
    def _disable_all_indicators(self):
        """禁用所有导航项的蓝色选中指示器，并增强选中背景"""
        try:
            from PySide6.QtWidgets import QWidget
            from PySide6.QtGui import QColor, QPainter
            from PySide6.QtCore import QPoint, QRect, Qt, QRectF
            
            panel = getattr(self.navigationInterface, 'panel', None)
            if not panel:
                logger.warning("未找到 navigationInterface.panel")
                return
            
            # 1. 再次隐藏动画指示器（防止被意外重置）
            if hasattr(panel, 'indicator') and panel.indicator:
                panel.indicator.hide()
                panel.indicator.setMaximumSize(0, 0)
            
            # 2. 遍历所有导航项，将指示器颜色设为透明，并增强选中背景
            transparent = QColor(0, 0, 0, 0)
            # 定义更醒目的选中背景色 (参考网易UU - 浅蓝色背景)
            SELECTED_BG_LIGHT = QColor(0, 120, 212, 30)  # 浅蓝色背景 (亮色模式)
            SELECTED_BG_DARK = QColor(0, 120, 212, 40)   # 蓝色背景 (暗色模式)
            
            for item in panel.findChildren(QWidget):
                if hasattr(item, 'setIndicatorColor'):
                    item.setIndicatorColor(transparent, transparent)
                    
                    # Monkey patch: 增强选中背景的可见性（仅在展开状态下）
                    # 保存原始的 paintEvent
                    if not hasattr(item, '_original_paintEvent'):
                        item._original_paintEvent = item.paintEvent
                        item._selected_bg_light = SELECTED_BG_LIGHT
                        item._selected_bg_dark = SELECTED_BG_DARK
                        
                        def make_enhanced_paint(widget):
                            def enhanced_paintEvent(e):
                                # 仅在展开状态且选中时才绘制增强背景
                                # 收起状态下不绘制，避免位置异常
                                is_compact = getattr(widget, 'isCompacted', False)
                                is_selected = getattr(widget, 'isSelected', False)
                                
                                if is_selected and not is_compact:
                                    painter = QPainter(widget)
                                    painter.setRenderHint(QPainter.Antialiasing)
                                    painter.setPen(Qt.NoPen)
                                    
                                    # 根据主题选择背景色
                                    from qfluentwidgets import isDarkTheme
                                    bg_color = widget._selected_bg_dark if isDarkTheme() else widget._selected_bg_light
                                    painter.setBrush(bg_color)
                                    painter.drawRoundedRect(widget.rect(), 5, 5)
                                    painter.end()
                                
                                # 调用原始绘制
                                widget._original_paintEvent(e)
                            return enhanced_paintEvent
                        
                        item.paintEvent = make_enhanced_paint(item)
                
                # 同时处理嵌套的 itemWidget
                if hasattr(item, 'itemWidget') and hasattr(item.itemWidget, 'setIndicatorColor'):
                    item.itemWidget.setIndicatorColor(transparent, transparent)
                    
                    iw = item.itemWidget
                    if not hasattr(iw, '_original_paintEvent'):
                        iw._original_paintEvent = iw.paintEvent
                        iw._selected_bg_light = SELECTED_BG_LIGHT
                        iw._selected_bg_dark = SELECTED_BG_DARK
                        
                        def make_enhanced_paint_iw(widget):
                            def enhanced_paintEvent(e):
                                # 仅在展开状态且选中时才绘制增强背景
                                is_compact = getattr(widget, 'isCompacted', False)
                                is_selected = getattr(widget, 'isSelected', False)
                                
                                if is_selected and not is_compact:
                                    painter = QPainter(widget)
                                    painter.setRenderHint(QPainter.Antialiasing)
                                    painter.setPen(Qt.NoPen)
                                    from qfluentwidgets import isDarkTheme
                                    bg_color = widget._selected_bg_dark if isDarkTheme() else widget._selected_bg_light
                                    painter.setBrush(bg_color)
                                    painter.drawRoundedRect(widget.rect(), 5, 5)
                                    painter.end()
                                widget._original_paintEvent(e)
                            return enhanced_paintEvent
                        
                        iw.paintEvent = make_enhanced_paint_iw(iw)
            
            logger.debug("所有导航项指示器已禁用，选中背景已增强（导航设置完成后）")
        except Exception as e:
            logger.warning(f"禁用导航指示器失败: {e}")

    def _on_page_changed(self, index: int):
        """页面切换回调 - 已优化为同步执行，无延迟切换"""
        try:
            current_widget = self.stackedWidget.widget(index)
            if not current_widget:
                return
                
            current_name = current_widget.objectName()
            
            # 子页面到父容器的映射
            child_to_parent = {
                # 发布管理
                "publish_list_page": "publish_container",
                "publish_records_page": "publish_container",
                # 视频发布
                "single_publish_page": "video_publish_container",
                "batch_publish_page": "video_publish_container",
                # 图文发布
                "image_single_publish_page": "image_publish_container",
                "image_batch_publish_page": "image_batch_publish_container",
                # 评论互动
                "comment_page": "interaction_container",
                "private_message_page": "interaction_container",
            }
            
            if not hasattr(self, 'navigationInterface'):
                return
            
            current_parent_key = child_to_parent.get(current_name)
            
            if current_parent_key:
                # 有父级的页面：同步执行所有操作
                # 1. 设置当前项选中
                self.navigationInterface.setCurrentItem(current_name)
                
                # 2. 展开当前父级 + 折叠其他父级 (同步执行)
                # self._update_accordion_state(current_parent_key) # Removed to fix accordion conflict
                pass
            else:
                # 无父级的独立页面
                self.navigationInterface.setCurrentItem(current_name)
                # 折叠所有父级
                # self._update_accordion_state(None) # Removed to fix accordion conflict
                pass

        except Exception as e:
            logger.error(f"处理页面切换逻辑失败: {e}", exc_info=True)


    def _update_accordion_state(self, current_parent_key):
        """更新侧边栏手风琴状态"""
        try:
            # 定义所有父级容器
            all_containers = [
                "publish_container",
                "video_publish_container",
                "image_publish_container",
                "interaction_container"
            ]
            
            # 1. 先确保当前父级展开 (优先展示用户关心的内容)
            if current_parent_key:
                item = self._nav_items.get(current_parent_key)
                if item:
                    # 获取当前状态 (兼容属性访问)
                    is_expanded = item.isExpanded
                    if callable(is_expanded):
                        is_expanded = is_expanded()
                    
                    if not is_expanded:
                        # 开启优雅的展开动画
                        item.setExpanded(True, ani=True)
            
            # 2. 再折叠其他父级
            for container_name in all_containers:
                if container_name == current_parent_key:
                    continue
                    
                item = self._nav_items.get(container_name)
                if item:
                     # 获取当前状态
                    is_expanded = item.isExpanded
                    if callable(is_expanded):
                        is_expanded = is_expanded()
                        
                    if is_expanded:
                        # 开启优雅的折叠动画
                        item.setExpanded(False, ani=True)
                        
        except Exception as e:
            logger.warning(f"更新手风琴状态失败: {e}")

    def navigate_to(self, page_name: str):
        """导航到指定页面 (支持 Lazy Loading)
        
        Args:
            page_name: 页面名称 (routeKey)
        """
        try:
            # 1. 尝试获取或创建页面
            page = self._get_or_create_page(page_name)
            
            if page:
                # 2. 切换到页面
                self.switchTo(page)
                
                # 3. 更新导航栏高亮
                if hasattr(self, 'navigationInterface'):
                    self.navigationInterface.setCurrentItem(page_name)
                          
                logger.debug(f"已导航到页面: {page_name}")
            else:
                logger.warning(f"无法导航，页面不存在: {page_name}")
        except Exception as e:
            logger.error(f"导航到页面失败 {page_name}: {e}", exc_info=True)
    
        # 初始化事件总线订阅
        self._init_event_subscriptions()

    def _init_event_subscriptions(self):
        """初始化全局事件订阅"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.infrastructure.common.event.event_bus import EventBus
            from src.infrastructure.common.event.events import GlobalToastEvent
            
            service_locator = ServiceLocator()
            if service_locator.is_registered(EventBus):
                event_bus = service_locator.get(EventBus)
                
                # 订阅全局 Toast 事件
                event_bus.subscribe(
                    GlobalToastEvent.__name__, 
                    self._on_global_toast,
                    priority=0 # 最高优先级，确保UI响应
                )
                logger.debug("全局事件订阅成功")
        except Exception as e:
            logger.error(f"初始化事件订阅失败: {e}")

    def _on_global_toast(self, event):
        """处理全局 Toast 通知"""
        # 确保在主线程执行 UI 操作
        # 如果是异步回调，qasync 会自动处理，但 InfoBar 最好在主线程
        from qfluentwidgets import InfoBar, InfoBarPosition
        
        title = getattr(event, 'title', '通知')
        content = getattr(event, 'content', '')
        toast_type = getattr(event, 'toast_type', 'info')
        
        if toast_type == 'success':
            InfoBar.success(title=title, content=content, parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)
        elif toast_type == 'warning':
            InfoBar.warning(title=title, content=content, parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)
        elif toast_type == 'error':
            InfoBar.error(title=title, content=content, parent=self, position=InfoBarPosition.TOP_RIGHT, duration=5000)
        else:
            InfoBar.info(title=title, content=content, parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)

    @qasync.asyncSlot()
    async def _warmup_browser_service(self):
        """浏览器服务预热 (3秒延迟启动)"""
        try:
            from src.infrastructure.browser.browser_manager import UndetectedBrowserManager
            await UndetectedBrowserManager.warmup_environment()
        except Exception as e:
            logger.warning(f"Browser warmup failed: {e}")


    
    def _cleanup_flow_layouts(self, widget):
        """递归清理 widget 中的 FlowLayout 事件过滤器"""
        try:
            from qfluentwidgets.components.layout import FlowLayout
            from PySide6.QtWidgets import QWidget
            
            # 检查 widget 的 layout
            layout = widget.layout()
            if layout is not None:
                if isinstance(layout, FlowLayout):
                    # 清除 FlowLayout 的 items 列表以避免访问已删除对象
                    try:
                        if hasattr(layout, '_items'):
                            for item in layout._items:
                                try:
                                    if item and item.widget():
                                        item.widget().removeEventFilter(layout)
                                except RuntimeError:
                                    pass
                            layout._items.clear()
                    except (RuntimeError, AttributeError):
                        pass
            
            # 递归处理子组件
            for child in widget.findChildren(QWidget):
                try:
                    child_layout = child.layout()
                    if child_layout is not None:
                        if isinstance(child_layout, FlowLayout) and hasattr(child_layout, '_items'):
                            child_layout._items.clear()
                except RuntimeError:
                    pass
                    
        except Exception:
            pass

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        if hasattr(self, 'custom_status_bar') and self.custom_status_bar:
            self.custom_status_bar.resize(self.width(), 32)
            self.custom_status_bar.move(0, self.height() - 32)
            self.custom_status_bar.raise_()
