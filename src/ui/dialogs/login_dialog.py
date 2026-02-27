"""
登录对话框
文件路径：src/ui/dialogs/login_dialog.py
功能：用户登录界面，使用 PySide6-Fluent-Widgets 组件
"""

from typing import Optional
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
import logging

# 导入 PySide6-Fluent-Widgets 组件
try:
    from qfluentwidgets import (
        MessageBoxBase, SubtitleLabel, BodyLabel, LineEdit, PasswordLineEdit,
        PrimaryPushButton, PushButton, CheckBox, InfoBar, InfoBarPosition,
        FluentIcon, CardWidget
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False
    from PySide6.QtWidgets import QDialog

logger = logging.getLogger(__name__)


class LoginDialog(MessageBoxBase if FLUENT_WIDGETS_AVAILABLE else QWidget):
    """登录对话框 - 使用 PySide6-Fluent-Widgets MessageBoxBase"""
    
    # 登录成功信号
    login_success = Signal(dict)  # 传递user_info
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化登录对话框"""
        super().__init__(parent)
        self.user_auth = None
        self._user_info = None
        self._init_services()
        self._setup_ui()
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.services.auth import UserAuth
            
            self.user_auth = UserAuth()
            logger.debug("登录服务初始化成功")
        except Exception as e:
            logger.warning(f"初始化登录服务失败: {e}")
    
    def _setup_ui(self):
        """设置UI"""
        if not FLUENT_WIDGETS_AVAILABLE:
            return
        
        # 设置对话框大小
        self.widget.setMinimumWidth(400)
        
        # 标题
        title = SubtitleLabel("登录", self.widget)
        self.viewLayout.addWidget(title)
        
        # 说明文字
        desc = BodyLabel("请输入您的账号和密码", self.widget)
        desc.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
        self.viewLayout.addWidget(desc)
        
        self.viewLayout.addSpacing(16)
        
        # 用户名输入
        self.username_input = LineEdit(self.widget)
        self.username_input.setPlaceholderText("用户名（3-20位字母、数字或下划线）")
        self.username_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.username_input)
        
        self.viewLayout.addSpacing(12)
        
        # 密码输入
        self.password_input = PasswordLineEdit(self.widget)
        self.password_input.setPlaceholderText("密码（8-20位）")
        self.viewLayout.addWidget(self.password_input)
        
        self.viewLayout.addSpacing(8)
        
        # 记住我
        self.remember_checkbox = CheckBox("记住我（7天内免登录）", self.widget)
        self.viewLayout.addWidget(self.remember_checkbox)
        
        self.viewLayout.addSpacing(16)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        btn_forgot = PushButton("忘记密码", self.widget)
        btn_forgot.clicked.connect(self._on_forgot_password)
        btn_layout.addWidget(btn_forgot)
        
        btn_register = PushButton("注册账号", self.widget)
        btn_register.clicked.connect(self._on_register)
        btn_layout.addWidget(btn_register)
        
        btn_layout.addStretch()
        self.viewLayout.addLayout(btn_layout)
        
        # 设置按钮文字
        self.yesButton.setText("登录")
        self.cancelButton.setText("取消")
        
        # 绑定登录按钮
        self.yesButton.clicked.disconnect()  # 先断开默认连接
        self.yesButton.clicked.connect(self._on_login)
        
        # 回车键登录
        self.password_input.returnPressed.connect(self._on_login)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
    
    def _on_login(self):
        """处理登录"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember_me = self.remember_checkbox.isChecked()
        
        if not username:
            InfoBar.warning(
                title="输入错误",
                content="请输入用户名",
                duration=2000,
                parent=self
            )
            self.username_input.setFocus()
            return
        
        if not password:
            InfoBar.warning(
                title="输入错误",
                content="请输入密码",
                duration=2000,
                parent=self
            )
            self.password_input.setFocus()
            return
        
        if not self.user_auth:
            # 如果服务未初始化，尝试模拟登录（开发模式）
            logger.warning("登录服务未初始化，使用模拟登录")
            self._user_info = {
                'id': 1,
                'username': username,
                'email': f'{username}@example.com',
                'role': 'user'
            }
            InfoBar.success(
                title="登录成功",
                content=f"欢迎，{username}！（开发模式）",
                duration=2000,
                parent=self
            )
            self.login_success.emit(self._user_info)
            self.accept()
            return
        
        # 执行登录
        try:
            import asyncio
            # 注意：由于这是 UI 线程调用异步方法，这里使用一个临时的同步等待
            # 理想情况下应该使用 qasync 驱动
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 使用包装器执行登录
            async def do_login():
                user_info = await self.user_auth.login(username, password)
                if user_info:
                    return {'success': True, 'user_info': user_info}
                return {'success': False, 'message': '用户名或密码错误'}
            
            result = loop.run_until_complete(do_login())
            
            if result.get('success'):
                self._user_info = result.get('user_info', {})
                InfoBar.success(
                    title="登录成功",
                    content=f"欢迎回来，{username}！",
                    duration=2000,
                    parent=self
                )
                self.login_success.emit(self._user_info)
                self.accept()
            else:
                InfoBar.error(
                    title="登录失败",
                    content=result.get('message', '用户名或密码错误'),
                    duration=3000,
                    parent=self
                )
                self.password_input.clear()
                self.password_input.setFocus()
        except Exception as e:
            logger.error(f"登录失败: {e}", exc_info=True)
            InfoBar.error(
                title="登录失败",
                content=f"登录出错: {str(e)}",
                duration=3000,
                parent=self
            )
    
    def _on_register(self):
        """打开注册对话框"""
        try:
            from .register_dialog import RegisterDialog
            
            self.hide()
            register_dialog = RegisterDialog(self.parent())
            if register_dialog.exec():
                # 注册成功，自动填充用户名
                if hasattr(register_dialog, 'get_username'):
                    self.username_input.setText(register_dialog.get_username())
                self.password_input.setFocus()
            self.show()
        except Exception as e:
            logger.error(f"打开注册对话框失败: {e}")
    
    def _on_forgot_password(self):
        """打开密码重置对话框"""
        try:
            from .password_reset_dialog import PasswordResetDialog
            
            self.hide()
            reset_dialog = PasswordResetDialog(self.parent())
            reset_dialog.exec()
            self.show()
        except Exception as e:
            logger.error(f"打开密码重置对话框失败: {e}")
    
    def get_user_info(self) -> Optional[dict]:
        """获取用户信息（登录成功后）"""
        return self._user_info
