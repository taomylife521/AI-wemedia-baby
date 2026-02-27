"""
账号加载过滤器（异步版本）
文件路径：src/business/publish_pipeline/filters/account_load_filter_async.py
功能：加载账号信息和Cookie（异步）
"""

from typing import Optional, List, Dict, Any
from src.infrastructure.common.pipeline.base_filter import BaseFilter, PublishContext
from src.services.account.account_manager_async import AccountManagerAsync
from src.infrastructure.browser.qwebengine_browser import QWebEngineBrowser
import logging

logger = logging.getLogger(__name__)


class AccountLoadFilterAsync(BaseFilter):
    """账号加载过滤器（异步版本）"""
    
    def __init__(self, account_manager: AccountManagerAsync):
        """初始化账号加载过滤器
        
        Args:
            account_manager: 账号管理器实例（异步版本）
        """
        super().__init__()
        self.account_manager = account_manager
    
    def _convert_cookie_dict_to_list(
        self,
        cookie_dict: Dict[str, str],
        domain: str = ""
    ) -> List[Dict[str, Any]]:
        """将Cookie字典转换为列表格式
        
        Args:
            cookie_dict: Cookie字典（name: value格式）
            domain: 域名（可选）
        
        Returns:
            Cookie列表格式
        """
        cookie_list = []
        for name, value in cookie_dict.items():
            cookie_item = {
                'name': name,
                'value': value,
                'domain': domain or '.douyin.com',  # 默认抖音域名
                'path': '/',
                'secure': True,
                'httpOnly': False
            }
            cookie_list.append(cookie_item)
        return cookie_list
    
    async def process(self, context: PublishContext) -> bool:
        """加载账号信息（异步）
        
        Args:
            context: 发布上下文
        
        Returns:
            如果加载成功返回True，否则返回False
        """
        try:
            # 获取账号信息（异步）
            accounts = await self.account_manager.get_accounts(platform=context.platform)
            account = None
            for acc in accounts:
                if acc.get('account_name') == context.account_name:
                    account = acc
                    break
            
            if not account:
                self.set_error(f"账号不存在: {context.account_name}")
                return False
            
            # 将账号数据转换为Account实体（如果需要）
            # 这里暂时直接使用字典
            context.account = account
            
            # 加载Cookie（异步）
            account_id = account.get('id')
            cookie_data = await self.account_manager.load_account_cookie(account_id)
            
            if not cookie_data:
                self.set_error(f"Cookie不存在或已失效: {context.account_name}")
                return False
            
            # 创建浏览器实例
            browser = QWebEngineBrowser()
            
            # 转换Cookie格式并注入
            if isinstance(cookie_data, dict):
                # 判断是简单格式（name:value）还是完整格式（列表）
                if 'name' in cookie_data or (cookie_data and isinstance(list(cookie_data.values())[0] if cookie_data else None, dict)):
                    # 完整格式，直接使用
                    cookie_list = cookie_data if isinstance(cookie_data, list) else [cookie_data]
                else:
                    # 简单格式，转换为列表
                    domain = self._get_domain_for_platform(context.platform)
                    cookie_list = self._convert_cookie_dict_to_list(cookie_data, domain)
            elif isinstance(cookie_data, list):
                cookie_list = cookie_data
            else:
                self.set_error(f"Cookie格式不正确: {type(cookie_data)}")
                return False
            
            # 注入Cookie
            if not browser.inject_cookie(cookie_list):
                self.set_error("Cookie注入失败")
                return False
            
            # 注意：新架构中，context可能不直接存储browser
            # 这里保留兼容性
            if hasattr(context, 'browser'):
                context.browser = browser
            
            self.logger.info(f"账号加载成功: {context.account_name}")
            return True
            
        except Exception as e:
            self.set_error(f"账号加载失败: {str(e)}")
            self.logger.error(self.get_error(), exc_info=True)
            return False
    
    def _get_domain_for_platform(self, platform: str) -> str:
        """根据平台获取域名
        
        Args:
            platform: 平台名称
        
        Returns:
            域名
        """
        domain_map = {
            'douyin': '.douyin.com',
            'kuaishou': '.kuaishou.com',
            'xiaohongshu': '.xiaohongshu.com'
        }
        return domain_map.get(platform, '.douyin.com')

