# 步骤6：扩展信息 — 补充信息弹窗等（视频/图文共用）
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


class ExtraInfoCommonStep(BasePublishStep):
    """扩展信息公共部分（视频/图文共用）。

    当前版本主要负责兜底处理“补充信息”弹窗，避免阻塞发布。
    后续可以在此步骤中逐步接入位置、合集、权限等字段。
    """

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        logger.info("===== 扩展信息（公共） =====")

        supplement_selector = ", ".join(Selectors.SECURITY.get("PUBLISH_MODAL_SUPPLEMENT", []))
        if supplement_selector:
            try:
                if await page.locator(supplement_selector).count() > 0:
                    logger.info("检测到补充信息弹窗，尝试自动处理（公共部分）")
                    USER_LOG.info("[步骤6/8 扩展信息] ▶ 检测到补充信息弹窗，尝试处理")
                    btn_candidates = [
                        "button:has-text('确定')",
                        "button:has-text('确认')",
                        "button:has-text('完成')",
                        "button:has-text('下一步')",
                        "button:has-text('知道了')",
                        "button:has-text('跳过')",
                    ]
                    config = metadata.get("anti_risk_config") or {}
                    for btn_sel in btn_candidates:
                        btn = page.locator(btn_sel).first
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
                            logger.info(f"已点击补充信息弹窗按钮: {btn_sel}")
                            USER_LOG.info("[步骤6/8 扩展信息] ✓ 已处理补充信息弹窗")
                            break
            except Exception as e:
                logger.warning(f"处理补充信息弹窗失败: {e}")
                USER_LOG.warning("[步骤6/8 扩展信息] ✗ 处理弹窗失败（不阻断）")

        return None

