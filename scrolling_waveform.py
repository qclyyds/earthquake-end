import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QPushButton, QLabel, QComboBox, QCheckBox, QScrollArea, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from obspy import Stream, Trace, UTCDateTime
import time

class ScrollingWaveformDisplay(QWidget):
    """滚动波形显示组件 - 实现在已加载波形上的滑动窗口模拟"""
    
    def __init__(self, window_length=60.0):
        """
        初始化滚动波形显示组件
        
        参数:
        - window_length: 显示窗口长度（秒）
        """
        super().__init__()
        self.window_length = window_length  # 窗口长度（秒）
        self.stream = None  # 存储原始波形流
        self.lines = {}  # 每个通道的线条对象
        self.axes = {}  # 每个通道的坐标轴对象
        self.sampling_rate = 100.0  # 默认采样率
        self.current_position = 0  # 当前滑动窗口位置（秒）
        self.max_position = 0  # 最大位置（即数据总时长）
        self.channel_colors = ['r', 'b', 'g', 'c', 'm', 'y', 'k']  # 通道颜色循环
        self.auto_scale_y = False  # 默认不自动缩放Y轴，保持与原图像一致
        self.is_streaming = False  # 是否正在模拟流
        self.speed_factor = 1.0  # 播放速度
        self.picks = []  # 存储相位检测结果
        
        # 创建UI
        self.init_ui()
        
        # 创建定时器，用于模拟滚动
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.update_window_position)
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 创建matplotlib图形
        self.figure = Figure(figsize=(14, 8))
        self.canvas = FigureCanvas(self.figure)
        
        # 设置canvas的大小策略，使其能够随窗口大小调整而伸缩
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(400)  # 设置最小高度确保图形可见
        
        # 创建一个滚动区域来容纳画布，以防图形太大
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)  # 允许画布调整大小
        layout.addWidget(scroll_area, 1)  # 使用权重1使它占据大部分空间
        
        # 创建控制面板
        control_panel = QHBoxLayout()
        
        # 播放/暂停按钮
        self.play_pause_btn = QPushButton("播放")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        control_panel.addWidget(self.play_pause_btn)
        
        # 播放速度选择
        speed_label = QLabel("速度:")
        control_panel.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "2.0x", "4.0x", "10.0x", "超快"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        control_panel.addWidget(self.speed_combo)
        
        # 窗口长度控制
        window_label = QLabel("窗口长度(秒):")
        control_panel.addWidget(window_label)
        
        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setMinimum(10)
        self.window_slider.setMaximum(300)
        self.window_slider.setValue(int(self.window_length))
        self.window_slider.setTickPosition(QSlider.TicksBelow)
        self.window_slider.setTickInterval(30)
        self.window_slider.valueChanged.connect(self.change_window_length)
        control_panel.addWidget(self.window_slider)
        
        self.window_value_label = QLabel(f"{self.window_length}s")
        control_panel.addWidget(self.window_value_label)
        
        # 自动缩放Y轴
        self.auto_scale_checkbox = QCheckBox("自动Y轴")
        self.auto_scale_checkbox.setChecked(self.auto_scale_y)
        self.auto_scale_checkbox.stateChanged.connect(self.toggle_auto_scale)
        control_panel.addWidget(self.auto_scale_checkbox)
        
        # 添加重置按钮
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_position)
        control_panel.addWidget(self.reset_btn)
        
        # 将控制面板添加到主布局
        control_layout = QWidget()
        control_layout.setLayout(control_panel)
        layout.addWidget(control_layout)
        
        # 位置滑块
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("位置:"))
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(100)  # 使用百分比
        self.position_slider.setValue(0)
        self.position_slider.setTickPosition(QSlider.TicksBelow)
        self.position_slider.setTickInterval(10)
        self.position_slider.valueChanged.connect(self.slider_position_changed)
        position_layout.addWidget(self.position_slider, 1)
        
        self.position_label = QLabel("0.0s / 0.0s")
        position_layout.addWidget(self.position_label)
        
        position_widget = QWidget()
        position_widget.setLayout(position_layout)
        layout.addWidget(position_widget)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def set_stream(self, stream):
        """设置要显示的波形流"""
        if not stream or len(stream) == 0:
            return
            
        # 保存原始流数据
        self.stream = stream
        
        # 获取流的时间范围和采样率
        self.sampling_rate = stream[0].stats.sampling_rate
        duration = max([tr.stats.endtime - tr.stats.starttime for tr in stream])
        self.max_position = duration
        self.current_position = 0
        
        # 更新位置滑块
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(100)  # 使用百分比
        self.position_slider.setValue(0)
        self.update_position_label()
        
        # 初始化图形显示
        self.init_plot()
        
    def init_plot(self):
        """初始化绘图"""
        if not self.stream:
            return
            
        # 清除当前图表
        self.figure.clear()
        self.lines = {}
        self.axes = {}
        
        # 为每个通道创建子图
        num_traces = len(self.stream)
        
        # 设置更合适的图形大小，针对少量通道
        height_per_trace = 3.0  # 减小每个通道的高度，使波形看起来更宽
        self.figure.set_size_inches(28, num_traces * height_per_trace)  # 增加宽度，保持相对高度
        
        # 计算全局Y轴范围，确保所有通道使用相同的缩放
        global_y_ranges = {}
        for trace in self.stream:
            # 计算整个波形的全局范围
            data = trace.data
            if len(data) > 0:
                y_min, y_max = np.min(data), np.max(data)
                # 如果振幅太小，设置一个合理的默认范围
                if abs(y_max - y_min) < 0.001:
                    y_min, y_max = -1, 1
                # 添加边距
                margin = (y_max - y_min) * 0.1
                global_y_ranges[trace.id] = (y_min - margin, y_max + margin)
            else:
                global_y_ranges[trace.id] = (-1, 1)
        
        # 创建子图并调整纵横比使波形更加拉长
        for i, trace in enumerate(self.stream):
            # 创建子图，但高度更小以使波形拉长
            ax = self.figure.add_subplot(num_traces, 1, i+1)
            ax.set_ylabel(trace.id, fontsize=10)
            
            # 调整子图的纵横比，使波形看起来更加拉长
            box = ax.get_position()
            # 减小高度，保持位置
            ax.set_position([box.x0, box.y0, box.width, box.height * 0.8])
            
            if i == num_traces - 1:  # 最后一个子图添加x轴标签
                ax.set_xlabel('时间 (s)', fontsize=10)
            else:
                ax.set_xticklabels([])  # 非最后一个子图隐藏x轴刻度标签
            
            # 创建空线条，使用不同颜色区分通道
            color_idx = i % len(self.channel_colors)
            line, = ax.plot([], [], self.channel_colors[color_idx], linewidth=1.5)
            
            # 添加网格
            ax.grid(True, alpha=0.3)
            
            # 设置初始轴范围
            ax.set_xlim(0, self.window_length)
            
            # 设置Y轴范围为全局范围
            ax.set_ylim(*global_y_ranges[trace.id])
            
            # 存储线条和轴对象
            self.lines[trace.id] = line
            self.axes[trace.id] = ax
        
        # 添加标题
        if num_traces > 0:
            start_time_str = self.stream[0].stats.starttime.strftime('%Y-%m-%d %H:%M:%S')
            self.figure.suptitle(f"地震波形监测 - {start_time_str}", fontsize=14, y=0.99)
        
        # 优化布局 - 增加水平方向的空间
        self.figure.tight_layout(pad=1.0, rect=[0.01, 0.03, 0.99, 0.95])
        self.canvas.draw()
        
    def update_window_position(self):
        """更新滑动窗口位置"""
        if not self.stream or not self.is_streaming:
            return
            
        # 更新位置
        if self.speed_factor == -1:
            # 超快模式，每次前进10秒
            new_position = self.current_position + 10
        else:
            # 普通模式，根据速度因子调整前进速度
            new_position = self.current_position + 0.1 * self.speed_factor
        
        # 检查是否到达末尾
        if new_position >= self.max_position - self.window_length:
            new_position = 0  # 循环回到开始
            self.status_label.setText("已到达波形末尾，重新开始")
        
        # 设置新位置
        self.current_position = new_position
        self.update_plot()
        
        # 更新滑块位置（不触发事件）
        self.position_slider.blockSignals(True)
        position_percent = int(100 * self.current_position / max(1, self.max_position - self.window_length))
        self.position_slider.setValue(position_percent)
        self.position_slider.blockSignals(False)
        
        # 更新位置标签
        self.update_position_label()
    
    def update_plot(self):
        """更新图表，显示当前窗口位置的数据"""
        if not self.stream:
            return
        
        # 计算当前窗口的时间范围
        window_start = self.current_position
        window_end = window_start + self.window_length
        
        # 更新每个通道的数据
        for i, trace in enumerate(self.stream):
            trace_id = trace.id
            if trace_id not in self.lines:
                continue
                
            # 获取对应时间范围的数据
            start_sample = int(window_start * self.sampling_rate)
            end_sample = int(window_end * self.sampling_rate)
            
            # 确保采样点位于有效范围内
            start_sample = max(0, min(start_sample, len(trace.data) - 1))
            end_sample = max(0, min(end_sample, len(trace.data)))
            
            if start_sample >= end_sample:
                continue
            
            # 获取数据片段
            data_slice = trace.data[start_sample:end_sample]
            
            # 计算对应的时间点 - 使用更密集的点以提高显示平滑度
            times = np.linspace(0, min(self.window_length, (end_sample - start_sample) / self.sampling_rate), len(data_slice))
            
            # 更新线条数据
            self.lines[trace_id].set_data(times, data_slice)
            
            # 仅在启用自动缩放时调整Y轴范围
            if self.auto_scale_y:
                y_min, y_max = np.min(data_slice), np.max(data_slice)
                if abs(y_max - y_min) < 0.001:  # 避免平坦波形没有范围
                    y_min, y_max = -1, 1
                margin = (y_max - y_min) * 0.1 if y_max > y_min else 0.1
                self.axes[trace_id].set_ylim(y_min - margin, y_max + margin)
            
            # 显示相位检测结果
            if self.picks:
                # 获取当前通道的相位检测结果
                channel_id = '.'.join(trace.id.split('.', 2)[:2])  # 提取通道ID
                channel_picks = [p for p in self.picks if p['channel'] == channel_id]
                
                # 清除之前的相位标记
                for artist in self.axes[trace_id].lines + self.axes[trace_id].texts:
                    if artist != self.lines[trace_id]:  # 保留波形线条
                        artist.remove()
                
                # 添加相位标记
                for pick in channel_picks:
                    # 计算相位时间相对于当前窗口的位置
                    pick_time_rel = pick['time'] - (trace.stats.starttime + window_start)
                    
                    # 只显示当前窗口内的相位
                    if 0 <= pick_time_rel <= self.window_length:
                        # 绘制相位线
                        color = 'red' if pick['phase'] == 'P' else 'blue'
                        self.axes[trace_id].axvline(pick_time_rel, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
                        
                        # 添加相位标签
                        y_position = self.axes[trace_id].get_ylim()[1] * 0.8
                        self.axes[trace_id].text(pick_time_rel + 0.5, y_position,
                                f"{pick['phase']}\n{pick['probability']:.2f}",
                                color=color, va='top', fontsize=10, 
                                bbox=dict(facecolor='white', alpha=0.7, pad=2))
        
        # 更新标题显示当前时间
        if len(self.stream) > 0:
            current_time = self.stream[0].stats.starttime + self.current_position
            title = f"地震波形监测 - {current_time.strftime('%Y-%m-%d %H:%M:%S')} (位置: {self.current_position:.1f}s)"
            self.figure.suptitle(title, fontsize=14, y=0.99)
        
        # 重绘画布
        self.canvas.draw_idle()
    
    def start_streaming(self):
        """开始模拟波形滚动"""
        if not self.stream:
            self.status_label.setText("错误: 没有波形数据")
            return
            
        self.is_streaming = True
        self.play_pause_btn.setText("暂停")
        self.status_label.setText(f"正在模拟波形滚动 (速度: {self.speed_factor}x)")
        
        # 启动定时器，每100毫秒更新一次
        self.scroll_timer.start(100)
    
    def stop_streaming(self):
        """停止模拟波形滚动"""
        self.is_streaming = False
        self.play_pause_btn.setText("播放")
        self.status_label.setText("滚动已暂停")
        
        # 停止定时器
        self.scroll_timer.stop()
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.is_streaming:
            self.stop_streaming()
        else:
            self.start_streaming()
    
    def change_speed(self, speed_text):
        """更改播放速度"""
        if speed_text == "超快":
            # 特殊处理超快模式，每次更新前进10秒
            self.speed_factor = -1  # 使用-1标记超快模式
        else:
            speed = float(speed_text.replace('x', ''))
            self.speed_factor = speed
        
        if self.is_streaming:
            if self.speed_factor == -1:
                self.status_label.setText(f"正在模拟波形滚动 (速度: 超快)")
            else:
                self.status_label.setText(f"正在模拟波形滚动 (速度: {self.speed_factor}x)")
    
    def change_window_length(self, value):
        """更改显示窗口长度"""
        self.window_length = float(value)
        self.window_value_label.setText(f"{self.window_length}s")
        
        # 更新所有轴的x范围
        for ax in self.axes.values():
            ax.set_xlim(0, self.window_length)
        
        # 更新显示
        self.update_plot()
    
    def toggle_auto_scale(self, state):
        """切换自动Y轴缩放"""
        self.auto_scale_y = state == Qt.Checked
        if self.auto_scale_y:
            self.update_plot()  # 立即更新以应用自动缩放
    
    def slider_position_changed(self, value):
        """处理位置滑块值变化"""
        # 根据百分比计算实际位置
        position_percent = value / 100.0
        new_position = position_percent * max(0, self.max_position - self.window_length)
        
        # 设置新位置
        self.current_position = new_position
        
        # 更新位置标签
        self.update_position_label()
        
        # 更新图表
        self.update_plot()
    
    def update_position_label(self):
        """更新位置标签"""
        self.position_label.setText(f"{self.current_position:.1f}s / {self.max_position:.1f}s")
    
    def reset_position(self):
        """重置到波形起始位置"""
        self.current_position = 0
        
        # 更新滑块位置
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(0)
        self.position_slider.blockSignals(False)
        
        # 更新图表
        self.update_plot()
        
        # 更新位置标签
        self.update_position_label()
        
        self.status_label.setText("已重置到波形起始位置") 
        
    def set_picks(self, picks):
        """设置相位检测结果
        
        参数:
        - picks: 相位检测结果列表，每个元素是一个字典，包含time, phase, channel, probability等键
        """
        self.picks = picks
        # 如果当前正在显示波形，则更新图表以显示相位标记
        if self.stream:
            self.update_plot()