from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient

class SkeletonItem(QWidget):
    """单个骨架屏元素（支持呼吸动画）"""
    
    def __init__(self, parent=None, radius=4):
        super().__init__(parent)
        self.radius = radius
        self._color_alpha = 255
        self.setFixedHeight(20)  # 默认高度
        
        # 呼吸动画定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.direction = -1  # -1: 变淡, 1: 变深
        self.alpha = 100
        self.min_alpha = 50
        self.max_alpha = 150
        
        self.timer.start(50)  # 20fps

    def update_animation(self):
        self.alpha += self.direction * 5
        if self.alpha <= self.min_alpha:
            self.alpha = self.min_alpha
            self.direction = 1
        elif self.alpha >= self.max_alpha:
            self.alpha = self.max_alpha
            self.direction = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        # 浅灰色背景
        color = QColor(200, 200, 200, self.alpha)
        
        # 适配暗色模式 (简单判断，实际应从 ThemeManager 获取)
        # 这里简单处理，如果父背景色较深则调整
        # try:
        #     from qfluentwidgets import isDarkTheme
        #     if isDarkTheme():
        #         color = QColor(80, 80, 80, self.alpha)
        # except:
        #     pass
            
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)


class SkeletonTable(QWidget):
    """骨架屏表格（模拟列表加载状态）"""
    
    def __init__(self, rows=5, columns=4, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.columns = columns
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 模拟表头
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        header_layout.setContentsMargins(24, 0, 24, 0)
        for _ in range(self.columns):
            item = SkeletonItem(self)
            item.setFixedHeight(24)
            header_layout.addWidget(item)
        layout.addLayout(header_layout)
        
        layout.addSpacing(4)
        
        # 模拟数据行
        for _ in range(self.rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(16)
            row_layout.setContentsMargins(24, 0, 24, 0)
            
            # 第一列通常是头像或复选框，窄一点
            avatar = SkeletonItem(self, radius=16)
            avatar.setFixedSize(32, 32)
            row_layout.addWidget(avatar)
            
            # 其他列
            for _ in range(self.columns - 1):
                item = SkeletonItem(self)
                item.setFixedHeight(16)
                row_layout.addWidget(item)
                
            layout.addLayout(row_layout)
            
        layout.addStretch()
