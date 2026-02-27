
import os
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.common.path_manager import PathManager
from src.infrastructure.browser.profile_manager import ProfileManager
from src.services.account.cookie_manager import CookieManager

def test_directory_structure():
    print("Testing Directory Structure...")
    
    platform = "test_platform"
    platform_username = "test_account_001"
    
    # 1. Test PathManager
    base_dir = PathManager.get_platform_account_dir(platform, platform_username)
    print(f"Base Dir: {base_dir}")
    
    assert base_dir.name == platform_username
    assert base_dir.parent.name == platform
    assert base_dir.parent.parent.name == "data"
    assert "WeMediaBaby" in str(base_dir)
    
    if base_dir.exists():
        shutil.rmtree(base_dir)
        print("Cleaned up existing test dir")
    
    base_dir = PathManager.get_platform_account_dir(platform, platform_username)
    assert base_dir.exists()
    print("✓ PathManager.get_platform_account_dir created directory successfully")

    # 2. Test ProfileManager
    pm = ProfileManager("acc_123", platform, platform_username)
    print(f"ProfileManager Base Dir: {pm.base_dir}")
    
    assert pm.base_dir == base_dir / "browser"
    assert pm.base_dir.exists()
    print("✓ ProfileManager created browser directory successfully")
    
    # 3. Test CookieManager Path
    # We need a dummy user_id for CookieManager init, but we are testing static method or instance method that uses passed params
    # Actually CookieManager.get_cookie_path is an instance method usually but we updated it to use params
    
    # Mocking AccountRepository for CookieManager if needed, or just instantiating if dependencies are loose
    # CookieManager takes (user_id, data_storage, file_storage)
    # But get_cookie_path only uses self.user_id for LEGACY path. 
    # WAIT, I updated get_cookie_path to NOT use self.user_id anymore.
    
    class MockCookieManager(CookieManager):
        def __init__(self):
            self.user_id = 999
            self.logger = type('Logger', (), {'warning': print, 'info': print, 'error': print})
            
    cm = MockCookieManager()
    cookie_path = cm.get_cookie_path(platform_username, platform)
    print(f"Cookie Path: {cookie_path}")
    
    expected_cookie_path = base_dir / "backup.encrypted"
    assert Path(cookie_path) == expected_cookie_path
    print("✓ CookieManager.get_cookie_path returns correct path")
    
    # Cleanup
    shutil.rmtree(base_dir.parent) # remove test_platform dir
    print("\nAll directory structure tests passed!")

if __name__ == "__main__":
    test_directory_structure()
