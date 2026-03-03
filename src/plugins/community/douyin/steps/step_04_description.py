# 步骤4：作品描述 — 填写标题、作品简介（含 #话题）
# 作品简介规则：与单发页一致，仅「#关键词+空格」视为已确认话题，整段 description 原样填入抖音简介输入框
import logging
import re
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome
from ..selectors import Selectors

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")

class MetadataFillStep(BasePublishStep):
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        """填写元数据：标题 + 作品简介（含已确认的 #话题，与单发页解析规则一致）。"""
        await self._await_pause(metadata)
        title = metadata.get("title", "") or ""
        description = metadata.get("description", "") or ""
        tags = metadata.get("tags", []) or []
        tags = (
            tags
            if isinstance(tags, list)
            else [t.strip() for t in str(tags).split(",") if t.strip()]
        )

        logger.info(f"开始填写元数据: 标题={(title or '')[:20]}..., 作品简介长度={len(description)}, 已确认话题数={len(tags) if tags else 0}")

        # 发布速度倍率：界面「速度」设置，倍率越高输入与等待越慢
        speed_rate = max(0.5, float(metadata.get("speed_rate", 1.0)))
        desc_delay = max(20, int(50 * speed_rate))
        wait_ms = lambda ms: int(ms * speed_rate)
        config = metadata.get("anti_risk_config") or {}

        # 1) 标题（尽力填写，失败不强阻断；拟人输入）
        if title:
            for selector in Selectors.PUBLISH["TITLE_INPUT"]:
                try:
                    title_input = page.locator(selector).first
                    if await title_input.count() > 0 and await title_input.is_visible():
                        try:
                            from src.infrastructure.anti_risk.human_like import human_type_text
                            await human_type_text(page, selector, title.strip(), metadata, config)
                        except Exception:
                            await title_input.click()
                            await page.keyboard.press("Control+A")
                            await page.keyboard.press("Backspace")
                            await title_input.type(title.strip(), delay=max(10, int(30 * speed_rate)))
                        logger.info(f"已填写标题: {selector}")
                        t = (title or "").strip()
                        t_display = t[:25] + "..." if len(t) > 25 else t or "（空）"
                        USER_LOG.info(f"[步骤4/8 作品描述] ▶ 标题已填写：{t_display}")
                        break
                except Exception:
                    continue

        # 作品简介输入框：抖音为 contenteditable div，优先用精确选择器，失败时用 placeholder 备选
        editor_selectors = list(Selectors.PUBLISH["DESC_EDITOR"])
        if Selectors.PUBLISH.get("DESC_PLACEHOLDER"):
            for s in Selectors.PUBLISH["DESC_PLACEHOLDER"]:
                if s not in editor_selectors:
                    editor_selectors.append(s)

        for selector in editor_selectors:
            try:
                edit_box = page.locator(selector).first
                if await edit_box.count() > 0 and await edit_box.is_visible():
                    logger.info(f"找到编辑器: {selector}")
                    try:
                        from src.infrastructure.anti_risk.human_like import human_click
                        await human_click(page, edit_box, metadata, config)
                    except Exception:
                        await edit_box.click()
                    try:
                        from src.infrastructure.anti_risk.delays import random_delay
                        await random_delay(page, wait_ms(500), metadata, config)
                    except Exception:
                        await page.wait_for_timeout(wait_ms(500))

                    # 清空已有内容
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    try:
                        from src.infrastructure.anti_risk.delays import random_delay
                        await random_delay(page, wait_ms(300), metadata, config)
                    except Exception:
                        await page.wait_for_timeout(wait_ms(300))

                    # 作品简介 = 全文（含已确认的 #话题），与单发页一致，不在此处再追加 tags
                    full_text = (description or title or "").strip()

                    # 以模拟真实用户的速度逐字输入到抖音作品简介输入框（delay 受 speed_rate 控制）
                    await edit_box.type(full_text, delay=desc_delay)
                    try:
                        from src.infrastructure.anti_risk.delays import random_delay
                        await random_delay(page, wait_ms(800), metadata, config)
                    except Exception:
                        await page.wait_for_timeout(wait_ms(800))

                    # 仅当简介以 #关键词 结尾且无空格时，补按空格以在抖音端确认末尾话题（与单发页「按空格才确认」一致）
                    if full_text and re.search(r"#\S+$", full_text):
                        await page.keyboard.press("Space")
                        await page.wait_for_timeout(200)

                    logger.info("元数据填写完成（作品简介已含话题）")
                    desc_part = (description or title or "").strip()
                    desc_display = (desc_part[:35] + "...") if len(desc_part) > 35 else (desc_part or "（空）")
                    tag_count = len(tags) if isinstance(tags, list) and tags else 0
                    USER_LOG.info(f"[步骤4/8 作品描述] ✓ 作品简介已填写：{desc_display}，已确认话题数={tag_count}")
                    return None
            except Exception as e:
                logger.warning(f"使用选择器 {selector} 填写失败: {e}")
                continue

        logger.warning("未能找到编辑器元素，跳过元数据填写 (如果平台必须填写则这会导致发布失败)")
        return None
