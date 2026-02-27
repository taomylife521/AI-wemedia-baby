# -*- coding: utf-8 -*-
"""
设置账号组对话框
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
)
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, BodyLabel, ComboBox, PrimaryPushButton, PushButton
)

class SetGroupDialog(MessageBoxBase):
    """设置账号组对话框"""
    
    def __init__(self, parent=None, current_group_id=None, groups=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("设置账号组", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.groups = groups or []
        self.current_group_id = current_group_id
        self.selected_group_id = None
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI"""
        # 下拉框选择分组
        self.group_combo = ComboBox(self)
        self.group_combo.setPlaceholderText("选择分分组")
        
        # 添加选项
        self.group_combo.addItem("未分类", userData=None)
        
        for group in self.groups:
            self.group_combo.addItem(group['group_name'], userData=group['id'])
            
        # 选中当前分组
        if self.current_group_id:
            for i in range(self.group_combo.count()):
                if self.group_combo.itemData(i) == self.current_group_id:
                    self.group_combo.setCurrentIndex(i)
                    break
        else:
            self.group_combo.setCurrentIndex(0)
            
        self.viewLayout.addWidget(self.group_combo)
        
        # 确定/取消按钮由 MessageBoxBase 提供 (yesButton, cancelButton)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(300)
        
    def validate(self):
        """验证并获取结果"""
        self.selected_group_id = self.group_combo.currentData()
        return True
