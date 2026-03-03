# 步骤2：进入发布页 — 从首页点击「发布视频」或「发布图文」
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


class EnterPublishEntryStep(BasePublishStep):
    """从首页点击“发布视频/发布图文”入口，进入对应发布页。"""

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        file_type = (metadata.get("file_type") or "video").lower()
        logger.info(f"===== 进入发布入口: file_type={file_type} =====")

        if file_type not in ("video", "image"):
            logger.warning(f"未知 file_type={file_type}，按视频处理")
            file_type = "video"

        # 1. 点击首页入口按钮
        if file_type == "video":
            selectors = Selectors.HOME["PUBLISH_VIDEO_BTN"]
            action_text = "发布视频"
        else:
            selectors = Selectors.HOME["PUBLISH_IMAGE_BTN"]
            action_text = "发布图文"

        config = metadata.get("anti_risk_config") or {}
        clicked = False
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    try:
                        from src.infrastructure.anti_risk.human_like import human_click
                        await human_click(page, btn, metadata, config)
                    except Exception:
                        await btn.click()
                    clicked = True
                    logger.info(f"已点击发布入口按钮: {sel}")
                    USER_LOG.info(f"[步骤2/8 进入发布页] ▶ 点击“{action_text}”")
                    break
            except Exception:
                continue

        if not clicked:
            return PublishResult(
                success=False,
                error_message=f"未找到发布入口按钮（file_type={file_type}），请检查首页布局或选择器配置",
            )

        # 2. 等待跳转到对应发布页：通过 URL + 关键元素综合判断
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))
        wait_ms = int(2000 * speed_rate)
        try:
            try:
                from src.infrastructure.anti_risk.delays import random_delay
                await random_delay(page, wait_ms, metadata, config)
            except Exception:
                await page.wait_for_timeout(wait_ms)
            current_url = page.url
            logger.info(f"点击发布入口后 URL: {current_url}")
            USER_LOG.info(f"[步骤2/8 进入发布页] ▶ 进入 {current_url}")
        except Exception:
            current_url = ""

        markers = (
            Selectors.HOME.get("VIDEO_PUBLISH_PAGE_MARKERS", [])
            if file_type == "video"
            else Selectors.HOME.get("IMAGE_PUBLISH_PAGE_MARKERS", [])
        )

        ok = False
        for sel in markers:
            try:
                if await page.locator(sel).count() > 0:
                    ok = True
                    logger.info(f"已检测到发布页特征元素: {sel}")
                    break
            except Exception:
                continue

        if not ok:
            return PublishResult(
                success=False,
                error_message=f"未能确认进入发布页：未检测到发布页特征元素（file_type={file_type}，url={current_url}）",
            )

        return None
