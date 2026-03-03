"""
发布记录详情对话框
文件路径：src/ui/dialogs/publish_record_detail_dialog.py
功能：显示发布记录详细信息
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
import logging
import json

try:
    from qfluentwidgets import (
        Dialog, BodyLabel, SubtitleLabel, PushButton, ScrollArea
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class PublishRecordDetailDialog(Dialog if FLUENT_WIDGETS_AVAILABLE else QDialog):
    """发布记录详情对话框"""
    
    def __init__(self, record: Dict[str, Any], parent: Optional[QDialog] = None):
        """初始化发布记录详情对话框
        
        Args:
            record: 发布记录字典
            parent: 父对话框
        """
        if FLUENT_WIDGETS_AVAILABLE:
            super().__init__("发布记录详情", "", parent)
        else:
            super().__init__(parent)
            self.setWindowTitle("发布记录详情")
            self.setModal(True)
        
        self.record = record
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        if not FLUENT_WIDGETS_AVAILABLE:
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("详情功能需要Fluent Widgets支持", self))
            return
        
        layout = QVBoxLayout(self.viewLayout)
        layout.setSpacing(16)
        
        # 创建滚动区域
        scroll_area = ScrollArea(self)
        scroll_content = QDialog()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        
        # 基本信息
        self._add_section(scroll_layout, "基本信息", [
            ("记录ID", str(self.record.get('id', ''))),
            ("平台", self._get_platform_display(self.record.get('platform', ''))),
            ("账号", self.record.get('account_name', '')),
            ("文件类型", self.record.get('file_type', '')),
            ("状态", self._get_status_display(self.record.get('status', ''))),
            ("创建时间", self.record.get('created_at', '')),
            ("更新时间", self.record.get('updated_at', '') or '未更新'),
        ])
        
        # 文件信息
        self._add_section(scroll_layout, "文件信息", [
            ("文件路径", self.record.get('file_path', '')),
        ])
        
        # 发布内容
        self._add_section(scroll_layout, "发布内容", [
            ("标题", self.record.get('title', '') or '(无标题)'),
            ("描述", self.record.get('description', '') or '(无描述)'),
            ("标签", self._format_tags(self.record.get('tags'))),
        ])
        
        # 发布结果
        result_items = []
        if self.record.get('publish_url'):
            result_items.append(("发布链接", self.record.get('publish_url')))
        if self.record.get('error_message'):
            result_items.append(("错误信息", self.record.get('error_message')))
        
        if result_items:
            self._add_section(scroll_layout, "发布结果", result_items)
        
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 关闭按钮
        btn_close = PushButton("关闭", self)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def _add_section(self, layout: QVBoxLayout, title: str, items: list):
        """添加信息区块"""
        section_title = SubtitleLabel(title, self)
        layout.addWidget(section_title)
        
        for label, value in items:
            item_layout = QHBoxLayout()
            
            label_widget = BodyLabel(f"{label}:", self)
            label_widget.setMinimumWidth(100)
            item_layout.addWidget(label_widget)
            
            value_widget = BodyLabel(str(value), self)
            value_widget.setWordWrap(True)
            value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            item_layout.addWidget(value_widget, stretch=1)
            
            layout.addLayout(item_layout)
        
        layout.addSpacing(8)
    
    def _get_platform_display(self, platform: str) -> str:
        """获取平台显示名称"""
        platform_map = {
            'douyin': '抖音',
            'kuaishou': '快手',
            'xiaohongshu': '小红书'
        }
        return platform_map.get(platform, platform)
    
    def _get_status_display(self, status: str) -> str:
        """获取状态显示名称"""
        status_map = {
            'success': '✅ 成功',
            'failed': '❌ 失败',
            'pending': '⏳ 待发布'
        }
        return status_map.get(status, status)
    
    def _format_tags(self, tags_str: Optional[str]) -> str:
        """格式化标签"""
        if not tags_str:
            return '(无标签)'
        
        try:
            if isinstance(tags_str, str):
                tags = json.loads(tags_str)
            else:
                tags = tags_str
            
            if isinstance(tags, list):
                return ', '.join(tags) if tags else '(无标签)'
            else:
                return str(tags)
        except:
            return tags_str or '(无标签)'

