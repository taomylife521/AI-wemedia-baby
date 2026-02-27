# -*- coding: utf-8 -*-
"""
账号表格组件
文件路径：src/ui/pages/account/components/account_table.py
功能：独立的账号列表表格组件，负责账号的显示和基本交互
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, QVBoxLayout,
    QLabel, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QBrush
import logging

try:
    from qfluentwidgets import (
        FluentIcon, TableWidget, BodyLabel, IconWidget,
        TransparentToolButton, InfoBadge
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class AccountTableWidget(QWidget):
    """账号表格组件
    
    负责显示账号列表，处理选择、筛选等基本交互。
    通过信号与外部通信，保持组件的独立性。
    """
    
    # 信号定义
    account_double_clicked = Signal(int)  # 账号ID
    account_selected = Signal(list)       # 选中的账号ID列表
    switch_account_requested = Signal(int) # 账号ID
    context_menu_requested = Signal(dict, object)  # account_data, pos
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = None
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建表格
        if FLUENT_WIDGETS_AVAILABLE:
            self.table = TableWidget(self)
            self._setup_table_style(self.table)
            self.table.setBorderRadius(0)
            self.table.setWordWrap(False)
            
            # 强制设置选中样式 (Fix: 解决全局样式不生效问题)
            # 使用更广泛的选择器覆盖 FluentWidgets 的默认样式
            # 强制设置选中样式 (Fix: 解决全局样式不生效问题)
            # ThemeManager 已接管
            pass
            
            # 同时修改 Palette 以防样式表不生效 (双重保险)
            palette = self.table.palette()
            palette.setColor(QPalette.Highlight, QColor(0, 120, 212, 15))
            palette.setColor(QPalette.HighlightedText, QColor("black"))
            self.table.setPalette(palette)
        else:
            self.table = QTableWidget(self)
        
        # 设置列
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "平台", "平台昵称", "账号组", "登录状态", "操作"
        ])
        
        # 设置表头居中
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        # 设置列宽
        self.table.setColumnWidth(0, 140)  # 平台
        self.table.setColumnWidth(1, 200)  # 平台昵称
        self.table.setColumnWidth(2, 120)  # 账号组
        self.table.setColumnWidth(3, 100)  # 登录状态
        self.table.setColumnWidth(4, 120)  # 操作
        
        # 选择模式
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 连接信号
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        
        layout.addWidget(self.table)
    
    def _setup_table_style(self, table):
        """设置表格样式（Fluent UI）"""
        if not FLUENT_WIDGETS_AVAILABLE:
            return
        table.setBorderVisible(True)
        table.setBorderRadius(8)
        table.setWordWrap(False)
    
    def load_accounts(self, accounts: List[Dict]):
        """加载账号列表
        
        Args:
            accounts: 账号列表，每个账号是一个字典
        """
        self.table.setRowCount(0)  # 清空现有数据
        logger.info(f"开始加载账号列表到表格，共 {len(accounts)} 个")
        
        for account in accounts:
            self._add_account_row(account)
        
        logger.info(f"账号表格加载完成，共 {len(accounts)} 个账号，当前行数: {self.table.rowCount()}")
    
    def _add_account_row(self, account: Dict):
        """添加账号行
        
        Args:
            account: 账号数据字典
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 52)
        
        # 1. 平台列（带图标）
        platform = account.get('platform', '')
        platform_name = self._get_platform_name(platform)
        
        # logger.debug(f"添加行 {row}: {platform} - {account.get('platform_username')}")
        
        platform_container = QWidget()
        platform_layout = QHBoxLayout(platform_container)
        platform_layout.setContentsMargins(12, 0, 8, 0)
        platform_layout.setSpacing(8)
        platform_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = IconWidget(self._get_platform_icon(platform), platform_container)
        icon_label.setFixedSize(24, 24)
        
        name_label = BodyLabel(platform_name, platform_container)
        name_label.setStyleSheet("font-weight: bold; color: #333333; font-size: 13px;")
        
        platform_layout.addWidget(icon_label)
        platform_layout.addWidget(name_label)
        # platform_layout.addStretch() # 居中则不需要 stretch 挤在左边，或者两边加 stretch
        
        self.table.setCellWidget(row, 0, platform_container)
        
        # 隐藏的文本项（用于排序和搜索）
        hidden_item = QTableWidgetItem("")
        hidden_item.setData(Qt.ItemDataRole.UserRole, platform)
        self.table.setItem(row, 0, hidden_item)
        
        # 2. 昵称列
        platform_username = account.get('platform_username') or account.get('account_name', '未命名')
        item_name = QTableWidgetItem(platform_username)
        item_name.setTextAlignment(Qt.AlignCenter)
        # item_name.setToolTip(platform_username)
        item_name.setData(Qt.ItemDataRole.UserRole, account.get('id'))
        item_name.setData(Qt.ItemDataRole.UserRole + 1, platform_username)
        self.table.setItem(row, 1, item_name)
        
        # 3. 账号组列
        group_name = account.get('group_name', '未分类')
        if not group_name:
            group_name = '未分类'
            
        if group_name == '未分类':
            # 使用原生 Item 确保文本完全居中
            item_group = QTableWidgetItem("未分类")
            item_group.setTextAlignment(Qt.AlignCenter)
            item_group.setForeground(QBrush(QColor("#999999")))
            self.table.setItem(row, 2, item_group)
            # 移除可能存在的 CellWidget
            self.table.removeCellWidget(row, 2)
        else:
            # 使用 Badge 样式显示账号组
            group_container = QWidget()
            group_layout = QHBoxLayout(group_container)
            group_layout.setContentsMargins(8, 0, 8, 0)
            group_layout.setAlignment(Qt.AlignCenter)
            
            if FLUENT_WIDGETS_AVAILABLE:
                # 已分类使用 InfoBadge
                from qfluentwidgets import InfoBadge
                group_badge = InfoBadge.info(group_name)
                # 明确添加对齐参数
                group_layout.addWidget(group_badge, 0, Qt.AlignCenter)
            else:
                group_label = QLabel(group_name)
                group_label.setAlignment(Qt.AlignCenter)
                group_layout.addWidget(group_label, 0, Qt.AlignCenter)
                
            self.table.setCellWidget(row, 2, group_container)
        
        # 4. 登录状态
        login_status = account.get('login_status', 'offline')
        status_widget = self._create_status_widget(login_status)
        self.table.setCellWidget(row, 3, status_widget)
        
        # 5. 操作列
        actions_widget = self._create_actions_widget(account)
        self.table.setCellWidget(row, 4, actions_widget)
    
    def _create_status_widget(self, login_status: str, tooltip: str = "") -> QWidget:
        """创建状态显示组件
        
        Args:
            login_status: 登录状态 ('online' / 'offline')
            tooltip: 离线原因悬浮提示（仅离线时有效）
        """
        from PySide6.QtWidgets import QVBoxLayout
        
        # 使用固定高度的容器来确保垂直居中
        status_widget = QWidget()
        status_widget.setFixedHeight(50)  # 匹配行高 52px
        
        # 离线时，在整个状态单元格容器上设置悬浮提示
        # （设在容器上而非 Badge 上，确保鼠标悬停在状态列任意位置都能看到）
        if login_status != 'online' and tooltip:
            status_widget.setToolTip(f"离线原因：{tooltip}")
        
        # 使用 QVBoxLayout + QHBoxLayout 实现双向居中
        main_layout = QVBoxLayout(status_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 添加上方弹簧
        main_layout.addStretch(1)
        
        # 中间放置水平布局
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        
        try:
            if FLUENT_WIDGETS_AVAILABLE:
                badge = InfoBadge.success("在线") if login_status == 'online' else InfoBadge.error("离线")
                h_layout.addStretch()
                h_layout.addWidget(badge)
                h_layout.addStretch()
        except:
            # 回退方案
            status_text = "●" if login_status == 'online' else "●"
            status_color = "#107C10" if login_status == 'online' else "#E81123"
            lbl = QLabel(status_text)
            lbl.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 10px;")
            h_layout.addStretch()
            h_layout.addWidget(lbl)
            h_layout.addStretch()
        
        main_layout.addLayout(h_layout)
        
        # 添加下方弹簧
        main_layout.addStretch(1)
        
        return status_widget
    
    def update_account_status(self, account_id: int, new_status: str, error_msg: str = ""):
        """实时更新指定账号的状态列（逐条刷新，无需重载整个表格）
        
        Args:
            account_id: 账号ID
            new_status: 新状态 ('online' / 'offline')
            error_msg: 离线原因（用于悬浮提示）
        """
        # 遍历表格找到匹配 account_id 的行
        for row in range(self.table.rowCount()):
            username_item = self.table.item(row, 1)
            if username_item and username_item.data(Qt.ItemDataRole.UserRole) == account_id:
                # 替换状态列的组件
                status_widget = self._create_status_widget(new_status, error_msg)
                self.table.setCellWidget(row, 3, status_widget)
                logger.debug(f"实时更新账号 {account_id} 状态为 {new_status}")
                break
    
    def _create_actions_widget(self, account: Dict) -> QWidget:
        """创建操作按钮组件"""
        widget_actions = QWidget()
        layout_actions = QHBoxLayout(widget_actions)
        layout_actions.setContentsMargins(2, 0, 2, 0)
        layout_actions.setSpacing(4)
        layout_actions.setAlignment(Qt.AlignCenter)
        
        btn_switch = TransparentToolButton(FluentIcon.SEND, widget_actions)
        btn_switch.setToolTip("切换并打开此账号")
        btn_switch.setFixedSize(32, 32)
        btn_switch.setIconSize(QSize(16, 16))
        
        # 连接点击信号
        # 注意：需要传递用户ID，利用lambda捕获
        account_id = account.get('id')
        if account_id:
            btn_switch.clicked.connect(lambda: self.switch_account_requested.emit(account_id))
        
        layout_actions.addWidget(btn_switch)
        
        return widget_actions
    
    def _get_platform_icon(self, platform: str):
        """获取平台图标"""
        if platform == 'douyin':
            return FluentIcon.VIDEO
        elif platform == 'kuaishou':
            return FluentIcon.MOVIE
        elif platform == 'wechat_video':
            return FluentIcon.CHAT
        elif platform == 'xiaohongshu':
            return FluentIcon.PHOTO
        return FluentIcon.GLOBE
    
    def _get_platform_name(self, platform: str) -> str:
        """获取平台显示名称"""
        platform_names = {
            'douyin': '抖音',
            'kuaishou': '快手',
            'wechat_video': '视频号',
            'xiaohongshu': '小红书'
        }
        return platform_names.get(platform, platform)
    
    def filter_accounts(self, keyword: str = "", platform: str = "all"):
        """筛选账号
        
        Args:
            keyword: 搜索关键词
            platform: 平台筛选（"all" 表示全部）
        """
        logger.info(f"AccountTableWidget 筛选: keyword='{keyword}', platform='{platform}' (type: {type(platform)})")
        hidden_count = 0
        total_rows = self.table.rowCount()
        
        for row in range(total_rows):
            show_row = True
            
            # 平台筛选
            if platform != "all":
                platform_item = self.table.item(row, 0)
                if platform_item:
                    row_platform = platform_item.data(Qt.ItemDataRole.UserRole)
                    # logger.debug(f"Row {row} platform: '{row_platform}' vs filter '{platform}'")
                    if row_platform != platform:
                        show_row = False
                else:
                    logger.warning(f"Row {row} missing platform item")
                    show_row = False
            
            # 关键词筛选
            if keyword and show_row:
                username_item = self.table.item(row, 1)
                if username_item:
                    username = username_item.text()
                    if keyword.lower() not in username.lower():
                        show_row = False
            
            self.table.setRowHidden(row, not show_row)
            if not show_row:
                hidden_count += 1
                
        logger.info(f"筛选完成: 总行数 {total_rows}, 隐藏 {hidden_count}, 显示 {total_rows - hidden_count}")
    
    def get_selected_account_ids(self) -> List[int]:
        """获取选中的账号ID列表"""
        selected_ids = []
        for item in self.table.selectedItems():
            if item.column() == 1:  # 只从昵称列获取
                account_id = item.data(Qt.ItemDataRole.UserRole)
                if account_id:
                    selected_ids.append(account_id)
        return selected_ids
    
    def _on_selection_changed(self):
        """选择变化时的回调"""
        selected_ids = self.get_selected_account_ids()
        self.account_selected.emit(selected_ids)
    
    def _on_item_double_clicked(self, item):
        """表格项双击事件"""
        if item.column() == 1:  # 昵称列
            account_id = item.data(Qt.ItemDataRole.UserRole)
            if account_id:
                logger.info(f"双击账号，ID: {account_id}")
                self.account_double_clicked.emit(account_id)
    
    def _on_context_menu(self, pos):
        """右键菜单请求"""
        item = self.table.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        
        # 获取账号信息
        platform_item = self.table.item(row, 0)
        username_item = self.table.item(row, 1)
        
        if not username_item:
            return
        
        account_id = username_item.data(Qt.ItemDataRole.UserRole)
        platform_username = username_item.data(Qt.ItemDataRole.UserRole + 1)
        platform = platform_item.data(Qt.ItemDataRole.UserRole) if platform_item else ""
        
        account_data = {
            'id': account_id,
            'platform_username': platform_username,
            'platform': platform
        }
        
        # 将局部坐标转换为全局屏幕坐标
        # 注意：pos 是相对于 table.viewport() 的坐标
        global_pos = self.table.viewport().mapToGlobal(pos)
        
        # 发射信号，让外部处理菜单
        self.context_menu_requested.emit(account_data, global_pos)
