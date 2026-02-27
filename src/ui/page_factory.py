import logging
from typing import Dict, Type, Optional, Any
from PySide6.QtWidgets import QWidget

# 导入所有页面类
from src.ui.pages import (
    WorkspacePage,
    AccountPage,
    BrowserPage,
    FilePage,
    SettingsPage
)

from src.ui.pages.publish import (
    PublishRecordsPage,
    SinglePublishPage
)

from src.ui.pages.account_group import AccountGroupPage
from src.ui.pages.publish.publish_list_page import PublishListPage
from src.ui.pages.publish.image_single_publish_page import ImageSinglePublishPage

logger = logging.getLogger(__name__)

class PageFactory:
    """页面工厂 - 负责管理页面类的注册和实例化"""

    def __init__(self):
        self._registry: Dict[str, Type[QWidget]] = {
            "workspace_page": WorkspacePage,
            "account_page": AccountPage,
            "account_group_page": AccountGroupPage,
            "publish_list_page": PublishListPage,
            "publish_records_page": PublishRecordsPage,
            "single_publish_page": SinglePublishPage,
            "image_single_publish_page": ImageSinglePublishPage,
            "browser_page": BrowserPage,
            "file_page": FilePage,
            "settings_page": SettingsPage
        }
        
        self._register_optional_pages()

    def _register_optional_pages(self):
        """注册基于功能开关的可选页面"""
        
        # 批量功能
        try:
            from src.pro_features.batch.pages.batch_publish_page import BatchPublishPage
            from src.pro_features.batch.pages.image_batch_publish_page import ImageBatchPublishPage
            self._registry["batch_publish_page"] = BatchPublishPage
            self._registry["image_batch_publish_page"] = ImageBatchPublishPage
        except ImportError:
            pass
            
        # 数据中心
        try:
            from src.pro_features.data_center.pages.data_center_page import DataCenterPage
            self._registry["data_center_page"] = DataCenterPage
        except ImportError:
            pass
            
        # 互动功能
        try:
            from src.pro_features.interaction.pages.comment_page import CommentPage
            from src.pro_features.interaction.pages.private_message_page import PrivateMessagePage
            self._registry["comment_page"] = CommentPage
            self._registry["private_message_page"] = PrivateMessagePage
        except ImportError:
            pass
        
        # 个人中心
        try:
            from src.ui.pages.subscription_page import PersonalCenterPage
            self._registry["personal_center_page"] = PersonalCenterPage
        except ImportError:
            pass

    def create_page(self, page_name: str, parent=None) -> Optional[QWidget]:
        """创建页面实例"""
        if page_name not in self._registry:
            logger.error(f"PageFactory: 未找到页面定义 [{page_name}]")
            return None
            
        try:
            page_class = self._registry[page_name]
            # 假设所有页面构造函数都接受 parent 参数
            page_instance = page_class(parent)
            page_instance.setObjectName(page_name)
            return page_instance
        except Exception as e:
            logger.error(f"PageFactory: 实例化页面失败 [{page_name}]: {e}", exc_info=True)
            return None

    def get_all_page_names(self) -> list[str]:
        """获取所有注册的页面名称"""
        return list(self._registry.keys())
