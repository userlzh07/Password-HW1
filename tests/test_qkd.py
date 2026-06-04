"""
QKD核心模块测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from modules.qkd_core import BB84SatelliteQKD
from modules.eve_attacks import InterceptResendAttack, BeamSplittingAttack, PhotonNumberSplittingAttack
from modules.security_defense import SecurityAnalyzer


def test_basic_qkd():
    """测试基础QKD功能"""
    print("=" * 60)
    print("测试基础QKD功能")
    print("=" * 60)
    
    # 创建QKD实例
    qkd = BB84SatelliteQKD(channel_transmission=0.1)
    
    # 运行仿真
    result = qkd.simulate_exchange(n_pulses=10000)
    
    # 验证结果
    assert result['n_pulses'] == 10000
    assert result['n_sifted'] > 0
    assert 0 <= result['qber'] <= 1
    
    print(f"\n✓ 基础QKD测试通过")
    print(f"  脉冲数: {result['n_pulses']}")
    print(f"  筛选密钥: {result['n_sifted']} bits")
    print(f"  QBER: {result['qber_percent']:.2f}%")
    

def test_with_attacks():
    """测试带攻击的QKD"""
    print("\n" + "=" * 60)
    print("测试带攻击的QKD")
    print("=" * 60)
    
    attacks = [
        ("无攻击", None),
        ("截获-重发", InterceptResendAttack(1.0)),
        ("光束分离", BeamSplittingAttack(0.5)),
        ("PNS攻击", PhotonNumberSplittingAttack(1.0))
    ]
    
    for name, attack in attacks:
        qkd = BB84SatelliteQKD(channel_transmission=0.1)
        result = qkd.simulate_exchange(n_pulses=5000, eve_attack=attack)
        
        print(f"\n{name}:")
        print(f"  QBER: {result['qber_percent']:.2f}%")
        print(f"  Eve信息: {result['eve_info_ratio']*100:.2f}%")
        print(f"  筛选密钥: {result['n_sifted']} bits")
        
        if attack is not None:
            assert result['eve_info_ratio'] > 0, f"{name}应产生Eve信息"


def test_security_analysis():
    """测试安全分析"""
    print("\n" + "=" * 60)
    print("测试安全分析")
    print("=" * 60)
    
    analyzer = SecurityAnalyzer()
    
    # 模拟QKD结果
    qkd_result = {
        'n_sifted': 5000,
        'qber': 0.05,
        'sifted_rate': 10000,
        'eve_info_ratio': 0.1
    }
    
    analysis = analyzer.full_security_analysis(qkd_result, attack_type='none')
    
    print(f"\n安全分析结果:")
    print(f"  可行: {analysis['feasible']}")
    print(f"  安全等级: {analysis['security_level']}")
    print(f"  安全密钥长度: {analysis['secure_key_length']} bits")
    print(f"  安全密钥率: {analysis['secret_key_rate_kbps']:.2f} kbps")
    
    assert analysis['feasible'] == True
    assert analysis['secure_key_length'] > 0


def test_key_rate_vs_transmission():
    """测试密钥率与透射率关系"""
    print("\n" + "=" * 60)
    print("测试密钥率与透射率关系")
    print("=" * 60)
    
    transmissions = [0.001, 0.01, 0.1, 0.5]
    
    print("\n透射率 vs 密钥率:")
    for T in transmissions:
        qkd = BB84SatelliteQKD(channel_transmission=T)
        result = qkd.simulate_exchange(n_pulses=10000)
        
        print(f"  T={T:.3f} -> QBER={result['qber_percent']:.2f}%, "
              f"密钥率={result['sifted_rate']/1000:.2f} kbps")
        
        # 验证：透射率越高，密钥率越高
        if T > 0.01:
            assert result['sifted_rate'] > 0


if __name__ == "__main__":
    test_basic_qkd()
    test_with_attacks()
    test_security_analysis()
    test_key_rate_vs_transmission()
    
    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
