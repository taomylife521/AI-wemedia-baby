"""
发布执行器
文件路径：src/services/publish/publish_executor.py
功能：集成 UndetectedBrowserManager 与发布管道，管理浏览器生命周期
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio

from src.infrastructure.common.pipeline.base_filter import PublishContext, PublishResult

logger = logging.getLogger(__name__)


class PublishExecutor:
    """发布执行器 - 集成浏览器管理与发布流程
    
    职责:
    1. 启动浏览器并加载账号凭证
    2. 将浏览器/页面实例注入 PublishContext
    3. 执行发布管道
    4. 管理浏览器生命周期
    """
    
    def __init__(
        self,
        user_id: int,
        data_storage=None,
        max_concurrent: int = 3
    ):
        """初始化发布执行器
        
        Args:
            user_id: 用户ID
            data_storage: 数据存储实例（可选）
            max_concurrent: 最大并发数
        """
        self.user_id = user_id
        self.data_storage = data_storage
        self.max_concurrent = max_concurrent
        
        self._browser_managers: Dict[str, Any] = {}  # account_id -> browser_manager
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_single(
        self,
        account_name: str,
        platform: str,
        file_path: str,
        title: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        file_type: str = "video",
        headless: bool = True,
        speed_rate: float = 1.0,
        pause_event: Any = None
    ) -> PublishResult:
        """执行单个发布任务
        
        Args:
            account_name: 账号名称（用作 account_id）
            platform: 平台ID
            file_path: 文件路径
            title: 标题
            description: 描述
            tags: 标签列表
            file_type: 文件类型 (video/image)
            headless: 是否使用无头模式
            speed_rate: 发布速度倍率
            pause_event: 暂停控制事件
            
        Returns:
            发布结果
        """
        browser_manager = None
        context = None
        page = None
        result = None  # 初始化 result 用于 finally 块判断
        
        try:
            async with self._semaphore:
                # Step 1: 获取 PlaywrightBrowserService 单例
                from src.infrastructure.common.di.service_locator import ServiceLocator
                from src.services.browser.playwright_service import PlaywrightBrowserService
                
                pw_service = ServiceLocator().get(PlaywrightBrowserService)
                if not pw_service or not pw_service.account_manager:
                    return PublishResult(success=False, error_message="PlaywrightBrowserService 未初始化，无法启动浏览器")
                
                account_mgr = pw_service.account_manager
                
                # Step 2: 通过 account_name + platform 查找数据库中的账号ID
                account_db_id = None
                try:
                    all_accounts = await account_mgr.get_accounts(platform=platform)
                    for a in all_accounts:
                        name = a.get('platform_username') or a.get('account_name', '') if isinstance(a, dict) else getattr(a, 'platform_username', '')
                        if name == account_name:
                            account_db_id = a.get('id') if isinstance(a, dict) else getattr(a, 'id', None)
                            break
                except Exception as e:
                    logger.warning(f"查询账号列表失败: {e}")
                
                if not account_db_id:
                    return PublishResult(success=False, error_message=f"未在数据库中找到账号: {account_name} (平台: {platform})")
                
                logger.info(f"发布任务: 账号={account_name}, 数据库ID={account_db_id}, 平台={platform}")
                
                # Step 3: 复用模块化方法打开浏览器（内部完成 查询→URL→启动→Cookie注入→导航）
                browser_wrapper = await pw_service.open_browser_for_db_account(account_db_id)
                if not browser_wrapper or not browser_wrapper.context:
                    return PublishResult(success=False, error_message="未能正确拉起或获取浏览器组件实例")
                    
                browser_context = browser_wrapper.context
                page = browser_wrapper.page
                browser_manager = browser_wrapper.browser_manager
                
                logger.info("发布所用浏览器拉取成功")
                
                # Step 4: 创建发布上下文
                context = PublishContext(
                    user_id=self.user_id,
                    account_name=account_name,
                    platform=platform,
                    file_path=file_path,
                    file_type=file_type,
                    title=title,
                    description=description,
                    tags=tags or [],
                    headless=headless,
                    speed_rate=speed_rate,
                    pause_event=pause_event
                )
                
                # 注入浏览器实例到上下文
                context.browser = browser_context
                context.page = page
                context.browser_manager = browser_manager
                
                # Step 5: 获取平台适配器并执行发布
                logger.info(f"开始执行平台发布逻辑: platform={platform}")
                result = await self._execute_platform_publish(context, platform)
                logger.info(f"平台发布逻辑执行结束: success={result.success}")
                
                # Step 6: 保存发布后的状态
                if result.success:
                    if browser_manager and hasattr(browser_manager, 'save_state'):
                        await browser_manager.save_state()
                    logger.info(f"发布成功: {result.publish_url}")
                else:
                    logger.warning(f"发布失败，保持浏览器打开以便用户查看: {result.error_message}")
                
                return result
                
        except Exception as e:
            logger.error(f"发布执行失败: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error_message=str(e)
            )
        finally:
            # 清理资源 - 只有成功时才清理，失败时保持浏览器打开
            if result and result.success:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                
                if browser_manager:
                    try:
                        await browser_manager.close()
                    except Exception:
                        pass
    
    async def _execute_platform_publish(
        self,
        context: PublishContext,
        platform: str
    ) -> PublishResult:
        """执行平台特定的发布逻辑
        
        Args:
            context: 发布上下文（已包含浏览器实例）
            platform: 平台ID
            
        Returns:
            发布结果
        """
        try:
            # 获取平台发布插件 (统一使用 src.plugins.core.plugin_manager)
            from src.plugins.core.plugin_manager import PluginManager
            
            plugin = PluginManager.get_publish_plugin(platform)
            
            if not plugin:
                return PublishResult(
                    success=False,
                    error_message=f"未找到平台插件: {platform}"
                )
            
            # 调用插件发布方法 (使用新接口 async publish)
            metadata = {
                "title": context.title,
                "description": context.description,
                "tags": context.tags,
                "speed_rate": context.speed_rate,
                "pause_event": context.pause_event,
                "file_type": context.file_type
            }
            
            result = await plugin.publish(
                context=context.page,  # 传入 Playwright Page 对象
                file_path=context.file_path,
                metadata=metadata
            )
            
            return result
            
        except Exception as e:
            logger.error(f"平台发布失败: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    async def _publish_video_with_plugin(
        self,
        plugin,
        context: PublishContext
    ) -> PublishResult:
        """使用插件发布视频
        
        Args:
            plugin: 平台插件实例
            context: 发布上下文
            
        Returns:
            发布结果
        """
        try:
            # 调用插件的发布方法
            # 注意：插件的 publish_video 可能需要适配异步
            result = await plugin.publish_video(
                page=context.page,
                file_path=context.file_path,
                title=context.title,
                description=context.description,
                tags=context.tags,
                speed_rate=context.speed_rate,
                pause_event=context.pause_event
            )
            
            if result.get('success'):
                return PublishResult(
                    success=True,
                    publish_url=result.get('publish_url')
                )
            else:
                # 插件返回 'message' 字段，兼容读取
                error_msg = result.get('message') or result.get('error_message', '发布失败')
                logger.error(f"插件发布失败: {error_msg}")
                return PublishResult(
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    async def _publish_image_with_plugin(
        self,
        plugin,
        context: PublishContext
    ) -> PublishResult:
        """使用插件发布图片
        
        Args:
            plugin: 平台插件实例
            context: 发布上下文
            
        Returns:
            发布结果
        """
        try:
            result = await plugin.publish_image(
                page=context.page,
                image_paths=[context.file_path],
                title=context.title,
                description=context.description,
                tags=context.tags
            )
            
            if result.get('success'):
                return PublishResult(
                    success=True,
                    publish_url=result.get('publish_url')
                )
            else:
                return PublishResult(
                    success=False,
                    error_message=result.get('error_message', '发布失败')
                )
                
        except Exception as e:
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    async def execute_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[PublishResult]:
        """批量执行发布任务
        
        Args:
            tasks: 任务列表，每个任务包含 account_name, platform, file_path 等
            
        Returns:
            发布结果列表
        """
        coroutines = [
            self.execute_single(
                account_name=task.get('account_name'),
                platform=task.get('platform'),
                file_path=task.get('file_path'),
                title=task.get('title', ''),
                description=task.get('description', ''),
                tags=task.get('tags'),
                file_type=task.get('file_type', 'video')
            )
            for task in tasks
        ]
        
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(PublishResult(
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results


class PublishExecutorFactory:
    """发布执行器工厂"""
    
    _instances: Dict[int, PublishExecutor] = {}
    
    @classmethod
    def get_executor(
        cls,
        user_id: int,
        data_storage=None,
        max_concurrent: int = 3
    ) -> PublishExecutor:
        """获取或创建发布执行器
        
        Args:
            user_id: 用户ID
            data_storage: 数据存储实例
            max_concurrent: 最大并发数
            
        Returns:
            发布执行器实例
        """
        if user_id not in cls._instances:
            cls._instances[user_id] = PublishExecutor(
                user_id=user_id,
                data_storage=data_storage,
                max_concurrent=max_concurrent
            )
        return cls._instances[user_id]
    
    @classmethod
    def clear_executor(cls, user_id: int):
        """清除指定用户的执行器"""
        if user_id in cls._instances:
            del cls._instances[user_id]
