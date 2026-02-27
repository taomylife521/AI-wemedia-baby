"""
快速操作卡片组件
文件路径：src/ui/components/quick_action_card.py
功能：显示主要操作的可点击卡片，包含大图标、标题和描述
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from qfluentwidgets import (
    CardWidget, IconWidget, FluentIconBase, BodyLabel, CaptionLabel
)

class QuickActionCard(CardWidget):
    """快速操作卡片"""
    
    clicked = Signal()
    
    def __init__(
        self,
        icon: FluentIconBase,
        title: str,
        desc: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # 图标
        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(32, 32)
        layout.addWidget(self.icon_widget, 0, Qt.AlignCenter)
        
        # 标题
        self.title_label = BodyLabel(title, self)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(self.title_label, 0, Qt.AlignCenter)
        
        # 描述
        self.desc_label = CaptionLabel(desc, self)
        self.desc_label.setStyleSheet("color: #757575;")
        self.desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.desc_label, 0, Qt.AlignCenter)
        
    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.clicked.emit()
