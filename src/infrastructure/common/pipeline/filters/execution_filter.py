"""
发布执行过滤器
文件路径：src/infrastructure/common/pipeline/filters/execution_filter.py
功能：调用 PublishExecutor 执行实际的发布操作
"""

import logging
from typing import List
from src.infrastructure.common.pipeline.base_filter import BaseFilter, PublishContext
from src.services.publish.publish_executor import PublishExecutorFactory

logger = logging.getLogger(__name__)

class PublishExecutionFilter(BaseFilter):
    """发布执行过滤器 - 调用执行器进行发布"""
    
    async def process(self, context: PublishContext) -> bool:
        """执行发布"""
        try:
            logger.info(f"ExecutionFilter: 开始执行发布任务 - {context.platform} - {context.account_name}")
            
            # 获取执行器
            executor = PublishExecutorFactory.get_executor(user_id=context.user_id)
            
            # 处理标签格式 (str -> List[str])
            tags_input = context.tags
            tags_list: List[str] = []
            
            if isinstance(tags_input, list):
                tags_list = tags_input
            elif isinstance(tags_input, str) and tags_input:
                # 尝试分割
                tags_list = [t.strip() for t in tags_input.replace('，', ',').split(',') if t.strip()]
            
            # 执行发布
            result = await executor.execute_single(
                account_name=context.account_name, # 注意：Executor使用account_name作为ID/Name
                platform=context.platform,
                file_path=context.file_path,
                title=context.title or "",
                description=context.description or "",
                tags=tags_list,
                headless=context.headless,
                speed_rate=context.speed_rate,
                pause_event=context.pause_event
                # file_type 默认为 video，暂不支持图片
            )
            
            if result.success:
                context.publish_url = result.publish_url
                logger.info("ExecutionFilter: 发布成功")
                return True
            else:
                self.set_error(result.error_message)
                logger.error(f"ExecutionFilter: 发布失败 - {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"ExecutionFilter: 执行异常 - {e}", exc_info=True)
            self.set_error(str(e))
            return False
