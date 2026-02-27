"""
文件管理业务模块
文件路径：src/business/file/__init__.py
"""

# 异步版本 (新架构)
from .file_manager_async import FileManagerAsync

# 兼容性别名
FileManager = FileManagerAsync

__all__ = ['FileManagerAsync', 'FileManager']
