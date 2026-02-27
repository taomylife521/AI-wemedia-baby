"""
基础页面类
文件路径：src/ui/pages/base_page.py
功能：提供所有页面的基类，统一页面布局和样式
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QAbstractItemView
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QShowEvent
import logging

# 导入 PySide6-Fluent-Widgets 组件
from qfluentwidgets import (
    ScrollArea, InfoBar, InfoBarPosition, TableWidget,
    CardWidget, SubtitleLabel, BodyLabel, isDarkTheme
)
FLUENT_WIDGETS_AVAILABLE = True

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """基础页面类
    
    所有页面都应继承此类，提供统一的布局和样式。
    使用 PySide6-Fluent-Widgets 组件构建现代化 UI。
    """
    
    def __init__(self, title: str, parent: Optional[QWidget] = None, enable_scroll: bool = False):
        """初始化页面
        
        Args:
            title: 页面标题
            parent: 父组件
            enable_scroll: 是否启用全局滚动 (解决小屏幕遮挡问题)
        """
        super().__init__(parent)
        self.title = title
        self.enable_scroll = enable_scroll
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        if self.enable_scroll:
            # 1. 启用滚动：创建根布局包裹 ScrollArea
            self.root_layout = QVBoxLayout(self)
            self.root_layout.setContentsMargins(0, 0, 0, 0)
            self.root_layout.setSpacing(0)
            
            self.scroll_area = ScrollArea(self)
            # 背景透明，边框无
            self.scroll_area.setStyleSheet("QScrollArea {background: transparent; border: none;}")
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # 滚动容器
            self.scroll_widget = QWidget()
            self.scroll_widget.setObjectName("scroll_widget")
            self.scroll_widget.setStyleSheet(".QWidget{background: transparent;}")
            
            # 主布局作用于 scroll_widget
            self.main_layout = QVBoxLayout(self.scroll_widget)
            self.main_layout.setContentsMargins(24, 16, 24, 16)
            self.main_layout.setSpacing(16)
            
            self.scroll_area.setWidget(self.scroll_widget)
            self.root_layout.addWidget(self.scroll_area)
        else:
            # 2. 不启用滚动：传统方式
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(24, 16, 24, 16)
            self.main_layout.setSpacing(16)
        
        # 内容区域布局
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用 stretch 让内容区域可以扩展
        self.main_layout.addLayout(self.content_layout, stretch=1)
    
    def _setup_table_style(self, table):
        """统一设置表格样式
        
        Args:
            table: TableWidget 实例
        """

        
        # 设置表格基础样式
        table.setBorderVisible(True)
        table.setBorderRadius(8)
        table.setWordWrap(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 设置表头
        header = table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
    
    def show_info(self, title: str, content: str, duration: int = 3000):
        """显示信息提示
        
        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.info(title, content, duration=duration, 
                        position=InfoBarPosition.TOP, parent=self)
    
    def show_success(self, title: str, content: str, duration: int = 3000):
        """显示成功提示
        
        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.success(title, content, duration=duration,
                          position=InfoBarPosition.TOP, parent=self)
    
    def show_warning(self, title: str, content: str, duration: int = 3000):
        """显示警告提示
        
        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.warning(title, content, duration=duration,
                          position=InfoBarPosition.TOP, parent=self)
    
    def show_error(self, title: str, content: str, duration: int = 5000):
        """显示错误提示
        
        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.error(title, content, duration=duration,
                        position=InfoBarPosition.TOP, parent=self)
    
    def showEvent(self, event: QShowEvent):
        """页面显示事件，优化切换时的渲染"""
        # 禁用更新，避免切换时的闪动
        self.setUpdatesEnabled(False)
        super().showEvent(event)
        # 短暂延迟后重新启用更新，确保内容正确显示
        QTimer.singleShot(10, lambda: self.setUpdatesEnabled(True))
