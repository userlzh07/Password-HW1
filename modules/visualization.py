"""
可视化模块
使用Plotly和Dash创建交互式图表
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Union
from datetime import datetime
import sys
import os

# 导入Plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class QKDVisualizer:
    """
    QKD可视化器
    
    功能:
        1. 创建密钥率时序图
        2. 创建QBER时序图
        3. 创建卫星轨迹地图
        4. 创建安全状态分析图
    """
    
    def __init__(self):
        self.colors = {
            'primary': '#007BFF',
            'success': '#28A745',
            'warning': '#FFC107',
            'danger': '#DC3545',
            'info': '#17A2B8',
            'dark': '#343A40'
        }
    
    def create_key_rate_plot(self, 
                             timestamps,
                             secret_key_rates: List[float],
                             sifted_rates: Optional[List[float]] = None,
                             title: str = "密钥率时序图",
                             xaxis_title: str = "时间") -> Union[go.Figure, Dict]:
        """
        创建密钥率时序图
        
        Args:
            timestamps: 时间戳列表或分钟数值列表
            secret_key_rates: 安全密钥率列表 (bps)
            sifted_rates: 筛选密钥率列表 (可选)
            title: 图表标题
            xaxis_title: x轴标题
            
        Returns:
            go.Figure: Plotly图表对象
        """
        if not PLOTLY_AVAILABLE:
            return {}
        
        fig = go.Figure()
        
        # 安全密钥率
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=[r/1000 for r in secret_key_rates],  # 转换为kbps
            mode='lines+markers',
            name='安全密钥率',
            line=dict(color=self.colors['success'], width=2),
            marker=dict(size=6)
        ))
        
        # 筛选密钥率（如果有）
        if sifted_rates is not None:
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[r/1000 for r in sifted_rates],
                mode='lines',
                name='筛选密钥率',
                line=dict(color=self.colors['info'], width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='密钥率 (kbps)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_qber_plot(self,
                        timestamps,
                        qber_values: List[float],
                        threshold: float = 0.11,
                        title: str = "量子误码率时序图",
                        xaxis_title: str = "时间") -> Union[go.Figure, Dict]:
        """
        创建QBER时序图
        
        Args:
            timestamps: 时间戳列表或分钟数值列表
            qber_values: QBER值列表 (0-1)
            threshold: QBER阈值
            title: 图表标题
            xaxis_title: x轴标题
            
        Returns:
            go.Figure: Plotly图表对象
        """
        if not PLOTLY_AVAILABLE:
            return {}
        
        fig = go.Figure()
        
        # QBER曲线
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=[q*100 for q in qber_values],  # 转换为百分比
            mode='lines+markers',
            name='QBER',
            line=dict(color=self.colors['primary'], width=2),
            marker=dict(size=6)
        ))
        
        # 阈值线
        fig.add_trace(go.Scatter(
            x=[timestamps[0], timestamps[-1]],
            y=[threshold*100, threshold*100],
            mode='lines',
            name='安全阈值',
            line=dict(color=self.colors['danger'], width=2, dash='dash')
        ))
        
        y_max = max(20, max(qber_values)*100*1.1) if len(qber_values) > 0 else 20
        
        fig.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='QBER (%)',
            yaxis=dict(range=[0, y_max]),
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_satellite_map(self,
                            sat_lons: List[float],
                            sat_lats: List[float],
                            ground_station: Optional[Dict] = None,
                            timestamps: Optional[List[datetime]] = None,
                            visibility: Optional[List[bool]] = None,
                            title: str = "卫星轨迹") -> Union[go.Figure, Dict]:
        """
        创建卫星轨迹地图
        
        Args:
            sat_lons: 卫星经度列表
            sat_lats: 卫星纬度列表
            ground_station: 地面站位置 {'lat': x, 'lon': y}
            timestamps: 时间戳列表（用于悬停提示）
            visibility: 可见性列表
            title: 图表标题
            
        Returns:
            go.Figure: Plotly图表对象
        """
        if not PLOTLY_AVAILABLE:
            return {}
        
        fig = go.Figure()
        
        # 轨迹线
        if visibility is not None:
            # 根据可见性分段着色
            visible_lons = [lon if vis else None for lon, vis in zip(sat_lons, visibility)]
            visible_lats = [lat if vis else None for lat, vis in zip(sat_lats, visibility)]
            
            fig.add_trace(go.Scattergeo(
                lon=visible_lons,
                lat=visible_lats,
                mode='lines',
                name='可见轨道',
                line=dict(color=self.colors['success'], width=3)
            ))
        else:
            fig.add_trace(go.Scattergeo(
                lon=sat_lons,
                lat=sat_lats,
                mode='lines',
                name='轨道',
                line=dict(color=self.colors['primary'], width=2)
            ))
        
        # 当前位置标记
        if sat_lons and sat_lats:
            fig.add_trace(go.Scattergeo(
                lon=[sat_lons[-1]],
                lat=[sat_lats[-1]],
                mode='markers',
                name='卫星位置',
                marker=dict(size=12, color=self.colors['danger'], symbol='circle')
            ))
        
        # 地面站
        if ground_station:
            fig.add_trace(go.Scattergeo(
                lon=[ground_station['lon']],
                lat=[ground_station['lat']],
                mode='markers',
                name='地面站',
                marker=dict(size=12, color=self.colors['success'], symbol='diamond')
            ))
        
        fig.update_layout(
            title=title,
            geo=dict(
                projection_type='natural earth',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                showocean=True,
                oceancolor='rgb(204, 229, 255)',
                showcountries=True,
                countrycolor='rgb(150, 150, 150)',
                showcoastlines=True,
                coastlinecolor='rgb(100, 100, 100)'
            ),
            hovermode='closest'
        )
        
        return fig
    
    def create_security_analysis_plot(self,
                                     qber: float,
                                     eve_info: float,
                                     secure_key_ratio: float,
                                     title: str = "安全状态分析") -> Union[go.Figure, Dict]:
        """
        创建安全状态分析图
        
        Args:
            qber: 量子误码率
            eve_info: Eve信息比例
            secure_key_ratio: 安全密钥比例
            title: 图表标题
            
        Returns:
            go.Figure: Plotly图表对象
        """
        if not PLOTLY_AVAILABLE:
            return {}
        
        # 使用条形图显示安全指标
        categories = ['QBER', 'Eve信息', '密钥损失', '安全密钥']
        values = [
            qber * 100,
            eve_info * 100,
            (1 - secure_key_ratio) * 100,
            secure_key_ratio * 100
        ]
        colors = [
            self.colors['warning'] if qber < 0.11 else self.colors['danger'],
            self.colors['danger'] if eve_info > 0.2 else self.colors['warning'],
            self.colors['info'],
            self.colors['success'] if secure_key_ratio > 0.5 else self.colors['warning']
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f'{v:.1f}%' for v in values],
            textposition='outside'
        ))
        
        fig.update_layout(
            title=title,
            yaxis_title='百分比 (%)',
            yaxis=dict(range=[0, 100]),
            template='plotly_white'
        )
        
        return fig
    
    def create_dashboard(self,
                        timeline_data: List[Dict],
                        title: str = "QKD链路监控面板") -> Union[go.Figure, Dict]:
        """
        创建综合监控面板
        
        Args:
            timeline_data: 时间序列数据列表
            title: 面板标题
            
        Returns:
            go.Figure: 包含多个子图的面板对象
        """
        if not PLOTLY_AVAILABLE:
            return {}
        
        # 提取数据
        timestamps = [d['timestamp'] for d in timeline_data]
        qber_values = [d.get('qber', 0) for d in timeline_data]
        secret_rates = [d.get('secret_key_rate', 0) for d in timeline_data]
        sifted_rates = [d.get('sifted_rate', 0) for d in timeline_data]
        
        # 创建子图
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('密钥率', '量子误码率', '卫星高度', '安全状态'),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}]
            ]
        )
        
        # 子图1: 密钥率
        fig.add_trace(
            {'type': 'scatter', 'x': timestamps, 'y': [r/1000 for r in secret_rates],
             'name': '安全密钥率', 'line': {'color': 'green'}},
            row=1, col=1
        )
        
        # 子图2: QBER
        fig.add_trace(
            {'type': 'scatter', 'x': timestamps, 'y': [q*100 for q in qber_values],
             'name': 'QBER', 'line': {'color': 'blue'}},
            row=1, col=2
        )
        
        # 子图3: 高度
        elevations = [d.get('elevation_deg', 0) for d in timeline_data]
        fig.add_trace(
            {'type': 'scatter', 'x': timestamps, 'y': elevations,
             'name': '仰角', 'line': {'color': 'purple'}},
            row=2, col=1
        )
        
        # 子图4: 安全状态 (简化为文本)
        fig.add_annotation(
            text="安全状态: 正常" if np.mean(qber_values) < 0.11 else "安全状态: 警告",
            xref="x4 domain", yref="y4 domain",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="green" if np.mean(qber_values) < 0.11 else "red")
        )
        
        fig.update_layout(
            title_text=title,
            height=800,
            showlegend=False
        )
        
        return fig


def create_sample_data() -> List[Dict]:
    """生成示例时间序列数据"""
    from datetime import timedelta
    
    base_time = datetime.now()
    data = []
    
    for i in range(60):
        time = base_time + timedelta(minutes=i)
        elevation = 10 + 80 * np.sin(np.pi * i / 60)  # 模拟过境
        
        # 随仰角变化的参数
        transmission = 10 ** (-1 + 0.01 * elevation)  # 透射率
        qber = 0.02 + 0.1 * np.exp(-elevation / 30)  # QBER
        
        data.append({
            'timestamp': time,
            'elevation_deg': elevation,
            'qber': qber,
            'sifted_rate': 10000 * transmission,
            'secret_key_rate': 10000 * transmission * max(0, 1 - 2 * qber)
        })
    
    return data


def test_visualization():
    """测试可视化模块"""
    print("=" * 60)
    print("测试可视化模块")
    print("=" * 60)
    
    try:
        import plotly.graph_objects as go
        PLOTLY_AVAILABLE = True
    except ImportError:
        PLOTLY_AVAILABLE = False
        print("Plotly未安装，跳过可视化测试")
        return
    
    # 生成示例数据
    data = create_sample_data()
    
    visualizer = QKDVisualizer()
    
    # 测试各种图表
    print("\n生成示例图表...")
    
    # 密钥率图
    fig1 = visualizer.create_key_rate_plot(
        [d['timestamp'] for d in data],
        [d['secret_key_rate'] for d in data],
        [d['sifted_rate'] for d in data]
    )
    print("  ✓ 密钥率图")
    
    # QBER图
    fig2 = visualizer.create_qber_plot(
        [d['timestamp'] for d in data],
        [d['qber'] for d in data]
    )
    print("  ✓ QBER图")
    
    # 卫星地图
    sat_lons = np.linspace(116, 122, len(data))
    sat_lats = 30 + 10 * np.sin(np.linspace(0, np.pi, len(data)))
    fig3 = visualizer.create_satellite_map(
        sat_lons.tolist(),
        sat_lats.tolist(),
        ground_station={'lat': 31.82, 'lon': 117.28}
    )
    print("  ✓ 卫星地图")
    
    # 安全分析图
    fig4 = visualizer.create_security_analysis_plot(
        qber=0.05,
        eve_info=0.1,
        secure_key_ratio=0.6
    )
    print("  ✓ 安全分析图")
    
    print("\n所有图表配置已生成!")
    print("可以使用 plotly.graph_objects.Figure(fig_dict).show() 显示")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_visualization()
