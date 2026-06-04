#!/usr/bin/env python3
"""
下载中国科学技术大学（USTC）所在地（合肥）的天气预报数据
坐标：31.8226°N, 117.2814°E
"""
import requests
import pandas as pd
from datetime import datetime
import os

# USTC坐标配置
USTC_LAT = 31.8226  # 纬度
USTC_LON = 117.2814  # 经度
USTC_ELEV = 50  # 海拔(米)，合肥市区约50米

# 输出路径
OUTPUT_DIR = 'F:/Meteoinfo/Output'

def download_forecast():
    """从Open-Meteo下载7天预报数据"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": USTC_LAT,
        "longitude": USTC_LON,
        "hourly": [
            "temperature_2m",           # 2米温度
            "relative_humidity_2m",     # 相对湿度
            "wind_speed_10m",           # 10米风速
            "wind_direction_10m",       # 10米风向
            "precipitation",            # 降水量
            "pressure_msl",             # 海平面气压
            "cloud_cover",              # 云量
            "dew_point_2m"              # 露点温度
        ],
        "forecast_days": 7,
        "timezone": "Asia/Shanghai"
    }
    
    print(f"正在下载USTC（合肥）天气预报数据...")
    print(f"坐标: {USTC_LAT}°N, {USTC_LON}°E")
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 整理数据
    df = pd.DataFrame({
        'time': data['hourly']['time'],
        'temp_c': data['hourly']['temperature_2m'],
        'rh': data['hourly']['relative_humidity_2m'],
        'wind': data['hourly']['wind_speed_10m'],
        'wind_dir': data['hourly']['wind_direction_10m'],
        'precip': data['hourly']['precipitation'],
        'pressure': data['hourly']['pressure_msl'],
        'cloud': data['hourly']['cloud_cover'],
        'dewpoint': data['hourly']['dew_point_2m']
    })
    
    # 降尺度修正（针对USTC微气候）
    # 1. 海拔修正：每100米降温0.6℃
    elevation_corr = USTC_ELEV * 0.006
    df['temp_farm'] = df['temp_c'] - elevation_corr
    
    # 2. 城市热岛效应修正（夜间温度略高）
    df['hour'] = pd.to_datetime(df['time']).dt.hour
    night_mask = (df['hour'] >= 20) | (df['hour'] <= 6)
    df.loc[night_mask, 'temp_farm'] += 0.5
    
    # 3. 风速修正（城市建筑阻挡，减速15%）
    df['wind_farm'] = df['wind'] * 0.85
    
    # 保存原始数据
    output = f'{OUTPUT_DIR}/ustc_forecast_raw.csv'
    df.to_csv(output, index=False, encoding='utf-8-sig')
    print(f"\n原始数据保存: {output}")
    
    # 保存降尺度后数据
    output_ds = f'{OUTPUT_DIR}/ustc_forecast_downscaled.csv'
    df[['time', 'temp_farm', 'wind_farm', 'rh', 'precip', 'pressure', 'cloud']].to_csv(
        output_ds, index=False, encoding='utf-8-sig'
    )
    print(f"降尺度数据保存: {output_ds}")
    
    # 保存为MICAPS格式（MeteoInfo原生支持）
    save_micaps_format(df)
    
    print("\n数据统计:")
    print(f"  温度范围: {df['temp_farm'].min():.1f} ~ {df['temp_farm'].max():.1f}℃")
    print(f"  平均风速: {df['wind_farm'].mean():.1f} m/s")
    print(f"  总降水量: {df['precip'].sum():.1f} mm")
    
    return df

def save_micaps_format(df):
    """保存为MICAPS第1类格式（站点数据）"""
    today = datetime.now()
    
    # 生成站点信息文件
    output = f'{OUTPUT_DIR}/ustc_forecast_micaps.txt'
    
    with open(output, 'w', encoding='utf-8') as f:
        # 文件头：diamond 1 站点数据
        f.write('diamond 1 USTC_Forecast\n')
        # 年月日 时次 时效 站点数
        f.write(f'{today.year} {today.month:02d} {today.day:02d} 00 168 1 0 0 0\n')
        
        # 站点数据：日期 时间 温度 风速 湿度
        for _, row in df.iterrows():
            dt = pd.to_datetime(row['time'])
            date_str = dt.strftime('%Y%m%d')
            hour_str = dt.strftime('%H')
            f.write(f"{date_str} {hour_str} "
                   f"{row['temp_farm']:.1f} "
                   f"{row['wind_farm']:.1f} "
                   f"{row['rh']:.0f}\n")
    
    print(f"MICAPS格式保存: {output}")

def download_historical():
    """下载过去7天的实况数据（用于对比）"""
    url = "https://api.open-meteo.com/v1/archive"
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
    
    params = {
        "latitude": USTC_LAT,
        "longitude": USTC_LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "timezone": "Asia/Shanghai"
    }
    
    print(f"\n下载历史实况数据 ({start_date} 至 {end_date})...")
    
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame({
        'time': data['hourly']['time'],
        'temp_c': data['hourly']['temperature_2m'],
        'rh': data['hourly']['relative_humidity_2m'],
        'wind': data['hourly']['wind_speed_10m']
    })
    
    # 同样的降尺度处理
    df['temp_farm'] = df['temp_c'] - (USTC_ELEV * 0.006)
    df['wind_farm'] = df['wind'] * 0.85
    
    output = f'{OUTPUT_DIR}/ustc_historical.csv'
    df.to_csv(output, index=False, encoding='utf-8-sig')
    print(f"历史数据保存: {output}")
    
    return df

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 下载预报数据
    forecast_df = download_forecast()
    
    # 可选：下载历史数据
    # historical_df = download_historical()
    
    print("\n[完成] USTC天气数据下载完成！")
