"""
抖音发布插件
文件路径：src/plugins/community/douyin/publish_plugin.py
功能：基于 Playwright 自动化完成抖音创作者平台的内容发布
"""

from typing import List, Dict, Any, Optional
import logging
import json
import asyncio
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishPluginInterface, PublishResult, FormField
from .selectors import Selectors

logger = logging.getLogger(__name__)


class DouyinPublishPlugin(PublishPluginInterface):
    """抖音发布插件 - 负责在抖音创作者平台执行自动化视频发布"""

    # ========== 抖音创作者平台关键常量 ==========
    UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"
    # 用于检测未登录状态的 URL 关键词列表
    LOGIN_URL_KEYWORDS = ["login", "passport", "sso"]
    # 用于检测页面中出现登录组件的文字列表
    LOGIN_TEXT_INDICATORS = ["密码登录", "短信登录", "扫码登录", "验证码登录"]

    @property
    def platform_id(self) -> str:
        return "douyin"

    def get_form_schema(self, content_type: str = "video") -> List[FormField]:
        """返回发布表单定义"""
        schema = [
            FormField(name="title", label="标题", field_type="text", placeholder="输入视频标题"),
            FormField(name="description", label="描述", field_type="textarea", placeholder="输入作品描述..."),
            FormField(name="tags", label="标签", field_type="text", required=False, placeholder="标签, 用逗号隔开"),
        ]
        return schema

    async def publish(
        self,
        context: Page,
        file_path: str,
        metadata: Dict[str, Any]
    ) -> PublishResult:
        """执行抖音自动发布流程 (基于步骤责任链)

        Args:
            context: Playwright Page 对象（已注入账号凭证）
            file_path: 本地视频文件路径
            metadata: 元数据字典，包含 title, description, tags 等

        Returns:
            PublishResult 发布结果
        """
        page = context
        try:
            logger.info(f"===== 抖音发布插件启动 =====")
            logger.info(f"目标文件: {file_path}")

            from .steps.navigate_step import NavigateStep
            from .steps.upload_step import UploadStep
            from .steps.metadata_step import MetadataFillStep
            from .steps.submit_step import SubmitStep

            # 构建责任链/任务管线
            steps = [
                NavigateStep(self.UPLOAD_URL, self.LOGIN_URL_KEYWORDS),
                UploadStep(),
                MetadataFillStep(),
                SubmitStep()
            ]

            result = None
            for step in steps:
                step_name = step.__class__.__name__
                logger.info(f"--- 正在执行步骤: {step_name} ---")
                
                step_result = await step.execute(page, file_path, metadata)
                
                # 如果某一步骤返回了具体的 PublishResult 对象，说明其主动截断了流程
                # 这可能是发生了异常，也可能是最后一步的成功断言
                if step_result is not None:
                    result = step_result
                    break

            if result is None:
                return PublishResult(
                    success=False, 
                    error_message="发布流程异常中断：最后步骤未返回明确结果"
                )
                
            return result

        except Exception as e:
            logger.error(f"抖音发布插件异常: {e}", exc_info=True)
            return PublishResult(success=False, error_message=f"插件执行异常: {str(e)}")
