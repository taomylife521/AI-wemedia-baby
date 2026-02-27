from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class LoginResult:
    """登录结果数据类"""
    success: bool
    cookies: Optional[Dict] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    is_valid: bool = True # 默认有效

@dataclass
class AccountVerificationContext:
    """账号验证上下文"""
    account_id: int
    account_name: str
    platform: str
    cookies: Dict[str, str]
    user_agent: Optional[str] = None
    http_session: Optional[object] = None # aiohttp.ClientSession
    service_locator: Optional[object] = None # ServiceLocator

class LoginPluginInterface(ABC):
    """登录插件抽象接口"""

    # ... (existing properties)

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """平台标识 (如: douyin, kuaishou)"""
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台显示名称 (如: 抖音, 快手)"""
        pass

    @property
    @abstractmethod
    def login_url(self) -> str:
        """创作者中心登录URL"""
        pass
    
    @property
    def check_url(self) -> str:
        """用于 HTTP 验证的 URL，默认同登录页"""
        return self.login_url

    @property
    def cookie_domain(self) -> str:
        """
        Cookie域名
        默认实现为 .{platform_id}.com，子类可覆盖
        """
        return f".{self.platform_id}.com"

    @abstractmethod
    async def check_login_status(self, context) -> bool:
        """检查是否已登录 (基于 Playwright 页面环境)"""
        pass
    
    @abstractmethod
    async def verify_cookie_http(self, session, cookies: Dict[str, str], user_agent: Optional[str] = None) -> LoginResult:
        """
        [已过时] 请使用 verify_account_status
        通过纯 HTTP 请求验证 Cookie 有效性
        """
        pass

    async def verify_account_status(self, context: AccountVerificationContext) -> LoginResult:
        """
        验证账号状态 (统一入口)
        默认实现调用 extract_cookie_http，子类可重写以实现更复杂的逻辑 (如 Headless)
        """
        if context.http_session:
             return await self.verify_cookie_http(
                 context.http_session, 
                 context.cookies, 
                 context.user_agent
             )
        return LoginResult(success=False, error_message="缺少 HTTP Session")

    @abstractmethod
    async def extract_user_info(self, context) -> LoginResult:
        """提取用户信息 (Cookie/昵称等)"""
        pass

    async def wait_for_login(self, context, timeout: int = 900) -> LoginResult:
        """
        等待用户登录完成 (默认实现：轮询检测)
        
        Args:
            context: 浏览器上下文
            timeout: 超时时间(秒)，默认15分钟
        """
        import asyncio
        # 每3秒检测一次
        check_interval = 3
        max_attempts = timeout // check_interval
        
        for _ in range(max_attempts):
            try:
                if await self.check_login_status(context):
                    return await self.extract_user_info(context)
            except Exception:
                # 忽略检测过程中的临时错误
                pass
            await asyncio.sleep(check_interval)
            
        return LoginResult(success=False, error_message="登录超时，请重试")
