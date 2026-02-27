# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

# 尝试导入 fluent widgets
try:
    from qfluentwidgets import PrimaryPushButton, PushButton
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

from src.infrastructure.browser.qwebengine_browser import QWebEngineBrowser

class BrowserLoginDialog(QDialog):
    """浏览器登录对话框"""
    
    def __init__(self, account_name: str, platform_name: str, platform_url: str, parent=None):
        super().__init__(parent)
        self.account_name = account_name
        self.platform_name = platform_name
        self.platform_url = platform_url
        self.cookies = None
        
        self.setWindowTitle(f"登录 {account_name} - {platform_name}")
        self.resize(1000, 700)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 提示标签
        tip_text = (
            f"请在下方浏览器中完成登录，登录成功后点击「完成登录」按钮。\n"
            f"平台：{self.platform_name}\n"
            f"账号名称：{self.account_name}"
        )
        tip_label = QLabel(tip_text, self)
        layout.addWidget(tip_label)
        
        # 创建浏览器
        self.browser = QWebEngineBrowser(self)
        self.browser.load_url(self.platform_url)
        layout.addWidget(self.browser)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        if FLUENT_WIDGETS_AVAILABLE:
            self.btn_finish = PrimaryPushButton("完成登录", self)
            self.btn_cancel = PushButton("取消", self)
        else:
            self.btn_finish = QPushButton("完成登录", self)
            self.btn_cancel = QPushButton("取消", self)
            
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_finish)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        # 连接信号
        self.btn_finish.clicked.connect(self._on_finish)
        self.btn_cancel.clicked.connect(self.reject)
        
    def _on_finish(self):
        """点击完成登录"""
        if self.browser:
            self.cookies = self.browser.extract_cookies_dict()
        self.accept()
        
    def get_cookies(self):
        """获取提取的Cookies"""
        return self.cookies
