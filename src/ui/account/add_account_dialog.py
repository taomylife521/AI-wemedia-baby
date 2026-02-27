"""
添加账号对话框
文件路径：src/ui/account/add_account_dialog.py
功能：添加平台账号的对话框，包含平台选择和账号名称输入
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QPainterPath
import logging
import re

try:
    from qfluentwidgets import (
        MessageBoxBase, SubtitleLabel, BodyLabel, LineEdit, 
        PrimaryPushButton, PushButton, SearchLineEdit, TitleLabel,
        CardWidget, FluentIcon
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False
    from PySide6.QtWidgets import QDialog

logger = logging.getLogger(__name__)


# 平台配置
PLATFORM_CONFIG = {
    "douyin": {
        "name": "抖音",
        "url": "https://creator.douyin.com/",
        "icon": "🎵",
        "color": "#000000",
        "category": "popular"
    },
    "wechat_video": {
        "name": "微信视频号",
        "url": "https://channels.weixin.qq.com/",
        "icon": "📹",
        "color": "#07C160",
        "category": "popular"
    },
    "kuaishou": {
        "name": "快手",
        "url": "https://cp.kuaishou.com/",
        "icon": "⚡",
        "color": "#FF6600",
        "category": "popular"
    },
    "xiaohongshu": {
        "name": "小红书",
        "url": "https://creator.xiaohongshu.com/",
        "icon": "📕",
        "color": "#FF2442",
        "category": "popular"
    }
}


class PlatformCard(QPushButton):
    """平台卡片按钮"""
    
    def __init__(self, platform_id: str, config: Dict[str, Any], parent=None):
        """初始化平台卡片"""
        super().__init__(parent)
        self.platform_id = platform_id
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setFixedSize(110, 130)
        self.setCursor(Qt.PointingHandCursor)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)
        
        # 图标区域
        icon_label = QLabel(self.config.get("icon", "📱"), self)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_label.setFont(icon_font)
        
        # 平台名称
        name_label = BodyLabel(self.config.get("name", ""), self)
        name_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        
        # 设置样式 - 更加美观的卡片样式
        self.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid #EDEDED;
                border-radius: 10px;
                background-color: #FFFFFF;
                text-align: center;
                padding: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid {self.config.get("color", "#0078D4")};
                background-color: #FAFAFA;
            }}
            QPushButton:pressed {{
                background-color: #F5F5F5;
                border: 1px solid {self.config.get("color", "#0078D4")};
            }}
        """)
        
        # 添加阴影效果 (通过 QGraphicsDropShadowEffect 可能更好，这里先用简单的边框样式)



class PlatformSelectMessageBox(MessageBoxBase):
    """平台选择对话框（Fluent UI）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_platform: Optional[str] = None
        self.platform_cards: List[PlatformCard] = []
        
        # MessageBoxBase does not have titleLabel, we must create it
        self.titleLabel = SubtitleLabel("添加账号", self.widget)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 调整大小
        self.widget.setMinimumWidth(600)
        
        self._setup_content()
        
        # 隐藏确定按钮，因为点击卡片即确认
        self.yesButton.hide()
        self.cancelButton.setText("取消")
        
        self.cancelButton.setText("取消")
        
        # 移除遮罩背景变暗效果 - 使用官方 API
        self.setMaskColor(QColor(0, 0, 0, 0))
        
        # 增加内容内边距
        self.widget.setContentsMargins(0, 0, 0, 0)
        
        # 统一底部背景颜色
        self.buttonGroup.setStyleSheet("background-color: transparent; border-top: 1px solid #EDEDED;")
        self.cancelButton.setStyleSheet("""
            QPushButton {
                border: 1px solid #EDEDED;
                border-radius: 5px;
                background-color: #FFFFFF;
                padding: 6px 12px;
                font-size: 14px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #EEEEEE;
            }
        """)

        
    def showEvent(self, e):
        """显示时再次强制设置透明背景"""
        super().showEvent(e)
        self.setMaskColor(QColor(0, 0, 0, 0))
        
    def _setup_content(self):
        """设置内容区域"""
        # 1. 搜索框
        search_layout = QHBoxLayout()
        self.search_edit = SearchLineEdit(self.widget)
        self.search_edit.setPlaceholderText("请输入要查找的平台")
        self.search_edit.setFixedWidth(250)
        self.search_edit.textChanged.connect(self._on_search_changed)
        
        search_layout.addWidget(self.search_edit)
        search_layout.addStretch()
        
        self.viewLayout.addLayout(search_layout)
        
        # 2. 热门平台标题
        self.viewLayout.addSpacing(30)
        popular_label = SubtitleLabel("热门平台", self.widget)
        self.viewLayout.addWidget(popular_label)
        self.viewLayout.addSpacing(15)
        
        # 3. 平台展示区域
        # 使用 FlowLayout 或 Grid 模拟
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignLeft)
        
        # 获取所有平台
        platforms = [
            ("douyin", PLATFORM_CONFIG["douyin"]),
            ("wechat_video", PLATFORM_CONFIG["wechat_video"]),
            ("kuaishou", PLATFORM_CONFIG["kuaishou"]),
            ("xiaohongshu", PLATFORM_CONFIG["xiaohongshu"])
        ]
        
        for platform_id, config in platforms:
            card = PlatformCard(platform_id, config, self.widget)
            # 使用闭包捕获 platform_id
            card.clicked.connect(lambda checked=False, pid=platform_id: self._on_platform_clicked(pid))
            cards_layout.addWidget(card)
            self.platform_cards.append(card)
            
        cards_layout.addStretch()
        self.viewLayout.addLayout(cards_layout)
        
        # 添加底部间距
        self.viewLayout.addSpacing(20)

    def _on_search_changed(self, text: str):
        """搜索过滤"""
        search_text = text.lower().strip()
        for card in self.platform_cards:
            name = card.config.get("name", "").lower()
            if not search_text or search_text in name:
                card.show()
            else:
                card.hide()
                
    def _on_platform_clicked(self, platform_id: str):
        """平台点击回调"""
        self.selected_platform = platform_id
        self.accept()


class AccountNameMessageBox(MessageBoxBase):
    """账号名称输入对话框（Fluent UI）"""
    
    def __init__(self, platform_id: str, platform_config: Dict, parent=None):
        super().__init__(parent)
        self.platform_id = platform_id
        self.platform_config = platform_config
        self.result_data = None
        
        self.titleLabel = SubtitleLabel("完善账号信息", self.widget)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 调整大小
        self.widget.setMinimumWidth(450)
        
        self._setup_content()
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("上一步")
        
        self.yesButton.clicked.connect(self._on_confirm)
        self.cancelButton.clicked.disconnect()
        self.cancelButton.clicked.connect(self.reject)

        # 移除遮罩背景变暗效果 - 使用官方 API
        self.setMaskColor(QColor(0, 0, 0, 0))
        
        # 统一底部背景颜色
        self.buttonGroup.setStyleSheet("background-color: transparent; border-top: 1px solid #EDEDED;")
        
        # 调整按钮顺序：上一步(cancel)在左，确定(yes)在右
        # 获取 buttonGroup 的布局（通常是 QHBoxLayout）
        button_layout = self.buttonGroup.layout()
        if button_layout:
             button_layout.removeWidget(self.yesButton)
             button_layout.removeWidget(self.cancelButton)
             button_layout.addWidget(self.cancelButton)
             button_layout.addWidget(self.yesButton)

        self.yesButton.setStyleSheet("""
            QPushButton {
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 14px;
            }
        """)
        self.cancelButton.setStyleSheet("""
            QPushButton {
                border: 1px solid #EDEDED;
                border-radius: 5px;
                background-color: #FFFFFF;
                padding: 6px 12px;
                font-size: 14px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #EEEEEE;
            }
        """)

    def showEvent(self, e):
        """显示时再次强制设置透明背景"""
        super().showEvent(e)
        self.setMaskColor(QColor(0, 0, 0, 0))

    def _setup_content(self):
        """设置内容"""
        # 平台信息展示
        info_layout = QHBoxLayout()
        icon_label = QLabel(self.platform_config.get("icon", "📱"), self.widget)
        font = QFont()
        font.setPointSize(24)
        icon_label.setFont(font)
        
        name_label = SubtitleLabel(self.platform_config.get("name", ""), self.widget)
        
        info_layout.addWidget(icon_label)
        info_layout.addWidget(name_label)
        info_layout.addStretch()
        
        self.viewLayout.addLayout(info_layout)
        self.viewLayout.addSpacing(20)
        
        # 账号名称输入
        self.viewLayout.addWidget(BodyLabel("账号名称（可选）", self.widget))
        self.name_edit = LineEdit(self.widget)
        default_name = f"{self.platform_config['name']}账号"
        self.name_edit.setPlaceholderText(f"留空则默认：{default_name}")
        self.name_edit.setMaxLength(20)
        self.name_edit.returnPressed.connect(self._on_confirm)
        
        self.viewLayout.addWidget(self.name_edit)
        self.viewLayout.addSpacing(10)
        
        # 提示信息
        tip_label = BodyLabel("提示：名称仅用于本地区分，不影响实际发布。", self.widget)
        tip_label.setTextColor('#999999', '#999999') # 设置灰度
        self.viewLayout.addWidget(tip_label)

    def _on_confirm(self):
        """确定按钮回调"""
        account_name = self.name_edit.text().strip()
        default_name = f"{self.platform_config['name']}账号"
        
        if not account_name:
            account_name = default_name
            
        # 简单验证
        if len(account_name) > 20:
             # 这里无法直接弹窗，只能通过 InfoBar 提示，但 MessageBoxBase 也是通过遮罩显示的
             # 简单起见，我们重置焦点并return，或者抖动窗口
             self.name_edit.setFocus()
             return
            
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', account_name):
             # 同样，简单处理
             self.name_edit.setFocus()
             self.name_edit.selectAll()
             return

        self.result_data = {
            "platform_username": account_name,
            "platform": self.platform_id,
            "platform_name": self.platform_config["name"],
            "platform_url": self.platform_config["url"]
        }
        self.accept()


class AddAccountDialog:
    """添加账号流程控制器"""
    
    def __init__(self, parent=None):
        self.parent = parent
        
    def show(self) -> Optional[Dict[str, Any]]:
        """显示添加账号流程"""
        if not FLUENT_WIDGETS_AVAILABLE:
            return None # 降级处理略,假设环境已就绪
            
        # 第一步：选择平台
        step1 = PlatformSelectMessageBox(self.parent)
        if not step1.exec():
            return None  # 用户取消
        
        platform_id = step1.selected_platform
        config = PLATFORM_CONFIG.get(platform_id)
        
        # 第二步：配置指纹
        from .fingerprint_config_dialog import FingerprintConfigMessageBox
        step2 = FingerprintConfigMessageBox(self.parent)
        if not step2.exec():
            # 用户点击"上一步",返回第一步
            return self.show()  # 递归调用重新开始
        
        fingerprint_config = step2.get_fingerprint_config()
        
        # 返回结果
        return {
            "platform_username": f"{config['name']}账号",
            "platform": platform_id,
            "platform_name": config["name"],
            "platform_url": config["url"],
            "fingerprint_config": fingerprint_config  # 新增字段
        }

