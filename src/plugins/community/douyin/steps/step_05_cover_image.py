# 步骤5：图文封面 — 设置图文封面（首张/本地图/AI）
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


class CoverImageStep(BasePublishStep):
    """图文封面设置：按任务配置分支——首帧/第一张、本地图片封面、AI 推荐。"""

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        cover_type = (metadata.get("cover_type") or "first_frame").strip().lower() if metadata.get("cover_type") else "first_frame"
        cover_path = (metadata.get("cover_path") or "").strip()
        if cover_path and cover_type != "custom":
            cover_type = "custom"
        logger.info("===== 图文封面设置 =====")
        USER_LOG.info("[步骤5/8 图文封面] ▶ 尝试设置")
        config = metadata.get("anti_risk_config") or {}

        for selector in Selectors.PUBLISH["COVER_BTN"]:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    try:
                        from src.infrastructure.anti_risk.human_like import human_click
                        await human_click(page, btn, metadata, config)
                    except Exception:
                        await btn.click()
                    try:
                        from src.infrastructure.anti_risk.delays import random_delay
                        await random_delay(page, 800, metadata, config)
                    except Exception:
                        await page.wait_for_timeout(800)
                    logger.info(f"已点击图文封面按钮: {selector}")
                    USER_LOG.info("[步骤5/8 图文封面] ▶ 已点击封面入口")
                    break
            except Exception:
                continue

        if await self._is_cover_modal_open(page):
            return await self._handle_cover_modal(page, metadata, cover_type, cover_path)

        # 无弹窗时：图文页常用“第一张图即封面”
        if cover_type == "first_frame":
            try:
                img_thumb_selector = ", ".join(Selectors.PUBLISH.get("IMAGE_THUMBNAIL", []))
                thumbs = page.locator(img_thumb_selector)
                cnt = await thumbs.count()
                if cnt > 0:
                    first_thumb = thumbs.nth(0)
                    try:
                        from src.infrastructure.anti_risk.human_like import human_click
                        await human_click(page, first_thumb, metadata, config)
                    except Exception:
                        await first_thumb.click()
                    try:
                        from src.infrastructure.anti_risk.delays import random_delay
                        await random_delay(page, 300, metadata, config)
                    except Exception:
                        await page.wait_for_timeout(300)
                    logger.info("已在图文图片列表中点击第一张图片作为封面候选")
                    USER_LOG.info("[步骤5/8 图文封面] ✓ 已选择第一张作为候选")
                    return None
            except Exception:
                pass

        logger.info("未能找到图文封面设置入口，跳过图文封面设置")
        USER_LOG.info("[步骤5/8 图文封面] ✓ 跳过（未找到入口）")
        return None

    async def _is_cover_modal_open(self, page: Page) -> bool:
        for selector in Selectors.PUBLISH.get("COVER_MODAL", []):
            try:
                if await page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    async def _handle_cover_modal(
        self, page: Page, metadata: Dict[str, Any], cover_type: str, cover_path: str
    ) -> Optional[PublishResult]:
        await self._await_pause({})
        logger.info("图文封面弹窗已打开，按配置执行: %s", cover_type)
        USER_LOG.info("[步骤5/8 图文封面] ▶ 弹窗已打开，选择并确认")

        if cover_type == "custom" and cover_path:
            if await self._handle_cover_upload_local(page, cover_path):
                USER_LOG.info("[步骤5/8 图文封面] ✓ 已上传本地封面并确认")
                return None
        if cover_type == "ai":
            if await self._handle_cover_ai(page):
                USER_LOG.info("[步骤5/8 图文封面] ✓ 已选择 AI 智能封面并确认")
                return None

        clicked = False
        thumb_selector = ", ".join(Selectors.PUBLISH.get("COVER_THUMB", [])) or "div[role='dialog'] img"
        try:
            thumbs = page.locator(thumb_selector)
            cnt = await thumbs.count()
            if cnt > 0:
                await thumbs.nth(0).click()
                clicked = True
                await page.wait_for_timeout(300)
                logger.info(f"已选择图文封面缩略图: {thumb_selector}")
        except Exception:
            pass

        for selector in Selectors.PUBLISH.get("COVER_CONFIRM_BTN", []):
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(800)
                    logger.info(f"已确认图文封面: {selector}")
                    USER_LOG.info("[步骤5/8 图文封面] ✓ 已确认")
                    return None
            except Exception:
                continue

        if clicked:
            logger.warning("已选择图文封面但未找到确认按钮，继续流程（可能自动保存）")
            return None

        logger.warning("图文封面弹窗操作失败：未找到缩略图或确认按钮")
        return None

    async def _handle_cover_upload_local(self, page: Page, cover_path: str) -> bool:
        from pathlib import Path
        if not Path(cover_path).exists():
            return False
        for sel in Selectors.PUBLISH.get("COVER_UPLOAD_BTN", []):
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(800)
                    break
            except Exception:
                continue
        for sel in Selectors.PUBLISH.get("COVER_FILE_INPUT", []):
            try:
                inp = page.locator(sel).first
                if await inp.count() > 0:
                    await inp.set_input_files(cover_path)
                    await page.wait_for_timeout(2000)
                    for confirm_sel in Selectors.PUBLISH.get("COVER_CONFIRM_BTN", []):
                        try:
                            cbtn = page.locator(confirm_sel).first
                            if await cbtn.count() > 0 and await cbtn.is_visible():
                                await cbtn.click()
                                await page.wait_for_timeout(1000)
                                return True
                        except Exception:
                            continue
                    return True
            except Exception:
                continue
        return False

    async def _handle_cover_ai(self, page: Page) -> bool:
        for sel in Selectors.PUBLISH.get("COVER_AI_OPTION", []):
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(1500)
                    thumbs = page.locator(", ".join(Selectors.PUBLISH.get("COVER_THUMB", [])) or "div[role='dialog'] img")
                    if await thumbs.count() > 0:
                        await thumbs.nth(0).click()
                        await page.wait_for_timeout(300)
                    for confirm_sel in Selectors.PUBLISH.get("COVER_CONFIRM_BTN", []):
                        try:
                            cbtn = page.locator(confirm_sel).first
                            if await cbtn.count() > 0 and await cbtn.is_visible():
                                await cbtn.click()
                                await page.wait_for_timeout(1000)
                                return True
                        except Exception:
                            continue
                    return True
            except Exception:
                continue
        return False

