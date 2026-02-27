"""
单视频发布页面（开源版）
文件路径：src/ui/pages/publish/single_publish_page.py
功能：抖音单视频发布功能 - Community Edition
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFileDialog, QMessageBox, QComboBox, QTextEdit, QLineEdit,
    QFrame, QScrollArea, QButtonGroup
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QDate, QTime, QDateTime, QEasingCurve, QPropertyAnimation
import logging
import os
import asyncio

from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, PrimaryPushButton, 
    PushButton, FluentIcon, IconWidget, LineEdit, TextEdit,
    ComboBox, ProgressRing, InfoBar, InfoBarPosition,
    CalendarPicker, TimePicker, CheckBox, SmoothScrollArea,
    ImageLabel, RadioButton, ZhDatePicker, StateToolTip
)
FLUENT_WIDGETS_AVAILABLE = True

from ..base_page import BasePage
from qasync import asyncSlot

logger = logging.getLogger(__name__)


class SinglePublishPage(BasePage):
    """单视频发布页面 - 开源版核心功能"""
    
    # 发布完成信号
    publish_completed = Signal(bool, str)  # (success, message)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化"""
        super().__init__("单视频发布", parent)
        self.user_id = 1
        self.account_manager = None
        self.selected_file_path = ""
        self.selected_account = None
        self.editing_record_id = None # 当前正在编辑的记录ID
        
        self._init_services()
        self._setup_content()
        # 注意：不在 __init__ 里提交异步任务，此时 qasync 事件循环可能还未就绪
        
    def showEvent(self, event):
        """页面显示时触发账号加载（此时 qasync 事件循环已就绪）"""
        super().showEvent(event)
        # 每次页面显示时，如果账号列表为空则重新加载
        if not hasattr(self, 'available_accounts') or not self.available_accounts:
            logger.info("showEvent: 账号列表为空，触发异步加载...")
            asyncio.ensure_future(self._load_accounts())
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.services.account.account_manager_async import AccountManagerAsync
            from src.infrastructure.common.event.event_bus import EventBus
            from src.services.account.account_group_service import AccountGroupService
            
            service_locator = ServiceLocator()
            event_bus = service_locator.get(EventBus)
            
            # 创建账号管理器（已迁移为 Repository 模式）
            self.account_manager = AccountManagerAsync(
                user_id=self.user_id,
                event_bus=event_bus
            )
            # 创建账号组服务（待迁移为 AccountGroupRepositoryAsync）
            self.group_service = AccountGroupService()
        except Exception as e:
            logger.error(f"初始化单发布页面服务失败: {e}", exc_info=True)
    
    def _setup_content(self):
        """设置内容"""
        # 创建滚动区域
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setScrollAnimation(Qt.Vertical, 400, QEasingCurve.OutQuint)
        self.scroll_area.setScrollAnimation(Qt.Horizontal, 400, QEasingCurve.OutQuint)
            
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        # 防止宽度抖动：强制启用垂直滚动条，禁用水平滚动条
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(16, 0, 16, 24)
        layout.setSpacing(16)
        
        # --- 主内容双栏布局 ---
        main_hbox = QHBoxLayout()
        main_hbox.setSpacing(16)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        
        # 左侧：操作卡片列表 (账号、视频、信息)
        left_vbox = QVBoxLayout()
        left_vbox.setSpacing(16)
        
        # 顶部并排卡片布局 (账号 + 视频)
        top_config_hbox = QHBoxLayout()
        top_config_hbox.setSpacing(16)
        
        account_card = self._create_account_card()
        video_card = self._create_video_card()
        
        top_config_hbox.addWidget(account_card, 3) # 缩小账号区权重 (由4降为3)
        top_config_hbox.addWidget(video_card, 6)   # 增加视频区权重 (由5升为6)
        
        left_vbox.addLayout(top_config_hbox)
        
        description_card = self._create_description_card()
        settings_card = self._create_settings_card()
        left_vbox.addWidget(description_card)
        left_vbox.addWidget(settings_card)
        
        main_hbox.addLayout(left_vbox, 3) # 操作区比重
        
        # 右侧：独立预览卡片 (通高展示)
        right_vbox = QVBoxLayout()
        right_vbox.setContentsMargins(0, 0, 0, 0) # 消除侧边布局外距
        preview_card = self._create_preview_card()
        right_vbox.addWidget(preview_card)
        right_vbox.addStretch()
        
        main_hbox.addLayout(right_vbox, 1) # 预览区比重
        
        layout.addLayout(main_hbox)
        
        # 发布按钮卡片
        action_card = self._create_action_card()
        layout.addWidget(action_card)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 设置滚动区域的内容
        self.scroll_area.setWidget(self.content_widget)
        
        # 将滚动区域添加到BasePage的内容布局中
        self.content_layout.addWidget(self.scroll_area)
    
    def _create_preview_card(self) -> QWidget:
        """创建独立的视频预览卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0) # 彻底移除内边距，让画面铺满
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter) # 顶部居中对齐
        
        # 预览提示文本 (如果需要可以在此处添加标题)
        # --- 预览预览区 ---
        # 使用固定尺寸的黑底容器，营造专业播放器感
        self.preview_label = QLabel(card)
        
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(280, 280) # 保持固定正方形 (280x280)
        self.preview_label.setText("视频预览窗口") # 占位文本
        self.preview_label.setStyleSheet("""
            background-color: #f8f8f8; 
            border: 2px dashed #ddd; 
            border-radius: 12px; 
            color: #888;
            font-weight: bold;
        """)
        
        layout.addWidget(self.preview_label)
        
        return card
    
    def _create_account_card(self) -> QWidget:
        """创建专门的账号选择卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)
        
        btn_row = QHBoxLayout()
        
        self.btn_select_account = PrimaryPushButton(FluentIcon.PEOPLE, "选择发布账号", card)
        self.account_label = BodyLabel("未选择账号", card)
            
        self.account_label.setStyleSheet("color: red; font-weight: bold; margin-top: 4px;") # 移除 margin-left，改为顶部间距
        self.btn_select_account.clicked.connect(self._on_select_account)
        self.btn_select_account.setFixedWidth(160)
        
        # 按钮单独一行
        btn_row.addWidget(self.btn_select_account)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # 信息显示在下方
        layout.addWidget(self.account_label)
        
        return card

    def _create_video_card(self) -> QWidget:
        """创建专门的视频文件卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # --- 第一行: 视频文件选择 ---
        video_row = QHBoxLayout()
        self.btn_add_video = PrimaryPushButton(FluentIcon.VIDEO, "添加视频", card)
        self.file_info_label = BodyLabel("暂未选择视频", card)
        
        self.file_info_label.setWordWrap(True)
        self.btn_add_video.clicked.connect(self._on_browse_file)
        self.btn_add_video.setFixedWidth(120)
        self.file_info_label.setStyleSheet("color: #888; margin-left: 10px;")
        
        video_row.addWidget(self.btn_add_video)
        video_row.addWidget(self.file_info_label, 1) # 给 label 权重 1，由其占满剩余空间并触发换行
        layout.addLayout(video_row)
        
        # --- 第二行: 封面设置 ---
        cover_row = QHBoxLayout()
        cover_title = BodyLabel("视频封面", card)
        self.check_default_first_frame = CheckBox("首帧", card)
        self.cover_path_edit = LineEdit(card)
        self.btn_browse_cover = PushButton(FluentIcon.PHOTO, "选择", card)
            
        cover_title.setFixedWidth(60)
        self.check_default_first_frame.setChecked(True)
        self.check_default_first_frame.setFixedWidth(60)
        
        # AI封面按钮
        self.btn_ai_cover = PushButton(FluentIcon.BRUSH, "AI封面", card)
        self.btn_ai_cover.setFixedWidth(100)
        self.btn_ai_cover.clicked.connect(self._on_ai_cover_clicked)
        
        self.cover_path_edit.setPlaceholderText("默认自动截取...")
        self.cover_path_edit.setReadOnly(True)
        self.cover_path_edit.setFixedWidth(160)
        
        # 初始状态
        self.cover_path_edit.setEnabled(False)
        self.btn_browse_cover.setEnabled(False)
        self.btn_ai_cover.setEnabled(True) # AI封面始终可用，或者根据逻辑调整
        
        # 绑定逻辑
        self.check_default_first_frame.stateChanged.connect(self._on_first_frame_toggled)
        self.btn_browse_cover.clicked.connect(self._on_browse_cover)
        
        cover_row.addWidget(cover_title)
        cover_row.addWidget(self.check_default_first_frame)
        cover_row.addWidget(self.btn_ai_cover) # 添加AI封面按钮
        cover_row.addWidget(self.cover_path_edit)
        cover_row.addWidget(self.btn_browse_cover)
        cover_row.addStretch()
        layout.addLayout(cover_row)
        
        return card
    
    def _create_description_card(self) -> QWidget:
        """创建作品描述独立卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题 (作品描述)
        title = SubtitleLabel("作品描述", card)
        layout.addWidget(title)
        
        # 一体化容器
        entry_container = QFrame(card)
        entry_container.setObjectName("EntryContainer")
        entry_container.setStyleSheet("""
            #EntryContainer {
                border: 1px solid #e5e5e5;
                border-radius: 8px;
                background-color: white;
            }
            #EntryContainer:hover {
                border-color: #ccc;
            }
        """)
        container_layout = QVBoxLayout(entry_container)
        container_layout.setContentsMargins(16, 8, 16, 8)
        container_layout.setSpacing(0)
        
        # (1) 标题行: 输入框 + 字数
        title_hbox = QHBoxLayout()
        self.title_edit = LineEdit(entry_container)
            
        self.title_edit.setPlaceholderText("填写作品标题，为作品获得更多流量")
        self.title_edit.setStyleSheet("border: none; background: transparent; font-size: 14px; padding: 6px 0;")
        
        title_count_label = QLabel("0/30", entry_container)
        title_count_label.setStyleSheet("color: #ccc; font-size: 12px;")
        
        title_hbox.addWidget(self.title_edit)
        title_hbox.addWidget(title_count_label)
        container_layout.addLayout(title_hbox)
        
        # (2) 分割线
        line = QFrame(entry_container)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #f2f2f2; max-height: 1px; margin: 4px 0;")
        container_layout.addWidget(line)
        
        # (3) 描述文本区
        self.desc_edit = TextEdit(entry_container)
        self.desc_edit.setPlaceholderText("添加作品简介")
        self.desc_edit.setStyleSheet("border: none; background: transparent; font-size: 14px; padding: 10px 0;")
        self.desc_edit.setMinimumHeight(80)
        self.desc_edit.setMaximumHeight(160)
        container_layout.addWidget(self.desc_edit)
        
        # (4) 底部工具栏: 话题、@常用词 + 字数统计
        toolbar_hbox = QHBoxLayout()
        toolbar_hbox.setContentsMargins(0, 4, 0, 0)
        
        self.btn_topic = PushButton("#添加话题", entry_container)
        self.btn_mention = PushButton("@好友", entry_container)
            
        btn_style = "border: none; background: transparent; color: #888; font-size: 13px; font-weight: 500; padding: 4px 8px;"
        self.btn_topic.setStyleSheet(btn_style)
        self.btn_mention.setStyleSheet(btn_style + "margin-left: 4px;")
        self.btn_topic.setCursor(Qt.PointingHandCursor)
        self.btn_mention.setCursor(Qt.PointingHandCursor)
        
        self.btn_topic.clicked.connect(self._on_add_topic_clicked)
        self.btn_mention.clicked.connect(self._on_add_mention_clicked)
        
        total_count_label = QLabel("0 / 1000", entry_container)
        total_count_label.setStyleSheet("color: #ccc; font-size: 12px;")
        
        # 实时统计字数
        self.title_edit.textChanged.connect(lambda text: title_count_label.setText(f"{len(text)}/30"))
        self.desc_edit.textChanged.connect(lambda: total_count_label.setText(f"{len(self.desc_edit.toPlainText())} / 1000"))
        
        toolbar_hbox.addWidget(self.btn_topic)
        toolbar_hbox.addWidget(self.btn_mention)
        toolbar_hbox.addStretch()
        toolbar_hbox.addWidget(total_count_label)
        container_layout.addLayout(toolbar_hbox)
        
        layout.addWidget(entry_container)
        return card

    def _create_settings_card(self) -> QWidget:
        """创建更多设置卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        LABEL_WIDTH = 100 # 左侧标签统一宽度
        
        # 初始化标签数据存储
        if not hasattr(self, 'tag_values'):
            self.tag_values = {}
        
        # 标题 (更多设置)
        title = SubtitleLabel("更多设置", card)
        layout.addWidget(title)
        
        # --- 添加标签 (下拉选择 + 输入框) ---
        add_tags_row = QHBoxLayout()
        tags_label = BodyLabel("添加标签", card)
        self.tag_type_combo = ComboBox(card)
        self.tag_content_edit = LineEdit(card)
            
        tags_label.setFixedWidth(LABEL_WIDTH)
        
        # 配置下拉选项
        tag_types = ["位置", "影视演绎", "小程序", "游戏手柄", "标记万物", "购物车"]
        self.tag_type_combo.addItems(tag_types)
        self.tag_type_combo.setFixedWidth(120)
        
        self.tag_content_edit.setPlaceholderText("请输入对应内容")
        
        # 绑定逻辑
        self.tag_type_combo.currentTextChanged.connect(self._on_tag_type_changed)
        self.tag_content_edit.textChanged.connect(self._on_tag_content_changed)
        
        # 初始化当前显示的类型
        current_type = self.tag_type_combo.currentText()
        self.tag_content_edit.setText(self.tag_values.get(current_type, ""))
        
        add_tags_row.addWidget(tags_label)
        add_tags_row.addWidget(self.tag_type_combo)
        add_tags_row.addWidget(self.tag_content_edit)
        layout.addLayout(add_tags_row)

        # --- 5. 权限设置 ---
        perm_row = QHBoxLayout()
        perm_label = BodyLabel("设置权限", card)
            
        perm_label.setFixedWidth(LABEL_WIDTH)
        
        perm_vbox_row = QHBoxLayout()
        self.privacy_combo = ComboBox(card)
        self.allow_download_check = CheckBox("允许保存视频", card)
        
        self.privacy_combo.setFixedWidth(120)
        self.privacy_combo.addItems(["公开可见", "好友可见", "私密"])
        self.allow_download_check.setChecked(True)
        
        perm_vbox_row.addWidget(self.privacy_combo)
        perm_vbox_row.addWidget(self.allow_download_check)
        perm_vbox_row.addStretch()
        
        perm_row.addWidget(perm_label)
        perm_row.addLayout(perm_vbox_row)
        layout.addLayout(perm_row)

        # --- 6. 定时发布 ---
        schedule_row = QHBoxLayout()
        schedule_label = BodyLabel("发布时间", card)
        schedule_label.setFixedWidth(LABEL_WIDTH)
        
        schedule_content_vbox = QVBoxLayout()
        self._init_schedule_ui(schedule_content_vbox, card)
        
        schedule_row.addWidget(schedule_label)
        schedule_row.addLayout(schedule_content_vbox)
        layout.addLayout(schedule_row)
        
        return card

    def _on_add_topic_clicked(self):
        """插入话题符号"""
        self.desc_edit.insertPlainText("#")
        self.desc_edit.setFocus()

    def _on_add_mention_clicked(self):
        """插入艾特符号"""
        self.desc_edit.insertPlainText("@")
        self.desc_edit.setFocus()
        
    def _on_tag_type_changed(self, text):
        """标签类型切换"""
        # 切换时，输入框显示对应类型的值
        # 注意: 之前的输入值已经在 textChanged 中保存了
        val = self.tag_values.get(text, "")
        self.tag_content_edit.setText(val)
        
    def _on_tag_content_changed(self, text):
        """标签内容变更"""
        current_type = self.tag_type_combo.currentText()
        self.tag_values[current_type] = text

    def _init_schedule_ui(self, layout, parent):
        """初始化定时发布UI (立即/定时)"""
        # 1. 选项行 (立即发布 vs 定时发布)
        option_row = QHBoxLayout()
        option_row.setContentsMargins(0, 0, 0, 0)
        option_row.setSpacing(20)
        
        self.radio_now = RadioButton("立即发布")
        self.radio_schedule = RadioButton("定时发布")
        self.radio_now.setChecked(True)
        # 禁用焦点防止滚动条跳动
        self.radio_now.setFocusPolicy(Qt.NoFocus)
        self.radio_schedule.setFocusPolicy(Qt.NoFocus)
        
        # 逻辑互斥组
        self.publish_time_group = QButtonGroup(parent)
        self.publish_time_group.addButton(self.radio_now)
        self.publish_time_group.addButton(self.radio_schedule)
        
        option_row.addWidget(self.radio_now)
        option_row.addWidget(self.radio_schedule)
        
        # 2. 从 Date/Time Pickers (直接放在同一行，减少层级)
        # 添加一些间距
        option_row.addSpacing(16)
        
        # 使用内置的 ZhDatePicker (已预设好中文格式和顺序)
        self.date_picker = ZhDatePicker()
        
        self.time_picker = TimePicker()
        
        # 默认设置为当前时间 + 2小时
        now = QDateTime.currentDateTime()
        target = now.addSecs(7200 + 600) # 2h 10m later
        self.date_picker.setDate(target.date())
        self.time_picker.setTime(target.time())
        
        option_row.addWidget(self.date_picker)
        option_row.addWidget(self.time_picker)
        option_row.addStretch() # 整体靠左
        
        layout.addLayout(option_row)
        
        # 连接信号进行校验
        self.date_picker.dateChanged.connect(self._validate_schedule_time)
        self.time_picker.timeChanged.connect(self._validate_schedule_time)
        
        # 4. 动态显隐逻辑 (直接控制组件)
        self.date_picker.setVisible(False)
        self.time_picker.setVisible(False)
        
        self.radio_schedule.toggled.connect(self.date_picker.setVisible)
        self.radio_schedule.toggled.connect(self.time_picker.setVisible)

    def _validate_schedule_time(self):
        """校验定时时间：必须至少在当前时间2小时后"""
        # 防止递归调用
        if getattr(self, '_is_validating_time', False):
            return
            
        current_date = self.date_picker.date
        current_time = self.time_picker.time
        
        if not current_date.isValid() or not current_time.isValid():
            return
            
        selected_dt = QDateTime(current_date, current_time)
        now = QDateTime.currentDateTime()
        min_dt = now.addSecs(7200) # +2 hours
        
        if selected_dt < min_dt:
            self._is_validating_time = True
            
            # 重置为最小合法时间
            target_dt = min_dt.addSecs(300) # 加5分钟缓冲
            self.date_picker.setDate(target_dt.date())
            self.time_picker.setTime(target_dt.time())
            
            StateToolTip(
                "时间已修正",
                "定时发布必须至少设置在 2 小时以后",
                parent=self.window()
            ).show()
            
            self._is_validating_time = False


    

    def _create_action_card(self) -> QWidget:
        """创建操作按钮卡片"""
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # 状态标签
        self.status_label = BodyLabel("准备就绪", card)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 发布按钮 (改为添加到发布列表)
        self.btn_publish = PrimaryPushButton(FluentIcon.ADD, "添加到发布列表", card)
        self.btn_publish.clicked.connect(self._on_publish)
        self.btn_publish.setEnabled(False)
        layout.addWidget(self.btn_publish)
        layout.addSpacing(32) # 右侧留白，使按钮左移
        
        return card
    
    async def _load_accounts(self):
        """异步加载全部平台账号列表"""
        logger.info("SinglePublishPage 准备加载可用账号列表...")
        if not hasattr(self, 'account_manager') or not self.account_manager:
            logger.warning("account_manager 未初始化，放弃加载账号。")
            return
        
        # 直接从数据库获取全部账号，跳过 PlatformRegistry（发布页未注册适配器）
        try:
            accounts = await self.account_manager.get_accounts()
            logger.info(f"从数据库加载到 {len(accounts) if accounts else 0} 个账号")
            
            self.available_accounts = accounts or []
            logger.info(f"账号列表加载完毕，共 {len(self.available_accounts)} 个账号")
            
            # 更新 UI 状态
            if self.available_accounts:
                self.btn_select_account.setEnabled(True)
            else:
                self.account_label.setText("无可用发布账号 (请先添加并登录)")
                self.btn_select_account.setEnabled(False)
                
        except Exception as e:
            logger.error(f"加载账号列表失败: {e}", exc_info=True)
    
    async def _load_accounts_async(self, platform='douyin'):
        """异步加载账号"""
        try:
            accounts = await self.account_manager.get_accounts(platform=platform)
            
            if not accounts:
                return

            if not hasattr(self, 'available_accounts') or self.available_accounts is None:
                self.available_accounts = []
                
            self.available_accounts.extend(accounts)
            
            # 去重 (根据id)
            seen_ids = set()
            unique_accounts = []
            for acc in self.available_accounts:
                if acc['id'] not in seen_ids:
                    unique_accounts.append(acc)
                    seen_ids.add(acc['id'])
            self.available_accounts = unique_accounts

            if not self.available_accounts:
                self.account_label.setText("无可用发布账号 (请先添加并登录)")
                self.btn_select_account.setEnabled(False)
            else:
                self.btn_select_account.setEnabled(True)
                # 如果当前已选账号不在列表中（可能被删除），则重置
                if self.selected_account and self.selected_account.get('type') == 'account':
                    # 注意：selected_account 结构变化了，这里需要小心
                    # 这里简化处理，只有当 selected_account 是单个账号时才检查
                    current_acc_id = self.selected_account['data'].get('id')
                    exists = any(a['id'] == current_acc_id for a in self.available_accounts)
                    if not exists:
                        self.selected_account = None
                        self.account_label.setText("未选择账号")
            
            # 加载完成后更新发布按钮状态
            self._update_publish_button_state()
                
        except Exception as e:
            logger.error(f"异步加载账号失败 ({platform}): {e}")
            
    @asyncSlot()
    async def _on_select_account(self):
        """选择账号按钮点击槽函数"""
        logger.info(f"点击选择账号按钮, available_accounts count: {len(getattr(self, 'available_accounts', []))}")
        if not hasattr(self, 'available_accounts') or not self.available_accounts:
            logger.warning("账号列表为空，尝试重新加载...")
            # 账号为空时先尝试加载，加载完再显示弹窗
            await self._load_accounts()
            if not self.available_accounts:
                InfoBar.warning(
                    title="暂无账号",
                    content="请先在账号管理页面添加并登录账号",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
            
        # 异步显示选择弹窗
        logger.info("准备显示账号选择弹窗...")
        await self._async_show_selection_dialog()

    async def _async_show_selection_dialog(self):
        """异步显示选择弹窗"""
        try:
            groups = []
            if hasattr(self, 'group_service'):
                groups = await self.group_service.get_groups(self.user_id)
            
            from src.ui.dialogs.account_selection_dialog import AccountSelectionDialog
            dialog = AccountSelectionDialog(self)
            dialog.set_data(self.available_accounts, groups)
            
            result = None
            if dialog.exec():
                result = dialog.get_selected_result()
            
            if result:
                # 结果可能是 {'type': 'account', 'data': ...} 或 {'type': 'group', 'data': ...}
                self.selected_account = result 
                # 注意：self.selected_account 原本存储的是 account dict, 现在变成了 result dict
                # 后后续使用 self.selected_account 的地方都需要适配
                
                # 更新显示
                if result['type'] == 'account':
                    account = result['data']
                    platform = account.get('platform', 'unknown')
                    platform_cn = self._get_platform_name_cn(platform)
                    name = account.get('platform_username', '未命名')
                    self.account_label.setText(f"{platform_cn} | {name}")
                elif result['type'] == 'group':
                    group = result['data']
                    name = group.get('group_name', '未命名')
                    count = len(group.get('platforms', []))
                    self.account_label.setText(f"账号组 | {name} ({count}个平台)")
                
                self._update_publish_button_state()
        except Exception as e:
            logger.error(f"显示账号选择弹窗失败: {e}", exc_info=True)
            InfoBar.error(
                title="错误",
                content=f"加载账号组数据失败: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def _get_platform_name_cn(self, platform: str) -> str:
        """获取平台中文名称"""
        platform_name_map = {
            'douyin': '抖音',
            'kuaishou': '快手',
            'xiaohongshu': '小红书',
            'bilibili': '哔哩哔哩',
            'wechat_video': '视频号'
        }
        return platform_name_map.get(platform, platform)
    
    def _on_browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv);;所有文件 (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            # self.file_path_edit.setText(file_path) # 已移除
            
            # 更新文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            size_mb = file_size / (1024 * 1024)
            self.file_info_label.setText(f"{file_name}\n大小: {size_mb:.2f} MB")
            
            # 如果标题为空，使用文件名
            if not self.title_edit.text():
                title = os.path.splitext(file_name)[0]
                self.title_edit.setText(title)
            
            # 启用发布按钮
            self._update_publish_button_state()
            
            # 异步加载缩略图
            asyncio.create_task(self._load_thumbnail_async(file_path))

    async def _load_thumbnail_async(self, file_path: str):
        """异步加载缩略图"""
        try:
            # 在线程池中执行耗时的 ffmpeg 操作
            loop = asyncio.get_running_loop()
            from src.utils.video_metadata import extract_video_thumbnail
            
            thumb_path = await loop.run_in_executor(None, extract_video_thumbnail, file_path)
            
            if thumb_path and os.path.exists(thumb_path):
                self._update_preview(thumb_path)
        except Exception as e:
            logger.error(f"加载缩略图失败: {e}")

    def _update_preview(self, image_path: str):
        """更新预览图（高清适配版本）"""
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return
            
        # 针对高分屏 (DPI) 进行优化，防止模糊
        ratio = self.devicePixelRatio()
        # 目标逻辑像素 280x280 -> 物理像素 280*ratio x 280*ratio
        target_w = int(280 * ratio)
        target_h = int(280 * ratio)
        
        # 使用平滑缩放算法处理高清源图
        scaled_pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 告诉 Qt 该图片包含多倍像素数据，防止在渲染时再次拉伸导致模糊
        scaled_pixmap.setDevicePixelRatio(ratio)
        
        # 移除虚线边框，背景设为透明
        self.preview_label.setStyleSheet("background-color: transparent; border: none; border-radius: 12px;")
        
        # 设置高清图片
        self.preview_label.setPixmap(scaled_pixmap)
        
        # 移除占位文字
        self.preview_label.setText("")

    def _on_browse_cover(self):
        """浏览封面"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择封面图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*.*)"
        )
        
        if file_path:
            self.cover_path_edit.setText(file_path)

    def _on_ai_cover_clicked(self):
        """点击AI封面生成"""
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.warning(
                title='功能开发中',
                content="AI生成封面功能将在后续版本中推出，敬请期待！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
        else:
            QMessageBox.information(self, "提示", "AI生成封面功能将在后续版本中推出，敬请期待！")

    def _on_first_frame_toggled(self):
        """处理首帧复选框状态变化"""
        is_checked = self.check_default_first_frame.isChecked()
        self.cover_path_edit.setEnabled(not is_checked)
        self.btn_browse_cover.setEnabled(not is_checked)
        if is_checked:
            self.cover_path_edit.clear()
            self.cover_path_edit.setPlaceholderText("默认自动截取...")
    
    def _update_publish_button_state(self):
        """更新发布按钮状态"""
        has_file = bool(self.selected_file_path)
        has_account = self.selected_account is not None
        self.btn_publish.setEnabled(has_file and has_account)
    
    def _on_publish(self):
        """发布视频"""
        if not self.selected_file_path:
            QMessageBox.warning(self, "错误", "请先选择视频文件")
            return
        
        if not self.selected_account:
            QMessageBox.warning(self, "错误", "请选择发布账号")
            return
            
        target_accounts = []
        if self.selected_account['type'] == 'account':
            target_accounts.append(self.selected_account['data'])
        elif self.selected_account['type'] == 'group':
            # 过滤掉无效账号（如未登录？目前仅获取列表，暂不过滤状态，由发布服务处理或提示）
            # 注意：group 数据里的 accounts 可能只包含基本信息，如果需要完整信息可能需要再查询
            # 但 _execute_add_to_list 里似乎只需要 account id 和 platform 等基本信息
            target_accounts.extend(self.selected_account['data'].get('accounts', []))
            
        if not target_accounts:
            QMessageBox.warning(self, "错误", "所选账号组为空")
            return
        
        # 获取发布信息
        title = self.title_edit.text() or os.path.splitext(os.path.basename(self.selected_file_path))[0]
        description = self.desc_edit.toPlainText() if hasattr(self.desc_edit, 'toPlainText') else self.desc_edit.text()
        
        # 获取标签信息，并转为数组(格式: 类型|内容)
        tags = []
        if hasattr(self, 'tag_values'):
            # 将所有非空的标签类型和内容拼接为 "类型|内容" 格式
            tags = [f"{k}|{v.strip()}" for k, v in self.tag_values.items() if v.strip()]
        
        # 更新状态
        self.status_label.setText(f"正在提交 {len(target_accounts)} 个任务...")
        self.btn_publish.setEnabled(False)
        
        # 批量提交
        for account_data in target_accounts:
            asyncio.create_task(self._execute_add_to_list(
                account=account_data,
                file_path=self.selected_file_path,
                title=title,
                description=description,
                tags=tags
            ))
    
    async def _execute_add_to_list(
        self,
        account: dict,
        file_path: str,
        title: str,
        description: str,
        tags: List[str]
    ):
        """执行添加到列表（使用 PublishRecordRepositoryAsync）"""
        try:
            from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
            publish_repo = PublishRecordRepositoryAsync()
            
            # 格式化标签字符串
            tags_str = ",".join(tags) if tags else ""
            
            # 获取定时发布时间
            scheduled_time = None
            is_schedule = False
            
            if hasattr(self, 'radio_schedule'):
                is_schedule = self.radio_schedule.isChecked()
            elif hasattr(self, 'schedule_checkbox'):
                is_schedule = self.schedule_checkbox.isChecked()
                
            if is_schedule:
                date = self.date_picker.date
                time = self.time_picker.time
                dt = QDateTime(date, time)
                scheduled_time = dt.toString(Qt.ISODate)

            # 获取封面路径
            cover_path = self.cover_path_edit.text() if hasattr(self, 'cover_path_edit') else None
            
            # 使用 self.tag_values 安全获取扩展字段
            tv = getattr(self, 'tag_values', {})
            poi_info = tv.get("位置", "")
            micro_app_info = tv.get("小程序", "")
            goods_info = tv.get("购物车", "")
            anchor_info = tv.get("标记万物", "")
            
            # 获取隐私设置
            privacy = "public"
            if hasattr(self, 'privacy_combo'):
                p_text = self.privacy_combo.currentText()
                if "好友" in p_text: privacy = "friend"
                elif "私密" in p_text: privacy = "private"
                elif "粉丝" in p_text: privacy = "fans"
            
            allow_dl = True
            if hasattr(self, 'allow_download_check'):
                allow_dl = self.allow_download_check.isChecked()
            
            import json
            privacy_settings = json.dumps({
                "privacy": privacy,
                "allow_download": allow_dl
            }, ensure_ascii=False)

            # 判断是新建还是更新
            if self.editing_record_id:
                # 通过 Repository 更新现有记录
                await publish_repo.update_content(
                    record_id=self.editing_record_id,
                    platform_username=account.get('platform_username', ''),
                    platform=account.get('platform', 'douyin'),
                    file_path=file_path,
                    file_type='video',
                    title=title,
                    description=description,
                    tags=tags_str,
                    cover_path=cover_path,
                    poi_info=poi_info,
                    micro_app_info=micro_app_info,
                    goods_info=goods_info,
                    anchor_info=anchor_info,
                    privacy_settings=privacy_settings,
                    scheduled_publish_time=scheduled_time
                )
                msg_base = "已更新发布任务"
            else:
                # 通过 Repository 创建发布记录
                await publish_repo.create(
                    user_id=self.user_id,
                    platform_username=account.get('platform_username', ''),
                    platform=account.get('platform', 'douyin'),
                    file_path=file_path,
                    file_type='video',
                    title=title,
                    description=description,
                    tags=tags_str,
                    cover_path=cover_path,
                    poi_info=poi_info,
                    micro_app_info=micro_app_info,
                    goods_info=goods_info,
                    anchor_info=anchor_info,
                    privacy_settings=privacy_settings,
                    scheduled_publish_time=scheduled_time
                )
                msg_base = "已添加到发布列表"
            
            msg = msg_base
            if scheduled_time:
                msg += f" (定时: {dt.toString('yyyy-MM-dd HH:mm')})"
            
            # 操作后重置编辑状态
            self.editing_record_id = None
            self.btn_publish.setText("添加到发布列表")
            
            self._on_publish_success(msg)
                
        except Exception as e:
            logger.error(f"添加到发布列表失败: {e}", exc_info=True)
            self._on_publish_error(str(e))
    
    def _on_publish_success(self, message: str):
        """发布成功"""
        self.status_label.setText("✓ 发布成功！")
        self.btn_publish.setEnabled(True)
        
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.success(
                title="添加成功",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        else:
            QMessageBox.information(self, "成功", message)
        
        self.publish_completed.emit(True, message)
        
        # 跳转到发布列表页面
        try:
            main_window = self.window()
            if hasattr(main_window, 'switchTo') and hasattr(main_window, 'publish_list_page'):
                main_window.switchTo(main_window.publish_list_page)
        except Exception as e:
            logger.error(f"跳转发布列表失败: {e}")
    
    def _on_publish_error(self, error_message: str):
        """发布失败"""
        self.status_label.setText(f"✗ 发布失败: {error_message}")
        self.btn_publish.setEnabled(True)
        
        if FLUENT_WIDGETS_AVAILABLE:
            InfoBar.error(
                title="发布失败",
                content=error_message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
        else:
            QMessageBox.warning(self, "错误", f"发布失败: {error_message}")
        
        self.publish_completed.emit(False, error_message)

    def set_publish_data(self, record: dict):
        """回填发布数据 (用于编辑或重新发布)"""
        # 判断是修改待发布记录，还是重用已发布记录
        status = record.get('status', '')
        if status in ['success', 'failed', 'completed']:
            # 如果是终态记录，则不覆盖原始记录，作为新任务保存
            self.editing_record_id = None
            self.btn_publish.setText("保存为新任务")
        else:
            # 否则进入编辑模式
            self.editing_record_id = record.get('id')
            self.btn_publish.setText("保存修改")
        
        # 1. 基础文本
        title = record.get('title', '')
        description = record.get('description', '')
        self.title_edit.setText(title)
        self.desc_edit.setText(description)
        
        # 2. 文件处理
        file_path = record.get('file_path', '')
        if file_path and os.path.exists(file_path):
            self.selected_file_path = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            self.file_info_label.setText(f"{file_name}\n大小: {size_mb:.2f} MB")
            
            # 加载缩略图
            asyncio.create_task(self._load_thumbnail_async(file_path))
        else:
            if file_path:
                self.file_info_label.setText(f"文件不存在: {os.path.basename(file_path)}")
            self.selected_file_path = ""
            
        # 3. 标签处理
        tags_str = record.get('tags', '')
        if tags_str:
            # 简单处理：如果描述里没有标签，追加到描述末尾
            # 或者什么都不做，因为当前 UI 没有独立标签输入框
            pass
            
        # 4. 账号回填 (尝试匹配)
        target_name = record.get('platform_username', '')
        target_platform = record.get('platform', '')
        
        found_account = None
        if hasattr(self, 'available_accounts') and self.available_accounts:
            for acc in self.available_accounts:
                p_name = acc.get('platform_username')
                
                if acc.get('platform') == target_platform:
                    if p_name and p_name == target_name:
                        found_account = acc
                        break
        
        if found_account:
            self.selected_account = {'type': 'account', 'data': found_account}
            name = found_account.get('platform_username', '未命名')
            self.account_label.setText(f"{target_platform} | {name}")
            self._update_publish_button_state()
        else:
            if target_name:
                self.account_label.setText(f"{target_platform} | {target_name} (未登录/不存在)")
                self.selected_account = None
