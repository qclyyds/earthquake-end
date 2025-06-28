import numpy as np
from obspy import read, Stream, UTCDateTime
import seisbench.models as sbm
import pyocto
import pandas as pd
from datetime import datetime
from obspy.core.event import Catalog, Event, Origin, Magnitude, Pick
from PyQt5.QtCore import QThread, pyqtSignal
import traceback

# 波形加载线程类
class WaveformLoadThread(QThread):
    progressChanged = pyqtSignal(int)
    finished = pyqtSignal(Stream)
    error = pyqtSignal(str)
    statusUpdate = pyqtSignal(str)
    
    def __init__(self, filename, start_time=None, end_time=None):
        super().__init__()
        self.filename = filename
        self.start_time = start_time
        self.end_time = end_time
    
    def run(self):
        try:
            self.statusUpdate.emit("正在加载波形数据...")
            self.progressChanged.emit(10)
            
            # 根据是否提供了时间窗口来决定加载方式
            if self.start_time and self.end_time:
                self.statusUpdate.emit(f"加载从 {self.start_time} 到 {self.end_time} 的数据...")
                stream = read(self.filename, starttime=self.start_time, endtime=self.end_time)
            else:
                self.statusUpdate.emit("加载整个波形文件...")
                stream = read(self.filename)
            
            self.progressChanged.emit(50)
            
            # 数据预处理
            self.statusUpdate.emit("正在预处理波形数据...")
            stream.detrend('linear')
            
            # 获取采样率
            sampling_rate = stream[0].stats.sampling_rate
            nyquist = sampling_rate / 2.0
            
            # 确保高截止频率低于奈奎斯特频率
            freqmax = min(20.0, nyquist - 0.1)
            
            stream.filter('bandpass', freqmin=1.0, freqmax=freqmax)
            
            self.progressChanged.emit(100)
            self.statusUpdate.emit("波形数据加载和预处理完成")
            self.finished.emit(stream)
            
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))

# 相位检测线程类
class PhaseDetectionThread(QThread):
    # 定义信号
    progressChanged = pyqtSignal(int)  # 进度更新信号
    finished = pyqtSignal(list)  # 完成信号，返回检测到的相位
    error = pyqtSignal(str)  # 错误信号
    statusUpdate = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, model, stream, threshold, chunk_mode=False, chunk_size=None):
        super().__init__()
        self.model = model
        self.stream = stream
        self.threshold = threshold
        self.chunk_mode = chunk_mode
        self.chunk_size = chunk_size  # 单位:秒
        
    def run(self):
        try:
            picks = []
            
            if not self.chunk_mode or not self.chunk_size:
                # 常规处理 - 一次性处理整个流
                self.statusUpdate.emit("正在检测相位...")
                pred = self.model.classify(self.stream, P_threshold=self.threshold, S_threshold=self.threshold)
                
                # 处理预测结果
                total_picks = len(pred.picks)
                for i, pick in enumerate(pred.picks):
                    prob = pick.peak_value
                    phase_name = pick.phase
                    start_time = pick.start_time
                    trace_id = '.'.join(pick.trace_id.split('.', 2)[:2])
                    picks.append({
                        'time': start_time,
                        'phase': phase_name,
                        'channel': trace_id,
                        'probability': pick.peak_value
                    })
                    
                    # 更新进度
                    progress = int((i + 1) / total_picks * 100) if total_picks > 0 else 100
                    self.progressChanged.emit(progress)
                
            else:
                # 分块处理
                if len(self.stream) == 0:
                    self.error.emit("波形数据为空，无法进行分块处理")
                    return
                
                # 获取流的时间范围
                self.statusUpdate.emit("准备分块处理...")
                start_time = min([tr.stats.starttime for tr in self.stream])
                end_time = max([tr.stats.endtime for tr in self.stream])
                total_duration = end_time - start_time
                
                # 计算块数
                num_chunks = int(np.ceil(total_duration / self.chunk_size))
                chunk_minutes = self.chunk_size / 60
                self.statusUpdate.emit(f"将以 {chunk_minutes:.1f} 分钟为块大小，分成 {num_chunks} 个块进行处理...")
                
                # 逐块处理
                for chunk_idx in range(num_chunks):
                    try:
                        chunk_start = start_time + chunk_idx * self.chunk_size
                        chunk_end = min(chunk_start + self.chunk_size, end_time)
                        
                        # 确保开始时间小于结束时间
                        if chunk_end <= chunk_start:
                            self.statusUpdate.emit(f"跳过无效时间块 {chunk_idx+1}/{num_chunks}: {chunk_start} - {chunk_end}")
                            continue
                        
                        # 提取当前时间块
                        self.statusUpdate.emit(f"处理时间块 {chunk_idx+1}/{num_chunks}: {chunk_start} - {chunk_end}")
                        
                        # 从原始流切片出当前时间块
                        chunk_stream = self.stream.slice(chunk_start, chunk_end)
                        
                        # 处理当前块
                        if len(chunk_stream) > 0:
                            self.statusUpdate.emit(f"检测块 {chunk_idx+1} 中的相位...")
                            pred = self.model.classify(chunk_stream, P_threshold=self.threshold, S_threshold=self.threshold)
                            
                            # 添加当前块中的相位
                            for pick in pred.picks:
                                prob = pick.peak_value
                                phase_name = pick.phase
                                pick_time = pick.start_time
                                trace_id = '.'.join(pick.trace_id.split('.', 2)[:2])
                                picks.append({
                                    'time': pick_time,
                                    'phase': phase_name,
                                    'channel': trace_id,
                                    'probability': pick.peak_value
                                })
                        else:
                            self.statusUpdate.emit(f"块 {chunk_idx+1} 没有可用数据，跳过")
                            
                    except ValueError as e:
                        self.statusUpdate.emit(f"处理块 {chunk_idx+1} 时出错: {str(e)}，跳过此块")
                    except Exception as e:
                        self.statusUpdate.emit(f"处理块 {chunk_idx+1} 时出现未知错误: {str(e)}，跳过此块")
                    
                    # 更新总体进度
                    progress = int((chunk_idx + 1) / num_chunks * 100)
                    self.progressChanged.emit(progress)
            
            # 结果排序
            picks.sort(key=lambda x: x['time'])
            self.statusUpdate.emit(f"检测完成，共找到 {len(picks)} 个相位")
            
            # 发送完成信号
            self.finished.emit(picks)
            
        except Exception as e:
            traceback.print_exc()
            # 发送错误信号
            self.error.emit(str(e))

# 事件关联线程类
class EventAssociationThread(QThread):
    # 定义信号
    progressChanged = pyqtSignal(int)  # 进度更新信号
    finished = pyqtSignal(pd.DataFrame, pd.DataFrame)  # 完成信号，返回事件和关联结果
    error = pyqtSignal(str)  # 错误信号
    statusUpdate = pyqtSignal(str)  # 状态更新信号
    
    def __init__(self, associator, picks, stations_df):
        super().__init__()
        self.associator = associator
        self.picks = picks
        self.stations_df = stations_df
        
    def run(self):
        try:
            # 发送状态更新
            self.statusUpdate.emit("准备关联数据...")
            self.progressChanged.emit(10)
            
            # 获取所有有效台站的ID列表
            valid_stations = set(self.stations_df['id'].values)
            
            # 转换picks格式为PyOcto格式
            pyocto_picks_data = {
                'station': [],
                'phase': [],
                'time': [],
                'probability': []
            }
            
            filtered_picks = []
            missing_stations = set()
            
            # 发送状态更新
            self.statusUpdate.emit("处理拾取数据...")
            self.progressChanged.emit(20)
            
            for pick in self.picks:
                # 从通道中提取台站ID
                station_parts = pick['channel'].split('.')
                station_id = f"{station_parts[0]}.{station_parts[1]}."
                
                if station_id in valid_stations:
                    pyocto_picks_data['station'].append(station_id)
                    pyocto_picks_data['phase'].append(pick['phase'])
                    pyocto_picks_data['time'].append(pick['time'].timestamp)
                    pyocto_picks_data['probability'].append(pick['probability'])
                    filtered_picks.append(pick)
                else:
                    missing_stations.add(station_id)
            
            # 检查是否还有足够的拾取
            if len(filtered_picks) == 0:
                self.error.emit("所有拾取都被过滤掉了，没有拾取与台站信息匹配")
                return
            
            # 创建过滤后的pandas数据框
            picks_df = pd.DataFrame(pyocto_picks_data)
            
            # 发送状态更新
            self.statusUpdate.emit(f"开始关联 {len(filtered_picks)} 个拾取点...")
            self.progressChanged.emit(30)
            
            # 使用associate方法
            events_df, assignments_df = self.associator.associate(picks_df, self.stations_df)
            
            # 发送状态更新
            self.statusUpdate.emit("转换事件坐标...")
            self.progressChanged.emit(80)
            
            # 转换事件坐标从局部坐标系统到经纬度
            if not events_df.empty:
                events_df = self.associator.transform_events(events_df)
                self.statusUpdate.emit(f"成功关联 {len(events_df)} 个地震事件")
            else:
                self.statusUpdate.emit("未找到关联事件")
            
            # 发送完成信号
            self.progressChanged.emit(100)
            self.finished.emit(events_df, assignments_df)
            
        except Exception as e:
            # 发送错误信号
            traceback.print_exc()
            self.error.emit(str(e))

# 模型加载函数
def load_neural_model(model_name):
    """加载指定的 SeisBench 神经网络模型"""
    try:
        import seisbench
        seisbench.use_backup_repository()  # 使用备用下载库
        
        if model_name == "EQTransformer":
            model = sbm.EQTransformer.from_pretrained("original")
        elif model_name == "PhaseNet":
            model = sbm.PhaseNet.from_pretrained("geofon")
        elif model_name == "PickBlue":
            model = sbm.PickBlue()  # 直接实例化
        elif model_name == "OBSTransformer":
            model = sbm.OBSTransformer.from_pretrained("obst2024")
        else:
            return None, f"不支持的模型: {model_name}"
            
        return model, None
        
    except Exception as e:
        traceback.print_exc()
        return None, str(e)

# 创建关联器函数
def setup_associator():
    """配置PyOcto关联器"""
    try:
        # 根据官方文档配置均匀速度模型
        velocity_model = pyocto.VelocityModel0D(
            p_velocity=7.0,      # P波速度 (km/s)
            s_velocity=4.0,      # S波速度 (km/s)
            tolerance=2.0,       # 速度模型容差 (s)
            association_cutoff_distance=250,  # 用于空间分区关联的最大台站距离 (km)
        )
        
        # 创建关联器，使用from_area方法自动选择局部坐标投影
        associator = pyocto.OctoAssociator.from_area(
            lat=(-25, -18),      # 纬度范围
            lon=(-71.5, -68),    # 经度范围
            zlim=(0, 200),       # 深度范围 (km)
            time_before=300,     # 重叠时间 (s)
            velocity_model=velocity_model,  # 速度模型
            n_picks=10,          # 最小拾取数
            n_p_and_s_picks=4,   # 最小P和S波拾取数
        )
        
        return associator, None
        
    except Exception as e:
        # 尝试不使用速度模型直接创建关联器
        try:
            associator = pyocto.OctoAssociator.from_area(
                lat=(-25, -18),      # 纬度范围
                lon=(-71.5, -68),    # 经度范围
                zlim=(0, 200),       # 深度范围 (km)
                time_before=300,     # 重叠时间 (s)
                n_picks=10,          # 最小拾取数
                n_p_and_s_picks=4,   # 最小P和S波拾取数
            )
            return associator, None
        except Exception as e2:
            traceback.print_exc()
            return None, str(e2)

# 其他实用函数可以根据需要添加到这里 