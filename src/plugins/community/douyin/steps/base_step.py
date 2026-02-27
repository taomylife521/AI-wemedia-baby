from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from playwright.async_api import Page
from src.plugins.core.interfaces.publish_plugin import PublishResult

class BasePublishStep(ABC):
    @abstractmethod
    async def execute(self, page: Page, file_path: str, metadata: Dict[str, Any]) -> Optional[PublishResult]:
        """
        执行当前发布步骤
        
        Args:
            page: Playwright Page 对象
            file_path: 视频文件路径
            metadata: 元数据信息 (标题、描述等)
            
        Returns:
            None 表示成功执行完毕当前步骤，流程可放行继续
            PublishResult 表示该步骤发生中断、错误或流程完结，需抛出给外层
        """
        pass
