"""
指纹配置对话框
文件路径:src/ui/account/fingerprint_config_dialog.py
功能:添加账号时配置浏览器指纹参数(中国专用版)
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import logging

try:
    from qfluentwidgets import (
        MessageBoxBase, SubtitleLabel, BodyLabel, 
        RadioButton, ComboBox
    )
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


# 固定参数(中国专用)
FIXED_CHINA_CONFIG = {
    "timezone_id": "Asia/Shanghai",
    "locale": "zh-CN",
    "languages": ["zh-CN", "zh", "en"],
}

# 可自定义的参数选项
CUSTOMIZABLE_OPTIONS = {
    "screen_resolution": [
        {"name": "1920x1080 (全高清)", "width": 1920, "height": 1080},
        {"name": "2560x1440 (2K)", "width": 2560, "height": 1440},
        {"name": "1366x768 (笔记本)", "width": 1366, "height": 768},
        {"name": "1536x864 (笔记本)", "width": 1536, "height": 864},
        {"name": "3840x2160 (4K)", "width": 3840, "height": 2160},
    ],
    "hardware_concurrency": [4, 8, 12, 16],
    "device_memory": [4, 8, 16, 32],
    "user_agent_platform": [
        {"name": "Windows 10", "value": "Win32"},
        {"name": "Windows 11", "value": "Win32"},
        {"name": "MacOS", "value": "MacIntel"},
    ],
    "webgl_vendor": [
        {"name": "Intel", "value": "Intel Inc."},
        {"name": "NVIDIA", "value": "NVIDIA Corporation"},
        {"name": "AMD", "value": "AMD"},
        {"name": "Apple", "value": "Apple Inc."},
    ],
    "canvas_noise": [
        {"name": "低噪声", "value": 0.0001},
        {"name": "中噪声", "value": 0.0003},
        {"name": "高噪声", "value": 0.0005},
    ],
}


class FingerprintConfigMessageBox(MessageBoxBase):
    """指纹配置对话框(中国专用版)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "random"  # random 或 custom
        self.custom_config = {}
        
        # 设置标题
        self.titleLabel = SubtitleLabel("配置浏览器指纹", self.widget)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 调整大小
        self.widget.setMinimumWidth(500)
        
        self._setup_content()
        
        # 设置按钮
        self.yesButton.setText("确定")
        self.cancelButton.setText("上一步")
        
        # 移除遮罩背景
        self.setMaskColor(QColor(0, 0, 0, 0))
        
        # 统一底部背景颜色
        self.buttonGroup.setStyleSheet("background-color: transparent; border-top: 1px solid #EDEDED;")
        
        # 调整按钮顺序
        button_layout = self.buttonGroup.layout()
        if button_layout:
            button_layout.removeWidget(self.yesButton)
            button_layout.removeWidget(self.cancelButton)
            button_layout.addWidget(self.cancelButton)
            button_layout.addWidget(self.yesButton)
        
        # 按钮样式
        self.yesButton.setStyleSheet("""
            QPushButton {
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 14px;
            }
        """)
        self.cancelButton.setStyleSheet("""
            QPushButton {
                border: 1px solid #EDEDED;
                border-radius: 5px;
                background-color: #FFFFFF;
                padding: 6px 12px;
                font-size: 14px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #EEEEEE;
            }
        """)
    
    def showEvent(self, e):
        """显示时再次强制设置透明背景"""
        super().showEvent(e)
        self.setMaskColor(QColor(0, 0, 0, 0))
    
    def _setup_content(self):
        """设置内容区域"""
        # 模式选择
        self.random_radio = RadioButton("随机生成 (推荐)", self.widget)
        self.random_radio.setChecked(True)
        self.random_radio.clicked.connect(self._on_mode_changed)  # 使用clicked信号
        
        self.viewLayout.addWidget(self.random_radio)
        self.viewLayout.addSpacing(5)
        
        # 随机生成提示
        tip_label = BodyLabel("自动生成随机指纹参数", self.widget)
        tip_label.setTextColor('#999999', '#999999')
        self.viewLayout.addWidget(tip_label)
        
        self.viewLayout.addSpacing(20)
        
        # 自定义配置选项
        self.custom_radio = RadioButton("自定义配置", self.widget)
        self.custom_radio.clicked.connect(self._on_mode_changed)  # 使用clicked信号
        self.viewLayout.addWidget(self.custom_radio)
        
        self.viewLayout.addSpacing(10)
        
        # 自定义配置区域
        self._create_custom_config_area()
        
        # 固定参数提示
        self.viewLayout.addSpacing(15)
        fixed_tip = BodyLabel("提示: 时区和语言已固定为中国大陆", self.widget)
        fixed_tip.setTextColor('#666666', '#666666')
        self.viewLayout.addWidget(fixed_tip)
        
        self.viewLayout.addSpacing(10)
    
    def _create_custom_config_area(self):
        """创建自定义配置区域"""
        self.custom_area = QWidget(self.widget)
        # 使用网格布局优化空间利用
        from PySide6.QtWidgets import QGridLayout, QPushButton
        custom_layout = QGridLayout(self.custom_area)
        custom_layout.setContentsMargins(20, 0, 0, 0)
        custom_layout.setVerticalSpacing(15)
        custom_layout.setHorizontalSpacing(20)
        
        # 存储选项数据
        self.options_data = {}
        
        # --- 第一列 ---
        
        # 1. 屏幕分辨率
        custom_layout.addWidget(BodyLabel("屏幕分辨率:", self.custom_area), 0, 0)
        self.resolution_combo = ComboBox(self.custom_area)
        self.options_data["resolution"] = CUSTOMIZABLE_OPTIONS["screen_resolution"]
        for res in self.options_data["resolution"]:
            self.resolution_combo.addItem(res["name"])
        self.resolution_combo.setCurrentIndex(0)
        custom_layout.addWidget(self.resolution_combo, 0, 1)
        
        # 2. CPU核心数
        custom_layout.addWidget(BodyLabel("CPU核心数:", self.custom_area), 1, 0)
        self.cpu_combo = ComboBox(self.custom_area)
        self.options_data["cpu"] = CUSTOMIZABLE_OPTIONS["hardware_concurrency"]
        for cpu in self.options_data["cpu"]:
            self.cpu_combo.addItem(f"{cpu}核")
        self.cpu_combo.setCurrentIndex(1)
        custom_layout.addWidget(self.cpu_combo, 1, 1)
        
        # 3. 内存
        custom_layout.addWidget(BodyLabel("内存:", self.custom_area), 2, 0)
        self.memory_combo = ComboBox(self.custom_area)
        self.options_data["memory"] = CUSTOMIZABLE_OPTIONS["device_memory"]
        for mem in self.options_data["memory"]:
            self.memory_combo.addItem(f"{mem}GB")
        self.memory_combo.setCurrentIndex(2)
        custom_layout.addWidget(self.memory_combo, 2, 1)
        
        # --- 第二列 ---
        
        # 4. 操作系统平台
        custom_layout.addWidget(BodyLabel("操作系统平台:", self.custom_area), 0, 2)
        self.platform_combo = ComboBox(self.custom_area)
        self.options_data["platform"] = CUSTOMIZABLE_OPTIONS["user_agent_platform"]
        for p in self.options_data["platform"]:
            self.platform_combo.addItem(p["name"])
        self.platform_combo.setCurrentIndex(0)
        custom_layout.addWidget(self.platform_combo, 0, 3)
        
        # 5. 显卡供应商
        custom_layout.addWidget(BodyLabel("显卡供应商:", self.custom_area), 1, 2)
        self.webgl_combo = ComboBox(self.custom_area)
        self.options_data["webgl"] = CUSTOMIZABLE_OPTIONS["webgl_vendor"]
        for v in self.options_data["webgl"]:
            self.webgl_combo.addItem(v["name"])
        self.webgl_combo.setCurrentIndex(0)
        custom_layout.addWidget(self.webgl_combo, 1, 3)
        
        # 6. Canvas噪声
        custom_layout.addWidget(BodyLabel("Canvas噪声强度:", self.custom_area), 2, 2)
        self.canvas_combo = ComboBox(self.custom_area)
        self.options_data["canvas"] = CUSTOMIZABLE_OPTIONS["canvas_noise"]
        for c in self.options_data["canvas"]:
            self.canvas_combo.addItem(c["name"])
        self.canvas_combo.setCurrentIndex(1)
        custom_layout.addWidget(self.canvas_combo, 2, 3)
        
        # --- 底部操作栏 ---
        
        # 恢复默认按钮
        if FLUENT_WIDGETS_AVAILABLE:
            from qfluentwidgets import PushButton
            self.reset_btn = PushButton("恢复默认", self.custom_area)
        else:
            self.reset_btn = QPushButton("恢复默认", self.custom_area)
            
        self.reset_btn.setFixedWidth(100)
        self.reset_btn.clicked.connect(self._reset_to_default)
        custom_layout.addWidget(self.reset_btn, 3, 0)

        self.custom_area.setEnabled(False)  # 初始禁用
        self.viewLayout.addWidget(self.custom_area)
        
    def _reset_to_default(self):
        """恢复默认设置"""
        self.resolution_combo.setCurrentIndex(0)
        self.cpu_combo.setCurrentIndex(1)
        self.memory_combo.setCurrentIndex(2) 
        self.platform_combo.setCurrentIndex(0)
        self.webgl_combo.setCurrentIndex(0)
        self.canvas_combo.setCurrentIndex(1)
        
        if FLUENT_WIDGETS_AVAILABLE:
            from qfluentwidgets import InfoBar
            InfoBar.success(
                title='已恢复默认',
                content="自定义配置已重置为默认推荐值",
                parent=self,
                duration=2000
            )
    
    def _on_mode_changed(self):
        """模式切换"""
        if self.random_radio.isChecked():
            self.mode = "random"
            self.custom_area.setEnabled(False)
            logger.info("切换到随机生成模式")
        else:
            self.mode = "custom"
            self.custom_area.setEnabled(True)
            logger.info("切换到自定义配置模式")
        
        # 强制刷新UI
        self.custom_area.update()
    
    def get_fingerprint_config(self) -> Optional[Dict[str, Any]]:
        """获取指纹配置"""
        if self.mode == "random":
            logger.info("用户选择随机生成指纹")
            return None
        
        # 获取当前选中的索引
        res_idx = self.resolution_combo.currentIndex()
        cpu_idx = self.cpu_combo.currentIndex()
        mem_idx = self.memory_combo.currentIndex()
        plat_idx = self.platform_combo.currentIndex()
        webgl_idx = self.webgl_combo.currentIndex()
        canvas_idx = self.canvas_combo.currentIndex()
        
        # 从本地数据中检索
        resolution = self.options_data["resolution"][res_idx]
        cpu = self.options_data["cpu"][cpu_idx]
        memory = self.options_data["memory"][mem_idx]
        platform = self.options_data["platform"][plat_idx]
        webgl = self.options_data["webgl"][webgl_idx]
        canvas = self.options_data["canvas"][canvas_idx]
        
        config = {
            "screen_width": resolution["width"],
            "screen_height": resolution["height"],
            "hardware_concurrency": cpu,
            "device_memory": memory,
            "platform": platform["value"],
            "webgl_vendor": webgl["value"],
            "canvas_noise": canvas["value"],
            # 固定参数
            **FIXED_CHINA_CONFIG
        }
        
        logger.info(f"用户自定义指纹: {resolution['name']}, {cpu}核, {memory}GB, {platform['name']}, {webgl['name']}")
        return config
