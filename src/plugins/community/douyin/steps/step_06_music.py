# 步骤6：选择音乐 — 图文发布时选背景音乐（占位）
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult
from ._base import BasePublishStep, StepOutcome

logger = logging.getLogger(__name__)
USER_LOG = logging.getLogger("publish.user_log")


class SelectMusicStep(BasePublishStep):
    """图文专属的选择音乐步骤（当前为框架占位，采用尽力而为策略）。"""

    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        await self._await_pause(metadata)
        logger.info("===== 图文扩展信息：选择音乐（占位实现） =====")
        keyword = (metadata.get("music_keyword") or "").strip()
        if keyword:
            USER_LOG.info(f"[步骤6/8 选择音乐] ▶ 关键字={keyword}（待实现）")
        else:
            USER_LOG.info("[步骤6/8 选择音乐] ✓ 跳过（未配置音乐）")

        # 这里暂时只做占位：后续可以根据真实 DOM 实现：
        # 1）点击“添加音乐/选择音乐”按钮
        # 2）根据 metadata['music_keyword'] 搜索
        # 3）选择第一首结果并确认
        # 目前直接返回 None，不阻断发布流程。
        return None

