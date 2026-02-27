"""
账号服务单元测试
测试范围：账号添加、删除、查询
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.account.account_service import AccountService

class TestAccountService:
    """账号服务测试类"""
    
    @pytest.fixture
    def mock_data_storage(self):
        """模拟数据存储"""
        storage = MagicMock()
        storage.add_account = AsyncMock(return_value=1)
        storage.delete_account = AsyncMock(return_value=True)
        storage.get_accounts = AsyncMock(return_value=[])
        return storage
    
    @pytest.mark.asyncio
    async def test_add_account(self, mock_data_storage, sample_account):
        """测试添加账号"""
        service = AccountService(mock_data_storage)
        
        account_id = await service.add_account(
            platform="douyin",
            platform_username="测试账号",
            cookie_data={"sessionid": "test"}
        )
        
        assert account_id == 1
        mock_data_storage.add_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_account(self, mock_data_storage):
        """测试删除账号"""
        service = AccountService(mock_data_storage)
        
        result = await service.delete_account(account_id=1)
        
        assert result is True
        mock_data_storage.delete_account.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_accounts(self, mock_data_storage, sample_account):
        """测试查询账号列表"""
        mock_data_storage.get_accounts.return_value = [sample_account]
        service = AccountService(mock_data_storage)
        
        accounts = await service.get_accounts()
        
        assert len(accounts) == 1
        assert accounts[0]["platform_username"] == "测试账号"
