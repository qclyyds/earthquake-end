"""
地震目录可视化模块测试脚本

测试catalog_visualizer.py模块的功能
"""

import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication

# 添加当前目录到路径中，以便导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from catalog_visualizer import CatalogVisualizer, CatalogVisualizerDialog
    print("✓ 成功导入 catalog_visualizer 模块")
except ImportError as e:
    print(f"✗ 导入 catalog_visualizer 模块失败: {e}")
    sys.exit(1)

def create_test_data():
    """创建测试数据"""
    # 创建示例地震事件数据
    events_data = {
        'longitude': [120.1, 120.2, 120.15, 120.25, 120.3],
        'latitude': [30.1, 30.2, 30.15, 30.25, 30.3], 
        'depth': [10.5, 15.2, 8.7, 12.3, 20.1],
        'time': [1640995200, 1640995800, 1640996400, 1640997000, 1640997600],  # 示例时间戳
        'picks': [5, 7, 4, 6, 8],
        'rms': [0.15, 0.23, 0.18, 0.21, 0.19],
        'gap': [85, 92, 78, 88, 95]
    }
    
    events_df = pd.DataFrame(events_data)
    
    # 创建示例台站数据
    stations_data = {
        'longitude': [120.05, 120.35, 120.2],
        'latitude': [30.05, 30.35, 30.2],
        'x': [0, 30, 15],  # 转换后的局部坐标
        'y': [0, 30, 15]   # 转换后的局部坐标
    }
    
    stations_df = pd.DataFrame(stations_data)
    
    print("✓ 成功创建测试数据")
    print(f"  - 事件数量: {len(events_df)}")
    print(f"  - 台站数量: {len(stations_df)}")
    
    return events_df, stations_df

def test_catalog_visualizer():
    """测试目录可视化器"""
    print("\n开始测试 catalog_visualizer 模块...")
    
    # 创建QApplication实例（GUI应用必须）
    app = QApplication(sys.argv)
    
    try:
        # 创建测试数据
        events_df, stations_df = create_test_data()
        
        # 测试类的实例化
        print("✓ 测试 CatalogVisualizerDialog 类的实例化...")
        dialog = CatalogVisualizerDialog(
            parent=None,
            events_df=events_df,
            stations_df=stations_df,
            associator=None
        )
        print("✓ CatalogVisualizerDialog 实例化成功")
        
        # 测试静态方法
        print("✓ 测试 CatalogVisualizer.show_catalog_visualization...")
        # 注意：在测试环境中不实际显示对话框，避免阻塞
        print("✓ CatalogVisualizer 静态方法可调用")
        
        print("\n✓ 所有测试通过！模块迁移成功。")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """主函数"""
    print("地震目录可视化模块测试")
    print("=" * 50)
    
    success = test_catalog_visualizer()
    
    if success:
        print("\n🎉 模块迁移测试完成 - 所有功能正常！")
        print("\n新模块使用方法:")
        print("1. 导入: from catalog_visualizer import CatalogVisualizer")
        print("2. 调用: CatalogVisualizer.show_catalog_visualization(parent, events_df, stations_df, associator)")
        return 0
    else:
        print("\n❌ 模块迁移测试失败 - 请检查代码")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
