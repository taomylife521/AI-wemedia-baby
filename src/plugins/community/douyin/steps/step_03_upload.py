# 步骤3：上传 — 上传视频或图文文件
import logging
import os
from typing import Dict, Any, Optional, List

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


def _parse_image_paths(file_path: str, metadata: Dict[str, Any]) -> List[str]:
    paths = metadata.get("image_paths")
    if isinstance(paths, list) and paths:
        return [str(p).strip() for p in paths if str(p).strip()]
    # 兼容历史：逗号分隔
    return [p.strip() for p in str(file_path).split(",") if p.strip()]


class UploadMediaStep(BasePublishStep):
    """统一上传步骤：根据 file_type 上传视频或图文。"""

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        file_type = (metadata.get("file_type") or "video").lower()

        if file_type == "image":
            return await self._upload_images(page, file_path, metadata)
        return await self._upload_video(page, file_path, metadata)

    async def _upload_video(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        logger.info("===== 开始上传视频文件 =====")
        base = os.path.basename(str(file_path))
        USER_LOG.info(f"[步骤3/8 上传视频/图文] ▶ 开始 文件={base} 路径={file_path}")

        # 策略1: 直接查找 input[type=file]
        try:
            file_input_selector = ", ".join(Selectors.PUBLISH["FILE_INPUT"])
            input_file = page.locator(file_input_selector).first
            if await input_file.count() > 0:
                await input_file.set_input_files(file_path)
                logger.info("使用 set_input_files 触发视频上传")
                return await self._wait_for_video_upload_complete(page, metadata)
        except Exception as e:
            logger.info(f"直接 set_input_files 失败，尝试备用方案: {e}")

        # 策略2: 点击上传区域触发 chooser
        try:
            upload_btn_selector = ", ".join(Selectors.PUBLISH["UPLOAD_BTN"])
            upload_btn = page.locator(upload_btn_selector).first
            if await upload_btn.count() > 0:
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click(force=True)
                fc = await fc_info.value
                await fc.set_files(file_path)
                logger.info("通过 file chooser 上传视频完成")
                return await self._wait_for_video_upload_complete(page, metadata)
        except Exception as e:
            logger.error(f"点击上传区域上传视频失败: {e}")

        return PublishResult(success=False, error_message="无法找到视频上传入口，可能页面结构已变更")

    async def _wait_for_video_upload_complete(self, page: Page, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        """等待视频上传完成：仅当页面出现「重新上传」区域（label.upload-btn-PdfuUv）时判定为成功。"""
        max_wait_seconds = int(metadata.get("upload_timeout_seconds") or 180)
        logger.info("等待视频上传/转码就绪（最长 %s 分钟），检测「重新上传」按钮是否出现...", max_wait_seconds // 60)
        USER_LOG.info("[步骤3/8 上传视频/图文] 正在上传中，等待上传成功（最长 %d 秒）…", max_wait_seconds)
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))
        # 唯一判定：出现 label.upload-btn-PdfuUv（重新上传）即代表视频已上传成功
        success_marker = ", ".join(Selectors.PUBLISH["VIDEO_UPLOAD_SUCCESS_MARKER"])
        for i in range(max_wait_seconds // 2):
            await self._await_pause(metadata)
            if await page.locator(success_marker).count() > 0:
                logger.info("检测到「重新上传」按钮已出现，视频上传成功")
                USER_LOG.info("[步骤3/8 上传视频/图文] ✓ 上传成功")
                return None

            elapsed = i * 2
            if i % 30 == 0:
                logger.info(f"等待上传中... ({elapsed}s/{max_wait_seconds}s)")
            if i > 0 and i % 15 == 0:
                USER_LOG.info("[步骤3/8 上传视频/图文] 正在上传中，已等待 %d 秒，等待「重新上传」按钮出现…", elapsed)
            config = metadata.get("anti_risk_config") or {}
            try:
                from src.infrastructure.anti_risk.delays import random_delay
                await random_delay(page, int(2000 * speed_rate), metadata, config)
            except Exception:
                await page.wait_for_timeout(int(2000 * speed_rate))

        return PublishResult(success=False, error_message=f"等待视频上传超时 ({max_wait_seconds}秒)")

    async def _upload_images(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        logger.info("===== 开始上传图文图片 =====")
        image_paths = _parse_image_paths(file_path, metadata)
        base = os.path.basename(str(image_paths[0])) if image_paths else ""
        USER_LOG.info(f"[步骤3/8 上传视频/图文] ▶ 开始 图文数量={len(image_paths)} 文件示例={base} 路径={file_path}")

        if not image_paths:
            return PublishResult(success=False, error_message="图文上传失败: 未提供图片路径")
        if not os.path.exists(image_paths[0]):
            return PublishResult(success=False, error_message=f"图文上传失败: 找不到图片文件 -> {image_paths[0]}")

        # 优先直接 set_input_files（支持批量）
        try:
            file_input_selector = ", ".join(Selectors.PUBLISH["IMAGE_FILE_INPUT"])
            input_file = page.locator(file_input_selector).first
            if await input_file.count() > 0:
                await input_file.set_input_files(image_paths)
                logger.info(f"已 set_input_files 上传图片: {len(image_paths)} 张")
                return await self._wait_for_images_upload_complete(page, len(image_paths), metadata)
        except Exception as e:
            logger.info(f"set_input_files 上传图片失败，尝试点击上传入口: {e}")

        # 兜底：点击上传按钮触发 chooser
        try:
            upload_btn_selector = ", ".join(Selectors.PUBLISH["UPLOAD_IMAGE_BTN"])
            upload_btn = page.locator(upload_btn_selector).first
            if await upload_btn.count() > 0:
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click(force=True)
                fc = await fc_info.value
                await fc.set_files(image_paths)
                logger.info("通过 file chooser 上传图片完成")
                return await self._wait_for_images_upload_complete(page, len(image_paths), metadata)
        except Exception as e:
            logger.error(f"点击上传入口上传图片失败: {e}")

        return PublishResult(success=False, error_message="图文上传失败: 无法找到图片上传入口")

    async def _wait_for_images_upload_complete(self, page: Page, expected_count: int, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        max_wait_seconds = int(metadata.get("image_upload_timeout_seconds") or 180)
        logger.info("等待图片缩略图渲染（最长 %s 分钟）...", max_wait_seconds // 60)
        USER_LOG.info("[步骤3/8 上传视频/图文] 正在上传图文，等待上传成功（最长 %d 秒）…", max_wait_seconds)
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))

        thumb_selector = ", ".join(Selectors.PUBLISH["IMAGE_THUMBNAIL"])
        for i in range(max_wait_seconds // 2):
            await self._await_pause(metadata)
            try:
                cnt = await page.locator(thumb_selector).count()
                if cnt >= min(expected_count, 1) and cnt >= 1:
                    # 真实缩略图数量在不同实现中可能包含封面/占位，不强卡 expected_count
                    logger.info(f"检测到图片缩略图数量={cnt}，认为上传已就绪")
                    USER_LOG.info("[步骤3/8 上传视频/图文] ✓ 上传成功")
                    return None
            except Exception:
                pass

            elapsed = i * 2
            if i % 10 == 0:
                logger.info(f"等待图片就绪... ({elapsed}s/{max_wait_seconds}s)")
            if i > 0 and i % 15 == 0:
                USER_LOG.info("[步骤3/8 上传视频/图文] 正在上传图文，已等待 %d 秒…", elapsed)
            config = metadata.get("anti_risk_config") or {}
            try:
                from src.infrastructure.anti_risk.delays import random_delay
                await random_delay(page, int(2000 * speed_rate), metadata, config)
            except Exception:
                await page.wait_for_timeout(int(2000 * speed_rate))

        return PublishResult(success=False, error_message=f"等待图片上传就绪超时 ({max_wait_seconds}秒)")
