from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal, Union

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult


@dataclass(frozen=True)
class NeedsAction:
    """步骤链中的“可补救动作”信号。

    用于在 Submit 后遇到“需要封面/补充信息”等阻塞时，返回给上层 Runner 处理并重试提交。
    """

    action: Literal["need_cover", "need_supplement", "need_retry"]
    message: str = ""


StepOutcome = Optional[Union[PublishResult, NeedsAction]]

class BasePublishStep(ABC):
    @abstractmethod
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> StepOutcome:
        """
        执行当前发布步骤
        
        Args:
            page: Playwright Page 对象
            file_path: 视频文件路径
            metadata: 元数据信息 (标题、描述等)
            
        Returns:
            None 表示成功执行完毕当前步骤，流程可放行继续
            PublishResult 表示该步骤发生中断、错误或流程完结，需抛出给外层
            NeedsAction 表示需要补齐信息或做特定动作后再继续/重试
        """
        pass

    async def _await_pause(self, metadata: Dict[str, Any]) -> None:
        """检查并等待暂停事件"""
        pause_event = metadata.get("pause_event")
        if pause_event is not None and hasattr(pause_event, "wait"):
            await pause_event.wait()
