"""
卫星星下点轨迹交互地图（增强版）- 增加卫星选择下拉菜单
依赖安装：
    pip install dash plotly geopandas pandas skyfield
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import numpy as np
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone

# ==================== 1. 读取并简化中国省、市、县边界 ====================
# 请将下面的文件路径替换为你的实际路径
province_gpkg = r"C:\Users\user\Downloads\boundary\province.gpkg"
city_gpkg     = r"C:\Users\user\Downloads\boundary\city.gpkg"
county_gpkg   = r"C:\Users\user\Downloads\boundary\county.gpkg"

def load_and_simplify(gpkg_path, tolerance=0.01):
    """读取 GPKG，确保坐标系为 WGS84，简化几何，返回边界坐标 (lons, lats)"""
    try:
        gdf = gpd.read_file(gpkg_path)
    except:
        print(f"警告：无法读取 {gpkg_path}，将使用空数据")
        return [], []
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    gdf['geometry'] = gdf.geometry.simplify(tolerance=tolerance, preserve_topology=True)

    lons = []
    lats = []
    for geom in gdf.geometry:
        if geom.geom_type == 'MultiPolygon':
            polys = geom.geoms
        else:
            polys = [geom]
        for poly in polys:
            ext = poly.exterior
            lons.extend(ext.coords.xy[0].tolist() + [None])
            lats.extend(ext.coords.xy[1].tolist() + [None])
            for int_ring in poly.interiors:
                lons.extend(int_ring.coords.xy[0].tolist() + [None])
                lats.extend(int_ring.coords.xy[1].tolist() + [None])
    return lons, lats

province_lons, province_lats = load_and_simplify(province_gpkg, tolerance=0.01)
city_lons,     city_lats     = load_and_simplify(city_gpkg,     tolerance=0.01)
county_lons,   county_lats   = load_and_simplify(county_gpkg,   tolerance=0.01)

# ==================== 2. 首都数据列表（完整列表保持不变）====================
capitals_data = [
    {"国家": "中国", "首都": "北京", "经度": 116.40, "纬度": 39.90},
    {"国家": "日本", "首都": "东京", "经度": 139.69, "纬度": 35.69},
    {"国家": "印度", "首都": "新德里", "经度": 77.20, "纬度": 28.61},
    {"国家": "俄罗斯", "首都": "莫斯科", "经度": 37.62, "纬度": 55.76},
    {"国家": "埃及", "首都": "开罗", "经度": 31.24, "纬度": 30.04},
    {"国家": "英国", "首都": "伦敦", "经度": -0.13, "纬度": 51.51},
    {"国家": "法国", "首都": "巴黎", "经度": 2.35, "纬度": 48.86},
    {"国家": "美国", "首都": "华盛顿", "经度": -77.04, "纬度": 38.91},
    {"国家": "巴西", "首都": "巴西利亚", "经度": -47.88, "纬度": -15.79},
    {"国家": "澳大利亚", "首都": "堪培拉", "经度": 149.13, "纬度": -35.28},
    {"国家": "加拿大", "首都": "渥太华", "经度": -75.70, "纬度": 45.42},
    {"国家": "墨西哥", "首都": "墨西哥城", "经度": -99.13, "纬度": 19.43},
    {"国家": "阿根廷", "首都": "布宜诺斯艾利斯", "经度": -58.38, "纬度": -34.60},
    {"国家": "德国", "首都": "柏林", "经度": 13.40, "纬度": 52.52},
    {"国家": "意大利", "首都": "罗马", "经度": 12.50, "纬度": 41.90},
    {"国家": "西班牙", "首都": "马德里", "经度": -3.70, "纬度": 40.42},
    {"国家": "葡萄牙", "首都": "里斯本", "经度": -9.14, "纬度": 38.72},
    {"国家": "荷兰", "首都": "阿姆斯特丹", "经度": 4.90, "纬度": 52.37},
    {"国家": "比利时", "首都": "布鲁塞尔", "经度": 4.35, "纬度": 50.85},
    {"国家": "瑞士", "首都": "伯尔尼", "经度": 7.45, "纬度": 46.95},
    {"国家": "瑞典", "首都": "斯德哥尔摩", "经度": 18.07, "纬度": 59.33},
    {"国家": "挪威", "首都": "奥斯陆", "经度": 10.75, "纬度": 59.91},
    {"国家": "丹麦", "首都": "哥本哈根", "经度": 12.57, "纬度": 55.68},
    {"国家": "芬兰", "首都": "赫尔辛基", "经度": 24.94, "纬度": 60.17},
    {"国家": "波兰", "首都": "华沙", "经度": 21.01, "纬度": 52.23},
    {"国家": "捷克", "首都": "布拉格", "经度": 14.42, "纬度": 50.09},
    {"国家": "奥地利", "首都": "维也纳", "经度": 16.37, "纬度": 48.21},
    {"国家": "匈牙利", "首都": "布达佩斯", "经度": 19.04, "纬度": 47.50},
    {"国家": "希腊", "首都": "雅典", "经度": 23.73, "纬度": 37.98},
    {"国家": "土耳其", "首都": "安卡拉", "经度": 32.85, "纬度": 39.93},
    {"国家": "沙特阿拉伯", "首都": "利雅得", "经度": 46.72, "纬度": 24.65},
    {"国家": "伊朗", "首都": "德黑兰", "经度": 51.42, "纬度": 35.69},
    {"国家": "伊拉克", "首都": "巴格达", "经度": 44.40, "纬度": 33.34},
    {"国家": "以色列", "首都": "耶路撒冷", "经度": 35.22, "纬度": 31.78},
    {"国家": "约旦", "首都": "安曼", "经度": 35.93, "纬度": 31.95},
    {"国家": "黎巴嫩", "首都": "贝鲁特", "经度": 35.50, "纬度": 33.89},
    {"国家": "叙利亚", "首都": "大马士革", "经度": 36.30, "纬度": 33.51},
    {"国家": "阿联酋", "首都": "阿布扎比", "经度": 54.37, "纬度": 24.48},
    {"国家": "卡塔尔", "首都": "多哈", "经度": 51.53, "纬度": 25.28},
    {"国家": "科威特", "首都": "科威特城", "经度": 47.98, "纬度": 29.37},
    {"国家": "阿曼", "首都": "马斯喀特", "经度": 58.59, "纬度": 23.61},
    {"国家": "也门", "首都": "萨那", "经度": 44.21, "纬度": 15.35},
    {"国家": "哈萨克斯坦", "首都": "阿斯塔纳", "经度": 71.43, "纬度": 51.18},
    {"国家": "乌兹别克斯坦", "首都": "塔什干", "经度": 69.27, "纬度": 41.31},
    {"国家": "土库曼斯坦", "首都": "阿什哈巴德", "经度": 58.38, "纬度": 37.95},
    {"国家": "吉尔吉斯斯坦", "首都": "比什凯克", "经度": 74.59, "纬度": 42.87},
    {"国家": "塔吉克斯坦", "首都": "杜尚别", "经度": 68.78, "纬度": 38.56},
    {"国家": "阿富汗", "首都": "喀布尔", "经度": 69.18, "纬度": 34.53},
    {"国家": "巴基斯坦", "首都": "伊斯兰堡", "经度": 73.07, "纬度": 33.72},
    {"国家": "孟加拉国", "首都": "达卡", "经度": 90.41, "纬度": 23.71},
    {"国家": "斯里兰卡", "首都": "科伦坡", "经度": 79.85, "纬度": 6.93},
    {"国家": "尼泊尔", "首都": "加德满都", "经度": 85.32, "纬度": 27.72},
    {"国家": "不丹", "首都": "廷布", "经度": 89.64, "纬度": 27.47},
    {"国家": "缅甸", "首都": "内比都", "经度": 96.11, "纬度": 19.75},
    {"国家": "泰国", "首都": "曼谷", "经度": 100.50, "纬度": 13.75},
    {"国家": "老挝", "首都": "万象", "经度": 102.60, "纬度": 17.97},
    {"国家": "柬埔寨", "首都": "金边", "经度": 104.92, "纬度": 11.55},
    {"国家": "越南", "首都": "河内", "经度": 105.85, "纬度": 21.03},
    {"国家": "马来西亚", "首都": "吉隆坡", "经度": 101.69, "纬度": 3.14},
    {"国家": "新加坡", "首都": "新加坡", "经度": 103.82, "纬度": 1.35},
    {"国家": "菲律宾", "首都": "马尼拉", "经度": 120.98, "纬度": 14.60},
    {"国家": "印度尼西亚", "首都": "雅加达", "经度": 106.83, "纬度": -6.17},
    {"国家": "韩国", "首都": "首尔", "经度": 126.98, "纬度": 37.57},
    {"国家": "朝鲜", "首都": "平壤", "经度": 125.75, "纬度": 39.03},
    {"国家": "蒙古", "首都": "乌兰巴托", "经度": 106.92, "纬度": 47.92},
    {"国家": "南非", "首都": "比勒陀利亚", "经度": 28.19, "纬度": -25.74},
    {"国家": "尼日利亚", "首都": "阿布贾", "经度": 7.50, "纬度": 9.08},
    {"国家": "肯尼亚", "首都": "内罗毕", "经度": 36.82, "纬度": -1.29},
    {"国家": "埃塞俄比亚", "首都": "亚的斯亚贝巴", "经度": 38.75, "纬度": 9.02},
    {"国家": "摩洛哥", "首都": "拉巴特", "经度": -6.84, "纬度": 34.02},
    {"国家": "阿尔及利亚", "首都": "阿尔及尔", "经度": 3.05, "纬度": 36.75},
    {"国家": "突尼斯", "首都": "突尼斯", "经度": 10.18, "纬度": 36.81},
    {"国家": "利比亚", "首都": "的黎波里", "经度": 13.19, "纬度": 32.88},
    {"国家": "苏丹", "首都": "喀土穆", "经度": 32.53, "纬度": 15.59},
    {"国家": "南苏丹", "首都": "朱巴", "经度": 31.60, "纬度": 4.85},
    {"国家": "厄立特里亚", "首都": "阿斯马拉", "经度": 38.93, "纬度": 15.33},
    {"国家": "吉布提", "首都": "吉布提市", "经度": 43.14, "纬度": 11.58},
    {"国家": "索马里", "首都": "摩加迪沙", "经度": 45.34, "纬度": 2.04},
    {"国家": "乌干达", "首都": "坎帕拉", "经度": 32.58, "纬度": 0.31},
    {"国家": "卢旺达", "首都": "基加利", "经度": 30.06, "纬度": -1.94},
    {"国家": "布隆迪", "首都": "基特加", "经度": 29.92, "纬度": -3.43},
    {"国家": "坦桑尼亚", "首都": "多多马", "经度": 35.75, "纬度": -6.17},
    {"国家": "莫桑比克", "首都": "马普托", "经度": 32.58, "纬度": -25.97},
    {"国家": "马达加斯加", "首都": "塔那那利佛", "经度": 47.53, "纬度": -18.93},
    {"国家": "安哥拉", "首都": "罗安达", "经度": 13.24, "纬度": -8.84},
    {"国家": "纳米比亚", "首都": "温得和克", "经度": 17.09, "纬度": -22.57},
    {"国家": "博茨瓦纳", "首都": "哈博罗内", "经度": 25.92, "纬度": -24.66},
    {"国家": "赞比亚", "首都": "卢萨卡", "经度": 28.28, "纬度": -15.42},
    {"国家": "津巴布韦", "首都": "哈拉雷", "经度": 31.05, "纬度": -17.83},
    {"国家": "马拉维", "首都": "利隆圭", "经度": 33.78, "纬度": -13.99},
    {"国家": "刚果民主共和国", "首都": "金沙萨", "经度": 15.31, "纬度": -4.33},
    {"国家": "刚果共和国", "首都": "布拉柴维尔", "经度": 15.28, "纬度": -4.27},
    {"国家": "加蓬", "首都": "利伯维尔", "经度": 9.45, "纬度": 0.39},
    {"国家": "赤道几内亚", "首都": "马拉博", "经度": 8.78, "纬度": 3.75},
    {"国家": "喀麦隆", "首都": "雅温得", "经度": 11.52, "纬度": 3.87},
    {"国家": "中非共和国", "首都": "班吉", "经度": 18.55, "纬度": 4.37},
    {"国家": "乍得", "首都": "恩贾梅纳", "经度": 15.04, "纬度": 12.11},
    {"国家": "尼日尔", "首都": "尼亚美", "经度": 2.11, "纬度": 13.51},
    {"国家": "马里", "首都": "巴马科", "经度": -8.00, "纬度": 12.64},
    {"国家": "毛里塔尼亚", "首都": "努瓦克肖特", "经度": -15.98, "纬度": 18.08},
    {"国家": "塞内加尔", "首都": "达喀尔", "经度": -17.44, "纬度": 14.69},
    {"国家": "冈比亚", "首都": "班珠尔", "经度": -16.58, "纬度": 13.45},
    {"国家": "几内亚比绍", "首都": "比绍", "经度": -15.60, "纬度": 11.86},
    {"国家": "几内亚", "首都": "科纳克里", "经度": -13.71, "纬度": 9.54},
    {"国家": "塞拉利昂", "首都": "弗里敦", "经度": -13.23, "纬度": 8.48},
    {"国家": "利比里亚", "首都": "蒙罗维亚", "经度": -10.80, "纬度": 6.30},
    {"国家": "科特迪瓦", "首都": "亚穆苏克罗", "经度": -5.28, "纬度": 6.82},
    {"国家": "加纳", "首都": "阿克拉", "经度": -0.20, "纬度": 5.56},
    {"国家": "多哥", "首都": "洛美", "经度": 1.22, "纬度": 6.13},
    {"国家": "贝宁", "首都": "波多诺伏", "经度": 2.63, "纬度": 6.50},
    {"国家": "布基纳法索", "首都": "瓦加杜古", "经度": -1.53, "纬度": 12.37},
    {"国家": "佛得角", "首都": "普拉亚", "经度": -23.51, "纬度": 14.92},
    {"国家": "圣多美和普林西比", "首都": "圣多美", "经度": 6.73, "纬度": 0.33},
    {"国家": "科摩罗", "首都": "莫罗尼", "经度": 43.25, "纬度": -11.70},
    {"国家": "毛里求斯", "首都": "路易港", "经度": 57.50, "纬度": -20.16},
    {"国家": "塞舌尔", "首都": "维多利亚", "经度": 55.45, "纬度": -4.62},
    {"国家": "古巴", "首都": "哈瓦那", "经度": -82.38, "纬度": 23.13},
    {"国家": "牙买加", "首都": "金斯敦", "经度": -76.79, "纬度": 17.98},
    {"国家": "海地", "首都": "太子港", "经度": -72.34, "纬度": 18.54},
    {"国家": "多米尼加共和国", "首都": "圣多明各", "经度": -69.90, "纬度": 18.48},
    {"国家": "波多黎各（美）", "首都": "圣胡安", "经度": -66.11, "纬度": 18.47},
    {"国家": "巴哈马", "首都": "拿骚", "经度": -77.34, "纬度": 25.07},
    {"国家": "特立尼达和多巴哥", "首都": "西班牙港", "经度": -61.52, "纬度": 10.66},
    {"国家": "巴巴多斯", "首都": "布里奇顿", "经度": -59.62, "纬度": 13.10},
    {"国家": "圣卢西亚", "首都": "卡斯特里", "经度": -61.00, "纬度": 14.01},
    {"国家": "格林纳达", "首都": "圣乔治", "经度": -61.75, "纬度": 12.06},
    {"国家": "圣文森特和格林纳丁斯", "首都": "金斯敦", "经度": -61.22, "纬度": 13.16},
    {"国家": "安提瓜和巴布达", "首都": "圣约翰", "经度": -61.85, "纬度": 17.12},
    {"国家": "多米尼克", "首都": "罗索", "经度": -61.39, "纬度": 15.30},
    {"国家": "圣基茨和尼维斯", "首都": "巴斯特尔", "经度": -62.72, "纬度": 17.30},
    {"国家": "危地马拉", "首都": "危地马拉城", "经度": -90.53, "纬度": 14.62},
    {"国家": "伯利兹", "首都": "贝尔莫潘", "经度": -88.77, "纬度": 17.25},
    {"国家": "洪都拉斯", "首都": "特古西加尔巴", "经度": -87.20, "纬度": 14.09},
    {"国家": "萨尔瓦多", "首都": "圣萨尔瓦多", "经度": -89.20, "纬度": 13.70},
    {"国家": "尼加拉瓜", "首都": "马那瓜", "经度": -86.27, "纬度": 12.15},
    {"国家": "哥斯达黎加", "首都": "圣何塞", "经度": -84.08, "纬度": 9.93},
    {"国家": "巴拿马", "首都": "巴拿马城", "经度": -79.52, "纬度": 8.98},
    {"国家": "哥伦比亚", "首都": "波哥大", "经度": -74.08, "纬度": 4.60},
    {"国家": "委内瑞拉", "首都": "加拉加斯", "经度": -66.88, "纬度": 10.49},
    {"国家": "圭亚那", "首都": "乔治敦", "经度": -58.17, "纬度": 6.80},
    {"国家": "苏里南", "首都": "帕拉马里博", "经度": -55.17, "纬度": 5.87},
    {"国家": "法属圭亚那", "首都": "卡宴", "经度": -52.33, "纬度": 4.93},
    {"国家": "厄瓜多尔", "首都": "基多", "经度": -78.52, "纬度": -0.23},
    {"国家": "秘鲁", "首都": "利马", "经度": -77.04, "纬度": -12.05},
    {"国家": "玻利维亚", "首都": "拉巴斯（行政）", "经度": -68.15, "纬度": -16.50},  # 拉巴斯是行政首都，法定首都为苏克雷
    {"国家": "巴拉圭", "首都": "亚松森", "经度": -57.64, "纬度": -25.30},
    {"国家": "智利", "首都": "圣地亚哥", "经度": -70.65, "纬度": -33.45},
    {"国家": "乌拉圭", "首都": "蒙得维的亚", "经度": -56.19, "纬度": -34.90},
    {"国家": "阿根廷", "首都": "布宜诺斯艾利斯", "经度": -58.38, "纬度": -34.60},  # 重复但保留
    {"国家": "新西兰", "首都": "惠灵顿", "经度": 174.78, "纬度": -41.29},
    {"国家": "巴布亚新几内亚", "首都": "莫尔兹比港", "经度": 147.18, "纬度": -9.48},
    {"国家": "斐济", "首都": "苏瓦", "经度": 178.42, "纬度": -18.14},
    {"国家": "所罗门群岛", "首都": "霍尼亚拉", "经度": 159.95, "纬度": -9.43},
    {"国家": "瓦努阿图", "首都": "维拉港", "经度": 168.32, "纬度": -17.73},
    {"国家": "萨摩亚", "首都": "阿皮亚", "经度": -171.76, "纬度": -13.83},
    {"国家": "汤加", "首都": "努库阿洛法", "经度": -175.20, "纬度": -21.13},
    {"国家": "基里巴斯", "首都": "塔拉瓦", "经度": 173.01, "纬度": 1.33},
    {"国家": "密克罗尼西亚联邦", "首都": "帕利基尔", "经度": 158.16, "纬度": 6.92},
    {"国家": "马绍尔群岛", "首都": "马朱罗", "经度": 171.18, "纬度": 7.09},
    {"国家": "帕劳", "首都": "恩吉鲁穆德", "经度": 134.62, "纬度": 7.50},
    {"国家": "瑙鲁", "首都": "亚伦", "经度": 166.93, "纬度": -0.55},
    {"国家": "图瓦卢", "首都": "富纳富提", "经度": 179.19, "纬度": -8.52},
    {"国家": "冰岛", "首都": "雷克雅未克", "经度": -21.94, "纬度": 64.15},
    {"国家": "爱尔兰", "首都": "都柏林", "经度": -6.26, "纬度": 53.35},
    {"国家": "葡萄牙", "首都": "里斯本", "经度": -9.14, "纬度": 38.72},  # 重复但保留
    {"国家": "安道尔", "首都": "安道尔城", "经度": 1.52, "纬度": 42.51},
    {"国家": "摩纳哥", "首都": "摩纳哥", "经度": 7.42, "纬度": 43.73},
    {"国家": "列支敦士登", "首都": "瓦杜兹", "经度": 9.52, "纬度": 47.14},
    {"国家": "卢森堡", "首都": "卢森堡市", "经度": 6.13, "纬度": 49.61},
    {"国家": "圣马力诺", "首都": "圣马力诺", "经度": 12.45, "纬度": 43.94},
    {"国家": "梵蒂冈", "首都": "梵蒂冈城", "经度": 12.45, "纬度": 41.90},
    {"国家": "马耳他", "首都": "瓦莱塔", "经度": 14.51, "纬度": 35.90},
    {"国家": "塞浦路斯", "首都": "尼科西亚", "经度": 33.37, "纬度": 35.17},
    {"国家": "阿尔巴尼亚", "首都": "地拉那", "经度": 19.82, "纬度": 41.33},
    {"国家": "北马其顿", "首都": "斯科普里", "经度": 21.43, "纬度": 42.00},
    {"国家": "保加利亚", "首都": "索非亚", "经度": 23.32, "纬度": 42.70},
    {"国家": "罗马尼亚", "首都": "布加勒斯特", "经度": 26.10, "纬度": 44.43},
    {"国家": "摩尔多瓦", "首都": "基希讷乌", "经度": 28.86, "纬度": 47.01},
    {"国家": "乌克兰", "首都": "基辅", "经度": 30.52, "纬度": 50.45},
    {"国家": "白俄罗斯", "首都": "明斯克", "经度": 27.57, "纬度": 53.90},
    {"国家": "立陶宛", "首都": "维尔纽斯", "经度": 25.28, "纬度": 54.69},
    {"国家": "拉脱维亚", "首都": "里加", "经度": 24.10, "纬度": 56.95},
    {"国家": "爱沙尼亚", "首都": "塔林", "经度": 24.75, "纬度": 59.44},
    {"国家": "格鲁吉亚", "首都": "第比利斯", "经度": 44.79, "纬度": 41.72},
    {"国家": "亚美尼亚", "首都": "埃里温", "经度": 44.51, "纬度": 40.18},
    {"国家": "阿塞拜疆", "首都": "巴库", "经度": 49.87, "纬度": 40.38},
    {"国家": "塞尔维亚", "首都": "贝尔格莱德", "经度": 20.46, "纬度": 44.82},
    {"国家": "克罗地亚", "首都": "萨格勒布", "经度": 15.98, "纬度": 45.81},
    {"国家": "斯洛文尼亚", "首都": "卢布尔雅那", "经度": 14.51, "纬度": 46.05},
    {"国家": "波黑", "首都": "萨拉热窝", "经度": 18.36, "纬度": 43.85},
    {"国家": "黑山", "首都": "波德戈里察", "经度": 19.26, "纬度": 42.44},
    {"国家": "科索沃", "首都": "普里什蒂纳", "经度": 21.17, "纬度": 42.67},
    {"国家": "斯洛伐克", "首都": "布拉迪斯拉发", "经度": 17.11, "纬度": 48.15},
    {"国家": "波斯尼亚和黑塞哥维那", "首都": "萨拉热窝", "经度": 18.36, "纬度": 43.85}  # 重复但保留
]  # 请粘贴之前提供的完整首都列表
lons_cap = [city["经度"] for city in capitals_data]
lats_cap = [city["纬度"] for city in capitals_data]
texts_cap = [f"{city['首都']}<br>{city['国家']}" for city in capitals_data]

# ==================== 3. 创建底图（不含轨迹）的函数 ====================
def create_base_figure():
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
    )

    # 添加首都图层
    fig.add_trace(go.Scattergeo(
        lon=lons_cap,
        lat=lats_cap,
        text=texts_cap,
        mode='markers',
        marker=dict(size=6, color='red', symbol='circle', line=dict(width=1, color='white')),
        name='首都',
        hoverinfo='text+lon+lat'
    ))

    # 添加边界图层（默认隐藏）
    fig.add_trace(go.Scattergeo(
        lon=province_lons, lat=province_lats,
        mode='lines', line=dict(color='blue', width=2.5),
        name='省界', visible=False, hoverinfo='skip', showlegend=True
    ))
    fig.add_trace(go.Scattergeo(
        lon=city_lons, lat=city_lats,
        mode='lines', line=dict(color='green', width=1),
        name='市界', visible=False, hoverinfo='skip', showlegend=True
    ))
    fig.add_trace(go.Scattergeo(
        lon=county_lons, lat=county_lats,
        mode='lines', line=dict(color='orange', width=0.5),
        name='县界', visible=False, hoverinfo='skip', showlegend=True
    ))

    # ===== 经纬网格和特殊线 =====
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
    fig.add_trace(go.Scattergeo(
        lon=lons_meridian, lat=lats_meridian,
        mode='lines', line=dict(color='gray', width=1, dash='dot'),
        name='经线 (10°)', hoverinfo='skip', showlegend=True
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
    fig.add_trace(go.Scattergeo(
        lon=lons_parallel, lat=lats_parallel,
        mode='lines', line=dict(color='gray', width=1, dash='dot'),
        name='纬线 (10°)', hoverinfo='skip', showlegend=True
    ))

    # 赤道
    lons_equator = list(range(-180, 181, 1))
    lats_equator = [0] * len(lons_equator)
    fig.add_trace(go.Scattergeo(
        lon=lons_equator, lat=lats_equator,
        mode='lines', line=dict(color='red', width=1),
        name='赤道', hoverinfo='skip', showlegend=True
    ))

    # 北回归线
    lons_tropic_n = list(range(-180, 181, 1))
    lats_tropic_n = [23.5] * len(lons_tropic_n)
    fig.add_trace(go.Scattergeo(
        lon=lons_tropic_n, lat=lats_tropic_n,
        mode='lines', line=dict(color='blue', width=1, dash='dash'),
        name='北回归线', hoverinfo='skip', showlegend=True
    ))

    # 南回归线
    lons_tropic_s = list(range(-180, 181, 1))
    lats_tropic_s = [-23.5] * len(lons_tropic_s)
    fig.add_trace(go.Scattergeo(
        lon=lons_tropic_s, lat=lats_tropic_s,
        mode='lines', line=dict(color='blue', width=1, dash='dash'),
        name='南回归线', hoverinfo='skip', showlegend=True
    ))

    # 北极圈
    lons_arctic = list(range(-180, 181, 1))
    lats_arctic = [66.5] * len(lons_arctic)
    fig.add_trace(go.Scattergeo(
        lon=lons_arctic, lat=lats_arctic,
        mode='lines', line=dict(color='blue', width=1, dash='dash'),
        name='北极圈', hoverinfo='skip', showlegend=True
    ))

    # 南极圈
    lons_antarctic = list(range(-180, 181, 1))
    lats_antarctic = [-66.5] * len(lons_antarctic)
    fig.add_trace(go.Scattergeo(
        lon=lons_antarctic, lat=lats_antarctic,
        mode='lines', line=dict(color='blue', width=1, dash='dash'),
        name='南极圈', hoverinfo='skip', showlegend=True
    ))

    # ===== 边界控制按钮 =====
    # 轨迹索引: 0首都, 1省界, 2市界, 3县界, 4经线, 5纬线, 6赤道, 7北回归线, 8南回归线, 9北极圈, 10南极圈
    def make_visible_array(cap_vis, pro_vis, city_vis, county_vis):
        return [cap_vis, pro_vis, city_vis, county_vis] + [True]*7

    buttons = [
        dict(label="无边界", method="restyle",
             args=[{"visible": make_visible_array(True, False, False, False)}]),
        dict(label="仅省界", method="restyle",
             args=[{"visible": make_visible_array(True, True, False, False)}]),
        dict(label="仅市界", method="restyle",
             args=[{"visible": make_visible_array(True, False, True, False)}]),
        dict(label="仅县界", method="restyle",
             args=[{"visible": make_visible_array(True, False, False, True)}]),
        dict(label="省+市", method="restyle",
             args=[{"visible": make_visible_array(True, True, True, False)}]),
        dict(label="省+县", method="restyle",
             args=[{"visible": make_visible_array(True, True, False, True)}]),
        dict(label="市+县", method="restyle",
             args=[{"visible": make_visible_array(True, False, True, True)}]),
        dict(label="全部边界", method="restyle",
             args=[{"visible": make_visible_array(True, True, True, True)}]),
    ]

    fig.update_layout(
        title="世界地图 + 首都 + 中国省/市/县边界 + 经纬网格 + 星下点轨迹",
        geo=dict(showframe=False),
        hovermode='closest',
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                x=0.7,
                y=1.15,
                showactive=True,
                buttons=buttons
            )
        ]
    )
    return fig

# ==================== 4. 轨道计算函数（返回北京时间字符串）====================
def compute_groundtrack(tle_line1, tle_line2, start_time, end_time, step_seconds=60):
    """
    根据两行 TLE 计算从 start_time 到 end_time 的星下点轨迹。
    返回 (lons, lats, beijing_times) 三个列表，长度相同，遇到经度跳变处插入 None。
    beijing_times 为字符串列表，对应每个点的北京时间（UTC+8），格式如 "2025-03-08 16:00:00"
    """
    ts = load.timescale()
    satellite = EarthSatellite(tle_line1, tle_line2)
    # 生成时间序列
    t0 = ts.from_datetime(start_time)
    t1 = ts.from_datetime(end_time)
    num_steps = int((end_time - start_time).total_seconds() / step_seconds) + 1
    times = ts.linspace(t0, t1, num_steps)

    lons = []
    lats = []
    beijing_times = []
    last_lon = None
    for t in times:
        # 计算星下点
        geocentric = satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)
        lon = subpoint.longitude.degrees
        lat = subpoint.latitude.degrees

        # 处理经度跳变
        if last_lon is not None and abs(lon - last_lon) > 180:
            lons.append(None)
            lats.append(None)
            beijing_times.append(None)   # 跳变点无实际时间对应

        # 当前点
        lons.append(lon)
        lats.append(lat)
        # 将 UTC 时间转换为北京时间 (UTC+8)
        utc_dt = t.utc_datetime()                # 返回 naive datetime, 实际为 UTC
        # 明确标记为 UTC 再转换
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        beijing_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
        beijing_times.append(beijing_dt.strftime("%Y-%m-%d %H:%M:%S"))

        last_lon = lon

    return lons, lats, beijing_times

# ==================== 5. 预定义卫星TLE字典 ====================
satellite_tle = {
    '中国空间站': (
        '1 48274U 21035A   26066.15577909  .00030452  00000-0  36120-3 0  9998',
        '2 48274  41.4664 223.5772 0006996 257.5663 102.4393 15.60515598277210 12345'
    ),
    'fy3d': (
        '1 43010U 17072A   26064.05521054  .00000000  00000-0  00000-0 0  0000',  
        '2 43010  99.0028  36.6574  0001823  2.0220  358.1039  14.19716669430220 12345' 
    ),
    'fy3e': (
        '1 49009U 21063B   26067.01083486  .00000000  00000-0  00000-0 0  0000',
        '2 49009  98.7500  71.5451  0001814  33.4880  326.6489  14.19886895242230 12345'
    ),
    'fy3f': (
        '1 57490U 23111A  26067.06725954  .00000000  00000-0  00000-0 0  0000',  
        '2 57490  98.6926  138.9262  0000646  87.8848  272.2481  14.19923762134520 12345'
    ),
    'fy3g': (
        '1 56232U 23055A  26066.54166667  .00052070  00000-0  77069-3 0  00003',  
        '2 56232  049.9924  150.0857  0010757  003.5220  160.8582  15.54459013164227 12345'  
    ),
    'fy4a': (
        '1 41882U 16077A   24055.54166667  .00000000  00000-0  00000-0 0  9998',
        '2 41882  0.0456 123.4567 0001234  34.5678 325.6789  1.00270000 12345'
    ),
}

# ==================== 6. 创建 Dash 应用（紧凑布局）====================
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("卫星星下点轨迹交互地图", style={'textAlign': 'center', 'marginBottom': 5}),
    html.Div([
        # 左侧输入面板 - 宽度20%，紧凑设计
        html.Div([
            html.H4("轨道参数", style={'marginTop': 0, 'marginBottom': 10}),

            # 新增卫星选择下拉菜单
            html.Label("选择卫星", style={'fontSize': 'small'}),
            dcc.Dropdown(
                id='satellite-select',
                options=[
                    {'label': '中国空间站', 'value': '中国空间站'},
                    {'label': '风云三号D星 (FY-3D)', 'value': 'fy3d'},
                    {'label': '风云三号E星 (FY-3E)', 'value': 'fy3e'},
                    {'label': '风云三号F星 (FY-3F)', 'value': 'fy3f'},
                    {'label': '风云三号G星 (FY-3G)', 'value': 'fy3g'},
                    {'label': '风云四号A星 (FY-4A)', 'value': 'fy4a'},
                ],
                placeholder="选择卫星自动填充TLE",
                style={'width': '100%', 'marginBottom': '12px', 'fontSize': 'small'}
            ),

            html.Label("TLE 第一行", style={'fontSize': 'small'}),
            dcc.Input(id='tle1', type='text',
                      value='1 25544U 98067A   24055.54166667  .00015000  00000-0  25000-3 0  9999',
                      style={'width': '100%', 'marginBottom': '8px', 'padding': '3px', 'fontSize': 'small'}),
            html.Label("TLE 第二行", style={'fontSize': 'small'}),
            dcc.Input(id='tle2', type='text',
                      value='2 25544  51.6443  78.4567 0005678  34.5678 325.6789 15.50000000 12345',
                      style={'width': '100%', 'marginBottom': '8px', 'padding': '3px', 'fontSize': 'small'}),
            html.Label("开始时间 (UTC)", style={'fontSize': 'small'}),
            dcc.Input(id='start_time', type='text', value='2025-03-08 00:00:00',
                      style={'width': '100%', 'marginBottom': '8px', 'padding': '3px', 'fontSize': 'small'}),
            html.Label("结束时间 (UTC)", style={'fontSize': 'small'}),
            dcc.Input(id='end_time', type='text', value='2025-03-08 23:59:59',
                      style={'width': '100%', 'marginBottom': '8px', 'padding': '3px', 'fontSize': 'small'}),
            html.Label("步长 (秒)", style={'fontSize': 'small'}),
            dcc.Input(id='step', type='number', value=60,
                      style={'width': '100%', 'marginBottom': '15px', 'padding': '3px', 'fontSize': 'small'}),
            html.Button('绘制轨迹', id='plot_button', n_clicks=0,
                        style={'width': '100%', 'backgroundColor': '#007BFF', 'color': 'white',
                               'padding': '5px', 'fontSize': 'medium', 'border': 'none', 'borderRadius': '3px'}),
        ], style={'padding': '15px', 'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top',
                  'backgroundColor': '#f8f9fa', 'borderRadius': '5px', 'boxSizing': 'border-box'}),

        # 右侧地图区域 - 宽度80%
        html.Div([
            dcc.Graph(id='world-map', figure=create_base_figure(),
                      style={'height': '85vh', 'width': '100%'})   # 使用视口高度，地图更大
        ], style={'width': '80%', 'display': 'inline-block', 'padding': '0', 'boxSizing': 'border-box'})
    ], style={'display': 'flex', 'flexWrap': 'wrap'})
])

# ==================== 7. 回调：卫星选择自动填充TLE ====================
@app.callback(
    [Output('tle1', 'value'),
     Output('tle2', 'value')],
    Input('satellite-select', 'value'),
    prevent_initial_call=True
)
def fill_tle_from_satellite(selected_sat):
    if selected_sat is None:
        return dash.no_update, dash.no_update
    tle1, tle2 = satellite_tle.get(selected_sat, (None, None))
    if tle1 is None or tle2 is None:
        return dash.no_update, dash.no_update
    return tle1, tle2

# ==================== 8. 回调：绘制轨迹 ====================
@app.callback(
    Output('world-map', 'figure'),
    Input('plot_button', 'n_clicks'),
    State('tle1', 'value'),
    State('tle2', 'value'),
    State('start_time', 'value'),
    State('end_time', 'value'),
    State('step', 'value'),
    prevent_initial_call=True
)
def update_track(n_clicks, tle1, tle2, start_str, end_str, step):
    if not tle1 or not tle2:
        return dash.no_update
    try:
        # 将字符串转换为带 UTC 时区的 datetime
        start = pd.to_datetime(start_str).tz_localize('UTC')
        end = pd.to_datetime(end_str).tz_localize('UTC')
        # 计算星下点轨迹及北京时间
        lons, lats, beijing_times = compute_groundtrack(tle1.strip(), tle2.strip(), start, end, step)

        # 重新生成基础地图
        fig = create_base_figure()

        # 添加轨迹，设置 customdata 为北京时间字符串，并自定义悬停模板
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            customdata=beijing_times,          # 每个点对应的北京时间字符串（或 None）
            mode='lines+markers',
            marker=dict(size=4, color='lightgrey'),
            line=dict(width=1, color='magenta'),
            name='星下点轨迹',
            hovertemplate=(
                "<b>北京时间:</b> %{customdata}<br>" +
                "<b>经度:</b> %{lon:.4f}°<br>" +
                "<b>纬度:</b> %{lat:.4f}°<br>" +
                "<extra></extra>"               # 隐藏第二个框
            )
        ))
        return fig
    except Exception as e:
        print(f"Error: {e}")
        return dash.no_update

if __name__ == '__main__':
    app.run(debug=True)