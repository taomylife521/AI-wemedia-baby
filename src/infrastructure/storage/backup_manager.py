"""
数据库备份管理器
文件路径：src/core/infrastructure/storage/backup_manager.py
功能：定时备份数据库，每天凌晨2点自动备份
"""

import asyncio
from datetime import datetime, time as dt_time
from pathlib import Path
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import shutil
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)


class BackupManager:
    """数据库备份管理器
    
    使用APScheduler定时备份数据库。
    """
    
    def __init__(
        self,
        backup_dir: str = None
    ):
        """初始化备份管理器
        
        Args:
            backup_dir: 备份目录 (None则使用默认AppData路径)
        """
        if backup_dir is None:
             self.backup_dir = PathManager.get_app_data_dir() / "data" / "backup"
        else:
             self.backup_dir = Path(backup_dir)
             
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> None:
        """启动备份调度器"""
        # 每天凌晨2点执行备份
        self.scheduler.add_job(
            self._backup_job,
            CronTrigger(hour=2, minute=0),
            id='daily_backup',
            name='每日数据库备份'
        )
        
        self.scheduler.start()
        self.logger.info("数据库备份调度器已启动，每天凌晨2点执行备份")
    
    async def _backup_job(self) -> None:
        """备份任务（异步）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"database_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            db_path = PathManager.get_app_data_dir() / "data" / "wemedia.db"
            if db_path.exists():
                await asyncio.to_thread(shutil.copy2, str(db_path), str(backup_path))
                success = True
            else:
                self.logger.error(f"找不到数据库文件: {db_path}")
                success = False
            
            if success:
                self.logger.info(f"定时备份成功: {backup_path}")
                # 清理旧备份（只保留最近30天）
                await self._cleanup_old_backups()
            else:
                self.logger.error("定时备份失败")
        except Exception as e:
            self.logger.error(f"定时备份任务执行失败: {e}", exc_info=True)
    
    async def _cleanup_old_backups(self, days: int = 30) -> None:
        """清理旧备份（异步）
        
        Args:
            days: 保留天数（默认30天）
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for backup_file in self.backup_dir.glob("database_backup_*.db"):
                # 从文件名提取时间戳
                try:
                    timestamp_str = backup_file.stem.replace("database_backup_", "")
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        self.logger.debug(f"删除旧备份: {backup_file}")
                except Exception:
                    # 文件名格式不正确，跳过
                    pass
        except Exception as e:
            self.logger.error(f"清理旧备份失败: {e}", exc_info=True)
    
    async def manual_backup(self) -> str:
        """手动备份（异步）
        
        Returns:
            备份文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"database_backup_manual_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        db_path = PathManager.get_app_data_dir() / "data" / "wemedia.db"
        if not db_path.exists():
            raise Exception(f"找不到数据库文件: {db_path}")
        await asyncio.to_thread(shutil.copy2, str(db_path), str(backup_path))
        success = True
        
        if success:
            self.logger.info(f"手动备份成功: {backup_path}")
            return str(backup_path)
        else:
            raise Exception("手动备份失败")
    
    def stop(self) -> None:
        """停止备份调度器"""
        self.scheduler.shutdown()
        self.logger.info("数据库备份调度器已停止")

