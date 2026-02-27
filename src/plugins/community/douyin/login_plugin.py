from typing import Dict, Any, Optional
import json
import logging

from src.plugins.core.interfaces.login_plugin import LoginPluginInterface, LoginResult
from src.plugins.core.interfaces.login_plugin import LoginPluginInterface, LoginResult
from .selectors import Selectors

logger = logging.getLogger(__name__)

class DouyinLoginPlugin(LoginPluginInterface):
    @property
    def platform_id(self) -> str:
        return "douyin"
    
    @property
    def platform_name(self) -> str:
        return "抖音"
    
    @property
    def login_url(self) -> str:
        return "https://creator.douyin.com/"
    
    async def check_login_status(self, context) -> bool:
        """检查登录状态"""
        try:
            # 1. 如果页面已加载，使用结合 Cookie 与 DOM 的检测
            pages = context.pages
            if pages:
                page = pages[0]
                # 只有在相关域名下才检查
                if "douyin.com" in page.url or "amemv.com" in page.url:
                    # 首先检查 Cookie，如果没有 Session Cookie，则可断言未登录
                    cookies = await context.cookies()
                    has_session = any(c['name'] in Selectors.REQUIRED_COOKIES for c in cookies)
                    if not has_session:
                        return False
                        
                    # 再检查 DOM 元素中是否渲染了关键用户信息
                    # 合并头像和昵称选择器
                    indicators = Selectors.USER_INFO["NICKNAME"] + Selectors.USER_INFO["AVATAR"]
                    for selector in indicators:
                        # 快速探测
                        try:
                            if await page.locator(selector).count() > 0:
                                return True
                        except Exception:
                            continue
                            
                    # 补充检查：如果通过了 Cookie，并且处于强制登录态的管理页
                    for keyword in ["/manage/", "/content/", "/home"]:
                        if keyword in page.url:
                            return True
            return False
        except Exception as e:
            logger.warning(f"抖音登录检测失败: {e}")
            return False
    
    async def extract_user_info(self, context) -> LoginResult:
        """提取用户信息"""
        nickname = None
        cookies = await context.cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        
        try:
            pages = context.pages
            if pages:
                page = pages[0]
                current_url = page.url
                
                # 确保在相关页面
                if "douyin.com" in current_url:
                    # 1. 尝试使用 Playwright Python 端原生选择器提取昵称
                    
                    # 优先查找特定的元素，如 .name-_lSSDc 或者 class^="name-" 且包含文本的div
                    high_priority_selectors = [
                        "div.name-_lSSDc",
                        "div[class^='name-']",
                        ".user-info .name"
                    ]
                    
                    # 全部的候选选择器
                    all_selectors = high_priority_selectors + Selectors.USER_INFO["NICKNAME"]
                    
                    for selector in all_selectors:
                        try:
                            loc = page.locator(selector)
                            count = await loc.count()
                            if count > 0:
                                # 可能匹配到多个，取第一个可见且符合逻辑的
                                for i in range(count):
                                    text = await loc.nth(i).inner_text()
                                    if text and "登录" not in text:
                                        text = text.strip()
                                        if text:
                                            nickname = text
                                            break
                                if nickname:
                                    break
                        except Exception:
                            continue
                            
                    # 2. 如果页面较新结构变动，作为备用：通过精简的一段 JS 从全局变量中安全提取
                    if not nickname:
                        logger.info("DOM 提取昵称兜底：尝试从全局变量对象提取")
                        extract_js = '''() => {
                            for (let varName of ['__INITIAL_STATE__', '__USER_INFO__', 'USER_INFO', 'userInfo']) {
                                if (window[varName] && window[varName].nickname) {
                                    return window[varName].nickname;
                                }
                            }
                            return null;
                        }'''
                        nickname = await page.evaluate(extract_js)
        except Exception as e:
            logger.warning(f"提取用户信息异常: {e}")
            
        success = nickname is not None
        return LoginResult(
            success=success,
            cookies=cookie_dict,
            nickname=nickname,
            error_message=None if success else "未能提取到昵称"
        )
    
    async def verify_cookie_http(self, session, cookies: Dict[str, str], user_agent: Optional[str] = None) -> LoginResult:
        """通过 HTTP 请求验证抖音 Cookie"""
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': cookie_str,
            'Referer': 'https://creator.douyin.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate'  # 禁用 br 压缩，避免 aiohttp 解码失败
        }
        
        try:
            # 访问用户信息 API
            api_url = 'https://creator.douyin.com/aweme/v1/creator/pc/user/info/'
            async with session.get(api_url, headers=headers, timeout=5, allow_redirects=False) as response:
                if response.status == 200:
                    data = await response.json()
                    # 只要 status_code 为 0 且有 uid 或 user_info 即视为已登录
                    if data.get('status_code') == 0:
                        user_info = data.get('user_info', {})
                        nickname = user_info.get('nickname') or user_info.get('unique_id')
                        
                        # 如果没有 user_info 但有 uid，也视为登录成功
                        if not nickname and data.get('uid'):
                             return LoginResult(success=True, nickname=None)

                        if nickname:
                            return LoginResult(success=True, nickname=nickname)
                
                return LoginResult(success=False, error_message=f"验证失败: HTTP {response.status}")
        except Exception as e:
            return LoginResult(success=False, error_message=f"异常: {str(e)}")
