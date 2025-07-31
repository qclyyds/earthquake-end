"""
地震目录可视化模块使用示例

展示如何使用新迁移的catalog_visualizer模块
"""

# 使用示例1: 完整的可视化对话框
def example_full_visualization():
    """完整的可视化对话框示例"""
    from catalog_visualizer import CatalogVisualizer
    import pandas as pd
    
    # 假设你已经有了地震事件数据
    events_df = pd.DataFrame({
        'longitude': [120.1, 120.2, 120.15],
        'latitude': [30.1, 30.2, 30.15], 
        'depth': [10.5, 15.2, 8.7],
        'time': [1640995200, 1640995800, 1640996400],
        'picks': [5, 7, 4]
    })
    
    # 台站数据（可选）
    stations_df = pd.DataFrame({
        'x': [0, 30, 15],
        'y': [0, 30, 15]
    })
    
    # 调用可视化
    CatalogVisualizer.show_catalog_visualization(
        parent=None,  # 如果在主窗口中调用，传入self
        events_df=events_df,
        stations_df=stations_df,
        associator=None  # 如果有关联器，传入关联器对象
    )


# 使用示例2: 仅绘制图形到现有Figure
def example_plot_only():
    """仅绘制图形示例"""
    from catalog_visualizer import CatalogVisualizer
    from matplotlib.figure import Figure
    import pandas as pd
    
    # 创建数据
    events_df = pd.DataFrame({
        'longitude': [120.1, 120.2, 120.15],
        'latitude': [30.1, 30.2, 30.15], 
        'depth': [10.5, 15.2, 8.7],
        'time': [1640995200, 1640995800, 1640996400],
        'picks': [5, 7, 4]
    })
    
    # 创建matplotlib图形
    figure = Figure(figsize=(10, 8))
    
    # 绘制到指定图形
    ax = CatalogVisualizer.plot_events_only(
        figure=figure,
        events_df=events_df,
        stations_df=None,
        associator=None
    )
    
    # 可以进一步自定义图形
    if ax:
        ax.set_title("自定义地震事件分布图")
    
    return figure


# 使用示例3: 在主程序类中的集成方式
class ExampleSeismicApp:
    """示例地震应用程序类"""
    
    def __init__(self):
        self.events_df = None
        self.stations_df = None
        self.associator = None
    
    def visualize_catalog(self):
        """可视化地震目录 - 新的实现方式"""
        from catalog_visualizer import CatalogVisualizer
        
        # 检查数据是否存在
        if self.events_df is None or self.events_df.empty:
            print("警告: 没有地震事件数据可显示")
            return
        
        # 调用可视化模块
        CatalogVisualizer.show_catalog_visualization(
            parent=self,  # 传入当前窗口作为父窗口
            events_df=self.events_df,
            stations_df=self.stations_df,
            associator=self.associator
        )


# 使用示例4: 兼容性调用（保持原有代码不变）
def example_compatibility():
    """使用兼容性函数"""
    from catalog_visualizer import visualize_catalog, plot_3d_from_dataframe
    from matplotlib.figure import Figure
    import pandas as pd
    
    events_df = pd.DataFrame({
        'longitude': [120.1, 120.2],
        'latitude': [30.1, 30.2], 
        'depth': [10.5, 15.2],
        'time': [1640995200, 1640995800],
        'picks': [5, 7]
    })
    
    # 方式1: 使用兼容性函数显示对话框
    visualize_catalog(
        parent=None,
        events_df=events_df,
        stations_df=None,
        associator=None
    )
    
    # 方式2: 使用兼容性函数绘制图形
    figure = Figure()
    plot_3d_from_dataframe(
        figure=figure,
        events_df=events_df,
        stations_df=None,
        associator=None
    )


if __name__ == "__main__":
    print("地震目录可视化模块使用示例")
    print("=" * 50)
    print("1. example_full_visualization() - 完整对话框")
    print("2. example_plot_only() - 仅绘制图形")
    print("3. ExampleSeismicApp - 类中集成")
    print("4. example_compatibility() - 兼容性调用")
    print("\n请根据需要选择合适的使用方式！")
