"""
世界地图 + 卫星星下点轨迹可视化
整合自星下点轨迹展示1.py
"""

import plotly.graph_objects as go
import numpy as np
from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta


# ==================== 首都数据 ====================
CAPITALS_DATA = [
    {"country": "China", "capital": "Beijing", "lon": 116.40, "lat": 39.90},
    {"country": "Japan", "capital": "Tokyo", "lon": 139.69, "lat": 35.69},
    {"country": "India", "capital": "New Delhi", "lon": 77.20, "lat": 28.61},
    {"country": "Russia", "capital": "Moscow", "lon": 37.62, "lat": 55.76},
    {"country": "Egypt", "capital": "Cairo", "lon": 31.24, "lat": 30.04},
    {"country": "UK", "capital": "London", "lon": -0.13, "lat": 51.51},
    {"country": "France", "capital": "Paris", "lon": 2.35, "lat": 48.86},
    {"country": "USA", "capital": "Washington", "lon": -77.04, "lat": 38.91},
    {"country": "Brazil", "capital": "Brasilia", "lon": -47.88, "lat": -15.79},
    {"country": "Australia", "capital": "Canberra", "lon": 149.13, "lat": -35.28},
    {"country": "Canada", "capital": "Ottawa", "lon": -75.70, "lat": 45.42},
    {"country": "Germany", "capital": "Berlin", "lon": 13.40, "lat": 52.52},
    {"country": "Italy", "capital": "Rome", "lon": 12.50, "lat": 41.90},
    {"country": "Spain", "capital": "Madrid", "lon": -3.70, "lat": 40.42},
    {"country": "South Korea", "capital": "Seoul", "lon": 126.98, "lat": 37.57},
    {"country": "North Korea", "capital": "Pyongyang", "lon": 125.75, "lat": 39.03},
    {"country": "Singapore", "capital": "Singapore", "lon": 103.82, "lat": 1.35},
    {"country": "Thailand", "capital": "Bangkok", "lon": 100.50, "lat": 13.75},
    {"country": "Vietnam", "capital": "Hanoi", "lon": 105.85, "lat": 21.03},
    {"country": "Indonesia", "capital": "Jakarta", "lon": 106.83, "lat": -6.17},
    {"country": "Mexico", "capital": "Mexico City", "lon": -99.13, "lat": 19.43},
    {"country": "Argentina", "capital": "Buenos Aires", "lon": -58.38, "lat": -34.60},
    {"country": "South Africa", "capital": "Pretoria", "lon": 28.19, "lat": -25.74},
    {"country": "Turkey", "capital": "Ankara", "lon": 32.85, "lat": 39.93},
    {"country": "Saudi Arabia", "capital": "Riyadh", "lon": 46.72, "lat": 24.65},
    {"country": "Iran", "capital": "Tehran", "lon": 51.42, "lat": 35.69},
    {"country": "Pakistan", "capital": "Islamabad", "lon": 73.07, "lat": 33.72},
    {"country": "Afghanistan", "capital": "Kabul", "lon": 69.18, "lat": 34.53},
    {"country": "Mongolia", "capital": "Ulaanbaatar", "lon": 106.92, "lat": 47.92},
    {"country": "Kazakhstan", "capital": "Astana", "lon": 71.43, "lat": 51.18},
    {"country": "Poland", "capital": "Warsaw", "lon": 21.01, "lat": 52.23},
    {"country": "Ukraine", "capital": "Kiev", "lon": 30.52, "lat": 50.45},
    {"country": "Sweden", "capital": "Stockholm", "lon": 18.07, "lat": 59.33},
    {"country": "Norway", "capital": "Oslo", "lon": 10.75, "lat": 59.91},
    {"country": "Finland", "capital": "Helsinki", "lon": 24.94, "lat": 60.17},
    {"country": "Netherlands", "capital": "Amsterdam", "lon": 4.90, "lat": 52.37},
    {"country": "Belgium", "capital": "Brussels", "lon": 4.35, "lat": 50.85},
    {"country": "Switzerland", "capital": "Bern", "lon": 7.45, "lat": 46.95},
    {"country": "Austria", "capital": "Vienna", "lon": 16.37, "lat": 48.21},
    {"country": "Greece", "capital": "Athens", "lon": 23.73, "lat": 37.98},
    {"country": "Portugal", "capital": "Lisbon", "lon": -9.14, "lat": 38.72},
    {"country": "Ireland", "capital": "Dublin", "lon": -6.26, "lat": 53.35},
    {"country": "New Zealand", "capital": "Wellington", "lon": 174.78, "lat": -41.29},
    {"country": "Chile", "capital": "Santiago", "lon": -70.65, "lat": -33.45},
    {"country": "Peru", "capital": "Lima", "lon": -77.04, "lat": -12.05},
    {"country": "Colombia", "capital": "Bogota", "lon": -74.08, "lat": 4.60},
    {"country": "Nigeria", "capital": "Abuja", "lon": 7.50, "lat": 9.08},
    {"country": "Kenya", "capital": "Nairobi", "lon": 36.82, "lat": -1.29},
    {"country": "Ethiopia", "capital": "Addis Ababa", "lon": 38.75, "lat": 9.02},
    {"country": "Morocco", "capital": "Rabat", "lon": -6.84, "lat": 34.02},
    {"country": "Iceland", "capital": "Reykjavik", "lon": -21.94, "lat": 64.15},
]


class WorldMapVisualizer:
    """世界地图 + 卫星轨迹可视化器"""
    
    def __init__(self):
        self.capitals = CAPITALS_DATA
        
    def _create_geographic_lines(self) -> List[go.Scattergeo]:
        """创建经纬网格和特殊地理线"""
        traces = []
        
        # 经线（10度间隔）
        lons_meridian = []
        lats_meridian = []
        for lon in range(-180, 181, 10):
            for lat in range(-90, 91, 1):
                lons_meridian.append(lon)
                lats_meridian.append(lat)
            lons_meridian.append(None)
            lats_meridian.append(None)
        if lons_meridian and lons_meridian[-1] is None:
            lons_meridian.pop()
            lats_meridian.pop()
        
        traces.append(go.Scattergeo(
            lon=lons_meridian, lat=lats_meridian,
            mode='lines', line=dict(color='rgba(150,150,150,0.3)', width=0.5, dash='dot'),
            name='Meridian (10°)', hoverinfo='skip', showlegend=True
        ))
        
        # 纬线（10度间隔，排除特殊纬度）
        special_lats = {0, 23.5, -23.5, 66.5, -66.5}
        std_lats = [lat for lat in range(-80, 81, 10) if lat not in special_lats]
        lons_parallel = []
        lats_parallel = []
        for lat in std_lats:
            for lon in range(-180, 181, 1):
                lons_parallel.append(lon)
                lats_parallel.append(lat)
            lons_parallel.append(None)
            lats_parallel.append(None)
        if lons_parallel and lons_parallel[-1] is None:
            lons_parallel.pop()
            lats_parallel.pop()
        
        traces.append(go.Scattergeo(
            lon=lons_parallel, lat=lats_parallel,
            mode='lines', line=dict(color='rgba(150,150,150,0.3)', width=0.5, dash='dot'),
            name='Parallel (10°)', hoverinfo='skip', showlegend=True
        ))
        
        # 赤道
        lons_equator = list(range(-180, 181, 1))
        lats_equator = [0] * len(lons_equator)
        traces.append(go.Scattergeo(
            lon=lons_equator, lat=lats_equator,
            mode='lines', line=dict(color='red', width=1),
            name='Equator', hoverinfo='skip', showlegend=True
        ))
        
        # 北回归线
        lons_tropic_n = list(range(-180, 181, 1))
        lats_tropic_n = [23.5] * len(lons_tropic_n)
        traces.append(go.Scattergeo(
            lon=lons_tropic_n, lat=lats_tropic_n,
            mode='lines', line=dict(color='blue', width=1, dash='dash'),
            name='Tropic of Cancer', hoverinfo='skip', showlegend=True
        ))
        
        # 南回归线
        lons_tropic_s = list(range(-180, 181, 1))
        lats_tropic_s = [-23.5] * len(lons_tropic_s)
        traces.append(go.Scattergeo(
            lon=lons_tropic_s, lat=lats_tropic_s,
            mode='lines', line=dict(color='blue', width=1, dash='dash'),
            name='Tropic of Capricorn', hoverinfo='skip', showlegend=True
        ))
        
        # 北极圈
        lons_arctic = list(range(-180, 181, 1))
        lats_arctic = [66.5] * len(lons_arctic)
        traces.append(go.Scattergeo(
            lon=lons_arctic, lat=lats_arctic,
            mode='lines', line=dict(color='blue', width=1, dash='dash'),
            name='Arctic Circle', hoverinfo='skip', showlegend=True
        ))
        
        # 南极圈
        lons_antarctic = list(range(-180, 181, 1))
        lats_antarctic = [-66.5] * len(lons_antarctic)
        traces.append(go.Scattergeo(
            lon=lons_antarctic, lat=lats_antarctic,
            mode='lines', line=dict(color='blue', width=1, dash='dash'),
            name='Antarctic Circle', hoverinfo='skip', showlegend=True
        ))
        
        return traces
    
    def _create_capitals_trace(self) -> go.Scattergeo:
        """创建首都标记"""
        lons_cap = [c["lon"] for c in self.capitals]
        lats_cap = [c["lat"] for c in self.capitals]
        texts_cap = [f"{c['capital']}<br>{c['country']}" for c in self.capitals]
        
        return go.Scattergeo(
            lon=lons_cap,
            lat=lats_cap,
            text=texts_cap,
            mode='markers',
            marker=dict(size=5, color='red', symbol='circle', 
                       line=dict(width=1, color='white')),
            name='Capitals',
            hoverinfo='text+lon+lat'
        )
    
    def create_base_map(self) -> go.Figure:
        """创建基础世界地图"""
        fig = go.Figure()
        
        # 地理投影设置
        fig.update_geos(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(240, 230, 210)",
            oceancolor="rgb(200, 230, 250)",
            showocean=True,
            showcountries=True,
            countrycolor="rgb(150, 150, 150)",
            countrywidth=0.5,
            showframe=False,
            coastlinewidth=0.5,
            coastlinecolor="rgb(100, 100, 100)",
        )
        
        # 添加地理线
        geo_lines = self._create_geographic_lines()
        for trace in geo_lines:
            fig.add_trace(trace)
        
        # 添加首都
        fig.add_trace(self._create_capitals_trace())
        
        # 布局设置
        fig.update_layout(
            title="Satellite Ground Track Visualization",
            geo=dict(showframe=False),
            hovermode='closest',
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.7)",
                bordercolor="gray",
                borderwidth=1
            )
        )
        
        return fig
    
    def add_satellite_track(self, 
                           fig: go.Figure,
                           lons: List[float],
                           lats: List[float],
                           timestamps: Optional[List[str]] = None,
                           track_name: str = "Satellite Track") -> go.Figure:
        """
        添加卫星轨迹到地图
        
        Args:
            fig: Plotly Figure对象
            lons: 经度列表
            lats: 纬度列表
            timestamps: 时间戳列表（可选）
            track_name: 轨迹名称
        """
        # 处理经度跳变（跨太平洋时）
        lons_clean = []
        lats_clean = []
        timestamps_clean = [] if timestamps else None
        
        last_lon = None
        for i, (lon, lat) in enumerate(zip(lons, lats)):
            if last_lon is not None and abs(lon - last_lon) > 180:
                # 插入None断开线条
                lons_clean.append(None)
                lats_clean.append(None)
                if timestamps_clean is not None:
                    timestamps_clean.append(None)
            
            lons_clean.append(lon)
            lats_clean.append(lat)
            if timestamps_clean is not None:
                timestamps_clean.append(timestamps[i] if i < len(timestamps) else "")
            
            last_lon = lon
        
        # 创建悬停文本
        if timestamps_clean:
            hover_text = [
                f"Time: {t}<br>Lon: {lon:.2f}°<br>Lat: {lat:.2f}°" 
                if t else "" 
                for t, lon, lat in zip(timestamps_clean, lons_clean, lats_clean)
            ]
        else:
            hover_text = [
                f"Lon: {lon:.2f}°<br>Lat: {lat:.2f}°" 
                if lon is not None else "" 
                for lon, lat in zip(lons_clean, lats_clean)
            ]
        
        # 添加轨迹
        fig.add_trace(go.Scattergeo(
            lon=lons_clean,
            lat=lats_clean,
            mode='lines+markers',
            marker=dict(size=3, color='magenta'),
            line=dict(width=1.5, color='magenta'),
            name=track_name,
            text=hover_text,
            hoverinfo='text'
        ))
        
        return fig
    
    def add_ground_station(self,
                          fig: go.Figure,
                          lon: float,
                          lat: float,
                          name: str = "Ground Station",
                          color: str = "green") -> go.Figure:
        """添加地面站标记"""
        fig.add_trace(go.Scattergeo(
            lon=[lon],
            lat=[lat],
            mode='markers+text',
            marker=dict(size=12, color=color, symbol='star',
                       line=dict(width=2, color='white')),
            text=[name],
            textposition="top center",
            name=name,
            hoverinfo='text+lon+lat'
        ))
        return fig


def test_world_map():
    """测试世界地图"""
    visualizer = WorldMapVisualizer()
    fig = visualizer.create_base_map()
    
    # 添加示例地面站
    fig = visualizer.add_ground_station(fig, 116.40, 39.90, "Beijing", "red")
    fig = visualizer.add_ground_station(fig, 117.28, 31.82, "Hefei", "green")
    
    # 添加示例轨迹（模拟）
    import numpy as np
    lons = np.linspace(-180, 180, 100)
    lats = 30 * np.sin(np.linspace(0, 4*np.pi, 100))
    timestamps = [f"2025-01-01 {h:02d}:00:00" for h in range(100)]
    
    fig = visualizer.add_satellite_track(fig, lons.tolist(), lats.tolist(), 
                                         timestamps, "Test Satellite")
    
    fig.show()


if __name__ == "__main__":
    test_world_map()
