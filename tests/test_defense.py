"""
防御模块测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from modules.security_defense import (
    PrivacyAmplification,
    DecoyStateProtocol,
    SecurityDecisionEngine,
    SecurityAnalyzer
)


def test_privacy_amplification():
    """测试隐私放大"""
    print("=" * 60)
    print("测试隐私放大")
    print("=" * 60)
    
    pa = PrivacyAmplification()
    
    # 测试场景
    test_cases = [
        (10000, 0.03, 0.0),   # 理想情况
        (10000, 0.05, 0.1),   # 轻微攻击
        (10000, 0.08, 0.2),   # 中等攻击
        (10000, 0.12, 0.3),   # 高QBER，应返回0
    ]
    
    for n, qber, eve_info in test_cases:
        secure_len = pa.calculate_secure_length(n, qber, eve_info)
        ratio = secure_len / n if n > 0 else 0
        
        print(f"\nQBER={qber*100:.1f}%, Eve_info={eve_info*100:.1f}%")
        print(f"  原始密钥: {n} bits")
        print(f"  安全密钥: {secure_len} bits")
        print(f"  保留比例: {ratio*100:.1f}%")
        
        if qber < 0.11:
            assert secure_len > 0, "QBER<11%时应能提取安全密钥"
        else:
            assert secure_len == 0, "QBER过高时不应提取密钥"
    
    print("✓ 隐私放大测试通过")


def test_decoy_state():
    """测试诱骗态协议"""
    print("\n" + "=" * 60)
    print("测试诱骗态协议")
    print("=" * 60)
    
    decoy = DecoyStateProtocol()
    
    # 生成脉冲序列
    n_pulses = 10000
    intensities, pulse_types = decoy.generate_pulse_sequence(n_pulses)
    
    print(f"\n生成 {n_pulses} 个脉冲:")
    print(f"  信号态(μ=0.5): {np.sum(pulse_types == 0)} ({np.mean(pulse_types == 0)*100:.1f}%)")
    print(f"  诱骗态(ν=0.1): {np.sum(pulse_types == 1)} ({np.mean(pulse_types == 1)*100:.1f}%)")
    print(f"  真空态: {np.sum(pulse_types == 2)} ({np.mean(pulse_types == 2)*100:.1f}%)")
    
    # 测试PNS检测
    print("\nPNS攻击检测测试:")
    
    test_cases = [
        (0.5, 0.2, 0.01, False),   # 正常情况
        (0.5, 0.12, 0.01, True),   # PNS攻击
        (0.5, 0.08, 0.01, True),   # 严重PNS攻击
    ]
    
    for sig_y, dec_y, vac_y, expected_detection in test_cases:
        result = decoy.detect_pns_attack(sig_y, dec_y, vac_y)
        
        print(f"\n  信号={sig_y:.2f}, 诱骗={dec_y:.2f}")
        print(f"    产额比: {result['yield_ratio']:.2f}")
        print(f"    预期比: {result['expected_ratio']:.2f}")
        print(f"    检测结果: {'攻击!' if result['pns_detected'] else '正常'}")
        
        assert result['pns_detected'] == expected_detection
    
    print("✓ 诱骗态协议测试通过")


def test_security_decision():
    """测试安全决策引擎"""
    print("\n" + "=" * 60)
    print("测试安全决策引擎")
    print("=" * 60)
    
    engine = SecurityDecisionEngine()
    
    test_scenarios = [
        (0.03, 5000, 0.0, 10000, True, 'HIGH'),    # 正常
        (0.08, 5000, 0.05, 10000, True, 'MEDIUM'), # 轻微问题
        (0.12, 5000, 0.0, 10000, False, None),     # QBER过高
        (0.05, 50, 0.0, 10000, False, None),       # 光子率过低
        (0.05, 5000, 0.4, 10000, True, 'LOW'),     # Eve信息高
        (0.05, 5000, 0.6, 10000, False, None),     # Eve信息过高
    ]
    
    for qber, rate, eve, n_sifted, expected_feasible, expected_level in test_scenarios:
        decision = engine.make_decision(qber, rate, eve, n_sifted)
        
        print(f"\n场景: QBER={qber*100:.0f}%, rate={rate}, Eve={eve*100:.0f}%")
        print(f"  可行: {decision['feasible']} (期望: {expected_feasible})")
        print(f"  等级: {decision['security_level']}")
        
        if decision['warnings']:
            print(f"  警告: {decision['warnings']}")
        if decision['abort_reasons']:
            print(f"  中止原因: {decision['abort_reasons']}")
        
        assert decision['feasible'] == expected_feasible
        if expected_level:
            assert decision['security_level'] == expected_level
    
    print("✓ 安全决策引擎测试通过")


def test_defense_recommendations():
    """测试防御建议"""
    print("\n" + "=" * 60)
    print("测试防御建议")
    print("=" * 60)
    
    engine = SecurityDecisionEngine()
    
    test_cases = [
        ('pns', 0.05, 0.3),
        ('intercept_resend', 0.1, 0.2),
        ('beam_splitting', 0.05, 0.15),
        (None, 0.05, 0.05),
    ]
    
    for attack, qber, eve in test_cases:
        recommendations = engine.recommend_defense(attack, qber, eve)
        
        print(f"\n攻击={attack}, QBER={qber*100:.0f}%, Eve={eve*100:.0f}%")
        print(f"  建议: {recommendations}")
        
        if attack == 'pns':
            assert any('诱骗态' in r for r in recommendations), "PNS攻击应推荐诱骗态"
        if eve > 0.1:
            assert any('隐私放大' in r for r in recommendations), "高Eve信息应推荐隐私放大"
    
    print("✓ 防御建议测试通过")


def test_security_analyzer():
    """测试完整安全分析器"""
    print("\n" + "=" * 60)
    print("测试完整安全分析器")
    print("=" * 60)
    
    analyzer = SecurityAnalyzer()
    
    # 模拟QKD结果
    qkd_result = {
        'n_sifted': 10000,
        'qber': 0.05,
        'sifted_rate': 10000,
        'eve_info_ratio': 0.1
    }
    
    analysis = analyzer.full_security_analysis(qkd_result, attack_type='beam_splitting')
    
    print("\n完整安全分析结果:")
    print(f"  可行: {analysis['feasible']}")
    print(f"  安全等级: {analysis['security_level']}")
    print(f"  原始密钥: {analysis['original_key_length']} bits")
    print(f"  安全密钥: {analysis['secure_key_length']} bits")
    print(f"  隐私放大比例: {analysis['privacy_amplification_ratio']*100:.1f}%")
    print(f"  安全密钥率: {analysis['secret_key_rate_kbps']:.2f} kbps")
    print(f"  建议: {analysis['recommendations']}")
    
    assert analysis['feasible'] == True
    assert analysis['secure_key_length'] > 0
    assert len(analysis['recommendations']) > 0
    
    print("✓ 完整安全分析器测试通过")


if __name__ == "__main__":
    test_privacy_amplification()
    test_decoy_state()
    test_security_decision()
    test_defense_recommendations()
    test_security_analyzer()
    
    print("\n" + "=" * 60)
    print("所有防御测试通过!")
    print("=" * 60)
