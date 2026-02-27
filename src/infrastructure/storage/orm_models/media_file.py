"""
媒体文件表 ORM 模型
对应数据库表：media_files
"""

from tortoise import fields
from tortoise.models import Model


class MediaFile(Model):
    """媒体文件表 ORM 模型

    字段说明：
        id: 主键ID（自增）
        user: 关联用户（外键）
        file_path: 文件路径（唯一）
        file_name: 文件名
        file_type: 文件类型（video/image）
        file_size: 文件大小（字节）
        duration: 时长（秒，可选）
        resolution: 分辨率（可选）
        width: 宽度（可选）
        height: 高度（可选）
        has_script: 是否有脚本（0/1）
        script_path: 脚本路径（可选）
        created_at: 创建时间（自动填充）
        updated_at: 更新时间（可选）
    """

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="media_files", on_delete=fields.CASCADE
    )
    file_path = fields.CharField(max_length=1000, unique=True)
    file_name = fields.CharField(max_length=500)
    file_type = fields.CharField(max_length=20)
    file_size = fields.IntField()
    duration = fields.FloatField(null=True)
    resolution = fields.CharField(max_length=50, null=True)
    width = fields.IntField(null=True)
    height = fields.IntField(null=True)
    has_script = fields.BooleanField(default=False)
    script_path = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(null=True)

    class Meta:
        table = "media_files"

    def __str__(self):
        return f"MediaFile(id={self.id}, name={self.file_name}, type={self.file_type})"
