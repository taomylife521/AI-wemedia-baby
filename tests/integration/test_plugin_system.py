
import unittest
import asyncio
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.plugins.plugin_manager import PluginManager
from src.plugins.interfaces.login_plugin import LoginPluginInterface
from src.config.feature_flags import USE_PLUGIN_SYSTEM

class TestPluginSystem(unittest.TestCase):
    
    def test_feature_flag(self):
        """测试特性开关是否开启"""
        print(f"\n[Test] Checking Feature Flag: USE_PLUGIN_SYSTEM={USE_PLUGIN_SYSTEM}")
        self.assertTrue(USE_PLUGIN_SYSTEM, "Plugin system should be enabled by default")

    def test_douyin_plugin_loader(self):
        """测试抖音插件加载"""
        print("\n[Test] Loading Douyin Plugin...")
        plugin = PluginManager.get_login_plugin('douyin')
        self.assertIsNotNone(plugin, "Douyin plugin should be loaded")
        self.assertIsInstance(plugin, LoginPluginInterface, "Plugin must implement LoginPluginInterface")
        self.assertEqual(plugin.platform_id, 'douyin')
        self.assertEqual(plugin.platform_name, '抖音')
        print(f"  - Loaded: {plugin.platform_name} ({plugin.platform_id})")
        print(f"  - Login URL: {plugin.login_url}")

    def test_kuaishou_plugin_loader(self):
        """测试快手插件加载"""
        print("\n[Test] Loading Kuaishou Plugin...")
        plugin = PluginManager.get_login_plugin('kuaishou')
        self.assertIsNotNone(plugin, "Kuaishou plugin should be loaded")
        self.assertIsInstance(plugin, LoginPluginInterface)
        self.assertEqual(plugin.platform_id, 'kuaishou')
        print(f"  - Loaded: {plugin.platform_name} ({plugin.platform_id})")

    def test_xiaohongshu_plugin_loader(self):
        """测试小红书插件加载 (Pro)"""
        print("\n[Test] Loading Xiaohongshu Plugin (Pro)...")
        plugin = PluginManager.get_login_plugin('xiaohongshu')
        if os.path.exists(os.path.join(project_root, 'plugins_pro', 'plugins', 'xiaohongshu')):
             self.assertIsNotNone(plugin, "Xiaohongshu plugin should be loaded if directory exists")
             print(f"  - Loaded: {plugin.platform_name} ({plugin.platform_id})")
        else:
             print("  - Pro plugin directory not found, skipping check.")

    def test_wechat_video_plugin_loader(self):
        """测试视频号插件加载 (Pro)"""
        print("\n[Test] Loading Wechat Video Plugin (Pro)...")
        plugin = PluginManager.get_login_plugin('wechat_video')
        if os.path.exists(os.path.join(project_root, 'plugins_pro', 'plugins', 'wechat_video')):
             self.assertIsNotNone(plugin, "Wechat Video plugin should be loaded if directory exists")
             print(f"  - Loaded: {plugin.platform_name} ({plugin.platform_id})")
        else:
             print("  - Pro plugin directory not found, skipping check.")

    def test_invalid_plugin(self):
        """测试不存在的插件"""
        print("\n[Test] Loading Invalid Plugin...")
        plugin = PluginManager.get_login_plugin('invalid_platform_xyz')
        self.assertIsNone(plugin, "Invalid plugin should return None")
        print("  - Correctly returned None")

if __name__ == '__main__':
    unittest.main()
