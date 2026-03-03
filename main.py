"""
主程序入口
文件路径：main.py
功能：应用程序入口，初始化所有服务并启动主窗口
"""

import sys
import os
import logging
import ctypes

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 抑制 WebEngine 相关的系统级警告
# DirectComposition 错误是 Chromium 在 Windows 上的已知问题，不影响功能
os.environ.setdefault('QT_LOGGING_RULES', 'qt.webenginecontext.info=false;qt.webenginecontext.debug=false')
# 抑制 Chromium 的 DirectComposition 相关错误输出
os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', '')
# 禁用 Chromium 的日志输出
os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '0')
# 设置 Chromium 日志级别为 FATAL（只显示致命错误）
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-logging --log-level=3')

# ============================================================================
# 防止 console=False 打包模式下因为 print 或向 sys.stdout 输出导致的闪退
# ============================================================================
class DummyStream:
    def write(self, data): pass
    def flush(self): pass
    def fileno(self):
        import io
        raise io.UnsupportedOperation("fileno")
    @property
    def closed(self):
        return False

if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()

# ============================================================================
# 全局异常钩子：静默处理 qfluentwidgets 的已知问题
# ============================================================================
# qfluentwidgets 的 FlowLayout 在窗口关闭时会触发 RuntimeError，
# 这是因为其 eventFilter 尝试访问已被 C++ 层删除的 QWidgetItem 对象。
# 这是库的已知问题，不影响应用功能，使用全局钩子静默处理。
_original_excepthook = sys.excepthook

def _custom_excepthook(exc_type, exc_value, exc_tb):
    """自定义异常钩子，静默处理 qfluentwidgets / asyncio 退出时的已知无害异常"""
    # asyncio 退出时常见：取消、事件循环已关闭等
    if exc_type is RuntimeError:
        msg = str(exc_value)
        if any(p in msg for p in (
            'Event loop is closed',
            'Event loop stopped',
            'no running event loop',
        )):
            return
    if exc_type is RuntimeError:
        error_msg = str(exc_value)
        if any(pattern in error_msg for pattern in [
            'QWidgetItem',
            'already deleted',
            'eventFilter',
            'Python override of QObject::eventFilter',
            'Python override of QLayout::eventFilter',
        ]):
            return
    try:
        if exc_type.__name__ == 'CancelledError':
            return
    except Exception:
        pass

    # 针对未被屏蔽的严重错误，记录到独立日志并尝试弹窗
    try:
        import traceback
        import datetime
        from pathlib import Path
        
        # 写入应急崩溃日志
        crash_dir = Path(os.environ.get('APPDATA', '')) / "wemedia_baby_data" / "logs"
        crash_dir.mkdir(parents=True, exist_ok=True)
        crash_file = crash_dir / "fatal_crash.log"
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(crash_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{time_str}] FATAL CRASH:\n{err_msg}\n")
            
        # 尝试弹框警告用户（如果 QApplication 已初始化）
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance():
            QMessageBox.critical(
                None, 
                "应用发生严重错误", 
                f"发生未捕获的严重异常，程序可能不稳定或即将退出。\n\n详情已记录到:\n{crash_file}\n\n错误信息:\n{str(exc_value)}"
            )
    except Exception:
        pass

    _original_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = _custom_excepthook


class StderrFilter:
    """stderr 过滤器，过滤掉已知的无害错误信息（Qt/qfluentwidgets 关闭、asyncio 退出等）"""
    
    # 一旦出现这些行，则开始过滤后续多行（直到空行或明显非错误行）
    _block_start_patterns = (
        'Exception ignored in atexit callback',
        'Task was destroyed but it is pending',
        'Task exception was never retrieved',
        'Future exception was never retrieved',
        'coroutine was never awaited',
        'RuntimeWarning: coroutine ',
        'Event loop stopped before Future completed',
        'Event loop is closed',
    )

    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.filtered_patterns = [
            # DirectComposition 相关错误
            'direct_composition_support.cc',
            'QueryInterface to IDCompositionDevice4 failed',
            '涓嶆敮鎸佹鎺ュ彛',  # 乱码版本的错误信息
            'ERROR:direct_composition',
            # qfluentwidgets 在 atexit 回调期间的已知问题
            'Exception ignored in atexit callback',
            '__moduleShutdown',
            'QWidgetItem',
            'already deleted',
            'eventFilter',
            'flow_layout.py',
            'style_sheet.py',
            'scroll_bar.py',
            'tool_tip.py',
            'Python override of QObject::eventFilter',
            'Python override of QLayout::eventFilter',
            'Python override of QWidget::eventFilter',
            'Internal C++ object',
            # Traceback lines frequent in qfluentwidgets exit errors
            'if e.type() != QEvent.DynamicPropertyChange:',
            'if e.type() != QEvent.Type.Paint',
            'dirty-qss',
            'if obj is self.parent():',
            'if obj in [w.widget() for w in self._items]',
            'wrapped C/C++ object has been deleted',
            'RuntimeError: wrapped C/C++ object has been deleted',
            'if e.type() == QEvent.ToolTip:',
            'if e.type() == QEvent.Type.Wheel:',
            'if obj is not self.parent():',
            # asyncio/qasync 退出时的无害报错
            'Task was destroyed but it is pending',
            'Task exception was never retrieved',
            'Future exception was never retrieved',
            'coroutine was never awaited',
            'Event loop stopped before Future completed',
            'Event loop is closed',
            'asyncio.exceptions.CancelledError',
            'qasync',
            # Qt 退出时线程存储清理
            'QThreadStorage:',
            'destroyed before end of thread',
            'Enable tracemalloc to get the object allocation traceback',
        ]
        self._filtering_block = False

    def write(self, text):
        """过滤掉包含特定模式的行，并对多行错误块整体过滤"""
        if not text or not self.original_stderr:
            return
        # 检测多行错误块的开始（整块后续都过滤）
        if any(p in text for p in self._block_start_patterns):
            self._filtering_block = True
            return
        # 正在过滤块：Traceback/File/空行/缩进行 视为同一块继续过滤
        if self._filtering_block:
            is_traceback_line = (
                text.startswith(' ') or text.startswith('\t') or
                text.startswith('File ') or text.startswith('Traceback ') or
                text.strip().startswith('File ') or
                'Traceback (most recent' in text or '  File "' in text
            )
            if text.strip() == '' and not is_traceback_line:
                self._filtering_block = False
            elif is_traceback_line or any(p in text for p in self.filtered_patterns):
                return
            else:
                self._filtering_block = False
        should_filter = any(pattern in text for pattern in self.filtered_patterns)
        if not should_filter:
            try:
                self.original_stderr.write(text)
            except Exception:
                pass
    
    def flush(self):
        if self.original_stderr:
            try:
                self.original_stderr.flush()
            except Exception:
                pass
    
    def __getattr__(self, name):
        # 转发其他属性到原始 stderr
        return getattr(self.original_stderr, name)

# ============================================================================
# 安装 stderr 过滤器（必须在所有其他导入之前）
# ============================================================================
sys.stderr = StderrFilter(sys.stderr)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# 导入核心模块（保持兼容性，新目录结构已创建但暂不启用）
# 未来迁移完成后切换到新路径
from src.infrastructure.common.path_manager import PathManager
from src.infrastructure.monitoring.log_setup import init_log_manager
from src.infrastructure.common.di.service_locator import ServiceLocator, Scope
from src.infrastructure.common.event.event_bus import EventBus
from src.infrastructure.common.cache.cache_manager import CacheManager
from src.infrastructure.common.config.config_center import ConfigCenter
from src.plugins.core.plugin_manager import PluginManager
from src.infrastructure.common.security.rbac import RBAC
from src.infrastructure.common.security.encryption import EncryptionManager
from src.infrastructure.storage.file_storage import AsyncFileStorage
from src.infrastructure.storage.backup_manager import BackupManager
from src.infrastructure.network.http_client import AsyncHttpClient
from src.services.publish.publish_service import PublishService
from src.services.account.account_service import AccountService
from src.services.subscription.subscription_service import SubscriptionService
from src.infrastructure.common.pipeline.publish_pipeline import PublishPipeline
from src.infrastructure.monitoring.metrics import MetricsCollector
from src.infrastructure.monitoring.logger import StructuredLogger
from src.infrastructure.monitoring.alerting import AlertManager
from src.services.browser.playwright_service import PlaywrightBrowserService

# Tortoise ORM 及 Repository 层（新架构）
from src.infrastructure.storage.tortoise_manager import init_tortoise, close_tortoise
from src.domain.repositories import (
    AccountRepositoryAsync,
    UserRepositoryAsync,
    SubscriptionRepositoryAsync,
    PublishRecordRepositoryAsync,
    MediaFileRepositoryAsync,
    BatchTaskRepositoryAsync,
)

# UI 层
from src.ui.main_window import MainWindow


async def initialize_services_async() -> bool:
    """初始化所有服务（异步版本，新架构）
    
    Returns:
        如果初始化成功返回True，否则返回False
    """
    try:
        # 0. 数据迁移 (已移除)
        
        # 初始化日志管理器 (使用 AppData 下的 logs 目录)
        log_dir = str(PathManager.get_log_dir())
        log_manager = init_log_manager(log_dir=log_dir)
        
        # 使用标准logging模块获取logger
        logger = logging.getLogger("main")
        logger.info("=" * 60)
        logger.info("🚀 媒小宝启动中...")
        logger.info("=" * 60)
        logger.info(f"📁 应用数据目录: {PathManager.get_app_data_dir()}")
        logger.info(f"📝 日志目录: {log_dir}")
        logger.info("")
        
        # 拆分初始化任务
        logger.info("⚡开始并发加载组件与配置...")
        # 提取环境目录供各服务初始化使用
        db_path = str(PathManager.get_db_path())
        file_storage_path = str(PathManager.get_app_data_dir() / "data")
        cache_dir = str(PathManager.get_cache_dir())
        config_dir = str(PathManager.get_config_dir())
        
        service_locator = ServiceLocator()
        service_locator.register(type(log_manager), log_manager, scope=Scope.SINGLETON)
        
        # ----------------------------------------------------
        # 同步轻量级组件：Repository、基础内存模块、DI 组装等
        # ----------------------------------------------------
        
        account_repo = AccountRepositoryAsync()
        service_locator.register(AccountRepositoryAsync, account_repo, scope=Scope.SINGLETON)
        user_repo = UserRepositoryAsync()
        service_locator.register(UserRepositoryAsync, user_repo, scope=Scope.SINGLETON)
        subscription_repo = SubscriptionRepositoryAsync()
        service_locator.register(SubscriptionRepositoryAsync, subscription_repo, scope=Scope.SINGLETON)
        publish_record_repo = PublishRecordRepositoryAsync()
        service_locator.register(PublishRecordRepositoryAsync, publish_record_repo, scope=Scope.SINGLETON)
        media_file_repo = MediaFileRepositoryAsync()
        service_locator.register(MediaFileRepositoryAsync, media_file_repo, scope=Scope.SINGLETON)
        batch_task_repo = BatchTaskRepositoryAsync()
        service_locator.register(BatchTaskRepositoryAsync, batch_task_repo, scope=Scope.SINGLETON)
        
        async_file_storage = AsyncFileStorage(file_storage_path)
        service_locator.register(AsyncFileStorage, async_file_storage, scope=Scope.SINGLETON)
        
        http_client = AsyncHttpClient()
        service_locator.register(AsyncHttpClient, http_client, scope=Scope.SINGLETON)
        
        event_bus = EventBus()
        service_locator.register(EventBus, event_bus, scope=Scope.SINGLETON)
        
        cache_manager = CacheManager(l2_cache_dir=cache_dir)
        service_locator.register(CacheManager, cache_manager, scope=Scope.SINGLETON)
        
        rbac = RBAC()
        service_locator.register(RBAC, rbac, scope=Scope.SINGLETON)
        
        encryption_manager = EncryptionManager()
        service_locator.register(EncryptionManager, encryption_manager, scope=Scope.SINGLETON)
        
        publish_pipeline = PublishPipeline(max_concurrent=5)
        from src.infrastructure.common.pipeline.filters.execution_filter import PublishExecutionFilter
        publish_pipeline.add_filter(PublishExecutionFilter())
        service_locator.register(PublishPipeline, publish_pipeline, scope=Scope.SINGLETON)
        
        publish_service = PublishService()
        service_locator.register(PublishService, publish_service, scope=Scope.SINGLETON)
        
        account_service = AccountService()
        service_locator.register(AccountService, account_service, scope=Scope.SINGLETON)
        
        subscription_service = SubscriptionService()
        service_locator.register(SubscriptionService, subscription_service, scope=Scope.SINGLETON)
        
        from src.services.account.account_manager_async import AccountManagerAsync
        browser_account_manager = AccountManagerAsync(user_id=1, event_bus=event_bus)
        playwright_browser_service = PlaywrightBrowserService(browser_account_manager)
        service_locator.register(PlaywrightBrowserService, playwright_browser_service, scope=Scope.SINGLETON)
        
        metrics_collector = MetricsCollector()
        service_locator.register(MetricsCollector, metrics_collector, scope=Scope.SINGLETON)
        
        structured_logger = StructuredLogger()
        service_locator.register(StructuredLogger, structured_logger, scope=Scope.SINGLETON)
        
        alert_manager = AlertManager()
        service_locator.register(AlertManager, alert_manager, scope=Scope.SINGLETON)
        
        backup_manager = BackupManager()
        backup_manager.start()
        service_locator.register(BackupManager, backup_manager, scope=Scope.SINGLETON)
        logger.info("✅ 1/2 轻量组件注入完毕")
        
        # ----------------------------------------------------
        # 并发执行耗时任务 (IO 或密集型等)
        # ----------------------------------------------------
        config_center = ConfigCenter(config_dir=config_dir)
        service_locator.register(ConfigCenter, config_center, scope=Scope.SINGLETON)
        
        import asyncio
        def wrap_plugin_init():
             PluginManager.initialize()
             service_locator.register(PluginManager, PluginManager(), scope=Scope.SINGLETON)
        
        init_tasks = [
            init_tortoise(db_path),
            config_center.initialize(),
            asyncio.to_thread(wrap_plugin_init)
        ]
        
        # 等待所有重负荷操作并发生效
        await asyncio.gather(*init_tasks)
        logger.info("✅ 2/2 模块配置、ORM初始化、插件扫描（并发加载）完成")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 所有服务初始化成功! Application ready!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logging.error(f"服务初始化失败: {e}", exc_info=True)
        return False


def main():
    """主函数
    
    使用 qasync 统一 Qt 和 asyncio 事件循环，解决以下问题：
    1. 避免 UI 假死（在主线程直接 await 会卡死界面）
    2. 避免任务不执行（未启动 asyncio loop 导致异步任务挂起）
    3. 统一事件循环管理，简化异步代码
    """
    import asyncio
    import qasync
    
    # 这样可以捕获 Chromium 输出的 DirectComposition 错误
    original_stderr = sys.stderr
    stderr_filter = StderrFilter(original_stderr)
    sys.stderr = stderr_filter
    
    # 设置 AppUserModelID，确保任务栏图标正确显示（独立于 Python 图标）
    # 修改 ID 以强制刷新 Windows 图标缓存
    try:
        myappid = 'wemedia_baby.client.1.0.1.force_refresh' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    
    try:
        # [高DPI屏幕适配]
        # Qt6 默认已开启 High-DPI scaling 和 High-DPI pixmaps
        # 这里配置缩放策略，确保 2K/4K 屏幕（125%, 150% 缩放）下显示清晰不模糊
        if hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("媒小宝")
        
        from src.version import __version__
        app.setApplicationVersion(__version__)

        # [异常过滤] 配置全局异常钩子，忽略退出时的 C++ 对象删除错误
        def exception_hook(exctype, value, traceback):
            # 忽略 PySide6/Qt 对象已删除的 RuntimeError
            if exctype == RuntimeError and 'wrapped C/C++ object' in str(value):
                return
            sys.__excepthook__(exctype, value, traceback)
        
        sys.excepthook = exception_hook

        # --- 初始化主题管理器 ---
        try:
            from src.ui.styles.theme_manager import get_theme_manager
            # 获取实例会自动应用主题和QSS
            theme_manager = get_theme_manager() 
            logging.info("主题管理器初始化完成")
        except Exception as e:
            logging.error(f"主题管理器初始化失败: {e}")

        # --- 单实例应用检查 ---
        from PySide6.QtNetwork import QLocalSocket, QLocalServer
        
        # 定义唯一的服务名称（通常使用 AppUserModelID 或类似的唯一标识）
        # 注意: 在 Windows 上，LocalServer 名称如果是全局的，可能受权限影响，但在用户 Session 下通常没问题
        INSTANCE_SERVICE_NAME = "wemedia_baby_single_instance_v1"
        
        # 1. 尝试连接已存在的实例
        check_socket = QLocalSocket()
        check_socket.connectToServer(INSTANCE_SERVICE_NAME)
        if check_socket.waitForConnected(500):
            logging.info("检测到已有实例在运行，尝试唤醒并退出当前进程...")
            # 连接成功，说明已有实例。
            # 这里可以发送参数给旧实例（例如要打开的文件），暂不需要
            check_socket.disconnectFromServer()
            return 0
        
        # 2. 如果连接失败，说明是第一个实例，启动服务器
        local_server = QLocalServer()
        # 清理可能残留的死链接 (例如上次崩溃导致未正常关闭)
        local_server.removeServer(INSTANCE_SERVICE_NAME)
        
        if not local_server.listen(INSTANCE_SERVICE_NAME):
            logging.warning(f"启动单实例监听服务失败: {local_server.errorString()}")
        else:
            logging.info(f"单实例监听服务已启动: {INSTANCE_SERVICE_NAME}")
        
        # --- 检查结束 ---
        
        # 设置全局应用图标 (使用绝对路径)
        project_root = os.path.dirname(os.path.abspath(__file__))
        icon_path_ico = os.path.join(project_root, "resources", "icons", "app.ico")
        icon_path_png = os.path.join(project_root, "resources", "logo.png")
        
        # 优先使用 PNG (Qt对PNG支持很好)，其次使用 ICO
        icon_to_use = None
        if os.path.exists(icon_path_png):
            icon_to_use = icon_path_png
            logging.info(f"发现 PNG 图标: {icon_path_png}")
        elif os.path.exists(icon_path_ico):
             icon_to_use = icon_path_ico
             logging.info(f"发现 ICO 图标: {icon_path_ico}")
        
        if icon_to_use:
            app_icon = QIcon(icon_to_use)
            if not app_icon.isNull():
                app.setWindowIcon(app_icon)
                logging.info(f"成功设置应用图标: {icon_to_use}")
            else:
                logging.error(f"加载图标失败 (QIcon isNull): {icon_to_use}")
        else:
            logging.warning(f"未找到任何应用图标文件")



        
        # 使用 qasync 统一事件循环
        # 这样 Qt 事件和 asyncio 协程共用同一个事件循环
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # 捕获异步事件循环中未处理的异常
        def custom_exception_handler(loop, context):
            msg = context.get("exception", context["message"])
            logging.error(f"[Asyncio 未处理异常]: {msg}")
            
            # 记录到崩溃日志
            try:
                import datetime
                from pathlib import Path
                crash_dir = Path(os.environ.get('APPDATA', '')) / "wemedia_baby_data" / "logs"
                crash_dir.mkdir(parents=True, exist_ok=True)
                with open(crash_dir / "fatal_crash.log", "a", encoding="utf-8") as f:
                    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"\n[{time_str}] ASYNC ERROR:\n{context}\n")
            except Exception:
                pass
                
        loop.set_exception_handler(custom_exception_handler)
        
        async def run_app():
            """异步运行应用程序"""
            # 异步初始化服务
            if not await initialize_services_async():
                logging.error("服务初始化失败，程序退出")
                return 1
            
            # 创建主窗口
            try:
                window = MainWindow()
                
                # 可选：在启动时显示登录对话框（如果需要登录才能使用）
                # 当前版本：不强制登录，用户可以在设置页面登录
                # 如果需要强制登录，取消下面的注释：
                # try:
                #     from src.ui.dialogs.login_dialog import LoginDialog
                #     login_dialog = LoginDialog(window)
                #     login_dialog.login_success.connect(lambda user_info: logging.info(f"用户登录成功: {user_info.get('username')}"))
                #     # 如果取消登录对话框，可以选择退出应用
                #     # if not login_dialog.exec():
                #     #     return 0
                # except Exception as e:
                #     logging.warning(f"启动时显示登录对话框失败: {e}")
                
                window.show()
                
                # 配置单实例唤醒逻辑
                def handle_activation():
                    """处理来自新实例的唤醒请求"""
                    logging.info("收到新实例的唤醒请求，正在激活主窗口...")
                    
                    # 必须处理 pending connection 否则信号会不断触发
                    while local_server.hasPendingConnections():
                        conn = local_server.nextPendingConnection()
                        conn.close()
                    
                    # 恢复窗口状态
                    current_state = window.windowState()
                    if current_state & Qt.WindowMinimized:
                        window.setWindowState(current_state & ~Qt.WindowMinimized | Qt.WindowActive)
                    else:
                        window.setWindowState(current_state | Qt.WindowActive)
                        
                    window.activateWindow()
                    window.raise_()
                    
                    # Windows 特有：闪烁任务栏（可选）
                    # QApplication.alert(window)

                if local_server.isListening():
                    local_server.newConnection.connect(handle_activation)
                
                logging.info("主窗口已显示（qasync 统一事件循环）")
                
                # 使用 asyncio.Event 等待应用退出
                # 这比轮询 isVisible() 更可靠
                quit_event = asyncio.Event()
                
                def on_about_to_quit():
                    """QApplication 即将退出时触发"""
                    logging.info("收到应用退出信号")
                    quit_event.set()
                
                app.aboutToQuit.connect(on_about_to_quit)
                
                # 等待退出事件
                try:
                    await quit_event.wait()
                except asyncio.CancelledError:
                    pass
                finally:
                    # --- 增强的资源清理逻辑（任一步骤异常也不阻塞退出，确保最终 os._exit 被执行）---
                    # 注意：必须先做依赖事件循环的异步清理（浏览器关闭），再做会可能影响事件循环的步骤（配置/HTTP 等）
                    try:
                        logging.info("开始清理应用资源...")
                        sl = None
                        try:
                            from src.infrastructure.common.di.service_locator import ServiceLocator
                            sl = ServiceLocator()
                        except Exception as e:
                            logging.warning(f"获取 ServiceLocator 失败: {e}")

                        # 1. 先关闭所有 Playwright 浏览器（必须在事件循环仍可用时执行，否则只做 Process Guardian）
                        try:
                            from src.services.browser.playwright_service import PlaywrightBrowserService
                            try:
                                asyncio.get_running_loop()
                                loop_ok = True
                            except RuntimeError:
                                loop_ok = False
                            if loop_ok and sl and sl.is_registered(PlaywrightBrowserService):
                                pw_service = sl.get(PlaywrightBrowserService)
                                if hasattr(pw_service, "shutdown"):
                                    logging.info("正在关闭所有浏览器实例...")
                                    try:
                                        await asyncio.wait_for(pw_service.shutdown(), timeout=8.0)
                                        logging.info("所有浏览器实例已关闭")
                                    except asyncio.TimeoutError:
                                        logging.warning("浏览器服务 shutdown 超时，继续执行进程清理")
                                    except RuntimeError as e:
                                        if "no running event loop" in str(e):
                                            logging.warning("事件循环已停止，跳过浏览器优雅关闭，将依赖 Process Guardian 清理")
                                        else:
                                            raise
                            elif not loop_ok:
                                logging.warning("事件循环已停止，跳过浏览器优雅关闭，将依赖 Process Guardian 清理")
                        except Exception as e:
                            if "no running event loop" not in str(e):
                                logging.warning(f"关闭浏览器服务失败: {e}，将依赖 Process Guardian 清理")

                        # 2. Process Guardian（同步，不依赖事件循环；两轮扫描中间短暂等待）
                        try:
                            from src.infrastructure.browser.browser_manager import UndetectedBrowserManager
                            UndetectedBrowserManager.cleanup_all_processes()
                            try:
                                await asyncio.sleep(0.5)
                            except RuntimeError:
                                pass  # 事件循环已停则跳过等待
                            UndetectedBrowserManager.cleanup_all_processes()
                        except Exception as e:
                            if "no running event loop" not in str(e):
                                logging.warning(f"浏览器进程清理失败: {e}")

                        if not sl:
                            try:
                                from src.infrastructure.common.di.service_locator import ServiceLocator
                                sl = ServiceLocator()
                            except Exception:
                                sl = None

                        # 3. 停止批量任务执行器
                        try:
                            if sl:
                                from src.pro_features.batch.services.batch_task_manager_async import BatchTaskManagerAsync
                                if sl.is_registered(BatchTaskManagerAsync):
                                    batch_manager = sl.get(BatchTaskManagerAsync)
                                    if hasattr(batch_manager, 'shutdown'):
                                        logging.info("正在停止批量任务管理器...")
                                        batch_manager.shutdown()
                        except Exception as e:
                            logging.warning(f"清理批量任务资源失败 (若模块未加载可忽略): {e}")

                        # 4. 停止备份调度器
                        try:
                            from src.infrastructure.storage.backup_manager import BackupManager
                            if sl and sl.is_registered(BackupManager):
                                backup_manager = sl.get(BackupManager)
                                backup_manager.stop()
                        except Exception as e:
                            logging.warning(f"停止备份管理器失败: {e}")

                        # 5. 停止配置中心
                        try:
                            # 提前导入，防止下面判定 sl.is_registered 时因未导入抛出进而导致 except 块中也找不到名字
                            from src.infrastructure.common.config.config_center import ConfigCenter
                            if sl and sl.is_registered(ConfigCenter):
                                config_center_instance = sl.get(ConfigCenter)
                                config_center_instance.close()
                                logging.info("配置中心监听已停止")
                        except ImportError as e:
                            logging.debug(f"ConfigCenter 未导入，跳过清理: {e}")
                        except Exception as e:
                            logging.warning(f"停止配置中心失败: {e}")

                        # 6. 关闭 HTTP 客户端
                        try:
                            from src.infrastructure.network.http_client import AsyncHttpClient
                            if sl and sl.is_registered(AsyncHttpClient):
                                client = sl.get(AsyncHttpClient)
                                await client.close()
                                logging.info("HTTP 客户端已关闭")
                        except RuntimeError as e:
                            if "no running event loop" in str(e):
                                pass
                            else:
                                logging.warning(f"关闭 HTTP 客户端失败: {e}")
                        except Exception as e:
                            logging.warning(f"关闭 HTTP 客户端失败: {e}")

                        # 7. 关闭 Tortoise ORM 连接
                        try:
                            coro = close_tortoise()
                            try:
                                loop = asyncio.get_running_loop()
                                task = loop.create_task(coro)
                                done, pending = await asyncio.wait([task], timeout=0.5)
                                if done:
                                    logging.info("Tortoise ORM 连接已安全关闭")
                                else:
                                    logging.debug("Tortoise ORM 关闭交接后台")
                            except RuntimeError:
                                coro.close()
                        except Exception as e:
                            pass

                    except Exception as e:
                        logging.error(f"资源清理过程发生错误: {e}")

                        # 6. [核心] 清理所有剩余的 asyncio 任务
                        try:
                            current_loop = asyncio.get_running_loop()
                        except RuntimeError:
                            current_loop = None
                        if current_loop:
                            current_task = asyncio.current_task(current_loop)
                            pending = [t for t in asyncio.all_tasks(current_loop) if t is not current_task]
                            if pending:
                                logging.info(f"发现 {len(pending)} 个未完成的后台任务，正在执行终止...")
                                for task in pending:
                                    task.cancel()
                                try:
                                    await asyncio.wait(pending, timeout=2.0)
                                except RuntimeError as e:
                                    if "no running event loop" not in str(e):
                                        logging.warning(f"等待任务取消时出错: {e}")
                                still_pending = [t for t in pending if not t.done()]
                                if still_pending:
                                    logging.warning(f"{len(still_pending)} 个后台任务在超时后仍未退出 (将被强行忽略)")
                                else:
                                    logging.info("所有后台任务已清理完毕")

                        logging.info("资源清理流程结束，准备退出进程")
                    except Exception as e:
                        logging.error(f"退出清理过程异常: {e}，仍将强制退出进程")
                    return 0
            
            except asyncio.CancelledError:
                # 正常捕获取消异常
                logging.info("主运行任务被取消")
                return 0
            except Exception as e:
                logging.error(f"启动主窗口失败: {e}", exc_info=True)
                return 1
        
        # 使用 qasync 运行应用程序
        with loop:
            try:
                return loop.run_until_complete(run_app())
            except RuntimeError as e:
                # qasync 在窗口关闭时会抛出此错误，属于正常行为
                if "Event loop stopped before Future completed" in str(e):
                    logging.debug("应用程序正常退出")
                    return 0
                raise
    
    except Exception as e:
        logging.error(f"应用程序启动失败: {e}", exc_info=True)
        return 1
    finally:
        # 恢复原始 stderr
        sys.stderr = original_stderr


if __name__ == "__main__":
    try:
        # 运行主函数
        ret_code = main()
        # [Fix] 强制终止进程，防止非守护线程（如 Chromium 残留）导致进程挂起
        logging.info(f"主程序退出，返回码: {ret_code}，执行 os._exit 强制终止...")
        os._exit(ret_code)
    except KeyboardInterrupt:
        os._exit(0)
    except Exception:
        os._exit(1)

