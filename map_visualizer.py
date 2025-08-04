"""
地震事件地图可视化模块

此模块提供地震事件在真实地图上的可视化功能，包括:
1. 使用Folium创建交互式地图
2. 在地图上标记地震事件位置
3. 根据深度和震级显示不同颜色和大小的标记
4. 提供事件详细信息的弹出窗口

作者：Eureashell
创建时间：2025年8月10日
"""

import os
import folium
from folium.plugins import HeatMap
import pandas as pd
import numpy as np
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QCheckBox, QGroupBox,
                            QMessageBox, QFormLayout, QWidget)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QFont
import tempfile

class MapVisualizerDialog(QDialog):
    """地震事件地图可视化对话框
    
    使用Folium库创建地图并在默认浏览器中打开。
    提供多种地图类型选择和可视化选项。
    """
    
    def __init__(self, parent=None, events_df=None, stations_df=None):
        """初始化地图可视化对话框
        
        参数:
            parent: 父窗口对象
            events_df: 地震事件数据框
            stations_df: 台站信息数据框
        """
        super().__init__(parent)
        
        # 存储数据
        self.events_df = events_df
        self.stations_df = stations_df
        
        # 创建临时目录存储地图文件
        self.temp_dir = tempfile.gettempdir()
        self.map_file = os.path.join(self.temp_dir, "earthquake_map.html")
        
        # 设置窗口属性
        self.setWindowTitle("地震事件地图定位")
        self.setGeometry(100, 100, 600, 400)
        
        # 检查数据有效性
        if self.events_df is None or self.events_df.empty:
            QMessageBox.warning(self, "警告", "没有地震事件可显示")
            return
            
        # 设置界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        main_layout = QVBoxLayout(self)
        
        # 顶部信息标签
        info_label = QLabel("选择地图类型和显示选项，然后点击'生成地图'按钮。地图将在默认浏览器中打开。")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setFont(QFont("SimSun", 10))
        main_layout.addWidget(info_label)
        
        # 控制区域
        controls_layout = QVBoxLayout()
        
        # 默认使用OpenStreetMap类型
        
        # 显示选项组
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout(display_group)
        
        self.show_events_cb = QCheckBox("显示地震事件")
        self.show_events_cb.setChecked(True)
        
        self.show_stations_cb = QCheckBox("显示台站位置")
        self.show_stations_cb.setChecked(True)
        
        self.show_heatmap_cb = QCheckBox("显示热力图")
        self.show_heatmap_cb.setChecked(False)
        
        display_layout.addWidget(self.show_events_cb)
        display_layout.addWidget(self.show_stations_cb)
        display_layout.addWidget(self.show_heatmap_cb)
        
        # 添加控件到控制布局
        controls_layout.addWidget(display_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 生成地图按钮
        generate_btn = QPushButton("生成地图")
        generate_btn.clicked.connect(self.generate_and_show_map)
        generate_btn.setMinimumHeight(40)
        generate_btn.setFont(QFont("SimSun", 10, QFont.Bold))
        
        # 取消按钮
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(generate_btn)
        button_layout.addWidget(cancel_btn)
        
        # 将控制布局添加到主布局
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(button_layout)
        
        # 添加底部说明
        legend_label = QLabel(
            "颜色标识: 红色 - 强震 (M≥6.0) | 橙色 - 中等 (5.0≤M<6.0) | " 
            "黄色 - 弱震 (M<5.0) | 标记大小代表深度"
        )
        legend_label.setFont(QFont("SimSun", 9))
        legend_label.setAlignment(Qt.AlignCenter)
        legend_label.setWordWrap(True)
        main_layout.addWidget(legend_label)
    
    def generate_and_show_map(self):
        """生成地图并在默认浏览器中打开"""
        try:
            # 使用默认地图类型
            map_type = "OpenStreetMap"
            show_events = self.show_events_cb.isChecked()
            show_stations = self.show_stations_cb.isChecked()
            show_heatmap = self.show_heatmap_cb.isChecked()
            
            # 创建地图
            self.create_map(
                map_type=map_type,
                show_events=show_events,
                show_stations=show_stations,
                show_heatmap=show_heatmap
            )
            
            # 在浏览器中打开地图
            webbrowser.open(self.map_file)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成地图时出错: {str(e)}")
    
    def create_map(self, map_type, show_events, show_stations, show_heatmap):
        """创建地图并保存为HTML文件
        
        参数:
            map_type: 地图类型
            show_events: 是否显示地震事件
            show_stations: 是否显示台站
            show_heatmap: 是否显示热力图
        """
        # 检查数据是否有效
        if self.events_df is None or self.events_df.empty:
            raise ValueError("没有地震事件可显示")
        
        # 打印事件数据框的列名，帮助调试
        print("事件数据框列名:", self.events_df.columns.tolist())
        # 打印第一行数据，了解数据结构
        if len(self.events_df) > 0:
            print("第一个事件数据:", dict(self.events_df.iloc[0]))
            
        # 计算事件的中心位置
        center_lat = self.events_df['latitude'].mean()
        center_lon = self.events_df['longitude'].mean()
        
        # 创建地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles=map_type
        )
        
        # 添加地震事件标记
        if show_events:
            for _, event in self.events_df.iterrows():
                # 计算震级的改进方法，综合考虑相位数、深度和残差
                picks = event.get('picks', 0)
                depth = event.get('depth', 10.0)
                rms = event.get('rms', 0.5)  # 残差均方根，如果有的话
                
                # 基础震级计算 - 相位数是主要因素
                base_mag = 2.5 + 0.6 * np.log10(max(picks, 1))
                
                # 深度调整因子 - 深度越大，调整越小（深源地震通常振幅较小但影响范围大）
                depth_factor = 0.2 * np.log10(max(depth, 1.0) / 10.0)
                
                # 残差调整因子 - 残差越小，拟合越好，震级可能越大
                rms_factor = -0.1 * min(rms, 1.0)  # 负相关，最大调整-0.1
                
                # 计算最终震级，并限制在合理范围内
                mag = min(max(base_mag + depth_factor + rms_factor, 2.0), 8.0)
                
                # 根据震级选择颜色
                if mag >= 6.0:
                    color = 'red'
                elif mag >= 5.0:
                    color = 'orange'
                else:
                    color = 'beige'
                    
                # 根据深度调整标记大小
                radius = min(10 + event['depth'] / 5, 25)
                
                # 创建弹出窗口内容
                popup_html = f"""
                <div style="width:200px">
                    <h4 style="color:darkgreen;margin:0">M {mag:.1f} 地震</h4>
                    <hr style="margin:3px">
                    <b>时间:</b> {datetime.fromtimestamp(event['time']).strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <b>经度:</b> {event['longitude']:.4f}°<br>
                    <b>纬度:</b> {event['latitude']:.4f}°<br>
                    <b>深度:</b> {event['depth']:.1f} km<br>
                    <b>震级:</b> {mag:.1f}<br>
                    <b>使用相位数:</b> {event.get('picks', 0)}
                </div>
                """
                
                # 添加标记
                folium.CircleMarker(
                    location=(event['latitude'], event['longitude']),
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(m)
        
        # 添加台站标记
        if show_stations and self.stations_df is not None and not self.stations_df.empty:
            # 检查台站数据是否包含所需的列
            if all(col in self.stations_df.columns for col in ['latitude', 'longitude', 'id']):
                for _, station in self.stations_df.iterrows():
                    # 创建台站弹出窗口内容
                    station_popup = f"""
                    <div style="width:180px">
                        <h4 style="color:blue;margin:0">台站: {station['id']}</h4>
                        <hr style="margin:3px">
                        <b>经度:</b> {station['longitude']:.4f}°<br>
                        <b>纬度:</b> {station['latitude']:.4f}°<br>
                        <b>海拔:</b> {station.get('elevation', 'N/A')} m<br>
                    </div>
                    """
                    
                    # 添加台站标记
                    folium.Marker(
                        location=(station['latitude'], station['longitude']),
                        icon=folium.Icon(color='blue', icon='info-sign'),
                        popup=folium.Popup(station_popup, max_width=300)
                    ).add_to(m)
        
        # 添加热力图
        if show_heatmap:
            # 准备热力图数据
            heat_data = []
            for _, event in self.events_df.iterrows():
                # 使用与上面相同的改进震级计算方法
                picks = event.get('picks', 0)
                depth = event.get('depth', 10.0)
                rms = event.get('rms', 0.5)
                
                # 基础震级计算 - 相位数是主要因素
                base_mag = 2.5 + 0.6 * np.log10(max(picks, 1))
                
                # 深度调整因子
                depth_factor = 0.2 * np.log10(max(depth, 1.0) / 10.0)
                
                # 残差调整因子
                rms_factor = -0.1 * min(rms, 1.0)
                
                # 计算最终震级
                mag = min(max(base_mag + depth_factor + rms_factor, 2.0), 8.0)
                # 使用震级作为强度
                heat_data.append([event['latitude'], event['longitude'], mag])
                
            # 添加热力图层
            HeatMap(heat_data, radius=15).add_to(m)
        
        # 添加图例和标题
        title_html = '''
             <div style="position: fixed; 
                         top: 10px; left: 50px; width: 800px; height: 50px; 
                         background-color: white; border-radius: 5px;
                         z-index:9999; font-size:16px; padding: 8px;
                         font-family: 'Arial', sans-serif;
                         box-shadow: 0 0 5px rgba(0,0,0,0.2);">
                 <b>地震事件地图定位</b> - 
                 红色: 强震 (M≥6.0) | 橙色: 中等 (5.0≤M<6.0) | 黄色: 弱震 (M<5.0)
             </div>
             '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # 保存地图为HTML文件
        m.save(self.map_file)


class EmbeddedMapWidget(QWidget):
    """嵌入式地图小部件
    
    可以嵌入到其他界面中的地图显示小部件，用于实时监测中显示地震事件位置。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events_df = None
        self.stations_df = None
        self.map_file = os.path.join(tempfile.gettempdir(), "embedded_map.html")
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建标题标签
        self.title_label = QLabel("地震事件地图")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("SimSun", 10, QFont.Bold))
        layout.addWidget(self.title_label)
        
        # 创建网页视图组件
        try:
            # 直接导入QWebEngineView，不使用动态导入
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self.web_view = QWebEngineView()
            self.web_view.setMinimumSize(300, 400)  # 设置最小尺寸
            self.web_view.setZoomFactor(0.8)  # 设置缩放因子，使地图更好地适应容器
            try:
                # 尝试使用新版 API
                self.web_view.page().settings().setAttribute(
                    QWebEngineSettings.WebAttribute.ShowScrollBars, False
                )
            except:
                try:
                    # 尝试使用旧版 API
                    self.web_view.page().settings().setAttribute(
                        QWebEngineSettings.ShowScrollBars, False
                    )
                except:
                    # 如果都失败，就不设置滚动条属性
                    pass
            layout.addWidget(self.web_view, 1)  # 1表示拉伸系数
            self.has_web_engine = True

        except Exception as e:
            # 如果出现任何问题，使用替代显示方式
            self.info_label = QLabel("地图加载失败")
            self.info_label.setWordWrap(True)
            self.info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.info_label)
            self.open_browser_btn = QPushButton("在浏览器中查看地图")
            self.open_browser_btn.clicked.connect(self.open_map_in_browser)
            layout.addWidget(self.open_browser_btn)
            self.has_web_engine = False
    
    def update_map(self, events_df, stations_df=None):
        """更新地图数据并刷新显示
        
        参数:
            events_df: 地震事件数据框
            stations_df: 台站信息数据框（可选）
        """
        if events_df is None or events_df.empty:
            self.title_label.setText("无地震事件数据")
            return
            
        self.events_df = events_df
        self.stations_df = stations_df
        
        # 创建地图
        self.create_map()
        
        # 更新标题
        self.title_label.setText(f"地震事件地图 ({len(events_df)}个事件)")
        
        # 如果有WebEngine，加载地图
        if self.has_web_engine:
            try:
                # 检查地图文件是否存在
                if not os.path.exists(self.map_file):
                    self.title_label.setText(f"地图文件不存在")
                    return
                    
                # 检查文件大小
                file_size = os.path.getsize(self.map_file)
                
                if file_size == 0:
                    self.title_label.setText("地图文件为空")
                    return
                
                # 创建URL并加载
                map_url = QUrl.fromLocalFile(self.map_file)
                self.web_view.load(map_url)
                

                
            except Exception:
                self.title_label.setText(f"地图加载失败")
    
    def open_map_in_browser(self):
        """在默认浏览器中打开地图"""
        if os.path.exists(self.map_file):
            webbrowser.open(self.map_file)
    
    def create_map(self):
        """创建地图并保存为HTML文件"""
        if self.events_df is None or self.events_df.empty:
            return
            
        
        try:
            # 计算事件的中心位置
            center_lat = self.events_df['latitude'].mean()
            center_lon = self.events_df['longitude'].mean()
            
            # 创建地图
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=6,
                tiles="OpenStreetMap"
            )
            
            # 添加地震事件标记
            for _, event in self.events_df.iterrows():
                # 计算震级
                picks = event.get('picks', 0)
                depth = event.get('depth', 10.0)
                rms = event.get('rms', 0.5)
                
                # 基础震级计算
                base_mag = 2.5 + 0.6 * np.log10(max(picks, 1))
                depth_factor = 0.2 * np.log10(max(depth, 1.0) / 10.0)
                rms_factor = -0.1 * min(rms, 1.0)
                mag = min(max(base_mag + depth_factor + rms_factor, 2.0), 8.0)
                
                # 根据震级选择颜色
                if mag >= 6.0:
                    color = 'red'
                elif mag >= 5.0:
                    color = 'orange'
                else:
                    color = 'beige'
                    
                # 根据深度调整标记大小
                radius = min(8 + event['depth'] / 5, 20)  # 稍微小一点以适应嵌入式显示
                
                # 创建弹出窗口内容
                popup_html = f"""
                <div style="width:180px">
                    <h4 style="color:darkgreen;margin:0">M {mag:.1f} 地震</h4>
                    <hr style="margin:3px">
                    <b>时间:</b> {datetime.fromtimestamp(event['time']).strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <b>经度:</b> {event['longitude']:.4f}°<br>
                    <b>纬度:</b> {event['latitude']:.4f}°<br>
                    <b>深度:</b> {event['depth']:.1f} km<br>
                    <b>震级:</b> {mag:.1f}<br>
                </div>
                """
                
                # 添加标记
                folium.CircleMarker(
                    location=(event['latitude'], event['longitude']),
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=250)
                ).add_to(m)
            
            # 添加台站标记（如果有）
            if self.stations_df is not None and not self.stations_df.empty:
                if all(col in self.stations_df.columns for col in ['latitude', 'longitude', 'id']):
                    for _, station in self.stations_df.iterrows():
                        # 添加台站标记
                        folium.Marker(
                            location=(station['latitude'], station['longitude']),
                            icon=folium.Icon(color='blue', icon='info-sign'),
                            popup=f"台站: {station['id']}"
                        ).add_to(m)
            
            # 保存地图为HTML文件
            m.save(self.map_file)
        except Exception as e:
            self.title_label.setText(f"创建地图失败")


class MapVisualizer:
    """地图可视化工具类
    
    提供静态方法来快速创建地图可视化窗口。
    """
    
    @staticmethod
    def show_map_visualization(parent, events_df, stations_df=None):
        """显示地震事件地图可视化对话框
        
        参数:
            parent: 父窗口对象
            events_df: 地震事件数据框
            stations_df: 台站信息数据框（可选）
            
        返回:
            None
        """
        # 检查数据有效性
        if events_df is None or events_df.empty:
            QMessageBox.warning(parent, "警告", "没有地震事件可显示")
            return
            
        # 创建并显示地图对话框
        dialog = MapVisualizerDialog(
            parent=parent,
            events_df=events_df,
            stations_df=stations_df
        )
        
        # 显示对话框
        dialog.exec_()