from typing import Dict, Any, Optional
import json
import logging

from src.plugins.core.interfaces.login_plugin import LoginPluginInterface, LoginResult
from .scripts import LOGIN_DETECTION_SCRIPT

logger = logging.getLogger(__name__)

class KuaishouLoginPlugin(LoginPluginInterface):
    @property
    def platform_id(self) -> str:
        return "kuaishou"
    
    @property
    def platform_name(self) -> str:
        return "快手"
    
    @property
    def login_url(self) -> str:
        return "https://cp.kuaishou.com/profile"
    
    async def check_login_status(self, context) -> bool:
        """检查登录状态"""
        try:
            # 1. 优先使用Cookie快速检测
            cookies = await context.cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            
            # 核心检测: userId
            if 'userId' in cookie_dict:
                return True
                
            # 辅助检测: web_st
            if 'kuaishou.live.web_st' in cookie_dict or 'kuaishou.web.cp_api_st' in cookie_dict:
                return True
            
            # 2. 如果页面已加载，使用脚本检测
            pages = context.pages
            if pages:
                page = pages[0]
                # 只有在相关域名下才执行脚本
                if "kuaishou.com" in page.url:
                    result_json = await page.evaluate(LOGIN_DETECTION_SCRIPT)
                    result = json.loads(result_json)
                    return result.get("loggedIn", False)
            
            return False
            
        except Exception as e:
            logger.warning(f"快手登录检测失败: {e}")
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
                if "kuaishou.com" in current_url:
                    # 尝试使用脚本提取
                    result_json = await page.evaluate(LOGIN_DETECTION_SCRIPT)
                    result = json.loads(result_json)
                    nickname = result.get("username")
                    
                    if not nickname:
                        logger.info("脚本提取昵称失败，尝试通用选择器")
        except Exception as e:
            logger.warning(f"提取快手用户信息失败: {e}")
            
        success = nickname is not None
        return LoginResult(
            success=success,
            cookies=cookie_dict,
            nickname=nickname,
            error_message=None if success else "未能提取到昵称"
        )
    
    async def verify_cookie_http(self, session, cookies: Dict[str, str], user_agent: Optional[str] = None) -> LoginResult:
        """通过 HTTP 请求验证快手 Cookie"""
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': cookie_str,
            'Referer': 'https://cp.kuaishou.com/',
            'Accept-Encoding': 'gzip, deflate'  # 禁用 br 压缩，避免 aiohttp 解码失败
        }
        
        try:
            # 访问快手创作者中心。快手主要通过重定向或 API 返回值判断状态。
            # 这里先检查创作者中心主页是否重定向
            api_url = 'https://cp.kuaishou.com/profile'
            async with session.get(api_url, headers=headers, timeout=5, allow_redirects=False) as response:
                # 如果返回 302 重定向到登录页，说明失效
                if response.status == 302:
                    location = response.headers.get('Location', '')
                    if 'login' in location.lower() or 'passport' in location.lower():
                        return LoginResult(success=False, error_message="Cookie 已过期或被重定向到登录页")
                
                if response.status == 200:
                    # 如果能正常访问，说明大概率是在线的
                    # 这里也可以进一步解析 HTML 提取昵称，为了简化目前仅检查访问性
                    return LoginResult(success=True)
                
                return LoginResult(success=False, error_message=f"状态异常: {response.status}")
        except Exception as e:
            return LoginResult(success=False, error_message=f"异常: {str(e)}")
