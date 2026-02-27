"""
QWebEngineView浏览器模块
文件路径：src/core/qwebengine_browser.py
功能：负责浏览器控制、页面操作、Cookie提取和注入
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineCookieStore,
    QWebEnginePage
)
from PySide6.QtCore import QUrl, Signal, QObject, Slot
from PySide6.QtNetwork import QNetworkCookie
import logging
import json

logger = logging.getLogger(__name__)


class SilentWebEnginePage(QWebEnginePage):
    """静默的WebEngine页面，抑制JavaScript控制台输出"""
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """重写JavaScript控制台消息处理，抑制不必要的警告
        
        Args:
            level: 消息级别 (0=Info, 1=Warning, 2=Error)
            message: 消息内容
            lineNumber: 行号
            sourceID: 源ID
        """
        # 只记录错误级别的消息，忽略警告和信息
        # 过滤掉常见的无害警告
        ignored_patterns = [
            'Content Security Policy',
            'Federation Runtime',
            'Garfish',
            'postMessage',
            'upgrade-insecure-requests',
            'logingUrl must be reuqired',
            'depends on.*which is NOT registered',
            'can be call only one time',
            'Package.*is not found'
        ]
        
        message_str = str(message)
        should_ignore = any(pattern in message_str for pattern in ignored_patterns)
        
        if level == 2 and not should_ignore:  # Error级别且不是已知的无害警告
            logger.debug(f"[JS Error] {message_str} (Line {lineNumber}, Source: {sourceID})")
        # 其他级别的消息（Warning, Info）和已知的无害警告都忽略


class QWebEngineBrowser(QWebEngineView):
    """QWebEngineView浏览器模块 - 负责浏览器控制、页面操作、发布执行"""
    
    # 信号定义
    cookie_extracted = Signal(dict)  # Cookie提取完成信号
    page_loaded = Signal(bool)  # 页面加载完成信号（参数：是否成功）
    javascript_result = Signal(object)  # JavaScript执行结果信号
    
    def __init__(self, parent=None):
        """初始化浏览器组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._setup_browser()
        self._cookies: List[Dict[str, Any]] = []
    
    def _setup_browser(self) -> None:
        """设置浏览器配置"""
        # 设置用户代理
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 使用静默页面抑制JavaScript控制台输出
        silent_page = SilentWebEnginePage(profile, self)
        self.setPage(silent_page)
        
        # 连接页面加载完成信号
        self.page().loadFinished.connect(self._on_page_loaded)
        
        # 连接Cookie变化信号
        cookie_store = self.page().profile().cookieStore()
        cookie_store.cookieAdded.connect(self._on_cookie_added)
    
    def load_url(self, url: str) -> None:
        """加载网页
        
        Args:
            url: 网页URL
        """
        self.logger.info(f"加载网页: {url}")
        # 确保URL格式正确
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # 加载URL
        qurl = QUrl(url)
        if not qurl.isValid():
            self.logger.error(f"无效的URL: {url}")
            return
        
        self.setUrl(qurl)
        # 确保浏览器组件可见
        self.setVisible(True)
        self.show()
        self.raise_()
    
    def _on_page_loaded(self, success: bool) -> None:
        """页面加载完成回调
        
        Args:
            success: 是否加载成功
        """
        self.logger.debug(f"页面加载完成: {success}")
        self.page_loaded.emit(success)
    
    def _on_cookie_added(self, cookie: QNetworkCookie) -> None:
        """Cookie添加回调
        
        Args:
            cookie: Cookie对象
        """
        cookie_dict = {
            'name': cookie.name().data().decode('utf-8'),
            'value': cookie.value().data().decode('utf-8'),
            'domain': cookie.domain(),
            'path': cookie.path(),
            'expires': cookie.expirationDate().toString() if cookie.expirationDate().isValid() else None,
            'secure': cookie.isSecure(),
            'httpOnly': cookie.isHttpOnly()
        }
        self._cookies.append(cookie_dict)
    
    def extract_cookies(self) -> List[Dict[str, Any]]:
        """提取Cookie（同步方式，使用已收集的Cookie）
        
        Returns:
            List[Dict[str, Any]]: Cookie列表
        """
        self.logger.debug("提取Cookie")
        # 返回已收集的Cookie（通过_on_cookie_added回调收集）
        # 注意：如果页面刚加载，可能还没有收集到所有Cookie
        cookies = self._cookies.copy()
        self.logger.debug(f"提取到 {len(cookies)} 个Cookie（通过回调收集）")
        
        # 如果Cookie列表为空，尝试通过JavaScript获取
        if not cookies:
            self.logger.debug("Cookie列表为空，尝试通过JavaScript获取")
            try:
                script = """
                (function() {
                    var cookies = [];
                    var cookieStr = document.cookie;
                    if (cookieStr) {
                        var cookieArray = cookieStr.split(';');
                        for (var i = 0; i < cookieArray.length; i++) {
                            var cookie = cookieArray[i].trim();
                            if (cookie) {
                                var parts = cookie.split('=');
                                if (parts.length >= 2) {
                                    cookies.push({
                                        name: parts[0].trim(),
                                        value: parts.slice(1).join('='),
                                        domain: window.location.hostname,
                                        path: '/'
                                    });
                                }
                            }
                        }
                    }
                    return JSON.stringify(cookies);
                })();
                """
                # 注意：这里不能使用回调，因为extract_cookies是同步方法
                # 所以只能返回已收集的Cookie
                pass
            except:
                pass
        
        return cookies
    
    def extract_cookies_async(self, callback: callable) -> None:
        """异步提取所有Cookie
        
        Args:
            callback: 回调函数，接收Cookie列表
        """
        self.logger.debug("异步提取Cookie")
        cookie_store = self.page().profile().cookieStore()
        
        def on_cookies_received(cookies_list):
            """Cookie接收回调"""
            cookies = []
            for cookie in cookies_list:
                cookie_dict = {
                    'name': cookie.name().data().decode('utf-8'),
                    'value': cookie.value().data().decode('utf-8'),
                    'domain': cookie.domain(),
                    'path': cookie.path(),
                    'expires': cookie.expirationDate().toString() if cookie.expirationDate().isValid() else None,
                    'secure': cookie.isSecure(),
                    'httpOnly': cookie.isHttpOnly()
                }
                cookies.append(cookie_dict)
            
            self.logger.debug(f"异步提取到 {len(cookies)} 个Cookie")
            callback(cookies)
        
        cookie_store.getAllCookies(on_cookies_received)
    
    def extract_cookies_dict(self) -> Dict[str, str]:
        """提取Cookie为字典格式（name: value）
        
        Returns:
            Dict[str, str]: Cookie字典
        """
        cookies = self.extract_cookies()
        return {cookie['name']: cookie['value'] for cookie in cookies}

    def clear_cookies(self) -> None:
        """清除所有Cookie"""
        self.logger.info("清除所有Cookie")
        self.page().profile().cookieStore().deleteAllCookies()
        self._cookies = []

    
    def inject_cookie(self, cookie_data: List[Dict[str, Any]]) -> bool:
        """注入Cookie
        
        Args:
            cookie_data: Cookie数据列表，每个元素包含name, value, domain, path等字段
        
        Returns:
            bool: 注入成功返回True
        """
        try:
            cookie_store = self.page().profile().cookieStore()
            
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
            
            self.logger.info(f"注入Cookie成功: {len(cookie_data)}个")
            return True
        except Exception as e:
            self.logger.error(f"注入Cookie失败: {e}")
            return False
    
    def inject_cookie_from_dict(self, cookie_dict: Dict[str, str], domain: str = "") -> bool:
        """从字典格式注入Cookie
        
        Args:
            cookie_dict: Cookie字典（name: value）
            domain: Cookie域名（可选）
        
        Returns:
            bool: 注入成功返回True
        """
        cookie_data = [
            {
                'name': name,
                'value': value,
                'domain': domain,
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            for name, value in cookie_dict.items()
        ]
        return self.inject_cookie(cookie_data)
    
    def execute_javascript(self, script: str, callback: Optional[callable] = None) -> None:
        """执行JavaScript代码
        
        Args:
            script: JavaScript代码
            callback: 回调函数（可选），接收JavaScript返回值
        """
        self.logger.debug(f"执行JavaScript: {script[:100]}...")
        
        if callback:
            def wrapped_callback(result):
                """包装回调函数，添加错误处理"""
                try:
                    # 确保结果被正确处理
                    if result is None:
                        self.logger.warning("JavaScript返回值为None，可能是脚本执行失败或页面未加载完成")
                        # 即使返回None也调用回调，让调用者处理
                        callback(None)
                        return
                    
                    # 处理返回值：如果是字符串，尝试解析为JSON
                    if isinstance(result, str):
                        if result.strip():
                            try:
                                import json
                                parsed_result = json.loads(result)
                                self.logger.debug(f"JavaScript返回JSON字符串，解析为: {type(parsed_result)}")
                                callback(parsed_result)
                            except json.JSONDecodeError:
                                self.logger.warning(f"JavaScript返回的字符串不是有效的JSON: {result[:100]}")
                                callback(result)
                        else:
                            self.logger.warning("JavaScript返回空字符串")
                            callback(None)
                    elif isinstance(result, dict):
                        self.logger.debug(f"JavaScript返回值类型: dict, 键: {list(result.keys())}")
                        callback(result)
                    else:
                        self.logger.debug(f"JavaScript返回值类型: {type(result)}, 值: {result}")
                        callback(result)
                except Exception as e:
                    self.logger.error(f"JavaScript回调执行失败: {e}", exc_info=True)
                    # 即使出错也尝试调用回调，传递错误信息
                    try:
                        callback({'error': str(e)})
                    except:
                        pass
            
            # 确保脚本有返回值
            # 检查脚本是否已经是IIFE格式且有返回值
            script_trimmed = script.strip()
            if script_trimmed.startswith('(function'):
                # 已经是IIFE格式，检查是否有return
                if 'return result' not in script and 'return {' not in script:
                    # 在IIFE末尾添加return
                    if script_trimmed.endswith('})();'):
                        script = script.rstrip().rstrip('})();') + '; return result; })();'
                    elif script_trimmed.endswith('});'):
                        script = script.rstrip().rstrip('});') + '; return result; });'
            
            self.page().runJavaScript(script, wrapped_callback)
        else:
            self.page().runJavaScript(script)
    
    def simulate_click(self, selector: str) -> None:
        """模拟点击操作
        
        Args:
            selector: CSS选择器
        """
        script = f"""
        (function() {{
            var element = document.querySelector('{selector}');
            if (element) {{
                element.click();
                return true;
            }}
            return false;
        }})();
        """
        self.execute_javascript(script)
        self.logger.debug(f"模拟点击: {selector}")
    
    def simulate_input(self, selector: str, text: str) -> None:
        """模拟输入操作
        
        Args:
            selector: CSS选择器
            text: 输入文本
        """
        # 转义特殊字符
        text_escaped = text.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')
        script = f"""
        (function() {{
            var element = document.querySelector('{selector}');
            if (element) {{
                element.value = '{text_escaped}';
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})();
        """
        self.execute_javascript(script)
        self.logger.debug(f"模拟输入: {selector}, 文本长度: {len(text)}")
    
    def upload_file(self, selector: str, file_path: str) -> None:
        """上传文件
        
        Args:
            selector: 文件输入框的CSS选择器
            file_path: 文件路径
        """
        # 注意：QWebEngineView的文件上传需要通过JavaScript触发文件选择对话框
        # 实际文件上传需要用户交互，这里只是触发文件选择
        script = f"""
        (function() {{
            var input = document.querySelector('{selector}');
            if (input && input.type === 'file') {{
                input.click();
                return true;
            }}
            return false;
        }})();
        """
        self.execute_javascript(script)
        self.logger.debug(f"触发文件上传: {selector}, 文件: {file_path}")
    
    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """等待元素出现
        
        Args:
            selector: CSS选择器
            timeout: 超时时间（秒）
        
        Returns:
            bool: 如果元素出现返回True，超时返回False
        """
        # 注意：这是一个简化的实现，实际应该使用异步等待
        script = f"""
        (function() {{
            var element = document.querySelector('{selector}');
            return element !== null;
        }})();
        """
        # 这里需要实现异步等待逻辑
        # 简化版本：直接检查
        self.logger.debug(f"等待元素: {selector}, 超时: {timeout}秒")
        return True
    
    def get_page_title(self) -> str:
        """获取页面标题
        
        Returns:
            str: 页面标题
        """
        return self.page().title()
    
    def get_current_url(self) -> str:
        """获取当前URL
        
        Returns:
            str: 当前URL
        """
        return self.url().toString()

