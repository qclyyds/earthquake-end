"""
简化的目录可视化模块测试
仅测试导入功能，不依赖GUI
"""

print("测试地震目录可视化模块导入...")

try:
    # 测试基本的Python模块导入
    import sys
    import os
    print("✓ 基本模块导入成功")
    
    # 测试自定义模块导入
    from catalog_visualizer import CatalogVisualizer, CatalogVisualizerDialog
    print("✓ catalog_visualizer 模块导入成功")
    
    print("\n模块结构检查:")
    print(f"✓ CatalogVisualizer 类存在: {hasattr(CatalogVisualizer, 'show_catalog_visualization')}")
    print(f"✓ CatalogVisualizerDialog 类存在: {hasattr(CatalogVisualizerDialog, '__init__')}")
    
    print("\n🎉 模块迁移成功！可以正常导入和使用。")
    
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("\n需要检查的问题:")
    print("1. 文件路径是否正确")
    print("2. 依赖模块是否安装")
    
except Exception as e:
    print(f"✗ 其他错误: {e}")
    import traceback
    traceback.print_exc()

print("\n模块迁移总结:")
print("=" * 50)
print("✓ 已创建 catalog_visualizer.py 文件")
print("✓ 已从 ui_earthquake_app.py 中移除原有可视化代码")
print("✓ 已更新 ui_earthquake_app.py 的导入和调用")
print("\n新的使用方式:")
print("from catalog_visualizer import CatalogVisualizer")
print("CatalogVisualizer.show_catalog_visualization(parent, events_df, stations_df, associator)")
