"""
发布管道过滤器基类
文件路径：src/core/common/pipeline/base_filter.py
功能：定义过滤器接口和基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Protocol, Any
from dataclasses import dataclass


@dataclass
class PublishContext:
    """发布上下文
    
    在管道中传递的上下文数据。
    """
    user_id: int
    account_name: str
    platform: str
    file_path: str
    file_type: str = "video" # video or image
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    account: Optional[Any] = None  # Account实体
    headless: bool = True  # 是否无头模式
    speed_rate: float = 1.0  # 发布速度倍率 (1.0=正常, >1.0=慢速)
    pause_event: Any = None  # 暂停控制事件 (asyncio.Event)
    error_message: Optional[str] = None
    cover_type: Optional[str] = None  # 封面类型: "first_frame", "custom", None


@dataclass
class PublishRequest:
    """发布请求"""
    user_id: int
    account_name: str
    platform: str
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    headless: bool = True  # 是否无头模式
    speed_rate: float = 1.0  # 发布速度倍率
    pause_event: Any = None  # 暂停控制事件 (asyncio.Event)
    cover_type: Optional[str] = None  # 封面类型: "first_frame", "custom", None


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    task_id: Optional[int] = None
    publish_url: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class PublishResponse:
    """发布响应"""
    results: list[PublishResult]
    total_count: int
    success_count: int
    failed_count: int


class IPublishFilter(Protocol):
    """发布过滤器接口"""
    
    async def process(self, context: PublishContext) -> bool:
        """处理上下文
        
        Args:
            context: 发布上下文
        
        Returns:
            如果处理成功返回True，否则返回False
        """
        ...
    
    def get_error(self) -> Optional[str]:
        """获取错误信息
        
        Returns:
            错误信息，如果没有错误返回None
        """
        ...


class BaseFilter(ABC):
    """发布过滤器基类"""
    
    def __init__(self):
        """初始化过滤器"""
        self._error: Optional[str] = None
    
    @abstractmethod
    async def process(self, context: PublishContext) -> bool:
        """处理上下文（异步）
        
        Args:
            context: 发布上下文
        
        Returns:
            如果处理成功返回True，否则返回False
        """
        pass
    
    def get_error(self) -> Optional[str]:
        """获取错误信息
        
        Returns:
            错误信息，如果没有错误返回None
        """
        return self._error
    
    def set_error(self, error: str) -> None:
        """设置错误信息
        
        Args:
            error: 错误信息
        """
        self._error = error

