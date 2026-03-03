# -*- coding: utf-8 -*-
"""
插件管理器 (v2.1 - 静态导入版)
文件路径：src/plugins/core/plugin_manager.py
功能：管理平台插件的加载与获取

重要更新 (2026-03-01):
    为兼容 Nuitka 打包，已将 importlib 动态扫描替换为静态 import。
    新增平台时，请在 _register_all_plugins() 方法中添加对应的静态导入。
"""

import logging
from typing import Dict, Optional, List

from .interfaces.login_plugin import LoginPluginInterface
from .interfaces.publish_plugin import PublishPluginInterface

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器 - 通过静态导入注册所有平台插件
    兼容 PyInstaller / Nuitka 等编译打包方案
    """

    # 插件缓存 {platform_id: PluginInstance}
    _login_plugins: Dict[str, LoginPluginInterface] = {}
    _publish_plugins: Dict[str, PublishPluginInterface] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """初始化插件系统，通过静态导入注册所有内置插件"""
        if cls._initialized:
            return

        logger.info("正在初始化插件系统（静态导入模式）...")
        cls._register_all_plugins()
        cls._initialized = True
        logger.info(
            f"插件初始化完成. "
            f"登录插件: {list(cls._login_plugins.keys())}, "
            f"发布插件: {list(cls._publish_plugins.keys())}"
        )

    @classmethod
    def _register_all_plugins(cls):
        """静态注册所有已知的平台插件（Nuitka/PyInstaller 兼容）

        如需新增平台，请在此方法中添加对应的 import 和注册语句。
        """

        # ========================================
        # 社区插件 (community)
        # ========================================

        # --- 抖音 ---
        try:
            from src.plugins.community.douyin.login_plugin import DouyinLoginPlugin
            cls._login_plugins["douyin"] = DouyinLoginPlugin()
            logger.debug("已加载插件: DouyinLoginPlugin (douyin)")
        except Exception as e:
            logger.error(f"加载抖音登录插件失败: {e}", exc_info=True)

        try:
            from src.plugins.community.douyin.publish_plugin import DouyinPublishPlugin
            cls._publish_plugins["douyin"] = DouyinPublishPlugin()
            logger.debug("已加载插件: DouyinPublishPlugin (douyin)")
        except Exception as e:
            logger.error(f"加载抖音发布插件失败: {e}", exc_info=True)

        # --- 快手 ---
        try:
            from src.plugins.community.kuaishou.login_plugin import KuaishouLoginPlugin
            cls._login_plugins["kuaishou"] = KuaishouLoginPlugin()
            logger.debug("已加载插件: KuaishouLoginPlugin (kuaishou)")
        except Exception as e:
            logger.error(f"加载快手登录插件失败: {e}", exc_info=True)

        try:
            from src.plugins.community.kuaishou.publish_plugin import KuaishouPublishPlugin
            cls._publish_plugins["kuaishou"] = KuaishouPublishPlugin()
            logger.debug("已加载插件: KuaishouPublishPlugin (kuaishou)")
        except Exception as e:
            logger.error(f"加载快手发布插件失败: {e}", exc_info=True)

        # ========================================
        # 专业版插件 (pro)
        # ========================================

        # --- 微信视频号 ---
        try:
            from src.plugins.pro.wechat_video.login_plugin import WechatVideoLoginPlugin
            cls._login_plugins["wechat_video"] = WechatVideoLoginPlugin()
            logger.debug("已加载插件: WechatVideoLoginPlugin (wechat_video)")
        except Exception as e:
            logger.debug(f"加载视频号登录插件失败（可能未授权）: {e}")

        try:
            from src.plugins.pro.wechat_video.publish_plugin import WechatVideoPublishPlugin
            cls._publish_plugins["wechat_video"] = WechatVideoPublishPlugin()
            logger.debug("已加载插件: WechatVideoPublishPlugin (wechat_video)")
        except Exception as e:
            logger.debug(f"加载视频号发布插件失败（可能未授权）: {e}")

        # --- 小红书 ---
        try:
            from src.plugins.pro.xiaohongshu.login_plugin import XiaohongshuLoginPlugin
            cls._login_plugins["xiaohongshu"] = XiaohongshuLoginPlugin()
            logger.debug("已加载插件: XiaohongshuLoginPlugin (xiaohongshu)")
        except Exception as e:
            logger.debug(f"加载小红书登录插件失败（可能未授权）: {e}")

    @classmethod
    def get_login_plugin(cls, platform_id: str) -> Optional[LoginPluginInterface]:
        """获取登录插件"""
        cls.initialize()
        return cls._login_plugins.get(platform_id)

    @classmethod
    def get_publish_plugin(cls, platform_id: str) -> Optional[PublishPluginInterface]:
        """获取发布插件"""
        cls.initialize()
        return cls._publish_plugins.get(platform_id)

    @classmethod
    def get_available_platforms(cls) -> List[str]:
        """获取所有可用平台ID列表"""
        cls.initialize()
        # 以登录插件为准，因为发布通常依赖登录
        return sorted(list(cls._login_plugins.keys()))
