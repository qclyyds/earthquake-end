#!/usr/bin/env python3
"""
测试修改后的滚动波形显示组件
"""

import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from obspy import Stream, Trace, UTCDateTime
from scrolling_waveform import ScrollingWaveformDisplay

def create_test_stream():
    """创建测试用的波形流数据"""
    stream = Stream()
    
    # 创建多个通道的测试数据
    for i in range(12):  # 创建12个通道，测试滚动功能
        # 生成测试波形数据
        npts = 10000  # 100秒的数据，采样率100Hz
        sampling_rate = 100.0
        delta = 1.0 / sampling_rate
        
        # 创建复合波形：正弦波 + 噪声 + 一些人工"地震"信号
        t = np.linspace(0, npts * delta, npts)
        
        # 基础噪声
        data = np.random.normal(0, 0.1, npts)
        
        # 添加一些正弦波成分
        data += 0.5 * np.sin(2 * np.pi * 0.1 * t)  # 0.1Hz
        data += 0.3 * np.sin(2 * np.pi * 0.05 * t)  # 0.05Hz
        
        # 添加一些"地震"脉冲
        for pulse_time in [20, 45, 70]:
            pulse_start = int(pulse_time * sampling_rate)
            pulse_length = int(5 * sampling_rate)  # 5秒长的脉冲
            if pulse_start + pulse_length < npts:
                # 创建衰减的振荡信号
                pulse_t = np.linspace(0, 5, pulse_length)
                amplitude = 2.0 * np.exp(-pulse_t * 0.5)  # 指数衰减
                frequency = 5.0  # 5Hz振荡
                pulse_signal = amplitude * np.sin(2 * np.pi * frequency * pulse_t)
                data[pulse_start:pulse_start + pulse_length] += pulse_signal
        
        # 创建Trace对象
        stats = {
            'network': 'TEST',
            'station': f'STA{i:02d}',
            'location': '',
            'channel': f'BHZ' if i % 3 == 0 else (f'BHN' if i % 3 == 1 else 'BHE'),
            'starttime': UTCDateTime('2023-01-01T00:00:00'),
            'sampling_rate': sampling_rate,
            'npts': npts
        }
        
        trace = Trace(data=data, header=stats)
        stream.append(trace)
    
    return stream

class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('滚动波形显示组件测试')
        self.setGeometry(100, 100, 1400, 800)
        
        # 创建中央小部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建滚动波形显示组件
        self.waveform_display = ScrollingWaveformDisplay(window_length=30.0)
        layout.addWidget(self.waveform_display)
        
        # 加载测试数据
        self.load_test_data()
    
    def load_test_data(self):
        """加载测试数据"""
        print("正在生成测试数据...")
        stream = create_test_stream()
        print(f"生成了 {len(stream)} 个通道的测试数据")
        
        # 设置到滚动显示组件
        self.waveform_display.set_stream(stream)
        print("测试数据已加载到滚动显示组件")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = TestWindow()
    window.show()
    
    print("测试窗口已显示")
    print("功能测试说明:")
    print("1. **x轴时间刻度测试**: 观察x轴显示的实际时间值")
    print("2. **播放同步测试**: 点击播放，观察x轴时间的实时更新")
    print("3. **窗口长度测试**: 调整窗口长度滑块，观察时间刻度间隔的智能变化")
    print("4. **垂直滚动测试**: 使用▲▼按钮或滑动条浏览不同通道")
    print("5. **窗口大小测试**: 拖拽窗口边缘，观察画布的自动适配")
    print("6. **速度控制测试**: 使用不同播放速度观察x轴变化")
    print("7. **位置跳转测试**: 使用位置滑块跳转到不同时间点")
    print("8. **相位标记测试**: 如有相位数据，验证标记的时间准确性")
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
