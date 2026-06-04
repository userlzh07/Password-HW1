"""
攻击模块测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from modules.eve_attacks import (
    InterceptResendAttack, 
    BeamSplittingAttack, 
    PhotonNumberSplittingAttack,
    get_attack
)


def test_intercept_resend():
    """测试截获-重发攻击"""
    print("=" * 60)
    print("测试截获-重发攻击")
    print("=" * 60)
    
    # 生成测试数据
    n_pulses = 10000
    photon_numbers = np.random.poisson(0.5, n_pulses)
    alice_bases = np.random.randint(0, 2, n_pulses)
    alice_bits = np.random.randint(0, 2, n_pulses)
    
    # 创建攻击
    attack = InterceptResendAttack(attack_strength=1.0)
    
    # 执行攻击
    modified_photons, eve_info = attack.attack(photon_numbers, alice_bases, alice_bits)
    
    print(f"\n攻击强度: 100%")
    print(f"Eve信息比例: {eve_info*100:.2f}%")
    print(f"预期信息比例: ~50% (基匹配) + ~25% (基不匹配)")
    
    # 验证：Eve应该获得信息
    assert eve_info > 0.4, "截获-重发攻击应产生显著Eve信息"
    
    print("✓ 截获-重发攻击测试通过")


def test_beam_splitting():
    """测试光束分离攻击"""
    print("\n" + "=" * 60)
    print("测试光束分离攻击")
    print("=" * 60)
    
    n_pulses = 10000
    photon_numbers = np.random.poisson(0.5, n_pulses)
    alice_bases = np.random.randint(0, 2, n_pulses)
    alice_bits = np.random.randint(0, 2, n_pulses)
    
    # 不同分光比例
    split_ratios = [0.1, 0.3, 0.5]
    
    for ratio in split_ratios:
        attack = BeamSplittingAttack(split_ratio=ratio)
        modified_photons, eve_info = attack.attack(photon_numbers, alice_bases, alice_bits)
        
        print(f"\n分光比例: {ratio*100:.0f}%")
        print(f"Eve信息比例: {eve_info*100:.2f}%")
        print(f"Bob接收平均光子: {np.mean(modified_photons):.3f}")
        
        # Bob接收的光子应该减少
        assert np.mean(modified_photons) <= np.mean(photon_numbers)
    
    print("✓ 光束分离攻击测试通过")


def test_pns_attack():
    """测试PNS攻击"""
    print("\n" + "=" * 60)
    print("测试PNS攻击")
    print("=" * 60)
    
    n_pulses = 10000
    mean_photon = 0.5
    photon_numbers = np.random.poisson(mean_photon, n_pulses)
    alice_bases = np.random.randint(0, 2, n_pulses)
    alice_bits = np.random.randint(0, 2, n_pulses)
    
    # 统计多光子态比例
    multi_photon_ratio = np.mean(photon_numbers > 1)
    
    attack = PhotonNumberSplittingAttack(storage_efficiency=1.0)
    modified_photons, eve_info = attack.attack(photon_numbers, alice_bases, alice_bits)
    
    print(f"\n平均光子数: {mean_photon}")
    print(f"多光子态比例: {multi_photon_ratio*100:.2f}%")
    print(f"Eve信息比例: {eve_info*100:.2f}%")
    print(f"预期信息比例: ~{multi_photon_ratio*100:.2f}%")
    
    # Eve信息应主要来自多光子态
    assert abs(eve_info - multi_photon_ratio) < 0.05, "Eve信息应约等于多光子态比例"
    
    print("✓ PNS攻击测试通过")


def test_attack_factory():
    """测试攻击工厂函数"""
    print("\n" + "=" * 60)
    print("测试攻击工厂函数")
    print("=" * 60)
    
    attacks_to_test = [
        ('none', None),
        ('intercept_resend', InterceptResendAttack),
        ('beam_splitting', BeamSplittingAttack),
        ('pns', PhotonNumberSplittingAttack)
    ]
    
    for attack_type, expected_class in attacks_to_test:
        attack = get_attack(attack_type)
        
        if expected_class is None:
            assert attack is None, f"{attack_type}应返回None"
            print(f"\n{attack_type}: None ✓")
        else:
            assert isinstance(attack, expected_class), f"{attack_type}应返回{expected_class}"
            print(f"\n{attack_type}: {type(attack).__name__} ✓")
    
    print("✓ 攻击工厂测试通过")


def test_attack_strength():
    """测试攻击强度影响"""
    print("\n" + "=" * 60)
    print("测试攻击强度影响")
    print("=" * 60)
    
    n_pulses = 10000
    photon_numbers = np.random.poisson(0.5, n_pulses)
    alice_bases = np.random.randint(0, 2, n_pulses)
    alice_bits = np.random.randint(0, 2, n_pulses)
    
    strengths = [0.0, 0.3, 0.6, 1.0]
    
    print("\n截获-重发攻击强度测试:")
    for strength in strengths:
        attack = InterceptResendAttack(attack_strength=strength)
        _, eve_info = attack.attack(photon_numbers, alice_bases, alice_bits)
        print(f"  强度={strength:.1f} -> Eve信息={eve_info*100:.1f}%")


if __name__ == "__main__":
    test_intercept_resend()
    test_beam_splitting()
    test_pns_attack()
    test_attack_factory()
    test_attack_strength()
    
    print("\n" + "=" * 60)
    print("所有攻击测试通过!")
    print("=" * 60)
