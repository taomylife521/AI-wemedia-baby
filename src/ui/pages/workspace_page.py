"""
工作台页面
文件路径：src/ui/pages/workspace_page.py
功能：工作台页面，显示概览信息和快速操作
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import QTimer, Qt
import logging

from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, TitleLabel,
    CaptionLabel, PrimaryPushButton, PushButton, IndeterminateProgressRing,
    FluentIcon, IconWidget, HyperlinkButton, TransparentToolButton, DisplayLabel
)
FLUENT_WIDGETS_AVAILABLE = True

from .base_page import BasePage
from ..utils.async_helper import AsyncWorker

logger = logging.getLogger(__name__)


class WorkspacePage(BasePage):
    """工作台页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化工作台页面"""
        super().__init__("工作台", parent)
        self.user_id = 1  # 默认用户ID，实际应该从登录状态获取
        self.dashboard_service = None
        self._active_workers = []  # 保存所有活动的AsyncWorker引用
        self._is_loading = False
        self._init_services()
        self._setup_content()
        self._setup_refresh_timer()
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.services.account.account_manager_async import AccountManagerAsync
            from src.services.workspace.dashboard_service import DashboardService
            from src.infrastructure.common.event.event_bus import EventBus
            
            service_locator = ServiceLocator()
            event_bus = service_locator.get(EventBus)
            
            # 创建账号管理器
            account_manager = AccountManagerAsync(
                user_id=self.user_id,
                event_bus=event_bus
            )
            
            # 尝试加载批量任务管理器 (Pro功能)
            batch_task_manager = None
            try:
                from src.pro_features.batch.services.batch_task_manager_async import BatchTaskManagerAsync
                batch_task_manager = BatchTaskManagerAsync(
                    user_id=self.user_id,
                    event_bus=event_bus
                )
            except ImportError:
                logger.info("批量任务管理器不可用 (Pro功能未安装)")
            
            # 创建数据统计服务
            self.dashboard_service = DashboardService(
                user_id=self.user_id,
                account_manager=account_manager,
                batch_task_manager=batch_task_manager
            )
            
            logger.debug("工作台服务初始化成功")
        except Exception as e:
            logger.error(f"初始化工作台服务失败: {e}", exc_info=True)
    
    def _setup_refresh_timer(self):
        """设置刷新定时器"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(60000)  # 每60秒刷新一次
    
    def _setup_content(self):
        """设置内容"""
        # 应用全局样式
        # 应用全局样式
        # ThemeManager 已接管样式加载，无需手动加载
        pass


            
        # 导入组件
        from ..components.statistics_card import StatisticsCard
        from ..components.quick_action_card import QuickActionCard
        from ..components.recent_activity import RecentActivityWidget
        
        try:
            from ..components.charts import PlatformDistributionChart, PublishTrendChart
            CHARTS_AVAILABLE = True
        except ImportError:
            CHARTS_AVAILABLE = False
        
        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(30, 30, 30, 30) # 增加边距
        scroll_layout.setSpacing(24) # 增加间距
        
        # 1. 欢迎标题区域
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 10, 0, 0) # 增加顶部间距
        title_layout.setSpacing(8)
        
        
        date_str = ""
        try:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y年%m月%d日")
        except:
            pass
        welcome_desc = BodyLabel(f"欢迎回来，今天是 {date_str}。以下是您的账号概览。", self)
        # welcome_desc.setStyleSheet("color: #666;") # Removed for Dark Mode compatibility
        
        # title_layout.addWidget(welcome_title) # Removed as requested
        title_layout.addWidget(welcome_desc)
        scroll_layout.addWidget(title_widget)

        # 2. 统计卡片区域（一行布局）
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.account_card = StatisticsCard("账号总数", "0", "0 在线 | 0 离线", FluentIcon.PEOPLE, self)
        self.publish_card = StatisticsCard("今日发布", "0", "0 成功 | 0 失败", FluentIcon.SEND, self)
        self.task_card = StatisticsCard("待执行任务", "0", "完成率 0%", FluentIcon.FOLDER, self)
        self.success_rate_card = StatisticsCard("发布成功率", "0%", "近7天数据", FluentIcon.ACCEPT, self)
        
        stats_layout.addWidget(self.account_card)
        stats_layout.addWidget(self.publish_card)
        stats_layout.addWidget(self.task_card)
        stats_layout.addWidget(self.success_rate_card)
        
        scroll_layout.addLayout(stats_layout)
        
        # 3. 主体内容区域 (左右分栏: 左侧图表/快捷操作，右侧动态)
        main_content_grid = QGridLayout()
        main_content_grid.setSpacing(20)
        main_content_grid.setColumnStretch(0, 2) # 左侧宽
        main_content_grid.setColumnStretch(1, 1) # 右侧窄
        
        # --- 左侧内容 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # 3.1 快捷操作
        actions_label = SubtitleLabel("快速操作", self)
        left_layout.addWidget(actions_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)
        
        self.action_add_account = QuickActionCard(FluentIcon.ADD, "添加账号", "绑定新平台账号", self)
        self.action_publish = QuickActionCard(FluentIcon.EDIT, "发布内容", "创建新的发布任务", self) # 使用 Edit 或 Send
        self.action_manager = QuickActionCard(FluentIcon.PEOPLE, "账号管理", "管理已绑定账号", self)
        
        self.action_add_account.clicked.connect(self._on_add_account_clicked)
        self.action_publish.clicked.connect(self._on_quick_publish_clicked)
        self.action_manager.clicked.connect(self._on_navigate_to_account)
        
        actions_layout.addWidget(self.action_add_account)
        actions_layout.addWidget(self.action_publish)
        actions_layout.addWidget(self.action_manager)
        
        left_layout.addLayout(actions_layout)
        
        # 3.2 图表 (如果可用)
        if CHARTS_AVAILABLE:
            chart_title = SubtitleLabel("数据概览", self)
            left_layout.addWidget(chart_title)
            
            charts_layout = QHBoxLayout()
            self.platform_chart = PlatformDistributionChart(self)
            self.platform_chart.setFixedHeight(320)
            charts_layout.addWidget(self.platform_chart)
            
            self.trend_chart = PublishTrendChart(self)
            self.trend_chart.setFixedHeight(320)
            charts_layout.addWidget(self.trend_chart)
            
            left_layout.addLayout(charts_layout)
        
        left_layout.addStretch()
        main_content_grid.addWidget(left_panel, 0, 0)
        
        # --- 右侧内容 (最近活动) ---
        self.recent_activity = RecentActivityWidget(self)
        self.recent_activity.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        main_content_grid.addWidget(self.recent_activity, 0, 1)
        
        scroll_layout.addLayout(main_content_grid)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        self.content_layout.addWidget(scroll_area)
        
        # 加载数据
        self._refresh_data()
    
    def _refresh_data(self):
        """刷新数据（异步）"""
        if not self.dashboard_service or self._is_loading:
            return
        
        self._is_loading = True
        
        # 使用异步方式加载数据
        async def load_dashboard_data():
            return self.dashboard_service.get_dashboard_data()
        
        worker = AsyncWorker(load_dashboard_data)
        worker.finished.connect(self._on_data_loaded)
        worker.error.connect(self._on_data_load_error)
        self._active_workers.append(worker)
        worker.setParent(self)
        worker.start()


    def _on_data_loaded(self, dashboard_data: Dict[str, Any]):
        """数据加载完成回调"""
        try:
            self._is_loading = False
            
            # 更新账号数量卡片
            account_stats = dashboard_data.get('account', {})
            account_total = account_stats.get('total', 0)
            account_online = account_stats.get('online', 0)
            account_offline = account_stats.get('offline', 0)
            if hasattr(self, 'account_card'):
                self.account_card.set_value(str(account_total))
                self.account_card.set_description(f"{account_online} 在线 | {account_offline} 离线")
            
            # 更新今日发布卡片
            publish_stats = dashboard_data.get('publish', {})
            today_count = publish_stats.get('today_count', 0)
            today_success = publish_stats.get('today_success', 0)
            today_failed = publish_stats.get('today_failed', 0)
            publish_total = publish_stats.get('total', 0)
            if hasattr(self, 'publish_card'):
                self.publish_card.set_value(str(today_count))
                self.publish_card.set_description(f"{today_success} 成功 | {today_failed} 失败")
            
            # 更新任务统计卡片
            task_stats = dashboard_data.get('task', {})
            task_total = task_stats.get('total', 0)
            task_pending = task_stats.get('by_status', {}).get('pending', 0)
            completion_rate = task_stats.get('completion_rate', 0)
            if hasattr(self, 'task_card'):
                self.task_card.set_value(str(task_pending))
                self.task_card.set_description(f"总任务: {task_total} | 完成: {completion_rate:.0f}%")
            
            # 更新成功率卡片
            if publish_total > 0:
                success_rate = (publish_stats.get('success', 0) / publish_total * 100)
            else:
                success_rate = 0
            if hasattr(self, 'success_rate_card'):
                self.success_rate_card.set_value(f"{success_rate:.1f}%")
                # self.success_rate_card.set_description("近7天发布成功率")
            
            # 更新平台分布（将英文平台 ID 转为中文显示名称）
            platform_stats = account_stats.get('by_platform', {})
            if hasattr(self, 'platform_chart') and platform_stats:
                # 平台名称中文映射表
                platform_name_map = {
                    'douyin': '抖音',
                    'kuaishou': '快手',
                    'wechat_video': '视频号',
                    'xiaohongshu': '小红书',
                    'bilibili': '哔哩哔哩',
                    'weibo': '微博',
                }
                platform_stats_cn = {
                    platform_name_map.get(k, k): v
                    for k, v in platform_stats.items()
                }
                self.platform_chart.set_data(platform_stats_cn)
            
            # 更新发布趋势
            trend_data = publish_stats.get('daily_stats', []) 
            if hasattr(self, 'trend_chart') and trend_data:
                self.trend_chart.set_data(trend_data)

            # 更新最近活动
            # 将后端数据转换为 RecentActivityWidget 需要的格式
            publish_records = publish_stats.get('recent_records', [])
            activity_items = []
            
            for r in publish_records[:8]: # 最多显示8条
                status_raw = r.get('status', 'unknown')
                status_ui = 'info'
                icon = FluentIcon.INFO
                
                if status_raw == 'success':
                    status_ui = 'success'
                    icon = FluentIcon.ACCEPT
                elif status_raw == 'failed':
                    status_ui = 'failed'
                    icon = FluentIcon.CANCEL
                
                activity_items.append({
                    'title': f"发布到 {r.get('platform', '未知平台')}",
                    'subtitle': f"{r.get('platform_username', '未知账号')} - {r.get('title', '无标题')}",
                    'time': r.get('time', '刚刚'), # 需要后端提供格式化后的时间，或在此处格式化
                    'status': status_ui,
                    'icon': icon
                })
            
            if hasattr(self, 'recent_activity'):
                 # 如果没有记录，也要传空列表进去以显示空状态
                self.recent_activity.set_activities(activity_items)
                    
        except Exception as e:
            logger.error(f"更新工作台数据失败: {e}", exc_info=True)
            self._is_loading = False

    def _on_data_load_error(self, error: str):
        """数据加载错误回调"""
        logger.error(f"加载工作台数据失败: {error}")
        self._is_loading = False
    
    def _on_add_account_clicked(self):
        """添加账号按钮点击"""
        self._navigate_to_page("account_page")
    
    def _on_quick_publish_clicked(self):
        """快速发布按钮点击"""
        self._navigate_to_page("publish_page")
    
    def _on_batch_task_clicked(self):
        """批量任务按钮点击"""
        self._navigate_to_page("publish_page")
    
    def _on_navigate_to_account(self):
        """导航到账号管理页面"""
        self._navigate_to_page("account_page")
    
    def _on_navigate_to_publish(self):
        """导航到发布管理页面"""
        self._navigate_to_page("publish_page")
    
    def _on_navigate_to_file(self):
        """导航到文件管理页面"""
        self._navigate_to_page("file_page")
    
    def _on_navigate_to_browser(self):
        """导航到浏览器页面"""
        self._navigate_to_page("browser_page")
    
    def _navigate_to_page(self, page_name: str):
        """导航到指定页面
        
        Args:
            page_name: 页面名称（如 "account_page", "publish_page"）
        """
        try:
            main_window = self.window()
            if not main_window:
                return
            
            # 获取页面对象
            page = getattr(main_window, page_name, None)
            if not page:
                logger.warning(f"页面不存在: {page_name}")
                return
            
            # 切换到页面
            if hasattr(main_window, 'switchTo'):
                main_window.switchTo(page)
            elif hasattr(main_window, 'navigationInterface'):
                nav = main_window.navigationInterface
                if hasattr(nav, 'stackedWidget'):
                    stacked = nav.stackedWidget
                    idx = stacked.indexOf(page)
                    if idx >= 0:
                        stacked.setCurrentIndex(idx)
        except Exception as e:
            logger.error(f"导航到页面失败: {e}", exc_info=True)

