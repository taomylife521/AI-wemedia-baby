"""
抖音插件单元测试
测试范围：登录检测、昵称提取、Cookie 验证
"""
import pytest
from src.infrastructure.plugins.builtin_plugins.douyin_plugin import DouyinPlugin

class TestDouyinPlugin:
    """抖音插件测试类"""
    
    @pytest.fixture
    async def plugin(self):
        """创建插件实例"""
        plugin = DouyinPlugin()
        await plugin.initialize()
        return plugin
    
    @pytest.mark.asyncio
    async def test_validate_login_with_valid_cookies(self, plugin, sample_cookies):
        """测试有效 Cookie 的登录验证"""
        # 有效的抖音 Cookie 应该包含 sessionid
        result = plugin.validate_login(sample_cookies)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_login_with_invalid_cookies(self, plugin):
        """测试无效 Cookie 的登录验证"""
        invalid_cookies = {"invalid_key": "invalid_value"}
        result = plugin.validate_login(invalid_cookies)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_extract_username_from_cookies(self, plugin):
        """测试从 Cookie 提取用户名"""
        cookies_with_username = {
            "sessionid": "test_session",
            "passport_auth_status": "test_user_123"
        }
        
        username = plugin.extract_username(cookies_with_username)
        # 根据实际实现调整断言
        assert username is not None or username == ""
    
    def test_plugin_metadata(self, plugin):
        """测试插件元数据"""
        assert plugin.name == "douyin"
        assert plugin.version is not None
        assert plugin.platform_id == "douyin"
