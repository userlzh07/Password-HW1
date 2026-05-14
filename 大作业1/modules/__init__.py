"""
星地量子密钥分发链路仿真系统 - 核心模块包

模块说明:
    orbit_adapter    - 卫星轨道计算适配模块
    weather_adapter  - 气象数据获取与处理模块
    channel_model    - 信道传输模型
    qkd_core         - BB84协议核心实现
    eve_attacks      - Eve攻击模拟
    security_defense - 安全防御与决策
    visualization    - 数据可视化
"""

__version__ = "1.0.0"
__author__ = "QKD-Satellite-Sim"

# 可选：导出主要类，方便直接导入
# from .orbit_adapter import OrbitAdapter
# from .weather_adapter import WeatherAdapter
# from .channel_model import ChannelModel
# from .qkd_core import BB84SatelliteQKD
# from .eve_attacks import InterceptResendAttack, BeamSplittingAttack, PNAttack
# from .security_defense import PrivacyAmplification, DecoyStateProtocol, SecurityDecisionEngine
