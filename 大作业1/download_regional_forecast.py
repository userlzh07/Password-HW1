#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Download regional forecast data for Anhui + Jiangsu provinces
Uses Open-Meteo API to get grid data
"""

import requests
import csv
import os
from datetime import datetime, timedelta

# Regional bounding box (Anhui + Jiangsu + surrounding area)
# Lon: 115-120E, Lat: 29-35N
REGION = {
    'name': 'Anhui_Jiangsu',
    'min_lon': 115.0,
    'max_lon': 120.5,
    'min_lat': 29.0,
    'max_lat': 35.0,
    'resolution': 0.25  # degree
}

OUTPUT_DIR = 'F:/Meteoinfo/Output'

def download_regional_data():
    """
    Download regional forecast data from Open-Meteo
    Uses multiple point requests to simulate grid
    """
    print("Downloading regional forecast data...")
    print("Region: Anhui + Jiangsu (%s)" % REGION['name'])
    
    # Generate grid points
    lats = []
    lons = []
    lat = REGION['min_lat']
    while lat <= REGION['max_lat']:
        lon = REGION['min_lon']
        while lon <= REGION['max_lon']:
            lats.append(lat)
            lons.append(lon)
            lon += REGION['resolution']
        lat += REGION['resolution']
    
    print("Grid size: %d x %d = %d points" % (
        len(range(int(REGION['min_lat']*4), int(REGION['max_lat']*4)+1)),
        len(range(int(REGION['min_lon']*4), int(REGION['max_lon']*4)+1)),
        len(lats)
    ))
    
    # Download data for each time step
    url = "https://api.open-meteo.com/v1/forecast"
    
    all_data = []
    
    # Process in batches to avoid overwhelming the API
    batch_size = 10
    for i in range(0, len(lats), batch_size):
        batch_lats = lats[i:i+batch_size]
        batch_lons = lons[i:i+batch_size]
        
        for lat, lon in zip(batch_lats, batch_lons):
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["temperature_2m", "relative_humidity_2m", 
                          "wind_speed_10m", "wind_direction_10m", "pressure_msl"],
                "forecast_days": 3,  # 3 days for regional view
                "timezone": "Asia/Shanghai"
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                # Extract data for each time step
                for t_idx, time_str in enumerate(data['hourly']['time']):
                    all_data.append({
                        'lat': lat,
                        'lon': lon,
                        'time': time_str,
                        'temp': data['hourly']['temperature_2m'][t_idx],
                        'rh': data['hourly']['relative_humidity_2m'][t_idx],
                        'wind': data['hourly']['wind_speed_10m'][t_idx],
                        'wind_dir': data['hourly']['wind_direction_10m'][t_idx],
                        'pressure': data['hourly']['pressure_msl'][t_idx]
                    })
                    
            except Exception as e:
                print("Error at (%.2f, %.2f): %s" % (lat, lon, str(e)))
                continue
        
        if (i // batch_size) % 5 == 0:
            print("Progress: %d/%d points" % (min(i + batch_size, len(lats)), len(lats)))
    
    print("Downloaded %d records" % len(all_data))
    
    # Save as CSV
    save_regional_csv(all_data)
    
    # Save as MICAPS format (simplified)
    save_micaps_format(all_data)
    
    return all_data

def save_regional_csv(data):
    """Save data as CSV file"""
    output = '%s/regional_forecast.csv' % OUTPUT_DIR
    
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['lat', 'lon', 'time', 'temp', 'rh', 'wind', 'wind_dir', 'pressure'])
        
        for row in data:
            writer.writerow([
                row['lat'], row['lon'], row['time'],
                row['temp'], row['rh'], row['wind'],
                row['wind_dir'], row['pressure']
            ])
    
    print("Saved: %s" % output)

def save_micaps_format(data):
    """Save as MICAPS format (diamond 4 - grid data)"""
    # Group by time
    times = sorted(set([d['time'] for d in data]))
    
    for time_str in times[:6]:  # Save first 6 time steps only
        time_data = [d for d in data if d['time'] == time_str]
        
        dt = datetime.fromisoformat(time_str)
        
        # MICAPS diamond 4 format (grid data)
        output = '%s/regional_%s.txt' % (OUTPUT_DIR, time_str.replace(':', ''))
        
        with open(output, 'w') as f:
            # Header
            f.write('diamond 4 Regional_Forecast\n')
            f.write('%d %02d %02d %02d %02d\n' % (dt.year, dt.month, dt.day, dt.hour, 0))
            
            # Grid info (simplified - irregular grid)
            lats = sorted(set([d['lat'] for d in time_data]))
            lons = sorted(set([d['lon'] for d in time_data]))
            
            f.write('%d %d %.2f %.2f %.2f %.2f %.2f %.2f\n' % (
                len(lons), len(lats),
                min(lons), max(lons), min(lats), max(lats),
                REGION['resolution'], REGION['resolution']
            ))
            
            # Temperature data (interpolated to regular grid)
            for lat in lats:
                for lon in lons:
                    # Find nearest point
                    nearest = min(time_data, 
                                key=lambda x: abs(x['lat']-lat) + abs(x['lon']-lon))
                    f.write('%.1f ' % nearest['temp'])
                f.write('\n')
        
        print("Saved MICAPS: %s" % output)

def download_gfs_simple():
    """
    Alternative: Download GFS data from NOAA
    This requires xarray and cfgrib, but provides real grid data
    """
    print("\nAlternative: Using simple grid interpolation method...")
    
    # Create a synthetic grid based on real point forecasts
    # This is a demonstration - real implementation would use GFS/ECMWF data
    
    print("For full regional GRIB/NetCDF data, consider:")
    print("1. GFS: https://nomads.ncep.noaa.gov/")
    print("2. ECMWF: https://cds.climate.copernicus.eu/")
    print("3. CMA-GD: China Meteorological Administration data")

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Download regional data
    data = download_regional_data()
    
    print("\nRegional data download complete!")
    print("Next: Run plot_regional_forecast.py in MeteoInfoLab to visualize")
