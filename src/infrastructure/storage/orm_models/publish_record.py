"""
发布记录表 ORM 模型
对应数据库表：publish_records
"""

from tortoise import fields
from tortoise.models import Model


class PublishRecord(Model):
    """发布记录表 ORM 模型

    字段说明：
        id: 主键ID（自增）
        user: 关联用户（外键）
        platform_username: 平台账号昵称
        platform: 平台名称
        file_path: 文件路径
        file_type: 文件类型（video/image）
        title: 标题（可选）
        description: 描述（可选）
        tags: 标签（可选）
        cover_path: 封面路径（可选）
        poi_info: 位置信息（可选）
        micro_app_info: 小程序信息（可选）
        goods_info: 商品信息（可选）
        anchor_info: 锚点信息（可选）
        privacy_settings: 隐私设置（可选）
        scheduled_publish_time: 定时发布时间（可选）
        status: 发布状态（pending/running/success/failed）
        error_message: 错误信息（可选）
        publish_url: 发布链接（可选）
        created_at: 创建时间（自动填充）
        updated_at: 更新时间（可选）
    """

    id = fields.IntField(pk=True)
    # 使用普通整数字段存储用户ID（兼容旧数据，不强制外键约束）
    user_id = fields.IntField()
    platform_username = fields.CharField(max_length=200)
    platform = fields.CharField(max_length=50)
    file_path = fields.TextField()
    file_type = fields.CharField(max_length=20)
    title = fields.TextField(null=True)
    description = fields.TextField(null=True)
    tags = fields.TextField(null=True)
    cover_path = fields.TextField(null=True)
    poi_info = fields.TextField(null=True)
    micro_app_info = fields.TextField(null=True)
    goods_info = fields.TextField(null=True)
    anchor_info = fields.TextField(null=True)
    privacy_settings = fields.TextField(null=True)
    scheduled_publish_time = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=20)
    error_message = fields.TextField(null=True)
    publish_url = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(null=True)

    class Meta:
        table = "publish_records"

    def __str__(self):
        return f"PublishRecord(id={self.id}, platform={self.platform}, status={self.status})"
