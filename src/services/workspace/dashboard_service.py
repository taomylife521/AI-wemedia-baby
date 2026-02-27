"""
数据统计服务
文件路径：src/business/workspace/dashboard_service.py
功能：提供工作台数据统计
"""

from typing import Dict, Any, Optional
import asyncio
import inspect
from ...utils.date_utils import get_today_start, get_today_end
import logging

logger = logging.getLogger(__name__)


class DashboardService:
    """数据统计服务（支持同步和异步）"""
    
    def __init__(
        self,
        user_id: int,
        account_manager=None,
        batch_task_manager=None,
        publish_record_repository=None
    ):
        """初始化数据统计服务
        
        Args:
            user_id: 用户ID
            account_manager: 账号管理器（可以是同步或异步版本）
            batch_task_manager: 批量任务管理器（可以是同步或异步版本）
            publish_record_repository: 发布记录仓储服务（可选，从服务定位器获取）
        """
        from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
        from src.infrastructure.common.di.service_locator import ServiceLocator
        
        self.user_id = user_id
        self.publish_record_repo = publish_record_repository or ServiceLocator().get(PublishRecordRepositoryAsync)
        self.account_manager = account_manager
        self.batch_task_manager = batch_task_manager
        self.logger = logging.getLogger(__name__)
    
    def _run_async(self, coro):
        """运行异步协程（同步包装）
        
        注意：如果事件循环已经在运行，需要使用新线程来执行
        """
        import threading
        
        # 检查是否有运行中的事件循环
        try:
            asyncio.get_running_loop()
            # 如果有运行中的事件循环，在新线程中执行
            result_container = {'value': None, 'exception': None}
            
            def run_in_thread():
                """在新线程中运行异步代码"""
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result_container['value'] = new_loop.run_until_complete(coro)
                    new_loop.close()
                except Exception as e:
                    result_container['exception'] = e
            
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            thread.join(timeout=30)  # 最多等待30秒
            
            if thread.is_alive():
                raise TimeoutError("异步操作超时")
            
            if result_container['exception']:
                raise result_container['exception']
            return result_container['value']
        except RuntimeError:
            # 没有运行中的事件循环，尝试获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，使用新线程
                    result_container = {'value': None, 'exception': None}
                    
                    def run_in_thread():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result_container['value'] = new_loop.run_until_complete(coro)
                            new_loop.close()
                        except Exception as e:
                            result_container['exception'] = e
                    
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
                    thread.join(timeout=30)
                    
                    if thread.is_alive():
                        raise TimeoutError("异步操作超时")
                    
                    if result_container['exception']:
                        raise result_container['exception']
                    return result_container['value']
                else:
                    # 事件循环存在但未运行，可以直接使用
                    return loop.run_until_complete(coro)
            except RuntimeError:
                # 完全没有事件循环，创建新的
                return asyncio.run(coro)
    
    def get_account_statistics(self) -> Dict[str, Any]:
        """获取账号统计
        
        Returns:
            账号统计字典
        """
        try:
            # 检查是否是异步方法
            get_accounts = getattr(self.account_manager, 'get_accounts')
            if inspect.iscoroutinefunction(get_accounts):
                accounts = self._run_async(get_accounts())
            else:
                accounts = get_accounts()
            
            total = len(accounts)
            
            # 按平台统计
            platform_stats = {}
            for account in accounts:
                platform = account.get('platform', 'unknown')
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
            
            # 在线/离线统计
            online = sum(1 for acc in accounts if acc.get('login_status') == 'online')
            offline = total - online
            
            return {
                'total': total,
                'online': online,
                'offline': offline,
                'by_platform': platform_stats
            }
        except Exception as e:
            self.logger.error(f"获取账号统计失败: {e}", exc_info=True)
            return {
                'total': 0,
                'online': 0,
                'offline': 0,
                'by_platform': {}
            }
    
    def get_publish_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取发布统计
        
        Args:
            days: 统计天数（默认30天）
        
        Returns:
            发布统计字典
        """
        try:
            # 检查是否是异步方法
            get_publish_records = getattr(self.publish_record_repo, 'find_records')
            if inspect.iscoroutinefunction(get_publish_records):
                records = self._run_async(get_publish_records(
                    user_id=self.user_id,
                    limit=10000  # 获取足够多的记录
                ))
            else:
                records = get_publish_records(
                    user_id=self.user_id,
                    limit=10000  # 获取足够多的记录
                )
            
            total = len(records)
            success = sum(1 for r in records if r.get('status') == 'success')
            failed = sum(1 for r in records if r.get('status') == 'failed')
            pending = sum(1 for r in records if r.get('status') == 'pending')
            
            # 今日发布统计
            today_start = get_today_start().strftime('%Y-%m-%d %H:%M:%S')
            today_end = get_today_end().strftime('%Y-%m-%d %H:%M:%S')
            today_records = [
                r for r in records
                if today_start <= r.get('created_at', '') <= today_end
            ]
            today_count = len(today_records)
            today_success = sum(1 for r in today_records if r.get('status') == 'success')
            
            # 按平台统计
            platform_stats = {}
            for record in records:
                platform = record.get('platform', 'unknown')
                if platform not in platform_stats:
                    platform_stats[platform] = {
                        'total': 0,
                        'success': 0,
                        'failed': 0
                    }
                platform_stats[platform]['total'] += 1
                if record.get('status') == 'success':
                    platform_stats[platform]['success'] += 1
                elif record.get('status') == 'failed':
                    platform_stats[platform]['failed'] += 1
            
            # 获取最近发布记录（用于最近活动显示）
            recent_records = sorted(
                records,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )[:10]  # 最近10条
            
            return {
                'total': total,
                'success': success,
                'failed': failed,
                'pending': pending,
                'today_count': today_count,
                'today_success': today_success,
                'by_platform': platform_stats,
                'recent_records': recent_records
            }
        except Exception as e:
            self.logger.error(f"获取发布统计失败: {e}", exc_info=True)
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'pending': 0,
                'today_count': 0,
                'today_success': 0,
                'by_platform': {},
                'recent_records': []
            }
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计
        
        Returns:
            任务统计字典
        """
        try:
            if not self.batch_task_manager:
                return {
                    'total': 0,
                    'by_status': {},
                    'completion_rate': 0
                }
                
            # 检查是否是异步方法
            get_tasks = getattr(self.batch_task_manager, 'get_tasks')
            if inspect.iscoroutinefunction(get_tasks):
                tasks = self._run_async(get_tasks())
            else:
                tasks = get_tasks()
            
            total = len(tasks)
            
            # 按状态统计
            status_stats = {}
            for task in tasks:
                status = task.get('status', 'unknown')
                status_stats[status] = status_stats.get(status, 0) + 1
            
            # 计算完成率
            completed = status_stats.get('completed', 0)
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'by_status': status_stats,
                'completion_rate': round(completion_rate, 2)
            }
        except Exception as e:
            self.logger.error(f"获取任务统计失败: {e}", exc_info=True)
            return {
                'total': 0,
                'by_status': {},
                'completion_rate': 0
            }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取所有工作台数据
        
        Returns:
            工作台数据字典
        """
        return {
            'account': self.get_account_statistics(),
            'publish': self.get_publish_statistics(),
            'task': self.get_task_statistics()
        }

