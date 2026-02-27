"""
事件总线模块（优化版）
文件路径：src/core/common/event/event_bus.py
功能：统一管理事件的发布和订阅，支持优先级、事件溯源、异步处理器
"""

from typing import Dict, List, Callable, Any, Optional, Tuple
import asyncio
import logging
import aiosqlite
from datetime import datetime
from pathlib import Path

from .events import DomainEvent
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)


class EventHandler:
    """事件处理器包装类"""
    def __init__(self, handler: Callable, priority: int, is_async: bool):
        self.handler = handler
        self.priority = priority
        self.is_async = is_async

class EventBus:
    """事件总线 - 统一管理事件的发布和订阅（优化版）
    
    支持：
    - 事件优先级（0-10，数字越小优先级越高）
    - 异步处理器
    - 事件溯源（记录到event_log.sqlite）
    - 事件过滤
    """
    
    def __init__(self, event_log_path: str = None):
        """初始化事件总线
        
        Args:
            event_log_path: 事件日志数据库路径 (None则使用默认AppData路径)
        """
        self._subscribers: Dict[str, List[EventHandler]] = {}
        if event_log_path is None:
             self._event_log_path = str(PathManager.get_app_data_dir() / "data" / "event_log.sqlite")
        else:
             self._event_log_path = event_log_path
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._processing_task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(__name__)
        
        # 确保事件日志目录存在
        Path(self._event_log_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化事件日志数据库（延迟初始化，避免在__init__中创建任务）
        self._init_task: Optional[asyncio.Task] = None
    
    async def _init_event_log(self) -> None:
        """初始化事件日志数据库"""
        try:
            async with aiosqlite.connect(self._event_log_path) as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS event_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        event_id TEXT,
                        aggregate_id TEXT,
                        timestamp TEXT NOT NULL,
                        event_data TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_event_type ON event_log(event_type)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aggregate_id ON event_log(aggregate_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON event_log(timestamp)
                """)
                await conn.commit()
        except Exception as e:
            self._logger.error(f"初始化事件日志数据库失败: {e}", exc_info=True)
    
    async def _log_event(self, event: DomainEvent) -> None:
        """记录事件到事件日志（事件溯源）
        
        Args:
            event: 领域事件
        """
        try:
            import json
            event_data = json.dumps(event.to_dict(), ensure_ascii=False)
            
            async with aiosqlite.connect(self._event_log_path) as conn:
                await conn.execute("""
                    INSERT INTO event_log (event_type, event_id, aggregate_id, timestamp, event_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event.event_type,
                    event.event_id,
                    event.aggregate_id,
                    event.timestamp.isoformat(),
                    event_data
                ))
                await conn.commit()
        except Exception as e:
            self._logger.error(f"记录事件到日志失败: {e}", exc_info=True)
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        priority: int = 5
    ) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型（事件类名，如 "AccountAddedEvent"）
            handler: 事件处理函数，可以是同步或异步函数
            priority: 优先级（0-10，数字越小优先级越高，默认5）
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        # 检查是否为异步函数
        is_async = asyncio.iscoroutinefunction(handler)
        
        event_handler = EventHandler(handler, priority, is_async)
        
        # 按优先级插入（保持有序）
        subscribers = self._subscribers[event_type]
        inserted = False
        for i, existing_handler in enumerate(subscribers):
            if event_handler.priority < existing_handler.priority:
                subscribers.insert(i, event_handler)
                inserted = True
                break
        
        if not inserted:
            subscribers.append(event_handler)
        
        self._logger.debug(
            f"订阅事件: {event_type}, 优先级: {priority}, 异步: {is_async}"
        )
    
    async def publish(
        self,
        event: DomainEvent,
        priority: int = 5
    ) -> None:
        """发布事件（异步）
        
        Args:
            event: 事件实例
            priority: 事件优先级（0-10，数字越小优先级越高，默认5）
        """
        event_type = event.event_type
        
        # 确保事件日志数据库已初始化
        if self._init_task is None:
            self._init_task = asyncio.create_task(self._init_event_log())
            await self._init_task
        
        # 记录事件到日志（事件溯源）
        await self._log_event(event)
        
        if event_type not in self._subscribers:
            self._logger.debug(f"事件 {event_type} 无订阅者")
            return
        
        # 按优先级处理订阅者
        subscribers = self._subscribers[event_type]
        
        for handler_wrapper in subscribers:
            try:
                if handler_wrapper.is_async:
                    # 异步处理器
                    await handler_wrapper.handler(event)
                else:
                    # 同步处理器，在线程池中执行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler_wrapper.handler, event)
            except Exception as e:
                self._logger.error(
                    f"事件处理失败: {event_type}, 处理器: {handler_wrapper.handler.__name__}, "
                    f"优先级: {handler_wrapper.priority}, 错误: {e}",
                    exc_info=True
                )
    
    def publish_sync(self, event: DomainEvent) -> None:
        """发布事件（同步版本，用于向后兼容）
        
        Args:
            event: 事件实例
        """
        # 创建新的事件循环或使用现有循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建任务
                asyncio.create_task(self.publish(event))
            else:
                # 如果事件循环未运行，运行直到完成
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # 如果没有事件循环，创建新的
            asyncio.run(self.publish(event))
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._subscribers:
            subscribers = self._subscribers[event_type]
            self._subscribers[event_type] = [
                h for h in subscribers if h.handler != handler
            ]
            self._logger.debug(f"取消订阅事件: {event_type}")
    
    def clear(self) -> None:
        """清空所有订阅"""
        self._subscribers.clear()
        self._logger.debug("清空所有事件订阅")
    
    def get_subscriber_count(self, event_type: str) -> int:
        """获取指定事件的订阅者数量
        
        Args:
            event_type: 事件类型
        
        Returns:
            订阅者数量
        """
        return len(self._subscribers.get(event_type, []))
    
    async def get_event_history(
        self,
        event_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取事件历史（事件溯源查询）
        
        Args:
            event_type: 事件类型（可选，过滤）
            aggregate_id: 聚合根ID（可选，过滤）
            limit: 返回数量限制
        
        Returns:
            事件历史列表
        """
        try:
            import json
            async with aiosqlite.connect(self._event_log_path) as conn:
                conn.row_factory = aiosqlite.Row
                
                query = "SELECT * FROM event_log WHERE 1=1"
                params = []
                
                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)
                
                if aggregate_id:
                    query += " AND aggregate_id = ?"
                    params.append(aggregate_id)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                async with conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    
                    result = []
                    for row in rows:
                        event_data = json.loads(row['event_data'])
                        result.append({
                            'id': row['id'],
                            'event_type': row['event_type'],
                            'event_id': row['event_id'],
                            'aggregate_id': row['aggregate_id'],
                            'timestamp': row['timestamp'],
                            'event_data': event_data,
                            'created_at': row['created_at'],
                        })
                    
                    return result
        except Exception as e:
            self._logger.error(f"查询事件历史失败: {e}", exc_info=True)
            return []

