"""
账号凭证与指纹配置管理器
文件路径：src/infrastructure/browser/profile_manager.py
功能：管理 storage_state.json (登录凭证) 和 fingerprint_config.json (浏览器指纹)
"""

import os
import json
import random
import logging
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


# 常见的屏幕分辨率列表
COMMON_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]


class ProfileManager:
    """账号凭证与指纹配置管理器
    
    职责：
    1. 管理 storage_state.json (Cookies, LocalStorage)
    2. 管理 fingerprint_config.json (UA, Viewport, Locale)
    3. 确保每个账号有独立的持久化目录
    """
    
    def __init__(self, account_id: str, platform: str = "", account_name: str = "", fingerprint_config: Optional[dict] = None):
        """初始化
        
        Args:
            account_id: 账号唯一标识 (如手机号或平台ID) - 在新版结构中可能只作为标识符使用
            platform: 平台名称 (如 douyin)
            account_name: 平台用户名 (唯一标识，用于生成文件夹名)
            fingerprint_config: 指纹配置,None则随机生成
        """
        self.account_id = account_id
        
        # 兼容旧代码：如果未提供 platform/account_name，尝试从 account_id 推断或回退
        # 但为了强制迁移，建议调用方必须提供 (暂时保留回退逻辑)
        if not platform or not account_name:
            # 回退到旧逻辑，但统一使用 PathManager (Local AppData) 避免数据分散到 Roaming
            from src.infrastructure.common.path_manager import PathManager
            self.base_dir = PathManager.get_app_data_dir() / 'data' / 'browsers' / account_id
        else:
            # 新逻辑: 使用 PathManager 获取统一的账号根目录
            from src.infrastructure.common.path_manager import PathManager
            account_root = PathManager.get_platform_account_dir(platform, account_name)
            self.base_dir = account_root / 'browser'
        
        # 确保目录存在
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径
        self.storage_state_path = self.base_dir / 'storage_state.json'
        self.fingerprint_path = self.base_dir / 'fingerprint_config.json'
        self.user_data_dir = self.base_dir / 'user_data'
        
        # 如果提供了自定义指纹配置，生成并保存
        if fingerprint_config is not None:
            logger.info(f"使用自定义指纹配置初始化: {account_name}")
            self.generate_fingerprint(fingerprint_config)
            
        logger.debug(f"ProfileManager 初始化: account={account_name}, platform={platform}, base_dir={self.base_dir}")

    
    async def save_storage_state(self, context: BrowserContext) -> bool:
        """保存浏览器上下文的 storage_state
        
        Args:
            context: Playwright BrowserContext 实例
            
        Returns:
            是否保存成功
        """
        try:
            # 使用 Playwright 内置方法导出
            await context.storage_state(path=str(self.storage_state_path))
            logger.info(f"凭证已保存: {self.storage_state_path}")
            return True
        except Exception as e:
            logger.error(f"保存凭证失败: {e}", exc_info=True)
            return False
    
    async def load_storage_state(self) -> Optional[Dict[str, Any]]:
        """加载已保存的 storage_state
        
        Returns:
            storage_state 字典，不存在则返回 None
        """
        if not self.storage_state_path.exists():
            logger.debug(f"凭证文件不存在: {self.storage_state_path}")
            return None
        
        try:
            async with aiofiles.open(self.storage_state_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                logger.info(f"凭证已加载: {self.storage_state_path}")
                return data
        except Exception as e:
            logger.error(f"加载凭证失败: {e}", exc_info=True)
            return None
    
    def get_storage_state_path(self) -> Optional[str]:
        """获取 storage_state 文件路径 (如果存在)
        
        Returns:
            文件路径字符串，不存在则返回 None
        """
        if self.storage_state_path.exists():
            return str(self.storage_state_path)
        return None
    
    def get_fingerprint(self) -> Dict[str, Any]:
        """获取指纹配置，若不存在则生成默认配置
        
        Returns:
            指纹配置字典，包含 user_agent, viewport, locale, timezone 等
        """
        if self.fingerprint_path.exists():
            try:
                with open(self.fingerprint_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 检查并补全缺失的字段 (针对旧版本指纹文件)
                is_dirty = False
                
                # 1. 补全硬件并发数
                if "hardware_concurrency" not in config:
                    config["hardware_concurrency"] = random.choice([4, 8, 12, 16])
                    is_dirty = True
                    
                # 2. 补全设备内存
                if "device_memory" not in config:
                    config["device_memory"] = random.choice([4, 8, 16, 32])
                    is_dirty = True
                    
                # 3. 补全显卡信息
                if "webgl_vendor" not in config or "webgl_renderer" not in config:
                    config["webgl_vendor"] = "Google Inc. (NVIDIA)"
                    config["webgl_renderer"] = random.choice([
                        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                        "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
                        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
                        "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                        "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                    ])
                    is_dirty = True

                # 4. 补全 Canvas 噪声种子
                if "canvas_noise_seed" not in config:
                    config["canvas_noise_seed"] = random.randint(1, 1000000)
                    is_dirty = True
                
                # 如果有更新，则保存回去
                if is_dirty:
                    logger.info(f"升级旧版指纹配置，补全硬件参数: {self.fingerprint_path}")
                    self.save_fingerprint(config)
                    
                logger.debug(f"指纹配置已加载: {self.fingerprint_path}")
                return config
            except Exception as e:
                logger.warning(f"加载指纹配置失败，将重新生成: {e}")
        
        # 生成默认配置
        config = self._generate_default_fingerprint()
        self.save_fingerprint(config)
        return config
    
    def generate_fingerprint(self, custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成指纹配置(支持自定义)
        
        Args:
            custom_config: 用户自定义配置,None则随机生成
            
        Returns:
            指纹配置字典
        """
        if custom_config is None:
            # 随机生成
            logger.info("使用随机生成指纹")
            config = self._generate_default_fingerprint()
        else:
            # 使用用户配置
            logger.info(f"使用自定义指纹配置: {custom_config.keys()}")
            base_config = self._generate_default_fingerprint()
            # 用自定义配置覆盖
            base_config.update(custom_config)
            config = base_config
        
        # 一致性检查
        from .fingerprint_checker import validate_fingerprint
        config = validate_fingerprint(config)
        
        # 保存配置
        self.save_fingerprint(config)
        return config

    
    def save_fingerprint(self, config: Dict[str, Any]) -> bool:
        """保存指纹配置
        
        Args:
            config: 指纹配置字典
            
        Returns:
            是否保存成功
        """
        try:
            with open(self.fingerprint_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"指纹配置已保存: {self.fingerprint_path}")
            return True
        except Exception as e:
            logger.error(f"保存指纹配置失败: {e}", exc_info=True)
            return False
    
    def _generate_default_fingerprint(self) -> Dict[str, Any]:
        """生成默认指纹配置
        
        注意：UA 版本将在 BrowserManager 启动时动态对齐到实际内核版本
        
        Returns:
            默认指纹配置字典
        """
        # 默认 viewport 为 None，让浏览器自适应窗口大小
        viewport = None
        
        # 常见屏幕分辨率池
        screen_resolutions = [
            {"width": 1920, "height": 1080},
            {"width": 2560, "height": 1440},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 3840, "height": 2160},
        ]
        screen = random.choice(screen_resolutions)
        
        config = {
            # UA 占位符，将在 BrowserManager 中根据实际浏览器版本动态填充，这里先给一个默认值通过检查
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "viewport": viewport,
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "color_scheme": "light",
            "device_scale_factor": 1.0,
            
            # --- Canvas 指纹 ---
            # Canvas 噪声种子 (每个账号固定，确保指纹一致性)
            "canvas_noise_seed": random.randint(1, 1000000),
            
            # --- 硬件参数指纹 ---
            # 1. CPU 核心数 (hardwareConcurrency)
            "hardware_concurrency": random.choice([4, 8, 12, 16]),
            
            # 2. 设备内存 (deviceMemory)
            "device_memory": random.choice([4, 8, 16, 32]),
            
            # 3. WebGL 厂商与渲染器 (显卡指纹)
            "webgl_vendor": "Google Inc. (NVIDIA)", # 默认前缀，通常即为此格式
            "webgl_renderer": random.choice([
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            ]),
            
            # --- Screen 屏幕指纹 ---
            "screen_width": screen["width"],
            "screen_height": screen["height"],
            "screen_avail_width": screen["width"],
            "screen_avail_height": screen["height"] - 40,  # 减去任务栏高度
            "screen_color_depth": 24,
            "screen_pixel_depth": 24,
            
            # --- AudioContext 音频指纹 ---
            "audio_context_seed": random.randint(1, 1000000),
            
            # --- Battery API ---
            "battery_charging": True,
            "battery_level": round(random.uniform(0.5, 1.0), 2),
            
            # --- Navigator 扩展属性 ---
            "platform": "Win32",
            "max_touch_points": 0,
            "vendor": "Google Inc.",
            "vendor_sub": "",
            "product_sub": "20030107",
            
            # --- Connection 网络连接 ---
            "connection_effective_type": random.choice(["4g", "wifi"]),
            "connection_downlink": random.choice([10, 20, 50, 100]),
            "connection_rtt": random.randint(20, 100),
        }
        
        logger.info(f"生成默认指纹配置: viewport={viewport}, screen={screen['width']}x{screen['height']}")
        
        # 一致性检查
        from .fingerprint_checker import validate_fingerprint
        config = validate_fingerprint(config)
        
        return config
    
    def get_user_data_dir(self) -> str:
        """获取 user_data_dir 路径
        
        Returns:
            用户数据目录路径
        """
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        return str(self.user_data_dir)
    
    def has_valid_credentials(self) -> bool:
        """检查是否有有效的登录凭证
        
        Returns:
            是否存在 storage_state.json
        """
        return self.storage_state_path.exists()
