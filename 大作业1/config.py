"""
配置文件 - 星地量子密钥分发链路仿真系统
"""

# ==================== 地面站配置 ====================
GROUND_STATIONS = {
    # ========== 中国观测站 ==========
    "USTC_合肥": {
        "lat": 31.8226,
        "lon": 117.2814,
        "elevation": 50,
        "description": "中国科学技术大学"
    },
    "北京": {
        "lat": 39.9042,
        "lon": 116.4074,
        "elevation": 43,
        "description": "北京量子信息科学研究院"
    },
    "上海": {
        "lat": 31.2304,
        "lon": 121.4737,
        "elevation": 10,
        "description": "上海微系统所"
    },
    "乌鲁木齐": {
        "lat": 43.8256,
        "lon": 87.6168,
        "elevation": 800,
        "description": "新疆天文台"
    },
    "丽江": {
        "lat": 26.8721,
        "lon": 100.2299,
        "elevation": 2400,
        "description": "丽江量子通信地面站"
    },
    "深圳": {
        "lat": 22.5431,
        "lon": 114.0579,
        "elevation": 10,
        "description": "深圳量子科学与工程研究院"
    },
    "西安": {
        "lat": 34.3416,
        "lon": 108.9398,
        "elevation": 400,
        "description": "西安光学精密机械研究所"
    },
    
    # ========== 国际观测站 ==========
    "东京_日本": {
        "lat": 35.6762,
        "lon": 139.6503,
        "elevation": 40,
        "description": "日本国立信息学研究所 (NICT)"
    },
    "华盛顿_美国": {
        "lat": 38.9072,
        "lon": -77.0369,
        "elevation": 10,
        "description": "NASA戈达德航天中心附近"
    },
    "维也纳_奥地利": {
        "lat": 48.2082,
        "lon": 16.3738,
        "elevation": 170,
        "description": "奥地利科学院量子光学研究所"
    },
    "日内瓦_瑞士": {
        "lat": 46.2044,
        "lon": 6.1432,
        "elevation": 375,
        "description": "CERN欧洲核子研究中心"
    },
    "莫斯科_俄罗斯": {
        "lat": 55.7558,
        "lon": 37.6173,
        "elevation": 150,
        "description": "俄罗斯科学院量子中心"
    },
    "伦敦_英国": {
        "lat": 51.5074,
        "lon": -0.1278,
        "elevation": 35,
        "description": "英国国家物理实验室 (NPL)"
    },
    "巴黎_法国": {
        "lat": 48.8566,
        "lon": 2.3522,
        "elevation": 35,
        "description": "巴黎天文台"
    },
    "柏林_德国": {
        "lat": 52.5200,
        "lon": 13.4050,
        "elevation": 35,
        "description": "德国联邦物理技术研究院 (PTB)"
    },
    "新加坡": {
        "lat": 1.3521,
        "lon": 103.8198,
        "elevation": 15,
        "description": "新加坡国立大学量子技术中心"
    },
    "悉尼_澳大利亚": {
        "lat": -33.8688,
        "lon": 151.2093,
        "elevation": 30,
        "description": "澳大利亚国立大学"
    },
    "多伦多_加拿大": {
        "lat": 43.6532,
        "lon": -79.3832,
        "elevation": 80,
        "description": "加拿大滑铁卢大学量子计算研究所"
    },
    "新德里_印度": {
        "lat": 28.6139,
        "lon": 77.2090,
        "elevation": 220,
        "description": "印度拉曼研究所"
    },
    "迪拜_阿联酋": {
        "lat": 25.2048,
        "lon": 55.2708,
        "elevation": 5,
        "description": "迪拜未来基金会量子实验室"
    },
    "耶路撒冷_以色列": {
        "lat": 31.7683,
        "lon": 35.2137,
        "elevation": 750,
        "description": "以色列魏茨曼研究所"
    },
    "首尔_韩国": {
        "lat": 37.5665,
        "lon": 126.9780,
        "elevation": 40,
        "description": "韩国标准科学研究院 (KRISS)"
    },
    "曼谷_泰国": {
        "lat": 13.7563,
        "lon": 100.5018,
        "elevation": 10,
        "description": "泰国国家电子和计算机技术中心"
    },
    "开罗_埃及": {
        "lat": 30.0444,
        "lon": 31.2357,
        "elevation": 25,
        "description": "埃及国家研究中心"
    },
    "里约热内卢_巴西": {
        "lat": -22.9068,
        "lon": -43.1729,
        "elevation": 10,
        "description": "巴西国家空间研究所"
    },
    "开普敦_南非": {
        "lat": -33.9249,
        "lon": 18.4241,
        "elevation": 40,
        "description": "南非国家激光中心"
    }
}

# ==================== 卫星TLE数据配置 ====================
# TLE数据可以从 https://celestrak.org/ 获取最新数据
SAMPLE_TLE = {
    "演示-ISS类型过顶": {
        "line1": "1 99991U 24001A   26066.50000000  .00010000  00000-0  12345-4 0  9999",
        "line2": "2 99991  51.6000 117.2800 0001000  0.0000  90.0000 15.50000000 12345",
        "description": "演示用低轨卫星(400km) - 模拟ISS/空间站过境，全程约90分钟，可自选天气"
    },
    "演示-高轨过顶": {
        "line1": "1 99992U 24002A   26066.50000000  .00010000  00000-0  12345-4 0  9999",
        "line2": "2 99992  51.6000 116.4000 0001000  0.0000  90.0000 15.50000000 12345",
        "description": "演示用中轨卫星 - 模拟较长过境时间"
    },
    "国际空间站(ISS)": {
        "line1": "1 25544U 98067A   24086.51782565  .00022085  00000-0  39445-3 0  9992",
        "line2": "2 25544  51.6416  71.4136 0004731  25.0343  96.0716 15.49227164436112",
        "description": "国际空间站ISS - 轨道高度约420km，倾角51.6° (真实TLE数据)"
    },
    "中国空间站(CSS)": {
        "line1": "1 48274U 21035A   26085.92437350  .00022168  00000+0  25435-3 0  9990",
        "line2": "2 48274  41.4668 103.2237 0004238  32.2282 327.8815 15.61531781280305",
        "description": "中国空间站 (CSS) - 真实TLE数据 (2026-03-26)，倾角41.5°"
    },
    "墨子号(Micius)": {
        "line1": "1 41743U 16051A   26086.51782565  .00022085  00000-0  39445-3 0  9992",
        "line2": "2 41743  51.6416  71.4136 0004731  25.0343  96.0716 15.49227164436112",
        "description": "世界首颗量子科学实验卫星 (演示用轨道，基于ISS TLE，实际过境需查真实星历)"
    }
}

# ==================== Open-Meteo API配置 ====================
OPENMETEO_CONFIG = {
    "forecast_url": "https://api.open-meteo.com/v1/forecast",
    "archive_url": "https://api.open-meteo.com/v1/archive",
    "default_params": {
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation",
            "pressure_msl",
            "cloud_cover",
            "cloud_cover_low",     # 低云量（影响更大）
            "cloud_cover_mid",     # 中云量
            "cloud_cover_high",    # 高云量
            "visibility",          # 能见度（直接影响QKD！）
            "weather_code"
        ],
        "timezone": "Asia/Shanghai"
    }
}

# ==================== 天气衰减系数映射表 ====================
# 单位: dB/km
WEATHER_ATTENUATION = {
    "clear": {
        "visibility_km": 20,
        "attenuation_db_per_km": 0.2,
        "weather_codes": [0, 1, 2, 3]  # 晴、多云
    },
    "mist": {
        "visibility_km": 10,
        "attenuation_db_per_km": 2.0,
        "weather_codes": [45, 48]  # 雾、沉积雾
    },
    "fog": {
        "visibility_km": 2,
        "attenuation_db_per_km": 10.0,
        "weather_codes": [45, 48]
    },
    "light_rain": {
        "visibility_km": 5,
        "attenuation_db_per_km": 3.0,
        "weather_codes": [51, 53, 55, 56, 57]  # 小雨
    },
    "rain": {
        "visibility_km": 3,
        "attenuation_db_per_km": 5.0,
        "weather_codes": [61, 63, 65, 66, 67]  # 中雨、大雨
    },
    "heavy_rain": {
        "visibility_km": 1,
        "attenuation_db_per_km": 10.0,
        "weather_codes": [65, 67, 80, 81, 82]  # 暴雨
    },
    "snow": {
        "visibility_km": 1,
        "attenuation_db_per_km": 8.0,
        "weather_codes": [71, 73, 75, 77, 85, 86]  # 雪
    }
}

# ==================== QKD系统参数 ====================
QKD_PARAMETERS = {
    # 光源参数
    "pulse_rate": 1e8,           # 脉冲率 (Hz) - 100MHz，更适合卫星链路
    "wavelength_nm": 850,        # 波长 (nm)
    "mean_photon_number": 0.8,   # 平均光子数 (弱脉冲，稍强一些)
    
    # 光学效率
    "alice_efficiency": 0.9,     # Alice端效率
    "bob_efficiency": 0.7,       # Bob端效率
    "detector_efficiency": 0.4,  # 探测器效率 (提高)
    "detector_dark_count": 50,   # 暗计数 (Hz，降低)
    
    # 安全阈值
    "max_qber": 0.11,            # 最大可接受误码率
    "min_photon_rate": 100,      # 最小光子率 (Hz)
    "max_eve_info": 0.3,         # 最大Eve信息比例
    "security_parameter": 1e-9,  # 安全参数 ε
}

# ==================== 攻击类型配置 ====================
ATTACK_TYPES = {
    "none": {
        "name": "无攻击",
        "description": "正常通信，无窃听者"
    },
    "intercept_resend": {
        "name": "截获-重发攻击",
        "description": "Eve截获并重发光子，引入25%误码",
        "introduced_qber": 0.25,
        "eve_info_ratio": 0.5
    },
    "beam_splitting": {
        "name": "光束分离攻击",
        "description": "Eve分离部分光束，不引入误码但泄露信息",
        "introduced_qber": 0.0,
        "eve_info_ratio": 0.3
    },
    "pns": {
        "name": "光子数分离攻击",
        "description": "针对弱脉冲光源，多光子态被Eve获取",
        "introduced_qber": 0.0,
        "eve_info_ratio": 0.4
    }
}

# ==================== 仿真时间配置 ====================
SIMULATION_CONFIG = {
    "default_duration_minutes": 90,  # 默认仿真时长（卫星过境）
    "time_step_seconds": 60,         # 时间步长
    "min_elevation_deg": 10,         # 最小通信仰角
}
