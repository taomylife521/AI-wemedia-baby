"""
Cookie 管理器单元测试
测试范围：Cookie 加密/解密、格式验证、过期检查
"""
import pytest
from src.services.account.cookie_manager import CookieManager

class TestCookieManager:
    """Cookie 管理器测试类"""
    
    def test_cookie_encryption_decryption(self, sample_cookies):
        """测试 Cookie 加密和解密"""
        manager = CookieManager()
        
        # 加密
        encrypted = manager.encrypt_cookies(sample_cookies)
        assert encrypted is not None
        assert isinstance(encrypted, str)
        
        # 解密
        decrypted = manager.decrypt_cookies(encrypted)
        assert decrypted == sample_cookies
    
    def test_cookie_validation(self, sample_cookies):
        """测试 Cookie 格式验证"""
        manager = CookieManager()
        
        # 有效 Cookie
        assert manager.validate_cookies(sample_cookies) is True
        
        # 无效 Cookie（空字典）
        assert manager.validate_cookies({}) is False
        
        # 无效 Cookie（None）
        assert manager.validate_cookies(None) is False
    
    def test_cookie_expiry_check(self):
        """测试 Cookie 过期检查"""
        manager = CookieManager()
        
        # 未过期的 Cookie
        valid_cookie = {"sessionid": "valid_session", "expires": "2099-12-31"}
        assert manager.is_expired(valid_cookie) is False
        
        # 已过期的 Cookie
        expired_cookie = {"sessionid": "expired_session", "expires": "2020-01-01"}
        assert manager.is_expired(expired_cookie) is True
