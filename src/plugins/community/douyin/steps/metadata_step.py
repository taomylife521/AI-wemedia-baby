import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from .base_step import BasePublishStep
from ..selectors import Selectors

logger = logging.getLogger(__name__)

class MetadataFillStep(BasePublishStep):
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        """填写视频元数据（标题/描述/标签）"""
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])

        logger.info(f"开始填写元数据: 标题={title[:20]}..., 标签数量={len(tags) if tags else 0}")

        # 查找描述输入区域（抖音使用 contenteditable div）
        editor_selectors = Selectors.PUBLISH["DESC_EDITOR"]

        for selector in editor_selectors:
            try:
                edit_box = page.locator(selector).first
                if await edit_box.count() > 0 and await edit_box.is_visible():
                    logger.info(f"找到编辑器: {selector}")
                    await edit_box.click()
                    await page.wait_for_timeout(500)

                    # 清空已有内容
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await page.wait_for_timeout(300)

                    # 拼接描述和话题标签
                    full_text = description or title or ""
                    if tags:
                        for tag in tags:
                            tag_clean = tag.strip().lstrip('#')
                            if tag_clean:
                                full_text += f" #{tag_clean} "

                    # 以模拟真实用户的速度逐字输入
                    await edit_box.type(full_text.strip(), delay=50)
                    logger.info("元数据填写完成")
                    return None
            except Exception as e:
                logger.warning(f"使用选择器 {selector} 填写失败: {e}")
                continue

        logger.warning("未能找到编辑器元素，跳过元数据填写 (如果平台必须填写则这会导致发布失败)")
        return None
