import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from .base_step import BasePublishStep
from ..selectors import Selectors

logger = logging.getLogger(__name__)

class UploadStep(BasePublishStep):
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        logger.info("===== 开始上传视频文件 =====")

        # 策略1: 直接查找隐藏的 input[type="file"]
        logger.info("尝试直接通过 input[type=file] 设置文件")
        try:
            # 使用统一配置的 FILE_INPUT 选择器（合并为一个复合 CSS 选择器）
            file_input_selector = ", ".join(Selectors.PUBLISH["FILE_INPUT"])
            input_file = page.locator(file_input_selector).first
            if await input_file.count() > 0:
                await input_file.set_input_files(file_path)
                logger.info("使用 set_input_files 成功触发文件上传")
                
                # 开始等待上传和转码完成
                return await self._wait_for_upload_complete(page)
        except Exception as e:
            logger.info(f"直接设置文件失败，尝试备用方案: {e}")
            
        logger.info("尝试通过点击上传区域触发文件选择器")
        try:
            # 使用统一配置的 UPLOAD_BTN 兜底点击区域
            upload_btn_selector = ", ".join(Selectors.PUBLISH["UPLOAD_BTN"])
            upload_btn = page.locator(upload_btn_selector).first
            
            if await upload_btn.count() > 0:
                logger.info(f"找到上传按钮: {upload_btn_selector}")
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click(force=True)  # force=True 解决被浮动层遮挡问题
                file_chooser = await fc_info.value
                await file_chooser.set_files(file_path)
                logger.info("通过文件选择器上传完成")
                return await self._wait_for_upload_complete(page)
        except Exception as e:
            logger.error(f"策略2（点击上传）也失败: {e}")

        # 所有策略都失败
        return PublishResult(
            success=False,
            error_message="无法找到上传入口，可能是页面结构已变更，请检查抖音创作者平台是否有更新"
        )

    async def _wait_for_upload_complete(self, page: Page) -> Optional[PublishResult]:
        logger.info("正在等待视频上传完成（最长等待 3 分钟）...")
        max_wait_seconds = 180 # 3分钟
        for i in range(max_wait_seconds // 2):
            # 转码成功的标志：出现"重新上传"
            reupload_selector = ", ".join(Selectors.PUBLISH["REUPLOAD_BTN"])
            success_text_selector = Selectors.PUBLISH["UPLOAD_SUCCESS_TEXT"]
            
            if await page.locator(reupload_selector).count() > 0 or await page.locator(success_text_selector).count() > 0:
                logger.info("视频初步上传成功，等待填表...")
                return None
                
            await page.wait_for_timeout(2000)
            
            # 每10秒打印一次日志
            if i % 5 == 0:
                logger.info(f"正在等待上传完成... ({i*2}s/{max_wait_seconds}s)")
                
        return PublishResult(
            success=False,
            error_message=f"等待上传超时 ({max_wait_seconds}秒)"
        )
