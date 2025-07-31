"""
地震目录可视化模块

此模块包含了地震事件目录的可视化功能，包括：
1. 震源分布图绘制
2. 事件列表表格显示
3. 可视化对话框界面

作者：Eureashell
创建时间：2025年7月29日
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QWidget, 
                             QHeaderView, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from datetime import datetime


class CatalogVisualizerDialog(QDialog):
    """地震目录可视化对话框类
    
    本类创建一个包含震源分布图和事件列表的可视化窗口。
    主要组件：
    - 左侧：震源分布图（matplotlib绘制）
    - 右侧：事件详细信息表格
    """
    
    def __init__(self, parent=None, events_df=None, stations_df=None, associator=None):
        """初始化可视化对话框
        
        参数:
            parent: 父窗口对象
            events_df: 地震事件数据框
            stations_df: 台站信息数据框  
            associator: 地震关联器对象
        """
        super().__init__(parent)
        
        # 存储数据
        self.events_df = events_df
        self.stations_df = stations_df
        self.associator = associator
        
        # 设置窗口属性
        self.setWindowTitle("地震事件可视化")
        self.setGeometry(100, 100, 2000, 1200)  # 窗口位置和大小(x, y, 宽, 高)
        
        # 检查数据有效性
        if self.events_df is None or self.events_df.empty:
            QMessageBox.warning(self, "警告", "没有关联事件可显示")
            return
        
        # 设置界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面布局
        
        【布局修改指南】：
        - 要改为垂直布局: 将 QHBoxLayout 改为 QVBoxLayout
        - 要改为网格布局: 将 QHBoxLayout 改为 QGridLayout，然后使用 layout.addWidget(widget, row, col)
        - 调整部件比例: 修改 main_layout.addWidget() 的比例参数
        """
        # 创建主水平布局 - 【如需改为垂直布局，将QHBoxLayout改为QVBoxLayout】
        main_layout = QHBoxLayout(self)
        
        #===================================================================
        # 【震源分布图部分】
        #===================================================================
        left_widget = self.create_map_widget()
        # 将左侧部分添加到主布局，使其填充剩余空间
        main_layout.addWidget(left_widget, 1)  # 设置为1，将占用除右侧固定宽度外的所有空间 
        
        #===================================================================
        # 【事件列表部分】
        #===================================================================
        right_widget = self.create_table_widget()
        # 将右侧部分添加到主布局，使用固定宽度
        right_widget.setFixedWidth(700)  # 设置固定宽度，比表格稍宽以留出边距
        main_layout.addWidget(right_widget)
        
    def create_map_widget(self):
        """创建震源分布图部件
        
        返回:
            QWidget: 包含震源分布图的部件
        """
        left_widget = QWidget()  # 创建一个容器部件
        left_layout = QVBoxLayout(left_widget)  # 左侧使用垂直布局
        
        # 创建标题标签
        title_label = QLabel("震源分布图")
        title_label.setFont(QFont("SimSun", 12, QFont.Bold))  # 字体设置：字体名，大小，粗体
        title_label.setAlignment(Qt.AlignCenter)  # 文本居中对齐
        left_layout.addWidget(title_label)
        
        # 创建Matplotlib图形容器
        map_widget = QWidget()  # Matplotlib需要一个容器来承载
        map_layout = QVBoxLayout(map_widget)
        map_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距
        
        # 创建自适应窗口大小的Matplotlib图形
        self.figure = Figure()  # 不指定大小，将根据容器自动调整
        self.canvas = FigureCanvas(self.figure)  # 创建画布
        # 设置画布的大小策略为Expanding，使其填充可用空间
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        map_layout.addWidget(self.canvas)
        
        # 绘制震源分布图 - 调用实际绘图函数
        self.plot_earthquake_distribution()
        
        # 添加到左侧布局，移除弹性空间以使图形填满区域
        left_layout.addWidget(map_widget)
        
        return left_widget
    
    def create_table_widget(self):
        """创建事件列表表格部件
        
        返回:
            QWidget: 包含事件列表表格的部件
        """
        right_widget = QWidget()  # 创建右侧容器部件
        right_layout = QVBoxLayout(right_widget)  # 右侧使用垂直布局
        
        # 添加事件列表标题
        events_title = QLabel("事件列表")
        events_title.setFont(QFont("SimSun", 12, QFont.Bold))  # 使用中文字体
        events_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(events_title)
        
        # 创建表格
        self.events_table = QTableWidget()
        
        # 设置表格最小高度
        self.events_table.setMinimumHeight(600)
        # 设置表格固定宽度，确保能完全显示表头
        self.events_table.setFixedWidth(650)  # 设置固定宽度
        
        # 填充表格数据 - 调用填充表格的函数
        self.populate_events_table()
        
        # 添加表格到右侧布局
        right_layout.addWidget(self.events_table)
        
        return right_widget
        
    def plot_earthquake_distribution(self):
        """绘制震源位置分布图（2D平面图）
            
        【修改指南】:
            - 修改图形类型: 更改add_subplot的参数(如3D图：add_subplot(111, projection='3d'))
            - 更改颜色设置: 修改scatter中的cmap参数(如"jet", "viridis", "plasma"等)
            - 修改点大小: 更改scatter中的s参数
            - 添加图例: 使用ax.legend()
            - 调整坐标轴: 使用ax.set_xlim(), ax.set_ylim()
        """
        # 清除图形
        self.figure.clear()
        
        # 设置中文字体支持 - 允许在图像中显示中文
        plt.rcParams['font.sans-serif'] = ['SimSun']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        
        # 创建2D子图 - 111表示1行1列的第1个图
        ax = self.figure.add_subplot(111)
        ax.set_aspect("equal")  # 保持X和Y轴的比例相同
        
        # 获取事件和台站信息
        events = self.events_df.copy()  # 创建副本避免修改原数据
        stations = self.stations_df
        
        #===================================================================
        # 【坐标数据准备部分】- 确保有可绘制的x和y坐标数据
        #===================================================================
        # 检查必要的列是否存在
        if 'x' not in events.columns or 'y' not in events.columns:
            # 尝试使用关联器从经纬度转换为局部坐标
            if self.associator is not None and 'latitude' in events.columns and 'longitude' in events.columns:
                try:
                    # 转换经纬度坐标为局部平面坐标(单位:km)
                    local_coords = self.associator.transform_origin(events)
                    # 添加到事件数据框
                    events = pd.concat([events, local_coords[['x', 'y']]], axis=1)
                    print("已将经纬度转换为局部坐标用于绘图")
                except Exception as e:
                    print(f"坐标转换失败: {e}")
                    # 如果转换失败，使用经纬度作为坐标
                    events['x'] = events['longitude']
                    events['y'] = events['latitude']
                    print("使用经纬度作为坐标")
            else:
                # 直接使用经纬度
                events['x'] = events['longitude']
                events['y'] = events['latitude']
                print("无法转换坐标，使用经纬度代替")
        
        #===================================================================
        # 【震源点绘制部分】- 主要散点图绘制
        #===================================================================
        # 绘制事件点，使用颜色表示深度
        # 【修改点】可以调整这里的参数来更改散点图外观:
        # - s: 点大小
        # - cmap: 颜色映射("viridis", "jet", "plasma", "inferno"等)
        # - alpha: 透明度(0-1)
        scatter = ax.scatter(
            events["x"], events["y"],  # X和Y坐标
            c=events["depth"],         # 颜色映射值(深度)
            s=80,                      # 点大小
            cmap="viridis",            # 颜色映射
            alpha=0.8                  # 透明度
        )
        
        # 添加颜色条并反转颜色条
        cbar = self.figure.colorbar(scatter, ax=ax)
        cbar.ax.set_ylim(cbar.ax.get_ylim()[::-1])  # 反转颜色条(深度由浅至深)
        cbar.set_label("深度 [km]")                  # 颜色条标签
        
        #===================================================================
        # 【台站位置绘制】- 如果有台站数据
        #===================================================================
        # 绘制台站位置(红色三角形)
        if stations is not None and 'x' in stations.columns and 'y' in stations.columns:
            # 【修改点】可以调整三角形样式:
            # - "r^": 红色三角形
            # - ms: 标记大小
            # - mew: 标记边缘宽度
            # - mec: 标记边缘颜色
            ax.plot(stations["x"], stations["y"], "r^", ms=10, mew=1, mec="k", label="台站")
        
        #===================================================================
        # 【坐标轴和标签设置】
        #===================================================================
        # 根据使用的坐标类型设置轴标签
        if 'longitude' in events.columns and events['x'].equals(events['longitude']):
            ax.set_xlabel("经度 [°]")
            ax.set_ylabel("纬度 [°]")
        else:
            ax.set_xlabel("东向距离 [km]")
            ax.set_ylabel("北向距离 [km]")
        
        # 设置图表标题
        ax.set_title("地震事件分布图")
        
        # 添加网格线
        ax.grid(True, alpha=0.3)
        
        # 如果绘制了台站，添加图例
        if stations is not None and 'x' in stations.columns and 'y' in stations.columns:
            ax.legend()
        
        #===================================================================
        # 【图形最终处理】
        #===================================================================
        # 调整布局以确保所有元素可见
        self.figure.tight_layout()
        # 刷新画布
        self.figure.canvas.draw()

    def populate_events_table(self):
        """填充事件表格数据"""
        # 设置表格列
        headers = ['ID', '经度', '纬度', '深度 (km)', '发生时间', '相位数', 'RMS', 'GAP']
        self.events_table.setColumnCount(len(headers))
        self.events_table.setHorizontalHeaderLabels(headers)
        
        # 从数据框填充
        if self.events_df is not None and not self.events_df.empty:
            self.events_table.setRowCount(len(self.events_df))
            
            for i, (idx, event) in enumerate(self.events_df.iterrows()):
                # ID
                self.events_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                # 经度
                self.events_table.setItem(i, 1, QTableWidgetItem(f"{event['longitude']:.4f}"))
                # 纬度
                self.events_table.setItem(i, 2, QTableWidgetItem(f"{event['latitude']:.4f}"))
                # 深度
                self.events_table.setItem(i, 3, QTableWidgetItem(f"{event['depth']:.2f}"))
                # 时间
                time_str = datetime.fromtimestamp(event['time']).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                self.events_table.setItem(i, 4, QTableWidgetItem(time_str))
                # 相位数
                self.events_table.setItem(i, 5, QTableWidgetItem(str(event['picks'])))
                # RMS（如果有）
                rms = event.get('rms', 0)
                self.events_table.setItem(i, 6, QTableWidgetItem(f"{rms:.2f}"))
                # GAP（如果有）
                gap = event.get('gap', 0)
                self.events_table.setItem(i, 7, QTableWidgetItem(str(gap)))
        
        # 设置各列的固定宽度，确保表头文字完全显示
        header = self.events_table.horizontalHeader()
        column_widths = [40, 80, 80, 80, 150, 60, 60, 60]  # 各列宽度
        
        for i, width in enumerate(column_widths):
            self.events_table.setColumnWidth(i, width)
            header.setSectionResizeMode(i, QHeaderView.Fixed)  # 设置列宽为固定值


class CatalogVisualizer:
    """地震目录可视化器类
    
    用于创建和管理地震目录可视化对话框的工具类。
    提供静态方法来快速创建可视化窗口。
    """
    
    @staticmethod
    def show_catalog_visualization(parent, events_df, stations_df=None, associator=None):
        """显示地震目录可视化对话框
        
        参数:
            parent: 父窗口对象
            events_df: 地震事件数据框
            stations_df: 台站信息数据框（可选）
            associator: 地震关联器对象（可选）
            
        返回:
            None
        """
        # 检查数据有效性
        if events_df is None or events_df.empty:
            QMessageBox.warning(parent, "警告", "没有关联事件可显示")
            return
            
        # 创建并显示可视化对话框
        dialog = CatalogVisualizerDialog(
            parent=parent,
            events_df=events_df,
            stations_df=stations_df,
            associator=associator
        )
        
        # 显示对话框 - 这是一个模态对话框，会阻塞直到关闭
        dialog.exec_()
    
    @staticmethod
    def plot_events_only(figure, events_df, stations_df=None, associator=None):
        """仅绘制事件分布图到指定的matplotlib图形对象
        
        参数:
            figure: matplotlib的Figure对象
            events_df: 地震事件数据框
            stations_df: 台站信息数据框（可选）
            associator: 地震关联器对象（可选）
            
        返回:
            matplotlib.axes.Axes: 绘制的坐标轴对象
        """
        # 创建临时的可视化器对象来使用绘图方法
        temp_visualizer = CatalogVisualizerDialog(
            parent=None,
            events_df=events_df,
            stations_df=stations_df,
            associator=associator
        )
        
        # 设置图形对象
        temp_visualizer.figure = figure
        
        # 绘制图形
        temp_visualizer.plot_earthquake_distribution()
        
        return figure.axes[0] if figure.axes else None


# 兼容性函数，保持与原代码的接口一致
def visualize_catalog(parent, events_df, stations_df=None, associator=None):
    """可视化关联的地震目录 - 兼容性函数
    
    参数:
        parent: 父窗口对象
        events_df: 地震事件数据框
        stations_df: 台站信息数据框（可选）
        associator: 地震关联器对象（可选）
    """
    CatalogVisualizer.show_catalog_visualization(
        parent=parent,
        events_df=events_df,
        stations_df=stations_df,
        associator=associator
    )


def plot_3d_from_dataframe(figure, events_df, stations_df=None, associator=None):
    """从DataFrame绘制震源位置分布图 - 兼容性函数
    
    参数:
        figure: matplotlib的Figure对象
        events_df: 地震事件数据框
        stations_df: 台站信息数据框（可选）
        associator: 地震关联器对象（可选）
    """
    return CatalogVisualizer.plot_events_only(
        figure=figure,
        events_df=events_df,
        stations_df=stations_df,
        associator=associator
    )
