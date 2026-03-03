"""
发布记录页面
文件路径：src/ui/pages/publish/publish_records_page.py
功能：显示发布任务记录列表
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidgetItem, QAbstractItemView, QMenu
from PySide6.QtCore import Qt, QTimer, QSettings
import logging
import os

from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, PushButton, TableWidget, 
    LineEdit, ComboBox, MessageBox, InfoBar, FluentIcon, IconWidget,
    PrimaryPushButton, CheckBox
)
FLUENT_WIDGETS_AVAILABLE = True

from ..base_page import BasePage
from src.utils.date_utils import format_schedule_time_st_str

logger = logging.getLogger(__name__)

class PublishRecordsPage(BasePage):
    """发布记录页面"""
    
    def __init__(self, parent: Optional[QWidget] = None, title: str = "发布记录", target_statuses: List[str] = None):
        """初始化"""
        super().__init__(title, parent)
        self.user_id = 1
        self.publish_records = []
        self._active_workers = []
        
        # 默认只显示成功（发布记录）
        self.target_statuses = target_statuses if target_statuses is not None else ["success"]
        
        self._setup_content()
        # 延迟加载
        QTimer.singleShot(100, self._load_publish_records)
        
    def _setup_content(self):
        """设置内容"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 筛选和搜索区域
        filter_card = CardWidget(self)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)
        

        

        
        # 删除按钮
        btn_delete = PushButton(FluentIcon.DELETE, "删除", filter_card)
        btn_delete.clicked.connect(self._on_delete_records)
        filter_layout.addWidget(btn_delete)
        
        filter_layout.addSpacing(20)
        
        # 开始发布按钮
        self.btn_start_publish = PrimaryPushButton(FluentIcon.PLAY, "发布", filter_card)
        self.btn_start_publish.clicked.connect(self._on_start_publish)
        filter_layout.addWidget(self.btn_start_publish)
        
        # 停止发布按钮
        self.btn_stop_publish = PushButton(FluentIcon.PAUSE, "停止", filter_card)
        
        self.btn_stop_publish.setEnabled(False) # 默认禁用
        self.btn_stop_publish.clicked.connect(self._on_stop_publish)
        filter_layout.addWidget(self.btn_stop_publish)

        # 暂停/继续按钮
        self.btn_pause_publish = PushButton(FluentIcon.GAME, "暂停", filter_card) # 使用 GAME 图标代替 PAUSE (避免冲突) 或其他合适图标
        
        self.btn_pause_publish.setEnabled(False)
        self.btn_pause_publish.clicked.connect(self._on_pause_publish)
        filter_layout.addWidget(self.btn_pause_publish)
        
        # 自动发布复选框
        self.auto_publish_check = CheckBox("自动发布", filter_card)
        self.auto_publish_check.setToolTip("勾选后，只要列表中有待发布任务，将自动开始发布")
        self.auto_publish_check.setChecked(False)
        filter_layout.addWidget(self.auto_publish_check)
        
        # 显示浏览器复选框
        self.headless_check = CheckBox("显示浏览器", filter_card)
        self.headless_check.setToolTip("勾选：显示浏览器窗口（有头模式）\n未勾选：后台静默运行（无头模式）")
        self.headless_check.setChecked(True) # 默认显示，方便调试
        filter_layout.addWidget(self.headless_check)

        # 速度设置
        filter_layout.addWidget(BodyLabel("速度:", filter_card))
        self.combo_speed_setting = ComboBox(filter_card)
        self.combo_speed_setting.addItem("正常 (1.0x)")
        self.combo_speed_setting.addItem("慢速 (1.5x)")
        self.combo_speed_setting.addItem("极慢 (2.0x)")
        # 额外倍率（仅追加，避免影响已保存的 speed_index）
        self.combo_speed_setting.addItem("超慢 (3.0x)")
        self.combo_speed_setting.addItem("调试 (5.0x)")
        # 使用 setItemData 设置 userData (qfluentwidgets addItem 第二参数是 icon)
        self.combo_speed_setting.setItemData(0, 1.0)
        self.combo_speed_setting.setItemData(1, 1.5)
        self.combo_speed_setting.setItemData(2, 2.0)
        self.combo_speed_setting.setItemData(3, 3.0)
        self.combo_speed_setting.setItemData(4, 5.0)
        self.combo_speed_setting.setCurrentIndex(0)
        self.combo_speed_setting.setFixedWidth(120)
        self.combo_speed_setting.setToolTip("调整发布操作的等待时间倍率，倍率越高越慢，越安全")
        self.combo_speed_setting.currentIndexChanged.connect(self._on_speed_changed)
        filter_layout.addWidget(self.combo_speed_setting)
        
        # 加载保存的速度设置
        self._load_speed_setting()
        
        filter_layout.addSpacing(20)
        
        # 平台筛选
        filter_layout.addWidget(BodyLabel("平台:", filter_card))
        self.platform_filter = ComboBox(filter_card)
        self.platform_filter.addItems(["全部", "抖音", "快手", "小红书", "微信视频号"])
        self.platform_filter.setFixedWidth(120)
        self.platform_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.platform_filter)
        
        # 状态筛选 (基于 target_statuses 动态生成)
        filter_layout.addWidget(BodyLabel("状态:", filter_card))
        self.status_filter = ComboBox(filter_card)
        
        status_items = ["全部"]
        status_map_rev = {"success": "成功", "failed": "失败", "pending": "待发布"}
        
        # 如果配置的所有状态都是可显示状态，则添加到下拉列表
        for s in self.target_statuses:
            if s in status_map_rev:
                status_items.append(status_map_rev[s])
                
        self.status_filter.addItems(status_items)
        self.status_filter.setFixedWidth(120)
        self.status_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_filter)
        
        filter_layout.addStretch()
        layout.addWidget(filter_card)
        
        # 记录表格
        table_container = CardWidget(self)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.records_table = TableWidget(table_container)
        self.records_table.setBorderVisible(True)
        self.records_table.setBorderRadius(8)
        self.records_table.setWordWrap(False)
        self.records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            
        self.records_table.setColumnCount(8)
        self.records_table.setHorizontalHeaderLabels([
            "平台", "平台昵称", "文件", "封面", "作品描述", "发布时间", "状态", "操作"
        ])
        
        # 列宽设置 (总宽约 1440px，适配宽屏)
        self.records_table.setColumnWidth(0, 100) # 平台
        self.records_table.setColumnWidth(1, 120) # 账号
        self.records_table.setColumnWidth(2, 200) # 文件
        self.records_table.setColumnWidth(3, 80)  # 封面
        self.records_table.setColumnWidth(4, 300) # 描述
        self.records_table.setColumnWidth(5, 150) # 发布时间
        self.records_table.setColumnWidth(6, 100) # 状态
        self.records_table.setColumnWidth(7, 100) # 操作
        self.records_table.verticalHeader().setDefaultSectionSize(60) # 增加行高以适应该封面
        
        self.records_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self._on_context_menu)
        self.records_table.cellDoubleClicked.connect(self._on_view_record_detail)
        
        table_layout.addWidget(self.records_table)
        layout.addWidget(table_container)
        
        self.content_layout.addLayout(layout)

    def _load_publish_records(self):
        """加载发布记录"""
        from src.infrastructure.common.di.service_locator import ServiceLocator
        from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
        from src.ui.utils.async_helper import AsyncWorker
        
        service_locator = ServiceLocator()
        if not service_locator.is_registered(PublishRecordRepositoryAsync):
            logger.warning("PublishRecordRepositoryAsync 未注册")
            return
            
        publish_repo = service_locator.get(PublishRecordRepositoryAsync)
        
        async def load_async():
            try:
                return await publish_repo.find_records(
                    user_id=self.user_id,
                    limit=1000
                )
            except Exception as e:
                logger.error(f"查询记录异常: {e}")
                return []
                
        worker = AsyncWorker(load_async)
        worker.finished.connect(self._on_records_loaded)
        worker.finished.connect(lambda: self._remove_worker(worker))
        worker.setParent(self)
        self._active_workers.append(worker)
        worker.start()

    def _remove_worker(self, worker):
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    def _on_records_loaded(self, records):
        self.publish_records = records
        self._apply_filters()

    def _apply_filters(self):
        """应用筛选"""
        if not hasattr(self, 'records_table'):
            return
            
        platform_filter = self.platform_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        platform_map = {
            "抖音": "douyin", "快手": "kuaishou", 
            "小红书": "xiaohongshu", "微信视频号": "wechat_video"
        }
        status_map = {"成功": "success", "失败": "failed", "待发布": "pending"}
        
        filtered = []
        for r in self.publish_records:
            # 0. 基础过滤: 只显示 target_statuses 包含的状态
            r_status = r.get('status', '')
            if self.target_statuses and r_status not in self.target_statuses:
                continue
                
            if platform_filter != "全部" and r.get('platform') != platform_map.get(platform_filter):
                continue
            if status_filter != "全部" and r_status != status_map.get(status_filter):
                continue
            filtered.append(r)
            
        self.records_table.setRowCount(len(filtered))
        
        for row, r in enumerate(filtered):
            # 0. 平台 (存储ID)
            p_display = {
                'douyin': '抖音', 'kuaishou': '快手', 
                'xiaohongshu': '小红书', 'wechat_video': '微信视频号'
            }.get(r.get('platform', ''), r.get('platform', ''))
            
            item_platform = QTableWidgetItem(p_display)
            item_platform.setData(Qt.UserRole, r.get('id')) # Store ID in UserRole
            self.records_table.setItem(row, 0, item_platform)
            
            # 1. 账号 (使用平台昵称替代备注名)
            self.records_table.setItem(row, 1, QTableWidgetItem(r.get('platform_username', '')))
            
            # 2. 文件
            fname = os.path.basename(r.get('file_path', ''))
            self.records_table.setItem(row, 2, QTableWidgetItem(fname))

            # 3. 封面
            # 简化为纯文本展示
            cover_path = r.get('cover_path', '')
            cover_text = "本地封面" if cover_path and os.path.exists(cover_path) else "首帧封面"
            self.records_table.setItem(row, 3, QTableWidgetItem(cover_text))
            
            # 4. 作品描述 (标题 | 简介)
            # 简化为纯文本展示
            title_text = r.get('title', '').strip()
            desc_text = r.get('description', '').strip()
            if title_text and desc_text:
                desc_plain = f'{title_text} | {desc_text}'
            elif title_text:
                desc_plain = title_text
            elif desc_text:
                desc_plain = desc_text
            else:
                desc_plain = '(无描述)'
            self.records_table.setItem(row, 4, QTableWidgetItem(desc_plain))
            
            # 5. 发布时间 (区分定时和立即，统一 st_str 格式)
            scheduled_time = r.get('scheduled_publish_time')
            time_display = format_schedule_time_st_str(scheduled_time) or "立即发布"
            self.records_table.setItem(row, 5, QTableWidgetItem(time_display))
            
            # 6. 状态
            status = r.get('status', '')
            s_display = {
                'success': '✅ 成功', 'failed': '❌ 失败', 'pending': '⏳ 待发布'
            }.get(status, status)
            self.records_table.setItem(row, 6, QTableWidgetItem(s_display))
            
            # 7. 操作按钮
            btn_view = PushButton("查看", self.records_table)
            btn_view.setFixedSize(60, 26) # 缩小按钮尺寸
            btn_view.clicked.connect(lambda checked, rec=r: self._on_view_detail(rec))
            
            widget_container = QWidget()
            layout_container = QHBoxLayout(widget_container)
            layout_container.setContentsMargins(0, 0, 0, 0)
            layout_container.setAlignment(Qt.AlignCenter)
            layout_container.addWidget(btn_view)
            self.records_table.setCellWidget(row, 7, widget_container)
            
            # --- 设置所有单元格居中 ---
            for col in range(8): # 遍历所有列
                 item = self.records_table.item(row, col)
                 if item:
                     item.setTextAlignment(Qt.AlignCenter)

    def _on_filter_changed(self):
        self._apply_filters()

    def _on_view_record_detail(self, row, col):
        # 从该行第0列获取 UserRole 存储的 ID (因为封面变到了第3列)
        rid_item = self.records_table.item(row, 0)
        if rid_item:
            try:
                rid = int(rid_item.data(Qt.UserRole))
                rec = next((r for r in self.publish_records if r.get('id') == rid), None)
                if rec:
                    self._on_view_detail(rec)
            except (ValueError, TypeError):
                logger.warning(f"无法获取行 {row} 的记录ID")

    def _on_context_menu(self, pos):
        """记录表格的右键菜单"""
        item = self.records_table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        menu = QMenu(self)
        
        # 定义操作动作
        action_readd = menu.addAction("重新添加到发布列表")
        action_delete = menu.addAction("删除此记录")
        
        if FLUENT_WIDGETS_AVAILABLE:
            action_readd.setIcon(FluentIcon.ADD.icon())
            action_delete.setIcon(FluentIcon.DELETE.icon())
            
        # 弹出菜单并阻塞等待结果
        action = menu.exec(self.records_table.viewport().mapToGlobal(pos))
        
        if action == action_readd:
            self._handle_readd_to_list(row)
        elif action == action_delete:
            self.records_table.selectRow(row)
            self._on_delete_records()

    def _handle_readd_to_list(self, row):
        """将选中的历史记录快速转换为待发布任务"""
        rid_item = self.records_table.item(row, 0)
        if not rid_item: return
        
        try:
            rid = int(rid_item.data(Qt.UserRole))
            rec = next((r for r in self.publish_records if r.get('id') == rid), None)
            if not rec: return
            
            # 使用 publish_repo 创建新记录 (不带状态/原ID，且清空定时)
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
            from src.ui.utils.async_helper import AsyncWorker
            
            repo = ServiceLocator().get(PublishRecordRepositoryAsync)
            
            async def copy_and_create():
                await repo.create(
                    user_id=rec.get('user_id', 1),
                    platform_username=rec.get('platform_username', ''),
                    platform=rec.get('platform', 'douyin'),
                    file_path=rec.get('file_path', ''),
                    file_type=rec.get('file_type', 'video'),
                    title=rec.get('title', ''),
                    description=rec.get('description', ''),
                    tags=rec.get('tags', ''),
                    cover_path=rec.get('cover_path', ''),
                    poi_info=rec.get('poi_info', ''),
                    micro_app_info=rec.get('micro_app_info', ''),
                    goods_info=rec.get('goods_info', ''),
                    anchor_info=rec.get('anchor_info', ''),
                    privacy_settings=rec.get('privacy_settings', '{}'),
                    scheduled_publish_time=None # 默认为立即发布
                )
            
            worker = AsyncWorker(copy_and_create)
            worker.finished.connect(lambda: InfoBar.success("添加成功", "已将记录作为新任务加到了发布列表", parent=self))
            worker.finished.connect(lambda: self._remove_worker(worker))
            worker.error.connect(lambda e: InfoBar.error("添加失败", f"重新添加失败: {e}", parent=self))
            worker.error.connect(lambda e: self._remove_worker(worker))
            worker.setParent(self)
            self._active_workers.append(worker)
            worker.start()
            
        except Exception as e:
            logger.error(f"快速添加发布记录异常: {e}", exc_info=True)

    def _on_view_detail(self, record):
        """查看详情 -> 跳转到发布页并回填数据"""
        try:
            main_window = self.window()
            target_page = None
            if hasattr(main_window, '_get_or_create_page'):
                target_page = main_window._get_or_create_page("single_publish_page")
            elif hasattr(main_window, 'single_publish_page'):
                target_page = main_window.single_publish_page
                
            if target_page and hasattr(main_window, 'switchTo'):
                # 回填数据
                if hasattr(target_page, 'set_publish_data'):
                    target_page.set_publish_data(record)
                    
                # 跳转和更新导航高亮
                main_window.switchTo(target_page)
                if hasattr(main_window, 'navigationInterface'):
                    main_window.navigationInterface.setCurrentItem("single_publish_page")
            else:
                # Fallback: 使用之前的弹窗
                from src.ui.dialogs.publish_record_detail_dialog import PublishRecordDetailDialog
                PublishRecordDetailDialog(record, self).exec()
        except Exception as e:
            logger.error(f"跳转发布页面失败: {e}")
            # Fallback
            from src.ui.dialogs.publish_record_detail_dialog import PublishRecordDetailDialog
            PublishRecordDetailDialog(record, self).exec()

    def showEvent(self, event):
        """页面显示时自动刷新数据"""
        super().showEvent(event)
        self._load_publish_records()

    def _on_export_records(self):
        # 简化版导出，逻辑与之前类似
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "导出", "导出功能暂时未迁移，请联系管理员")

    def _on_delete_records(self):
        """删除选中记录"""
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'records_table'):
            return
            
        selected_rows = self.records_table.selectionModel().selectedRows()
        if not selected_rows:
            InfoBar.warning("未选择", "请先选择要删除的发布任务", parent=self)
            return
            
        # 获取选中行的ID
        record_ids = []
        for index in selected_rows:
            # ID存储在第0列（平台）的 UserRole 中
            item = self.records_table.item(index.row(), 0)
            if item:
                try:
                    rid = item.data(Qt.UserRole)
                    if rid is not None:
                        record_ids.append(int(rid))
                except (ValueError, TypeError):
                    pass
                    
        if not record_ids:
            return
            
        # 确认对话框
        # 确认对话框
        title = "确认删除"
        content = f"确定要删除选中的 {len(record_ids)} 条发布任务吗？此操作无法撤销。"
        w = MessageBox(title, content, self.window())
        if not w.exec():
            return
                
        # 执行删除
        from src.infrastructure.common.di.service_locator import ServiceLocator
        from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
        from src.ui.utils.async_helper import AsyncWorker
        
        service_locator = ServiceLocator()
        publish_repo = service_locator.get(PublishRecordRepositoryAsync)
        
        async def delete_async():
            return await publish_repo.delete_batch(record_ids)
            
        worker = AsyncWorker(delete_async)
        worker.finished.connect(lambda result: self._on_delete_finished(result))
        worker.finished.connect(lambda: self._remove_worker(worker))
        worker.setParent(self)
        self._active_workers.append(worker)
        worker.start()
        
    def _on_delete_finished(self, success):
        if success:
            InfoBar.success("删除成功", "选中的发布任务已删除", parent=self)
            self._load_publish_records()
        else:
            InfoBar.error("删除失败", "删除发布任务时发生错误", parent=self)

    def _on_start_publish(self):
        """开始发布任务"""
        from PySide6.QtWidgets import QMessageBox
        
        if not pending_records:
            InfoBar.warning("无任务", "当前没有待发布的任务", parent=self)
            return
        
        # 按创建时间排序，获取第一个任务
        pending_records.sort(key=lambda x: x.get('created_at', ''))
        first_task = pending_records[0]
        
        # 获取任务信息
        platform_username = first_task.get('platform_username', '')
        platform = first_task.get('platform', '')
        
        if not platform_username or not platform:
            InfoBar.error("任务信息不完整", "第一个待发布任务缺少账号或平台信息", parent=self)
            return
        
        logger.info(f"开始发布任务：账号={platform_username}, 平台={platform}")
        
        # 获取账号ID
        from src.infrastructure.common.di.service_locator import ServiceLocator
        from src.domain.repositories.account_repository_async import AccountRepositoryAsync
        from src.ui.utils.async_helper import AsyncWorker
        
        service_locator = ServiceLocator()
        account_repo = service_locator.get(AccountRepositoryAsync)
        
        async def get_account_info():
            """异步获取账号信息"""
            # 通过平台昵称和平台查询账号ID
            accounts = await account_repo.find_all(user_id=1)
            logger.info(f"查询到 {len(accounts)} 个账号")
            
            for acc in accounts:
                logger.info(f"账号: {acc.get('platform_username')}, 平台: {acc.get('platform')}, ID: {acc.get('id')}")
                
                # 匹配逻辑：平台和平台昵称都必须一致
                if acc.get('platform') == platform and acc.get('platform_username') == platform_username:
                    logger.info(f"找到匹配账号: {acc}")
                    return acc
            
            logger.warning(f"未找到匹配账号: platform_username={platform_username}, platform={platform}")
            return None
        
        def on_account_loaded(account_info):
            """账号信息加载完成"""
            if not account_info:
                InfoBar.error("账号不存在", f"未找到账号: {platform_username} ({platform})", parent=self)
                return
            
            account_id = account_info.get('id')
            
            # 平台URL映射
            platform_urls = {
                'douyin': 'https://creator.douyin.com/',
                'kuaishou': 'https://cp.kuaishou.com/',
                'xiaohongshu': 'https://creator.xiaohongshu.com/',
                'wechat_video': 'https://channels.weixin.qq.com/'
            }
            
            platform_url = platform_urls.get(platform)
            if not platform_url:
                InfoBar.error("不支持的平台", f"平台 {platform} 暂不支持", parent=self)
                return
            
            # 跳转到浏览器页面并打开账号
            try:
                main_window = self.window()
                
                # 获取配置的浏览器方案
                service_locator = ServiceLocator()
                from src.infrastructure.common.config.config_center import ConfigCenter
                config_center = service_locator.get(ConfigCenter)
                app_config = config_center.get_app_config()
                scheme = app_config.get("browser_scheme", "playwright")
                
                if scheme == "playwright" or scheme == "undetected_playwright":
                     # 纯净方案/Playwright：使用 AccountPage 的方法打开外部浏览器
                     if hasattr(main_window, 'account_page'):
                         logger.info(f"使用外部浏览器打开账号: {platform_username}")
                         main_window.account_page._open_playwright_browser_for_account(
                             account_id=account_id,
                             platform_username=platform_username,
                             platform=platform,
                             platform_url=platform_url
                         )
                         InfoBar.success(
                             "开始发布", 
                             f"正在启动外部浏览器打开 {platform_username} 的创作者中心...", 
                             parent=self
                         )
                     else:
                         InfoBar.warning("无法跳转", "未找到账号管理页面", parent=self)
                else:
                    # 混合方案：使用内置 QWebEngineView (BrowserPage)
                    if hasattr(main_window, 'browser_page') and hasattr(main_window, 'switchTo'):
                        # 先切换到浏览器页面
                        main_window.switchTo(main_window.browser_page)
                        
                        # 打开账号对应的创作者中心
                        browser_page = main_window.browser_page
                        browser_page.load_account_with_cookie(
                            account_id=account_id,
                            platform_username=platform_username,
                            platform=platform,
                            platform_url=platform_url
                        )
                        
                        logger.info(f"已打开账号 {platform_username} 的创作者中心: {platform_url}")
                        
                        InfoBar.success(
                            "开始发布", 
                            f"已打开 {platform_username} 的创作者中心，共 {len(pending_records)} 个待发布任务", 
                            parent=self
                        )
                    else:
                        InfoBar.warning("无法跳转", "未找到浏览器页面", parent=self)
            except Exception as e:
                logger.error(f"打开浏览器页面失败: {e}", exc_info=True)
                InfoBar.error("跳转失败", f"打开浏览器页面时发生错误: {str(e)}", parent=self)
        
        def on_error(error):
            """加载失败"""
            logger.error(f"获取账号信息失败: {error}")
            InfoBar.error("加载失败", f"获取账号信息失败: {str(error)}", parent=self)
        
        # 异步加载账号信息
        worker = AsyncWorker(get_account_info)
        worker.finished.connect(on_account_loaded)
        worker.error.connect(on_error)
        worker.setParent(self)
        worker.start()
    
    def _on_open_browser(self):
        """打开浏览器页面"""
        try:
            main_window = self.window()
            # 假设主窗口有 browser_page 属性
            if hasattr(main_window, 'browser_page') and hasattr(main_window, 'switchTo'):
                main_window.switchTo(main_window.browser_page)
            else:
                InfoBar.warning("无法跳转", "未找到浏览器页面", parent=self)
        except Exception as e:
            logger.error(f"打开浏览器页面失败: {e}")
            InfoBar.error("跳转失败", f"打开浏览器页面时发生错误: {str(e)}", parent=self)

    def _on_stop_publish(self):
        """停止发布（子类重写）"""
        pass

    def _on_pause_publish(self):
        """暂停/继续发布（子类重写）"""
        pass
    
    def _on_speed_changed(self, index: int):
        """速度设置变更时保存"""
        settings = QSettings("WeMediaBaby", "PublishSettings")
        settings.setValue("speed_index", index)
        logger.info(f"速度设置已保存: index={index}")
    
    def _load_speed_setting(self):
        """加载保存的速度设置"""
        try:
            settings = QSettings("WeMediaBaby", "PublishSettings")
            saved_index = settings.value("speed_index", 0, type=int)
            if 0 <= saved_index <= 2:
                self.combo_speed_setting.setCurrentIndex(saved_index)
                logger.info(f"速度设置已加载: index={saved_index}")
        except Exception as e:
            logger.debug(f"加载速度设置失败: {e}")

