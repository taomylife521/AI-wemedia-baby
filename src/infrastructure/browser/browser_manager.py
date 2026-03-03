"""
账号绑定的浏览器管理器
文件路径：src/infrastructure/browser/browser_manager.py
功能：统一管理 Playwright 浏览器生命周期，支持账号级环境隔离与指纹持久化
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext

from .profile_manager import ProfileManager
from src.infrastructure.common.path_manager import PathManager

logger = logging.getLogger(__name__)


# UA 模板列表 (主版本号占位符 {VERSION})
UA_TEMPLATES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{VERSION}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{VERSION}.0.6099.109 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{VERSION}.0.6099.130 Safari/537.36",
]


class UndetectedBrowserManager:
    """账号绑定的浏览器管理器
    
    核心职责：
    1. 管理 Playwright Browser/Context 生命周期
    2. 自动加载账号凭证和指纹配置
    3. 注入抗检测脚本
    4. 支持有头/无头模式切换
    """
    
    @classmethod
    async def warmup_environment(cls):
        """预热浏览器环境 (后台静默执行)
        
        主要目的：
        1. 预加载 Playwright 库到内存
        2. 确保 driver 进程可启动
        3. 减少用户首次点击时的等待时间
        """
        try:
            logger.info("[BrowserManager] 开始环境预热...")
            import time
            start_time = time.time()
            
            # 启动并立即关闭一个 Playwright 实例
            # 这会触发驱动解压（如需）和库加载
            async with async_playwright() as p:
                pass
                
            elapsed = time.time() - start_time
            logger.info(f"[BrowserManager] 环境预热完成，耗时: {elapsed:.2f}s")
        except Exception as e:
            logger.warning(f"[BrowserManager] 环境预热失败 (不影响正常使用): {e}")

    @classmethod
    def cleanup_all_processes(cls):
        """强力清理所有残留的浏览器进程 (Process Guardian)
        
        扫描所有 chrome/msedge 进程，若其命令行包含当前应用的数据目录，
        则视为残留进程进行强制结束。
        """
        try:
            import psutil
            
            # 获取应用数据根目录作为特征
            # e.g. .../AppData/Local/WeMediaBaby
            data_root = str(PathManager.get_app_data_dir()).lower().replace("\\", "/")
            logger.info(f"[Process Guardian] 开始全量扫描，特征路径: {data_root}")
            
            cleaned_count = 0
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 1. 进程名过滤
                    name = proc.info.get('name', '').lower()
                    if not any(x in name for x in ['chrome', 'msedge', 'chromium']):
                        continue
                        
                    # 2. 命令行过滤 (懒加载，只获取目标进程的 cmdline)
                    # proc.cmdline() 可能会抛出 AccessDenied 或 NoSuchProcess
                    cmdline_list = proc.cmdline()
                    cmdline = " ".join(cmdline_list or []).lower().replace("\\", "/")
                    
                    # 检查是否包含本应用的数据目录路径
                    if data_root in cmdline:
                        logger.warning(f"[Process Guardian] 发现残留进程 PID={proc.info['pid']} ({name}), 正在清理...")
                        try:
                            proc.kill()
                            proc.wait(timeout=1.0)
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                            pass
                        cleaned_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if cleaned_count > 0:
                logger.info(f"[Process Guardian] 清理完成，共结束 {cleaned_count} 个残留进程")
            else:
                logger.info("[Process Guardian] 系统干净，未发现残留进程")
                
        except ImportError:
            logger.warning("[Process Guardian] 未安装 psutil，跳过进程清理")
        except Exception as e:
            logger.error(f"[Process Guardian] 清理过程异常: {e}", exc_info=True)

    def __init__(
        self, 
        account_id: str, 
        platform: str = "", 
        account_name: str = "",
        fingerprint_config: Optional[Dict[str, Any]] = None,  # 新增参数
        profile_folder_name: Optional[str] = None
    ):
        """初始化
        
        Args:
            account_id: 账号唯一标识
            platform: 平台名称 (如 douyin)
            account_name: 账号名称 (用于生成文件夹名)
            fingerprint_config: 指纹配置,None则随机生成
            profile_folder_name: 持久化使用的唯一 UUID 文件夹
        """
        self.account_id = account_id
        self.profile_manager = ProfileManager(
            account_id, 
            platform, 
            account_name,
            fingerprint_config=fingerprint_config,  # 传递指纹配置
            profile_folder_name=profile_folder_name
        )
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.user_data_dir: Optional[Path] = None  # 新增：记录用户数据目录
        
        self._browser_version: Optional[str] = None
        
        logger.info(f"### [V9] UndetectedBrowserManager 加载成功 ### account={account_name}, platform={platform}")
    
    async def launch(self, headless: bool = True) -> Optional[BrowserContext]:
        """启动浏览器并返回 Context (Persistent)"""
        try:
            self.playwright = await async_playwright().start()
            
            # 如果已有 context，先关闭避免冲突
            if self.context:
                try:
                    logger.info("检测到已有浏览器实例，先关闭...")
                    await self.context.close()
                    self.context = None
                    self.browser = None
                except Exception as e:
                    logger.warning(f"关闭旧浏览器实例时出错: {e}")
            
            # 启动参数
            args = self._get_launch_args()
            
            # 仅使用本地 Chrome
            channel = "chrome"
            
            # 获取用户数据目录
            self.user_data_dir = self.profile_manager.get_user_data_dir()
            logger.info(f"正在启动浏览器 (Persistent Context): channel={channel}, user_data_dir={self.user_data_dir}")
            
            # 获取指纹配置
            fingerprint = self.profile_manager.get_fingerprint()
            
            # 1. 动态生成/获取 User Agent
            user_agent = fingerprint.get("user_agent")
            if not user_agent:
                # 如果没有保存的 UA，则生成一个新的
                import random
                template = random.choice(UA_TEMPLATES)
                
                # 尝试获取 Chrome 版本号 (简单模拟，实际应用中可能需要更复杂的查找)
                # 这里我们假设主流版本为 120-128 之间的一个随机大版本，或者硬编码
                # 为了更像真实浏览器，我们可以保留 {VERSION} 占位符后续替换，或者现在替换
                # 这里简单替换为 128 (较新版本) 避免过旧
                version_major = str(random.randint(120, 131)) 
                user_agent = template.replace("{VERSION}", version_major)
                
                # 保存回指纹配置，确保下次启动一致
                fingerprint["user_agent"] = user_agent
                self.profile_manager.save_fingerprint(fingerprint)
                logger.info(f"已生成并绑定新 User-Agent: {user_agent}")
            else:
                logger.debug(f"加载已有 User-Agent: {user_agent}")

            # 准备启动选项
            launch_options = {
                "user_data_dir": self.user_data_dir,
                "headless": headless,
                "args": args,
                "channel": channel,
                "user_agent": user_agent, # 注入 User-Agent
                "viewport": None, # 关键：禁用视口限制
                "no_viewport": True, # 显式禁用视口模拟，防止 Playwright 施加默认 1280x720 限制
                "locale": fingerprint.get("locale", "zh-CN"),
                "timezone_id": fingerprint.get("timezone_id", "Asia/Shanghai"),
                "permissions": ["geolocation", "notifications"],
                "ignore_https_errors": True,
                # "device_scale_factor": 1.0, # 移除，跟随系统
                "ignore_default_args": ["--enable-automation"], # 关键：去掉自动测试软件的控制提示条
            }
            
            # 使用 launch_persistent_context
            self.context = await self.playwright.chromium.launch_persistent_context(**launch_options)
            
            # 兼容性设置：让 self.browser 指向 context 
            self.browser = self.context 
            
            # 注入抗检测脚本
            await self._inject_stealth_scripts()
            
            # 如果是首次迁移，尝试注入旧的 storage_state (如果有)
            old_storage = await self.profile_manager.load_storage_state()
            if old_storage and old_storage.get("cookies"):
                try:
                    await self.context.add_cookies(old_storage["cookies"])
                    logger.info("已迁移旧版 Cookies 到 Persistent Context")
                except Exception as e:
                    logger.warning(f"迁移旧版 Cookies 失败: {e}")
            
            logger.info(f"浏览器启动成功 (Persistent, headless={headless})")
            return self.context
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}", exc_info=True)
            await self.close()
            return None
    
    def _get_launch_args(self) -> List[str]:
        """获取浏览器启动参数"""
        return [
            "--no-sandbox",
            "--test-type", # 关键：屏蔽“不受支持的命令行标记(--no-sandbox)”的安全警告横幅
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--ignore-certificate-errors",
            "--disable-infobars",
            "--exclude-switches=enable-automation",
            # "--use-gl=desktop", # 禁用此选项可能解决部分机器卡死问题
            # WebRTC 隐私保护
            "--webrtc-ip-handling-policy=default_public_interface_only",
            "--disable-webrtc-hw-encoding",
            "--disable-webrtc-hw-decoding",
            "--start-maximized",  # 启动时最大化窗口
        ]
    
    async def _inject_stealth_scripts(self):
        """注入抗检测脚本"""
        if not self.context:
            return
        
        # 获取指纹配置
        fingerprint = self.profile_manager.get_fingerprint()
        
        # 提取所有指纹参数 (提供默认值以防旧配置缺失)
        hardware_concurrency = fingerprint.get("hardware_concurrency", 4)
        device_memory = fingerprint.get("device_memory", 8)
        webgl_vendor = fingerprint.get("webgl_vendor", "Google Inc. (NVIDIA)")
        webgl_renderer = fingerprint.get("webgl_renderer", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)")
        
        # Screen 参数
        screen_width = fingerprint.get("screen_width", 1920)
        screen_height = fingerprint.get("screen_height", 1080)
        screen_avail_width = fingerprint.get("screen_avail_width", 1920)
        screen_avail_height = fingerprint.get("screen_avail_height", 1040)
        screen_color_depth = fingerprint.get("screen_color_depth", 24)
        screen_pixel_depth = fingerprint.get("screen_pixel_depth", 24)
        
        # AudioContext 种子
        audio_context_seed = fingerprint.get("audio_context_seed", 12345)
        
        # Battery 参数
        battery_charging = str(fingerprint.get("battery_charging", True)).lower()
        battery_level = fingerprint.get("battery_level", 1.0)
        
        # Navigator 扩展
        platform = fingerprint.get("platform", "Win32")
        max_touch_points = fingerprint.get("max_touch_points", 0)
        vendor = fingerprint.get("vendor", "Google Inc.")
        vendor_sub = fingerprint.get("vendor_sub", "")
        product_sub = fingerprint.get("product_sub", "20030107")
        
        # Connection 参数
        connection_type = fingerprint.get("connection_effective_type", "4g")
        connection_downlink = fingerprint.get("connection_downlink", 10)
        connection_rtt = fingerprint.get("connection_rtt", 50)
        
        # Canvas 种子
        canvas_noise_seed = fingerprint.get("canvas_noise_seed", 12345)
        
        # 读取外部 JS 模板文件
        try:
            # 假设资源目录结构: src/resources/scripts/stealth/stealth.js
            # 也可以通过相对路径定位
            script_path = PathManager.get_resource_dir() / "src" / "resources" / "scripts" / "stealth" / "stealth.js"
            
            if not script_path.exists():
                logger.error(f"抗检测脚本文件未找到: {script_path}")
                return

            stealth_template = script_path.read_text(encoding="utf-8")
            
            # 执行变量替换
            stealth_script = stealth_template.replace("__HARDWARE_CONCURRENCY__", str(hardware_concurrency)) \
                .replace("__DEVICE_MEMORY__", str(device_memory)) \
                .replace("__SCREEN_WIDTH__", str(screen_width)) \
                .replace("__SCREEN_HEIGHT__", str(screen_height)) \
                .replace("__SCREEN_AVAIL_WIDTH__", str(screen_avail_width)) \
                .replace("__SCREEN_AVAIL_HEIGHT__", str(screen_avail_height)) \
                .replace("__SCREEN_COLOR_DEPTH__", str(screen_color_depth)) \
                .replace("__SCREEN_PIXEL_DEPTH__", str(screen_pixel_depth)) \
                .replace("__WEBGL_VENDOR__", str(webgl_vendor)) \
                .replace("__WEBGL_RENDERER__", str(webgl_renderer)) \
                .replace("__PLATFORM__", str(platform)) \
                .replace("__MAX_TOUCH_POINTS__", str(max_touch_points)) \
                .replace("__VENDOR__", str(vendor)) \
                .replace("__VENDOR_SUB__", str(vendor_sub)) \
                .replace("__PRODUCT_SUB__", str(product_sub)) \
                .replace("__BATTERY_CHARGING__", battery_charging) \
                .replace("__BATTERY_LEVEL__", str(battery_level)) \
                .replace("__CONNECTION_TYPE__", str(connection_type)) \
                .replace("__CONNECTION_DOWNLINK__", str(connection_downlink)) \
                .replace("__CONNECTION_RTT__", str(connection_rtt)) \
                .replace("__AUDIO_CONTEXT_SEED__", str(audio_context_seed)) \
                .replace("__CANVAS_NOISE_SEED__", str(canvas_noise_seed))

        except Exception as e:
            logger.error(f"加载抗检测脚本失败: {e}", exc_info=True)
            return
        
        await self.context.add_init_script(stealth_script)
        logger.info("高级抗检测脚本已注入 (WebRTC/MediaDevices/Permissions/Intl/CDP/Headless)")


    
    async def save_state(self) -> bool:
        """保存当前 Context 的 storage_state (Persistent模式下可选，因为会自动保存到磁盘)
        但为了兼容旧逻辑检查，我们依然可以导出
        """
        if not self.context:
            logger.warning("无法保存状态：Context 不存在")
            return False
        
        return await self.profile_manager.save_storage_state(self.context)
    
    async def close(self):
        """关闭浏览器并清理资源 - 采用激进清理策略以防止卡死"""
        logger.info(f"[BrowserManager] 启动强制清理流程: {self.account_id}")
        
        # 1. 优先强制终止进程 (最高优先级)
        # 这一步最关键，直接释放文件锁和内存，防止接下来的优雅关闭步骤卡死
        try:
            logger.info(f"[BrowserManager] 步骤1: 优先强制杀死浏览器进程...")
            await self._force_kill_browser_process()
            logger.info(f"[BrowserManager] 步骤1: 进程已终止")
        except Exception as e:
            logger.warning(f"[BrowserManager] 步骤1: 进程清理出错: {e}")

        # 2. 尝试资源对象回收
        # 既然进程已经杀掉，下面的 close 调用通常会立即报错并返回，不会再挂起
        if self.context:
            try:
                logger.info(f"[BrowserManager] 步骤2: 清理 Context 对象...")
                # 极短超时，仅为触发 Playwright 内部清理
                await asyncio.wait_for(self.context.close(), timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                pass
            self.context = None
            self.browser = None
            
        if self.playwright:
            try:
                logger.info(f"[BrowserManager] 步骤3: 停止 Playwright 实例...")
                await asyncio.wait_for(self.playwright.stop(), timeout=1.0)
            except Exception:
                pass
            self.playwright = None
            
        logger.info(f"[BrowserManager] ✓ 浏览器清理流程圆满结束: {self.account_id}")

    async def _force_kill_browser_process(self):
        """强制终止与当前 user_data_dir 相关的浏览器进程"""
        if not self.user_data_dir:
            return

        # 核心逻辑：获取 user_data_dir 的特征路径片段（如 temp_new_xxx）
        # 路径通常如: .../data/{platform}/temp_new_177022.../browser/user_data
        target_path = str(self.user_data_dir).lower().replace("\\", "/")
        
        # 提取关键 UUID 特征（即 user_data 的父级目录的父级目录）
        path_parts = target_path.split("/")
        feature_token = None
        try:
            # 找到 browser/user_data 的前一级，即 UUID 目录名
            if "browser" in path_parts:
                idx = path_parts.index("browser")
                if idx > 0:
                    feature_token = path_parts[idx-1]
        except:
            pass
            
        search_target = feature_token or target_path
        logger.info(f"[BrowserManager] 扫描残留进程... 目标特征: {search_target}")
        
        try:
            import psutil
            terminated_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 1. 过滤：只关注浏览器进程
                    proc_name = proc.info.get('name', '').lower()
                    if not any(x in proc_name for x in ['chrome', 'msedge', 'browser', 'chromium']):
                        continue
                        
                    # 2. 匹配：检查命令行是否包含目标路径特征
                    cmdline = " ".join(proc.info.get('cmdline') or []).lower().replace("\\", "/")
                    
                    if search_target in cmdline:
                        logger.warning(f"[BrowserManager] 发现目标残留进程 PID={proc.info['pid']}, 正在强杀以释放文件锁...")
                        proc.kill() # 直接强杀，解决 Windows 上的句柄锁定问题
                        terminated_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if terminated_count > 0:
                logger.info(f"[BrowserManager] 成功清理 {terminated_count} 个残留进程，目标: {search_target}")
                # 稍微等待系统回收句柄
                await asyncio.sleep(1.0)
            else:
                logger.debug(f"[BrowserManager] 未发现匹配 {search_target} 的活跃进程")
                
        except Exception as e:
            logger.error(f"[BrowserManager] 强制清理进程异常: {e}")
    
    def get_browser_version(self) -> Optional[str]:
        """获取浏览器版本"""
        return self._browser_version
    
    def has_valid_credentials(self) -> bool:
        """检查账号是否有有效凭证"""
        # Persistent模式下，是否有凭证取决于 user_data_dir 是否有数据
        # 这里兼容旧逻辑，依然检查 storage_state.json
        # 或者检查 user_data_dir 是否为空？
        # 暂时保持原样，因为 save_state 依然会生成 storage_state.json
        return self.profile_manager.has_valid_credentials()
