# 星地量子密钥分发链路仿真与安全分析系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Version-1.0.0-orange.svg" alt="Version: 1.0.0">
</p>

## 📝 项目简介

本项目是一个基于真实卫星轨道和实时气象数据的**星地量子密钥分发(QKD)链路仿真平台**，集成完整的BB84协议模拟、Eve攻击仿真和安全防御机制，为星地量子通信链路规划提供工程决策支持。

### ✨ 核心特性

- **🛰️ 真实数据驱动**
  - 基于TLE数据的卫星轨道计算
  - Open-Meteo实时气象数据集成
  - 支持中国空间站、墨子号等多颗卫星

- **🔐 完整攻防体系**
  - 三类典型攻击：截获-重发、光束分离、光子数分离(PNS)
  - 防御机制：诱骗态协议、隐私放大
  - 安全决策引擎

- **📊 可视化分析**
  - 卫星轨迹地图
  - 实时密钥率/QBER监控
  - 安全状态分析

- **🌐 交互式界面**
  - Gradio Web界面
  - 参数实时调整
  - 结果导出

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖库（见requirements.txt）

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd qkd-satellite-sim

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
# 启动主应用
python app.py

# 运行测试
python tests/test_qkd.py
python tests/test_attacks.py
python tests/test_defense.py
```

## 📁 项目结构

```
qkd-satellite-sim/
├── README.md                 # 项目说明
├── requirements.txt          # 依赖列表
├── config.py                 # 全局配置
├── app.py                    # Gradio主应用
├── modules/                  # 核心模块
│   ├── __init__.py
│   ├── orbit_adapter.py      # 卫星轨道计算
│   ├── weather_adapter.py    # 气象数据获取
│   ├── channel_model.py      # 信道传输模型
│   ├── qkd_core.py           # BB84协议核心
│   ├── eve_attacks.py        # Eve攻击模拟
│   ├── security_defense.py   # 安全防御机制
│   └── visualization.py      # 数据可视化
├── tests/                    # 测试模块
│   ├── test_qkd.py
│   ├── test_attacks.py
│   └── test_defense.py
└── data/                     # 数据文件
    └── sample_tle.txt        # 示例TLE数据
```

## 🔧 模块说明

### 1. 轨道动力学模块 (`orbit_adapter.py`)

基于Skyfield库实现卫星轨道计算：

```python
from modules.orbit_adapter import OrbitAdapter

# 初始化卫星
adapter = OrbitAdapter(tle_line1, tle_line2)

# 获取卫星位置
pos = adapter.get_satellite_position(timestamp)

# 计算链路参数
link = adapter.calculate_slant_range(pos, ground_station)
```

### 2. 气象数据模块 (`weather_adapter.py`)

集成Open-Meteo API获取实时天气：

```python
from modules.weather_adapter import WeatherAdapter

adapter = WeatherAdapter()
weather = adapter.get_weather_data(lat, lon, forecast_days=7)
```

### 3. QKD协议核心 (`qkd_core.py`)

BB84协议完整实现：

```python
from modules.qkd_core import BB84SatelliteQKD

# 创建QKD实例
qkd = BB84SatelliteQKD(channel_transmission=0.1)

# 运行仿真
result = qkd.simulate_exchange(n_pulses=10000, eve_attack=attack)
```

### 4. Eve攻击模块 (`eve_attacks.py`)

三类攻击实现：

```python
from modules.eve_attacks import (
    InterceptResendAttack,
    BeamSplittingAttack,
    PhotonNumberSplittingAttack
)

# 截获-重发攻击
attack = InterceptResendAttack(attack_strength=0.5)

# 光束分离攻击
attack = BeamSplittingAttack(split_ratio=0.3)

# PNS攻击
attack = PhotonNumberSplittingAttack()
```

### 5. 安全防御模块 (`security_defense.py`)

```python
from modules.security_defense import (
    PrivacyAmplification,
    DecoyStateProtocol,
    SecurityDecisionEngine
)

# 隐私放大
pa = PrivacyAmplification()
secure_length = pa.calculate_secure_length(n_sifted, qber, eve_info)

# 诱骗态检测
decoy = DecoyStateProtocol()
result = decoy.detect_pns_attack(signal_yield, decoy_yield, vacuum_yield)
```

## 📊 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 仿真计算延迟 | <500ms | 单次QKD模拟（10000脉冲） |
| 界面响应延迟 | <100ms | 时间轴拖动到图表更新 |
| 支持时间点数 | >1000 | 单次过境动画流畅度 |

## 🛡️ 安全分析

### 攻击检测能力

| 攻击类型 | 检测方法 | 防御策略 |
|----------|----------|----------|
| 截获-重发 | QBER>11%时报警 | 隐私放大 |
| 光束分离 | Eve信息估算 | 隐私放大 |
| PNS攻击 | 诱骗态产额分析 | 诱骗态协议 |

### 安全密钥率公式

```
r = 1 - 2×H2(QBER)
R = r × R_sifted
H2(x) = -x·log₂(x) - (1-x)·log₂(1-x)
```

## 📚 参考文献

1. Gisin, N., et al. (2002). Quantum cryptography. *Reviews of Modern Physics*, 74(1), 145.
2. Wang, X. B. (2005). Beating the photon-number-splitting attack in practical quantum cryptography. *Physical Review Letters*, 94(23), 230503.
3. Lo, H. K., et al. (2005). Decoy state quantum key distribution. *Physical Review Letters*, 94(23), 230504.
4. Liao, S. K., et al. (2017). Satellite-to-ground quantum key distribution. *Nature*, 549(7670), 43-47.
5. Yin, J., et al. (2020). Entanglement-based secure quantum cryptography over 1,120 kilometres. *Nature*, 582(7813), 501-505.

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- 项目地址: <repository-url>
- 邮箱: <your-email>

---

<p align="center">
  Made with ❤️ for Quantum Communication Research
</p>
