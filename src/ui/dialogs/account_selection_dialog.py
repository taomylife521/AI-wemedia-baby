"""
账号选择弹窗
文件路径：src/ui/dialogs/account_selection_dialog.py
"""
import asyncio
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget
from PySide6.QtCore import Qt, Signal, QSize
from qfluentwidgets import MessageBoxBase, SubtitleLabel, BodyLabel, IconWidget, FluentIcon, ComboBox, InfoBadge

class AccountSelectionDialog(MessageBoxBase):
    """账号选择弹窗 (双列布局 - 账号/分组 模式)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("选择发布对象", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 主布局：水平分栏
        self.h_layout = QHBoxLayout()
        self.h_layout.setSpacing(16)
        
        # --- 左侧：导航栏 ---
        self.nav_list = QListWidget(self)
        self.nav_list.setFixedWidth(140)
        self.nav_list.setStyleSheet("""
            QListWidget {
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 0.5);
                outline: none;
            }
            QListWidget::item {
                height: 40px;
                padding-left: 8px;
                border-radius: 4px;
                color: #333;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 0, 0, 0.06);
                color: black;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.03);
            }
        """)
        self.h_layout.addWidget(self.nav_list)
        
        # --- 右侧：内容区域 (StackedWidget) ---
        self.content_stack = QStackedWidget(self)
        self.content_stack.setStyleSheet("""
             QStackedWidget {
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # 页面1: 账号列表
        self.account_list = QListWidget(self)
        self._set_list_style(self.account_list)
        self.content_stack.addWidget(self.account_list)
        
        # 页面2: 分组列表
        self.group_list = QListWidget(self)
        self._set_list_style(self.group_list)
        self.content_stack.addWidget(self.group_list)
        
        self.h_layout.addWidget(self.content_stack)
        
        self.viewLayout.addLayout(self.h_layout)
        
        # 调整弹窗大小
        self.widget.setMinimumWidth(680)
        self.widget.setMinimumHeight(480)
        
        # 数据
        self.all_accounts = []
        self.groups = []
        
        # 选中结果 {'type': 'account'|'group', 'data': ...}
        self.selection_result = None
        
        # 信号连接
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        
        self.account_list.itemClicked.connect(self._on_account_clicked)
        self.account_list.itemDoubleClicked.connect(self._on_account_double_clicked)
        
        self.group_list.itemClicked.connect(self._on_group_clicked)
        self.group_list.itemDoubleClicked.connect(self._on_group_double_clicked)
        
    def _set_list_style(self, list_widget):
        list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                height: 56px;
                padding: 4px;
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
                border-bottom: none;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.03);
                border-radius: 4px;
                border-bottom: none;
            }
        """)

    def set_data(self, accounts, groups=None, show_group_nav=True):
        """设置数据并初始化"""
        self.all_accounts = accounts
        self.groups = groups or []
        
        # 初始化左侧导航
        self.nav_list.clear() # 防止重复添加
        
        item_acc = QListWidgetItem("账号列表", self.nav_list)
        item_acc.setIcon(FluentIcon.PEOPLE.icon())
        item_acc.setData(Qt.UserRole, 0) # Index 0 => account_list
        
        if show_group_nav:
            item_grp = QListWidgetItem("账号组", self.nav_list)
            item_grp.setIcon(FluentIcon.LIBRARY.icon()) # 使用大写的 LIBRARY
            item_grp.setData(Qt.UserRole, 1) # Index 1 => group_list
        
        # 渲染内容
        self._render_accounts()
        if show_group_nav:
            self._render_groups()
        
        # 默认选中第一项
        self.nav_list.setCurrentRow(0)
            
    def set_accounts(self, accounts):
        """兼容旧接口"""
        self.set_data(accounts, show_group_nav=False)
        
    def _render_accounts(self):
        """渲染账号列表"""
        self.account_list.clear()
        
        from src.services.common.platform_registry import PlatformRegistry
        
        platform_icon_map = {
            'douyin': FluentIcon.VIDEO,
            'kuaishou': FluentIcon.VIDEO,
            'xiaohongshu': FluentIcon.BOOK_SHELF,
            'bilibili': FluentIcon.VIDEO,
            'wechat_video': FluentIcon.CHAT
        }
        
        platform_name_map = {
            'douyin': '抖音',
            'kuaishou': '快手',
            'xiaohongshu': '小红书',
            'bilibili': '哔哩哔哩',
            'wechat_video': '视频号'
        }
        
        for account in self.all_accounts:
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(12)
            
            # 图标
            platform = account.get('platform', '')
            platform_cn = platform_name_map.get(platform, platform)
            icon_enum = platform_icon_map.get(platform, FluentIcon.PEOPLE)
            
            icon_widget = IconWidget(icon_enum)
            icon_widget.setFixedSize(24, 24)
            layout.addWidget(icon_widget)
            
            # 信息
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            username = account.get('platform_username') or account.get('account_name', '未命名')
            name_label = BodyLabel(username)
            info_layout.addWidget(name_label)
            
            # 状态/平台
            login_status = account.get('login_status', 'offline')
            status_text = "在线" if login_status == 'online' else "离线"
            status_color = "#52c41a" if login_status == 'online' else "#999"
            sub_label = QLabel(f"{platform_cn} · {status_text}")
            sub_label.setStyleSheet(f"color: {status_color}; font-size: 12px;")
            info_layout.addWidget(sub_label)
            
            layout.addLayout(info_layout)
            layout.addStretch()
            
            # 若有分组显示分组标
            if account.get('group_id'):
                 # 简单查找一下分组名
                g_name = next((g['group_name'] for g in self.groups if g['id'] == account['group_id']), "")
                if g_name:
                    badge = InfoBadge.info(g_name)
                    layout.addWidget(badge)

            item = QListWidgetItem(self.account_list)
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.UserRole, account)
            self.account_list.setItemWidget(item, item_widget)
            
    def _render_groups(self):
        """渲染分组列表"""
        self.group_list.clear()
        
        for group in self.groups:
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(12)
            
            # 图标
            icon_widget = IconWidget(FluentIcon.FOLDER)
            icon_widget.setFixedSize(24, 24)
            layout.addWidget(icon_widget)
            
            # 信息
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            name_label = BodyLabel(group.get('group_name', '未命名'))
            info_layout.addWidget(name_label)
            
            desc = group.get('description', '无描述')
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: gray; font-size: 12px;")
            info_layout.addWidget(desc_label)
            
            layout.addLayout(info_layout)
            layout.addStretch()
            
            # 平台图标展示 (可选)
            platforms = group.get('platforms', [])
            if platforms:
                platforms_label = QLabel(", ".join(platforms))
                platforms_label.setStyleSheet("color: #666; font-size: 11px;")
                layout.addWidget(platforms_label)
            
            item = QListWidgetItem(self.group_list)
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.UserRole, group)
            self.group_list.setItemWidget(item, item_widget)
            
    def _on_nav_changed(self, row):
        """切换右侧视图"""
        if row < 0: return
        item = self.nav_list.item(row)
        page_index = item.data(Qt.UserRole)
        self.content_stack.setCurrentIndex(page_index)
        
        # 切换 tab 时清空另一侧的选择，或者保持? 
        # 为避免歧义，切换时先禁用确认按钮，要求用户重新选择
        self.yesButton.setEnabled(False)
        self.account_list.clearSelection()
        self.group_list.clearSelection()
        self.selection_result = None
        
    def _on_account_clicked(self, item):
        data = item.data(Qt.UserRole)
        self.selection_result = {'type': 'account', 'data': data}
        self.yesButton.setEnabled(True)
        # 清除分组选区
        self.group_list.blockSignals(True)
        self.group_list.clearSelection()
        self.group_list.blockSignals(False)
        
    def _on_account_double_clicked(self, item):
        self._on_account_clicked(item)
        self.accept()
        
    def _on_group_clicked(self, item):
        data = item.data(Qt.UserRole)
        self.selection_result = {'type': 'group', 'data': data}
        self.yesButton.setEnabled(True)
        # 清除账号选区
        self.account_list.blockSignals(True)
        self.account_list.clearSelection()
        self.account_list.blockSignals(False)

    def _on_group_double_clicked(self, item):
        self._on_group_clicked(item)
        self.accept()

    def get_selected_result(self):
        """获取选择结果 {'type': 'account'|'group', 'data': ...}"""
        return self.selection_result
    
    def get_selected_account(self):
        """兼容旧接口：如果是 account 类型则返回 data，否则 None"""
        if self.selection_result and self.selection_result['type'] == 'account':
            return self.selection_result['data']
        return None
