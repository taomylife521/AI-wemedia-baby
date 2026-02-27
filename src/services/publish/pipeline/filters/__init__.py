"""
发布管道过滤器模块
"""

# 异步版本 (新架构)
from .permission_check_filter_async import PermissionCheckFilterAsync
from .media_validate_filter_async import MediaValidateFilterAsync
from .account_load_filter_async import AccountLoadFilterAsync
from .platform_publish_filter_async import PlatformPublishFilterAsync
from .record_save_filter_async import RecordSaveFilterAsync

# 兼容性别名
PermissionCheckFilter = PermissionCheckFilterAsync
MediaValidateFilter = MediaValidateFilterAsync
AccountLoadFilter = AccountLoadFilterAsync
PlatformPublishFilter = PlatformPublishFilterAsync
RecordSaveFilter = RecordSaveFilterAsync

__all__ = [
    'PermissionCheckFilterAsync',
    'MediaValidateFilterAsync',
    'AccountLoadFilterAsync',
    'PlatformPublishFilterAsync',
    'RecordSaveFilterAsync',
    # 兼容性别名
    'PermissionCheckFilter',
    'MediaValidateFilter',
    'AccountLoadFilter',
    'PlatformPublishFilter',
    'RecordSaveFilter',
]
