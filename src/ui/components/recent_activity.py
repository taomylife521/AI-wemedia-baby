"""
最近活动列表组件
文件路径：src/ui/components/recent_activity.py
功能：显示最近的活动列表（如发布记录、任务状态等）
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from qfluentwidgets import (
    CardWidget, IconWidget, FluentIconBase, BodyLabel, CaptionLabel,
    FluentIcon, SubtitleLabel
)

class ActivityItemWidget(QWidget):
    """单条活动记录"""
    
    def __init__(self, title: str, subtitle: str, time_str: str, icon: FluentIconBase, status_color: str = "#666666", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # 1. 图标容器 (带背景)
        icon_container = QWidget(self)
        icon_container.setFixedSize(40, 40)
        icon_container.setStyleSheet(f"background-color: {status_color}22; border-radius: 20px;") # 10%透明度背景
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        self.icon_widget = IconWidget(icon, icon_container)
        self.icon_widget.setFixedSize(20, 20)
        # 设置图标颜色
        self.icon_widget.setStyleSheet(f"color: {status_color};") # 设置图标颜色无效，IconWidget通常跟随主题，需特殊处理
        # 这里简单起见，IconWidget不支持直接setColor，除非使用IconInfo，或者自定义
        
        icon_layout.addWidget(self.icon_widget, 0, Qt.AlignCenter)
        layout.addWidget(icon_container)
        
        # 2. 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        self.title_label = BodyLabel(title, self)
        self.title_label.setStyleSheet("font-weight: 500;")
        
        self.subtitle_label = CaptionLabel(subtitle, self)
        self.subtitle_label.setStyleSheet("color: #757575;")
        
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.subtitle_label)
        layout.addLayout(content_layout)
        
        # 3. 时间
        time_label = CaptionLabel(time_str, self)
        time_label.setStyleSheet("color: #999999;")
        layout.addWidget(time_label, 0, Qt.AlignRight | Qt.AlignTop)


class RecentActivityWidget(CardWidget):
    """最近活动列表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题
        self.title_label = SubtitleLabel("最近活动", self)
        layout.addWidget(self.title_label)
        
        # 列表容器
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(0)
        layout.addLayout(self.list_layout)
        
        # 空状态提示
        self.empty_label = CaptionLabel("暂无活动记录", self)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; margin: 20px;")
        layout.addWidget(self.empty_label)
        
    def set_activities(self, activities: List[Dict[str, Any]]):
        """设置活动数据
        
        Args:
            activities: 列表，每项包含:
                 - title: 标题
                 - subtitle: 副标题
                 - time: 时间
                 - icon: FluentIcon枚举 (可选)
                 - status: 'success' | 'failed' | 'info' (决定颜色)
        """
        # 清除旧数据
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not activities:
            self.empty_label.setVisible(True)
            return
            
        self.empty_label.setVisible(False)
        
        for activity in activities:
            # 确定颜色
            status = activity.get('status', 'info')
            if status == 'success':
                color = "#107C10" # 绿色
                icon = activity.get('icon', FluentIcon.ACCEPT)
            elif status == 'failed':
                color = "#E81123" # 红色
                icon = activity.get('icon', FluentIcon.CANCEL)
            else:
                color = "#0078D4" # 蓝色
                icon = activity.get('icon', FluentIcon.INFO)
            
            item = ActivityItemWidget(
                title=activity.get('title', '未知活动'),
                subtitle=activity.get('subtitle', ''),
                time_str=activity.get('time', ''),
                icon=icon,
                status_color=color,
                parent=self
            )
            self.list_layout.addWidget(item)
            
        self.list_layout.addStretch()
