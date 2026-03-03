"""
平台发布过滤器（异步版本）
文件路径：src/business/publish_pipeline/filters/platform_publish_filter_async.py
功能：执行平台发布操作（异步）
"""

from typing import Optional
from src.infrastructure.common.pipeline.base_filter import BaseFilter, PublishContext
from src.services.common.platform_adapter import PlatformAdapter
# 确保平台适配器已注册（可以通过导入 src.platforms 包实现）
# 这里简单假设在应用启动时加载了所有平台模块
import src.platforms.douyin
import src.platforms.xiaohongshu
import logging

logger = logging.getLogger(__name__)


from src.services.common.platform_registry import PlatformRegistry



class PlatformPublishFilterAsync(BaseFilter):
    """平台发布过滤器（异步版本）"""
    
    def __init__(self):
        """初始化平台发布过滤器"""
        super().__init__()
    
    async def process(self, context: PublishContext) -> bool:
        """执行发布操作（异步）
        
        Args:
            context: 发布上下文
        
        Returns:
            如果发布成功返回True，否则返回False
        """
        try:
            # 获取平台适配器
            # adapter = self.adapter_factory.create_adapter(context.platform)
            # 使用 Registry 获取适配器
            adapter = PlatformRegistry.get_adapter(context.platform)
            
            if not adapter:
                self.set_error(f"不支持的平台: {context.platform}")
                return False
            
            # 获取浏览器实例（从context或通过其他方式）
            browser = None
            if hasattr(context, 'browser'):
                browser = context.browser
            
            if not browser:
                self.set_error("浏览器实例不存在")
                return False
            
            # 执行发布（注意：PlatformAdapter可能是同步的，需要适配）
            # 这里假设适配器是同步的，如果需要异步，需要修改适配器
            # 使用管道层面透传下来的精准发布类型进行判别
            publish_type = getattr(context, 'publish_type', 'video')
            
            if publish_type == 'video':
                result = adapter.publish_video(
                    browser=browser,
                    cookie_data=None,  # Cookie已注入浏览器
                    file_path=context.file_path,
                    title=context.title,
                    description=context.description,
                    tags=context.tags
                )
            elif publish_type == 'image':
                # 图片发布需要路径列表
                image_paths = [context.file_path]  # 单个图片转为列表
                result = adapter.publish_image(
                    browser=browser,
                    cookie_data=None,  # Cookie已注入浏览器
                    image_paths=image_paths,
                    title=context.title,
                    description=context.description,
                    tags=context.tags
                )
            else:
                self.set_error(f"不支持的发布类型: {publish_type}")
                return False
            
            if result.get('success'):
                publish_url = result.get('publish_url')
                # 存储发布URL到context（如果context支持）
                if hasattr(context, 'publish_url'):
                    context.publish_url = publish_url
                self.logger.info(f"发布成功: {publish_url}")
                return True
            else:
                error_msg = result.get('error_message', '发布失败')
                self.set_error(error_msg)
                return False
            
        except Exception as e:
            self.set_error(f"发布操作失败: {str(e)}")
            self.logger.error(self.get_error(), exc_info=True)
            return False

