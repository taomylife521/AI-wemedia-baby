import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from .base_step import BasePublishStep
from ..selectors import Selectors

logger = logging.getLogger(__name__)

class SubmitStep(BasePublishStep):
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        """点击发布按钮并验证最终结果"""
        logger.info("===== 寻找并点击发布按钮 =====")

        publish_selectors = Selectors.PUBLISH["SUBMIT_BTN"]

        # 寻找发布按钮
        target_btn = None
        target_selector = ""
        for selector in publish_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0:
                    # 等待按钮可见
                    await btn.wait_for(state="visible", timeout=10000)
                    target_btn = btn
                    target_selector = selector
                    break
            except Exception:
                continue
                
        if not target_btn:
            return PublishResult(
                success=False,
                error_message="未找到发布按钮，可能页面结构已变更"
            )

        logger.info(f"找到发布按钮: {target_selector}，检查是否就绪...")
        
        # 视频上传后需要转码，这期间发布按钮可能是禁用的（disabled）
        # 等待按钮变为可用状态
        max_wait_seconds = 180
        is_ready = False
        
        for i in range(max_wait_seconds // 3):
            is_disabled = await target_btn.get_attribute("disabled")
            if is_disabled is None or is_disabled == "false":
                is_ready = True
                break
            logger.info("发布按钮当前不可用（可能仍在转码中），继续等待...")
            await page.wait_for_timeout(3000)
            
        if not is_ready:
            return PublishResult(
                success=False,
                error_message="等待视频转码/处理超时，发布按钮始终不可用"
            )
            
        logger.info("发布按钮已就绪，准备点击...")
        try:
            # 点击前再给一点缓冲时间
            await page.wait_for_timeout(1000)
            await target_btn.click()
            logger.info("已点击发布按钮")
        except Exception as e:
            return PublishResult(success=False, error_message=f"点击发布按钮失败: {str(e)}")
            
        # 点击发布后，检查是否有额外的确认弹窗或错误提示
        logger.info("检查发布后是否存在弹窗或错误提示...")
        await page.wait_for_timeout(2000) # 等待弹窗反应
        
        try:
            # 常见错误/提示弹窗选择器
            error_selectors = [
                (", ".join(Selectors.SECURITY["PUBLISH_TOAST_ERROR"]), "发布失败/错误"),
                (", ".join(Selectors.SECURITY["PUBLISH_MODAL_COVER"]), "需要选择封面"),
                (", ".join(Selectors.SECURITY["PUBLISH_MODAL_SUPPLEMENT"]), "需要补充额外信息"),
                (", ".join(Selectors.SECURITY["PUBLISH_TOAST_FREQ"]), "操作频繁，风控拦截")
            ]
            
            for selector, desc in error_selectors:
                if await page.locator(selector).count() > 0:
                    logger.warning(f"检测到异常弹窗/提示: {desc}")
                    # 尝试读取具体的提示文本
                    try:
                        text = await page.locator(selector).inner_text()
                        desc = f"{desc}: {text}"
                    except Exception:
                        pass
                    return PublishResult(success=False, error_message=f"点击发布后受阻: {desc}")
        except Exception as e:
            logger.debug(f"检查弹窗出现异常（不影响主流程）: {e}")

        # 将返回具体的验证结果，该步骤需要终结这个责任链
        return await self._verify_publish_result(page)

    async def _verify_publish_result(self, page: Page) -> PublishResult:
        """验证发布结果"""
        logger.info("===== 验证发布结果 =====")

        try:
            # 给页面留出充分的跳转反应时间
            logger.info("等待页面跳转到作品管理页...")
            await page.wait_for_url("**/manage/**", timeout=30000)
            
            # 额外验证：跳转后页面是否包含管理页标识
            manage_indicators = Selectors.VERIFY["MANAGE_PAGE_INDICATOR"]
            
            # 为了防止被快速 clear() 的假跳转，等待一下渲染
            await page.wait_for_timeout(2000)
            
            for indicator in manage_indicators:
                if await page.locator(indicator).count() > 0:
                    logger.info(f"已明确跳转到作品管理页 (验证特征: {indicator})，发布成功!")
                    return PublishResult(success=True, publish_url=page.url)
                    
            # 只要跳了 manage 就算成功
            logger.info(f"已跳转到作品管理页 URL: {page.url}，发布成功!")
            return PublishResult(success=True, publish_url=page.url)
            
        except Exception:
            logger.info("页面未成功跳转至管理页，尝试其他验证方式...")

        # 方式2: 页面上是否出现"发布成功"提示
        try:
            success_selector = Selectors.VERIFY["SUCCESS_TOAST"]
            if await page.locator(success_selector).count() > 0:
                logger.info("检测到「发布成功」提示文字")
                return PublishResult(success=True, publish_url=page.url)
        except Exception:
            pass

        # 方式3: 检查 URL 是否已经离开上传页（可能跳转到了其他管理页但 url 未匹配 manage）
        if "upload" not in page.url and "creator.douyin.com" in page.url:
            # 为防止是因为 browser 被关闭导致的 url 改变，验证该页面确实是加载完毕的并且存在发布内容
            try:
                has_nav = await page.locator('nav').count() > 0
                if has_nav:
                     logger.info(f"页面正常加载且已离开上传页: {page.url}，推测发布成功")
                     return PublishResult(success=True, publish_url=page.url)
            except Exception:
                 pass
            
            logger.warning(f"页面似乎离开了发布页，但状态不确定: {page.url}")

        logger.warning("未能确认发布成功，请手动检查")
        return PublishResult(
            success=False,
            error_message="发布后未能确认成功（未检测到跳转或成功提示），且页面可能卡在上传界面，请手动检查"
        )
