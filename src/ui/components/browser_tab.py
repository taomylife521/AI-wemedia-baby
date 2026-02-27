"""
浏览器标签页组件
文件路径：src/ui/components/browser_tab.py
功能：封装单个浏览器标签页，实现Cookie隔离
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import Signal, QUrl, Qt
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtGui import QFont
import logging

# 从核心模块导入静默页面类
from src.infrastructure.browser.qwebengine_browser import SilentWebEnginePage

logger = logging.getLogger(__name__)


class BrowserTabPlaceholder(QWidget):
    """浏览器标签页占位符组件（懒加载）"""
    
    def __init__(self, account_name: str, parent=None):
        super().__init__(parent)
        self._setup_ui(account_name)
    
    def _setup_ui(self, account_name: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 加载提示
        label = QLabel(f"正在初始化浏览器组件...\n账号: {account_name}", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Microsoft YaHei", 12))
        label.setStyleSheet("color: #666;")
        layout.addWidget(label)
        
        self.setStyleSheet("""
            BrowserTabPlaceholder {
                background-color: #F8F9FA;
            }
        """)


class BrowserTab(QWidget):
    """浏览器标签页组件
    
    每个标签页使用独立的QWebEngineProfile实现Cookie隔离
    采用懒加载策略，延迟创建WebEngine组件
    """
    
    # 信号定义
    url_changed = Signal(QUrl)  # URL变化信号
    title_changed = Signal(str)  # 标题变化信号
    load_progress = Signal(int)  # 加载进度信号
    load_finished = Signal(bool)  # 加载完成信号
    cookies_updated = Signal(list)  # Cookie更新信号
    
    def __init__(
        self,
        account_id: int,
        account_name: str,
        platform: str,
        parent: Optional[QWidget] = None
    ):
        """初始化浏览器标签页（懒加载）
        
        Args:
            account_id: 账号ID
            account_name: 账号名称
            platform: 平台ID
            parent: 父组件
        """
        super().__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.platform = platform
        
        # WebEngine组件（延迟创建）
        self.profile: Optional[QWebEngineProfile] = None
        self.page: Optional[QWebEnginePage] = None
        self.browser: Optional[QWebEngineView] = None
        
        # Cookie更新去抖动定时器
        from PySide6.QtCore import QTimer
        self._cookie_update_timer = QTimer(self)
        self._cookie_update_timer.setInterval(2000)  # 2秒延迟
        self._cookie_update_timer.setSingleShot(True)
        self._cookie_update_timer.timeout.connect(self._on_cookie_timer_timeout)
        
        # 初始化状态标记
        self._is_browser_ready = False
        
        # 设置布局（使用StackedWidget切换占位符和浏览器）
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)
        
        # 添加占位符
        self.placeholder = BrowserTabPlaceholder(account_name, self)
        self.stacked_widget.addWidget(self.placeholder)
        self.stacked_widget.setCurrentWidget(self.placeholder)
        
        logger.info(f"创建浏览器标签页（懒加载）: {account_name} (ID: {account_id}, 平台: {platform})")
    
    def _ensure_browser_ready(self):
        """确保浏览器组件已创建（懒加载）"""
        if self._is_browser_ready:
            return
        
        logger.info(f"标签页 [{self.account_name}] 开始创建WebEngine组件")
        
        # 创建独立的Profile实现Cookie隔离
        # profile_name 仅用于内存标识
        profile_name = f"account_{self.account_id}_{self.platform}"
        self.profile = QWebEngineProfile(profile_name, self)
        
        # [Crucial] 设置持久化存储路径，使其符合新的目录结构
        # data/{platform}/{account_name}/qt_profile
        try:
            from src.infrastructure.common.path_manager import PathManager
            account_root = PathManager.get_platform_account_dir(self.platform, self.account_name)
            qt_storage_path = account_root / "qt_profile"
            qt_cache_path = qt_storage_path / "cache"
            
            # 确保目录存在
            qt_storage_path.mkdir(parents=True, exist_ok=True)
            qt_cache_path.mkdir(parents=True, exist_ok=True)
            
            self.profile.setPersistentStoragePath(str(qt_storage_path))
            self.profile.setCachePath(str(qt_cache_path))
            logger.info(f"标签页 [{self.account_name}]设置存储路径: {qt_storage_path}")
        except Exception as e:
            logger.error(f"设置浏览器存储路径失败: {e}")

        
        # 设置用户代理
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 监听Cookie变化
        self.profile.cookieStore().cookieAdded.connect(self._on_cookie_added)
        self.profile.cookieStore().cookieRemoved.connect(self._on_cookie_removed)
        
        # 创建页面和浏览器视图（使用静默页面抑制控制台输出）
        self.page = SilentWebEnginePage(self.profile, self)
        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)
        
        # 禁用更新，避免切换过程中的闪动
        self.setUpdatesEnabled(False)
        try:
            # 添加到StackedWidget
            self.stacked_widget.addWidget(self.browser)
            
            # 切换到浏览器视图
            self.stacked_widget.setCurrentWidget(self.browser)
        finally:
            # 重新启用更新
            self.setUpdatesEnabled(True)
        
        # 连接信号
        self._connect_signals()
        
        self._is_browser_ready = True
        logger.info(f"标签页 [{self.account_name}] WebEngine组件创建完成")
    
    def _connect_signals(self):
        """连接浏览器信号"""
        if not self.page:
            return
        self.page.urlChanged.connect(self.url_changed.emit)
        self.page.titleChanged.connect(self.title_changed.emit)
        self.page.loadProgress.connect(self.load_progress.emit)
        self.page.loadFinished.connect(self.load_finished.emit)

    def _on_cookie_added(self, cookie: QNetworkCookie):
        """Cookie添加回调"""
        self._cookie_update_timer.start()
        
    def _on_cookie_removed(self, cookie: QNetworkCookie):
        """Cookie移除回调"""
        self._cookie_update_timer.start()
        
    def _on_cookie_timer_timeout(self):
        """Cookie更新定时器超时，触发信号"""
        if self.profile:
            self.profile.cookieStore().getAllCookies(self._process_all_cookies)
            
    def _process_all_cookies(self, cookies: List[QNetworkCookie]):
        """处理所有Cookie并转换格式"""
        cookie_list = []
        for cookie in cookies:
            cookie_dict = {
                'name': cookie.name().data().decode('utf-8'),
                'value': cookie.value().data().decode('utf-8'),
                'domain': cookie.domain(),
                'path': cookie.path(),
                'expires': cookie.expirationDate().toString() if cookie.expirationDate().isValid() else None,
                'secure': cookie.isSecure(),
                'httpOnly': cookie.isHttpOnly()
            }
            cookie_list.append(cookie_dict)
        self.cookies_updated.emit(cookie_list)
    
    def load_url(self, url: str):
        """加载URL（懒加载浏览器组件）
        
        Args:
            url: 要加载的URL
        """
        logger.info(f"[BrowserTab] load_url 调用: account_name={self.account_name}, url={url}")
        
        # 确保浏览器组件已创建
        self._ensure_browser_ready()
        
        # 验证URL
        if not url or not url.strip():
            logger.error(f"URL为空或无效: {url}")
            return
        
        # 确保URL有协议前缀
        original_url = url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.info(f"URL缺少协议前缀，已添加: {original_url} -> {url}")
        
        # 验证URL格式
        qurl = QUrl(url)
        if not qurl.isValid():
            logger.error(f"无效的URL: {url}")
            return
        
        try:
            # 验证浏览器组件
            if not self.browser:
                logger.error(f"浏览器组件未初始化")
                return
            
            # 确保浏览器可见
            if not self.browser.isVisible():
                logger.warning(f"浏览器组件不可见，尝试显示")
                self.browser.setVisible(True)
                self.browser.show()
            
            # 加载URL
            logger.info(f"开始设置URL到浏览器: {url}")
            self.browser.setUrl(qurl)
            logger.info(f"标签页 [{self.account_name}] URL设置成功: {url}")
            
            # 验证URL是否已设置
            current_url = self.browser.url().toString()
            logger.info(f"当前浏览器URL: {current_url}")
            
        except Exception as e:
            logger.error(f"加载URL失败: {e}", exc_info=True)
            raise
    
    def inject_cookie(self, cookie_data: List[Dict[str, Any]]) -> bool:
        """注入Cookie（懒加载浏览器组件）
        
        Args:
            cookie_data: Cookie数据列表
            
        Returns:
            bool: 注入成功返回True
        """
        # 确保浏览器组件已创建
        self._ensure_browser_ready()
        
        try:
            if not self.profile:
                logger.error(f"标签页 [{self.account_name}] Profile未初始化")
                return False
            
            cookie_store = self.profile.cookieStore()
            
            for cookie_dict in cookie_data:
                cookie = QNetworkCookie()
                cookie.setName(cookie_dict.get('name', '').encode('utf-8'))
                cookie.setValue(cookie_dict.get('value', '').encode('utf-8'))
                
                if 'domain' in cookie_dict:
                    cookie.setDomain(cookie_dict['domain'])
                if 'path' in cookie_dict:
                    cookie.setPath(cookie_dict.get('path', '/'))
                if 'secure' in cookie_dict:
                    cookie.setSecure(cookie_dict['secure'])
                if 'httpOnly' in cookie_dict:
                    cookie.setHttpOnly(cookie_dict['httpOnly'])
                
                cookie_store.setCookie(cookie)
            
            logger.info(f"标签页 [{self.account_name}] 注入Cookie成功: {len(cookie_data)}个")
            return True
        except Exception as e:
            logger.error(f"标签页 [{self.account_name}] 注入Cookie失败: {e}")
            return False
    
    def get_current_url(self) -> str:
        """获取当前URL
        
        Returns:
            str: 当前URL
        """
        if not self._is_browser_ready or not self.browser:
            return ""
        return self.browser.url().toString()
    
    def get_page_title(self) -> str:
        """获取页面标题
        
        Returns:
            str: 页面标题
        """
        if not self._is_browser_ready or not self.page:
            return ""
        return self.page.title()
    
    def back(self):
        """后退"""
        if self._is_browser_ready and self.browser:
            self.browser.back()
    
    def forward(self):
        """前进"""
        if self._is_browser_ready and self.browser:
            self.browser.forward()
    
    def reload(self):
        """刷新"""
        if self._is_browser_ready and self.browser:
            self.browser.reload()
    
    def can_go_back(self) -> bool:
        """是否可以后退"""
        if not self._is_browser_ready or not self.page:
            return False
        return self.page.history().canGoBack()
    
    def can_go_forward(self) -> bool:
        """是否可以前进"""
        if not self._is_browser_ready or not self.page:
            return False
        return self.page.history().canGoForward()
    
    def execute_javascript(self, script: str, callback: Optional[callable] = None):
        """执行JavaScript代码
        
        Args:
            script: JavaScript代码
            callback: 回调函数（可选）
        """
        if not self._is_browser_ready or not self.page:
            logger.warning(f"标签页 [{self.account_name}] 浏览器未就绪，无法执行JavaScript")
            return
        if callback:
            self.page.runJavaScript(script, callback)
        else:
            self.page.runJavaScript(script)
    
    def cleanup(self):
        """清理资源"""
        try:
            if self._is_browser_ready:
                # 断开信号连接
                if self.page:
                    try:
                        self.page.urlChanged.disconnect()
                        self.page.titleChanged.disconnect()
                        self.page.loadProgress.disconnect()
                        self.page.loadFinished.disconnect()
                    except Exception:
                        pass
                
                # 清理浏览器
                if self.browser:
                    self.browser.setPage(None)
                    self.browser.deleteLater()
                if self.page:
                    self.page.deleteLater()
                if self.profile:
                    self.profile.deleteLater()
            
            logger.info(f"标签页 [{self.account_name}] 资源已清理")
        except Exception as e:
            logger.warning(f"清理标签页资源时出错: {e}")

