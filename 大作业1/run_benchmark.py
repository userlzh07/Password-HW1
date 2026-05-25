# -*- coding: utf-8 -*-
import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.qkd_core import BB84SatelliteQKD
from modules.eve_attacks import InterceptResendAttack, BeamSplittingAttack, PhotonNumberSplittingAttack
from modules.security_defense import SecurityAnalyzer
from modules.channel_model import ChannelModel, ChannelParameters

def benchmark_qkd():
    print("=" * 60)
    print("QKD Core Benchmark")
    print("=" * 60)
    
    # 测试不同透射率
    test_cases = [
        ("Ideal channel", 1.0, None),
        ("Good channel", 0.1, None),
        ("Medium channel", 0.01, None),
        ("Poor channel", 0.001, None),
        ("Intercept-Resend 50%", 0.1, InterceptResendAttack(0.5)),
        ("Beam-Splitting 30%", 0.1, BeamSplittingAttack(0.3)),
        ("PNS Attack", 0.1, PhotonNumberSplittingAttack(1.0)),
    ]
    
    results = []
    for name, transmission, attack in test_cases:
        qkd = BB84SatelliteQKD(channel_transmission=transmission)
        
        # Warm-up
        qkd.simulate_exchange(n_pulses=1000, eve_attack=attack)
        
        # Benchmark
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            result = qkd.simulate_exchange(n_pulses=10000, eve_attack=attack)
            t1 = time.perf_counter()
            times.append(t1 - t0)
        
        avg_time = np.mean(times) * 1000  # ms
        std_time = np.std(times) * 1000
        
        results.append({
            'name': name,
            'transmission': transmission,
            'qber': result['qber_percent'],
            'n_sifted': result['n_sifted'],
            'sifted_rate_kbps': result['sifted_rate'] / 1000,
            'eve_info': result['eve_info_ratio'] * 100,
            'avg_time_ms': avg_time,
            'std_time_ms': std_time
        })
        
        print(f"{name}: QBER={result['qber_percent']:.2f}%, "
              f"Sifted={result['n_sifted']} bits, "
              f"Rate={result['sifted_rate']/1000:.2f} kbps, "
              f"Eve={result['eve_info_ratio']*100:.1f}%, "
              f"Time={avg_time:.2f} +/- {std_time:.2f} ms")
    
    return results

def benchmark_channel():
    print("\n" + "=" * 60)
    print("Channel Model Benchmark")
    print("=" * 60)
    
    model = ChannelModel()
    scenarios = [
        (400, 90, 0.2, "Zenith, clear"),
        (500, 30, 0.2, "Good elevation, clear"),
        (600, 20, 2.0, "Medium elevation, mist"),
        (700, 10, 5.0, "Low elevation, rain"),
    ]
    
    channel_results = []
    for dist, elev, atten, desc in scenarios:
        params = ChannelParameters(distance_km=dist, elevation_deg=elev, attenuation_db_per_km=atten)
        result = model.full_channel_analysis(params)
        channel_results.append({
            'desc': desc,
            'distance': dist,
            'elevation': elev,
            'atten': atten,
            'total_trans': result['transmission']['total'],
            'qber': result['qber_percent'],
            'secret_rate_kbps': result['key_rates']['secret_rate_kbps']
        })
        print(f"{desc}: T_total={result['transmission']['total']:.2e}, "
              f"QBER={result['qber_percent']:.2f}%, "
              f"SecretRate={result['key_rates']['secret_rate_kbps']:.3f} kbps")
    
    return channel_results

def benchmark_security():
    print("\n" + "=" * 60)
    print("Security Analysis Benchmark")
    print("=" * 60)
    
    analyzer = SecurityAnalyzer()
    
    test_cases = [
        (5000, 0.03, 0.0, 10000, "none", "Ideal"),
        (5000, 0.05, 0.1, 10000, "beam_splitting", "Mild attack"),
        (5000, 0.08, 0.2, 10000, "intercept_resend", "Strong attack"),
        (5000, 0.12, 0.3, 10000, "pns", "Above threshold"),
    ]
    
    sec_results = []
    for n_sifted, qber, eve_info, rate, attack_type, desc in test_cases:
        qkd_result = {
            'n_sifted': n_sifted,
            'qber': qber,
            'sifted_rate': rate,
            'eve_info_ratio': eve_info
        }
        analysis = analyzer.full_security_analysis(qkd_result, attack_type=attack_type)
        sec_results.append({
            'desc': desc,
            'qber': qber * 100,
            'eve_info': eve_info * 100,
            'feasible': analysis['feasible'],
            'level': analysis['security_level'],
            'secure_len': analysis['secure_key_length'],
            'secret_rate_kbps': analysis['secret_key_rate_kbps']
        })
        print(f"{desc}: QBER={qber*100:.1f}%, Eve={eve_info*100:.1f}% -> "
              f"Feasible={analysis['feasible']}, Level={analysis['security_level']}, "
              f"SecureKey={analysis['secure_key_length']} bits, "
              f"Rate={analysis['secret_key_rate_kbps']:.2f} kbps")
    
    return sec_results

if __name__ == "__main__":
    qkd_res = benchmark_qkd()
    ch_res = benchmark_channel()
    sec_res = benchmark_security()
    
    print("\n" + "=" * 60)
    print("All benchmarks completed!")
    print("=" * 60)
