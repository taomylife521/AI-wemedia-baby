"""
发布列表页面
文件路径：src/ui/pages/publish/publish_list_page.py
功能：显示待发布任务列表（复用发布记录页面布局）
"""

from typing import Optional
import logging
from PySide6.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QLabel

logger = logging.getLogger(__name__)
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QFont
import asyncio
from qasync import asyncSlot

from .publish_records_page import PublishRecordsPage
from src.ui.components.log_display_widget import LogDisplayWidget
from qfluentwidgets import InfoBar, MessageBox


class PublishListPage(PublishRecordsPage):
    """发布列表页面 - 复用发布记录页面的设计"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化"""
        # 调用父类构造函数，设置标题为 "发布列表"，并指定只显示待发布和失败的任务
        super().__init__(
            parent, 
            title="发布列表", 
            target_statuses=["pending", "failed"]
        )
        
        # 默认显示全部记录，避免发布失败后任务消失的错觉
        if hasattr(self, 'status_filter'):
            self.status_filter.setCurrentText("全部")
            
        self.current_task = None
        self.publish_pause_event = asyncio.Event()
        self.publish_pause_event.set() # 默认运行状态
        
        self.log_widget = None
        self._setup_log_window()
        
    def _setup_log_window(self):
        """配置日志窗口"""
        self.log_widget = LogDisplayWidget("发布日志", self)
        
        # 添加到主内容布局底部
        self.content_layout.addWidget(self.log_widget)
        
        # 启动日志监听
        target_loggers = [
            "src.services.publish",
            "src.infrastructure.plugins.builtin_plugins.douyin_plugin",
            "src.infrastructure.browser.browser_manager",
            "src.infrastructure.browser.browser_factory"
        ]
        self.log_widget.start_logging(target_loggers)
        
        # 3. 自动发布监听
        if hasattr(self, 'auto_publish_check'):
            self.auto_publish_check.stateChanged.connect(self._check_auto_start)
            
    def closeEvent(self, event):
        """关闭时移除 Handler"""
        if self.log_widget:
            self.log_widget.stop_logging()
        super().closeEvent(event)

    @asyncSlot()
    async def _on_start_publish(self):
        """开始发布任务（队列循环处理机制，集成前置状态校验）"""
        from src.infrastructure.common.di.service_locator import ServiceLocator
        from src.services.publish.publish_service import PublishService
        from src.domain.repositories.publish_record_repository_async import PublishRecordRepositoryAsync
        from src.domain.repositories.account_repository_async import AccountRepositoryAsync
        from src.services.account.account_verifier import AccountVerifier
        from src.services.account.account_manager_async import AccountManagerAsync
        from src.infrastructure.common.event.event_bus import EventBus
        
        # 防止重复启动
        if getattr(self, '_is_publishing_loop_active', False):
             InfoBar.warning("运行中", "自动发布队列已在运行中", parent=self)
             return
             
        # 设置状态标识
        self._is_publishing_loop_active = True
        # 预先获取依赖
        service_locator = ServiceLocator()
        publish_service = service_locator.get(PublishService)
        # 用作状态依赖注入
        try:
            db_publish = service_locator.get(PublishRecordRepositoryAsync)
        except Exception:
            db_publish = None
            logger.warning("无法获取 PublishRecordRepositoryAsync 实例")

        # 准备账号检测依赖
        account_repo = AccountRepositoryAsync()
        event_bus = service_locator.get(EventBus)
        account_manager = AccountManagerAsync(user_id=self.user_id, event_bus=event_bus)
        account_verifier = AccountVerifier(account_manager=account_manager, max_workers=1)

        self.log_widget.append_text("======== 🚀 启动自动发布队列 ========")
        
        # 更新按钮状态
        if hasattr(self, 'btn_start_publish'):
            self.btn_start_publish.setEnabled(False)
        if hasattr(self, 'btn_stop_publish'):
            self.btn_stop_publish.setEnabled(True)
        
        # 重置暂停事件
        self.publish_pause_event.set()
        if hasattr(self, 'btn_pause_publish'):
            self.btn_pause_publish.setEnabled(True)
            self.btn_pause_publish.setText("暂停")
            try:
                from qfluentwidgets import FluentIcon
                self.btn_pause_publish.setIcon(FluentIcon.GAME)
            except:
                pass

        try:
            while self._is_publishing_loop_active:
                # 重新拉取最新的 pending 数据（因为运行中可能有别处更新/添加了任务）
                pending_records = [r for r in self.publish_records if r.get('status') == 'pending']
                if not pending_records:
                    self.log_widget.append_text("✅ 所有待发布任务已处理完毕，队列结束。")
                    InfoBar.success("队列结束", "所有待办发布任务均已处理完毕！", parent=self)
                    break
                    
                # 排序并取首个任务
                pending_records.sort(key=lambda x: x.get('created_at', ''))
                task = pending_records[0]
                task_id = task.get('id')
                
                account_name = task.get('platform_username') 
                platform = task.get('platform')
                file_path = task.get('file_path')
                title = task.get('title') or ""
                desc = task.get('description') or ""
                tags_str = task.get('tags') or ""
                tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
                
                if not account_name or not platform or not file_path:
                    self.log_widget.append_error(f"任务 {task_id} 信息不完整，强制标为失败。")
                    if db_publish:
                        await db_publish.update_status(task_id, 'failed', error_message="任务信息不完整")
                    self._load_publish_records()
                    await asyncio.sleep(1)
                    continue

                self.log_widget.append_text(f"---")
                self.log_widget.append_text(f"⏳ 准备执行任务 [ID: {task_id}]: {platform} - {account_name}")
                
                # ==== 1. 严格的前置状态校验 ====
                self.log_widget.append_text(f"🔍 正在复用账号库校验机制检测账号 {account_name} 是否在线...")
                try:
                    # 去 Account库精准提取该账号id和信息以便校验
                    platform_accounts = await account_repo.find_all(user_id=self.user_id, platform=platform)
                    matched_acc = next((a for a in platform_accounts if a.get('platform_username') == account_name), None)
                    
                    if not matched_acc:
                         raise ValueError(f"系统账号库中未匹配到该账号 '{account_name}'")
                         
                    # 使用封装好的 account_verifier 检测该账号
                    check_res = await account_verifier.verify_accounts_batch([matched_acc])
                    acc_id = matched_acc.get('id')
                    res_info = check_res.get(acc_id, {})
                    
                    if not res_info.get('is_logged_in'):
                         error_reason = res_info.get('error', 'Cookie失效或未登录')
                         self.log_widget.append_error(f"🚨 前置检查失败: 账号已掉线 ({error_reason})，自动跳过调起浏览器！")
                         if db_publish:
                             await db_publish.update_status(task_id, 'failed', error_message="已掉线，失败")
                         self._load_publish_records()
                         await asyncio.sleep(1)
                         continue
                    else:
                         self.log_widget.append_text(f"✅ 前置检查通过: 账号处于在线状态。")
                except asyncio.CancelledError:
                    raise
                except Exception as check_e:
                    self.log_widget.append_error(f"🚨 前置检查发生异常: {str(check_e)}，视为不可用，终止任务。")
                    if db_publish:
                        await db_publish.update_status(task_id, 'failed', error_message=f"账号检测异常: {str(check_e)}")
                    self._load_publish_records()
                    await asyncio.sleep(1)
                    continue
                
                # ==== 2. 检查暂停状态 / 执行发布业务 ====
                try:
                    await self.publish_pause_event.wait() # 遵守暂停机制
                    if not self._is_publishing_loop_active:
                        break # 如果等待期间被立刻取消了
                    
                    self.log_widget.append_text(f"▶️ 正在启动浏览器执行发布流程...")
                    
                    # 获取配置参数
                    is_headful = True
                    if hasattr(self, 'headless_check'):
                         is_headful = self.headless_check.isChecked()
                    speed_rate = 1.0
                    if hasattr(self, 'combo_speed_setting'):
                         val = self.combo_speed_setting.currentData()
                         if val:
                             speed_rate = float(val)
                             
                    # 开始包装一层单独的任务执行供中途可取消操作
                    self.current_task = asyncio.create_task(publish_service.publish_single(
                        user_id=self.user_id,
                        account_name=account_name,
                        platform=platform,
                        file_path=file_path,
                        title=title,
                        description=desc,
                        tags=tags,
                        headless=not is_headful,
                        speed_rate=speed_rate,
                        pause_event=self.publish_pause_event,
                        cover_type="first_frame"
                    ))
                    
                    result = await self.current_task
                    
                    if result and result.success:
                         self.log_widget.append_success(f"🎉 任务发布成功！URL: {result.publish_url}")
                         if db_publish:
                             await db_publish.update_status(task_id, 'success', publish_url=result.publish_url)
                    else:
                         msg = result.error_message if result else "未知错误"
                         self.log_widget.append_error(f"❌ 任务发布失败: {msg}")
                         if db_publish:
                             await db_publish.update_status(task_id, 'failed', error_message=msg)
                             
                except asyncio.CancelledError:
                    self.log_widget.append_warning("⚠️ 当前单个发布任务被外界强制取消/停止。")
                    raise  # 抛到外层终止循环
                except Exception as e:
                    error_msg = str(e)
                    self.log_widget.append_error(f"🔥 处理队列发生业务崩溃: {error_msg}")
                    if db_publish:
                        await db_publish.update_status(task_id, 'failed', error_message=error_msg)
                finally:
                    self.current_task = None
                    self._load_publish_records()
                    await asyncio.sleep(1.5)  # 循环间歇喘息

        except asyncio.CancelledError:
            self.log_widget.append_warning("🛑 发布队列强制停止。")
            InfoBar.warning("任务停止", "发布操作已被手动停止", parent=self)
        except Exception as queue_e:
            self.log_widget.append_error(f"🤯 队列保护系统捕获致命异常: {str(queue_e)}")
            InfoBar.error("组件错误", f"队列异常断开：{str(queue_e)}", parent=self)
        finally:
            self._is_publishing_loop_active = False
            self.current_task = None
            if hasattr(self, 'btn_start_publish'):
                self.btn_start_publish.setEnabled(True)
            if hasattr(self, 'btn_stop_publish'):
                self.btn_stop_publish.setEnabled(False)
            if hasattr(self, 'btn_pause_publish'):
                self.btn_pause_publish.setEnabled(False)
                self.btn_pause_publish.setText("暂停")
            # 优雅断开 account_verifier 以防未释放 HttpClient
            try:
                await account_verifier.close()
            except Exception:
                pass

    def _on_stop_publish(self):
        """停止发布"""
        self._is_publishing_loop_active = False # 第一时间阻断下一次执行
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.log_widget.append_warning("🛑 正在请求停止整个队列调度...")

    def _on_pause_publish(self):
        """暂停/继续发布"""
        if not hasattr(self, 'publish_pause_event'):
            return
            
        if self.publish_pause_event.is_set():
            # 当前是运行状态，切换到暂停
            self.publish_pause_event.clear()
            self.log_widget.append_text("⏸️ 已请求暂停发布...")
            if hasattr(self, 'btn_pause_publish'):
                self.btn_pause_publish.setText("继续")
                try:
                    from qfluentwidgets import FluentIcon
                    self.btn_pause_publish.setIcon(FluentIcon.PLAY)
                except:
                    pass
        else:
            # 当前是暂停状态，切换到运行
            self.publish_pause_event.set()
            self.log_widget.append_text("▶️ 已恢复发布...")
            if hasattr(self, 'btn_pause_publish'):
                self.btn_pause_publish.setText("暂停")
                try:
                    from qfluentwidgets import FluentIcon
                    self.btn_pause_publish.setIcon(FluentIcon.GAME)
                except:
                    pass

    def _on_records_loaded(self, records):
        """重写父类方法，当记录加载完成后检查是否需要自动发布"""
        super()._on_records_loaded(records)
        self._check_auto_start()

    def _check_auto_start(self):
        """检查并触发自动发布"""
        # 1. 检查开关
        if not hasattr(self, 'auto_publish_check') or not self.auto_publish_check.isChecked():
            return
            
        # 2. 检查是否已有任务在运行
        if self.current_task is not None:
            return
            
        # 3. 检查是否有待发布任务
        pending_records = [r for r in self.publish_records if r.get('status') == 'pending']
        if not pending_records:
            return
            
        # 4. 触发发布 (使用 create_task 避免阻塞)
        self.log_widget.append_text("⏳ 检测到自动发布开启与待办任务，准备启动...")
        asyncio.create_task(self._on_start_publish())
