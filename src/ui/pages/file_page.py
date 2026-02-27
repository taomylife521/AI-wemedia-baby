"""
文件管理页面
文件路径：src/ui/pages/file_page.py
功能：文件管理页面，显示和管理媒体文件
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont
import logging
import os

from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
    TableWidget, LineEdit, FluentIcon, MessageBox, InfoBar, InfoBarPosition,
    IconWidget
)
FLUENT_WIDGETS_AVAILABLE = True

from .base_page import BasePage
from ..dialogs.file_select_dialog import FileSelectDialog
from ..dialogs.script_view_dialog import ScriptViewDialog

logger = logging.getLogger(__name__)


class FileProcessWorker(QThread):
    """文件处理工作线程"""
    
    progress = Signal(str)  # 进度消息
    finished = Signal(dict)  # 完成信号，传递结果字典
    
    def __init__(self, file_manager, file_paths: List[str], is_folder: bool = False):
        """初始化工作线程
        
        Args:
            file_manager: 文件管理器实例
            file_paths: 文件路径列表
            is_folder: 是否为文件夹模式
        """
        super().__init__()
        self.file_manager = file_manager
        self.file_paths = file_paths
        self.is_folder = is_folder
    
    def run(self):
        """执行文件处理"""
        try:
            all_results = []
            total = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths):
                self.progress.emit(f"正在处理: {os.path.basename(file_path)} ({i+1}/{total})")
                
                if self.is_folder:
                    # 文件夹模式：使用 add_folder
                    folder_result = self.file_manager.add_folder(file_path)
                    # add_folder 返回的结果中包含 results 字段，需要展开
                    if folder_result.get('success') and 'results' in folder_result:
                        # 展开文件夹中的文件结果
                        all_results.extend(folder_result['results'])
                    else:
                        # 如果失败，也记录结果
                        all_results.append({
                            'file_path': file_path,
                            'file_name': os.path.basename(file_path),
                            'success': False,
                            'message': folder_result.get('message', '处理失败')
                        })
                else:
                    # 单文件模式：使用 add_file
                    result = self.file_manager.add_file(file_path)
                    all_results.append({
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path),
                        **result
                    })
            
            self.finished.emit({
                'success': True,
                'results': all_results
            })
        except Exception as e:
            logger.error(f"文件处理失败: {e}", exc_info=True)
            self.finished.emit({
                'success': False,
                'error': str(e)
            })


class FileRefreshWorker(QThread):
    """文件刷新工作线程"""
    
    progress = Signal(str, int, int)  # 进度消息, 当前数量, 总数量
    finished = Signal(dict)  # 完成信号，传递结果字典
    
    def __init__(self, file_manager):
        """初始化刷新工作线程
        
        Args:
            file_manager: 文件管理器实例
        """
        super().__init__()
        self.file_manager = file_manager
    
    def run(self):
        """执行文件刷新"""
        try:
            # 获取所有文件
            files = self.file_manager.get_files()
            total = len(files)
            
            if total == 0:
                self.finished.emit({
                    'success': True,
                    'message': "没有需要刷新的文件",
                    'refreshed_count': 0
                })
                return
            
            # 定义进度回调
            def progress_callback(message, current, total_count):
                self.progress.emit(message, current, total_count)
            
            # 执行刷新（带进度回调）
            result = self.file_manager.refresh_all_files(progress_callback=progress_callback)
            
            # 发送完成信号
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"文件刷新失败: {e}", exc_info=True)
            self.finished.emit({
                'success': False,
                'message': f"刷新失败: {str(e)}",
                'refreshed_count': 0
            })


class FilePage(BasePage):
    """文件管理页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """初始化文件管理页面"""
        super().__init__("文件管理", parent)
        self.user_id = 1  # 默认用户ID，实际应该从登录状态获取
        self.file_manager = None
        self.worker = None  # 工作线程
        self.refresh_worker = None  # 刷新工作线程
        self.btn_refresh = None  # 刷新按钮引用
        self._init_services()
        self._setup_content()
        # 延迟加载文件列表，确保UI已完全初始化
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._load_files)
    
    def _init_services(self):
        """初始化服务"""
        try:
            from src.infrastructure.common.di.service_locator import ServiceLocator
            from src.infrastructure.storage.file_storage import AsyncFileStorage
            from src.infrastructure.common.event.event_bus import EventBus
            
            # 导入异步版本的 FileManager
            try:
                from src.services.file.file_manager_async import FileManagerAsync
                FILE_MANAGER_AVAILABLE = True
            except ImportError:
                FILE_MANAGER_AVAILABLE = False
                logger.warning("FileManagerAsync 模块不可用，文件管理功能受限")
            
            service_locator = ServiceLocator()
            
            if FILE_MANAGER_AVAILABLE:
                file_storage = service_locator.get(AsyncFileStorage)
                event_bus = service_locator.get(EventBus)
                
                # 创建文件管理器（异步版本）
                self.file_manager = FileManagerAsync(
                    user_id=self.user_id,
                    file_storage=file_storage,
                    event_bus=event_bus
                )
                self._is_async = True
                logger.info("文件管理器初始化成功（异步版本）")
            else:
                logger.warning("FileManagerAsync 不可用，文件管理功能受限")
        except Exception as e:
            logger.error(f"初始化文件管理器失败: {e}", exc_info=True)
    
    def _setup_content(self):
        """设置内容"""

        
        # 1. 操作按钮区域 (使用 CardWidget 包裹)
        header_card = CardWidget(self)
        header_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header_card.setFixedHeight(80)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)
        
        btn_add_file = PrimaryPushButton(FluentIcon.ADD, "添加文件", header_card)
        btn_add_file.clicked.connect(self._on_add_file)
        
        btn_add_folder = PushButton(FluentIcon.FOLDER_ADD, "添加文件夹", header_card)
        btn_add_folder.clicked.connect(self._on_add_folder)
        
        self.btn_refresh = PushButton(FluentIcon.SYNC, "刷新", header_card)
        self.btn_refresh.clicked.connect(self._on_refresh)
        
        btn_delete = PushButton(FluentIcon.DELETE, "批量删除", header_card)
        btn_delete.clicked.connect(self._on_batch_delete)
        
        header_layout.addWidget(btn_add_file)
        header_layout.addWidget(btn_add_folder)
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(btn_delete)
        header_layout.addStretch()
        
        # 搜索框
        header_layout.addWidget(BodyLabel("搜索:", header_card))
        self.search_input = LineEdit(header_card)
        self.search_input.setPlaceholderText("输入文件名搜索...")
        self.search_input.setFixedWidth(250)
        from ..utils.debounce_throttle import Debouncer
        self.search_debouncer = Debouncer(300, self._on_search)
        self.search_input.textChanged.connect(
            lambda text: self.search_debouncer.call(text)
        )
        header_layout.addWidget(self.search_input)
        
        self.content_layout.addWidget(header_card)
        
        # 2. 内容区域 (使用单一 CardWidget 包裹表格和空状态)
        self.content_container = CardWidget(self)
        self.content_layout_inner = QVBoxLayout(self.content_container)
        self.content_layout_inner.setContentsMargins(0, 0, 0, 0)
        
        # 表格
        self._setup_file_table(self.content_container)
        self.content_layout_inner.addWidget(self.file_table)
        
        # 空状态
        self.empty_widget = self._create_empty_widget()
        self.content_layout_inner.addWidget(self.empty_widget)
        
        # 初始状态：显示表格（如果为空会在 _load_files 中调整）
        self.file_table.setVisible(True)
        self.empty_widget.setVisible(False)
        
        self.content_layout.addWidget(self.content_container)
        
    def _create_empty_widget(self) -> QWidget:
        """创建空状态组件"""
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        icon_widget = IconWidget(FluentIcon.FOLDER, widget)
        icon_widget.setFixedSize(64, 64)
        layout.addWidget(icon_widget, 0, Qt.AlignCenter)
        
        empty_label = SubtitleLabel("暂无视频文件", widget)
        empty_desc = BodyLabel("添加视频文件后即可在这里进行管理和脚本编辑", widget)
        empty_label.setAlignment(Qt.AlignCenter)
        empty_desc.setAlignment(Qt.AlignCenter)
        
        btn_add = PrimaryPushButton("立即添加文件", widget)
        btn_add.setFixedWidth(160)
        btn_add.clicked.connect(self._on_add_file)
        
        layout.addWidget(empty_label)
        layout.addWidget(empty_desc)
        layout.addSpacing(8)
        layout.addWidget(btn_add, 0, Qt.AlignCenter)
        
        return widget
    
    def _setup_file_table(self, parent):
        """设置文件列表表格"""
        self.file_table = TableWidget(parent)
        self._setup_table_style(self.file_table)
        # 移除圆角，因为外层已经是 CardWidget 了
        self.file_table.setBorderRadius(0)
        self.file_table.setBorderVisible(False)
        
        self.file_table.setColumnCount(7)
        self.file_table.setHorizontalHeaderLabels([
            "文件名", "文件大小", "时长", "分辨率", "方向", "是否有脚本", "操作"
        ])
        
        self.file_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 启用多选
        
        # 设置列宽
        self.file_table.setColumnWidth(0, 350)  # 文件名
        self.file_table.setColumnWidth(1, 100)  # 文件大小
        self.file_table.setColumnWidth(2, 100)  # 时长
        self.file_table.setColumnWidth(3, 120)  # 分辨率
        self.file_table.setColumnWidth(4, 80)   # 方向
        self.file_table.setColumnWidth(5, 100)  # 是否有脚本
        
        self.file_table.setVisible(True)
    
    def _load_files(self, search_keyword: Optional[str] = None):
        """加载文件列表（使用异步工作器）
        
        Args:
            search_keyword: 搜索关键词
        """
        if not self.file_manager:
            logger.warning("文件管理器未初始化，无法加载文件列表")
            return
        
        try:
            from ..utils.async_helper import AsyncWorker
            
            async def load_files_async():
                return await self.file_manager.get_files(search_keyword=search_keyword)
            
            worker = AsyncWorker(load_files_async)
            worker.finished.connect(self._on_files_loaded)
            worker.error.connect(self._on_files_load_error)
            worker.setParent(self)
            worker.start()
            
        except Exception as e:
            logger.error(f"加载文件列表失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载文件列表失败: {str(e)}")
    
    def _on_files_loaded(self, files):
        """文件列表加载完成回调"""
        try:
            logger.info(f"加载到 {len(files)} 个文件")
            self._update_file_table(files)
            
            # 显示/隐藏空状态（只切换内部组件，不隐藏外部容器）
            if len(files) == 0:
                self.file_table.setVisible(False)
                if hasattr(self, 'empty_widget'):
                    self.empty_widget.setVisible(True)
            else:
                self.file_table.setVisible(True)
                if hasattr(self, 'empty_widget'):
                    self.empty_widget.setVisible(False)
        except Exception as e:
            logger.error(f"更新文件列表失败: {e}", exc_info=True)
    
    def _on_files_load_error(self, error: str):

        """文件列表加载错误回调"""
        logger.error(f"加载文件列表失败: {error}")
        QMessageBox.warning(self, "错误", f"加载文件列表失败: {error}")
    
    def _find_row_by_file_id(self, file_id: int) -> Optional[int]:
        """根据文件ID查找表格中的行号
        
        Args:
            file_id: 文件记录ID
        
        Returns:
            行号，如果未找到返回None
        """
        for row in range(self.file_table.rowCount()):
            name_item = self.file_table.item(row, 0)
            if name_item:
                item_file_id = name_item.data(Qt.UserRole)
                if item_file_id == file_id:
                    return row
        return None
    
    def _update_table_row(self, row: int, file_record: Dict[str, Any]):
        """更新表格中的单行数据（性能优化）
        
        Args:
            row: 行号
            file_record: 文件记录
        """
        from ...utils.video_metadata import format_duration
        from ...utils.file_utils import format_file_size
        
        file_id = file_record.get('id')
        file_name = file_record.get('file_name', '')
        
        # 文件名（保持原有的 file_id 数据）
        name_item = self.file_table.item(row, 0)
        if name_item:
            name_item.setText(file_name)
            name_item.setData(Qt.UserRole, file_id)
        else:
            name_item = QTableWidgetItem(file_name)
            name_item.setData(Qt.UserRole, file_id)
            self.file_table.setItem(row, 0, name_item)
        
        # 文件大小
        file_size = file_record.get('file_size', 0)
        size_str = format_file_size(file_size)
        size_item = self.file_table.item(row, 1)
        if size_item:
            size_item.setText(size_str)
        else:
            self.file_table.setItem(row, 1, QTableWidgetItem(size_str))
        
        # 时长
        duration = file_record.get('duration')
        if duration is not None and duration != '':
            try:
                duration_float = float(duration)
                duration_str = format_duration(duration_float)
            except (ValueError, TypeError):
                duration_str = "未知"
        else:
            duration_str = "未知"
        duration_item = self.file_table.item(row, 2)
        if duration_item:
            duration_item.setText(duration_str)
        else:
            self.file_table.setItem(row, 2, QTableWidgetItem(duration_str))
        
        # 分辨率
        resolution = file_record.get('resolution')
        width = file_record.get('width')
        height = file_record.get('height')
        if resolution is None or resolution == '' or str(resolution) == 'None':
            if width is not None and width != '' and height is not None and height != '':
                try:
                    resolution = f"{int(width)}x{int(height)}"
                except (ValueError, TypeError):
                    resolution = "未知"
            else:
                resolution = "未知"
        else:
            resolution = str(resolution)
        resolution_item = self.file_table.item(row, 3)
        if resolution_item:
            resolution_item.setText(resolution)
        else:
            self.file_table.setItem(row, 3, QTableWidgetItem(resolution))
        
        # 方向
        orientation = "未知"
        if width is not None and height is not None:
            try:
                w = int(width)
                h = int(height)
                if w > h:
                    orientation = "横屏"
                elif h > w:
                    orientation = "竖屏"
                else:
                    orientation = "方形"
            except (ValueError, TypeError):
                pass
        orientation_item = self.file_table.item(row, 4)
        if orientation_item:
            orientation_item.setText(orientation)
        else:
            self.file_table.setItem(row, 4, QTableWidgetItem(orientation))
        
        # 是否有脚本
        has_script = file_record.get('has_script', 0)
        script_text = "是" if has_script else "否"
        script_item = self.file_table.item(row, 5)
        if script_item:
            script_item.setText(script_text)
        else:
            self.file_table.setItem(row, 5, QTableWidgetItem(script_text))
    
    def _update_file_table(self, files: List[Dict[str, Any]]):
        """更新文件表格（优化版本）
        
        Args:
            files: 文件列表
        """
        logger.info(f"更新文件表格，文件数量: {len(files)}")
        
        # 先清空表格，然后设置行数（优化性能）
        self.file_table.setRowCount(0)
        self.file_table.setRowCount(len(files))
        
        from ...utils.video_metadata import format_duration
        from ...utils.file_utils import format_file_size
        
        for row, file_record in enumerate(files):
            file_name = file_record.get('file_name', '')
            
            # 文件名
            name_item = QTableWidgetItem(file_name)
            self.file_table.setItem(row, 0, name_item)
            
            # 文件大小
            file_size = file_record.get('file_size', 0)
            size_str = format_file_size(file_size)
            size_item = QTableWidgetItem(size_str)
            self.file_table.setItem(row, 1, size_item)
            
            # 时长 - 添加调试日志
            duration = file_record.get('duration')
            logger.debug(f"文件 {file_name}: duration={duration} (type={type(duration)})")
            if duration is not None and duration != '':
                try:
                    duration_float = float(duration)
                    duration_str = format_duration(duration_float)
                except (ValueError, TypeError) as e:
                    logger.warning(f"文件 {file_name}: 无法解析时长值 {duration}: {e}")
                    duration_str = "未知"
            else:
                logger.debug(f"文件 {file_name}: 时长为空，显示为未知")
                duration_str = "未知"
            duration_item = QTableWidgetItem(duration_str)
            self.file_table.setItem(row, 2, duration_item)
            
            # 分辨率 - 添加调试日志和改进逻辑
            resolution = file_record.get('resolution')
            width = file_record.get('width')
            height = file_record.get('height')
            logger.debug(f"文件 {file_name}: resolution={resolution}, width={width}, height={height}")
            
            # 如果resolution为空或为'None'字符串，尝试从width和height构建
            if resolution is None or resolution == '' or str(resolution) == 'None':
                if width is not None and width != '' and height is not None and height != '':
                    try:
                        resolution = f"{int(width)}x{int(height)}"
                        logger.debug(f"文件 {file_name}: 从width和height构建分辨率: {resolution}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"文件 {file_name}: 无法从width和height构建分辨率: {e}")
                        resolution = "未知"
                else:
                    logger.debug(f"文件 {file_name}: 分辨率信息不足，显示为未知")
                    resolution = "未知"
            else:
                # 确保resolution是字符串
                resolution = str(resolution)
            
            resolution_item = QTableWidgetItem(resolution)
            self.file_table.setItem(row, 3, resolution_item)
            
            # 方向（竖屏/横屏）
            width = file_record.get('width')
            height = file_record.get('height')
            orientation = "未知"
            if width is not None and height is not None:
                try:
                    w = int(width)
                    h = int(height)
                    if w > h:
                        orientation = "横屏"
                    elif h > w:
                        orientation = "竖屏"
                    else:
                        orientation = "方形"
                except (ValueError, TypeError):
                    orientation = "未知"
            orientation_item = QTableWidgetItem(orientation)
            self.file_table.setItem(row, 4, orientation_item)
            
            # 是否有脚本
            has_script = file_record.get('has_script', 0)
            script_text = "是" if has_script else "否"
            script_item = QTableWidgetItem(script_text)
            self.file_table.setItem(row, 5, script_item)
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            btn_layout.setSpacing(5)
            
            # 查看脚本按钮（仅当有脚本时显示）
            if has_script:
                btn_view_script = PushButton("查看脚本", btn_widget)
                btn_view_script.clicked.connect(
                    lambda checked, file_id=file_record['id']: self._on_view_script(file_id)
                )
                btn_layout.addWidget(btn_view_script)
            
            # 删除按钮
            btn_delete = PushButton("删除", btn_widget)
            btn_delete.clicked.connect(
                lambda checked, file_id=file_record['id']: self._on_delete_file(file_id)
            )
            btn_layout.addWidget(btn_delete)
            
            btn_layout.addStretch()
            self.file_table.setCellWidget(row, 6, btn_widget)
            
            # 保存文件ID到第一列的数据中，方便后续获取选中的文件ID
            name_item.setData(Qt.UserRole, file_record['id'])
    
    def _on_add_file(self):
        """添加文件按钮点击事件"""
        if not self.file_manager:
            QMessageBox.warning(self, "错误", "文件管理器未初始化")
            return
        
        file_path = FileSelectDialog.select_file(self)
        if file_path:
            self._process_files([file_path], is_folder=False)
    
    def _on_add_folder(self):
        """添加文件夹按钮点击事件"""
        if not self.file_manager:
            QMessageBox.warning(self, "错误", "文件管理器未初始化")
            return
        
        folder_path = FileSelectDialog.select_folder(self)
        if folder_path:
            self._process_files([folder_path], is_folder=True)
    
    def _process_files(self, file_paths: List[str], is_folder: bool = False):
        """处理文件添加（在后台线程中执行）
        
        Args:
            file_paths: 文件路径列表
            is_folder: 是否为文件夹模式
        """
        # 创建并启动工作线程
        self.worker = FileProcessWorker(self.file_manager, file_paths, is_folder)
        self.worker.progress.connect(self._on_process_progress)
        self.worker.finished.connect(self._on_process_finished)
        self.worker.start()
        
        # 显示处理提示（使用简单的消息框）
        # 注意：实际进度会在后台线程中处理，这里只是提示用户
        logger.info("开始处理文件添加...")
    
    def _on_process_progress(self, message: str):
        """处理进度更新
        
        Args:
            message: 进度消息
        """
        logger.info(f"文件处理进度: {message}")
    
    def _on_process_finished(self, result: Dict[str, Any]):
        """处理完成
        
        Args:
            result: 处理结果
        """
        logger.info(f"文件处理完成，结果: {result}")
        
        if result.get('success'):
            # 统计结果
            results = result.get('results', [])
            logger.info(f"处理结果数量: {len(results)}")
            success_count = sum(1 for r in results if r.get('success'))
            failed_count = len(results) - success_count
            
            logger.info(f"成功: {success_count}, 失败: {failed_count}")
            
            if failed_count > 0:
                QMessageBox.warning(
                    self,
                    "添加完成",
                    f"成功添加 {success_count} 个文件，失败 {failed_count} 个"
                )
            else:
                QMessageBox.information(
                    self,
                    "添加成功",
                    f"成功添加 {success_count} 个文件"
                )
            
            # 刷新文件列表
            logger.info("开始刷新文件列表...")
            self._load_files()
            logger.info("文件列表刷新完成")
        else:
            error = result.get('error', '未知错误')
            logger.error(f"文件处理失败: {error}")
            QMessageBox.critical(self, "添加失败", f"添加文件失败: {error}")
    
    def _on_refresh(self):
        """刷新按钮点击事件（使用后台线程）"""
        if not self.file_manager:
            QMessageBox.warning(self, "错误", "文件管理器未初始化")
            return
        
        # 如果已有刷新任务在运行，不重复启动
        if self.refresh_worker and self.refresh_worker.isRunning():
            return
        
        # 检查 ffmpeg 是否安装
        from ...utils.ffmpeg_installer import check_and_install_ffmpeg
        from ...utils.video_metadata import check_ffmpeg_available, FFMPEG_AVAILABLE
        is_installed, msg = check_and_install_ffmpeg(install_if_missing=False)
        
        if not is_installed:
            # 提供更详细的提示信息
            detailed_msg = (
                f"检测到 ffmpeg 未安装，无法提取视频元数据（时长、分辨率等）。\n\n"
                f"{msg}\n\n"
                f"选项说明：\n"
                f"• 点击「是」：尝试自动安装 ffmpeg（推荐）\n"
                f"• 点击「否」：继续刷新，但元数据将显示为「未知」\n"
                f"• 点击「取消」：取消刷新操作\n\n"
            )
            detailed_msg += "\n\n提示：安装 ffmpeg 后，可以重新刷新文件以获取完整的元数据信息。"

            
            # 使用 Standard QMessageBox for complex question
            reply = QMessageBox.question(
                self,
                "FFmpeg 未安装",
                detailed_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 尝试自动安装
                install_success, install_msg = check_and_install_ffmpeg(install_if_missing=True)
                if install_success:
                    InfoBar.success(
                        title='安装成功',
                        content='ffmpeg 安装成功，请重启应用程序后重新刷新文件以获取元数据',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=5000,
                        parent=self
                    )
                    return  # 安装成功后需要重启，不继续刷新
                else:
                    # 安装失败，询问是否继续刷新
                    continue_reply = QMessageBox.question(
                        self,
                        "安装失败",
                        f"自动安装失败：\n\n{install_msg}\n\n是否继续刷新？\n（元数据将显示为「未知」）",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if continue_reply != QMessageBox.StandardButton.Yes:
                        return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
            # 如果选择"No"，继续执行刷新（元数据将显示为未知）

        # 禁用刷新按钮
        if self.btn_refresh:
            self.btn_refresh.setEnabled(False)
            self.btn_refresh.setText("刷新中...")
        
        # 显示进度提示
        InfoBar.info(
            title='开始刷新',
            content='正在刷新文件信息，请稍候...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
        # 创建并启动刷新工作线程
        self.refresh_worker = FileRefreshWorker(self.file_manager)
        self.refresh_worker.finished.connect(self._on_refresh_finished)
        self.refresh_worker.start()
    
    def _on_refresh_finished(self, result: Dict[str, Any]):
        """刷新完成回调
        
        Args:
            result: 刷新结果
        """
        # 恢复刷新按钮
        if self.btn_refresh:
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("刷新")
        
        # 显示结果
        if result.get('success'):
            refreshed_count = result.get('refreshed_count', 0)
            failed_count = result.get('failed_count', 0)
            
            if failed_count > 0:
                InfoBar.warning(
                    title='刷新完成',
                    content=f"已刷新 {refreshed_count} 个文件，失败 {failed_count} 个",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.success(
                    title='刷新完成',
                    content=f"已刷新 {refreshed_count} 个文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            
            # 重新加载文件列表
            self._load_files()
        else:
            error_msg = result.get('message', '未知错误')
            InfoBar.error(
                title='刷新失败',
                content=error_msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        
        # 清理工作线程
        if self.refresh_worker:
            self.refresh_worker.deleteLater()
            self.refresh_worker = None
    
    def _on_search(self, keyword: str):
        """搜索框文本变化事件
        
        Args:
            keyword: 搜索关键词
        """
        self._load_files(search_keyword=keyword if keyword else None)
    
    def _on_view_script(self, file_id: int):
        """查看脚本按钮点击事件
        
        Args:
            file_id: 文件记录ID
        """
        if not self.file_manager:
            return
        
        script_content = self.file_manager.get_script_content(file_id)
        if script_content:
            # 获取文件名
            files = self.file_manager.get_files()
            file_name = ""
            for f in files:
                if f['id'] == file_id:
                    file_name = f.get('file_name', '')
                    break
            
            dialog = ScriptViewDialog(script_content, file_name, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "提示", "脚本文件不存在或无法读取")
    
    def _on_delete_file(self, file_id: int):
        """单个文件删除按钮点击事件
        
        Args:
            file_id: 文件记录ID
        """
        if not self.file_manager:
            QMessageBox.warning(self, "错误", "文件管理器未初始化")
            return
        
        # 获取文件名用于显示
        files = self.file_manager.get_files()
        file_name = ""
        for f in files:
            if f['id'] == file_id:
                file_name = f.get('file_name', '未知文件')
                break
        
        # 确认删除
        reply = QMessageBox.warning(
            self,
            "确认删除",
            f"确定要删除文件记录「{file_name}」吗？\n（注意：此操作不会删除实际文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # 默认选中"否"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 查找要删除的行
            row = self._find_row_by_file_id(file_id)
            
            # 删除文件
            success = self.file_manager.delete_file(file_id)
            
            if success:
                # 直接从表格中删除行（性能优化，不重新加载整个列表）
                if row is not None:
                    self.file_table.removeRow(row)
                    # 检查是否还有文件
                    if self.file_table.rowCount() == 0:
                        self.file_table.setVisible(False)
                        self.empty_card.setVisible(True)
                else:
                    # 如果找不到行，重新加载（兜底方案）
                    self._load_files()
                
                # 显示成功消息（使用非阻塞方式）
                InfoBar.success(
                    title="删除成功",
                    content=f"文件记录「{file_name}」已删除",
                    duration=2000,
                    parent=self
                )
            else:
                QMessageBox.critical(
                    self,
                    "删除失败",
                    f"删除文件记录「{file_name}」失败，请查看日志获取详细信息"
                )
    
    def _on_batch_delete(self):
        """批量删除文件按钮点击事件"""
        if not self.file_manager:
            QMessageBox.warning(self, "错误", "文件管理器未初始化")
            return
        
        # 获取选中的行
        selected_rows = self.file_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的文件")
            return
        
        # 获取选中的文件ID
        file_ids = []
        for index in selected_rows:
            row = index.row()
            name_item = self.file_table.item(row, 0)
            if name_item:
                file_id = name_item.data(Qt.UserRole)
                if file_id:
                    file_ids.append(file_id)
        
        if not file_ids:
            QMessageBox.warning(self, "提示", "未找到有效的文件记录")
            return
        
        # 确认删除
        file_count = len(file_ids)
        reply = QMessageBox.warning(
            self,
            "确认删除",
            f"确定要删除选中的 {file_count} 个文件记录吗？\n（注意：此操作不会删除实际文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # 默认选中"否"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 批量删除
            result = self.file_manager.delete_files(file_ids)
            
            if result.get('success'):
                deleted_count = result.get('deleted_count', 0)
                failed_count = result.get('failed_count', 0)
                
                # 直接从表格中删除行（性能优化，不重新加载整个列表）
                if deleted_count > 0:
                    # 从后往前删除，避免索引变化问题
                    rows_to_remove = []
                    for file_id in file_ids:
                        row = self._find_row_by_file_id(file_id)
                        if row is not None:
                            rows_to_remove.append(row)
                    
                    # 按行号从大到小排序，从后往前删除
                    rows_to_remove.sort(reverse=True)
                    for row in rows_to_remove:
                        self.file_table.removeRow(row)
                    
                    # 检查是否还有文件
                    if self.file_table.rowCount() == 0:
                        self.file_table.setVisible(False)
                        self.empty_card.setVisible(True)
                
                # 显示结果消息
                if failed_count == 0:
                    InfoBar.success(
                        title="删除成功",
                        content=f"成功删除 {deleted_count} 个文件记录",
                        duration=2000,
                        parent=self
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "删除完成",
                        f"成功删除 {deleted_count} 个，失败 {failed_count} 个"
                    )
            else:
                QMessageBox.critical(self, "删除失败", result.get('message', '未知错误'))
