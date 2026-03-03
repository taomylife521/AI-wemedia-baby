"""
发布管道模块（优化版）
文件路径：src/core/common/pipeline/publish_pipeline.py
功能：提供发布流程的管道-过滤器模式实现，支持并行执行、断点续传、动态过滤器
"""

import asyncio
import time
from typing import List, Optional, Type, Dict, Any
import logging

from .base_filter import (
    BaseFilter,
    IPublishFilter,
    PublishRequest,
    PublishResponse,
    PublishResult,
    PublishContext
)

logger = logging.getLogger(__name__)


class PublishPipeline:
    """发布管道 - 使用管道-过滤器模式执行发布流程（优化版）
    
    支持：
    - 并行执行（使用asyncio.Semaphore控制并发数）
    - 断点续传（从数据库恢复未完成任务）
    - 动态过滤器（执行前可插入过滤器）
    """
    
    def __init__(self, max_concurrent: int = 5, data_storage=None):
        """初始化发布管道
        
        Args:
            max_concurrent: 最大并发数（默认5）
            data_storage: 数据存储服务（可选，用于任务恢复）
        """
        self.filters: List[IPublishFilter] = []
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.data_storage = data_storage  # 用于任务恢复
        self.logger = logging.getLogger(__name__)
    
    def add_filter(self, filter_instance: IPublishFilter) -> None:
        """添加过滤器
        
        Args:
            filter_instance: 过滤器实例
        """
        self.filters.append(filter_instance)
        self.logger.debug(f"添加过滤器: {type(filter_instance).__name__}")
    
    def remove_filter(self, filter_type: Type[IPublishFilter]) -> None:
        """移除过滤器
        
        Args:
            filter_type: 过滤器类型
        """
        self.filters = [f for f in self.filters if not isinstance(f, filter_type)]
        self.logger.debug(f"移除过滤器: {filter_type.__name__}")
    
    def insert_filter(
        self,
        filter_instance: IPublishFilter,
        position: int
    ) -> None:
        """在指定位置插入过滤器（动态过滤器）
        
        Args:
            filter_instance: 过滤器实例
            position: 插入位置
        """
        self.filters.insert(position, filter_instance)
        self.logger.debug(f"插入过滤器: {type(filter_instance).__name__} at position {position}")
    
    async def execute(
        self,
        request: PublishRequest
    ) -> List[PublishResult]:
        """执行发布管道（异步，支持并行执行）
        
        Args:
            request: 发布请求
        
        Returns:
            发布结果列表（支持批量发布，返回多个结果）
        """
        async with self.semaphore:
            start_time = time.time()
            context = PublishContext(
                user_id=request.user_id,
                account_name=request.account_name,
                platform=request.platform,
                file_path=request.file_path,
                publish_type=getattr(request, 'publish_type', 'video'),
                title=request.title,
                description=request.description,
                tags=request.tags,
                headless=request.headless,
                speed_rate=request.speed_rate,
                pause_event=request.pause_event,
                cover_type=getattr(request, 'cover_type', None),
                cover_path=getattr(request, 'cover_path', None),
                scheduled_publish_time=getattr(request, 'scheduled_publish_time', None),
            )
            
            try:
                # 按顺序执行过滤器
                for filter_instance in self.filters:
                    success = await filter_instance.process(context)
                    if not success:
                        error = filter_instance.get_error() or "过滤器处理失败"
                        context.error_message = error
                        self.logger.error(f"过滤器处理失败: {type(filter_instance).__name__}, 错误: {error}")
                        
                        return [PublishResult(
                            success=False,
                            error_message=error,
                            execution_time=time.time() - start_time
                        )]
                
                # 所有过滤器处理成功
                execution_time = time.time() - start_time
                return [PublishResult(
                    success=True,
                    publish_url=context.publish_url if hasattr(context, 'publish_url') else None,
                    execution_time=execution_time
                )]
            
            except Exception as e:
                self.logger.error(f"发布管道执行失败: {e}", exc_info=True)
                return [PublishResult(
                    success=False,
                    error_message=str(e),
                    execution_time=time.time() - start_time
                )]
    
    async def execute_batch(
        self,
        requests: List[PublishRequest]
    ) -> List[PublishResult]:
        """批量执行发布管道（异步，并行执行）
        
        Args:
            requests: 发布请求列表
        
        Returns:
            发布结果列表
        """
        tasks = [self.execute(request) for request in requests]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 展平结果列表
        results = []
        for result in results_list:
            if isinstance(result, Exception):
                results.append(PublishResult(
                    success=False,
                    error_message=str(result)
                ))
            else:
                results.extend(result)
        
        return results
    
    async def resume_failed_tasks(
        self,
        user_id: int,
        platform: Optional[str] = None
    ) -> List[PublishResult]:
        """恢复失败的任务（断点续传）
        
        Args:
            user_id: 用户ID
            platform: 平台名称（可选）
        
        Returns:
            发布结果列表
        """
        # 从数据库获取未完成的任务（status=pending或running）
        # 这里需要注入DataStorage依赖
        # 为了简化，这里只提供接口，具体实现需要注入依赖
        
        # 从数据库恢复未完成的任务
        self.logger.info(f"恢复失败任务: user_id={user_id}, platform={platform}")
        
        if not self.data_storage:
            self.logger.warning("未配置数据存储服务，无法恢复任务")
            return []
        
        try:
            # 从数据库获取未完成的发布记录（status='pending' 或 'running'）
            pending_records = await self.data_storage.get_publish_records(
                user_id=user_id,
                platform=platform,
                status='pending',
                limit=100
            )
            
            running_records = await self.data_storage.get_publish_records(
                user_id=user_id,
                platform=platform,
                status='running',
                limit=100
            )
            
            # 合并未完成的任务
            failed_records = pending_records + running_records
            
            if not failed_records:
                self.logger.info("没有需要恢复的任务")
                return []
            
            self.logger.info(f"找到 {len(failed_records)} 个未完成的任务，开始恢复...")
            
            # 将数据库记录转换为 PublishRequest
            requests = []
            for record in failed_records:
                request = PublishRequest(
                    user_id=record.get('user_id'),
                    account_name=record.get('platform_username'),
                    platform=record.get('platform'),
                    file_path=record.get('file_path'),
                    title=record.get('title', ''),
                    description=record.get('description'),
                    tags=record.get('tags', '').split(',') if record.get('tags') else [],
                    headless=True,  # 恢复任务默认使用无头模式
                    speed_rate=1.0,
                    scheduled_publish_time=record.get('scheduled_publish_time')
                )
                requests.append(request)
            
            # 批量执行恢复的任务
            results = await self.execute_batch(requests)
            
            self.logger.info(f"任务恢复完成，成功: {sum(1 for r in results if r.success)}, 失败: {sum(1 for r in results if not r.success)}")
            return results
            
        except Exception as e:
            self.logger.error(f"恢复任务失败: {e}", exc_info=True)
            return []
    
    def load_from_config(self, platform_config: Dict[str, Any]) -> None:
        """从平台配置加载过滤器链
        
        Args:
            platform_config: 平台配置字典，包含publish_pipeline字段
        """
        pipeline_config = platform_config.get('publish_pipeline', [])
        
        # 清空现有过滤器
        self.filters.clear()
        
        # 根据配置动态加载过滤器
        for filter_config in pipeline_config:
            filter_type = filter_config.get('type')
            filter_params = filter_config.get('params', {})
            
            # 动态加载过滤器
            filter_instance = self._load_filter_by_type(filter_type, filter_params)
            if filter_instance:
                self.add_filter(filter_instance)
                self.logger.info(f"从配置加载过滤器: {filter_type}")
            else:
                self.logger.warning(f"未找到过滤器类型: {filter_type}")
    
    def _load_filter_by_type(self, filter_type: str, params: Dict[str, Any] = None) -> Optional[IPublishFilter]:
        """根据类型动态加载过滤器
        
        Args:
            filter_type: 过滤器类型（如 'validation', 'platform', 'notification'）
            params: 过滤器参数
        
        Returns:
            过滤器实例，如果不存在返回None
        """
        params = params or {}
        
        # 过滤器类型映射
        filter_mapping = {
            'validation': 'src.services.publish.pipeline.filters.validation_filter',
            'platform': 'src.services.publish.pipeline.filters.platform_publish_filter',
            'platform_async': 'src.services.publish.pipeline.filters.platform_publish_filter_async',
            'notification': 'src.services.publish.pipeline.filters.notification_filter',
            'logging': 'src.services.publish.pipeline.filters.logging_filter',
        }
        
        module_path = filter_mapping.get(filter_type)
        if not module_path:
            self.logger.warning(f"未知的过滤器类型: {filter_type}")
            return None
        
        try:
            # 动态导入模块
            import importlib
            module = importlib.import_module(module_path)
            
            # 获取过滤器类（首字母大写 + Filter）
            # 例如: 'validation' -> 'ValidationFilter'
            class_name = ''.join(word.capitalize() for word in filter_type.split('_')) + 'Filter'
            filter_class = getattr(module, class_name, None)
            
            if not filter_class:
                self.logger.warning(f"模块 {module_path} 中未找到类: {class_name}")
                return None
            
            # 实例化过滤器
            filter_instance = filter_class(**params)
            self.logger.debug(f"动态加载过滤器成功: {class_name}")
            return filter_instance
            
        except Exception as e:
            self.logger.error(f"加载过滤器失败: {filter_type}, 错误: {e}", exc_info=True)
            return None

