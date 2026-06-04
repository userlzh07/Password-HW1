"""
气象数据适配模块
基于Open-Meteo API获取实时天气数据
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENMETEO_CONFIG, WEATHER_ATTENUATION


class WeatherAdapter:
    """
    气象数据适配器
    
    功能:
        1. 从Open-Meteo获取实时/预报天气数据
        2. 获取历史天气数据
        3. 将天气代码转换为大气衰减系数
    """
    
    def __init__(self):
        self.forecast_url = OPENMETEO_CONFIG["forecast_url"]
        self.archive_url = OPENMETEO_CONFIG["archive_url"]
        self.default_params = OPENMETEO_CONFIG["default_params"]
        
    def get_weather_data(self, 
                         lat: float, 
                         lon: float, 
                         forecast_days: int = 7,
                         max_retries: int = 2) -> pd.DataFrame:
        """
        获取指定位置的预报天气数据（带重试机制）
        
        Args:
            lat: 纬度
            lon: 经度
            forecast_days: 预报天数
            max_retries: 最大重试次数
            
        Returns:
            DataFrame: 天气数据表
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": self.default_params["hourly"],
            "forecast_days": forecast_days,
            "timezone": self.default_params["timezone"]
        }
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # 增加延迟避免请求过快
                if attempt > 0:
                    import time
                    time.sleep(0.3)  # 固定短延迟
                
                # 使用5秒超时
                response = requests.get(
                    self.forecast_url, 
                    params=params, 
                    timeout=5,
                    headers={'User-Agent': 'QKD-Satellite-Sim/1.0'}
                )
                response.raise_for_status()
                data = response.json()
                
                # 整理数据 - 包含更详细的云量和能见度
                df = pd.DataFrame({
                    'time': pd.to_datetime(data['hourly']['time']),
                    'temp_c': data['hourly']['temperature_2m'],
                    'rh': data['hourly']['relative_humidity_2m'],
                    'wind': data['hourly']['wind_speed_10m'],
                    'wind_dir': data['hourly']['wind_direction_10m'],
                    'precip': data['hourly']['precipitation'],
                    'pressure': data['hourly']['pressure_msl'],
                    'cloud': data['hourly']['cloud_cover'],
                    'cloud_low': data['hourly'].get('cloud_cover_low', data['hourly']['cloud_cover']),
                    'cloud_mid': data['hourly'].get('cloud_cover_mid', 0),
                    'cloud_high': data['hourly'].get('cloud_cover_high', 0),
                    'visibility': data['hourly'].get('visibility', None),  # 能见度(m)
                    'weather_code': data['hourly']['weather_code']
                })
                
                # 使用能见度、云层和天气代码计算衰减系数
                # 综合考虑：能见度（雾/霾）、云层（散射）、天气代码（整体趋势）
                def calculate_combined_attenuation(row):
                    # 1. 基础衰减：从天气代码获取（晴天0.2，多云0.3等）
                    code_attenuation = self.weather_code_to_attenuation(row['weather_code'])
                    
                    # 2. 能见度衰减（如果能见度数据可用）
                    visibility_attenuation = None
                    if pd.notna(row.get('visibility')):
                        visibility_attenuation = self._calculate_attenuation_from_visibility(
                            row['visibility'],
                            0,  # 云层单独计算，这里先传0
                            0
                        )
                    
                    # 3. 云层附加衰减（低云+高云）
                    low_cloud = row.get('cloud_low', row.get('cloud', 0))
                    high_cloud = row.get('cloud_high', 0)
                    # 低云影响更大（每10%增加0.15），高云影响较小（每10%增加0.05）
                    cloud_correction = (low_cloud / 100.0) * 1.5 + (high_cloud / 100.0) * 0.5
                    
                    # 综合：取天气代码和能见度的较大者，加上云层修正
                    if visibility_attenuation is not None:
                        # 能见度好时（<0.5），更相信天气代码的整体趋势
                        if visibility_attenuation <= 0.5:
                            base = max(code_attenuation, visibility_attenuation * 0.5)
                        else:
                            base = max(code_attenuation, visibility_attenuation)
                    else:
                        base = code_attenuation
                    
                    return base + cloud_correction
                
                df['attenuation_db_per_km'] = df.apply(calculate_combined_attenuation, axis=1)
                
                # 计算天气类型
                df['weather_type'] = df['weather_code'].apply(
                    lambda x: self.weather_code_to_type(x)
                )
                
                # 成功获取，标记为真实数据
                df['is_default'] = False  # 标记为API数据
                if attempt > 0:
                    print(f"[天气] 第{attempt+1}次尝试成功获取数据")
                return df
                
            except requests.exceptions.SSLError as e:
                last_error = f"SSL错误: {str(e)[:50]}"
                continue  # 重试
            except requests.exceptions.Timeout as e:
                last_error = "连接超时"
                continue  # 重试
            except requests.exceptions.ConnectionError as e:
                last_error = "连接失败"
                continue  # 重试
            except Exception as e:
                last_error = f"其他错误: {str(e)[:50]}"
                break  # 其他错误不重试
        
        # 所有重试失败，返回默认数据并打印错误
        print(f"[天气] API调用失败({last_error})，使用默认天气数据")
        return self._get_default_weather(lat, lon, forecast_days)
    
    def get_historical_data(self,
                           lat: float,
                           lon: float,
                           start_date: datetime,
                           end_date: datetime) -> pd.DataFrame:
        """
        获取历史天气数据
        
        Args:
            lat: 纬度
            lon: 经度
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 历史天气数据
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "hourly": self.default_params["hourly"],
            "timezone": self.default_params["timezone"]
        }
        
        try:
            response = requests.get(self.archive_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame({
                'time': pd.to_datetime(data['hourly']['time']),
                'temp_c': data['hourly']['temperature_2m'],
                'rh': data['hourly']['relative_humidity_2m'],
                'wind': data['hourly']['wind_speed_10m'],
                'precip': data['hourly']['precipitation'],
                'pressure': data['hourly']['pressure_msl'],
                'weather_code': data['hourly']['weather_code']
            })
            
            df['attenuation_db_per_km'] = df['weather_code'].apply(
                lambda x: self.weather_code_to_attenuation(x)
            )
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"获取历史数据失败: {e}")
            return self._get_default_weather(lat, lon, 7)
    
    def get_weather_at_time(self, 
                           lat: float, 
                           lon: float, 
                           timestamp: datetime) -> Dict:
        """
        获取指定时间点的天气数据
        
        Args:
            lat: 纬度
            lon: 经度
            timestamp: 目标时间
            
        Returns:
            dict: 天气参数字典
        """
        # 获取预报数据
        df = self.get_weather_data(lat, lon, forecast_days=7)
        
        # 处理时区问题：确保timestamp和df['time']时区一致
        # 将timestamp转换为naive（去掉时区）
        if timestamp.tzinfo is not None:
            timestamp_naive = timestamp.replace(tzinfo=None)
        else:
            timestamp_naive = timestamp
        
        # 确保df['time']也是naive
        if pd.api.types.is_datetime64_any_dtype(df['time']):
            if df['time'].dt.tz is not None:
                df['time'] = df['time'].dt.tz_localize(None)
        
        # 找到最接近的时间点
        df['time_diff'] = abs(df['time'] - timestamp_naive)
        nearest_idx = df['time_diff'].idxmin()
        nearest_row = df.loc[nearest_idx]
        
        # 构建天气详情字符串
        visibility_info = ""
        if 'visibility' in nearest_row and pd.notna(nearest_row['visibility']):
            vis_km = nearest_row['visibility'] / 1000
            visibility_info = f" 能见度{vis_km:.1f}km"
        
        cloud_detail = ""
        if 'cloud_low' in nearest_row:
            cloud_detail = f" 低云{nearest_row['cloud_low']:.0f}%"
        
        weather_type_full = nearest_row['weather_type'] + cloud_detail + visibility_info
        
        return {
            'temperature': nearest_row['temp_c'],
            'humidity': nearest_row['rh'],
            'wind_speed': nearest_row['wind'],
            'precipitation': nearest_row['precip'],
            'pressure': nearest_row['pressure'],
            'cloud_cover': nearest_row['cloud'],
            'cloud_low': nearest_row.get('cloud_low', nearest_row['cloud']),
            'visibility': nearest_row.get('visibility', None),
            'weather_code': nearest_row['weather_code'],
            'weather_type': weather_type_full,  # 更详细的天气描述
            'attenuation_db_per_km': nearest_row['attenuation_db_per_km'],
            'is_default': nearest_row.get('is_default', True)
        }
    
    def weather_code_to_attenuation(self, code: int) -> float:
        """
        将WMO天气代码转换为衰减系数
        
        WMO Weather interpretation codes:
        0: Clear sky
        1, 2, 3: Mainly clear, partly cloudy, and overcast
        45, 48: Fog
        51, 53, 55: Drizzle
        61, 63, 65: Rain
        71, 73, 75: Snow
        95, 96, 99: Thunderstorm
        """
        if code == 0:
            return 0.2  # 晴天
        elif code in [1, 2, 3]:
            return 0.3  # 多云
        elif code in [45, 48]:
            return 5.0  # 雾
        elif code in [51, 53, 55]:
            return 2.0  # 毛毛雨
        elif code in [61, 63]:
            return 4.0  # 小雨/中雨
        elif code in [65]:
            return 8.0  # 大雨
        elif code in [71, 73, 75]:
            return 6.0  # 雪
        elif code in [80, 81, 82]:
            return 10.0  # 阵雨
        elif code in [95, 96, 99]:
            return 15.0  # 雷暴
        else:
            return 0.5  # 默认
    
    def _calculate_attenuation_from_visibility(self, visibility_m: float, 
                                               cloud_cover_percent: float = 0,
                                               cloud_low_percent: float = None) -> float:
        """
        基于能见度和云层计算大气衰减系数（更精确的方法）
        
        对于量子通信，云层会散射光子，即使能见度好也会有影响。
        
        公式参考：
        - 能见度 > 20km: 0.2 dB/km (晴朗) + 云层修正
        - 能见度 5-20km: 0.5-2.0 dB/km (轻雾)
        - 能见度 1-5km: 2.0-10.0 dB/km (雾)
        - 能见度 < 1km: >10 dB/km (浓雾)
        
        云层修正（针对QKD 850nm波长）：
        - 低云(<2km)每10%增加0.1-0.3 dB/km
        - 高云影响较小
        
        Args:
            visibility_m: 能见度（米）
            cloud_cover_percent: 总云量（%）
            cloud_low_percent: 低云量（%），如果为None则使用总云量估算
            
        Returns:
            float: 衰减系数 (dB/km)
        """
        visibility_km = visibility_m / 1000.0
        
        # 基础衰减（由能见度决定）
        if visibility_km >= 20:
            base_attenuation = 0.2  # 晴朗
        elif visibility_km >= 10:
            base_attenuation = 0.5  # 良好
        elif visibility_km >= 5:
            base_attenuation = 1.0  # 轻雾
        elif visibility_km >= 2:
            base_attenuation = 2.0  # 雾
        elif visibility_km >= 1:
            base_attenuation = 5.0  # 浓雾
        else:
            base_attenuation = 10.0  # 严重雾/霾
        
        # 云层附加衰减（量子通信特性）
        # 使用低云量（<2km）对QKD影响最大
        low_cloud = cloud_low_percent if cloud_low_percent is not None else cloud_cover_percent
        
        # 云层修正：每10%低云增加0.15 dB/km
        # 0%云 -> 0 dB 附加
        # 50%云 -> 0.75 dB 附加  
        # 100%云 -> 1.5 dB 附加
        cloud_correction = (low_cloud / 100.0) * 1.5
        
        return base_attenuation + cloud_correction
    
    def weather_code_to_type(self, code: int) -> str:
        """将天气代码转换为类型描述"""
        weather_types = {
            0: "晴",
            1: "多云",
            2: "多云",
            3: "阴",
            45: "雾",
            48: "雾",
            51: "毛毛雨",
            53: "小雨",
            55: "中雨",
            61: "小雨",
            63: "中雨",
            65: "大雨",
            71: "小雪",
            73: "中雪",
            75: "大雪",
            80: "阵雨",
            81: "强阵雨",
            82: "暴雨",
            95: "雷阵雨",
            96: "雷阵雨伴冰雹",
            99: "强雷暴"
        }
        return weather_types.get(code, "未知")
    
    def calculate_slant_attenuation(self,
                                   attenuation_db_per_km: float,
                                   distance_km: float,
                                   elevation_deg: float) -> float:
        """
        计算斜路径总衰减（考虑仰角）
        
        Args:
            attenuation_db_per_km: 水平衰减系数 (dB/km)
            distance_km: 斜距 (km)
            elevation_deg: 仰角 (度)
            
        Returns:
            float: 总衰减 (dB)
        """
        # 仰角低于10度时，大气路径更长
        if elevation_deg < 10:
            # 使用等效路径长度
            effective_path = distance_km / max(np.sin(np.radians(elevation_deg)), 0.1)
        else:
            effective_path = distance_km
        
        return attenuation_db_per_km * effective_path
    
    def _get_default_weather(self, lat: float, lon: float, days: int) -> pd.DataFrame:
        """
        生成默认天气数据（API失败时使用）
        基于地理位置生成合理的默认数据，并添加昼夜变化
        """
        import math
        
        now = datetime.now()
        times = [now + timedelta(hours=i) for i in range(days * 24)]
        
        # 根据纬度估算基础温度（简化模型）
        # 纬度越低温度越高，合肥(31°N)约20°C，北京(40°N)约15°C
        base_temp = 30 - abs(lat) * 0.3  # 简化估算
        
        data = {
            'time': times,
            'temp_c': [],
            'rh': [],
            'wind': [],
            'wind_dir': [],
            'precip': [],
            'pressure': [],
            'cloud': [],
            'cloud_low': [],
            'cloud_mid': [],
            'cloud_high': [],
            'visibility': [],  # 能见度(m)
            'weather_code': [],
            'weather_type': [],
            'attenuation_db_per_km': [],
            'is_default': []
        }
        
        for i, t in enumerate(times):
            # 添加昼夜温度变化（正弦波）
            hour = t.hour
            temp_variation = 5 * math.sin((hour - 6) * math.pi / 12)  # 白天高晚上低
            temp = base_temp + temp_variation + np.random.normal(0, 1)
            
            # 湿度与温度反向变化
            rh = 60 - temp_variation * 2 + np.random.normal(0, 5)
            rh = max(30, min(90, rh))
            
            # 随机天气代码（主要晴天，偶尔多云）
            if np.random.random() < 0.8:
                code = 0  # 晴天
                wtype = '晴(API默认)'
                atten = 0.2
                cloud = 10
                cloud_low = 5
                visibility = 20000  # 20km能见度
            else:
                code = 2  # 多云
                wtype = '多云(API默认)'
                atten = 0.5
                cloud = 60
                cloud_low = 40
                visibility = 10000  # 10km能见度
            
            data['temp_c'].append(round(temp, 1))
            data['rh'].append(round(rh, 1))
            data['wind'].append(round(5 + np.random.normal(0, 2), 1))
            data['wind_dir'].append(round(np.random.uniform(0, 360), 1))
            data['precip'].append(0.0)
            data['pressure'].append(round(1013 + np.random.normal(0, 5), 1))
            data['cloud'].append(cloud)
            data['cloud_low'].append(cloud_low)
            data['cloud_mid'].append(cloud // 3)  # 简化分配
            data['cloud_high'].append(cloud // 3)
            data['visibility'].append(visibility)
            data['weather_code'].append(code)
            data['weather_type'].append(wtype)
            data['attenuation_db_per_km'].append(atten)
            data['is_default'].append(True)
        
        df = pd.DataFrame(data)
        return df


def test_weather_adapter():
    """测试气象适配器"""
    import numpy as np
    
    print("=" * 50)
    print("测试气象适配器")
    print("=" * 50)
    
    # 初始化适配器
    adapter = WeatherAdapter()
    
    # 获取合肥天气
    lat, lon = 31.8226, 117.2814
    print(f"\n获取合肥 ({lat}, {lon}) 天气数据...")
    
    df = adapter.get_weather_data(lat, lon, forecast_days=1)
    
    print(f"获取到 {len(df)} 条数据")
    print("\n前5条数据预览:")
    print(df[['time', 'temp_c', 'rh', 'weather_type', 'attenuation_db_per_km']].head())
    
    # 获取指定时间天气
    target_time = datetime.now() + timedelta(hours=2)
    weather = adapter.get_weather_at_time(lat, lon, target_time)
    print(f"\n指定时间 ({target_time}) 天气:")
    print(f"  温度: {weather['temperature']:.1f}°C")
    print(f"  湿度: {weather['humidity']:.1f}%")
    print(f"  天气: {weather['weather_type']}")
    print(f"  衰减系数: {weather['attenuation_db_per_km']:.2f} dB/km")
    
    # 计算斜路径衰减
    slant_atten = adapter.calculate_slant_attenuation(
        weather['attenuation_db_per_km'], 
        500,  # 500km斜距
        30    # 30度仰角
    )
    print(f"\n斜路径衰减 (500km, 30°仰角): {slant_atten:.2f} dB")
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    test_weather_adapter()
