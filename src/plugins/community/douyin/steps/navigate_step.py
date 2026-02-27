import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from .base_step import BasePublishStep
from ..selectors import Selectors

logger = logging.getLogger(__name__)

class NavigateStep(BasePublishStep):
    def __init__(self, upload_url: str, login_keywords: list):
        self.upload_url = upload_url
        self.login_keywords = login_keywords

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        logger.info(f"导航至发布上传页: {self.upload_url}")
        
        try:
            # 增加超时限制和重试机制
            response = await page.goto(self.upload_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"当前页面 URL: {current_url}")
            
            # 1. 检测风控拦截和登录弹窗
            for selector in Selectors.SECURITY["RISK_MODAL"]:
                if await page.locator(selector).count() > 0:
                    try:
                        text = await page.locator(selector).inner_text()
                        logger.error(f"检测到风控或拦截提示: {text}")
                    except Exception:
                        pass
                    return PublishResult(
                        success=False,
                        error_message="检测到账号风控拦截或被强制要求重新登录，请关闭自动化后手动验证此账号"
                    )

            # 2. 检查是否被重定向到登录页
            for keyword in self.login_keywords:
                if keyword in current_url.lower():
                    logger.error(f"遭遇登录态失效拦截，被跳转至包含 '{keyword}' 的页面")
                    return PublishResult(
                        success=False,
                        # 触发此错误时，外层任务执行器会拦截这种特殊字符串，并进行重登录调度
                        error_message="Cookie失效，未登录或登录已过期"
                    )

            # 3. 检查是否成功处于创作者中心内
            if "creator.douyin.com" in current_url:
                logger.info("已成功确认处于抖音创作者平台域内")
                return None
            
            return PublishResult(
                success=False,
                error_message=f"无法确认已进入创作者平台，当前 URL: {current_url}"
            )

        except Exception as e:
            logger.error(f"导航过程发生网络异常: {e}")
            return PublishResult(success=False, error_message=f"页面导航加载失败: {str(e)}")
