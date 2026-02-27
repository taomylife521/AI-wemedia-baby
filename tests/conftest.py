# pytest 配置文件
import pytest
import asyncio
from pathlib import Path
import sys

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置 asyncio 事件循环
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 配置测试数据库
@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """创建临时测试数据库"""
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    return str(db_path)

# 配置测试账号数据
@pytest.fixture
def sample_account():
    """示例账号数据"""
    return {
        "id": 1,
        "platform": "douyin",
        "platform_username": "测试账号",
        "login_status": "valid",
        "cookie_data": {"sessionid": "test_session_123"}
    }

# 配置测试 Cookie 数据
@pytest.fixture
def sample_cookies():
    """示例 Cookie 数据"""
    return {
        "sessionid": "test_session_id",
        "sessionid_ss": "test_session_ss",
        "sid_tt": "test_sid_tt"
    }
