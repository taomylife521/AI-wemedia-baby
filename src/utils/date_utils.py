"""
日期时间工具模块
文件路径：src/utils/date_utils.py
功能：提供日期时间相关的工具函数
"""

from datetime import datetime, timedelta
from typing import Optional
import re


# 日期时间格式常量
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


def format_datetime(dt: datetime, format_str: str = DATETIME_FORMAT) -> str:
    """格式化日期时间为字符串
    
    Args:
        dt: 日期时间对象
        format_str: 格式字符串，默认为 "%Y-%m-%d %H:%M:%S"
    
    Returns:
        格式化后的日期时间字符串
    """
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = DATETIME_FORMAT) -> datetime:
    """解析日期时间字符串
    
    Args:
        date_str: 日期时间字符串
        format_str: 格式字符串，默认为 "%Y-%m-%d %H:%M:%S"
    
    Returns:
        日期时间对象
    
    Raises:
        ValueError: 日期时间字符串格式不正确
    """
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError as e:
        raise ValueError(f"日期时间格式不正确: {date_str}, 期望格式: {format_str}")


def get_today_start() -> datetime:
    """获取今天的开始时间（00:00:00）
    
    Returns:
        今天的开始时间
    """
    now = datetime.now()
    return datetime(now.year, now.month, now.day, 0, 0, 0)


def get_today_end() -> datetime:
    """获取今天的结束时间（23:59:59）
    
    Returns:
        今天的结束时间
    """
    now = datetime.now()
    return datetime(now.year, now.month, now.day, 23, 59, 59)


def add_days(dt: datetime, days: int) -> datetime:
    """在日期时间基础上增加指定天数
    
    Args:
        dt: 日期时间对象
        days: 要增加的天数（可以为负数）
    
    Returns:
        增加天数后的日期时间对象
    """
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """在日期时间基础上增加指定小时数
    
    Args:
        dt: 日期时间对象
        hours: 要增加的小时数（可以为负数）
    
    Returns:
        增加小时数后的日期时间对象
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """在日期时间基础上增加指定分钟数
    
    Args:
        dt: 日期时间对象
        minutes: 要增加的分钟数（可以为负数）
    
    Returns:
        增加分钟数后的日期时间对象
    """
    return dt + timedelta(minutes=minutes)


def get_current_datetime_str(format_str: str = DATETIME_FORMAT) -> str:
    """获取当前日期时间字符串
    
    Args:
        format_str: 格式字符串，默认为 "%Y-%m-%d %H:%M:%S"
    
    Returns:
        当前日期时间字符串
    """
    return format_datetime(datetime.now(), format_str)


def get_current_date_str() -> str:
    """获取当前日期字符串（YYYY-MM-DD）
    
    Returns:
        当前日期字符串
    """
    return format_datetime(datetime.now(), DATE_FORMAT)


def is_date_expired(date_str: str, format_str: str = DATE_FORMAT) -> bool:
    """检查日期是否已过期
    
    Args:
        date_str: 日期字符串
        format_str: 格式字符串，默认为 "%Y-%m-%d"
    
    Returns:
        如果日期已过期返回True，否则返回False
    """
    try:
        target_date = parse_datetime(date_str, format_str).date()
        today = datetime.now().date()
        return target_date < today
    except ValueError:
        return True  # 格式错误视为已过期


def get_datetime_diff_seconds(dt1: datetime, dt2: datetime) -> int:
    """计算两个日期时间之间的秒数差
    
    Args:
        dt1: 第一个日期时间
        dt2: 第二个日期时间
    
    Returns:
        秒数差（dt1 - dt2）
    """
    delta = dt1 - dt2
    return int(delta.total_seconds())

