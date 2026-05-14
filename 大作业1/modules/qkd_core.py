"""
QKD协议核心模块
实现BB84协议的完整流程
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import QKD_PARAMETERS


@dataclass
class PulseParameters:
    """脉冲参数"""
    pulse_rate: float  # 脉冲率 (Hz)
    mean_photon_number: float  # 平均光子数
    n_pulses: int  # 脉冲数


class BB84SatelliteQKD:
    """
    BB84卫星QKD仿真器
    
    功能:
        1. 光子发射（泊松分布）
        2. 信道传输仿真
        3. Bob测量仿真（包含误码）
        4. 筛选（Sifting）
        5. QBER计算
    """
    
    def __init__(self, 
                 channel_transmission: float,
                 pulse_rate: float = None,
                 mean_photon_number: float = None,
                 base_error_rate: float = 0.005):  # 基础光学误码率
        """
        初始化BB84仿真器
        
        Args:
            channel_transmission: 信道透射率 (0-1)
            pulse_rate: 脉冲率 (Hz)，默认1MHz
            mean_photon_number: 平均光子数，默认0.5
            base_error_rate: 基础光学误码率（偏振漂移、对准误差等）
        """
        self.channel_transmission = channel_transmission
        self.params = QKD_PARAMETERS
        self.base_error_rate = base_error_rate
        
        if pulse_rate is None:
            pulse_rate = self.params['pulse_rate']
        if mean_photon_number is None:
            mean_photon_number = self.params['mean_photon_number']
        
        self.pulse_rate = pulse_rate
        self.mean_photon_number = mean_photon_number
        
        # 存储仿真结果
        self.simulation_data = None
        
    def generate_alice_data(self, n_pulses: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Alice生成随机比特和基
        
        Args:
            n_pulses: 脉冲数量
            
        Returns:
            Tuple: (bits, bases, photon_numbers)
                - bits: 0或1
                - bases: 0=Z基(直), 1=X基(斜)
                - photon_numbers: 每脉冲光子数（泊松分布）
        """
        # 随机比特
        bits = np.random.randint(0, 2, n_pulses)
        
        # 随机基 (0=Z基, 1=X基)
        bases = np.random.randint(0, 2, n_pulses)
        
        # 每脉冲光子数（泊松分布）
        photon_numbers = np.random.poisson(self.mean_photon_number, n_pulses)
        
        return bits, bases, photon_numbers
    
    def simulate_transmission(self, 
                             photon_numbers: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        仿真光子通过信道的传输
        
        Args:
            photon_numbers: 每脉冲光子数
            
        Returns:
            Tuple: (arrived_photons, transmission_loss)
                - arrived_photons: 到达Bob的光子数
                - transmission_loss: 传输损耗标记
        """
        n_pulses = len(photon_numbers)
        
        # 每个光子独立传输
        arrived_photons = np.zeros(n_pulses, dtype=int)
        
        for i in range(n_pulses):
            n_photons = photon_numbers[i]
            if n_photons > 0:
                # 每个光子独立传输
                for _ in range(n_photons):
                    if np.random.random() < self.channel_transmission:
                        arrived_photons[i] += 1
        
        # 标记传输损耗
        transmission_loss = photon_numbers > arrived_photons
        
        return arrived_photons, transmission_loss
    
    def simulate_bob_measurement(self, 
                                 arrived_photons: np.ndarray,
                                 alice_bits: np.ndarray,
                                 alice_bases: np.ndarray,
                                 eve_attack_result: Dict = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Bob进行测量（包含误码）
        
        Args:
            arrived_photons: 到达的光子数
            alice_bits: Alice的比特
            alice_bases: Alice的基
            eve_attack_result: Eve攻击结果（包含引入的误码）
            
        Returns:
            Tuple: (bob_bases, bob_results, detector_clicks)
                - bob_bases: Bob选择的基
                - bob_results: 测量结果 (0/1)
                - detector_clicks: 探测器是否响应
        """
        n_pulses = len(arrived_photons)
        
        # Bob随机选择基
        bob_bases = np.random.randint(0, 2, n_pulses)
        
        # 测量结果
        bob_results = np.zeros(n_pulses, dtype=int)
        detector_clicks = np.zeros(n_pulses, dtype=bool)
        
        # 获取Eve攻击引入的误码（如果有）
        eve_error_mask = np.zeros(n_pulses, dtype=bool)
        if eve_attack_result and 'error_mask' in eve_attack_result:
            eve_error_mask = eve_attack_result['error_mask']
        
        for i in range(n_pulses):
            if arrived_photons[i] > 0:
                # 探测器响应概率
                detection_prob = self.params['detector_efficiency']
                
                # 暗计数
                dark_count_prob = self.params['detector_dark_count'] / self.pulse_rate
                
                # 是否探测到
                detected = False
                if np.random.random() < (1 - (1 - detection_prob) ** arrived_photons[i]):
                    detected = True
                    detector_clicks[i] = True
                elif np.random.random() < dark_count_prob:
                    # 暗计数
                    detected = True
                    detector_clicks[i] = True
                    
                if detected:
                    if bob_bases[i] == alice_bases[i]:
                        # 基匹配时的测量结果
                        # 正常情况下应该与Alice相同，但可能有误码
                        
                        # 基础光学误码
                        has_error = np.random.random() < self.base_error_rate
                        
                        # Eve攻击引入的误码
                        if eve_error_mask[i]:
                            has_error = True
                        
                        if has_error:
                            # 发生误码，结果翻转
                            bob_results[i] = 1 - alice_bits[i]
                        else:
                            # 无误码，结果正确
                            bob_results[i] = alice_bits[i]
                    else:
                        # 基不匹配，随机结果
                        bob_results[i] = np.random.randint(0, 2)
        
        return bob_bases, bob_results, detector_clicks
    
    def sifting(self,
                alice_bits: np.ndarray,
                alice_bases: np.ndarray,
                bob_bases: np.ndarray,
                bob_results: np.ndarray,
                detector_clicks: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        筛选过程：保留基匹配的比特
        
        Args:
            alice_bits: Alice的比特
            alice_bases: Alice的基
            bob_bases: Bob的基
            bob_results: Bob的测量结果
            detector_clicks: 探测器响应标记
            
        Returns:
            Tuple: (sifted_alice, sifted_bob)
                - sifted_alice: Alice的筛选后密钥
                - sifted_bob: Bob的筛选后密钥
        """
        # 选择基匹配且有探测的脉冲
        matching_indices = (alice_bases == bob_bases) & detector_clicks
        
        sifted_alice = alice_bits[matching_indices]
        sifted_bob = bob_results[matching_indices]
        
        return sifted_alice, sifted_bob
    
    def calculate_qber(self, 
                      sifted_alice: np.ndarray,
                      sifted_bob: np.ndarray) -> float:
        """
        计算量子误码率
        
        Args:
            sifted_alice: Alice的筛选密钥
            sifted_bob: Bob的筛选密钥
            
        Returns:
            float: QBER (0-1)
        """
        if len(sifted_alice) == 0:
            return 0.0
        
        errors = np.sum(sifted_alice != sifted_bob)
        qber = errors / len(sifted_alice)
        
        return qber
    
    def simulate_exchange(self, 
                         n_pulses: int = 10000,
                         eve_attack=None) -> Dict:
        """
        完整QKD交换仿真
        
        Args:
            n_pulses: 脉冲数量
            eve_attack: Eve攻击对象（可选）
            
        Returns:
            dict: 仿真结果
        """
        # Step 1: Alice生成数据
        alice_bits, alice_bases, photon_numbers = self.generate_alice_data(n_pulses)
        
        # Step 2: Eve攻击（如果有）
        eve_attack_result = None
        eve_info = 0.0
        
        if eve_attack is not None:
            photon_numbers, eve_info, eve_attack_result = eve_attack.attack_full(
                photon_numbers, alice_bases, alice_bits
            )
        
        # Step 3: 信道传输
        arrived_photons, transmission_loss = self.simulate_transmission(photon_numbers)
        
        # Step 4: Bob测量
        bob_bases, bob_results, detector_clicks = self.simulate_bob_measurement(
            arrived_photons, alice_bits, alice_bases, eve_attack_result
        )
        
        # Step 5: 筛选
        sifted_alice, sifted_bob = self.sifting(
            alice_bits, alice_bases, bob_bases, bob_results, detector_clicks
        )
        
        # Step 6: 计算QBER
        qber = self.calculate_qber(sifted_alice, sifted_bob)
        
        # 计算统计信息
        n_sifted = len(sifted_alice)
        raw_rate = np.sum(detector_clicks) / n_pulses * self.pulse_rate
        sifted_rate = n_sifted / n_pulses * self.pulse_rate
        
        # 存储结果
        result = {
            'n_pulses': n_pulses,
            'n_detections': int(np.sum(detector_clicks)),
            'n_sifted': n_sifted,
            'sifting_ratio': n_sifted / n_pulses if n_pulses > 0 else 0,
            'qber': qber,
            'qber_percent': qber * 100,
            'raw_rate': raw_rate,
            'sifted_rate': sifted_rate,
            'eve_info_ratio': eve_info,
            'alice_key': sifted_alice,
            'bob_key': sifted_bob
        }
        
        self.simulation_data = result
        return result
    
    def get_simulation_summary(self) -> str:
        """获取仿真结果摘要"""
        if self.simulation_data is None:
            return "尚未运行仿真"
        
        data = self.simulation_data
        summary = f"""
BB84仿真结果摘要:
==================
脉冲数: {data['n_pulses']:,}
探测事件: {data['n_detections']:,}
筛选后密钥长度: {data['n_sifted']:,}
筛选率: {data['sifting_ratio']*100:.2f}%
QBER: {data['qber_percent']:.2f}%
原始密钥率: {data['raw_rate']/1e3:.2f} kbps
筛选密钥率: {data['sifted_rate']/1e3:.2f} kbps
Eve信息比例: {data['eve_info_ratio']*100:.2f}%
"""
        return summary


def test_qkd_core():
    """测试QKD核心"""
    print("=" * 60)
    print("测试BB84 QKD核心")
    print("=" * 60)
    
    # 测试场景
    test_cases = [
        ("理想信道", 1.0),
        ("良好信道", 0.1),
        ("中等信道", 0.01),
        ("较差信道", 0.001),
    ]
    
    for name, transmission in test_cases:
        print(f"\n场景: {name} (透射率={transmission})")
        print("-" * 40)
        
        # 创建仿真器
        qkd = BB84SatelliteQKD(channel_transmission=transmission)
        
        # 运行仿真
        result = qkd.simulate_exchange(n_pulses=10000)
        
        print(f"  探测事件: {result['n_detections']}")
        print(f"  筛选密钥: {result['n_sifted']} bits")
        print(f"  QBER: {result['qber_percent']:.2f}%")
        print(f"  筛选密钥率: {result['sifted_rate']/1e3:.2f} kbps")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_qkd_core()
