"""
轨道动力学适配模块
基于Skyfield实现卫星轨道计算
"""

import numpy as np
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROUND_STATIONS, SAMPLE_TLE, SIMULATION_CONFIG


class OrbitAdapter:
    """
    卫星轨道计算适配器
    
    功能:
        1. 基于TLE数据计算卫星位置
        2. 计算卫星与地面站的斜距、仰角、方位角
        3. 生成过境时间序列
    """
    
    def __init__(self, tle_line1: str, tle_line2: str):
        """
        初始化卫星
        
        Args:
            tle_line1: TLE第一行
            tle_line2: TLE第二行
        """
        self.ts = load.timescale()
        self.satellite = EarthSatellite(tle_line1, tle_line2)
        
    def get_satellite_position(self, timestamp: datetime) -> Dict:
        """
        获取指定时刻的卫星位置
        
        Args:
            timestamp: UTC时间
            
        Returns:
            dict: {
                'lat': 纬度(度),
                'lon': 经度(度),
                'altitude_km': 海拔(km),
                'subpoint': 星下点对象
            }
        """
        t = self.ts.from_datetime(timestamp.replace(tzinfo=timezone.utc))
        geocentric = self.satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)
        
        return {
            'lat': subpoint.latitude.degrees,
            'lon': subpoint.longitude.degrees,
            'altitude_km': subpoint.elevation.km,
            'subpoint': subpoint,
            'geocentric': geocentric
        }
    
    def calculate_slant_range(self, sat_pos: Dict, ground_station: Dict, timestamp: datetime = None) -> Dict:
        """
        计算卫星与地面站的链路几何参数
        
        Args:
            sat_pos: 卫星位置字典（来自get_satellite_position）
            ground_station: 地面站配置字典
            timestamp: 计算时间（可选，默认使用当前时间）
            
        Returns:
            dict: {
                'distance_km': 斜距(km),
                'elevation_deg': 仰角(度),
                'azimuth_deg': 方位角(度),
                'visible': 是否可见(仰角>阈值)
            }
        """
        # 创建地面站地理坐标
        ground_lat = ground_station['lat']
        ground_lon = ground_station['lon']
        ground_elev = ground_station.get('elevation', 0) / 1000.0  # 转换为km
        
        ground_geographic = wgs84.latlon(ground_lat, ground_lon, ground_elev)
        
        # 计算卫星相对于地面站的方位
        # 使用skyfield的差分方法
        difference = self.satellite - ground_geographic
        
        # 使用指定时间或当前时间
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        t = self.ts.from_datetime(timestamp.replace(tzinfo=timezone.utc))
        
        # 计算在地平坐标系中的位置
        topocentric = difference.at(t)
        
        # 获取仰角、方位角和距离
        alt, az, distance = topocentric.altaz()
        
        elevation_deg = alt.degrees
        azimuth_deg = az.degrees
        
        # 判断是否可见
        min_elevation = SIMULATION_CONFIG['min_elevation_deg']
        
        return {
            'distance_km': distance.km,
            'elevation_deg': elevation_deg,
            'azimuth_deg': azimuth_deg,
            'visible': elevation_deg > min_elevation
        }
    
    def generate_pass_timeline(self, 
                              start_time: datetime, 
                              end_time: datetime,
                              ground_station: Dict,
                              step_seconds: int = 60) -> List[Dict]:
        """
        生成卫星过境时间序列数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            ground_station: 地面站配置
            step_seconds: 时间步长（秒）
            
        Returns:
            List[Dict]: 每个时间点的链路状态
        """
        timeline = []
        current_time = start_time
        
        while current_time <= end_time:
            # 获取卫星位置
            sat_pos = self.get_satellite_position(current_time)
            
            # 计算链路参数（传入正确的时间戳）
            link_params = self.calculate_slant_range(sat_pos, ground_station, current_time)
            
            timeline.append({
                'timestamp': current_time,
                'sat_lat': sat_pos['lat'],
                'sat_lon': sat_pos['lon'],
                'sat_altitude_km': sat_pos['altitude_km'],
                'distance_km': link_params['distance_km'],
                'elevation_deg': link_params['elevation_deg'],
                'azimuth_deg': link_params['azimuth_deg'],
                'visible': link_params['visible']
            })
            
            current_time += timedelta(seconds=step_seconds)
        
        return timeline
    
    def get_ground_track(self, 
                         start_time: datetime, 
                         end_time: datetime,
                         step_seconds: int = 60) -> Tuple[List, List, List]:
        """
        计算星下点轨迹（用于地图可视化）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            step_seconds: 时间步长
            
        Returns:
            Tuple: (lons, lats, timestamps)
        """
        t0 = self.ts.from_datetime(start_time.replace(tzinfo=timezone.utc))
        t1 = self.ts.from_datetime(end_time.replace(tzinfo=timezone.utc))
        
        num_steps = int((end_time - start_time).total_seconds() / step_seconds) + 1
        times = self.ts.linspace(t0, t1, num_steps)
        
        lons = []
        lats = []
        timestamps = []
        last_lon = None
        
        for t in times:
            geocentric = self.satellite.at(t)
            subpoint = wgs84.subpoint(geocentric)
            lon = subpoint.longitude.degrees
            lat = subpoint.latitude.degrees
            
            # 处理经度跳变
            if last_lon is not None and abs(lon - last_lon) > 180:
                lons.append(None)
                lats.append(None)
                timestamps.append(None)
            
            lons.append(lon)
            lats.append(lat)
            
            # 转换为北京时间
            utc_dt = t.utc_datetime()
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            beijing_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
            timestamps.append(beijing_dt)
            
            last_lon = lon
        
        return lons, lats, timestamps


def test_orbit_adapter():
    """测试轨道适配器"""
    print("=" * 50)
    print("测试轨道适配器")
    print("=" * 50)
    
    # 获取示例TLE
    tle_data = SAMPLE_TLE["中国空间站"]
    
    # 初始化适配器
    adapter = OrbitAdapter(tle_data["line1"], tle_data["line2"])
    
    # 获取当前位置
    now = datetime.now(timezone.utc)
    pos = adapter.get_satellite_position(now)
    print(f"\n当前卫星位置 (UTC: {now}):")
    print(f"  纬度: {pos['lat']:.4f}°")
    print(f"  经度: {pos['lon']:.4f}°")
    print(f"  高度: {pos['altitude_km']:.2f} km")
    
    # 计算与地面站的链路
    ground_station = GROUND_STATIONS["USTC_合肥"]
    link_params = adapter.calculate_slant_range(pos, ground_station)
    print(f"\n与{ground_station['description']}链路参数:")
    print(f"  斜距: {link_params['distance_km']:.2f} km")
    print(f"  仰角: {link_params['elevation_deg']:.2f}°")
    print(f"  方位角: {link_params['azimuth_deg']:.2f}°")
    print(f"  可见性: {'可见' if link_params['visible'] else '不可见'}")
    
    # 生成过境时间线
    end_time = now + timedelta(hours=1)
    timeline = adapter.generate_pass_timeline(now, end_time, ground_station, step_seconds=300)
    print(f"\n生成过境时间线（{len(timeline)}个时间点）:")
    print(f"  起始仰角: {timeline[0]['elevation_deg']:.2f}°")
    print(f"  结束仰角: {timeline[-1]['elevation_deg']:.2f}°")
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    test_orbit_adapter()
