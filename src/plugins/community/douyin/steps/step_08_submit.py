# 步骤8：点击发布 — 点击发布按钮并验证结果
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, NeedsAction, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")

class SubmitStep(BasePublishStep):
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        """点击发布按钮并验证最终结果"""
        await self._await_pause(metadata)
        logger.info("===== 寻找并点击发布按钮 =====")
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))
        wait_ms = lambda ms: int(ms * speed_rate)

        # 唯一选择器：步骤7 已滚到底且刚执行完，页面未变，发布按钮已加载
        selector = Selectors.PUBLISH["SUBMIT_BTN"][0]
        target_btn = None
        target_selector = ""
        find_timeout_ms = 5000
        try:
            btn = page.locator(selector).first
            if await btn.count() > 0:
                await btn.wait_for(state="visible", timeout=find_timeout_ms)
                target_btn = btn
                target_selector = selector
        except Exception:
            pass

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
            await self._await_pause(metadata)
            is_disabled = await target_btn.get_attribute("disabled")
            if is_disabled is None or is_disabled == "false":
                is_ready = True
                break
            logger.info("发布按钮当前不可用（可能仍在转码中），继续等待...")
            try:
                from src.infrastructure.anti_risk.delays import random_delay
                await random_delay(page, wait_ms(3000), metadata, metadata.get("anti_risk_config"))
            except Exception:
                await page.wait_for_timeout(wait_ms(3000))
            
        if not is_ready:
            return PublishResult(
                success=False,
                error_message="等待视频转码/处理超时，发布按钮始终不可用"
            )
            
        config = metadata.get("anti_risk_config") or {}
        logger.info("发布按钮已就绪，先定位到按钮位置再点击...")
        try:
            await self._await_pause(metadata)
            try:
                from src.infrastructure.anti_risk.delays import random_delay
                await random_delay(page, wait_ms(200), metadata, config)
            except Exception:
                await page.wait_for_timeout(wait_ms(200))
            # 点击前先查找发布按钮位置：重新定位、滚入视口、取 box 确认在屏内后再点
            target_btn = page.locator(selector).first
            await target_btn.wait_for(state="visible", timeout=5000)
            await target_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(150)
            box = await target_btn.bounding_box()
            if box:
                logger.info(f"发布按钮位置: x={box['x']:.0f} y={box['y']:.0f} w={box['width']:.0f} h={box['height']:.0f}")
            # 第一次点击
            await target_btn.click(force=True)
            logger.info("已执行第一次点击")
            USER_LOG.info("[步骤8/8 点击发布] ▶ 已点击发布按钮")

            # 2 秒内检测 Toast 或页面跳转，都没有则执行第二次点击
            toast_sel = "span.semi-toast-content-text:has-text('发布成功'), .semi-toast-success:has-text('发布成功')"
            detected = False
            for _ in range(10):
                await page.wait_for_timeout(200)
                try:
                    if await page.locator(toast_sel).first.count() > 0 and await page.locator(toast_sel).first.is_visible():
                        detected = True
                        logger.info("2s 内检测到「发布成功」Toast")
                        break
                except Exception:
                    pass
                try:
                    if "manage" in page.url and "creator.douyin.com" in page.url:
                        detected = True
                        logger.info("2s 内检测到页面已跳转")
                        break
                except Exception:
                    pass
            if not detected:
                logger.info("2s 内未检测到 Toast 或跳转，执行第二次点击...")
                try:
                    target_btn = page.locator(selector).first
                    if await target_btn.count() > 0:
                        await target_btn.wait_for(state="visible", timeout=3000)
                        await target_btn.scroll_into_view_if_needed()
                        await page.wait_for_timeout(100)
                        await target_btn.click(force=True)
                        logger.info("已执行第二次点击")
                except Exception as e:
                    logger.warning(f"第二次点击异常: {e}")
        except Exception as e:
            return PublishResult(success=False, error_message=f"点击发布按钮失败: {str(e)}")
            
        # 点击发布后尽快开始检测：Toast 仅显示约 2–3 秒即消失，延迟要短、检测要快
        logger.info("检查发布后是否存在弹窗或错误提示...")
        try:
            from src.infrastructure.anti_risk.delays import random_delay
            await random_delay(page, wait_ms(200), metadata, config)
        except Exception:
            await page.wait_for_timeout(wait_ms(200))
        
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
                    # 对可补救的阻塞转为 NeedsAction，交由 Runner/上层步骤闭环处理
                    if "封面" in desc:
                        return NeedsAction(action="need_cover", message=f"点击发布后受阻: {desc}")
                    if "补充信息" in desc:
                        return NeedsAction(action="need_supplement", message=f"点击发布后受阻: {desc}")
                    if "操作频繁" in desc or "风控" in desc:
                        try:
                            from src.infrastructure.anti_risk.delays import cooldown_before_retry
                            sec = (metadata.get("anti_risk_config") or {}).get("cooldown_after_frequent_seconds", 180)
                            await cooldown_before_retry(float(sec), reason="操作频繁")
                            return NeedsAction(action="need_retry", message="操作频繁，已冷却后重试")
                        except Exception:
                            pass
                    return PublishResult(success=False, error_message=f"点击发布后受阻: {desc}")
        except Exception as e:
            logger.debug(f"检查弹窗出现异常（不影响主流程）: {e}")

        # 将返回具体的验证结果，该步骤需要终结这个责任链
        return await self._verify_publish_result(page, metadata)

    async def _verify_publish_result(self, page: Page, metadata: Dict[str, Any]) -> PublishResult:
        """验证发布结果：先查 URL，再轮询 Toast，最后兜底等跳转。"""
        logger.info("===== 验证发布结果 =====")
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))

        # ── 0. 若已跳转则直接成功（点击后有时跳转很快）──
        try:
            current_url = page.url
            if "manage" in current_url and "creator.douyin.com" in current_url:
                logger.info(f"页面已在作品管理页: {current_url}，视为发布成功")
                USER_LOG.info(f"[步骤8/8 点击发布] ✓ 发布成功 ({current_url})")
                return PublishResult(success=True, publish_url=current_url)
        except Exception:
            pass

        # 点击正确会迅速出 Toast 并跳转；若未跳转即说明本次点击未生效，不拉长等待
        try:
            await page.wait_for_url(
                lambda url: "manage" in url and "creator.douyin.com" in url,
                timeout=10000
            )
            logger.info(f"点击后检测到跳转: {page.url}")
            USER_LOG.info(f"[步骤8/8 点击发布] ✓ 发布成功 ({page.url})")
            return PublishResult(success=True, publish_url=page.url)
        except Exception:
            pass

        toast_selectors = [
            "span.semi-toast-content-text:has-text('发布成功')",
            ".semi-toast-success:has-text('发布成功')",
            "text='发布成功'",
        ]
        combined_toast_selector = ", ".join(toast_selectors)
        poll_interval_ms = 150
        total_wait_ms = 6000   # 最多 6 秒

        logger.info("检测「发布成功」Toast…")
        for _ in range(0, total_wait_ms, poll_interval_ms):
            try:
                loc = page.locator(combined_toast_selector).first
                if await loc.count() > 0 and await loc.is_visible():
                    logger.info("✓ 检测到「发布成功」Toast")
                    USER_LOG.info("[步骤8/8 点击发布] ✓ 发布成功！")
                    try:
                        await page.wait_for_url("**/manage**", timeout=5000)
                        logger.info(f"页面已跳转到作品管理页: {page.url}")
                    except Exception:
                        pass
                    return PublishResult(success=True, publish_url=page.url)
            except Exception:
                pass
            await page.wait_for_timeout(poll_interval_ms)
            # 每轮顺带检查 URL，若已跳转则直接成功
            try:
                if "manage" in page.url and "creator.douyin.com" in page.url:
                    logger.info(f"轮询中检测到已跳转: {page.url}")
                    USER_LOG.info(f"[步骤8/8 点击发布] ✓ 发布成功 ({page.url})")
                    return PublishResult(success=True, publish_url=page.url)
            except Exception:
                pass

        logger.info("未捕获到 Toast，尝试跳转兜底校验...")

        # ── 方式2（兜底）：再等 URL 含 manage ──
        try:
            await page.wait_for_url(
                lambda url: "manage" in url and "creator.douyin.com" in url,
                timeout=5000
            )
            logger.info(f"页面已跳转到作品管理页: {page.url}，视为发布成功")
            USER_LOG.info(f"[步骤8/8 点击发布] ✓ 发布成功 ({page.url})")
            return PublishResult(success=True, publish_url=page.url)
        except Exception:
            pass

        # ── 方式3（保守兜底）：仅当 URL 明确为作品管理页（含 manage）才视为成功 ──
        # 不再用「只要不含 upload 就成功」——未选封面等会导致不跳转但 URL 可能变化，造成误判成功。
        current_url = page.url
        if "upload" not in current_url and "creator.douyin.com" in current_url and "manage" in current_url:
            logger.info(f"页面已进入作品管理页: {current_url}，视为发布成功")
            USER_LOG.info(f"[步骤8/8 点击发布] ✓ 发布成功 ({current_url})")
            return PublishResult(success=True, publish_url=current_url)
        if "upload" not in current_url and "creator.douyin.com" in current_url:
            logger.warning(f"未检测到发布成功 Toast 且 URL 未含 manage，当前: {current_url}，不采纳兜底成功")

        if "upload" in current_url:
            logger.warning(f"页面仍停留在上传页，可能发布遇到静默阻挡（如未选封面）: {current_url}")

        logger.warning("未能确认发布成功，请手动检查")
        return PublishResult(
            success=False,
            error_message="发布后未能确认成功（未检测到'发布成功'提示或页面跳转），请手动检测"
        )
