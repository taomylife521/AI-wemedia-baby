"""
统计卡片组件
文件路径：src/ui/components/statistics_card.py
功能：显示单一统计指标的卡片，包含图标、标题、数值和描述
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from qfluentwidgets import (
    CardWidget, CaptionLabel, TitleLabel, BodyLabel, 
    IconWidget, FluentIconBase, FluentIcon
)

class StatisticsCard(CardWidget):
    """统计卡片组件"""
    
    def __init__(
        self, 
        title: str, 
        value: str, 
        desc: str, 
        icon: Optional[FluentIconBase] = None,
        parent: Optional[QWidget] = None
    ):
        """初始化统计卡片"""
        super().__init__(parent)
        self.icon_enum = icon
        
        self.setFixedHeight(80) # 降低高度
        self.setMinimumWidth(240)
        
        self._init_ui(title, value, desc)
        
        # 增加左侧彩色边框点缀
        if self.icon_enum == FluentIcon.PEOPLE:
            self.setStyleSheet("CardWidget { border-left: 4px solid #0078D4; }")
        elif self.icon_enum == FluentIcon.SEND:
            self.setStyleSheet("CardWidget { border-left: 4px solid #107C10; }")
        elif self.icon_enum == FluentIcon.FOLDER:
            self.setStyleSheet("CardWidget { border-left: 4px solid #FFB900; }")
        elif self.icon_enum == FluentIcon.ACCEPT:
            self.setStyleSheet("CardWidget { border-left: 4px solid #5C2D91; }")


    def _init_ui(self, title: str, value: str, desc: str):
        """初始化UI (水平布局)"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 24, 16)
        layout.setSpacing(16)
        
        # 1. 图标 (左侧)
        if self.icon_enum:
            self.icon_widget = IconWidget(self.icon_enum, self)
            self.icon_widget.setFixedSize(24, 24) # 稍大的图标
            layout.addWidget(self.icon_widget, 0, Qt.AlignVCenter)
        
        # 2. 文本区域 (标题 + 描述)
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignVCenter)
        
        self.title_label = BodyLabel(title, self)
        self.title_label.setStyleSheet("color: #333333; font-weight: 600; font-size: 14px;")
        
        self.desc_label = CaptionLabel(desc, self)
        self.desc_label.setStyleSheet("color: #757575; font-size: 12px;")
        
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        
        layout.addWidget(text_container)
        
        layout.addStretch(1) # 中间弹簧
        
        # 3. 数值 (右侧，大号字体)
        self.value_label = TitleLabel(value, self)
        # 尝试从主题管理器获取颜色，如果失败则使用默认
        text_color = "#0078D4"
        try:
            from ..styles.theme_manager import theme_manager
            text_color = theme_manager.get_theme_color()
        except ImportError:
            pass
            
        self.value_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {text_color}; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.value_label, 0, Qt.AlignVCenter)
    
    def set_value(self, value: str):
        """更新数值"""
        self.value_label.setText(str(value))
        
    def set_description(self, desc: str):
        """更新描述"""
        self.desc_label.setText(desc)
