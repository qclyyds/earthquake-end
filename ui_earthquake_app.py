import sys
import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                             QComboBox, QToolBar, QAction, QMessageBox, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView,
                             QDialog, QProgressBar, QDateTimeEdit, QCheckBox, 
                             QGroupBox, QFormLayout, QDialogButtonBox, QSpinBox,
                             QSizePolicy)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QPixmap, QIcon, QFont
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from obspy import read, read_inventory, UTCDateTime
from datetime import datetime

# 导入我们的地震处理功能文件
from seismic_processor import (WaveformLoadThread, PhaseDetectionThread, 
                             EventAssociationThread, load_neural_model, setup_associator)

# 导入滚动波形显示组件
from scrolling_waveform import ScrollingWaveformDisplay

# 导入地震目录可视化模块
from catalog_visualizer import CatalogVisualizer

# 时间窗口选择对话框
class TimeWindowDialog(QDialog):
    def __init__(self, parent=None, start_time=None, end_time=None):
        super().__init__(parent)
        self.setWindowTitle("选择加载波形方式")
        self.resize(400, 300)
        
         # 添加分块处理参数
        self.current_file = None  # 当前加载的文件路径
        self.chunk_mode = False  # 是否使用分块模式
        self.chunk_size = None  # 分块大小（秒）
        self.time_window = {  # 时间窗口
            'start_time': None,
            'end_time': None
        }
        
        # 添加分块导航参数
        self.current_chunk_index = 0  # 当前分块索引
        self.total_chunks = 0  # 总分块数
        self.original_start_time = None  # 原始波形的起始时间
        self.original_end_time = None  # 原始波形的结束时间

        # 初始化起始和结束时间
        self.start_time = start_time or UTCDateTime()
        self.end_time = end_time or self.start_time + 3600  # 默认1小时
        
        # 创建布局
        main_layout = QVBoxLayout(self)
        
        # 添加说明标签
        info_label = QLabel("请选择波形数据加载方式：")
        info_label.setFont(QFont("Arial", 11, QFont.Bold))
        main_layout.addWidget(info_label)
        
        # 创建时间选择模式
        self.mode_group = QGroupBox("选择模式")
        mode_layout = QVBoxLayout()
        
        # 全部加载选项
        self.full_load_radio = QCheckBox("加载全部波形")
        self.full_load_radio.setChecked(True)
        self.full_load_radio.stateChanged.connect(self.toggle_time_inputs)
        mode_layout.addWidget(self.full_load_radio)
        
        # 分块处理选项
        self.chunk_process_radio = QCheckBox("分块加载（适用于非常大的文件）")
        self.chunk_process_radio.stateChanged.connect(self.toggle_time_inputs)
        mode_layout.addWidget(self.chunk_process_radio)
        
        self.mode_group.setLayout(mode_layout)
        main_layout.addWidget(self.mode_group)
        
        # 创建分块设置组
        self.time_group = QGroupBox("分块设置")
        time_layout = QFormLayout()
        
        # 分块大小（分钟）
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 60)
        self.chunk_size_spin.setValue(10)  # 默认10分钟
        self.chunk_size_spin.setSuffix(" 分钟")
        time_layout.addRow("分块大小:", self.chunk_size_spin)
        
        self.time_group.setLayout(time_layout)
        main_layout.addWidget(self.time_group)
        
        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # 初始状态
        self.toggle_time_inputs()
    
    def toggle_time_inputs(self):
        """根据选择的模式启用或禁用分块设置控件"""
        chunk_mode = self.chunk_process_radio.isChecked()
        
        # 禁用或启用分块相关控件
        self.chunk_size_spin.setEnabled(chunk_mode)
        
        # 确保只有一个选项被选中
        if self.sender() == self.full_load_radio and self.full_load_radio.isChecked():
            self.chunk_process_radio.setChecked(False)
        elif self.sender() == self.chunk_process_radio and self.chunk_process_radio.isChecked():
            self.full_load_radio.setChecked(False)
    
    def get_parameters(self):
        """返回对话框参数"""
        if self.full_load_radio.isChecked():
            return {
                'mode': 'full',
                'start_time': None,
                'end_time': None,
                'chunk_size': None
            }
        elif self.chunk_process_radio.isChecked():
            return {
                'mode': 'chunk',
                'start_time': None,
                'end_time': None,
                'chunk_size': self.chunk_size_spin.value() * 60  # 转换为秒
            }
        return None

# 主应用程序窗口类
class SeismicPhasePicker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Seismic Phase Picker')  # 设置窗口标题
        self.setGeometry(200, 100, 1800, 1000)  # 设置窗口大小和位置
        
        # 初始化变量
        self.stream = None
        self.picks = []
        self.model = None
        self.catalog = None  # 存储关联结果的目录
        self.associator = None  # PyOcto关联器
        self.inventory = None  # ObsPy台站目录
        self.stations_df = None  # 测站信息数据框
        self.events_df = None  # 事件数据框
        self.assignments_df = None  # 相位关联数据框
        
        # 添加分块处理参数
        self.current_file = None  # 当前加载的文件路径
        self.chunk_mode = False  # 是否使用分块模式
        self.chunk_size = None  # 分块大小（秒）
        self.time_window = {  # 时间窗口
            'start_time': None,
            'end_time': None
        }
        
        # 设置用户界面
        self.setup_ui()
        
        # 自动加载默认模型
        self.load_model("EQTransformer")  # 你可以选择其他默认模型，如 "PhaseNet", "PickBlue", "OBSTransformer"
        
        # 配置关联器
        self.setup_associator()
    
    def setup_ui(self):
        """设置用户界面"""
        

        # 添加进度条
        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)  # 初始可见
        
        # 创建中央小部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
         # 添加分块导航按钮
        self.prev_chunk_btn = QAction(QIcon("icons/prev.png") if os.path.exists("icons/prev.png") else QIcon(), "上一段", self)
        self.prev_chunk_btn.setStatusTip("加载上一个数据块")
        self.prev_chunk_btn.triggered.connect(self.load_previous_chunk)
        self.prev_chunk_btn.setEnabled(False)  # 初始禁用
        
        self.next_chunk_btn = QAction(QIcon("icons/next.png") if os.path.exists("icons/next.png") else QIcon(), "下一段", self)
        self.next_chunk_btn.setStatusTip("加载下一个数据块")
        self.next_chunk_btn.triggered.connect(self.load_next_chunk)
        self.next_chunk_btn.setEnabled(False)  # 初始禁用
        
        # 添加分块导航状态标签
        self.chunk_status_label = QLabel("未使用分块模式")
        
        # 将分块导航按钮添加到工具栏
        toolbar.addSeparator()
        toolbar.addAction(self.prev_chunk_btn)
        toolbar.addAction(self.next_chunk_btn)
        toolbar.addWidget(self.chunk_status_label)

        # 添加模型选择
        model_label = QLabel("模型：")
        toolbar.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(['EQTransformer', 'PhaseNet', 'PickBlue', 'OBSTransformer'])
        self.model_combo.currentTextChanged.connect(self.on_model_change)
        toolbar.addWidget(self.model_combo)
        
        # 添加加载波形按钮
        load_btn = QPushButton("加载波形")
        load_btn.clicked.connect(self.load_waveform)
        toolbar.addWidget(load_btn)
        
        # 添加加载台站目录按钮
        load_inv_btn = QPushButton("加载台站目录")
        load_inv_btn.clicked.connect(self.load_inventory)
        toolbar.addWidget(load_inv_btn)
        
        # 添加相位检测按钮
        pick_btn = QPushButton("相位检测")
        pick_btn.clicked.connect(self.detect_phases)
        toolbar.addWidget(pick_btn)
        
        # 添加关联按钮
        associate_btn = QPushButton("关联事件")
        associate_btn.clicked.connect(self.associate_events)
        toolbar.addWidget(associate_btn)
        
        # 添加可视化按钮
        visualize_btn = QPushButton("可视化目录")
        visualize_btn.clicked.connect(self.visualize_catalog)
        toolbar.addWidget(visualize_btn)
        
        # 添加实时模拟按钮
        stream_btn = QPushButton("实时模拟")
        stream_btn.clicked.connect(self.toggle_streaming_mode)
        toolbar.addWidget(stream_btn)
        
        # 添加阈值选择
        threshold_label = QLabel("阈值：")
        toolbar.addWidget(threshold_label)
        self.threshold_combo = QComboBox()
        self.threshold_combo.addItems(['0.3', '0.4', '0.5', '0.6', '0.7'])
        self.threshold_combo.setCurrentText('0.5')
        toolbar.addWidget(self.threshold_combo)
        
        # 添加清除按钮
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self.clear_picks)
        toolbar.addWidget(clear_btn)
        
        # 添加导出图像按钮
        export_img_btn = QPushButton("导出图像")
        export_img_btn.clicked.connect(self.export_image)
        toolbar.addWidget(export_img_btn)
        
        # 添加导出报告按钮
        export_report_btn = QPushButton("导出报告")
        export_report_btn.clicked.connect(self.export_report)
        toolbar.addWidget(export_report_btn)
        
        # 添加导出目录按钮
        export_catalog_btn = QPushButton("导出目录")
        export_catalog_btn.clicked.connect(self.export_catalog)
        toolbar.addWidget(export_catalog_btn)
        
        # 添加帮助按钮
        help_btn = QPushButton("帮助")
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建波形显示标签页
        self.waveform_tab = QWidget()
        waveform_layout = QVBoxLayout(self.waveform_tab)
        
        # 创建滚动区域，专门用于图表显示
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # 设置滚动条策略为始终显示
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # 创建一个容器小部件来放置 matplotlib 图形
        self.plot_widget = QWidget()  # 修改为实例变量
        plot_layout = QVBoxLayout(self.plot_widget)
        
        # 创建 matplotlib 图形
        self.figure = Figure(figsize=(16, 16))  # 增大图形尺寸
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(1200, 600)  # 设置最小尺寸，确保内容不会被缩小
        plot_layout.addWidget(self.canvas)
        
        # 将图形容器添加到滚动区域
        scroll_area.setWidget(self.plot_widget)
        waveform_layout.addWidget(scroll_area)
        
        # 创建实时滚动波形标签页
        self.streaming_tab = QWidget()
        streaming_layout = QVBoxLayout(self.streaming_tab)
        
        # 创建滚动波形显示组件
        self.scrolling_display = ScrollingWaveformDisplay(window_length=30.0)
        streaming_layout.addWidget(self.scrolling_display)
        
        # 将标签页添加到标签页控件
        self.tab_widget.addTab(self.waveform_tab, "波形分析")
        self.tab_widget.addTab(self.streaming_tab, "实时监测")
        
        # 添加状态栏、进度条
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.progress_bar)
        
        # 将状态栏添加到主布局
        main_layout.addLayout(status_layout)
        
        # 添加 logo (在滚动区域之外)
        self.logo_label = QLabel()
        try:
            logo_pixmap = QPixmap(r"LOGO.jpg") 
            logo_pixmap = logo_pixmap.scaledToWidth(800, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        except:
            self.logo_label.setText("Logo 未找到")
        self.logo_label.setScaledContents(True)
        main_layout.addWidget(self.logo_label)
        
        # 初始化空图
        self.update_plot()
        
    def on_model_change(self, model_name):
        """当模型选择改变时加载新模型"""
        self.status_label.setText(f"正在加载 {model_name} 模型...")
        self.load_model(model_name)
        
    def load_model(self, model_name):
        """加载神经网络模型"""
        self.model, err = load_neural_model(model_name)
        if err:
            QMessageBox.warning(self, "模型加载错误", f"加载模型失败: {err}")
            self.status_label.setText(f"模型加载失败: {err}")
        else:
            self.status_label.setText(f"{model_name} 模型加载成功")
    
    def setup_associator(self):
        """配置地震关联器"""
        self.associator, err = setup_associator()
        if err:
            QMessageBox.warning(self, "关联器配置错误", f"配置关联器失败: {err}")
        
    def load_waveform(self):
        """用支持时间窗口和分块处理的方式加载波形数据"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "选择波形文件", "",
                "波形文件 (*.mseed *.sac *.segy);;所有文件 (*)")
            
            if not filename:
                return
            
            self.current_file = filename
            
            # 首先尝试读取文件头，获取时间范围
            try:
                temp_stream = read(filename, headonly=True)
                if temp_stream:
                    start_time = min([tr.stats.starttime for tr in temp_stream])
                    end_time = max([tr.stats.endtime for tr in temp_stream])
                    
                    # 保存原始时间范围
                    self.original_start_time = start_time
                    self.original_end_time = end_time
                    
                    # 显示时间窗口选择对话框
                    time_dialog = TimeWindowDialog(self, start_time, end_time)
                    if time_dialog.exec_() == QDialog.Accepted:
                        params = time_dialog.get_parameters()
                        
                        if params['mode'] == 'full':
                            # 全部加载模式
                            self.chunk_mode = False
                            self.time_window['start_time'] = None
                            self.time_window['end_time'] = None
                            self.chunk_size = None
                            
                            # 禁用分块导航按钮
                            self.prev_chunk_btn.setEnabled(False)
                            self.next_chunk_btn.setEnabled(False)
                            self.chunk_status_label.setText("未使用分块模式")
                            
                            # 在线程中加载波形
                            self.load_thread = WaveformLoadThread(filename)
                            
                        elif params['mode'] == 'chunk':
                            # 分块处理模式
                            self.chunk_mode = True
                            self.time_window['start_time'] = start_time
                            self.time_window['end_time'] = end_time
                            self.chunk_size = params['chunk_size']
                            
                            # 计算总分块数
                            total_duration = end_time - start_time
                            self.total_chunks = int(np.ceil(total_duration / self.chunk_size))
                            self.current_chunk_index = 0
                            
                            # 启用分块导航按钮
                            self.prev_chunk_btn.setEnabled(False)  # 第一块，禁用上一块按钮
                            self.next_chunk_btn.setEnabled(self.total_chunks > 1)  # 如果有多个块，启用下一块按钮
                            
                            # 更新分块状态标签
                            self.update_chunk_status_label()
                            
                            # 加载第一个数据块
                            chunk_start = start_time
                            chunk_end = min(chunk_start + self.chunk_size, end_time)
                            
                            # 在线程中加载波形
                            self.load_thread = WaveformLoadThread(filename, chunk_start, chunk_end)
                        
                        # 连接线程信号
                        self.load_thread.progressChanged.connect(self.update_progress)
                        self.load_thread.finished.connect(self.on_waveform_loaded)
                        self.load_thread.error.connect(self.on_thread_error)
                        self.load_thread.statusUpdate.connect(self.update_status)
                        
                        # 初始化进度条
                        self.status_label.setText("正在加载波形数据...")
                        self.progress_bar.setValue(0)
                        self.progress_bar.setVisible(True)
                        
                        # 启动线程
                        self.load_thread.start()
                    else:
                        # 用户取消
                        return
                    
            except Exception as e:
                # 如果读取头信息失败，回退到常规加载方式
                self.status_label.setText(f"读取文件头失败: {str(e)}，尝试直接加载...")
                self.stream = read(filename)
                self.stream.detrend('linear')
                
                # 获取采样率
                sampling_rate = self.stream[0].stats.sampling_rate
                nyquist = sampling_rate / 2.0
                
                # 确保高截止频率低于奈奎斯特频率
                freqmax = min(20.0, nyquist - 0.1)
                
                self.stream.filter('bandpass', freqmin=1.0, freqmax=freqmax)
                self.picks = []
                self.update_plot()
                self.status_label.setText(f"已加载波形，共 {len(self.stream)} 个通道")
                
        except Exception as e:
            QMessageBox.warning(self, "加载错误", f"加载波形文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"加载波形失败: {str(e)}")
    
    def on_waveform_loaded(self, stream):
        """波形加载完成后的回调函数"""
        if self.chunk_mode:
            self.on_chunk_loaded(stream)
        else:
            self.stream = stream
            self.update_plot()
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"已加载 {len(self.stream)} 个波形通道")
        
        # 不再自动设置滚动波形显示数据，等用户点击实时模拟按钮时再设置
    
    def load_previous_chunk(self):
        """加载上一个数据块"""
        if not self.chunk_mode or self.current_chunk_index <= 0:
            return
        
        # 更新当前块索引
        self.current_chunk_index -= 1
        
        # 计算时间窗口
        chunk_start = self.original_start_time + self.current_chunk_index * self.chunk_size
        chunk_end = min(chunk_start + self.chunk_size, self.original_end_time)
        
        # 加载数据块
        self.load_chunk(chunk_start, chunk_end)
        
        # 更新导航按钮状态
        self.prev_chunk_btn.setEnabled(self.current_chunk_index > 0)
        self.next_chunk_btn.setEnabled(self.current_chunk_index < self.total_chunks - 1)
        
        # 更新状态标签
        self.update_chunk_status_label()

    def load_next_chunk(self):
        """加载下一个数据块"""
        if not self.chunk_mode or self.current_chunk_index >= self.total_chunks - 1:
            return
        
        # 更新当前块索引
        self.current_chunk_index += 1
        
        # 计算时间窗口
        chunk_start = self.original_start_time + self.current_chunk_index * self.chunk_size
        chunk_end = min(chunk_start + self.chunk_size, self.original_end_time)
        
        # 加载数据块
        self.load_chunk(chunk_start, chunk_end)
        
        # 更新导航按钮状态
        self.prev_chunk_btn.setEnabled(self.current_chunk_index > 0)
        self.next_chunk_btn.setEnabled(self.current_chunk_index < self.total_chunks - 1)
        
        # 更新状态标签
        self.update_chunk_status_label()

    def load_chunk(self, start_time, end_time):
        """加载指定时间范围的数据块"""
        if not self.current_file:
            return
        
        # 显示进度条
        self.status_label.setText(f"正在加载数据块 {self.current_chunk_index + 1}/{self.total_chunks}...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建并启动加载线程
        self.load_thread = WaveformLoadThread(self.current_file, start_time, end_time)
        self.load_thread.progressChanged.connect(self.update_progress)
        self.load_thread.finished.connect(self.on_chunk_loaded)
        self.load_thread.error.connect(self.on_thread_error)
        self.load_thread.statusUpdate.connect(self.update_status)
        self.load_thread.start()

    def on_chunk_loaded(self, stream):
        """数据块加载完成后的回调"""
        self.stream = stream
        
        # 清除之前的相位检测结果，因为它们可能不适用于当前分块
        self.picks = []
        
        self.update_plot()
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"已加载数据块 {self.current_chunk_index + 1}/{self.total_chunks}，共 {len(self.stream)} 个通道")

    def update_chunk_status_label(self):
        """更新分块状态标签"""
        if not self.chunk_mode:
            self.chunk_status_label.setText("未使用分块模式")
            return
        
        # 计算当前块的时间范围
        chunk_start = self.original_start_time + self.current_chunk_index * self.chunk_size
        chunk_end = min(chunk_start + self.chunk_size, self.original_end_time)
        
        # 格式化时间
        start_str = chunk_start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = chunk_end.strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新标签
        self.chunk_status_label.setText(f"块 {self.current_chunk_index + 1}/{self.total_chunks}: {start_str} - {end_str}")
    
    def load_inventory(self):
        """加载ObsPy台站目录"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "选择台站目录文件", "",
                "台站目录文件 (*.xml *.StationXML);;All Files (*)")
            
            if filename:
                self.inventory = read_inventory(filename)
                
                # 将台站目录转换为数据框
                if self.associator:
                    self.stations_df = self.associator.inventory_to_df(self.inventory)
                    self.status_label.setText(f"台站目录加载成功，共 {len(self.stations_df)} 个台站")
                else:
                    QMessageBox.warning(self, "警告", "关联器未配置成功，无法处理台站数据")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载台站目录失败: {str(e)}")
            self.inventory = None
            self.stations_df = None

    def detect_phases(self):
        """使用神经网络检测 P 和 S 相位，支持分块处理"""
        if not self.stream:
            QMessageBox.warning(self, "警告", "请先加载波形数据")
            return
        if not self.model:
            QMessageBox.warning(self, "警告", "请先加载神经网络模型")
            return

        threshold = float(self.threshold_combo.currentText())
        
        # 创建并配置线程，支持分块处理
        self.phase_thread = PhaseDetectionThread(
            model=self.model, 
            stream=self.stream, 
            threshold=threshold,
            chunk_mode=self.chunk_mode,
            chunk_size=self.chunk_size
        )
        
        # 连接信号
        self.phase_thread.progressChanged.connect(self.update_progress)
        self.phase_thread.finished.connect(self.on_phase_detection_finished)
        self.phase_thread.error.connect(self.on_thread_error)
        self.phase_thread.statusUpdate.connect(self.update_status)
        
        # 启用进度条和状态标签
        self.status_label.setText("正在检测相位...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 启动线程
        self.phase_thread.start()
    
    def on_phase_detection_finished(self, picks):
        """相位检测线程完成时的回调"""
        # 在分块模式下，只保留当前分块内的相位
        if self.chunk_mode:
            current_chunk_start = self.original_start_time + self.current_chunk_index * self.chunk_size
            current_chunk_end = min(current_chunk_start + self.chunk_size, self.original_end_time)
            
            # 过滤相位，只保留当前分块内的
            self.picks = [pick for pick in picks if current_chunk_start <= pick['time'] <= current_chunk_end]
            self.status_label.setText(f"在当前分块中找到 {len(self.picks)} 个相位到达")
        else:
            self.picks = picks
            self.status_label.setText(f"找到 {len(self.picks)} 个相位到达")
        
        self.update_plot()
        self.progress_bar.setVisible(False)
    
    def associate_events(self):
        """使用PyOcto关联器将相位关联为地震事件，现在在后台线程中运行"""
        if not self.model or not self.associator:
            msg = []
            if not self.model:
                msg.append("请先加载神经网络模型")
            if not self.associator:
                msg.append("关联器未配置成功")
            QMessageBox.warning(self, "警告", "\n".join(msg))
            return
        
        if not self.picks:
            QMessageBox.warning(self, "警告", "没有检测到相位，请先进行相位检测")
            return
            
        # 如果没有加载台站信息，提示用户
        if self.stations_df is None:
            QMessageBox.warning(self, "警告", "未加载台站信息，请先加载台站目录")
            return
        
        # 创建并配置线程
        self.association_thread = EventAssociationThread(self.associator, self.picks, self.stations_df)
        
        # 连接信号
        self.association_thread.progressChanged.connect(self.update_progress)
        self.association_thread.finished.connect(self.on_association_finished)
        self.association_thread.error.connect(self.on_thread_error)
        self.association_thread.statusUpdate.connect(self.update_status)
        
        # 启用进度条和状态标签
        self.status_label.setText("正在关联事件...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 启动线程
        self.association_thread.start()

    def on_association_finished(self, events_df, assignments_df):
        """事件关联线程完成时的回调"""
        self.events_df = events_df
        self.assignments_df = assignments_df
        
        # 更新图表显示关联结果
        if not events_df.empty:
            self.update_plot_with_events()
            self.status_label.setText(f"成功关联 {len(events_df)} 个地震事件")
        else:
            self.status_label.setText("未找到关联事件")
            
        self.progress_bar.setVisible(False)
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)
    
    def on_thread_error(self, error_message):
        """线程错误处理"""
        QMessageBox.critical(self, "错误", f"操作失败: {error_message}")
        self.status_label.setText("操作失败")
        self.progress_bar.setVisible(False)
        
    def clear_picks(self):
        """清除所有检测结果"""
        self.picks = []
        self.update_plot()
        self.status_label.setText("已清除所有相位检测结果")

    def update_plot(self):
        """使用当前波形和检测结果更新图形"""
        self.figure.clear()
        
        if not self.stream:
            # 显示空图和提示信息
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Load waveform data to begin',
                    ha='center', va='center', fontsize=18)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            # 绘制每个波形
            num_traces = len(self.stream)
            
            # 调整高度计算，添加额外的底部空间保证最后一个波形可以完全显示
            fixed_height = max(12, num_traces * 3 + 2)  # 增加总高度并添加额外空间
            self.figure.set_figheight(fixed_height)
            
            # 增加画布高度，确保有足够空间显示所有内容
            self.canvas.setMinimumHeight(fixed_height * 100)  # 增加系数从80到100
            
            # 确保plot_widget有更多的高度
            self.plot_widget.setMinimumHeight(fixed_height * 100 + 100)  # 添加额外100像素
            
            # 为每个子图保留足够的垂直空间，减小比例以留出更多空间
            subplot_height = 0.85 / num_traces if num_traces > 1 else 0.85
            
            # 计算时间偏移量，用于分块模式下的连续时间轴显示
            time_offset = 0
            if self.chunk_mode and self.current_chunk_index > 0:
                time_offset = self.current_chunk_index * self.chunk_size
            
            for i, trace in enumerate(self.stream):
                ax = self.figure.add_subplot(num_traces, 1, i+1)
                
                # 绘制波形
                times = trace.times()
                
                # 在分块模式下调整时间轴，使其显示连续的时间
                if self.chunk_mode:
                    times = times + time_offset
                
                ax.plot(times, trace.data, 'k', linewidth=1.0)
                
                # 对每个通道的检测结果显示
                channel_picks = [p for p in self.picks if p['channel'] == '.'.join(trace.id.split('.', 2)[:2])]
                for pick in channel_picks:
                    # 计算相对于当前分块的时间
                    if self.chunk_mode:
                        # 只显示当前分块内的相位
                        pick_time_relative = pick['time'] - trace.stats.starttime
                        pick_time = pick_time_relative + time_offset
                    else:
                        pick_time = pick['time'] - trace.stats.starttime
                    
                    color = 'red' if pick['phase'] == 'P' else 'blue'
                    ax.axvline(pick_time, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
                    y_position = ax.get_ylim()[1] * 0.8
                    ax.text(pick_time + 0.5, y_position+3,
                            f"{pick['phase']}\n{pick['probability']:.2f}",
                            color=color, va='top', fontsize=12, 
                            bbox=dict(facecolor='white', alpha=0.7, pad=2))
                
                # 设置标签和坐标轴文字大小
                ax.set_ylabel(trace.id, fontsize=12)
                if i == num_traces-1:
                    if self.chunk_mode:
                        ax.set_xlabel('Time (s) - Continuous', fontsize=12)
                    else:
                        ax.set_xlabel('Time (s)', fontsize=12)
                    # 为最后一个子图增加底部边距
                    plt_pos = ax.get_position()
                    ax.set_position([plt_pos.x0, plt_pos.y0, plt_pos.width, plt_pos.height - 0.02])
                
                # 设置刻度标签字体
                for label in ax.get_xticklabels():
                    label.set_fontsize(10)
                for label in ax.get_yticklabels():
                    label.set_fontsize(10)
                
                ax.grid(True, alpha=0.3)
        
            # 调整布局，增加底部空间
            self.figure.tight_layout(pad=3.0, h_pad=2.0, rect=[0, 0.02, 1, 0.98])
    
        self.canvas.draw()
        
        # 确保滚动区域更新
        self.plot_widget.updateGeometry()
        self.plot_widget.setMinimumSize(self.plot_widget.sizeHint())

    def export_image(self):
        """导出当前图像"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", "", 
                                                   "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)", 
                                                   options=options)
        if file_name:
            self.figure.savefig(file_name)
            self.status_label.setText(f"图像已保存为 {file_name}")

    def export_report(self):
        """导出检测报告"""
        if not self.picks:
            QMessageBox.warning(self, "警告", "没有检测结果可导出")
            return
            
        report_content = "Seismic Phase Detection Report\n\n"
        report_content += f"Number of Picks: {len(self.picks)}\n"
        report_content += "Picks Details:\n"
        for pick in self.picks:
            report_content += f"Time: {pick['time']}, Phase: {pick['phase']}, Channel: {pick['channel']}, Probability: {pick['probability']:.2f}\n"
        
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Report", "", 
                                                   "Text Files (*.txt);;All Files (*)", 
                                                   options=options)
        if file_name:
            with open(file_name, 'w') as report_file:
                report_file.write(report_content)
            self.status_label.setText(f"报告已保存为 {file_name}")

    def show_help(self):
        """显示帮助信息"""
        # 创建一个自定义的 QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Help")
        msg_box.setText("This application allows you to load seismic waveforms, "
                        "detect phases using a neural network, and export the results. "
                        "Use the toolbar buttons to interact with the application.")
        msg_box.exec_()

    def update_plot_with_events(self):
        """更新图表，显示关联的事件"""
        # 现有的绘图代码基础上添加关联事件的标记
        self.update_plot()
        
        if self.events_df is None or self.events_df.empty:
            print("没有关联事件可显示")
            return
        
        # 在每个波形上标记事件
        for i, trace in enumerate(self.stream):
            ax = self.figure.axes[i]
            
            # 为每个事件添加垂直线和标签
            for j, (idx, event) in enumerate(self.events_df.iterrows()):
                # 获取事件时间
                event_time = datetime.fromtimestamp(event['time'])
                event_time_rel = (event_time - trace.stats.starttime.datetime).total_seconds()
                
                # 确保事件时间在波形范围内
                if 0 <= event_time_rel <= trace.stats.endtime - trace.stats.starttime:
                    # 绘制事件线
                    ax.axvline(event_time_rel, color='green', linestyle='-', alpha=0.5, linewidth=2.0)
                    
                    # 添加事件标签
                    y_pos = ax.get_ylim()[1] * 0.9
                    ax.text(event_time_rel + 0.2, y_pos, 
                            f"Event {j+1}\nLat: {event['latitude']:.2f}\nLon: {event['longitude']:.2f}\nDepth: {event['depth']:.2f}km",
                            color='green', fontsize=10, 
                            bbox=dict(facecolor='white', alpha=0.7, pad=2))
                    
                    # 为该事件相关的相位添加标记
                    if self.assignments_df is not None:
                        event_picks = self.assignments_df[self.assignments_df['event_idx'] == idx]
                        for _, pick in event_picks.iterrows():
                            if pick['station'] == '.'.join(trace.id.split('.', 2)[:2]):
                                pick_time = datetime.fromtimestamp(pick['time'])
                                pick_time_rel = (pick_time - trace.stats.starttime.datetime).total_seconds()
                                if 0 <= pick_time_rel <= trace.stats.endtime - trace.stats.starttime:
                                    color = 'blue' if pick['phase'] == 'S' else 'red'
                                    ax.axvline(pick_time_rel, color=color, linestyle=':', linewidth=1.5)
                                    y_pos_pick = ax.get_ylim()[1] * 0.7
                                    ax.text(pick_time_rel + 0.2, y_pos_pick, 
                                            f"{pick['phase']} ({pick['residual']:.2f}s)",
                                            color=color, fontsize=8, 
                                            bbox=dict(facecolor='white', alpha=0.5, pad=1))
        
        self.canvas.draw()

    def visualize_catalog(self):
        """可视化关联的地震目录 - 调用外部模块"""
        CatalogVisualizer.show_catalog_visualization(
            parent=self,
            events_df=self.events_df,
            stations_df=self.stations_df,
            associator=self.associator
        )

    def export_catalog(self):
        """导出关联事件目录"""
        if self.events_df is None or self.events_df.empty:
            QMessageBox.warning(self, "警告", "没有关联事件可导出")
            return
        
        try:
            # 选择保存文件
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "导出事件目录", "", 
                                                        "CSV Files (*.csv);;All Files (*)", 
                                                        options=options)
            if not file_name:
                return
                
            # 导出事件目录为CSV
            self.events_df.to_csv(file_name, index=False)
            
            # 同时导出相位关联结果
            if self.assignments_df is not None and not self.assignments_df.empty:
                # 提取文件名部分
                base_name = file_name.rsplit('.', 1)[0]
                assignments_file = f"{base_name}_phases.csv"
                
                # 导出相位关联结果
                self.assignments_df.to_csv(assignments_file, index=False)
                
            QMessageBox.information(self, "成功", f"事件目录已成功导出到 {file_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出事件目录时出错: {str(e)}")

    def toggle_streaming_mode(self):
        """切换到实时模拟模式 - 在已加载波形上显示滑动窗口"""
        # 检查是否已加载波形数据
        if self.stream is None:
            QMessageBox.warning(self, "警告", "请先加载波形数据")
            return
            
        # 如果通道超过3个，弹出通道选择对话框
        if len(self.stream) > 3:
            selected_indices = self.show_channel_selection_dialog()
            if not selected_indices:  # 用户取消了选择
                return
            
            # 创建包含所选通道的子流
            selected_stream = self.stream.copy()
            selected_stream.clear()
            for idx in selected_indices:
                if 0 <= idx < len(self.stream):
                    selected_stream += self.stream[idx]
        else:
            # 通道少于等于3个，直接全部显示
            selected_stream = self.stream.copy()
            
        # 数据预处理，确保波形数据质量
        for tr in selected_stream:
            # 移除均值和线性趋势（改善显示效果）
            tr.detrend('demean')
            tr.detrend('linear')
            
            # 如果波形振幅异常（太小或太大），则进行归一化
            max_amp = np.max(np.abs(tr.data))
            if max_amp < 0.001 or max_amp > 1000:
                tr.data = tr.data / max_amp  # 归一化
        
        # 切换到实时监测标签页
        self.tab_widget.setCurrentIndex(1)  # 实时监测是第二个标签页
        
        # 重置滚动波形显示并设置波形数据
        self.scrolling_display.set_stream(selected_stream)
        
        # 如果有相位检测结果，传递给滚动波形显示组件
        if self.picks:
            self.scrolling_display.set_picks(self.picks)
            self.status_label.setText(f"实时监测模式已激活 (显示{len(selected_stream)}个通道，包含{len(self.picks)}个相位标记)")
        else:
            self.status_label.setText(f"实时监测模式已激活 (显示{len(selected_stream)}个通道)")
        
        # 自动启动滚动播放
        self.scrolling_display.start_streaming()
        
        # 更新状态
        self.status_label.setText(f"实时监测模式已激活 (显示{len(selected_stream)}个通道)")
        
        # 强制窗口重绘
        self.repaint()

    def show_channel_selection_dialog(self):
        """显示通道选择对话框，允许用户选择要显示的通道"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择要显示的通道")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(500)  # 设置最小高度
        
        layout = QVBoxLayout(dialog)
        
        info_label = QLabel("请选择要在实时监测中显示的通道（建议选择1-3个）：")
        layout.addWidget(info_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # 创建容器放置复选框
        checkbox_container = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_container)
        
        # 创建通道选择复选框
        checkboxes = []
        for i, trace in enumerate(self.stream):
            checkbox = QCheckBox(trace.id)
            # 默认选中前3个
            checkbox.setChecked(i < 3)
            checkbox_layout.addWidget(checkbox)
            checkboxes.append(checkbox)
        
        # 添加全选/取消全选的按钮
        select_buttons_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self.toggle_all_checkboxes(checkboxes, True))
        select_buttons_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self.toggle_all_checkboxes(checkboxes, False))
        select_buttons_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(select_buttons_layout)
        
        # 设置滚动区域的内容
        scroll_area.setWidget(checkbox_container)
        layout.addWidget(scroll_area)
        
        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # 执行对话框
        if dialog.exec_() == QDialog.Accepted:
            # 返回所选通道的索引
            return [i for i, checkbox in enumerate(checkboxes) if checkbox.isChecked()]
        else:
            return []
            
    def toggle_all_checkboxes(self, checkboxes, checked):
        """切换所有复选框状态"""
        for checkbox in checkboxes:
            checkbox.setChecked(checked)

# 主程序入口
def main():
    app = QApplication(sys.argv)
    window = SeismicPhasePicker()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()