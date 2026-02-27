"""
异步数据库存储模块
文件路径：src/core/infrastructure/storage/database.py
功能：提供异步数据库操作封装，使用aiosqlite替代sqlite3
"""

import aiosqlite
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
import time

from src.infrastructure.common.security.encryption import hash_password, verify_password
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)

# 禁用aiosqlite的DEBUG日志
logging.getLogger('aiosqlite').setLevel(logging.WARNING)

# 数据库操作重试配置
DB_RETRY_MAX_ATTEMPTS = 3
DB_RETRY_DELAY = 0.1  # 初始延迟（秒）
DB_TIMEOUT = 5.0  # 连接超时（秒）


class AsyncDataStorage:
    """异步数据存储服务 - 负责数据库操作（异步版本）
    
    使用aiosqlite进行所有数据库操作，完全异步化。
    优化SQLite性能设置（WAL模式、缓存等）。
    """
    
    def __init__(self, db_path: str = None):
        """初始化异步数据存储服务
        
        Args:
            db_path: 数据库文件路径 (如果为None，则使用PathManager默认路径)
        """
        if db_path is None:
            self.db_path = str(PathManager.get_db_path())
        else:
            self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 确保数据库目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库性能设置
        asyncio.create_task(self._init_db_settings())
    
    async def _init_db_settings(self) -> None:
        """初始化数据库性能设置（异步）"""
        try:
            # 先执行架构迁移检查
            await self._migrate_schema()
            
            # 检查 WAL 文件大小，如果过大则执行 Checkpoint (Stage 1 Optimization)
            try:
                import os
                wal_path = f"{self.db_path}-wal"
                if os.path.exists(wal_path):
                    wal_size = os.path.getsize(wal_path)
                    # 如果 WAL 文件超过 10MB，执行 TRUNCATE
                    if wal_size > 10 * 1024 * 1024:
                        self.logger.info(f"WAL 文件过大 ({wal_size / 1024 / 1024:.2f} MB), 执行 Checkpoint...")
                        async with aiosqlite.connect(self.db_path) as conn:
                            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                            await conn.commit()
                        self.logger.info("WAL Checkpoint (TRUNCATE) 完成")
            except Exception as e:
                self.logger.warning(f"WAL Checkpoint 检查失败: {e}")

            async with aiosqlite.connect(self.db_path) as conn:
                # 启用WAL模式（Write-Ahead Logging），提升并发性能
                await conn.execute("PRAGMA journal_mode=WAL")
                # 设置同步模式为NORMAL（平衡性能和安全性）
                await conn.execute("PRAGMA synchronous=NORMAL")
                # 增加缓存大小到10MB
                await conn.execute("PRAGMA cache_size=-10000")
                # 临时数据存储在内存中
                await conn.execute("PRAGMA temp_store=MEMORY")
                # 优化查询计划器
                await conn.execute("PRAGMA optimize")
                await conn.commit()
        except Exception as e:
            self.logger.warning(f"初始化数据库设置失败: {e}")

    async def _migrate_schema(self) -> None:
        """检查并迁移数据库架构"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 检查 platform_accounts 表是否有 profile_folder_name 列
                cursor = await conn.execute("PRAGMA table_info(platform_accounts)")
                columns = await cursor.fetchall()
                # columns row format: (cid, name, type, notnull, dflt_value, pk)
                column_names = [col[1] for col in columns]
                
                if columns and 'profile_folder_name' not in column_names:
                    self.logger.info("正在迁移数据库: 添加 profile_folder_name 列到 platform_accounts...")
                    try:
                        await conn.execute("ALTER TABLE platform_accounts ADD COLUMN profile_folder_name TEXT")
                        await conn.commit()
                        self.logger.info("数据库迁移完成: 已添加 profile_folder_name")
                    except Exception as alter_e:
                        self.logger.error(f"添加列失败 (可能已存在): {alter_e}")
                        
        except Exception as e:
            self.logger.error(f"数据库迁移检查失败: {e}")
    
    async def _optimize_connection(self, conn: aiosqlite.Connection) -> None:
        """优化连接设置
        
        Args:
            conn: 数据库连接
        """
        try:
            # 这些设置只需要设置一次，但为了确保每个连接都有，我们每次都设置
            # SQLite会自动忽略已经设置的值
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
        except Exception:
            # 忽略设置失败，继续执行
            pass
    
    async def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
        retry_count: int = DB_RETRY_MAX_ATTEMPTS
    ) -> Optional[Any]:
        """执行查询（通用方法，优化连接，支持重试）
        
        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否只获取一行
            fetch_all: 是否获取所有行
            retry_count: 重试次数（内部使用）
        
        Returns:
            查询结果
        
        Raises:
            aiosqlite.OperationalError: 数据库操作错误（重试后仍失败）
        """
        last_error = None
        delay = DB_RETRY_DELAY
        
        for attempt in range(retry_count):
            try:
                # 设置连接超时
                async with aiosqlite.connect(
                    self.db_path,
                    timeout=DB_TIMEOUT
                ) as conn:
                    conn.row_factory = aiosqlite.Row
                    await self._optimize_connection(conn)
                    cursor = await conn.execute(query, params)
                    
                    if fetch_one:
                        row = await cursor.fetchone()
                        return dict(row) if row else None
                    elif fetch_all:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
                    else:
                        await conn.commit()
                        return cursor.lastrowid
            except aiosqlite.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                
                # 如果是数据库锁定错误，进行重试
                if "locked" in error_msg or "database is locked" in error_msg:
                    if attempt < retry_count - 1:
                        self.logger.debug(
                            f"数据库锁定，重试 {attempt + 1}/{retry_count} "
                            f"(延迟 {delay:.2f}秒)"
                        )
                        await asyncio.sleep(delay)
                        delay *= 2  # 指数退避
                        continue
                    else:
                        self.logger.error(
                            f"数据库操作失败（已重试{retry_count}次）: {e}"
                        )
                        raise
                else:
                    # 其他操作错误，直接抛出
                    raise
            except Exception as e:
                # 非操作错误，直接抛出
                self.logger.error(f"数据库查询失败: {e}", exc_info=True)
                raise
        
        # 如果所有重试都失败
        if last_error:
            raise last_error
    
    async def execute_transaction(
        self,
        queries: List[tuple]
    ) -> None:
        """执行事务（多个查询，优化连接）
        
        Args:
            queries: 查询列表，每个元素为(query, params)元组
        
        Raises:
            Exception: 如果任何查询失败，回滚事务
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await self._optimize_connection(conn)
            try:
                await conn.execute("BEGIN")
                for query, params in queries:
                    await conn.execute(query, params)
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                self.logger.error(f"事务执行失败: {e}", exc_info=True)
                raise
    
    async def backup_database(self, backup_path: str) -> bool:
        """备份数据库（在线热备份）
        
        使用 SQLite 的 VACUUM INTO 命令进行安全的热备份。
        该命令在 SQLite 3.27.0+ 可用（Python 3.8+ 自带版本通常满足）。
        
        Args:
            backup_path: 备份文件目标路径
            
        Returns:
            是否备份成功
        """
        try:
            # 确保目标目录存在
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as conn:
                # VACUUM INTO 会创建数据库的一份事务一致性副本
                await conn.execute(f"VACUUM INTO ?", (backup_path,))
                
            self.logger.info(f"数据库备份成功: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"数据库备份失败: {e}", exc_info=True)
            return False
    
    # ========== 用户相关操作 ==========
    
    async def create_user(
        self,
        username: str,
        password: str,
        email: str
    ) -> int:
        """创建用户（异步）
        
        Args:
            username: 用户名
            password: 明文密码（将自动哈希）
            email: 邮箱
        
        Returns:
            新创建的用户ID
        
        Raises:
            ValueError: 用户名已存在
        """
        password_hash = hash_password(password)
        
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await self._optimize_connection(conn)
                cursor = await conn.execute("""
                    INSERT INTO users (username, password_hash, email)
                    VALUES (?, ?, ?)
                """, (username, password_hash, email))
                user_id = cursor.lastrowid
                await conn.commit()
                self.logger.info(f"创建用户成功: {username}, ID: {user_id}")
                return user_id
        except aiosqlite.IntegrityError:
            raise ValueError(f"用户名已存在: {username}")
        except Exception as e:
            self.logger.error(f"创建用户失败: {e}", exc_info=True)
            raise
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息（异步）
        
        Args:
            username: 用户名
        
        Returns:
            用户信息字典，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            fetch_one=True
        )
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户ID获取用户信息（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户信息字典，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
    
    async def verify_user_password(self, username: str, password: str) -> bool:
        """验证用户密码（异步）
        
        Args:
            username: 用户名
            password: 明文密码
        
        Returns:
            如果密码正确返回True，否则返回False
        """
        user = await self.get_user_by_username(username)
        if not user:
            return False
        
        return verify_password(password, user['password_hash'])
    
    async def update_user_password(self, username: str, new_password: str) -> bool:
        """更新用户密码（异步）
        
        Args:
            username: 用户名
            new_password: 新明文密码
            
        Returns:
            更新是否成功
        """
        password_hash = hash_password(new_password)
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await self._optimize_connection(conn)
                cursor = await conn.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (password_hash, username)
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新用户密码失败: {e}", exc_info=True)
            return False
    
    async def update_user_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            更新是否成功
        """
        from datetime import datetime
        
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await self._optimize_connection(conn)
                await conn.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                await conn.commit()
                self.logger.debug(f"更新用户最后登录时间成功: 用户ID={user_id}")
                return True
        except Exception as e:
            self.logger.error(f"更新用户最后登录时间失败: {e}", exc_info=True)
            return False
    
    async def update_user_trial_count(self, user_id: int, trial_count: int) -> bool:
        """更新用户试用次数（异步）
        
        Args:
            user_id: 用户ID
            trial_count: 新的试用次数
        
        Returns:
            更新是否成功
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await self._optimize_connection(conn)
                await conn.execute(
                    "UPDATE users SET trial_count = ? WHERE id = ?",
                    (trial_count, user_id)
                )
                await conn.commit()
                self.logger.debug(f"更新用户试用次数成功: 用户ID={user_id}, 次数={trial_count}")
                return True
        except Exception as e:
            self.logger.error(f"更新用户试用次数失败: {e}", exc_info=True)
            return False
    
    # ========== 平台账号相关操作 ==========
    
    async def create_platform_account(
        self,
        user_id: int,
        platform: str,
        platform_username: Optional[str] = None,
        cookie_path: str = "",
        profile_folder_name: Optional[str] = None
    ) -> int:
        """创建平台账号(异步)
        
        Args:
            user_id: 用户ID
            platform: 平台名称
            platform_username: 平台账号用户名（昵称）(可选)
            cookie_path: Cookie文件路径(默认为空字符串)
            profile_folder_name: 账号数据文件夹名称(UUID或临时名)，消除重命名需求
        
        Returns:
            新创建的账号ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                INSERT INTO platform_accounts 
                (user_id, platform, platform_username, cookie_path, profile_folder_name)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, platform, platform_username, cookie_path, profile_folder_name))
            account_id = cursor.lastrowid
            await conn.commit()
            self.logger.info(
                f"创建平台账号成功: {platform_username or '未指定'}, 平台: {platform}, "
                f"ID: {account_id}, ProfileFolder: {profile_folder_name}"
            )
            return account_id
    
    async def get_platform_accounts(
        self,
        user_id: int,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取平台账号列表（异步）
        
        Args:
            user_id: 用户ID
            platform: 平台名称（可选，如果指定则只返回该平台的账号）
        
        Returns:
            账号列表
        """
        if platform:
            return await self.execute_query(
                """
                SELECT * FROM platform_accounts 
                WHERE user_id = ? AND platform = ?
                ORDER BY created_at ASC
                """,
                (user_id, platform),
                fetch_all=True
            )
        else:
            return await self.execute_query(
                """
                SELECT * FROM platform_accounts 
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (user_id,),
                fetch_all=True
            )
    
    async def get_platform_account_by_id(
        self,
        account_id: int
    ) -> Optional[Dict[str, Any]]:
        """根据ID获取平台账号（异步）
        
        Args:
            account_id: 账号ID
        
        Returns:
            账号信息字典，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM platform_accounts WHERE id = ?",
            (account_id,),
            fetch_one=True
        )
    
    async def update_platform_username(
        self,
        account_id: int,
        platform_username: str
    ) -> None:
        """更新平台账号用户名（异步）
        
        Args:
            account_id: 账号ID
            platform_username: 平台账号用户名
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("""
                UPDATE platform_accounts 
                SET platform_username = ? 
                WHERE id = ?
            """, (platform_username, account_id))
            await conn.commit()
            self.logger.info(
                f"更新平台用户名成功: 账号ID={account_id}, 用户名={platform_username}"
            )
    
    async def update_account_status(
        self,
        account_id: int,
        login_status: str,
        last_login_at: Optional[str] = None
    ) -> None:
        """更新账号状态（异步）
        
        Args:
            account_id: 账号ID
            login_status: 登录状态（online/offline）
            last_login_at: 最后登录时间（可选）
        """
        from datetime import datetime
        
        if last_login_at is None:
            last_login_at = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("""
                UPDATE platform_accounts 
                SET login_status = ?, last_login_at = ?
                WHERE id = ?
            """, (login_status, last_login_at, account_id))
            await conn.commit()
    
    async def delete_platform_account(self, account_id: int) -> None:
        """删除平台账号（异步）
        
        Args:
            account_id: 账号ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("""
                DELETE FROM platform_accounts WHERE id = ?
            """, (account_id,))
            await conn.commit()
            self.logger.info(f"删除平台账号: ID {account_id}")
    
    # ========== 发布记录相关操作 ==========
    
    async def create_publish_record(
        self,
        user_id: int,
        platform_username: str,
        platform: str,
        file_path: str,
        file_type: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        cover_path: Optional[str] = None,
        poi_info: Optional[str] = None,
        micro_app_info: Optional[str] = None,
        goods_info: Optional[str] = None,
        anchor_info: Optional[str] = None,
        privacy_settings: Optional[str] = None,
        scheduled_publish_time: Optional[str] = None
    ) -> int:
        """创建发布记录（异步）
        
        Args:
            user_id: 用户ID
            platform_username: 平台昵称（如"我真的太难了"）
            platform: 平台名称
            file_path: 文件路径
            file_type: 文件类型（video/image）
            title: 标题（可选）
            description: 描述（可选）
            tags: 标签（可选）
            cover_path: 封面路径（可选）
            poi_info: 位置信息（可选）
            micro_app_info: 小程序信息（可选）
            goods_info: 商品信息（可选）
            anchor_info: 锚点信息（可选）
            privacy_settings: 隐私设置（可选）
            scheduled_publish_time: 定时发布时间（可选，ISO格式）
        
        Returns:
            新创建的记录ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                INSERT INTO publish_records 
                (user_id, platform_username, platform, file_path, file_type, 
                 title, description, tags, cover_path, poi_info, 
                 micro_app_info, goods_info, anchor_info, privacy_settings, 
                 scheduled_publish_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, platform_username, platform, file_path, file_type, 
                  title, description, tags, cover_path, poi_info, 
                  micro_app_info, goods_info, anchor_info, privacy_settings, 
                  scheduled_publish_time))
            record_id = cursor.lastrowid
            await conn.commit()
            return record_id
    
    async def update_publish_record(
        self,
        record_id: int,
        status: str,
        publish_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """更新发布记录（异步）
        
        Args:
            record_id: 记录ID
            status: 状态（pending/running/success/failed）
            publish_url: 发布URL（可选）
            error_message: 错误信息（可选）
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("""
                UPDATE publish_records 
                SET status = ?, publish_url = ?, error_message = ?
                WHERE id = ?
            """, (status, publish_url, error_message, record_id))
            await conn.commit()
    
    async def update_publish_record_content(
        self,
        record_id: int,
        platform_username: str,
        platform: str,
        file_path: str,
        file_type: str,
        title: str,
        description: str,
        tags: str,
        cover_path: Optional[str] = None,
        poi_info: Optional[str] = None,
        micro_app_info: Optional[str] = None,
        goods_info: Optional[str] = None,
        anchor_info: Optional[str] = None,
        privacy_settings: Optional[str] = None,
        scheduled_publish_time: Optional[str] = None
    ) -> bool:
        """更新发布记录内容（用于编辑）"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE publish_records 
                    SET platform_username=?, platform=?, file_path=?, file_type=?, 
                        title=?, description=?, tags=?, cover_path=?, poi_info=?, 
                        micro_app_info=?, goods_info=?, anchor_info=?, privacy_settings=?, 
                        scheduled_publish_time=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (platform_username, platform, file_path, file_type, 
                      title, description, tags, cover_path, poi_info, 
                      micro_app_info, goods_info, anchor_info, privacy_settings, 
                      scheduled_publish_time, record_id))
                await conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"更新发布记录内容失败: {e}", exc_info=True)
            return False
    
    async def delete_publish_records(self, record_ids: List[int]) -> bool:
        """批量删除发布记录（异步）
        
        Args:
            record_ids: 记录ID列表
            
        Returns:
            删除是否成功
        """
        if not record_ids:
            return True
            
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 生成占位符
                placeholders = ','.join('?' * len(record_ids))
                await conn.execute(
                    f"DELETE FROM publish_records WHERE id IN ({placeholders})",
                    record_ids
                )
                await conn.commit()
                self.logger.info(f"批量删除发布记录成功: {len(record_ids)}条")
                return True
        except Exception as e:
            self.logger.error(f"批量删除发布记录失败: {e}", exc_info=True)
            return False
    
    async def get_publish_records(
        self,
        user_id: int,
        platform_username: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取发布记录列表（异步）
        
        Args:
            user_id: 用户ID
            platform_username: 平台账号昵称（可选）
            platform: 平台名称（可选）
            status: 状态（可选）
            limit: 返回记录数限制
        
        Returns:
            发布记录列表
        """
        # 构建查询条件
        conditions = ["user_id = ?"]
        params = [user_id]
        
        if platform_username:
            conditions.append("platform_username = ?")
            params.append(platform_username)
        
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        
        return await self.execute_query(
            f"""
            SELECT * FROM publish_records
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            tuple(params) + (limit,),
            fetch_all=True
        )
    
    # ========== 订阅相关操作 ==========
    
    async def create_subscription(
        self,
        user_id: int,
        plan_type: str,
        price: float,
        start_date: str,
        end_date: str,
        order_id: Optional[str] = None
    ) -> int:
        """创建订阅（异步）
        
        Args:
            user_id: 用户ID
            plan_type: 套餐类型
            price: 价格
            start_date: 开始日期（ISO格式字符串）
            end_date: 结束日期（ISO格式字符串）
            order_id: 订单ID（可选）
        
        Returns:
            新创建的订阅ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                INSERT INTO subscriptions 
                (user_id, plan_type, price, start_date, end_date, order_id, status)
                VALUES (?, ?, ?, ?, ?, ?, 'active')
            """, (user_id, plan_type, price, start_date, end_date, order_id))
            subscription_id = cursor.lastrowid
            await conn.commit()
            return subscription_id
    
    async def get_user_subscription(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取用户订阅（异步）
        
        Args:
            user_id: 用户ID
        
        Returns:
            订阅信息字典，如果不存在返回None
        """
        return await self.execute_query(
            """
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
            fetch_one=True
        )
    
    # ========== 媒体文件相关操作 ==========
    
    async def get_media_files(
        self,
        user_id: int,
        file_type: Optional[str] = None,
        search_keyword: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取媒体文件列表（异步）
        
        Args:
            user_id: 用户ID
            file_type: 文件类型过滤（video/image，可选）
            search_keyword: 搜索关键词（在文件名中搜索，可选）
        
        Returns:
            媒体文件列表
        """
        conditions = ["user_id = ?"]
        params = [user_id]
        
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        
        if search_keyword:
            conditions.append("file_name LIKE ?")
            params.append(f"%{search_keyword}%")
        
        where_clause = " AND ".join(conditions)
        
        return await self.execute_query(
            f"""
            SELECT * FROM media_files
            WHERE {where_clause}
            ORDER BY created_at DESC
            """,
            tuple(params),
            fetch_all=True
        )
    
    async def get_media_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """根据文件路径获取媒体文件记录（异步）
        
        Args:
            file_path: 文件路径
        
        Returns:
            媒体文件记录，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM media_files WHERE file_path = ?",
            (file_path,),
            fetch_one=True
        )
    
    async def get_media_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """根据文件ID获取媒体文件记录（异步）
        
        Args:
            file_id: 文件ID
        
        Returns:
            媒体文件记录，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,),
            fetch_one=True
        )
    
    async def add_media_file(
        self,
        user_id: int,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        duration: Optional[float] = None,
        resolution: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        has_script: int = 0,
        script_path: Optional[str] = None
    ) -> int:
        """添加媒体文件记录（异步）
        
        Args:
            user_id: 用户ID
            file_path: 文件路径
            file_name: 文件名
            file_type: 文件类型（video/image）
            file_size: 文件大小（字节）
            duration: 时长（秒，可选）
            resolution: 分辨率（可选）
            width: 宽度（可选）
            height: 高度（可选）
            has_script: 是否有脚本（0/1，可选）
            script_path: 脚本路径（可选）
        
        Returns:
            新创建的文件记录ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                INSERT INTO media_files 
                (user_id, file_path, file_name, file_type, file_size, 
                 duration, resolution, width, height, has_script, script_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, file_path, file_name, file_type, file_size,
                  duration, resolution, width, height, has_script, script_path))
            file_id = cursor.lastrowid
            await conn.commit()
            self.logger.info(f"添加媒体文件记录成功: {file_name}, ID: {file_id}")
            return file_id
    
    async def delete_media_file(self, file_id: int) -> bool:
        """删除媒体文件记录（异步）
        
        Args:
            file_id: 文件记录ID
        
        Returns:
            删除成功返回True，否则返回False
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await conn.execute("DELETE FROM media_files WHERE id = ?", (file_id,))
                await conn.commit()
                self.logger.info(f"删除媒体文件记录成功: ID {file_id}")
                return True
        except Exception as e:
            self.logger.error(f"删除媒体文件记录失败: {e}", exc_info=True)
            return False

    # ========== 批量任务相关操作 ==========
    
    async def create_batch_task(
        self,
        user_id: int,
        task_name: str,
        platform_username: str,
        platform: str,
        task_type: str,
        script_config: str,
        video_count: int,
        task_description: Optional[str] = None,
        priority: int = 0,
        retry_count: int = 3,
        delay_seconds: int = 5,
        max_concurrent: int = 1
    ) -> int:
        """创建批量任务（异步）
        
        Args:
            user_id: 用户ID
            task_name: 任务名称
            platform_username: 平台账号用户名
            platform: 平台名称
            task_type: 任务类型
            script_config: 脚本配置（JSON字符串）
            video_count: 视频数量
            task_description: 任务描述（可选）
            priority: 优先级（默认0）
            retry_count: 重试次数（默认3）
            delay_seconds: 延迟秒数（默认5）
            max_concurrent: 最大并发数（默认1）
        
        Returns:
            新创建的任务ID
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await self._optimize_connection(conn)
            cursor = await conn.execute("""
                INSERT INTO batch_tasks 
                (user_id, task_name, task_description, platform_username, platform, 
                 task_type, script_config, video_count, status, priority, 
                 retry_count, delay_seconds, max_concurrent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """, (user_id, task_name, task_description, platform_username, platform,
                  task_type, script_config, video_count, priority,
                  retry_count, delay_seconds, max_concurrent))
            task_id = cursor.lastrowid
            await conn.commit()
            self.logger.info(
                f"创建批量任务成功: {task_name}, 平台: {platform}, "
                f"视频数量: {video_count}, ID: {task_id}"
            )
            return task_id
    
    async def get_batch_tasks(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取批量任务列表（异步）
        
        Args:
            user_id: 用户ID
            status: 任务状态（可选，用于筛选）
            limit: 返回数量限制
        
        Returns:
            任务列表
        """
        if status:
            return await self.execute_query(
                """
                SELECT * FROM batch_tasks 
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, status, limit),
                fetch_all=True
            )
        else:
            return await self.execute_query(
                """
                SELECT * FROM batch_tasks 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
                fetch_all=True
            )
    
    async def get_batch_task_by_id(
        self,
        task_id: int
    ) -> Optional[Dict[str, Any]]:
        """根据ID获取批量任务（异步）
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务信息字典，如果不存在返回None
        """
        return await self.execute_query(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (task_id,),
            fetch_one=True
        )
    
    async def update_batch_task_status(
        self,
        task_id: int,
        status: str,
        completed_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> bool:
        """更新批量任务状态（异步）
        
        Args:
            task_id: 任务ID
            status: 任务状态（pending/running/completed/failed/cancelled）
            completed_count: 已完成数量（可选）
            failed_count: 失败数量（可选）
            start_time: 开始时间（可选，ISO格式）
            end_time: 结束时间（可选，ISO格式）
        
        Returns:
            更新成功返回True，否则返回False
        """
        try:
            from datetime import datetime
            
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await self._optimize_connection(conn)
                
                # 构建更新语句
                update_fields = ["status = ?", "updated_at = ?"]
                params = [status, datetime.now().isoformat()]
                
                if completed_count is not None:
                    update_fields.append("completed_count = ?")
                    params.append(completed_count)
                
                if failed_count is not None:
                    update_fields.append("failed_count = ?")
                    params.append(failed_count)
                
                if start_time is not None:
                    update_fields.append("start_time = ?")
                    params.append(start_time)
                
                if end_time is not None:
                    update_fields.append("end_time = ?")
                    params.append(end_time)
                
                params.append(task_id)
                
                await conn.execute(
                    f"""
                    UPDATE batch_tasks 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                    """,
                    tuple(params)
                )
                await conn.commit()
                self.logger.info(f"更新批量任务状态成功: ID={task_id}, 状态={status}")
                return True
        except Exception as e:
            self.logger.error(f"更新批量任务状态失败: {e}", exc_info=True)
            return False

