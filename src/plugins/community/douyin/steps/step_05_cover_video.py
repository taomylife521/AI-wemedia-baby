# 步骤5：视频封面 — 设置视频封面（首帧/本地图/AI）
# 流程说明见 docs/03插件系统/3.3抖音视频发布封面设置步骤流程说明.md
# 方向一：本地/首帧 → 点击「选择封面」（竖封面3:4 或 横封面4:3 上方）→ 弹窗内操作 → 封面检测通过
# 方向二：AI → 仅在主页面「AI智能推荐封面」红框内点击三个推荐缩略图之一（通常第一个），不进弹窗 → 封面检测通过
# 两个方向共用同一套「封面效果检测通过」判定（COVER_SUCCESS_INDICATOR）
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


class CoverVideoStep(BasePublishStep):
    """视频封面设置：方向一 本地/首帧（进弹窗）；方向二 AI（主页面红框内直选）。完成判定均为「封面效果检测通过」."""

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        cover_type = (metadata.get("cover_type") or "first_frame").strip().lower() if metadata.get("cover_type") else "first_frame"
        cover_path = (metadata.get("cover_path") or "").strip()
        if cover_path and cover_type != "custom":
            cover_type = "custom"
        logger.info("===== 视频封面设置 =====")
        USER_LOG.info("[步骤5/8 视频封面] ▶ 尝试设置")

        # 【方向二】AI 智能推荐封面：仅在主页面红框区域（AI智能推荐封面）内点击第一个推荐缩略图，不进弹窗
        if cover_type == "ai":
            if await self._try_click_ai_recommend_cover(page, metadata):
                if await self._wait_cover_success_indicator(page, metadata):
                    USER_LOG.info("[步骤5/8 视频封面] ✓ 已选择AI智能推荐封面")
                    return None
                return PublishResult(success=False, error_message="已点击AI推荐封面，但未检测到「封面效果检测通过」")
            logger.error("未能在主页面「AI智能推荐封面」区域找到可点击缩略图")
            USER_LOG.error("[步骤5/8 视频封面] ✖ 失败（找不到AI封面）")
            raise Exception("AI智能推荐封面未找到或无法点击，任务宣告失败！")

        # 【方向一】本地/首帧：点击「选择封面」（竖封面3:4 或 横封面4:3 上方）→ 进弹窗操作
        # 如果已经有封面弹窗，直接在弹窗中操作
        if await self._is_cover_modal_open(page):
            result = await self._handle_cover_modal(page, metadata, cover_type, cover_path)
            if result is None:
                if not await self._wait_cover_success_indicator(page, metadata):
                    return PublishResult(success=False, error_message="弹窗内已操作，但未检测到「封面效果检测通过」")
            return result

        config = metadata.get("anti_risk_config") or {}
        # 视频上传成功后封面区可能延迟渲染，先等待「选择封面」入口出现再点击，避免多次盲试
        cover_btn_selector = ", ".join(Selectors.PUBLISH["COVER_BTN"])
        try:
            USER_LOG.info("[步骤5/8 视频封面] 等待「选择封面」入口出现…")
            await page.wait_for_selector(cover_btn_selector, state="visible", timeout=8000)
        except Exception as e:
            logger.warning("等待选择封面入口超时: %s", e)
        try:
            from src.infrastructure.anti_risk.delays import random_delay
            await random_delay(page, 800, metadata, config)
        except Exception:
            await page.wait_for_timeout(800)

        modal_opened = False
        # 1) 点击「选择封面」入口（竖封面3:4 / 横封面4:3 上方的卡片，DOM 唯一匹配）
        try:
            btn = page.locator(cover_btn_selector).first
            if await btn.count() > 0:
                await btn.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                try:
                    from src.infrastructure.anti_risk.human_like import human_click
                    await human_click(page, btn, metadata, config)
                except Exception:
                    await btn.click(force=True)
                logger.info("已点击「选择封面」入口（div.filter-k_CjvJ）")
                try:
                    from src.infrastructure.anti_risk.delays import random_delay
                    await random_delay(page, 1200, metadata, config)
                except Exception:
                    await page.wait_for_timeout(1200)
                if await self._is_cover_modal_open(page):
                    USER_LOG.info("[步骤5/8 视频封面] ▶ 已成功激活封面弹窗")
                    modal_opened = True
        except Exception as e:
            logger.warning("通过 COVER_BTN 点击封面入口失败: %s", e)

        if modal_opened:
            result = await self._handle_cover_modal(page, metadata, cover_type, cover_path)
            if result is None:
                if not await self._wait_cover_success_indicator(page, metadata):
                    return PublishResult(success=False, error_message="弹窗内已点击完成，但未检测到「封面效果检测通过」")
            return result

        logger.error("未找到「选择封面」入口或点击后弹窗未打开，请检查 DOM（div.filter-k_CjvJ）或页面布局")
        USER_LOG.error("[步骤5/8 视频封面] ✖ 失败：未打开封面设置弹窗")
        return PublishResult(
            success=False,
            error_message="未找到选择封面入口或点击后弹窗未打开，请对照 docs/抖音发布插件DOM对照表.md 检查页面 DOM",
        )

    async def _is_cover_modal_open(self, page: Page) -> bool:
        for selector in Selectors.PUBLISH.get("COVER_MODAL", []):
            try:
                if await page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    async def _see_cover_success_indicator(self, page: Page) -> bool:
        """当前页是否已出现「封面效果检测通过」（不等待）。"""
        selectors = Selectors.PUBLISH.get("COVER_SUCCESS_INDICATOR") or []
        if not selectors:
            return False
        combined = ", ".join(selectors)
        try:
            loc = page.locator(combined).first
            return await loc.count() > 0 and await loc.is_visible()
        except Exception:
            return False

    async def _wait_cover_success_indicator(self, page: Page, metadata: Dict[str, Any], timeout_ms: int = 15000) -> bool:
        """等待主页面出现「封面效果检测通过」提示（两方向共用），对应 COVER_SUCCESS_INDICATOR。仅当出现该提示时返回 True。"""
        selectors = Selectors.PUBLISH.get("COVER_SUCCESS_INDICATOR") or []
        if not selectors:
            USER_LOG.warning("[步骤5/8 视频封面] 未配置 COVER_SUCCESS_INDICATOR，无法判定封面是否成功")
            return False
        combined = ", ".join(selectors)
        USER_LOG.info("[步骤5/8 视频封面] 等待页面出现「封面效果检测通过」…（最长 %d 秒）", timeout_ms // 1000)
        try:
            await page.wait_for_selector(combined, state="visible", timeout=timeout_ms)
            logger.info("已检测到「封面效果检测通过」提示，封面设置成功")
            USER_LOG.info("[步骤5/8 视频封面] ✓ 封面效果检测通过")
            return True
        except Exception as e:
            logger.warning("等待「封面效果检测通过」超时或未出现: %s", e)
            USER_LOG.warning("[步骤5/8 视频封面] ✖ 未检测到「封面效果检测通过」，封面可能未生效")
            return False

    async def _try_click_ai_recommend_cover(self, page: Page, metadata: Dict[str, Any]) -> bool:
        """方向二：在主页面「AI智能推荐封面」红框内点击第一个推荐缩略图（唯一 DOM），不进弹窗。"""
        config = metadata.get("anti_risk_config") or {}
        for sel in (Selectors.PUBLISH.get("COVER_AI_RECOMMEND_FIRST") or []):
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    try:
                        from src.infrastructure.anti_risk.human_like import human_click
                        await human_click(page, loc, metadata, config)
                    except Exception:
                        await loc.click()
                    await page.wait_for_timeout(1000)
                    logger.info("已在「AI智能推荐封面」区域点击第一个推荐缩略图: %s", sel)
                    return True
            except Exception:
                continue
        return False

    async def _handle_cover_modal(
        self, page: Page, metadata: Dict[str, Any], cover_type: str, cover_path: str
    ) -> Optional[PublishResult]:
        await self._await_pause({})
        logger.info("封面弹窗已打开（视频），按配置执行: %s", cover_type)
        USER_LOG.info("[步骤5/8 视频封面] ▶ 弹窗已打开，选择并确认")

        # 分支一：本地图片封面 —— 点击上传封面 → 上传封面图片 → 上传成功后点击完成
        if cover_type == "custom" and cover_path:
            ok = await self._handle_cover_upload_local(page, cover_path)
            if ok:
                USER_LOG.info("[步骤5/8 视频封面] ✓ 已上传本地封面并确认")
                return None
            logger.warning("本地封面上传未成功，尝试首帧兜底")

        # 分支二：首帧封面（或兜底）—— 固定顺序（图1→图2→图3）：
        # 1) 点击「设置横封面」→ 弹窗切换为横封面设置状态（图2）；2) 点击「完成」→ 触发封面检测，主页面显示「封面效果检测通过」（图3）
        clicked_horizontal = False
        for sel in (Selectors.PUBLISH.get("COVER_HORIZONTAL_BTN") or []):
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked_horizontal = True
                    logger.info("弹窗内已点击「设置横封面」，等待弹窗切换为横封面设置状态（图2）")
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                continue
        if not clicked_horizontal:
            logger.debug("未找到或未点击「设置横封面」按钮，尝试直接点完成")

        # 点击「完成」后延迟 1–2s 检测「封面效果检测通过」是否出现，出现则代表封面设置成功（不以弹窗是否关闭为准）
        for selector in (Selectors.PUBLISH.get("COVER_CONFIRM_BTN") or []):
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await page.wait_for_timeout(500)
                    await btn.click(force=True)
                    logger.info("弹窗内已点击「完成」，延迟 1–2s 检测封面效果检测通过…")
                    USER_LOG.info("[步骤5/8 视频封面] 已点击完成，检测封面效果…")
                    await page.wait_for_timeout(1500)  # 1–2s
                    if await self._see_cover_success_indicator(page):
                        logger.info("已检测到「封面效果检测通过」，封面设置成功")
                        USER_LOG.info("[步骤5/8 视频封面] ✓ 封面效果检测通过")
                        return None
                    # 未立即出现时由调用方 _wait_cover_success_indicator 继续等待
                    return None
            except Exception:
                continue

        logger.error("视频封面操作失败：弹窗内未找到或未点击「完成」按钮")
        raise Exception("视频封面设置失败，弹窗内无法点击「完成」按钮！")

    async def _handle_cover_upload_local(self, page: Page, cover_path: str) -> bool:
        """弹窗内：点击上传封面 → 选择本地图片 → 等待上传成功 → 点击完成。"""
        from pathlib import Path
        if not Path(cover_path).exists():
            logger.warning("本地封面文件不存在: %s", cover_path)
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
                    await page.wait_for_timeout(3000) # 给更长的时间渲染图片
                    
                    found_confirm = False
                    # 弹窗内固定顺序（图1→图2→图3）：先点「设置横封面」→ 等待 → 再点「完成」才触发封面检测
                    for hor_sel in (Selectors.PUBLISH.get("COVER_HORIZONTAL_BTN") or []):
                        try:
                            btn_h = page.locator(hor_sel).first
                            if await btn_h.count() > 0 and await btn_h.is_visible():
                                await btn_h.click()
                                await page.wait_for_timeout(1500)
                                break
                        except Exception:
                            continue

                    for confirm_sel in Selectors.PUBLISH.get("COVER_CONFIRM_BTN", []):
                        try:
                            cbtn = page.locator(confirm_sel).first
                            if await cbtn.count() > 0 and await cbtn.is_visible():
                                await cbtn.click()
                                await page.wait_for_timeout(1000)
                                found_confirm = True
                                break
                        except Exception:
                            continue
                            
                    if not found_confirm:
                        logger.info("图片已放入 input，但未找到或无需点击'确认'按钮，视作设置完成")
                    return True
            except Exception as e:
                logger.warning(f"填入封面 input 发生异常: {e}")
                continue
        return False




