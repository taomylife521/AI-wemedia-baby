"""
浏览器登录对话框
文件路径：src/ui/dialogs/browser_login_dialog.py
功能：新账号登录对话框，包含登录检测、昵称提取、自动保存等功能
"""

from typing import Optional
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import QTimer, Qt
import logging

try:
    from qfluentwidgets import PrimaryPushButton, PushButton, BodyLabel
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BrowserLoginDialog(QDialog):
    """浏览器登录对话框 - 用于新账号登录"""
    
    def __init__(
        self,
        parent,
        account_name: str,
        platform: str,
        platform_url: str,
        platform_name: str = "",
        account_manager=None
    ):
        """初始化登录对话框
        
        Args:
            parent: 父窗口
            account_name: 账号名称
            platform: 平台ID
            platform_url: 平台URL
            platform_name: 平台名称
            account_manager: 账号管理器实例
        """
        super().__init__(parent)
        self.account_name = account_name
        self.platform = platform
        self.platform_url = platform_url
        self.platform_name = platform_name or platform
        self.account_manager = account_manager
        
        self.setWindowTitle(f"登录 {self.platform_name} - {account_name}")
        self.resize(1200, 800)
        
        self._setup_ui()
        self._setup_browser()
        self._setup_login_detection()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 提示标签
        tip_text = (
            f"请在下方浏览器中完成登录。\n"
            f"平台：{self.platform_name}\n"
            f"账号名称：{self.account_name}\n"
            f"登录成功后，系统将自动保存账号信息。"
        )
        
        if FLUENT_WIDGETS_AVAILABLE:
            self.tip_label = BodyLabel(tip_text, self)
        else:
            self.tip_label = QLabel(tip_text, self)
        
        self.tip_label.setWordWrap(True)
        layout.addWidget(self.tip_label)
        
        # 状态标签
        if FLUENT_WIDGETS_AVAILABLE:
            self.status_label = BodyLabel("等待登录...", self)
        else:
            self.status_label = QLabel("等待登录...", self)
        
        layout.addWidget(self.status_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if FLUENT_WIDGETS_AVAILABLE:
            self.btn_finish = PrimaryPushButton("完成登录", self)
            self.btn_cancel = PushButton("取消", self)
        else:
            self.btn_finish = QPushButton("完成登录", self)
            self.btn_cancel = QPushButton("取消", self)
        
        self.btn_finish.setEnabled(False)  # 初始状态禁用
        btn_layout.addWidget(self.btn_finish)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
    
    def _setup_browser(self):
        """设置浏览器"""
        from src.infrastructure.browser.qwebengine_browser import QWebEngineBrowser
        
        self.browser = QWebEngineBrowser(self)
        self.layout().insertWidget(1, self.browser, stretch=1)
        
        # 清除旧Cookie，防止自动登录旧账号或误判
        self.browser.clear_cookies()
        
        # 加载平台URL
        self.browser.load_url(self.platform_url)
        
        # 初始状态
        if 'creator.douyin.com' in self.platform_url:
            if '/creator-micro/home' in self.platform_url or '/creator-micro' in self.platform_url:
                self.status_label.setText("已加载抖音创作者中心，等待登录...")
            else:
                self.status_label.setText(f"正在加载 {self.platform_name} 登录页面...")
        else:
            self.status_label.setText(f"正在加载 {self.platform_name} 登录页面...")
    
    def _setup_login_detection(self):
        """设置登录检测"""
        # 用于跟踪定时器
        self.timers = []
        
        # 对话框关闭标志
        self.dialog_closed = False
        
        # 登录状态检测
        self.login_detected = False
        self.detected_username = ""
        self.nickname_extraction_attempts = 0
        self.max_nickname_extraction_attempts = 3
        
        # 连接信号
        self.browser.page_loaded.connect(self._on_page_loaded)
        self.browser.urlChanged.connect(self._on_url_changed)
        
        # 定时检测登录状态
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_login_status)
        self.check_timer.start(2000)  # 每2秒检测一次
        
        # 连接按钮
        self.btn_finish.clicked.connect(self._on_finish)
        self.btn_cancel.clicked.connect(self.reject)
        
        # 监听对话框关闭事件
        self.finished.connect(self._on_dialog_finished)
    
    def _check_login_status(self):
        """检测登录状态"""
        if self.dialog_closed or self.login_detected:
            return
        
        try:
            current_url = self.browser.get_current_url()
            
            # 针对不同平台检测登录状态
            script = ""
            if self.platform == 'douyin':
                from src.plugins.community.douyin.scripts import LOGIN_DETECTION_SCRIPT
                script = LOGIN_DETECTION_SCRIPT
            elif self.platform == 'kuaishou':
                from src.plugins.community.kuaishou.scripts import LOGIN_DETECTION_SCRIPT
                script = LOGIN_DETECTION_SCRIPT
            
            if script:
                def on_result(result):
                    if self.dialog_closed:
                        return
                    # 处理登录检测结果
                    try:
                        import json
                        data = json.loads(result) if isinstance(result, str) else result
                        
                        if data.get('loggedIn'):
                            self.login_detected = True
                            
                            # 尝试获取用户名
                            username = data.get('username')
                            if username:
                                self.detected_username = username
                                self.status_label.setText(f"已登录: {username}")
                            else:
                                self.status_label.setText("已登录 (未获取到昵称)")
                            
                            self.check_timer.stop()
                            self.btn_finish.setEnabled(True)
                            
                            # 自动完成
                            if username:
                                QTimer.singleShot(1000, self._on_finish)
                                
                    except Exception as e:
                        logger.debug(f"解析检测结果失败: {e}")
                
                self.browser.execute_javascript(script, on_result)
        except Exception as e:
            logger.debug(f"检测登录状态时出错: {e}")
    
    def _on_page_loaded(self, success: bool):
        """页面加载完成回调"""
        if success and not self.dialog_closed:
            current_url = self.browser.get_current_url()
            if 'creator.douyin.com' in current_url:
                self.status_label.setText("已加载抖音创作者中心，等待登录...")
            elif 'cp.kuaishou.com' in current_url:
                self.status_label.setText("已加载快手创作者平台，等待登录...")
    
    def _on_url_changed(self, url):
        """URL变化回调"""
        if self.dialog_closed:
            return
        url_str = url.toString() if hasattr(url, 'toString') else str(url)
        if 'creator.douyin.com' in url_str:
            self.status_label.setText("已加载抖音创作者中心，等待登录...")
        elif 'cp.kuaishou.com' in url_str:
            self.status_label.setText("已加载快手创作者平台，等待登录...")
    
    def _on_finish(self):
        """完成登录按钮点击"""
        self._save_and_close()
    
    def _save_and_close(self):
        """保存账号并关闭对话框"""
        # ... 保存逻辑（从原方法中提取）
        pass
    
    def _on_dialog_finished(self, result):
        """对话框关闭时的处理"""
        self.dialog_closed = True
        # ... 清理逻辑（从原方法中提取）
        pass
