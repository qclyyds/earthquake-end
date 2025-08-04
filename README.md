# 地震相位检测与事件关联系统

本系统是一个用于地震学研究的可视化分析工具，可以加载、显示、分析地震波形数据，检测地震相位并关联地震事件。

## 主要功能

### 1. 波形数据处理
- 加载地震波形数据 (支持 MSEED、SAC 等格式)
- 波形预处理 (去均值、去趋势、滤波等)
- 支持大型数据文件的分块处理

### 2. 相位检测
- 支持多种深度学习模型进行 P 波和 S 波相位检测
  - EQTransformer
  - PhaseNet
  - PickBlue
  - OBSTransformer
- 自定义检测阈值调整

### 3. 事件关联
- 将检测到的相位关联为地震事件
- 基于 PyOcto 关联引擎
- 地震定位与震源参数估计

### 4. 实时监测模拟
- 横向滚动显示波形数据
- 多种速度选项 (0.25x 至超快模式)
- 可调整显示窗口长度
- 自定义通道选择

### 5. 数据可视化
- 地震事件的二维和三维可视化
- 可交互式探索事件空间分布
- 多通道波形同步显示
- 基于OpenStreetMap的地震事件地图定位

### 6. 导出功能
- 导出检测结果和关联事件为 CSV 格式
- 导出图像为图形文件
- 生成分析报告

## 系统要求

- Python 3.8+
- 依赖库：
  - PyQt5
  - ObsPy
  - NumPy
  - Matplotlib
  - Pandas
  - SeisBench (用于神经网络模型)
  - PyOcto (用于事件关联)

## 安装指南

1. 克隆代码库：
   ```
   git clone https://github.com/yourusername/earthquake-analysis-system.git
   cd earthquake-analysis-system
   ```

2. 创建虚拟环境（推荐）：
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 启动应用程序：
   ```
   python main.py
   ```

## 使用指南

### 波形分析

1. 点击"加载波形"按钮加载地震数据文件
2. 选择适当的分块大小（适用于大文件）
3. 选择模型和检测阈值
4. 点击"相位检测"进行 P 波和 S 波检测
5. 点击"关联事件"分析地震事件

### 实时监测

1. 加载波形数据后，点击"实时模拟"按钮
2. 选择需要显示的通道（建议选择1-3个通道）
3. 使用控制面板调整播放速度和窗口长度
4. 通过播放/暂停按钮控制模拟流程
5. 使用位置滑块快速定位到感兴趣的位置

### 地震事件可视化

1. 完成事件关联后，点击"可视化目录"按钮
2. 查看震源位置的空间分布
3. 查看事件参数列表
4. 使用地图定位功能在OpenStreetMap上查看地震事件位置
