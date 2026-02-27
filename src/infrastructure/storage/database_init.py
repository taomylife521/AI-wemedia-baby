"""
数据库初始化脚本
文件路径：src/core/database_init.py
功能：创建所有数据表和索引
"""

import sqlite3
import os
from typing import Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


from src.infrastructure.common.path_manager import PathManager

def init_database(db_path: str = None) -> None:
    """初始化数据库
    
    Args:
        db_path: 数据库文件路径 (如果为None，则使用PathManager默认路径)

    
    Raises:
        sqlite3.Error: 数据库操作失败
    """
    if db_path is None:
        db_path = str(PathManager.get_db_path())
        
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                trial_count INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT
            )
        """)
        
        # 创建订阅表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_type TEXT NOT NULL,
                price REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                auto_renew INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                payment_method TEXT,
                order_id TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建发布记录表（account_name 改为 platform_username）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publish_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform_username TEXT NOT NULL,
                platform TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                title TEXT,
                description TEXT,
                tags TEXT,
                cover_path TEXT,
                poi_info TEXT,
                micro_app_info TEXT,
                goods_info TEXT,
                anchor_info TEXT,
                privacy_settings TEXT,
                scheduled_publish_time TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                publish_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建多账号表（已删除 account_name 字段，仅保留 platform_username）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                cookie_path TEXT NOT NULL,
                platform_username TEXT NOT NULL,
                login_status TEXT DEFAULT 'offline',
                last_login_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建账号组表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 如果表已存在但没有 platform_username 字段，则添加该字段
        try:
            cursor.execute("ALTER TABLE platform_accounts ADD COLUMN platform_username TEXT")
            logger.info("已添加 platform_username 字段到 platform_accounts 表")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
        
        # 为 platform_accounts 添加 group_id 外键字段
        try:
            cursor.execute("ALTER TABLE platform_accounts ADD COLUMN group_id INTEGER REFERENCES account_groups(id)")
            logger.info("已添加 group_id 字段到 platform_accounts 表")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
        # 检查并添加 scheduled_publish_time 字段到 publish_records 表
        try:
            cursor.execute("ALTER TABLE publish_records ADD COLUMN scheduled_publish_time TEXT")
            logger.info("已添加 scheduled_publish_time 字段到 publish_records 表")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
        # 添加抖音专属字段
        new_columns = [
            "cover_path", "poi_info", "micro_app_info", 
            "goods_info", "anchor_info", "privacy_settings"
        ]
        for col in new_columns:
            try:
                cursor.execute(f"ALTER TABLE publish_records ADD COLUMN {col} TEXT")
                logger.info(f"已添加 {col} 字段到 publish_records 表")
            except sqlite3.OperationalError:
                pass
        
        # 创建登录日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time TEXT DEFAULT CURRENT_TIMESTAMP,
                device_info TEXT,
                ip_address TEXT,
                login_status TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建批量任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_description TEXT,
                platform_username TEXT NOT NULL,
                platform TEXT NOT NULL,
                task_type TEXT NOT NULL,
                script_config TEXT NOT NULL,
                video_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                completed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                start_time TEXT,
                end_time TEXT,
                priority INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 3,
                delay_seconds INTEGER DEFAULT 5,
                max_concurrent INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建批量任务执行记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                execution_index INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                title TEXT,
                description TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                publish_url TEXT,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (task_id) REFERENCES batch_tasks(id) ON DELETE CASCADE
            )
        """)
        
        # 创建批量任务检查点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_task_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL UNIQUE,
                completed_indices TEXT NOT NULL,
                current_index INTEGER DEFAULT 0,
                checkpoint_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (task_id) REFERENCES batch_tasks(id) ON DELETE CASCADE
            )
        """)
        
        # 创建媒体文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                duration REAL,
                resolution TEXT,
                width INTEGER,
                height INTEGER,
                has_script INTEGER DEFAULT 0,
                script_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建索引
        create_indexes(cursor)
        
        conn.commit()
        logger.info("数据库初始化成功")
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        conn.close()


def create_indexes(cursor: sqlite3.Cursor) -> None:
    """创建索引
    
    Args:
        cursor: 数据库游标
    """
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)",
        "CREATE INDEX IF NOT EXISTS idx_subscriptions_order_id ON subscriptions(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_publish_records_user_id ON publish_records(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_publish_records_platform_username ON publish_records(platform_username)",
        "CREATE INDEX IF NOT EXISTS idx_publish_records_platform ON publish_records(platform)",
        "CREATE INDEX IF NOT EXISTS idx_publish_records_status ON publish_records(status)",
        "CREATE INDEX IF NOT EXISTS idx_publish_records_created_at ON publish_records(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_platform_accounts_user_id ON platform_accounts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_platform_accounts_platform ON platform_accounts(platform)",
        "CREATE INDEX IF NOT EXISTS idx_platform_accounts_login_status ON platform_accounts(login_status)",
        "CREATE INDEX IF NOT EXISTS idx_platform_accounts_group_id ON platform_accounts(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_groups_user_id ON account_groups(user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_account_groups_name ON account_groups(user_id, group_name)",
        "CREATE INDEX IF NOT EXISTS idx_login_logs_user_id ON login_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_login_logs_login_time ON login_logs(login_time)",
        "CREATE INDEX IF NOT EXISTS idx_batch_tasks_user_id ON batch_tasks(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_batch_tasks_status ON batch_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_batch_tasks_created_at ON batch_tasks(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_batch_task_executions_task_id ON batch_task_executions(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_batch_task_executions_status ON batch_task_executions(status)",
        "CREATE INDEX IF NOT EXISTS idx_batch_task_checkpoints_task_id ON batch_task_checkpoints(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_media_files_user_id ON media_files(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_media_files_file_type ON media_files(file_type)",
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成！")


