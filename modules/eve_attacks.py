"""
Eve攻击模拟模块
实现三类典型攻击：截获-重发、光束分离、光子数分离
"""

import numpy as np
from typing import Dict, Tuple
from abc import ABC, abstractmethod
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import QKD_PARAMETERS


class EveAttack(ABC):
    """
    Eve攻击基类
    
    所有攻击类型都继承此类
    """
    
    def __init__(self, attack_strength: float = 0.5):
        """
        初始化攻击
        
        Args:
            attack_strength: 攻击强度 (0-1)
        """
        self.attack_strength = attack_strength
        self.name = "Base Attack"
        self.description = "Base attack class"
        
    @abstractmethod
    def attack_full(self, 
                   photon_numbers: np.ndarray,
                   alice_bases: np.ndarray,
                   alice_bits: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        执行攻击（完整版，返回误码信息）
        
        Args:
            photon_numbers: 每脉冲光子数
            alice_bases: Alice的基
            alice_bits: Alice的比特
            
        Returns:
            Tuple: (modified_photon_numbers, eve_info_ratio, attack_result)
                - modified_photon_numbers: 修改后的光子数
                - eve_info_ratio: Eve信息比例
                - attack_result: 包含误码掩码等信息
        """
        pass
    
    def get_attack_info(self) -> Dict:
        """获取攻击信息"""
        return {
            'name': self.name,
            'description': self.description,
            'strength': self.attack_strength
        }


class InterceptResendAttack(EveAttack):
    """
    截获-重发攻击 (Intercept-Resend)
    
    原理:
        Eve随机选择基测量光子，然后重新发送她测量的结果。
        当Eve的基与Alice不同时，会引入25%的误码。
        当Eve的基与Alice一致时，不引入误码。
        平均引入25%误码。
    """
    
    def __init__(self, attack_strength: float = 0.5):
        super().__init__(attack_strength)
        self.name = "Intercept-Resend"
        self.description = "Eve截获并重发光子，引入25%误码"
        self.introduced_qber = 0.25
        
    def attack_full(self, 
                   photon_numbers: np.ndarray,
                   alice_bases: np.ndarray,
                   alice_bits: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        执行截获-重发攻击
        
        当Eve的基与Alice不匹配时，有50%概率发送错误比特，
        导致Bob测量时引入25%误码（基匹配情况下）。
        """
        n_pulses = len(photon_numbers)
        
        # Eve选择要攻击的脉冲
        attack_mask = np.random.random(n_pulses) < self.attack_strength
        
        # Eve随机选择基
        eve_bases = np.random.randint(0, 2, n_pulses)
        
        # 基匹配标记
        bases_match = (eve_bases == alice_bases)
        
        # 计算误码掩码
        # 当Eve攻击且基不匹配时：
        # - Eve随机猜测比特（50%正确）
        # - 如果猜错，重发的光子态错误
        # - Bob基匹配测量时，有50%概率得到错误结果
        # 所以基不匹配的攻击引入50%误码
        # 平均误码 = P(攻击) × P(基不匹配|Eve) × 0.5 = 0.5 × 0.5 × 0.5 = 0.25
        
        error_mask = np.zeros(n_pulses, dtype=bool)
        
        # 被攻击且基不匹配的脉冲
        mismatched_attack = attack_mask & (~bases_match)
        
        # Eve随机猜测，猜错的概率50%
        eve_wrong_guess = np.random.random(n_pulses) < 0.5
        
        # 只有当Eve猜错且重发时，才引入误码
        error_mask = mismatched_attack & eve_wrong_guess
        
        # Eve信息比例
        # 基匹配时：Eve知道完整信息
        # 基不匹配时：Eve有50%概率知道正确信息
        eve_info_per_pulse = np.where(
            attack_mask,
            np.where(bases_match, 1.0, 0.5),
            0.0
        )
        
        # 多光子态增加Eve的信息获取
        multi_photon = photon_numbers > 1
        eve_info_per_pulse = np.where(
            multi_photon & attack_mask,
            np.minimum(eve_info_per_pulse * 1.5, 1.0),
            eve_info_per_pulse
        )
        
        eve_info_ratio = np.mean(eve_info_per_pulse)
        
        # 计算理论QBER（仅在基匹配情况下）
        # 实际QBER还取决于Bob选择的基
        theoretical_qber = np.sum(error_mask) / np.sum(attack_mask) * 0.5 if np.sum(attack_mask) > 0 else 0
        
        attack_result = {
            'error_mask': error_mask,
            'attack_mask': attack_mask,
            'eve_bases': eve_bases,
            'bases_match': bases_match,
            'theoretical_qber': theoretical_qber
        }
        
        return photon_numbers, eve_info_ratio, attack_result


class BeamSplittingAttack(EveAttack):
    """
    光束分离攻击 (Beam-Splitting)
    
    原理:
        Eve使用分束器分离部分光强进行测量，其余部分转发给Bob。
        这种攻击不引入误码，但Eve获得部分信息。
        对多光子态特别有效。
    """
    
    def __init__(self, split_ratio: float = 0.3):
        """
        初始化光束分离攻击
        
        Args:
            split_ratio: 分光比例 (0-1)，默认30%
        """
        super().__init__(split_ratio)
        self.name = "Beam-Splitting"
        self.description = "Eve分离部分光束，不引入误码但泄露信息"
        self.split_ratio = split_ratio
        
    def attack_full(self,
                   photon_numbers: np.ndarray,
                   alice_bases: np.ndarray,
                   alice_bits: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        执行光束分离攻击
        
        Eve分离split_ratio比例的光子，不引入误码。
        """
        n_pulses = len(photon_numbers)
        
        # Eve分离部分光子
        photons_to_eve = np.random.binomial(photon_numbers, self.split_ratio)
        photons_to_bob = photon_numbers - photons_to_eve
        
        # Eve的信息获取
        # 对于每个被分离的光子，Eve有概率获得信息
        # 如果分离到至少一个光子，Eve可以测量
        eve_can_measure = photons_to_eve > 0
        
        # Eve随机选择基测量
        eve_bases = np.random.randint(0, 2, n_pulses)
        bases_match = (eve_bases == alice_bases)
        
        # Eve信息：能测量且基匹配时知道信息
        eve_info_per_pulse = np.where(
            eve_can_measure & bases_match,
            1.0,
            np.where(eve_can_measure, 0.5, 0.0)
        )
        
        eve_info_ratio = np.mean(eve_info_per_pulse)
        
        # 光束分离不引入误码
        error_mask = np.zeros(n_pulses, dtype=bool)
        
        attack_result = {
            'error_mask': error_mask,
            'photons_to_eve': photons_to_eve,
            'photons_to_bob': photons_to_bob,
            'eve_can_measure': eve_can_measure
        }
        
        return photons_to_bob, eve_info_ratio, attack_result


class PhotonNumberSplittingAttack(EveAttack):
    """
    光子数分离攻击 (PNS - Photon Number Splitting)
    
    原理:
        Eve测量光子数，对多光子态分离一个光子保存，
        其余转发给Bob。之后利用Alice和Bob公开的信息
        确定基，从而无误差获取信息。
        这是针对弱脉冲光源的最强攻击。
    """
    
    def __init__(self, storage_efficiency: float = 1.0):
        """
        初始化PNS攻击
        
        Args:
            storage_efficiency: 量子存储效率 (0-1)
        """
        super().__init__(storage_efficiency)
        self.name = "Photon Number Splitting (PNS)"
        self.description = "针对弱脉冲光源，获取多光子态信息"
        self.storage_efficiency = storage_efficiency
        
    def attack_full(self,
                   photon_numbers: np.ndarray,
                   alice_bases: np.ndarray,
                   alice_bits: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        执行PNS攻击
        
        Eve从多光子态分离一个光子存储，不引入误码。
        """
        n_pulses = len(photon_numbers)
        
        # 识别多光子态
        multi_photon = photon_numbers > 1
        
        # Eve从多光子态分离一个光子
        photons_to_bob = np.where(
            multi_photon,
            photon_numbers - 1,
            photon_numbers
        )
        
        # Eve获取的信息
        # 多光子态：Eve分离一个光子，基匹配后可以完全获得信息
        # 单光子态：Eve无法攻击（不拦截）
        
        # Eve随机选择基
        eve_bases = np.random.randint(0, 2, n_pulses)
        bases_match = (eve_bases == alice_bases)
        
        # 多光子态且基匹配时，Eve获得完整信息
        eve_info_per_pulse = np.where(
            multi_photon & bases_match,
            self.storage_efficiency,
            np.where(multi_photon, 0.5 * self.storage_efficiency, 0.0)
        )
        
        eve_info_ratio = np.mean(eve_info_per_pulse)
        
        # PNS攻击不引入误码
        error_mask = np.zeros(n_pulses, dtype=bool)
        
        attack_result = {
            'error_mask': error_mask,
            'multi_photon': multi_photon,
            'eve_bases': eve_bases,
            'bases_match': bases_match
        }
        
        return photons_to_bob, eve_info_ratio, attack_result


class CombinedAttack(EveAttack):
    """
    组合攻击
    
    结合多种攻击方式
    """
    
    def __init__(self, attacks: list, weights: list = None):
        """
        初始化组合攻击
        
        Args:
            attacks: 攻击对象列表
            weights: 攻击权重列表
        """
        super().__init__(1.0)
        self.name = "Combined Attack"
        self.description = "多种攻击的组合"
        self.attacks = attacks
        
        if weights is None:
            weights = [1.0 / len(attacks)] * len(attacks)
        self.weights = weights
        
    def attack_full(self,
                   photon_numbers: np.ndarray,
                   alice_bases: np.ndarray,
                   alice_bits: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """执行组合攻击"""
        current_photons = photon_numbers.copy()
        total_eve_info = 0.0
        combined_error_mask = np.zeros(len(photon_numbers), dtype=bool)
        
        for attack, weight in zip(self.attacks, self.weights):
            current_photons, eve_info, attack_result = attack.attack_full(
                current_photons, alice_bases, alice_bits
            )
            total_eve_info += weight * eve_info
            
            # 合并误码掩码
            if 'error_mask' in attack_result:
                combined_error_mask |= attack_result['error_mask']
        
        final_result = {
            'error_mask': combined_error_mask
        }
        
        return current_photons, total_eve_info, final_result


def get_attack(attack_type: str, **kwargs) -> EveAttack:
    """
    工厂函数：获取指定类型的攻击对象
    
    Args:
        attack_type: 攻击类型
            - 'none': 无攻击
            - 'intercept_resend': 截获-重发
            - 'beam_splitting': 光束分离
            - 'pns': 光子数分离
        **kwargs: 攻击参数
        
    Returns:
        EveAttack: 攻击对象
    """
    attack_map = {
        'none': None,
        'intercept_resend': InterceptResendAttack,
        'beam_splitting': BeamSplittingAttack,
        'pns': PhotonNumberSplittingAttack
    }
    
    attack_class = attack_map.get(attack_type)
    
    if attack_class is None:
        return None
    
    return attack_class(**kwargs)


def test_eve_attacks():
    """测试Eve攻击"""
    print("=" * 60)
    print("测试Eve攻击模块")
    print("=" * 60)
    
    # 生成测试数据
    n_pulses = 10000
    mean_photon = 0.5
    
    alice_bits = np.random.randint(0, 2, n_pulses)
    alice_bases = np.random.randint(0, 2, n_pulses)
    photon_numbers = np.random.poisson(mean_photon, n_pulses)
    
    print(f"\n测试数据: {n_pulses} 个脉冲")
    print(f"平均光子数: {mean_photon}")
    print(f"多光子态比例: {np.mean(photon_numbers > 1)*100:.2f}%")
    
    # 测试各种攻击
    attacks = [
        ("无攻击", None),
        ("截获-重发 (50%)", InterceptResendAttack(0.5)),
        ("截获-重发 (100%)", InterceptResendAttack(1.0)),
        ("光束分离 (30%)", BeamSplittingAttack(0.3)),
        ("光束分离 (50%)", BeamSplittingAttack(0.5)),
        ("PNS攻击", PhotonNumberSplittingAttack(1.0)),
    ]
    
    print("\n攻击效果分析:")
    print("-" * 60)
    
    for name, attack in attacks:
        if attack is None:
            print(f"\n{name}: 无攻击")
            continue
        
        modified_photons, eve_info, result = attack.attack_full(
            photon_numbers, alice_bases, alice_bits
        )
        
        print(f"\n{name}:")
        print(f"  Eve信息比例: {eve_info*100:.2f}%")
        print(f"  Bob接收平均光子: {np.mean(modified_photons):.3f}")
        if 'error_mask' in result:
            error_rate = np.mean(result['error_mask'])
            print(f"  引入误码比例: {error_rate*100:.2f}%")
        if 'theoretical_qber' in result:
            print(f"  理论QBER贡献: {result['theoretical_qber']*100:.2f}%")


if __name__ == "__main__":
    test_eve_attacks()
