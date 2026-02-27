
import asyncio
import logging
from typing import Optional, Tuple, Any
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext

logger = logging.getLogger(__name__)

class UndetectedPlaywrightBrowser:
    """Undetected Playwright 浏览器封装"""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
    
    async def create_context(
        self, 
        headless: bool = True, 
        user_data_dir: Optional[str] = None
    ) -> Tuple[Optional[BrowserContext], Optional[Browser]]:
        """创建浏览器上下文
        
        Args:
            headless: 是否无头模式
            user_data_dir: 用户数据目录（暂不支持持久化上下文启动，仅支持常规启动后创建上下文）
            
        Returns:
            (context, browser)
        """
        try:
            self.playwright = await async_playwright().start()
            
            # 启动参数
            args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled", # 关键：禁用自动化特征
                "--ignore-certificate-errors",
                "--disable-infobars",
                "--exclude-switches=enable-automation",
                "--use-gl=desktop"
            ]
            
            # 仅使用系统安装的 Chrome 以保障环境一致性
            channel = "chrome" 
            
            logger.info(f"正在启动浏览器 (channel={channel})...")
            
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=args,
                    channel=channel
                )
            except Exception as e:
                logger.error(f"Local Chrome 启动失败: {e}. 请确保已安装 Google Chrome 浏览器。")
                if self.playwright:
                    await self.playwright.stop()
                return None, None
            
            context = await self.browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", 
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                permissions=["geolocation", "notifications"],
                ignore_https_errors=True
            )
            
            # 注入更强的抗检测脚本
            await context.add_init_script("""
                // 1. Pass webdriver check
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 2. Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // 3. Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });

                // 4. Mock window.chrome
                window.chrome = {
                    runtime: {}
                };
                
                // 5. Mask permission query
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: 'granted' }) :
                    originalQuery(parameters)
                );
            """)
            
            logger.info(f"Undetected Playwright 浏览器启动成功 (headless={headless})")
            return context, self.browser
            
        except Exception as e:
            logger.error(f"Undetected Playwright 启动失败: {e}", exc_info=True)
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            return None, None

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.debug(f"关闭浏览器时出现错误 (已忽略): {e}")
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Undetected Playwright 浏览器已关闭")
