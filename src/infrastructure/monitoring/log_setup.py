"""
日志初始化模块
文件路径：src/infrastructure/monitoring/log_setup.py
功能：初始化应用程序日志配置
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

def init_log_manager(
    log_dir: str = "logs", 
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    app_name: str = "qasync_app"
) -> logging.Logger:
    """初始化日志管理器
    
    Args:
        log_dir: 日志目录
        console_level: 控制台日志级别
        file_level: 文件日志级别
        app_name: 应用名称
        
    Returns:
        Root Logger
    """
    # 确保日志目录存在
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根记录器捕获所有，由Handler过滤
    
    # 清除现有Handler（避免重复）
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # 定义日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 1. 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 文件 Handler (按大小轮转) - app.log
    file_path = os.path.join(log_dir, f"{app_name}.log")
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 3. 错误日志 Handler (按天轮转) - error.log
    error_path = os.path.join(log_dir, "error.log")
    error_handler = TimedRotatingFileHandler(
        error_path,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 抑制部分嘈杂库的日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("tortoise").setLevel(logging.WARNING)
    
    # 记录启动信息
    logging.info(f"日志系统初始化完成: console={logging.getLevelName(console_level)}, file={logging.getLevelName(file_level)}")
    
    return root_logger
