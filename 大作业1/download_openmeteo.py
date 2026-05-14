import requests
import pandas as pd
from datetime import datetime

# 农场坐标（修改为您的）
LAT, LON = 40.2, 116.5

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": LAT,
    "longitude": LON,
    "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
    "forecast_days": 7,
    "timezone": "auto"
}

response = requests.get(url, params=params)
data = response.json()

# 保存为CSV
df = pd.DataFrame({
    'time': data['hourly']['time'],
    'temp_c': data['hourly']['temperature_2m'],
    'rh': data['hourly']['relative_humidity_2m'],
    'wind': data['hourly']['wind_speed_10m']
})

output = '/mnt/f/Meteoinfo/Output/openmeteo_forecast.csv'
df.to_csv(output, index=False)
print(f"下载完成: {output}")
print(df.head())
