"""
浏览器标签栏组件
文件路径：src/ui/components/browser_tab_bar.py
功能：自定义标签栏，支持标签切换、关闭、新建（Chrome风格）
"""

from typing import Optional, Dict
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QLinearGradient, QPainterPath
import logging

try:
    from qfluentwidgets import PushButton as FluentPushButton
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TabButton(QWidget):
    """Chrome风格标签按钮"""
    
    clicked = Signal(int)
    close_requested = Signal(int)
    
    # 颜色配置
    # 颜色配置（默认为浅色，初始化时会根据主题更新）
    COLORS = {
        'active_bg': QColor(255, 255, 255),
        'inactive_bg': QColor(222, 225, 230),
        'hover_bg': QColor(235, 238, 242),
        'text': QColor(32, 33, 36),
        'text_inactive': QColor(95, 99, 104),
        'close_hover': QColor(232, 234, 237),
        'close_icon': QColor(95, 99, 104),
        'border': QColor(218, 220, 224),
    }

    def _update_colors(self):
        """根据主题更新颜色"""
        try:
            from qfluentwidgets import isDarkTheme
            dark = isDarkTheme()
        except ImportError:
            dark = False
            
        if dark:
            self.COLORS = {
                'active_bg': QColor(45, 45, 45),
                'inactive_bg': QColor(32, 32, 32),
                'hover_bg': QColor(38, 38, 38),
                'text': QColor(255, 255, 255),
                'text_inactive': QColor(160, 160, 160),
                'close_hover': QColor(60, 60, 60),
                'close_icon': QColor(160, 160, 160),
                'border': QColor(60, 60, 60),
            }
        else:
            self.COLORS = {
                'active_bg': QColor(255, 255, 255),
                'inactive_bg': QColor(222, 225, 230),
                'hover_bg': QColor(235, 238, 242),
                'text': QColor(32, 33, 36),
                'text_inactive': QColor(95, 99, 104),
                'close_hover': QColor(232, 234, 237),
                'close_icon': QColor(95, 99, 104),
                'border': QColor(218, 220, 224),
            }
    
    def __init__(self, tab_id: int, tab_name: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.tab_name = tab_name
        self.is_active = is_active
        self._is_hovered = False
        self._close_hovered = False
        
        self.setFixedHeight(36)
        self.setMinimumWidth(100)
        self.setMaximumWidth(240)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
        # 初始化实例级颜色字典
        self._colors_cache = self.COLORS.copy()
        self._update_colors()
        
    def _update_colors(self):
        """根据主题更新颜色"""
        try:
            from qfluentwidgets import isDarkTheme
            dark = isDarkTheme()
        except ImportError:
            dark = False
            
        # 使用实例变量 self._colors_cache
        if dark:
            self._colors_cache = {
                'active_bg': QColor(45, 45, 45),
                'inactive_bg': QColor(32, 32, 32),
                'hover_bg': QColor(38, 38, 38),
                'text': QColor(255, 255, 255),
                'text_inactive': QColor(160, 160, 160),
                'close_hover': QColor(60, 60, 60),
                'close_icon': QColor(160, 160, 160),
                'border': QColor(60, 60, 60),
            }
        else:
            self._colors_cache = {
                'active_bg': QColor(255, 255, 255),
                'inactive_bg': QColor(222, 225, 230),
                'hover_bg': QColor(235, 238, 242),
                'text': QColor(32, 33, 36),
                'text_inactive': QColor(95, 99, 104),
                'close_hover': QColor(232, 234, 237),
                'close_icon': QColor(95, 99, 104),
                'border': QColor(218, 220, 224),
            }

    def set_active(self, active: bool):
        self.is_active = active
        self.update()
    
    def update_name(self, name: str):
        self.tab_name = name
        self.update()
    
    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._close_hovered = False
        self.update()
        super().leaveEvent(event)
    
    def mouseMoveEvent(self, event):
        # 检测关闭按钮悬停
        close_rect = self._get_close_rect()
        was_close_hovered = self._close_hovered
        self._close_hovered = close_rect.contains(event.pos())
        if was_close_hovered != self._close_hovered:
            self.update()
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            close_rect = self._get_close_rect()
            if close_rect.contains(event.pos()):
                self.close_requested.emit(self.tab_id)
                event.accept()
                return
            self.clicked.emit(self.tab_id)
        super().mousePressEvent(event)
    
    def _get_close_rect(self):
        """获取关闭按钮区域"""
        from PySide6.QtCore import QRect
        return QRect(self.width() - 28, 8, 20, 20)
    
    def paintEvent(self, event):
        self._update_colors() # 每次绘制前更新颜色，以支持实时主题切换
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景
        if self.is_active:
            bg_color = self._colors_cache['active_bg']
        elif self._is_hovered:
            bg_color = self._colors_cache['hover_bg']
        else:
            bg_color = self._colors_cache['inactive_bg']
        
        # 绘制圆角标签背景
        path = QPainterPath()
        rect = self.rect().adjusted(2, 2, -2, 0 if self.is_active else -2)
        path.addRoundedRect(rect, 8, 8)
        painter.fillPath(path, bg_color)
        
        # 活动标签底部连接
        if self.is_active:
            painter.fillRect(2, self.height() - 4, self.width() - 4, 4, bg_color)
        
        # 文本
        painter.setPen(self._colors_cache['text'] if self.is_active else self._colors_cache['text_inactive'])
        font = QFont("Microsoft YaHei", 9)
        font.setWeight(QFont.Medium if self.is_active else QFont.Normal)
        painter.setFont(font)
        
        text_rect = self.rect().adjusted(12, 0, -32, 0)
        text = painter.fontMetrics().elidedText(self.tab_name, Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        
        # 关闭按钮
        close_rect = self._get_close_rect()
        if self._close_hovered:
            painter.setBrush(self._colors_cache['close_hover'])
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(close_rect)
        
        # 关闭图标 (X)
        painter.setPen(QPen(self._colors_cache['close_icon'], 1.5))
        cx, cy = close_rect.center().x(), close_rect.center().y()
        painter.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
        painter.drawLine(cx + 4, cy - 4, cx - 4, cy + 4)


class BrowserTabBar(QWidget):
    """Chrome风格浏览器标签栏"""
    
    tab_clicked = Signal(int)
    tab_close_requested = Signal(int)
    new_tab_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tabs: Dict[int, TabButton] = {}
        self.active_tab_id: Optional[int] = None
        
        self.setFixedHeight(40)
        self.setObjectName("BrowserTabBar")
        self.setAttribute(Qt.WA_StyledBackground, True) # 允许使用样式表设置背景
        self._is_dark = None  # 用于跟踪主题状态
        self._setup_ui()
        self._apply_style()

    def paintEvent(self, event):
        """绘制事件，用于检测主题变化并绘制背景"""
        # 支持样式表背景绘制
        from PySide6.QtWidgets import QStyle, QStyleOption
        from PySide6.QtGui import QPainter
        
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)
        
        try:
            from qfluentwidgets import isDarkTheme
            current_dark = isDarkTheme()
            if self._is_dark != current_dark:
                self._apply_style()
        except Exception:
            pass
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标签滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        # 标签容器
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(2)
        self.tabs_layout.addStretch()
        
        self.scroll_area.setWidget(self.tabs_container)
        layout.addWidget(self.scroll_area, stretch=1)
        
        # 新建标签按钮
        self.btn_new_tab = QPushButton("+", self)
        self.btn_new_tab.setFixedSize(28, 28)
        self.btn_new_tab.setToolTip("新建标签页")
        self.btn_new_tab.clicked.connect(self.new_tab_requested.emit)
        self.btn_new_tab.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_new_tab)
    
    def _apply_style(self):
        try:
            from qfluentwidgets import isDarkTheme
            dark = isDarkTheme()
        except ImportError:
            dark = False
            
        self._is_dark = dark
        
        if dark:
            # 深色模式样式
            self.setStyleSheet("""
                BrowserTabBar {
                    background-color: #202020;
                    border-bottom: 1px solid #3c3c3c;
                }
                QScrollArea {
                    background: transparent;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 14px;
                    font-size: 18px;
                    font-weight: bold;
                    color: #cfcfcf;
                }
                QPushButton:hover {
                    background-color: #3e3e3e;
                }
            """)
        else:
            # 浅色模式样式
            self.setStyleSheet("""
                BrowserTabBar {
                    background-color: #ffffff;
                    border-bottom: 1px solid #DADCE0;
                }
                QScrollArea {
                    background: transparent;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 14px;
                    font-size: 18px;
                    font-weight: bold;
                    color: #5F6368;
                }
                QPushButton:hover {
                    background-color: #E8EAED;
                }
            """)
    
    def add_tab(self, tab_id: int, tab_name: str, set_active: bool = True):
        if tab_id in self.tabs:
            return
        
        tab_button = TabButton(tab_id, tab_name, is_active=False, parent=self.tabs_container)
        tab_button.clicked.connect(self._on_tab_clicked)
        tab_button.close_requested.connect(self.tab_close_requested.emit)
        
        self.tabs[tab_id] = tab_button
        # 插入到 stretch 之前
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, tab_button)
        
        if set_active:
            self.set_active_tab(tab_id)
        
        logger.info(f"标签栏添加标签: {tab_name} (ID: {tab_id})")
    
    def remove_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        
        tab_button = self.tabs[tab_id]
        self.tabs_layout.removeWidget(tab_button)
        tab_button.deleteLater()
        del self.tabs[tab_id]
        
        if self.active_tab_id == tab_id:
            if self.tabs:
                next_tab_id = next(iter(self.tabs.keys()))
                self.set_active_tab(next_tab_id)
            else:
                self.active_tab_id = None
    
    def set_active_tab(self, tab_id: int):
        if tab_id not in self.tabs:
            return
        
        if self.active_tab_id and self.active_tab_id in self.tabs:
            self.tabs[self.active_tab_id].set_active(False)
        
        self.active_tab_id = tab_id
        self.tabs[tab_id].set_active(True)
    
    def update_tab_name(self, tab_id: int, new_name: str):
        if tab_id in self.tabs:
            self.tabs[tab_id].update_name(new_name)
    
    def _on_tab_clicked(self, tab_id: int):
        self.set_active_tab(tab_id)
        self.tab_clicked.emit(tab_id)
    
    def get_active_tab_id(self) -> Optional[int]:
        return self.active_tab_id
