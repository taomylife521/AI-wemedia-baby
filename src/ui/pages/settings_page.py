"""
设置页面（优化版）
文件路径：src/ui/pages/settings_page.py
功能：设置页面，显示应用设置、账户管理和关于信息，使用 SettingCard 组件优化布局
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
import logging

# 导入 PySide6-Fluent-Widgets 组件
from qfluentwidgets import (
    FluentIcon, InfoBar, MessageBox,
    ScrollArea, ExpandLayout, SettingCardGroup,
    SwitchSettingCard, OptionsSettingCard, PushSettingCard, PrimaryPushSettingCard,
    CustomColorSettingCard, HyperlinkCard,
    Theme, setTheme, isDarkTheme,
    SettingCard, ComboBox, SwitchButton, TitleLabel, InfoBarPosition
)
FLUENT_WIDGETS_AVAILABLE = True

from .base_page import BasePage
from ..styles import ThemeManager, ThemeMode, get_theme_manager
from src.infrastructure.common.path_manager import PathManager
from src.infrastructure.common.di.service_locator import ServiceLocator
from src.infrastructure.common.cache.cache_manager import CacheManager
from src.infrastructure.common.config.config_center import ConfigCenter

logger = logging.getLogger(__name__)


class SettingsPage(BasePage):
    """设置页面 - 使用 PySide6-Fluent-Widgets 标准组件"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化设置页面"""
        # BasePage.__init__ calls self._setup_ui(), so we don't need to call it manually
        super().__init__("设置", parent)
        
    def _setup_ui(self):
        """设置UI界面"""
        # Call super first to initialize main_layout and content_layout
        super()._setup_ui()
        


        # 1. 创建滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        
        # 视觉美化：透明背景
        # 使用 stylesheet 设置透明，避免使用 setAttribute(Qt.WA_TranslucentBackground) 导致渲染异常
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        self.scroll_widget.setObjectName("scrollWidget")
        self.scroll_widget.setStyleSheet("#scrollWidget { background-color: transparent; }")
        
        # 2. 滚动区域布局
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.expand_layout.setContentsMargins(36, 20, 36, 36)
        self.expand_layout.setSpacing(28)
        
        # 3. 添加页头标题
        self.title_label = TitleLabel("设置", self.scroll_widget)
        self.expand_layout.addWidget(self.title_label)
        
        # 3. 添加到主布局 (BasePage 的 content_layout)
        self.content_layout.addWidget(self.scroll_area)
        
        # 4. 创建各个设置组
        self._create_theme_group()
        self._create_browser_group()
        self._create_data_group()
        self._create_system_group()
        self._create_about_group()
        
    def _create_theme_group(self):
        """创建外观设置组"""
        self.theme_group = SettingCardGroup("外观设置", self.scroll_widget)
        
        # 主题模式
        self.theme_card = SettingCard(
            FluentIcon.BRUSH,
            "主题模式",
            "选择应用的主题颜色模式",
            parent=self.theme_group
        )
        
        self.theme_combo = ComboBox(self.theme_card)
        self.theme_combo.addItems(["跟随系统", "浅色模式", "深色模式"])
        self.theme_combo.setMinimumWidth(120)
        
        # 初始化选中状态
        theme_mode = get_theme_manager().get_theme_mode()
        if theme_mode == ThemeMode.AUTO:
            self.theme_combo.setCurrentIndex(0)
        elif theme_mode == ThemeMode.LIGHT:
            self.theme_combo.setCurrentIndex(1)
        elif theme_mode == ThemeMode.DARK:
            self.theme_combo.setCurrentIndex(2)
            
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        # 添加控件到卡片布局
        self.theme_card.hBoxLayout.addWidget(self.theme_combo, 0, Qt.AlignRight)
        self.theme_card.hBoxLayout.addSpacing(16)
        
        self.theme_group.addSettingCard(self.theme_card)
        self.expand_layout.addWidget(self.theme_group)
        
    def _create_browser_group(self):
        """创建浏览器配置组"""
        self.browser_group = SettingCardGroup("浏览器配置", self.scroll_widget)
        
        # 浏览器方案
        self.browser_scheme_card = SettingCard(
            FluentIcon.GLOBE,
            "浏览器方案",
            "选择自动化任务使用的浏览器方案",
            parent=self.browser_group
        )
        
        self.browser_scheme_combo = ComboBox(self.browser_scheme_card)
        self.browser_scheme_combo.addItems(["Playwright + QWebEngineView (混合)", "Undetected Playwright (纯净)"])
        self.browser_scheme_combo.setMinimumWidth(250)
        
        # 加载配置
        try:
            config_center = ServiceLocator().get(ConfigCenter)
            app_config = config_center.get_app_config()
            current_scheme = app_config.get("browser_scheme", "playwright")
            if current_scheme == "playwright":
                self.browser_scheme_combo.setCurrentIndex(1)
            else:
                self.browser_scheme_combo.setCurrentIndex(0)
        except Exception:
            self.browser_scheme_combo.setCurrentIndex(1)
            
        self.browser_scheme_combo.currentIndexChanged.connect(self._on_browser_scheme_changed)
        
        self.browser_scheme_card.hBoxLayout.addWidget(self.browser_scheme_combo, 0, Qt.AlignRight)
        self.browser_scheme_card.hBoxLayout.addSpacing(16)
        
        self.browser_group.addSettingCard(self.browser_scheme_card)
        self.expand_layout.addWidget(self.browser_group)
        
    def _create_data_group(self):
        """创建数据管理组"""
        self.data_group = SettingCardGroup("数据管理", self.scroll_widget)
        
        # 数据目录
        data_dir = str(PathManager.get_app_data_dir())
        self.data_dir_card = PushSettingCard(
            "打开目录",
            FluentIcon.FOLDER,
            "数据存储目录",
            data_dir,
            self.data_group
        )
        self.data_dir_card.clicked.connect(self._on_open_data_dir)
        
        # 清理缓存
        self.clear_cache_card = PrimaryPushSettingCard(
            "清理缓存",
            FluentIcon.DELETE,
            "应用缓存管理",
            "清理临时文件、缩略图和会话数据以释放空间",
            self.data_group
        )
        # 调整按钮样式为红色警戒色 (如果 PrimaryPushSettingCard 支持 setCustomBackgroundColor 最好，否则保持默认 Primary 颜色)
        # qfluentwidgets 的 Primary 颜色通常是主题色。为了强调危险，我们可以手动设置样式，但保持一致性也行。
        self.clear_cache_card.clicked.connect(self._on_clear_cache)
        
        self.data_group.addSettingCard(self.data_dir_card)
        self.data_group.addSettingCard(self.clear_cache_card)
        self.expand_layout.addWidget(self.data_group)
        
    def _create_system_group(self):
        """创建系统选项组"""
        self.system_group = SettingCardGroup("系统选项", self.scroll_widget)
        
        # 开机自启动
        self.auto_start_card = SettingCard(
            FluentIcon.POWER_BUTTON,
            "开机自启动",
            "启用后，系统启动时自动运行本软件",
            parent=self.system_group
        )
        self.auto_start_switch = SwitchButton(self.auto_start_card)
        self.auto_start_switch.setOnText("开")
        self.auto_start_switch.setOffText("关")
        self.auto_start_card.hBoxLayout.addWidget(self.auto_start_switch, 0, Qt.AlignRight)
        self.auto_start_card.hBoxLayout.addSpacing(16)
        
        # 最小化到托盘
        self.tray_card = SettingCard(
            FluentIcon.COMPLETED, 
            "关闭时最小化到托盘",
            "启用后，点击关闭按钮时最小化到系统托盘",
            parent=self.system_group
        )
        self.tray_switch = SwitchButton(self.tray_card)
        self.tray_switch.setOnText("开")
        self.tray_switch.setOffText("关")
        self.tray_card.hBoxLayout.addWidget(self.tray_switch, 0, Qt.AlignRight)
        self.tray_card.hBoxLayout.addSpacing(16)
        
        # 自动更新
        self.auto_update_card = SettingCard(
            FluentIcon.UPDATE,
            "自动检查更新",
            "启用后，启动时自动检查软件更新",
            parent=self.system_group
        )
        self.auto_update_switch = SwitchButton(self.auto_update_card)
        self.auto_update_switch.setChecked(True)
        self.auto_update_switch.setOnText("开")
        self.auto_update_switch.setOffText("关")
        self.auto_update_card.hBoxLayout.addWidget(self.auto_update_switch, 0, Qt.AlignRight)
        self.auto_update_card.hBoxLayout.addSpacing(16)
        
        self.system_group.addSettingCard(self.auto_start_card)
        self.system_group.addSettingCard(self.tray_card)
        self.system_group.addSettingCard(self.auto_update_card)
        self.expand_layout.addWidget(self.system_group)
        
    def _create_about_group(self):
        """创建关于组"""
        self.about_group = SettingCardGroup("关于", self.scroll_widget)
        
        # 检查更新
        self.check_update_card = PushSettingCard(
            "检查更新",
            FluentIcon.INFO,
            "媒小宝",
            "版本 1.0.0 (Build 20260102) © 2026 媒小宝团队",
            self.about_group
        )
        self.check_update_card.clicked.connect(self._on_check_update)
        
        # 反馈
        self.feedback_card = PushSettingCard(
            "反馈问题",
            FluentIcon.FEEDBACK,
            "帮助与反馈",
            "访问 GitHub 提交 Issue 或获取帮助",
            self.about_group
        )
        self.feedback_card.clicked.connect(self._on_feedback)
        
        self.about_group.addSettingCard(self.check_update_card)
        self.about_group.addSettingCard(self.feedback_card)
        self.expand_layout.addWidget(self.about_group)

    # --- Callbacks ---
    
    def _on_theme_changed(self, index: int):
        """主题切换"""
        text = self.theme_combo.currentText()
        
        try:
            theme_mgr = get_theme_manager()
            if text == "跟随系统":
                theme_mgr.set_theme_mode(ThemeMode.AUTO)
            elif text == "浅色模式":
                theme_mgr.set_theme_mode(ThemeMode.LIGHT)
            elif text == "深色模式":
                theme_mgr.set_theme_mode(ThemeMode.DARK)
            
            self.show_success("主题已更改", "新的主题设置已生效")
        except Exception as e:
            logger.error(f"切换主题失败: {e}")

    def _on_browser_scheme_changed(self, index: int):
        """浏览器方案切换"""
        settings_text = self.browser_scheme_combo.currentText()
        try:
            scheme = "playwright" if "Undetected" in settings_text else "mixed"
            
            config_center = ServiceLocator().get(ConfigCenter)
            
            import asyncio
            async def update_config():
                try:
                    app_config = config_center.get_app_config()
                    if not isinstance(app_config, dict):
                        app_config = {}
                    app_config["browser_scheme"] = scheme
                    await config_center.update("app_config", app_config)
                    logger.info(f"浏览器方案已更新为: {scheme}")
                except Exception as e:
                    logger.error(f"保存配置失败: {e}")

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(update_config())
                else:
                    asyncio.run(update_config())
            except Exception as e:
                logger.error(f"调度配置更新任务失败: {e}")
                
            self.show_success("设置已保存", "浏览器方案已更新，重启软件后生效")
            
        except Exception as e:
            logger.error(f"切换浏览器方案失败: {e}")
            self.show_error("错误", "保存设置失败")

    def _on_open_data_dir(self):
        """打开数据目录"""
        try:
            data_dir = PathManager.get_app_data_dir()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir)))
        except Exception as e:
            self.show_error("错误", f"无法打开目录: {e}")

    def _on_clear_cache(self):
        """清理缓存"""
        w = MessageBox("确认清理", "确定要清理所有应用缓存吗？\n这将删除临时文件、历史日志和浏览器环境以释放空间。\n(已登录账号的凭证不会被删除)", self.window())
        if w.exec():
            # 1. 显示“清理中”提示
            info_bar = InfoBar.info(
                title="正在清理",
                content="由于涉及日志和临时文件，清理可能需要几秒钟，请稍候...",
                orient=Qt.Horizontal,
                isClosable=False,
                duration=-1, # 永不关闭直到手动移除
                position=InfoBarPosition.TOP,
                parent=self
            )
            
            async def clear_task():
                try:
                    cache_mgr = ServiceLocator().get(CacheManager)
                    # 执行深度清理并获取结果
                    results = await cache_mgr.clear()
                    
                    # 2. 移除加载中提示
                    info_bar.close()
                    
                    # 3. 构造结果摘要
                    summary = []
                    if results.get("l2_cleared", 0) > 0:
                        summary.append(f"数据缓存: {results['l2_cleared']} 个文件")
                    if results.get("logs_cleared", 0) > 0:
                        summary.append(f"运行日志: {results['logs_cleared']} 个文件")
                    if results.get("browser_temp_cleared", 0) > 0:
                        summary.append(f"临时环境: {results['browser_temp_cleared']} 个目录")
                    
                    content = "应用缓存已深度清理。"
                    if summary:
                        content += "\n详细: " + ", ".join(summary)
                    
                    self.show_success("清理成功", content)
                except Exception as e:
                    if info_bar: info_bar.close()
                    self.show_error("错误", f"清理缓存过程中发生异常: {e}")
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(clear_task())
                else:
                    asyncio.run(clear_task())
            except Exception as e:
                if info_bar: info_bar.close()
                logger.error(f"启动清理任务失败: {e}")
                self.show_error("启动失败", "无法启动异步清理任务")

    def _on_check_update(self):
        self.show_info("检查更新", "正在检查最新版本...")
    
    def _on_feedback(self):
        import webbrowser
        webbrowser.open("https://github.com/wemedia-baby/wemedia-baby/issues")
