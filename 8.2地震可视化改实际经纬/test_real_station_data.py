#!/usr/bin/env python3
"""
测试台站和地震数据加载，模拟真实的XML和MSEED数据处理流程
"""

import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from obspy import read_inventory, read
from catalog_visualizer import CatalogVisualizer

def load_station_data_from_xml(xml_file):
    """从XML文件加载台站数据"""
    try:
        # 使用ObsPy读取台站文件
        inventory = read_inventory(xml_file)
        
        # 手动提取台站信息
        stations_data = []
        for network in inventory:
            for station in network:
                station_info = {
                    'network': network.code,
                    'station': station.code, 
                    'id': f"{network.code}.{station.code}.",
                    'latitude': station.latitude,
                    'longitude': station.longitude,
                    'elevation': station.elevation
                }
                stations_data.append(station_info)
        
        stations_df = pd.DataFrame(stations_data)
        print(f"从XML加载了 {len(stations_df)} 个台站")
        print("台站数据列:", list(stations_df.columns))
        print("前5个台站:")
        print(stations_df.head())
        
        return stations_df
        
    except Exception as e:
        print(f"加载台站XML失败: {e}")
        return None

def create_mock_earthquake_data():
    """创建模拟的地震事件数据"""
    # 基于智利地区的坐标范围创建地震数据
    num_events = 20
    np.random.seed(42)
    
    # 智利地区大致坐标范围
    base_lat = -21.0  # 基准纬度
    base_lon = -69.8  # 基准经度
    
    # 生成地震事件
    events_data = {
        'latitude': base_lat + np.random.normal(0, 1.0, num_events),
        'longitude': base_lon + np.random.normal(0, 0.8, num_events),
        'depth': np.random.uniform(5, 100, num_events),
        'time': np.random.uniform(1600000000, 1700000000, num_events),
        'picks': np.random.randint(8, 30, num_events),
        'rms': np.random.uniform(0.1, 1.2, num_events),
        'gap': np.random.randint(30, 250, num_events)
    }
    
    events_df = pd.DataFrame(events_data)
    print(f"创建了 {len(events_df)} 个模拟地震事件")
    print("事件数据列:", list(events_df.columns))
    
    return events_df

class TestStationVisualization(QMainWindow):
    """测试台站可视化的窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('台站和地震数据可视化测试')
        self.setGeometry(100, 100, 400, 300)
        
        # 创建界面
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 状态标签
        self.status_label = QLabel("准备加载数据...")
        layout.addWidget(self.status_label)
        
        # 加载数据按钮
        self.load_btn = QPushButton("加载真实台站和地震数据")
        self.load_btn.clicked.connect(self.load_real_data)
        layout.addWidget(self.load_btn)
        
        # 可视化按钮
        self.visualize_btn = QPushButton("显示台站和地震分布图")
        self.visualize_btn.clicked.connect(self.show_visualization)
        self.visualize_btn.setEnabled(False)
        layout.addWidget(self.visualize_btn)
        
        # 数据存储
        self.stations_df = None
        self.events_df = None
        
    def load_real_data(self):
        """加载真实的台站和地震数据"""
        try:
            # 加载台站数据
            xml_path = "e:\\c\\EQ_end\\app\\earthquake-end\\CX1\\CX1\\stations.xml"
            self.stations_df = load_station_data_from_xml(xml_path)
            
            if self.stations_df is None:
                self.status_label.setText("台站数据加载失败")
                return
            
            # 创建模拟地震数据
            self.events_df = create_mock_earthquake_data()
            
            self.status_label.setText(f"数据加载成功 - 台站: {len(self.stations_df)}, 事件: {len(self.events_df)}")
            self.visualize_btn.setEnabled(True)
            
            # 打印数据统计
            print("\n=== 数据统计 ===")
            print(f"台站数量: {len(self.stations_df)}")
            print(f"台站坐标范围:")
            print(f"  纬度: {self.stations_df['latitude'].min():.3f} ~ {self.stations_df['latitude'].max():.3f}")
            print(f"  经度: {self.stations_df['longitude'].min():.3f} ~ {self.stations_df['longitude'].max():.3f}")
            
            print(f"\n事件数量: {len(self.events_df)}")
            print(f"事件坐标范围:")
            print(f"  纬度: {self.events_df['latitude'].min():.3f} ~ {self.events_df['latitude'].max():.3f}")
            print(f"  经度: {self.events_df['longitude'].min():.3f} ~ {self.events_df['longitude'].max():.3f}")
            
        except Exception as e:
            self.status_label.setText(f"加载数据失败: {e}")
            print(f"加载数据失败: {e}")
            
    def show_visualization(self):
        """显示可视化图形"""
        if self.stations_df is None or self.events_df is None:
            self.status_label.setText("请先加载数据")
            return
            
        print("\n=== 开始可视化 ===")
        print("台站数据前5行:")
        print(self.stations_df.head())
        print("\n事件数据前5行:")
        print(self.events_df.head())
        
        # 调用可视化
        CatalogVisualizer.show_catalog_visualization(
            parent=self,
            events_df=self.events_df,
            stations_df=self.stations_df,
            associator=None
        )

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = TestStationVisualization()
    window.show()
    
    print("台站和地震数据可视化测试程序")
    print("1. 点击'加载真实台站和地震数据'按钮")
    print("2. 点击'显示台站和地震分布图'按钮")
    print("3. 观察台站（红色三角形）和地震事件（圆点）的显示")
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
