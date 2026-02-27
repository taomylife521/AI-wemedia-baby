"""
注册对话框
文件路径：src/ui/dialogs/register_dialog.py
功能：用户注册界面，使用 PySide6-Fluent-Widgets 组件
"""

from typing import Optional
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
import logging

# 导入 PySide6-Fluent-Widgets 组件
try:
    from qfluentwidgets import (
        MessageBoxBase, SubtitleLabel, BodyLabel, LineEdit, PasswordLineEdit,
        PrimaryPushButton, PushButton, InfoBar, InfoBarPosition
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False
    from PySide6.QtWidgets import QDialog

logger = logging.getLogger(__name__)


class RegisterDialog(MessageBoxBase if FLUENT_WIDGETS_AVAILABLE else QWidget):
    """注册对话框 - 使用 PySide6-Fluent-Widgets MessageBoxBase"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化注册对话框"""
        super().__init__(parent)
        self.user_auth = None
        self._username = None
        self._init_services()
        self._setup_ui()
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.services.auth import UserAuth
            
            self.user_auth = UserAuth()
            logger.debug("注册服务初始化成功")
        except Exception as e:
            logger.warning(f"初始化注册服务失败: {e}")
    
    def _setup_ui(self):
        """设置UI"""
        if not FLUENT_WIDGETS_AVAILABLE:
            return
        
        # 设置对话框大小
        self.widget.setMinimumWidth(420)
        
        # 标题
        title = SubtitleLabel("创建账号", self.widget)
        self.viewLayout.addWidget(title)
        
        # 说明文字
        desc = BodyLabel("请填写以下信息完成注册", self.widget)
        desc.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
        self.viewLayout.addWidget(desc)
        
        self.viewLayout.addSpacing(16)
        
        # 用户名输入
        self.username_input = LineEdit(self.widget)
        self.username_input.setPlaceholderText("用户名（3-20位字母、数字或下划线）")
        self.username_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.username_input)
        
        self.viewLayout.addSpacing(10)
        
        # 邮箱输入
        self.email_input = LineEdit(self.widget)
        self.email_input.setPlaceholderText("邮箱地址")
        self.email_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.email_input)
        
        self.viewLayout.addSpacing(10)
        
        # 密码输入
        self.password_input = PasswordLineEdit(self.widget)
        self.password_input.setPlaceholderText("密码（8-20位，含字母+数字+特殊符号）")
        self.viewLayout.addWidget(self.password_input)
        
        self.viewLayout.addSpacing(10)
        
        # 确认密码输入
        self.confirm_password_input = PasswordLineEdit(self.widget)
        self.confirm_password_input.setPlaceholderText("确认密码")
        self.viewLayout.addWidget(self.confirm_password_input)
        
        self.viewLayout.addSpacing(16)
        
        # 设置按钮文字
        self.yesButton.setText("注册")
        self.cancelButton.setText("取消")
        
        # 绑定注册按钮
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._on_register)
        
        # 回车键注册
        self.confirm_password_input.returnPressed.connect(self._on_register)
    
    def _validate_input(self) -> tuple[bool, str]:
        """验证输入
        
        Returns:
            (是否有效, 错误信息)
        """
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not username:
            self.username_input.setFocus()
            return False, "请输入用户名"
        
        if len(username) < 3 or len(username) > 20:
            self.username_input.setFocus()
            return False, "用户名长度应为3-20位"
        
        if not email:
            self.email_input.setFocus()
            return False, "请输入邮箱"
        
        if '@' not in email or '.' not in email:
            self.email_input.setFocus()
            return False, "请输入有效的邮箱地址"
        
        if not password:
            self.password_input.setFocus()
            return False, "请输入密码"
        
        if len(password) < 8 or len(password) > 20:
            self.password_input.setFocus()
            return False, "密码长度应为8-20位"
        
        if password != confirm_password:
            self.confirm_password_input.clear()
            self.confirm_password_input.setFocus()
            return False, "两次输入的密码不一致"
        
        return True, ""
    
    def _on_register(self):
        """处理注册"""
        # 验证输入
        valid, error_msg = self._validate_input()
        if not valid:
            InfoBar.warning(
                title="输入错误",
                content=error_msg,
                duration=2000,
                parent=self
            )
            return
        
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not self.user_auth:
            # 如果服务未初始化，模拟注册成功（开发模式）
            logger.warning("注册服务未初始化，使用模拟注册")
            self._username = username
            InfoBar.success(
                title="注册成功",
                content="注册成功，请登录（开发模式）",
                duration=2000,
                parent=self
            )
            self.accept()
            return
        
        # 执行注册
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def do_register():
                try:
                    user_id = await self.user_auth.register(username, password, email)
                    return {'success': True, 'user_id': user_id}
                except ValueError as e:
                    return {'success': False, 'message': str(e)}
                except Exception as e:
                    return {'success': False, 'message': f"注册失败: {str(e)}"}
            
            result = loop.run_until_complete(do_register())
            
            if result.get('success'):
                self._username = username
                InfoBar.success(
                    title="注册成功",
                    content="注册成功，请登录",
                    duration=2000,
                    parent=self
                )
                self.accept()
            else:
                InfoBar.error(
                    title="注册失败",
                    content=result.get('message', '注册失败，请重试'),
                    duration=3000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"注册失败: {e}", exc_info=True)
            InfoBar.error(
                title="注册失败",
                content=f"注册出错: {str(e)}",
                duration=3000,
                parent=self
            )
    
    def get_username(self) -> Optional[str]:
        """获取注册的用户名"""
        return self._username
