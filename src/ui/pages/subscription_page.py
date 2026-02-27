"""
个人中心页面 (原订阅管理页面)
文件路径：src/ui/pages/subscription_page.py
功能：个人中心，整合账户管理、订阅状态、套餐展示
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer
import logging

from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
    MessageBox, InfoBar, InfoBarPosition, FluentIcon, IconWidget, TitleLabel,
    CaptionLabel
)
FLUENT_WIDGETS_AVAILABLE = True

from .base_page import BasePage

logger = logging.getLogger(__name__)


class PersonalCenterPage(BasePage):
    """个人中心页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化个人中心页面"""
        super().__init__("个人中心", parent)
        self.user_id = 1  # 默认用户ID，后续对接真实用户
        self._current_user = None # 当前登录用户信息
        
        self.subscription_manager = None
        self.payment_handler = None
        self._active_workers = []  # 保存所有活动的AsyncWorker引用
        
        self._init_services()
        self._setup_content()
        
        # 延迟加载信息
        QTimer.singleShot(100, self._init_data)
    
    def _init_data(self):
        """初始化数据"""
        self._update_account_status() # 更新一次账户显示（初始为未登录）
        self._load_subscription_info()
        self._load_plans()

    def _init_services(self):
        """初始化服务"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.services.subscription.subscription_manager_async import SubscriptionManagerAsync
            from src.infrastructure.common.event.event_bus import EventBus
            
            service_locator = ServiceLocator()
            event_bus = service_locator.get(EventBus) if service_locator.is_registered(EventBus) else None
            
            # 创建订阅管理器（异步版本）
            self.subscription_manager = SubscriptionManagerAsync(
                user_id=self.user_id,
                event_bus=event_bus
            )
            
            # 注意：支付处理器需要单独异步化，暂时设为None
            self.payment_handler = None
            
            logger.info("个人中心服务初始化成功")
        except Exception as e:
            logger.error(f"初始化个人中心服务失败: {e}", exc_info=True)
    
    def _setup_content(self):
        """设置内容"""

        
        # 1. 顶部区域：账户信息 + 订阅状态 (并排)
        top_section = QHBoxLayout()
        top_section.setSpacing(16)
        
        # 账户卡片 (左)
        self.account_card = self._create_account_card()
        # 订阅状态卡片 (右)
        self.status_card = self._create_status_card()
        
        top_section.addWidget(self.account_card, 1) # 比例 1
        top_section.addWidget(self.status_card, 1)  # 比例 1
        
        self.content_layout.addLayout(top_section)
        
        self.content_layout.addSpacing(20)
        
        # 2. 套餐展示区域
        plans_header = QHBoxLayout()
        plans_icon = IconWidget(FluentIcon.SHOPPING_CART, self)
        plans_icon.setFixedSize(20, 20)
        plans_title = SubtitleLabel("订阅套餐", self)
        plans_header.addWidget(plans_icon)
        plans_header.addWidget(plans_title)
        plans_header.addStretch()
        self.content_layout.addLayout(plans_header)
        
        # 套餐卡片容器
        self.plans_container = QWidget(self)
        plans_layout = QHBoxLayout(self.plans_container)
        plans_layout.setContentsMargins(0, 8, 0, 8)
        plans_layout.setSpacing(20)
        self.content_layout.addWidget(self.plans_container)
        
        self.content_layout.addStretch() # 底部弹簧
    
    def _create_account_card(self) -> QWidget:
        """创建账户信息卡片"""
        card = CardWidget(self)
        card.setFixedHeight(180) # 固定高度与右侧一致
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        
        # 标题
        header = QHBoxLayout()
        icon = IconWidget(FluentIcon.CERTIFICATE, card)
        icon.setFixedSize(18, 18)
        title = BodyLabel("我的账户", card)
        title.setStyleSheet("font-weight: bold; color: #666;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)
        
        card_layout.addStretch()
        
        # 用户信息主体
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        # 头像
        self.avatar_widget = IconWidget(FluentIcon.CERTIFICATE, card)
        self.avatar_widget.setFixedSize(56, 56)
        self.avatar_widget.setStyleSheet("""
            background-color: rgba(0, 120, 212, 0.1);
            color: #0078D4;
            border-radius: 28px;
            padding: 12px;
        """)
        
        # 文字信息
        text_info = QVBoxLayout()
        text_info.setSpacing(4)
        text_info.setAlignment(Qt.AlignVCenter)
        self.account_status_label = TitleLabel("未登录", card)
        self.account_desc_label = CaptionLabel("登录解锁更多高级权益", card)
        self.account_desc_label.setTextColor(Qt.GlobalColor.gray, Qt.GlobalColor.gray)
        text_info.addWidget(self.account_status_label)
        text_info.addWidget(self.account_desc_label)
        
        info_layout.addWidget(self.avatar_widget)
        info_layout.addLayout(text_info)
        info_layout.addStretch()
        card_layout.addLayout(info_layout)
        
        card_layout.addStretch()

        # 按钮区域 (底部右侧)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_login = PrimaryPushButton("登录/注册", card)
        self.btn_login.clicked.connect(self._on_login)
        self.btn_login.setFixedHeight(32)
        
        self.btn_logout = PushButton("退出登录", card)
        self.btn_logout.clicked.connect(self._on_logout)
        self.btn_logout.setVisible(False)
        self.btn_logout.setFixedHeight(32)
        
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_logout)
        card_layout.addLayout(btn_layout)
        
        return card

    def _create_status_card(self) -> QWidget:
        """创建订阅状态卡片"""
        card = CardWidget(self)
        card.setFixedHeight(180)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        
        # 标题
        header = QHBoxLayout()
        icon = IconWidget(FluentIcon.CERTIFICATE, card)
        icon.setFixedSize(18, 18)
        title = BodyLabel("订阅权益", card)
        title.setStyleSheet("font-weight: bold; color: #666;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        # 刷新小按钮
        btn_refresh = PushButton(FluentIcon.SYNC, "刷新", card)
        btn_refresh.setFixedSize(60, 26)
        btn_refresh.clicked.connect(self._load_subscription_info)
        header.addWidget(btn_refresh)
        card_layout.addLayout(header)
        
        card_layout.addStretch()
        
        # 状态显示
        self.status_label = TitleLabel("检测中...", card)
        self.status_label.setStyleSheet("font-size: 20px; color: #0078d4;")
        self.status_desc = BodyLabel("正在获取您的订阅信息", card)
        self.status_desc.setStyleSheet("color: #666;")
        
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.status_desc)
        
        card_layout.addStretch()
        
        return card

    # --- 账户相关逻辑 ---

    def _on_login(self):
        """打开登录对话框"""
        try:
            from ..dialogs.login_dialog import LoginDialog
            dialog = LoginDialog(self)
            dialog.login_success.connect(self._on_login_success)
            dialog.exec()
        except ImportError:
             # 临时 Mock 登录用于演示
             self._on_login_success({'username': 'AdminUser', 'id': 1})
             self.show_success("演示模式", "已模拟登录成功")
        except Exception as e:
            logger.error(f"登录失败: {e}", exc_info=True)

    def _on_login_success(self, user_info: dict):
        """登录成功回调"""
        self._current_user = user_info
        self._update_account_status()
        self.show_success("登录成功", f"欢迎回来，{user_info.get('username', '用户')}！")

    def _on_logout(self):
        """退出登录"""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "确认退出", "确定要退出登录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._current_user = None
            self._update_account_status()
            self.show_success("已退出", "您已成功退出登录")

    def _update_account_status(self):
        """更新账户卡片状态"""
        if self._current_user:
            username = self._current_user.get('username', '用户')
            self.account_status_label.setText(username)
            self.account_desc_label.setText("普世版用户 (ID: 8888)") # 示例展示
            self.btn_login.setVisible(False)
            self.btn_logout.setVisible(True)
            # 可选：更新头像颜色表示已登录
            self.avatar_widget.setStyleSheet("""
                background-color: rgba(16, 124, 16, 0.1); 
                border-radius: 28px;
                padding: 12px;
            """)
        else:
            self.account_status_label.setText("未登录")
            self.account_desc_label.setText("登录解锁更多高级权益")
            self.btn_login.setVisible(True)
            self.btn_logout.setVisible(False)
            self.avatar_widget.setStyleSheet("""
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 28px;
                padding: 12px;
            """)

    # --- 订阅与支付相关逻辑 (保留原有大部分逻辑，略作适配) ---

    def _load_subscription_info(self):
        """加载订阅信息"""
        if not self.subscription_manager:
            return
        
        try:
            from ..utils.async_helper import AsyncWorker
            async def load_async():
                subscription = await self.subscription_manager.get_user_subscription()
                is_active = await self.subscription_manager.check_subscription_active()
                return {'subscription': subscription, 'is_active': is_active}
            
            worker = AsyncWorker(load_async)
            worker.finished.connect(self._on_subscription_loaded)
            worker.error.connect(self._on_subscription_load_error)
            worker.setParent(self)
            worker.start()
        except Exception as e:
            logger.error(f"加载订阅信息失败: {e}")

    def _on_subscription_loaded(self, result):
        """订阅加载完成"""
        try:
            subscription = result.get('subscription')
            is_active = result.get('is_active', False)
            
            if is_active and subscription:
                plan_name = {
                    'monthly': '月付会员',
                    'yearly': '年付会员'
                }.get(subscription.get('plan_type', ''), '高级会员')
                
                end_date = subscription.get('end_date', '未知')
                if ' ' in str(end_date): end_date = str(end_date).split(' ')[0]

                self.status_label.setText(f"{plan_name}")
                self.status_desc.setText(f"有效期至：{end_date}")
            else:
                self.status_label.setText("免费试用版")
                self.status_desc.setText("今日剩余免费发布次数: 5") # 示例逻辑
        except Exception as e:
            logger.error(f"处理订阅信息UI刷新失败: {e}")

    def _on_subscription_load_error(self, error):
        self.status_label.setText("状态未知")
        self.status_desc.setText("网络连接超时")

    def _load_plans(self):
        """加载套餐列表 (保持原有逻辑，简化UI创建)"""
        # ... (此处复用原有逻辑，但注意 plans_container 已变更为新的布局)
        if not self.subscription_manager:
            # 演示数据
            self._create_demo_plans()
            return

        try:
            plans = self.subscription_manager.get_subscription_plans()
            # 清理旧卡片
            while self.plans_container.layout().count():
                item = self.plans_container.layout().takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            for plan in plans:
                if plan.get('plan_type') == 'trial': continue
                self.plans_container.layout().addWidget(self._create_plan_card(plan))
        except Exception:
            self._create_demo_plans()

    def _create_demo_plans(self):
        """创建演示套餐卡片"""
        # 清理
        layout = self.plans_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        demo_plans = [
             {'name': '月付会员', 'price': '19.9', 'plan_type': 'monthly', 'description': '适合短期灵活使用的创作者', 'features': ['每日无限量发布', '优先技术支持', '去除水印']},
             {'name': '年付会员', 'price': '199', 'plan_type': 'yearly', 'description': '长期创作首选，立省40元', 'features': ['包含所有月付权益', '专属客服经理', '新功能优先体验']}
        ]
        
        for plan in demo_plans:
            layout.addWidget(self._create_plan_card(plan))
            
    def _create_plan_card(self, plan: dict) -> QWidget:
        """创建单个套餐卡片"""
        card = CardWidget(self)
        card.setFixedWidth(280)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        
        # 推荐标签
        if plan['plan_type'] == 'yearly':
            badge = QLabel("🔥 推荐", card)
            badge.setStyleSheet("color: #FF5722; font-weight: bold; font-size: 12px;")
            card_layout.addWidget(badge, 0, Qt.AlignRight)
        else:
            card_layout.addSpacing(18) # 占位
            
        # 标题与价格
        title = SubtitleLabel(plan['name'], card)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        
        price_line = QHBoxLayout()
        price = TitleLabel(f"¥{plan['price']}", card)
        price.setStyleSheet("color: #0078d4; font-size: 28px; font-weight: bold;")
        unit = CaptionLabel("/月" if 'monthly' in plan['plan_type'] else "/年", card)
        price_line.addStretch()
        price_line.addWidget(price)
        price_line.addWidget(unit)
        price_line.addStretch()
        card_layout.addLayout(price_line)
        
        desc = BodyLabel(plan['description'], card)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; font-size: 12px;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)
        
        # 分割线
        line = QFrame(card); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #eee;"); card_layout.addWidget(line)
        
        # 权益
        for feat in plan.get('features', []):
            item = QHBoxLayout()
            icon = IconWidget(FluentIcon.ACCEPT, card)
            icon.setFixedSize(14, 14)
            icon.setStyleSheet("color: green;")
            lbl = BodyLabel(feat, card)
            lbl.setStyleSheet("font-size: 12px;")
            item.addWidget(icon); item.addWidget(lbl); item.addStretch()
            card_layout.addLayout(item)
            
        card_layout.addStretch()
        
        btn = PrimaryPushButton("立即开通", card)
        btn.clicked.connect(lambda: self._on_subscribe_clicked(plan))
        card_layout.addWidget(btn)
        
        return card

    def _on_subscribe_clicked(self, plan):
        InfoBar.info("功能演示", f"正在发起 {plan['name']} 的支付请求...", duration=2000, parent=self)
        
    def closeEvent(self, event):
        for worker in self._active_workers:
            if worker.isRunning(): worker.terminate()
        super().closeEvent(event)
