"""
星地量子密钥分发链路仿真系统
主应用 - Gradio界面
"""

import gradio as gr
import numpy as np
import pandas as pd
import math
from datetime import datetime, timedelta, timezone
import sys
import os

# 导入自定义模块
from config import (
    GROUND_STATIONS, 
    SAMPLE_TLE, 
    ATTACK_TYPES, 
    QKD_PARAMETERS,
    SIMULATION_CONFIG
)
from modules.orbit_adapter import OrbitAdapter
from modules.weather_adapter import WeatherAdapter
from modules.channel_model import ChannelModel, ChannelParameters
from modules.qkd_core import BB84SatelliteQKD
from modules.eve_attacks import get_attack
from modules.security_defense import SecurityAnalyzer
from modules.visualization import QKDVisualizer
from modules.world_map import WorldMapVisualizer


class QKDSimulationApp:
    """
    QKD仿真应用主类
    """
    
    def __init__(self):
        self.orbit_adapter = None
        self.weather_adapter = WeatherAdapter()
        self.channel_model = ChannelModel()
        self.security_analyzer = SecurityAnalyzer()
        self.visualizer = QKDVisualizer()
        self.world_map = WorldMapVisualizer()
        
        # 当前仿真结果缓存
        self.current_results = None
        self.current_ground_track = None  # 星下点轨迹缓存
        
    def initialize_satellite(self, satellite_name: str):
        """初始化卫星"""
        tle_data = SAMPLE_TLE.get(satellite_name, SAMPLE_TLE.get("国际空间站(ISS)"))
        if tle_data is None:
            raise ValueError(f"卫星 {satellite_name} 未找到")
        self.orbit_adapter = OrbitAdapter(tle_data["line1"], tle_data["line2"])
        return f"已加载卫星: {satellite_name}"
    
    def _check_tle_age(self, line1: str, satellite_name: str):
        """
        检查TLE数据是否过期
        
        TLE格式：第1行第19-32位是历元（YYDDD.DDDDDDDD）
        - YY: 年份后两位
        - DDD.DDDDDDDD: 一年中的第几天（含小数）
        """
        try:
            from datetime import datetime, timezone
            
            # 提取历元
            epoch_str = line1[18:32].strip()
            year_short = int(epoch_str[0:2])
            day_of_year = float(epoch_str[2:])
            
            # 转换完整年份
            if year_short < 57:  # 假设1957年是太空时代开始
                year = 2000 + year_short
            else:
                year = 1900 + year_short
            
            # 计算TLE日期
            from datetime import timedelta
            tle_date = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
            
            # 当前日期
            now = datetime.now(timezone.utc)
            
            # 计算年龄（天）
            age_days = (now - tle_date).days
            
            # 警告阈值
            if age_days > 30:
                print(f"[警告] {satellite_name} 的TLE数据已过期 {age_days} 天")
                print(f"[提示] TLE历元: {tle_date.strftime('%Y-%m-%d')}")
                print(f"[提示] 建议从 https://celestrak.org/ 获取最新TLE数据")
            elif age_days > 7:
                print(f"[提示] {satellite_name} 的TLE数据已使用 {age_days} 天，可能影响精度")
                
        except Exception as e:
            # 检查失败不阻止程序运行
            pass
    
    def run_simulation(self,
                      satellite: str,
                      ground_station: str,
                      duration_minutes: int,
                      time_step: int,
                      attack_type: str,
                      demo_weather_mode: str,
                      weather_select: str,
                      enable_decoy: bool,
                      enable_privacy_amp: bool) -> tuple:
        """
        运行完整仿真
        
        Returns:
            tuple: (结果摘要, 结果表格, 密钥率图, QBER图, 安全分析图)
        """
        # 获取地面站
        gs = GROUND_STATIONS[ground_station]
        gs['name'] = ground_station  # 添加名称字段
        
        # 生成时间线
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # 检测是否为演示卫星
        is_demo = "演示" in satellite
        
        # 获取卫星倾角（用于显示）
        if is_demo:
            # 演示模式使用固定倾角（ISS类型约51.6°）
            orbit_inclination = 51.6
        else:
            # 从TLE数据提取倾角和检查过期
            tle_data = SAMPLE_TLE.get(satellite, {})
            line1 = tle_data.get('line1', '')
            line2 = tle_data.get('line2', '')
            
            # 检查TLE是否过期
            self._check_tle_age(line1, satellite)
            
            try:
                # TLE第二行第3个字段是倾角（单位：度）
                parts = line2.split()
                if len(parts) >= 3:
                    orbit_inclination = float(parts[2])
                else:
                    orbit_inclination = 0.0
            except:
                orbit_inclination = 0.0
        
        if is_demo:
            # 演示模式：生成模拟的过境轨迹（正弦波形状）
            timeline = self._generate_demo_timeline(
                start_time, end_time, gs, step_seconds=time_step
            )
        else:
            # 真实卫星：使用轨道计算
            self.initialize_satellite(satellite)
            timeline = self.orbit_adapter.generate_pass_timeline(
                start_time, end_time, gs, step_seconds=time_step
            )
            
            # 检查是否有可见过境
            visible_count = sum(1 for p in timeline if p['visible'])
            if visible_count == 0:
                print(f"[警告] 所选卫星在当前时间段内不可见")
                print(f"[提示] 建议：1) 延长仿真时间至24小时 2) 更换地面站位置 3) 更新TLE数据")
                print(f"[提示] 可从 https://celestrak.org/ 获取最新TLE数据")
        
        # 获取攻击对象
        attack = get_attack(attack_type)
        
        # 运行每个时间点的仿真
        results = []
        
        # 预先获取天气缓存（当需要API天气时使用）
        weather_cache = None
        weather_source = "默认"
        weather_df = None  # 存储完整天气数据框用于时间插值
        
        # 真实卫星模式 或 演示模式选择实时API时，获取天气
        if not is_demo or (is_demo and demo_weather_mode == "使用实时API天气"):
            print(f"[系统] 正在获取地面站实时天气数据，请稍候...")
            try:
                # 无论是演示模式还是真实卫星，都获取完整24小时数据用于插值
                weather_df = self.weather_adapter.get_weather_data(
                    gs['lat'], gs['lon'], forecast_days=1
                )
                
                # 同时获取起始时间点的天气用于显示
                weather_cache = self.weather_adapter.get_weather_at_time(
                    gs['lat'], gs['lon'], start_time
                )
                
                is_api = weather_df is not None and not weather_df.get('is_default', pd.Series([True])).iloc[0]
                weather_source = "API" if is_api else "默认"
                print(f"[系统] 天气数据获取完成 ({'实时API' if is_api else '默认数据'})")
            except Exception as e:
                print(f"[系统] 天气API调用失败: {str(e)[:50]}，使用默认数据")
                weather_cache = None
                weather_df = None
                weather_source = "默认"
        
        for point in timeline:
            if not point['visible']:
                # 即使不可见也记录天气状态
                weather_info = '未知'
                is_default = True
                if is_demo and demo_weather_mode == "使用自选模拟天气":
                    weather_info = weather_select + '（演示自选）'
                    is_default = True  # 自选天气也是模拟数据
                elif is_demo and demo_weather_mode == "使用实时API天气" and weather_cache:
                    weather_info = weather_cache.get('weather_type', '未知')
                    is_default = weather_cache.get('is_default', True)
                elif weather_cache:
                    weather_info = weather_cache.get('weather_type', '未知')
                    is_default = weather_cache.get('is_default', True)
                
                results.append({
                    'timestamp': point['timestamp'],
                    'visible': False,
                    'qber': 0,
                    'secret_key_rate': 0,
                    'sifted_rate': 0,
                    'weather_type': weather_info,
                    'is_default_weather': is_default,
                    'satellite_inclination': orbit_inclination,
                    'distance_km': point.get('distance_km', np.nan),
                    'elevation_deg': point.get('elevation_deg', np.nan),
                    'azimuth_deg': point.get('azimuth_deg', np.nan)
                })
                continue
            
            # 获取天气数据
            if is_demo and demo_weather_mode == "使用自选模拟天气":
                # 演示模式自选天气
                weather_map = {
                    '晴天': {'attenuation': 0.2, 'code': 0, 'type': '晴'},
                    '多云': {'attenuation': 0.5, 'code': 2, 'type': '多云'},
                    '小雨': {'attenuation': 3.0, 'code': 53, 'type': '小雨'},
                    '大雨': {'attenuation': 8.0, 'code': 65, 'type': '大雨'},
                    '雾天': {'attenuation': 10.0, 'code': 45, 'type': '雾'}
                }
                w = weather_map.get(weather_select, weather_map['晴天'])
                weather = {
                    'temperature': 20.0,
                    'humidity': 50.0,
                    'wind_speed': 5.0,
                    'precipitation': 0.0 if '雨' not in weather_select else 5.0,
                    'pressure': 1013.0,
                    'cloud_cover': 0.0 if weather_select == '晴天' else 50.0,
                    'weather_code': w['code'],
                    'weather_type': w['type'] + '（演示自选）',
                    'attenuation_db_per_km': w['attenuation'],
                    'is_default': True  # 标记为模拟数据
                }
            else:
                # 真实模式 或 演示模式选择实时API：使用预获取的天气数据
                if weather_df is not None:
                    # 从预获取的DataFrame中插值获取该时间点的天气
                    weather = self._get_weather_from_df(weather_df, point['timestamp'])
                elif weather_cache is not None:
                    # 演示模式使用缓存
                    weather = weather_cache
                else:
                    # 使用默认天气
                    weather = {
                        'temperature': 20.0, 'humidity': 50.0, 'wind_speed': 5.0,
                        'precipitation': 0.0, 'pressure': 1013.0, 'cloud_cover': 10.0,
                        'weather_code': 0, 'weather_type': '晴(默认)',
                        'attenuation_db_per_km': 0.2, 'is_default': True
                    }
            
            # 计算信道参数
            atten_db_per_km = weather['attenuation_db_per_km']
            
            # 调试输出（每10个点输出一次）
            if len(results) % 10 == 0:
                print(f"[调试] 时间={point['timestamp'].strftime('%H:%M')}, "
                      f"距离={point['distance_km']:.0f}km, 仰角={point['elevation_deg']:.1f}°, "
                      f"天气={weather.get('weather_type', '未知')}, 衰减={atten_db_per_km:.2f}dB/km")
            
            channel_params = ChannelParameters(
                distance_km=point['distance_km'],
                elevation_deg=point['elevation_deg'],
                attenuation_db_per_km=atten_db_per_km,
                wavelength_nm=QKD_PARAMETERS['wavelength_nm']
            )
            
            # 信道分析
            channel_result = self.channel_model.full_channel_analysis(channel_params)
            
            # 使用信道模型估算值（平滑连续）
            # 不再使用蒙特卡洛仿真（会导致离散跳跃）
            transmission = channel_result['transmission']['total']
            base_qber = channel_result['qber']  # 物理信道QBER
            sifted_rate = channel_result['key_rates']['sifted_rate_bps']
            
            # Eve信息和攻击引入的QBER根据攻击类型设定
            if attack_type == 'none' or attack is None:
                eve_info = 0.0
                attack_qber = 0.0
            elif attack_type == 'intercept_resend':
                eve_info = 0.5  # 截获重发，Eve知道50%信息
                attack_qber = 0.25  # 截获重发引入25%误码
            elif attack_type == 'beam_splitting':
                eve_info = 0.2  # 光束分离
                attack_qber = 0.0  # 不引入误码
            elif attack_type == 'pns':
                eve_info = 0.3  # PNS攻击
                attack_qber = 0.0  # 不引入误码
            else:
                eve_info = 0.0
                attack_qber = 0.0
            
            # 总QBER = 物理QBER + 攻击引入QBER
            # 注意：QBER是误码率，简单相加可能超过1，需要限制
            qber = min(base_qber + attack_qber, 0.5)  # 最大50%
            
            # 安全分析 - 计算安全密钥率
            # 使用GLLP公式：r = 1 - 2*H2(QBER) - 2*τ
            def binary_entropy(x):
                if x <= 0 or x >= 1:
                    return 0
                return -x * np.log2(x) - (1 - x) * np.log2(1 - x)
            
            # 基础损失：2倍QBER熵（纠错+隐私放大）
            base_loss = 2 * binary_entropy(qber)
            
            # Eve信息损失（根据防御策略计算）
            # 注意：防御越完善，eve_loss越大（主动牺牲密钥换安全）
            if enable_privacy_amp and enable_decoy:
                # 同时启用：最高级别防御
                # 诱骗态检测PNS + 隐私放大消除信息
                eve_loss = 2.2 * eve_info  # 最强防御，损失最大
            elif enable_privacy_amp:
                # 仅隐私放大：通用防御
                eve_loss = 2.0 * eve_info
            elif enable_decoy:
                # 仅诱骗态：对PNS攻击有效，但不如隐私放大彻底
                if attack_type == 'pns':
                    eve_loss = 1.8 * eve_info  # 诱骗态对PNS有效
                else:
                    eve_loss = 0.5 * eve_info  # 对其他攻击效果较弱
            else:
                # 无防御：不损失密钥，但不安全！
                eve_loss = 0
            
            # 总安全密钥比例
            secret_key_factor = max(0, 1 - base_loss - eve_loss)
            
            # 如果QBER超过阈值，无法生成安全密钥
            if qber >= 0.11:
                secret_key_factor = 0
            
            secret_rate = sifted_rate * secret_key_factor
            
            results.append({
                'timestamp': point['timestamp'],
                'visible': True,
                'distance_km': point['distance_km'],
                'elevation_deg': point['elevation_deg'],
                'azimuth_deg': point.get('azimuth_deg', np.nan),
                'qber': qber,
                'sifted_rate': sifted_rate,
                'secret_key_rate': secret_rate,
                'eve_info': eve_info,
                'weather_type': weather['weather_type'],
                'is_default_weather': weather.get('is_default', True),
                'satellite_inclination': orbit_inclination
            })
        
        self.current_results = results
        
        # 生成结果摘要
        summary = self._generate_summary(results, attack_type, enable_privacy_amp)
        
        # 生成结果表格
        df = pd.DataFrame(results)
        # 先统一转换为字符串格式，避免时区问题
        df['timestamp'] = df['timestamp'].apply(lambda x: x.strftime('%H:%M:%S') if hasattr(x, 'strftime') else str(x))
        df = df.round(3)
        
        # 重命名列以更好地显示
        column_names = {
            'timestamp': '时间',
            'visible': '可见',
            'distance_km': '距离(km)',
            'elevation_deg': '观测仰角(°)',
            'azimuth_deg': '观测方位角(°)',
            'qber': 'QBER',
            'sifted_rate': '筛选密钥率(bps)',
            'secret_key_rate': '安全密钥率(bps)',
            'eve_info': 'Eve信息',
            'weather_type': '天气',
            'is_default_weather': '默认天气',
            'satellite_inclination': '轨道倾角(°)'
        }
        df = df.rename(columns=column_names)
        
        # 生成图表 - 使用相对时间（分钟）作为x轴，更适合长时间仿真显示
        # 使用原始results中的时间戳计算相对时间
        base_time = results[0]['timestamp']
        time_minutes = []
        for r in results:
            ts = r['timestamp']
            # 确保两个时间都有时区或都没有
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                if hasattr(base_time, 'tzinfo') and base_time.tzinfo is not None:
                    diff = (ts - base_time).total_seconds() / 60
                else:
                    # base_time没有时区，去掉ts的时区
                    ts_naive = ts.replace(tzinfo=None)
                    diff = (ts_naive - base_time).total_seconds() / 60
            else:
                if hasattr(base_time, 'tzinfo') and base_time.tzinfo is not None:
                    # ts没有时区，去掉base_time的时区
                    base_naive = base_time.replace(tzinfo=None)
                    diff = (ts - base_naive).total_seconds() / 60
                else:
                    diff = (ts - base_time).total_seconds() / 60
            time_minutes.append(diff)
        
        fig1 = self.visualizer.create_key_rate_plot(
            time_minutes,
            [r['secret_key_rate'] for r in results],
            [r['sifted_rate'] for r in results],
            xaxis_title="时间 (分钟)"
        )
        
        fig2 = self.visualizer.create_qber_plot(
            time_minutes,
            [r['qber'] for r in results],
            xaxis_title="时间 (分钟)"
        )
        
        # 计算平均安全指标（避免空数组警告）
        visible_qber = [r['qber'] for r in results if r['visible']]
        visible_eve = [r['eve_info'] for r in results if r['visible']]
        visible_sifted = [r['sifted_rate'] for r in results if r['visible']]
        visible_secret = [r['secret_key_rate'] for r in results if r['visible']]
        
        avg_qber = np.mean(visible_qber) if visible_qber else 0.0
        avg_eve = np.mean(visible_eve) if visible_eve else 0.0
        avg_sifted = np.mean(visible_sifted) if visible_sifted else 0.0
        avg_secret = np.mean(visible_secret) if visible_secret else 0.0
        
        # 计算实际的安全密钥比例（安全密钥/筛选密钥）
        if avg_sifted > 0:
            secure_key_ratio = avg_secret / avg_sifted
        else:
            secure_key_ratio = 0
        
        fig3 = self.visualizer.create_security_analysis_plot(
            avg_qber, avg_eve, 
            secure_key_ratio
        )
        
        # 生成卫星星下点轨迹地图
        map_fig = self._create_satellite_map(
            timeline, gs, satellite, is_demo
        )
        
        return summary, df, fig1, fig2, fig3, map_fig
    
    def _generate_summary(self, results: list, attack_type: str, enable_privacy_amp: bool = False) -> str:
        """生成结果摘要"""
        visible_results = [r for r in results if r['visible']]
        
        # 获取天气显示（无论是否可见）
        all_weather_types = [r.get('weather_type', '未知') for r in results]
        weather_display = all_weather_types[0] if all_weather_types else '未知'
        is_default = results[0].get('is_default_weather', True) if results else True
        weather_source = "🌐 实时API" if not is_default else "📋 默认数据"
        
        if not visible_results:
            return f"""⚠️ **卫星在仿真期间不可见**

**地面站天气**: {weather_display} ({weather_source})

**建议**:
- 演示卫星（始终可见）
- 延长仿真时间至24小时
- 切换地面站位置"""
        
        # 计算可见时间统计
        total_points = len(results)
        visible_points = len(visible_results)
        visibility_ratio = visible_points / total_points * 100
        
        # 计算可见时间段
        time_step_min = 1  # 假设每分钟一个点
        if total_points > 1:
            time_step_min = (results[1]['timestamp'] - results[0]['timestamp']).total_seconds() / 60
        
        visible_duration = visible_points * time_step_min  # 分钟
        
        avg_qber = np.mean([r['qber'] for r in visible_results])
        avg_secret = np.mean([r['secret_key_rate'] for r in visible_results])
        max_secret = max([r['secret_key_rate'] for r in visible_results])
        total_key = sum([r['secret_key_rate'] * time_step_min * 60 for r in visible_results])  # 比特
        
        # 格式化可见时长
        if visible_duration >= 60:
            duration_str = f"{visible_duration/60:.1f}小时"
        else:
            duration_str = f"{visible_duration:.0f}分钟"
        
        summary = f"""
## 仿真结果摘要

### 链路状态
- **可见性**: {visible_points}/{total_points} ({visibility_ratio:.1f}%)，约{duration_str}
- **平均QBER**: {avg_qber*100:.2f}%
- **地面站天气**: {weather_display} ({weather_source})

### 密钥性能
- **平均安全密钥率**: {avg_secret/1000:.2f} kbps
- **峰值密钥率**: {max_secret/1000:.2f} kbps
- **估算总密钥量**: {total_key/1000:.2f} kbits

### 安全分析
- **攻击类型**: {ATTACK_TYPES[attack_type]['name']}
- **Eve原始信息**: {np.mean([r['eve_info'] for r in visible_results])*100:.1f}%
- **隐私放大**: {"✅ 已启用 - Eve信息已消除" if enable_privacy_amp else "❌ 未启用"}
- **安全等级**: {self._get_security_level(avg_qber, np.mean([r['eve_info'] for r in visible_results]), enable_privacy_amp)}

### 建议
{self._get_security_advice(avg_qber, np.mean([r['eve_info'] for r in visible_results]), enable_privacy_amp)}
"""
        return summary
    
    def _create_satellite_map(self, timeline: list, ground_station: dict, 
                              satellite_name: str, is_demo: bool) -> go.Figure:
        """
        创建卫星星下点轨迹地图
        
        Args:
            timeline: 轨道时间线数据
            ground_station: 地面站信息
            satellite_name: 卫星名称
            is_demo: 是否为演示模式
            
        Returns:
            Plotly Figure对象
        """
        # 创建基础地图
        fig = self.world_map.create_base_map()
        
        # 添加地面站标记
        gs_name = ground_station.get('name', 'Ground Station')
        fig = self.world_map.add_ground_station(
            fig, 
            ground_station['lon'], 
            ground_station['lat'],
            name=gs_name,
            color="green"
        )
        
        # 提取星下点轨迹
        # 检查timeline中是否有卫星位置数据
        if timeline and len(timeline) > 0:
            # 判断是否有真实卫星位置数据
            first_point = timeline[0]
            
            if 'sat_lat' in first_point and 'sat_lon' in first_point:
                # 真实卫星或演示模式有位置数据
                lons = [p['sat_lon'] for p in timeline]
                lats = [p['sat_lat'] for p in timeline]
                timestamps = [p['timestamp'].strftime('%H:%M:%S') for p in timeline]
                
                track_name = f"{satellite_name} (Demo)" if is_demo else satellite_name
                fig = self.world_map.add_satellite_track(
                    fig, lons, lats, timestamps, track_name
                )
            else:
                # 没有卫星位置数据，添加提示文本
                fig.add_annotation(
                    text="No satellite position data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="red")
                )
        
        # 更新标题
        mode_text = "演示模式" if is_demo else "真实轨道"
        fig.update_layout(
            title=f"卫星星下点轨迹 - {satellite_name} ({mode_text})",
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig
    
    def _get_help_content(self) -> str:
        """返回帮助文档内容"""
        return """
## 📚 系统功能完整说明

---

### 1️⃣ QKD密钥生成流程

```
Alice发送 ──────> 信道传输 ──────> Bob接收
  100万脉冲        （损耗90%）       10万探测
       │                               │
       └──────── 原始密钥 ─────────────┘
                    │
                    ▼ 基对比（Sifting）
              筛选密钥（Sifted）
                    │
                    ▼ 误码纠错
              纠错后密钥
                    │
                    ▼ 隐私放大
              安全密钥（Secure）
```

**三个阶段：**
| 阶段 | 说明 | 比例 |
|------|------|------|
| **筛选密钥** | Alice和Bob对比基，保留基匹配的比特 | 原始探测的50% |
| **纠错后密钥** | 通过纠错码修正误码 | 略少于筛选密钥 |
| **安全密钥** | 压缩密钥消除Eve信息 | 筛选密钥的20-80% |

---

### 2️⃣ 攻击类型详解

#### 🔴 截获-重发攻击（Intercept-Resend）
- **原理**：Eve拦截全部光子，测量后重新发送
- **对QBER影响**：引入 **+25%** 额外误码
- **检测方法**：QBER异常升高（>11%时报警）
- **防御策略**：当QBER>11%时中止通信

#### 🟡 光束分离攻击（Beam-Splitting）
- **原理**：Eve用分束器分流部分光强（如30%）
- **对QBER影响**：**不引入误码**
- **检测难度**：⭐⭐⭐⭐⭐（极难直接探测）
- **防御策略**：
  - 必须启用**隐私放大**消除Eve信息
  - 或监测信道损耗异常

#### 🟠 光子数分离攻击（PNS）
- **原理**：针对弱脉冲光源，分离多光子态中的一个光子
- **对QBER影响**：**不引入误码**
- **目标**：专门攻击多光子脉冲
- **防御策略**：
  - 必须启用**诱骗态协议**检测
  - 配合隐私放大消除信息

---

### 3️⃣ 防御机制说明

#### 🔐 隐私放大（Privacy Amplification）
**作用**：主动牺牲部分密钥长度，消除Eve的所有信息

**效果**（针对Eve信息比例τ）：
| Eve信息 | 不开隐私放大 | 开隐私放大 |
|---------|-------------|-----------|
| 0%（无攻击）| 安全 | 安全 |
| 20%（光束分离）| ❌ 不安全 | ✅ 安全（损失40%密钥）|
| 50%（截获重发）| ❌ 不安全 | ✅ 安全（损失100%密钥）|

**适用场景**：
- ✅ 通用防御，对所有攻击有效
- ✅ 光束分离攻击的唯一有效防御

#### 🎭 诱骗态协议（Decoy State Protocol）
**作用**：发送不同强度的脉冲（信号态+诱骗态），检测PNS攻击

**效果**：
| 攻击类型 | 诱骗态效果 |
|---------|-----------|
| PNS攻击 | ✅ **非常有效**（损失~90% Eve信息）|
| 光束分离 | ⚠️ 效果有限（损失~50% Eve信息）|
| 截获重发 | ❌ 无效（靠QBER检测）|

**适用场景**：
- ✅ PNS攻击的主要防御手段
- ⚠️ 对光束分离攻击需配合隐私放大

---

### 4️⃣ 安全等级评价标准

```
🟢 高（安全）
   ├── QBER < 5%
   └── Eve信息已被消除（启用隐私放大）

🟡 中（警告）
   ├── 5% ≤ QBER < 11%
   或 Eve信息 > 5% 但未启用防御

🔴 低（危险）
   ├── QBER ≥ 11%（超过安全阈值）
   或 Eve信息 > 15% 且未启用防御
```

---

### 5️⃣ 天气影响QBER计算算法

#### 计算流程
天气数据通过以下步骤影响QBER：

```
能见度 ──> 大气衰减系数(dB/km) ──> 斜距路径衰减 ──> 信道透射率 ──> QBER
```

**步骤1：能见度→衰减系数**
```
能见度 >= 20km:  衰减系数 = 0.2 dB/km  (晴天)
能见度 >= 10km:  衰减系数 = 0.5 dB/km  (多云)
能见度 >= 5km:   衰减系数 = 1.0 dB/km  (轻霾)
能见度 >= 2km:   衰减系数 = 2.0 dB/km  (霾)
能见度 >= 1km:   衰减系数 = 5.0 dB/km  (雾)
能见度 < 1km:    衰减系数 = 10.0 dB/km (浓雾)
```

**步骤2：斜距路径计算**
考虑分层大气模型：
- **晴朗天气**：有效高度 20km（光可穿透整个大气层）
- **雨/雾天气**：有效高度 3km（雨雾只存在于低层）

斜距路径长度 = 有效高度 / sin(仰角)  
*注：仰角<5°时按5°计算，避免除以零*

**步骤3：Beer-Lambert定律计算透射率**
```
总衰减(dB) = 衰减系数 × 路径长度
透射率 T = 10^(-总衰减/10)
```
衰减上限30dB（透射率不低于0.1%）

**步骤4：信噪比与QBER**
```
信号探测率 = 脉冲率 × 平均光子数 × 透射率 × 探测器效率
总探测率 = 信号探测率 + 暗计数率

信噪比 SNR = 信号探测率 / 暗计数率

基础误码 = 1%（光学系统固有）
暗计数贡献 = 0.5 × (暗计数率 / 总探测率)
QBER = 基础误码 + 暗计数贡献
```

当透射率降低时，信号探测率下降，暗计数占比上升，导致QBER升高。

#### 天气影响示例
| 天气 | 能见度 | 衰减系数 | 90°仰角透射率 | 30°仰角透射率 | 典型QBER |
|------|--------|---------|--------------|--------------|---------|
| ☀️ 晴天 | 20km+ | 0.2 dB/km | 91% | 87% | ~1.0% |
| ☁️ 多云 | 10km | 0.5 dB/km | 79% | 71% | ~1.5% |
| 🌧️ 小雨 | 5km | 3.0 dB/km | 95%* | 87%* | ~3.5% |
| ⛈️ 大雨 | 2km | 8.0 dB/km | 88%* | 69%* | ~8.0% |
| 🌫️ 雾天 | 1km | 10.0 dB/km | 85%* | 61%* | ~15% |

*雨/雾使用3km有效高度计算*

**关键物理规律**：
- 仰角越低，斜距越长，衰减越严重
- 晴天的衰减随仰角变化更敏感（20km vs 3km）
- 暗计数在低信噪比时显著推高QBER

---

### 6️⃣ 卫星与观测站说明

**演示-ISS类型过顶卫星**：
- 模拟400km轨道高度的低轨卫星
- 仰角从0°→90°→0°变化（完整过境）
- 信号强度随仰角增加（距离更近）
- 全程约90分钟，可自选天气条件

**真实卫星 vs 演示模式**：

| 特性 | 演示模式 | 真实卫星 |
|------|---------|---------|
| 可见性 | 始终可见（模拟过境） | 只在过境窗口可见 |
| 用途 | 教学演示、算法验证 | 真实任务规划 |
| 轨道数据 | 正弦波模拟 | 真实TLE数据 |
| 天气 | 可选模拟/API | API实时数据 |

**关于"看不到卫星"的问题**：

如果您选择真实卫星后显示"不可见"或仰角为负（如-45°），这是**正常现象**，因为：

1. **轨道特性**：真实卫星只在特定时间过境（每天1-2次，每次5-15分钟）
2. **时间窗口**：当前仿真时间可能恰好不在过境窗口
3. **TLE有效期**：示例TLE数据是2024年的，可能影响精度

**解决方案**：
1. ✅ **使用演示模式**（推荐教学使用）- 始终可见，完整展示过境过程
2. 设置**24小时仿真** - 等待过境窗口
3. 更新TLE数据 - 从 [CelesTrak](https://celestrak.org/) 下载最新数据

**可用卫星**：
- ✅ **演示-ISS类型过顶** - 始终可见，推荐教学使用
- ✅ **国际空间站(ISS)** - 真实TLE数据（可能需等待过境窗口）
- ⚠️ **中国空间站/墨子号** - 示例TLE，需用户自行更新

**国际观测站**（支持实时天气API）：
| 地区 | 观测站 | 特点 |
|------|--------|------|
| 亚洲 | 东京、首尔、新加坡、曼谷 | 季风气候，多云雨 |
| 欧洲 | 维也纳、日内瓦、伦敦、巴黎、柏林 | 温带海洋性气候 |
| 北美 | 华盛顿、多伦多 | 大陆性气候 |
| 其他 | 悉尼、迪拜、新德里等 | 多样气候条件 |

---

### 7️⃣ 快速操作指南

#### 基础测试（推荐新手）
1. 选择"演示-ISS类型过顶"
2. 选择"晴天"天气
3. 设置仿真时长60分钟
4. 点击"运行仿真"

#### 攻击测试
1. 选择"光束分离攻击"
2. **不启用**隐私放大 → 观察安全等级变化
3. **启用**隐私放大 → 观察密钥率下降

#### PNS攻击测试
1. 选择"PNS攻击"
2. 对比：
   - 只开诱骗态：检测攻击
   - 开诱骗态+隐私放大：完全防御

---

**💡 提示**：本系统基于GLLP安全性分析和BB84协议，所有参数均参考实际星地QKD实验数据。
"""
    
    def _get_weather_from_df(self, weather_df: pd.DataFrame, timestamp: datetime) -> Dict:
        """
        从预获取的天气DataFrame中插值获取指定时间点的天气数据
        
        Args:
            weather_df: 包含小时级天气数据的DataFrame
            timestamp: 目标时间戳
            
        Returns:
            dict: 该时间点的天气参数
        """
        try:
            # 确保timestamp和df['time']时区一致
            if timestamp.tzinfo is not None:
                ts_naive = timestamp.replace(tzinfo=None)
            else:
                ts_naive = timestamp
            
            # 确保df['time']也是naive
            if pd.api.types.is_datetime64_any_dtype(weather_df['time']):
                if weather_df['time'].dt.tz is not None:
                    weather_df['time'] = weather_df['time'].dt.tz_localize(None)
            
            # 找到最接近的时间点
            weather_df['time_diff'] = abs(weather_df['time'] - ts_naive)
            nearest_idx = weather_df['time_diff'].idxmin()
            row = weather_df.loc[nearest_idx]
            
            # 构建天气详情字符串
            visibility_info = ""
            if 'visibility' in row and pd.notna(row['visibility']):
                vis_km = row['visibility'] / 1000
                visibility_info = f" 能见度{vis_km:.1f}km"
            
            cloud_detail = ""
            if 'cloud_low' in row:
                cloud_detail = f" 低云{row['cloud_low']:.0f}%"
            
            weather_type_full = row['weather_type'] + cloud_detail + visibility_info
            
            return {
                'temperature': row['temp_c'],
                'humidity': row['rh'],
                'wind_speed': row['wind'],
                'precipitation': row['precip'],
                'pressure': row['pressure'],
                'cloud_cover': row['cloud'],
                'weather_code': row['weather_code'],
                'weather_type': weather_type_full,
                'attenuation_db_per_km': row['attenuation_db_per_km'],
                'is_default': row.get('is_default', True)
            }
        except Exception as e:
            # 出错时返回默认天气
            return {
                'temperature': 20.0, 'humidity': 50.0, 'wind_speed': 5.0,
                'precipitation': 0.0, 'pressure': 1013.0, 'cloud_cover': 10.0,
                'weather_code': 0, 'weather_type': f'晴(插值出错:{str(e)[:20]})',
                'attenuation_db_per_km': 0.2, 'is_default': True
            }
    
    def _get_security_level(self, qber: float, eve_info: float, privacy_amp: bool) -> str:
        """
        计算安全等级
        综合考虑QBER、Eve信息和隐私放大状态
        """
        # QBER过高，直接判定为低
        if qber >= 0.11:
            return "🔴 低 (QBER超过安全阈值)"
        
        # 有Eve攻击且未启用隐私放大
        if eve_info > 0.15 and not privacy_amp:
            return "🔴 低 (受到攻击但未启用防御)"
        if eve_info > 0.05 and not privacy_amp:
            return "🟡 中 (建议启用隐私放大)"
        
        # 基于QBER判断
        if qber < 0.05:
            return "🟢 高"
        else:
            return "🟡 中"
    
    def _get_security_advice(self, qber: float, eve_info: float, privacy_amp: bool) -> str:
        """生成安全建议"""
        if eve_info > 0.15 and not privacy_amp:
            return "⚠️ 严重警告：受到攻击但未启用隐私放大，通信不安全！"
        if eve_info > 0 and not privacy_amp:
            return "⚠️ 建议启用隐私放大以消除Eve信息泄露"
        if qber > 0.08:
            return "⚠️ QBER偏高，建议检查信道质量"
        return "✅ 当前安全策略适当"
    
    def _generate_demo_timeline(self, start_time, end_time, ground_station, step_seconds=60):
        """
        生成演示用的时间线（模拟卫星过境）
        
        生成正弦波形状的仰角变化，模拟一次完整的过境
        """
        from datetime import timedelta
        
        timeline = []
        
        # 确保start_time和end_time都是带时区的
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        # 创建current_time的副本（避免修改原始start_time）
        current_time = start_time.replace()
        
        # 过境参数 - 优化为更好的演示效果
        max_elevation = 90  # 最大仰角（度）- 天顶过顶
        orbit_height_km = 400  # 轨道高度（km）- 更低的轨道 = 更强信号
        earth_radius_km = 6371  # 地球半径（km）
        
        # 预计算总秒数
        total_seconds = (end_time - start_time).total_seconds()
        
        step = 0
        while current_time <= end_time:
            # 计算仿真进度（0到1）
            elapsed_seconds = step * step_seconds
            progress = elapsed_seconds / total_seconds if total_seconds > 0 else 0
            
            # 使用正弦波模拟仰角变化（从0度开始，达到最大，再回落）
            angle = progress * math.pi  # 0 到 π
            elevation = max_elevation * math.sin(angle)
            
            # 计算斜距
            if elevation > 0:
                elev_rad = math.radians(elevation)
                min_dist = orbit_height_km
                max_dist = math.sqrt(orbit_height_km**2 + 2*earth_radius_km*orbit_height_km)
                distance = max_dist - (max_dist - min_dist) * math.sin(elev_rad)
            else:
                distance = 2000
            
            timeline.append({
                'timestamp': current_time.replace(),  # 创建副本
                'sat_lat': ground_station['lat'] + 10 * math.cos(angle),
                'sat_lon': ground_station['lon'] + 10 * math.sin(angle),
                'sat_altitude_km': orbit_height_km,
                'distance_km': distance,
                'elevation_deg': elevation,
                'azimuth_deg': 180 + 90 * math.sin(angle),
                'visible': elevation > 10
            })
            
            current_time = current_time + timedelta(seconds=step_seconds)
            step += 1
        
        return timeline
    
    def create_interface(self):
        """创建Gradio界面"""
        
        with gr.Blocks(title="星地量子密钥分发链路仿真系统") as interface:
            gr.Markdown("""
            # 🛰️ 星地量子密钥分发链路仿真系统
            
            基于真实卫星轨道和实时气象数据的QKD链路仿真平台
            """)
            
            with gr.Row():
                # 左侧控制面板
                with gr.Column(scale=1):
                    gr.Markdown("### 仿真参数设置")
                    
                    satellite_select = gr.Dropdown(
                        choices=list(SAMPLE_TLE.keys()),
                        value="演示-ISS类型过顶",
                        label="选择卫星 - 推荐先用演示卫星测试"
                    )
                    
                    ground_station_select = gr.Dropdown(
                        choices=list(GROUND_STATIONS.keys()),
                        value="USTC_合肥",
                        label="地面站"
                    )
                    
                    duration_slider = gr.Slider(
                        minimum=10, maximum=1440, value=90, step=10,
                        label="仿真时长 (分钟) - 最大支持24小时"
                    )
                    
                    timestep_slider = gr.Slider(
                        minimum=30, maximum=300, value=60, step=30,
                        label="时间步长 (秒)"
                    )
                    
                    attack_select = gr.Dropdown(
                        choices=list(ATTACK_TYPES.keys()),
                        value="none",
                        label="攻击类型"
                    )
                    
                    with gr.Accordion("演示选项", open=True):
                        demo_weather_mode = gr.Dropdown(
                            choices=["使用实时API天气", "使用自选模拟天气"],
                            value="使用自选模拟天气",
                            label="演示模式天气来源"
                        )
                        weather_select = gr.Dropdown(
                            choices=["晴天", "多云", "小雨", "大雨", "雾天"],
                            value="晴天",
                            label="自选天气条件（仅自选模式有效）"
                        )
                    
                    with gr.Accordion("防御选项", open=True):
                        decoy_checkbox = gr.Checkbox(
                            label="启用诱骗态协议",
                            value=False
                        )
                        privacy_checkbox = gr.Checkbox(
                            label="启用隐私放大",
                            value=True
                        )
                    
                    run_button = gr.Button("🚀 运行仿真", variant="primary")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 使用说明")
                    gr.Markdown("""
                    **快速开始：**
                    1. 选择"演示-ISS类型过顶"卫星
                    2. 选择天气来源：
                       - 使用实时API天气：获取真实气象数据
                       - 使用自选模拟天气：选择晴天/小雨等预设
                    3. 设置仿真时长（如60-90分钟）
                    4. 点击"运行仿真"
                    
                    **结果查看：**
                    - 📊 结果摘要：密钥率、QBER、安全分析
                    - 📈 详细数据：逐点仿真数据表格
                    - 📉 性能图表：密钥率/QBER/安全等级随时间变化
                    - 🌍 卫星轨迹：显示卫星星下点轨迹和地面站位置
                    
                    **提示：**
                    - 演示模式支持实时天气API，始终有卫星过境（用于教学演示）
                    - 晴天信道最好，雾天/大雨最差
                    - 真实卫星需设置24小时仿真才能等到过境窗口
                    - 如果真实卫星显示"不可见"，请检查TLE数据是否最新
                    - 卫星轨迹地图显示世界地图+首都+回归线+卫星轨道
                    """)
                
                # 右侧结果面板
                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.TabItem("📊 结果摘要"):
                            summary_output = gr.Markdown()
                        
                        with gr.TabItem("📈 详细数据"):
                            table_output = gr.DataFrame()
                        
                        with gr.TabItem("📉 性能图表"):
                            with gr.Row():
                                keyrate_plot = gr.Plot(label="密钥率")
                                qber_plot = gr.Plot(label="QBER")
                            security_plot = gr.Plot(label="安全分析")
                        
                        with gr.TabItem("🌍 卫星轨迹"):
                            map_plot = gr.Plot(label="星下点轨迹")
            
            # 绑定按钮事件
            run_button.click(
                fn=self.run_simulation,
                inputs=[
                    satellite_select,
                    ground_station_select,
                    duration_slider,
                    timestep_slider,
                    attack_select,
                    demo_weather_mode,
                    weather_select,
                    decoy_checkbox,
                    privacy_checkbox
                ],
                outputs=[
                    summary_output,
                    table_output,
                    keyrate_plot,
                    qber_plot,
                    security_plot,
                    map_plot
                ]
            )
            
            # 帮助按钮和内容
            with gr.Accordion("📚 点击查看完整功能说明", open=False):
                help_content = gr.Markdown(self._get_help_content())
            
            gr.Markdown("---")
            gr.Markdown("""
            ### 📖 系统说明
            
            **系统功能：**
            - 真实卫星轨道计算（基于TLE数据）
            - 实时气象数据集成（Open-Meteo API）
            - BB84协议完整仿真
            - 三类Eve攻击模拟（截获-重发、光束分离、PNS）
            - 安全防御机制（诱骗态、隐私放大）
            
            **参考文献：**
            - GLLP安全性分析
            - Decoy-State QKD (Wang 2005, Lo 2005)
            - 星地量子通信综述
            """)
        
        return interface


def create_simple_demo():
    """
    创建简化演示界面（如果完整版依赖不全）
    """
    with gr.Blocks(title="QKD仿真系统 - 演示模式") as demo:
        gr.Markdown("""
        # 🛰️ 星地量子密钥分发链路仿真系统
        ## 演示模式
        
        这是一个简化演示界面。
        """)
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 系统功能")
                gr.Markdown("""
                - ✅ 卫星轨道计算模块
                - ✅ 气象数据获取模块
                - ✅ QKD协议核心模块
                - ✅ Eve攻击模拟模块
                - ✅ 安全防御模块
                - ✅ 可视化模块
                """)
            
            with gr.Column():
                gr.Markdown("### 运行测试")
                test_btn = gr.Button("运行模块测试")
                test_output = gr.Textbox(label="测试结果", lines=10)
        
        def run_tests():
            results = []
            
            # 测试轨道模块
            try:
                from modules.orbit_adapter import OrbitAdapter
                tle = SAMPLE_TLE["中国空间站"]
                adapter = OrbitAdapter(tle["line1"], tle["line2"])
                results.append("✅ 轨道模块测试通过")
            except Exception as e:
                results.append(f"❌ 轨道模块错误: {str(e)}")
            
            # 测试信道模块
            try:
                from modules.channel_model import ChannelModel
                model = ChannelModel()
                results.append("✅ 信道模块测试通过")
            except Exception as e:
                results.append(f"❌ 信道模块错误: {str(e)}")
            
            # 测试QKD模块
            try:
                from modules.qkd_core import BB84SatelliteQKD
                qkd = BB84SatelliteQKD(channel_transmission=0.1)
                result = qkd.simulate_exchange(n_pulses=1000)
                results.append(f"✅ QKD模块测试通过 (QBER: {result['qber_percent']:.2f}%)")
            except Exception as e:
                results.append(f"❌ QKD模块错误: {str(e)}")
            
            # 测试攻击模块
            try:
                from modules.eve_attacks import InterceptResendAttack
                attack = InterceptResendAttack(0.5)
                results.append("✅ 攻击模块测试通过")
            except Exception as e:
                results.append(f"❌ 攻击模块错误: {str(e)}")
            
            # 测试防御模块
            try:
                from modules.security_defense import PrivacyAmplification
                pa = PrivacyAmplification()
                results.append("✅ 防御模块测试通过")
            except Exception as e:
                results.append(f"❌ 防御模块错误: {str(e)}")
            
            return "\n".join(results)
        
        test_btn.click(fn=run_tests, outputs=test_output)
        
        gr.Markdown("---")
        gr.Markdown("""
        ### 使用说明
        
        完整功能需要安装依赖：
        ```bash
        pip install -r requirements.txt
        ```
        
        然后运行：
        ```bash
        python app.py
        ```
        """)
    
    return demo


def main():
    """主函数"""
    print("=" * 60)
    print("星地量子密钥分发链路仿真系统")
    print("=" * 60)
    
    # 检查依赖
    try:
        import gradio
        import plotly
        import skyfield
        print("\n✅ 所有依赖已安装")
        
        # 创建完整界面
        app = QKDSimulationApp()
        interface = app.create_interface()
        
    except ImportError as e:
        print(f"\n⚠️ 部分依赖未安装: {e}")
        print("启动演示模式...")
        interface = create_simple_demo()
    
    # 启动应用
    print("\n启动Gradio服务...")
    print("如果7860端口被占用，会自动尝试其他端口")
    interface.launch(
        server_name="127.0.0.1",  # 使用本地地址，避免防火墙问题
        server_port=7861,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
