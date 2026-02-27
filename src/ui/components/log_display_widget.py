"""
日志显示组件
文件路径：src/ui/components/log_display_widget.py
功能：通用的日志显示组件，支持多日志源监听、彩色日志显示
"""

import logging
from typing import List, Optional
from PySide6.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor

try:
    from qfluentwidgets import CardWidget, StrongBodyLabel
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False
    class CardWidget(QWidget): pass
    class StrongBodyLabel(QLabel): pass


class GuiLogHandler(logging.Handler, QObject):
    """GUI 日志处理器，将日志信号发射到界面"""
    log_signal = Signal(str, str)  # msg, levelname

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg, record.levelname)


class LogDisplayWidget(CardWidget if FLUENT_WIDGETS_AVAILABLE else QWidget):
    """日志显示组件"""
    
    def __init__(self, title: str = "运行日志", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.log_handler = GuiLogHandler()
        self.listening_loggers = []
        self._setup_ui(title)
        
        # 连接信号
        self.log_handler.log_signal.connect(self.append_log)

    def _setup_ui(self, title_text: str):
        layout = QVBoxLayout(self)
        
        # 标题
        if FLUENT_WIDGETS_AVAILABLE:
            title_label = StrongBodyLabel(title_text, self)
        else:
            title_label = QLabel(title_text, self)
            title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(title_label)
            
        # 文本框
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMinimumHeight(200)
        self.log_text_edit.setFont(QFont("Consolas", 9))
        self.log_text_edit.setObjectName("LogTextEdit") 
        # Note: 样式由全局 QSS (ThemeManager) 控制
        
        layout.addWidget(self.log_text_edit)

    def start_logging(self, logger_names: List[str], level=logging.INFO):
        """开始监听指定日志"""
        for name in logger_names:
            if name not in self.listening_loggers:
                logger = logging.getLogger(name)
                logger.addHandler(self.log_handler)
                logger.setLevel(level)
                self.listening_loggers.append(name)
    
    def stop_logging(self):
        """停止监听所有日志"""
        for name in self.listening_loggers:
            logger = logging.getLogger(name)
            logger.removeHandler(self.log_handler)
        self.listening_loggers.clear()

    @Slot(str, str)
    def append_log(self, msg: str, level: str = "INFO"):
        """追加日志"""
        # color logic based on level
        color = None
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "#ff9800" # Orange
        
        if color:
            self.append_html(f'<span style="color: {color};">{msg}</span>')
        else:
            self.log_text_edit.append(msg)
            
        self._auto_scroll()

    def append_text(self, text: str):
        """追加普通文本"""
        self.log_text_edit.append(text)
        self._auto_scroll()

    def append_error(self, text: str):
        """追加错误文本 (红色)"""
        self.append_html(f'<br><span style="color: red; font-weight: bold;">❌ {text}</span><br>')

    def append_success(self, text: str):
        """追加成功文本 (绿色)"""
        # 适配深色模式，绿色不宜太刺眼
        self.append_html(f'<span style="color: #2e7d32; font-weight: bold;">✅ {text}</span>')

    def append_html(self, html: str):
        """追加 HTML 内容"""
        cursor = self.log_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text_edit.setTextCursor(cursor)
        self.log_text_edit.insertHtml(html)
        self.log_text_edit.insertPlainText("\n") # 换行
        self._auto_scroll()
        
    def clear_logs(self):
        """清空日志"""
        self.log_text_edit.clear()

    def _auto_scroll(self):
        """自动滚动到底部"""
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def closeEvent(self, event):
        """组件关闭时自动停止监听"""
        self.stop_logging()
        super().closeEvent(event)
