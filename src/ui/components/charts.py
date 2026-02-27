"""
图表组件
文件路径：src/ui/components/charts.py
功能：封装PySide6.QtCharts，提供平台分布饼图和发布趋势图
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsLayout
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QPieSlice, 
    QLineSeries, QDateTimeAxis, QValueAxis
)
from PySide6.QtCore import Qt, QDateTime

from qfluentwidgets import CardWidget, SubtitleLabel

class ChartBase(CardWidget):
    """图表基类"""
    
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        # UI初始化
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(20, 20, 20, 20)
        self.v_layout.setSpacing(10)
        
        # 标题
        self.title_label = SubtitleLabel(title, self)
        self.v_layout.addWidget(self.title_label)
        
        # 图表视图
        self.v_layout.addWidget(self.chart_view)
        
        # 设置图表样式
        self.chart.setBackgroundVisible(False)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)

class PlatformDistributionChart(ChartBase):
    """平台分布饼图"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("平台分布", parent)
        self.series = QPieSeries()
        self.chart.addSeries(self.series)
        # 启用动画
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        
    def set_data(self, data: Dict[str, int]):
        """设置数据
        
        Args:
            data: 平台名称和数量的字典，例如 {'抖音': 10, '快手': 5}
        """
        self.series.clear()
        
        # 颜色列表 (Fluent Design colors)
        colors = ["#0078D4", "#0099BC", "#00B7C3", "#00CC6A", "#107C10", "#FFB900"]
        
        idx = 0
        total = sum(data.values())
        
        for platform, count in data.items():
            if count > 0:
                slice_ = self.series.append(platform, count)
                slice_.setLabel(f"{platform}: {count}")
                slice_.setColor(QColor(colors[idx % len(colors)]))
                
                # 连接信号（可选：点击效果）
                slice_.hovered.connect(lambda state, s=slice_: self._on_slice_hovered(state, s))
                
                idx += 1
                
        # 如果没有数据
        if total == 0:
             self.series.append("暂无数据", 1)
             
    def _on_slice_hovered(self, state: bool, slice_: QPieSlice):
        """扇区悬停效果"""
        slice_.setExploded(state)
        slice_.setLabelVisible(state)

class PublishTrendChart(ChartBase):
    """发布趋势折线图"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("发布趋势", parent)
        self.series = QLineSeries()
        self.chart.addSeries(self.series)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 坐标轴
        self.axis_x = QDateTimeAxis()
        self.axis_x.setTickCount(7)
        self.axis_x.setFormat("MM-dd")
        self.axis_x.setTitleText("日期")
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)
        
        self.axis_y = QValueAxis()
        self.axis_y.setLabelFormat("%i")
        self.axis_y.setTitleText("发布数量")
        self.axis_y.setMin(0)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)
        
    def set_data(self, history: List[Dict[str, Any]]):
        """设置数据
        
        Args:
            history: 包含日期和数量的列表，例如 [{'date': '2023-01-01', 'count': 5}, ...]
        """
        self.series.clear()
        
        if not history:
            return
            
        max_count = 0
        
        # 对数据进行排序
        sorted_history = sorted(history, key=lambda x: x['date'])
        
        for item in sorted_history:
            dt = QDateTime.fromString(item['date'], "yyyy-MM-dd")
            count = item['count']
            self.series.append(dt.toMSecsSinceEpoch(), count)
            if count > max_count:
                max_count = count
        
        # 更新坐标轴范围
        if sorted_history:
            first_date = QDateTime.fromString(sorted_history[0]['date'], "yyyy-MM-dd")
            last_date = QDateTime.fromString(sorted_history[-1]['date'], "yyyy-MM-dd")
            self.axis_x.setRange(first_date, last_date)
            
        # Y轴留一点余量
        self.axis_y.setRange(0, max_count + 2)
