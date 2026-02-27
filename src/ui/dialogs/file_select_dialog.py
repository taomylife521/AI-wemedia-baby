"""
文件选择对话框
文件路径：src/ui/dialogs/file_select_dialog.py
功能：选择单个文件或文件夹
"""

from typing import Optional, List
from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox
import logging

try:
    from qfluentwidgets import MessageBox
    FLUENT_WIDGETS_AVAILABLE = True
except ImportError:
    FLUENT_WIDGETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileSelectDialog:
    """文件选择对话框 - 用于选择文件或文件夹"""
    
    @staticmethod
    def select_file(parent: Optional[QWidget] = None) -> Optional[str]:
        """选择单个视频文件
        
        Args:
            parent: 父窗口
        
        Returns:
            选中的文件路径，如果取消则返回None
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.flv *.mkv *.wmv *.m4v *.webm);;所有文件 (*.*)"
        )
        
        if file_path:
            return file_path
        return None
    
    @staticmethod
    def select_folder(parent: Optional[QWidget] = None) -> Optional[str]:
        """选择文件夹
        
        Args:
            parent: 父窗口
        
        Returns:
            选中的文件夹路径，如果取消则返回None
        """
        folder_path = QFileDialog.getExistingDirectory(
            parent,
            "选择视频文件夹"
        )
        
        if folder_path:
            return folder_path
        return None
    
    @staticmethod
    def select_files(parent: Optional[QWidget] = None) -> List[str]:
        """选择多个视频文件
        
        Args:
            parent: 父窗口
        
        Returns:
            选中的文件路径列表，如果取消则返回空列表
        """
        files, _ = QFileDialog.getOpenFileNames(
            parent,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.flv *.mkv *.wmv *.m4v *.webm);;所有文件 (*.*)"
        )
        
        return files if files else []

