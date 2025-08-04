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
import numpy as np
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
        # 【坐标数据准备部分】- 优先使用实际经纬度坐标
        #===================================================================
        # 优先使用经纬度坐标进行绘图
        if 'latitude' in events.columns and 'longitude' in events.columns:
            # 直接使用经纬度作为绘图坐标
            events['x'] = events['longitude']
            events['y'] = events['latitude']
            print("使用实际经纬度坐标进行绘图")
            use_geographic_coords = True
        elif 'x' in events.columns and 'y' in events.columns:
            # 如果没有经纬度，但有相对坐标，则使用相对坐标
            print("使用相对坐标进行绘图")
            use_geographic_coords = False
        else:
            # 尝试使用关联器从经纬度转换为局部坐标（作为备选方案）
            if self.associator is not None and 'latitude' in events.columns and 'longitude' in events.columns:
                try:
                    # 转换经纬度坐标为局部平面坐标(单位:km)
                    local_coords = self.associator.transform_origin(events)
                    # 添加到事件数据框
                    events = pd.concat([events, local_coords[['x', 'y']]], axis=1)
                    print("已将经纬度转换为局部坐标用于绘图")
                    use_geographic_coords = False
                except Exception as e:
                    print(f"坐标转换失败: {e}")
                    # 如果转换失败，尝试使用经纬度作为坐标
                    if 'latitude' in events.columns and 'longitude' in events.columns:
                        events['x'] = events['longitude']
                        events['y'] = events['latitude']
                        print("转换失败，使用经纬度作为坐标")
                        use_geographic_coords = True
                    else:
                        print("无可用坐标数据")
                        return
            else:
                print("无可用坐标数据")
                return
        
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
        # 【台站位置绘制】- 如果有台站数据，优先使用经纬度
        #===================================================================
        # 绘制台站位置(红色三角形)
        if stations is not None and not stations.empty:
            print(f"开始绘制台站，台站数据形状: {stations.shape}")
            print(f"台站数据列: {stations.columns.tolist()}")
            
            # 处理台站坐标，优先使用经纬度
            stations_to_plot = stations.copy()
            station_plotted = False
            
            if use_geographic_coords:
                # 如果事件使用经纬度坐标，台站也优先使用经纬度
                if 'latitude' in stations_to_plot.columns and 'longitude' in stations_to_plot.columns:
                    stations_to_plot['x'] = stations_to_plot['longitude']
                    stations_to_plot['y'] = stations_to_plot['latitude']
                    print(f"台站使用经纬度坐标，台站数量: {len(stations_to_plot)}")
                    station_plotted = True
                elif 'x' in stations_to_plot.columns and 'y' in stations_to_plot.columns:
                    # 如果台站只有相对坐标，直接使用
                    print("台站使用现有的相对坐标")
                    station_plotted = True
                else:
                    print("台站数据中缺少坐标信息")
            else:
                # 如果事件使用相对坐标，台站也需要相对坐标
                if 'x' in stations_to_plot.columns and 'y' in stations_to_plot.columns:
                    print("台站使用现有的相对坐标")
                    station_plotted = True
                elif 'latitude' in stations_to_plot.columns and 'longitude' in stations_to_plot.columns:
                    if self.associator is not None:
                        try:
                            # 转换台站经纬度为相对坐标
                            local_coords = self.associator.transform_origin(stations_to_plot)
                            stations_to_plot = pd.concat([stations_to_plot, local_coords[['x', 'y']]], axis=1)
                            print("成功转换台站经纬度为相对坐标")
                            station_plotted = True
                        except Exception as e:
                            print(f"转换台站坐标失败: {e}")
                            # 转换失败，直接使用经纬度作为坐标
                            stations_to_plot['x'] = stations_to_plot['longitude']
                            stations_to_plot['y'] = stations_to_plot['latitude']
                            print("转换失败，直接使用经纬度作为坐标")
                            station_plotted = True
                    else:
                        # 没有关联器，直接使用经纬度作为坐标
                        stations_to_plot['x'] = stations_to_plot['longitude']
                        stations_to_plot['y'] = stations_to_plot['latitude']
                        print("没有关联器，直接使用经纬度作为坐标")
                        station_plotted = True
                else:
                    print("台站数据中缺少坐标信息")
            
            # 绘制台站
            if station_plotted and 'x' in stations_to_plot.columns and 'y' in stations_to_plot.columns:
                # 确保坐标数据是有效的
                valid_stations = stations_to_plot.dropna(subset=['x', 'y'])
                if not valid_stations.empty:
                    print(f"绘制 {len(valid_stations)} 个台站")
                    print(f"台站坐标范围: x=[{valid_stations['x'].min():.3f}, {valid_stations['x'].max():.3f}], y=[{valid_stations['y'].min():.3f}, {valid_stations['y'].max():.3f}]")
                    
                    # 【修改点】可以调整三角形样式:
                    # - "r^": 红色三角形
                    # - ms: 标记大小
                    # - mew: 标记边缘宽度
                    # - mec: 标记边缘颜色
                    ax.plot(valid_stations["x"], valid_stations["y"], "r^", ms=12, mew=1.5, mec="darkred", label="台站")
                    station_plotted = True
                else:
                    print("台站坐标数据无效（包含NaN值）")
                    station_plotted = False
            else:
                print("台站绘制条件不满足")
                station_plotted = False
        
        #===================================================================
        # 【坐标轴和标签设置】
        #===================================================================
        # 根据使用的坐标类型设置轴标签
        if use_geographic_coords:
            ax.set_xlabel("经度 [°]")
            ax.set_ylabel("纬度 [°]")
            # 设置更精确的刻度格式
            ax.ticklabel_format(style='plain', useOffset=False)
            
            # 为经纬度坐标优化显示范围和刻度
            self.optimize_geographic_display(ax, events, stations)
        else:
            ax.set_xlabel("东向距离 [km]")
            ax.set_ylabel("北向距离 [km]")
        
        # 设置图表标题
        title = "地震事件分布图"
        if use_geographic_coords:
            title += "（经纬度坐标）"
        else:
            title += "（相对坐标）"
        ax.set_title(title)
        
        # 添加网格线
        ax.grid(True, alpha=0.3)
        
        # 如果绘制了台站，添加图例
        if stations is not None and not stations.empty:
            # 检查是否成功绘制了台站
            try:
                if ('x' in stations.columns and 'y' in stations.columns) or \
                   ('latitude' in stations.columns and 'longitude' in stations.columns):
                    ax.legend()
                    print("添加了图例")
            except Exception as e:
                print(f"添加图例失败: {e}")
                pass
        
        #===================================================================
        # 【图形最终处理】
        #===================================================================
        # 调整布局以确保所有元素可见
        self.figure.tight_layout()
        # 刷新画布
        self.figure.canvas.draw()
    
    def optimize_geographic_display(self, ax, events, stations=None):
        """优化经纬度坐标的显示效果
        
        参数:
            ax: matplotlib坐标轴对象
            events: 事件数据框
            stations: 台站数据框（可选）
        """
        if 'longitude' in events.columns and 'latitude' in events.columns:
            # 计算事件经纬度范围
            lon_min, lon_max = events['longitude'].min(), events['longitude'].max()
            lat_min, lat_max = events['latitude'].min(), events['latitude'].max()
            
            # 如果有台站数据，也考虑台站的坐标范围
            if stations is not None and not stations.empty:
                if 'longitude' in stations.columns and 'latitude' in stations.columns:
                    station_lon_min, station_lon_max = stations['longitude'].min(), stations['longitude'].max()
                    station_lat_min, station_lat_max = stations['latitude'].min(), stations['latitude'].max()
                    
                    # 扩展坐标范围以包含台站
                    lon_min = min(lon_min, station_lon_min)
                    lon_max = max(lon_max, station_lon_max)
                    lat_min = min(lat_min, station_lat_min)
                    lat_max = max(lat_max, station_lat_max)
                    
                    print(f"坐标范围（包含台站）: 经度[{lon_min:.3f}, {lon_max:.3f}], 纬度[{lat_min:.3f}, {lat_max:.3f}]")
            
            # 添加适当的边距
            lon_margin = (lon_max - lon_min) * 0.1 if lon_max > lon_min else 0.01
            lat_margin = (lat_max - lat_min) * 0.1 if lat_max > lat_min else 0.01
            
            # 设置坐标轴范围
            ax.set_xlim(lon_min - lon_margin, lon_max + lon_margin)
            ax.set_ylim(lat_min - lat_margin, lat_max + lat_margin)
            
            # 设置合适的刻度间隔
            lon_range = lon_max - lon_min
            lat_range = lat_max - lat_min
            
            # 智能刻度间隔计算，确保刻度均匀且不拥挤
            # 目标：保持4-6个主要刻度，确保画幅充分利用
            
            def calculate_optimal_interval(data_range):
                """计算最优刻度间隔，确保4-6个刻度"""
                target_ticks = 5  # 目标刻度数量
                base_interval = data_range / target_ticks
                
                # 将间隔调整为"好看"的数值（1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01等）
                nice_intervals = [5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]
                for interval in nice_intervals:
                    if base_interval >= interval * 0.6:  # 收紧条件，更倾向于较大间隔
                        return interval
                return nice_intervals[-1]  # 最小间隔
            
            lon_tick_interval = calculate_optimal_interval(lon_range)
            lat_tick_interval = calculate_optimal_interval(lat_range)
            
            print(f"刻度间隔优化: 经度={lon_tick_interval}°, 纬度={lat_tick_interval}°")
            
            # 生成均匀分布的刻度
            import numpy as np
            
            # 计算刻度的起始和结束位置，确保刻度覆盖整个显示范围
            lon_start = np.floor((lon_min - lon_margin) / lon_tick_interval) * lon_tick_interval
            lon_end = np.ceil((lon_max + lon_margin) / lon_tick_interval) * lon_tick_interval
            lat_start = np.floor((lat_min - lat_margin) / lat_tick_interval) * lat_tick_interval
            lat_end = np.ceil((lat_max + lat_margin) / lat_tick_interval) * lat_tick_interval
            
            # 生成刻度数组
            lon_ticks = np.arange(lon_start, lon_end + lon_tick_interval/2, lon_tick_interval)
            lat_ticks = np.arange(lat_start, lat_end + lat_tick_interval/2, lat_tick_interval)
            
            # 确保刻度数量合理（4-6个），避免过于拥挤或稀疏
            max_ticks = 6  # 最大刻度数
            min_ticks = 4  # 最小刻度数
            
            # 如果刻度太多，适当减少
            if len(lon_ticks) > max_ticks:
                step = len(lon_ticks) // max_ticks + 1
                lon_ticks = lon_ticks[::step]
            if len(lat_ticks) > max_ticks:
                step = len(lat_ticks) // max_ticks + 1
                lat_ticks = lat_ticks[::step]
            
            # 如果刻度太少，适当增加
            if len(lon_ticks) < min_ticks and lon_range > 0:
                # 重新计算更密集的刻度
                lon_tick_interval = lon_tick_interval / 2
                lon_start = np.floor((lon_min - lon_margin) / lon_tick_interval) * lon_tick_interval
                lon_end = np.ceil((lon_max + lon_margin) / lon_tick_interval) * lon_tick_interval
                lon_ticks = np.arange(lon_start, lon_end + lon_tick_interval/2, lon_tick_interval)
                
            if len(lat_ticks) < min_ticks and lat_range > 0:
                lat_tick_interval = lat_tick_interval / 2
                lat_start = np.floor((lat_min - lat_margin) / lat_tick_interval) * lat_tick_interval
                lat_end = np.ceil((lat_max + lat_margin) / lat_tick_interval) * lat_tick_interval
                lat_ticks = np.arange(lat_start, lat_end + lat_tick_interval/2, lat_tick_interval)
            
            print(f"最终刻度数量: 经度={len(lon_ticks)}个, 纬度={len(lat_ticks)}个")
            
            ax.set_xticks(lon_ticks)
            ax.set_yticks(lat_ticks)
            
            # 设置刻度标签格式，确保不重叠
            if lon_tick_interval >= 1:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}°'))
            elif lon_tick_interval >= 0.1:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}°'))
            else:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}°'))
                
            if lat_tick_interval >= 1:
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}°'))
            elif lat_tick_interval >= 0.1:
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}°'))
            else:
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}°'))
            
            # 优化刻度标签显示，避免重叠
            ax.tick_params(axis='x', rotation=0, labelsize=9)  # x轴标签不旋转，使用较小字体
            ax.tick_params(axis='y', rotation=0, labelsize=9)  # y轴标签不旋转，使用较小字体
            
            # 如果刻度仍然拥挤，自动旋转x轴标签
            if len(lon_ticks) > 5:
                ax.tick_params(axis='x', rotation=45)  # 斜45度显示
            
            print(f"刻度标签优化完成")

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
