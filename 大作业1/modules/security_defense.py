"""
安全防御与决策模块
实现隐私放大、诱骗态协议和安全决策引擎
"""

import numpy as np
from typing import Dict, List, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import QKD_PARAMETERS, ATTACK_TYPES


class PrivacyAmplification:
    """
    隐私放大模块
    
    功能:
        1. 根据Eve的信息比例计算安全密钥长度
        2. 实现隐私放大算法（Toeplitz矩阵方法）
    """
    
    def __init__(self, security_parameter: float = None):
        """
        初始化隐私放大
        
        Args:
            security_parameter: 安全参数 ε
        """
        if security_parameter is None:
            security_parameter = QKD_PARAMETERS['security_parameter']
        self.security_parameter = security_parameter
        
    def calculate_secure_length(self,
                               n_sifted: int,
                               qber: float,
                               eve_info_ratio: float) -> int:
        """
        计算安全密钥长度（适用于短时仿真）
        
        简化公式: m = n × (1 - 2H2(QBER) - 2τ) 
        
        注意：省略了安全参数修正项（适用于单次短时仿真）
        
        Args:
            n_sifted: 筛选后密钥长度
            qber: 量子误码率
            eve_info_ratio: Eve信息比例
            
        Returns:
            int: 安全密钥长度
        """
        if n_sifted == 0 or qber >= QKD_PARAMETERS['max_qber']:
            return 0
        
        # 二元熵函数 H2(x) = -x*log2(x) - (1-x)*log2(1-x)
        def binary_entropy(x):
            if x <= 0 or x >= 1:
                return 0
            return -x * np.log2(x) - (1 - x) * np.log2(1 - x)
        
        # Eve信息导致的密钥损失（保守估计2倍）
        leakage = 2 * eve_info_ratio
        
        # 纠错损失（2倍QBER熵，用于隐私放大）
        error_correction_loss = 2 * binary_entropy(qber)
        
        # 总损失比例
        total_loss_ratio = leakage + error_correction_loss
        
        # 安全密钥比例（不低于0）
        secure_ratio = max(0, 1 - total_loss_ratio)
        
        # 安全密钥长度（短时仿真省略epsilon修正项）
        secure_length = int(n_sifted * secure_ratio)
        
        return max(0, secure_length)
    
    def amplify(self,
               sifted_key: np.ndarray,
               target_length: int) -> np.ndarray:
        """
        执行隐私放大（简化版）
        
        实际应使用Toeplitz矩阵或通用哈希函数
        这里使用简化的随机子集方法
        
        Args:
            sifted_key: 筛选后的密钥
            target_length: 目标安全密钥长度
            
        Returns:
            np.ndarray: 安全密钥
        """
        if target_length <= 0 or len(sifted_key) < target_length:
            return np.array([])
        
        # 简化方法：随机选择位并进行XOR压缩
        # 实际应使用Toeplitz矩阵
        n = len(sifted_key)
        
        # 随机Toeplitz矩阵模拟
        # 简化为随机线性组合
        secure_key = np.zeros(target_length, dtype=int)
        
        for i in range(target_length):
            # 随机选择一些位进行XOR
            indices = np.random.choice(n, size=min(n, 10), replace=False)
            secure_key[i] = np.bitwise_xor.reduce(sifted_key[indices])
        
        return secure_key


class DecoyStateProtocol:
    """
    诱骗态协议模块
    
    功能:
        1. 生成信号态和诱骗态脉冲序列
        2. 检测PNS攻击
        3. 计算单光子和多光子贡献
    """
    
    def __init__(self):
        self.signal_intensity = 0.5    # 信号态强度
        self.decoy_intensity = 0.1     # 诱骗态强度
        self.vacuum_intensity = 0.0    # 真空态强度
        
    def generate_pulse_sequence(self,
                                n_pulses: int,
                                signal_ratio: float = 0.7,
                                decoy_ratio: float = 0.2) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成诱骗态脉冲序列
        
        Args:
            n_pulses: 总脉冲数
            signal_ratio: 信号态比例
            decoy_ratio: 诱骗态比例
            
        Returns:
            Tuple: (intensities, pulse_types)
                - intensities: 每个脉冲的强度
                - pulse_types: 脉冲类型 (0=信号, 1=诱骗, 2=真空)
        """
        intensities = np.zeros(n_pulses)
        pulse_types = np.zeros(n_pulses, dtype=int)
        
        # 随机分配脉冲类型
        rand_vals = np.random.random(n_pulses)
        
        # 信号态
        signal_mask = rand_vals < signal_ratio
        intensities[signal_mask] = self.signal_intensity
        pulse_types[signal_mask] = 0
        
        # 诱骗态
        decoy_mask = (rand_vals >= signal_ratio) & (rand_vals < signal_ratio + decoy_ratio)
        intensities[decoy_mask] = self.decoy_intensity
        pulse_types[decoy_mask] = 1
        
        # 真空态
        vacuum_mask = rand_vals >= signal_ratio + decoy_ratio
        intensities[vacuum_mask] = self.vacuum_intensity
        pulse_types[vacuum_mask] = 2
        
        return intensities, pulse_types
    
    def detect_pns_attack(self,
                         signal_yield: float,
                         decoy_yield: float,
                         vacuum_yield: float) -> Dict:
        """
        检测PNS攻击
        
        原理:
            在PNS攻击下，信号态和诱骗态的产额比会异常
            
        Args:
            signal_yield: 信号态产额 (探测概率)
            decoy_yield: 诱骗态产额
            vacuum_yield: 真空态产额 (背景噪声)
            
        Returns:
            dict: 检测结果
        """
        # 理论产额计算
        # 信号态: Y_signal = Y0 + 1 - exp(-μ_signal × η)
        # 诱骗态: Y_decoy = Y0 + 1 - exp(-μ_decoy × η)
        
        # 移除背景噪声
        signal_net = max(0, signal_yield - vacuum_yield)
        decoy_net = max(0, decoy_yield - vacuum_yield)
        
        # 计算产额比
        if decoy_net > 0:
            yield_ratio = signal_net / decoy_net
            expected_ratio = self.signal_intensity / self.decoy_intensity
        else:
            yield_ratio = float('inf')
            expected_ratio = 5.0
        
        # 判断是否有攻击
        # 正常情况下 yield_ratio ≈ expected_ratio
        # PNS攻击下 yield_ratio > expected_ratio
        threshold = 1.2 * expected_ratio  # 20%容差
        
        pns_detected = yield_ratio > threshold
        
        # 估计多光子比例
        # 简化的估计方法
        if signal_yield > 0:
            multi_photon_fraction = max(0, (yield_ratio - expected_ratio) / yield_ratio)
        else:
            multi_photon_fraction = 0.0
        
        return {
            'pns_detected': pns_detected,
            'signal_yield': signal_yield,
            'decoy_yield': decoy_yield,
            'vacuum_yield': vacuum_yield,
            'yield_ratio': yield_ratio,
            'expected_ratio': expected_ratio,
            'multi_photon_fraction': multi_photon_fraction,
            'confidence': min(1.0, (yield_ratio - expected_ratio) / expected_ratio)
        }
    
    def calculate_single_photon_bounds(self,
                                      signal_gain: float,
                                      decoy_gain: float,
                                      signal_qber: float,
                                      decoy_qber: float) -> Dict:
        """
        计算单光子贡献的上下界
        
        Args:
            signal_gain: 信号态总增益
            decoy_gain: 诱骗态总增益
            signal_qber: 信号态误码率
            decoy_qber: 诱骗态误码率
            
        Returns:
            dict: 单光子参数估计
        """
        # GLLP分析中的简化公式
        # Q1 >= (μ^2 × exp(-μ) / (μ × μ')) × (Q_μ × exp(μ') - Q_μ' × exp(μ))
        
        mu = self.signal_intensity
        nu = self.decoy_intensity
        
        # 单光子增益下界（简化）
        if mu > nu:
            q1_lower = (mu * np.exp(-mu) / (mu - nu)) * (signal_gain * np.exp(nu) - decoy_gain * np.exp(mu))
        else:
            q1_lower = 0.0
        
        q1_lower = max(0, q1_lower)
        
        # 单光子误码率上界（简化）
        e1_upper = signal_qber  # 保守估计
        
        return {
            'q1_lower': q1_lower,
            'e1_upper': e1_upper,
            'signal_intensity': mu,
            'decoy_intensity': nu
        }


class SecurityDecisionEngine:
    """
    安全决策引擎
    
    功能:
        1. 根据QBER、Eve信息、密钥率等做出安全决策
        2. 推荐防御策略
        3. 判断通信是否安全可行
    """
    
    def __init__(self):
        self.params = QKD_PARAMETERS
        self.thresholds = {
            'max_qber': QKD_PARAMETERS['max_qber'],
            'min_photon_rate': QKD_PARAMETERS['min_photon_rate'],
            'max_eve_info': QKD_PARAMETERS['max_eve_info']
        }
        
    def make_decision(self,
                     qber: float,
                     photon_rate: float,
                     eve_info: float,
                     n_sifted: int) -> Dict:
        """
        做出安全决策
        
        Args:
            qber: 量子误码率
            photon_rate: 光子率 (Hz)
            eve_info: Eve信息比例
            n_sifted: 筛选后密钥长度
            
        Returns:
            dict: 决策结果
        """
        decision = {
            'feasible': True,
            'warnings': [],
            'recommendations': [],
            'abort_reasons': []
        }
        
        # 检查QBER
        if qber > self.thresholds['max_qber']:
            decision['feasible'] = False
            decision['abort_reasons'].append(
                f"QBER ({qber*100:.2f}%) 超过阈值 ({self.thresholds['max_qber']*100:.1f}%)"
            )
        elif qber > 0.08:
            decision['warnings'].append("QBER偏高，可能存在攻击或信道恶化")
            decision['recommendations'].append("建议启用隐私放大或检查信道状态")
        
        # 检查光子率
        if photon_rate < self.thresholds['min_photon_rate']:
            decision['feasible'] = False
            decision['abort_reasons'].append(
                f"光子率 ({photon_rate:.1f} Hz) 低于阈值 ({self.thresholds['min_photon_rate']} Hz)"
            )
        elif photon_rate < 1000:
            decision['warnings'].append("光子率偏低，通信效率可能受限")
        
        # 检查Eve信息
        if eve_info > self.thresholds['max_eve_info']:
            decision['warnings'].append("检测到高Eve信息泄露")
            decision['recommendations'].append("强烈建议启用诱骗态协议")
            
            if eve_info > 0.5:
                decision['feasible'] = False
                decision['abort_reasons'].append("Eve信息过多，无法保证安全")
        
        # 检查密钥长度
        if n_sifted < 100:
            decision['warnings'].append("密钥长度过短，统计误差可能较大")
        
        # 综合评估
        if decision['feasible']:
            decision['security_level'] = self._assess_security_level(
                qber, eve_info, photon_rate
            )
        else:
            decision['security_level'] = 'INSECURE'
        
        return decision
    
    def _assess_security_level(self, qber: float, eve_info: float, photon_rate: float) -> str:
        """评估安全等级"""
        score = 100
        
        # QBER扣分
        score -= (qber / self.thresholds['max_qber']) * 30
        
        # Eve信息扣分
        score -= (eve_info / self.thresholds['max_eve_info']) * 40
        
        # 光子率扣分
        score -= max(0, (1 - photon_rate / 10000)) * 30
        
        if score >= 80:
            return 'HIGH'
        elif score >= 60:
            return 'MEDIUM'
        elif score >= 40:
            return 'LOW'
        else:
            return 'CRITICAL'
    
    def recommend_defense(self,
                         attack_detected: str = None,
                         qber: float = 0.0,
                         eve_info: float = 0.0) -> List[str]:
        """
        推荐防御策略
        
        Args:
            attack_detected: 检测到的攻击类型
            qber: 当前QBER
            eve_info: Eve信息比例
            
        Returns:
            List[str]: 防御建议列表
        """
        recommendations = []
        
        if attack_detected == 'pns':
            recommendations.append("启用诱骗态协议")
            recommendations.append("使用多个诱骗强度")
            recommendations.append("降低信号态强度")
        elif attack_detected == 'intercept_resend':
            recommendations.append("监控QBER异常升高")
            recommendations.append("缩短密钥长度，提高隐私放大强度")
        elif attack_detected == 'beam_splitting':
            recommendations.append("启用隐私放大")
            recommendations.append("使用参量下转换光源")
        
        if qber > 0.05:
            recommendations.append("执行误码纠错")
        
        if eve_info > 0.1:
            recommendations.append("启用隐私放大")
        
        if not recommendations:
            recommendations.append("当前参数正常，继续监控")
        
        return recommendations


class SecurityAnalyzer:
    """
    安全分析器（整合所有安全功能）
    """
    
    def __init__(self):
        self.privacy_amp = PrivacyAmplification()
        self.decoy = DecoyStateProtocol()
        self.decision = SecurityDecisionEngine()
        
    def full_security_analysis(self,
                              qkd_result: Dict,
                              attack_type: str = 'none') -> Dict:
        """
        完整安全分析
        
        Args:
            qkd_result: QKD仿真结果
            attack_type: 攻击类型
            
        Returns:
            dict: 完整安全分析结果
        """
        # 基础参数
        n_sifted = qkd_result['n_sifted']
        qber = qkd_result['qber']
        eve_info = qkd_result.get('eve_info_ratio', 0.0)
        sifted_rate = qkd_result['sifted_rate']
        
        # 安全决策
        decision = self.decision.make_decision(
            qber, sifted_rate, eve_info, n_sifted
        )
        
        # 隐私放大
        secure_length = self.privacy_amp.calculate_secure_length(
            n_sifted, qber, eve_info
        )
        
        # 安全密钥率
        secret_key_rate = secure_length / n_sifted * sifted_rate if n_sifted > 0 else 0
        
        # 防御建议
        recommendations = self.decision.recommend_defense(
            attack_type, qber, eve_info
        )
        
        return {
            'feasible': decision['feasible'],
            'security_level': decision['security_level'],
            'warnings': decision['warnings'],
            'recommendations': recommendations,
            'abort_reasons': decision.get('abort_reasons', []),
            'original_key_length': n_sifted,
            'secure_key_length': secure_length,
            'privacy_amplification_ratio': secure_length / n_sifted if n_sifted > 0 else 0,
            'secret_key_rate': secret_key_rate,
            'secret_key_rate_kbps': secret_key_rate / 1000
        }


def test_security_defense():
    """测试安全防御模块"""
    print("=" * 60)
    print("测试安全防御模块")
    print("=" * 60)
    
    # 测试隐私放大
    print("\n1. 隐私放大测试")
    print("-" * 40)
    
    pa = PrivacyAmplification()
    
    test_cases = [
        (10000, 0.03, 0.0),   # 理想情况
        (10000, 0.05, 0.1),   # 轻微攻击
        (10000, 0.08, 0.2),   # 中等攻击
        (10000, 0.12, 0.3),   # 严重攻击
    ]
    
    for n, qber, eve_info in test_cases:
        secure_len = pa.calculate_secure_length(n, qber, eve_info)
        print(f"  QBER={qber*100:.1f}%, Eve_info={eve_info*100:.1f}% -> "
              f"安全密钥: {secure_len} bits")
    
    # 测试诱骗态
    print("\n2. 诱骗态协议测试")
    print("-" * 40)
    
    decoy = DecoyStateProtocol()
    
    # 模拟有攻击和无攻击的情况
    test_yields = [
        (0.5, 0.2, 0.01),   # 无攻击
        (0.5, 0.15, 0.01),  # 轻微PNS
        (0.5, 0.10, 0.01),  # 严重PNS
    ]
    
    for sig_y, dec_y, vac_y in test_yields:
        result = decoy.detect_pns_attack(sig_y, dec_y, vac_y)
        status = "攻击!" if result['pns_detected'] else "正常"
        print(f"  信号={sig_y:.2f}, 诱骗={dec_y:.2f} -> "
              f"产额比={result['yield_ratio']:.2f} ({status})")
    
    # 测试决策引擎
    print("\n3. 安全决策测试")
    print("-" * 40)
    
    engine = SecurityDecisionEngine()
    
    test_scenarios = [
        (0.03, 5000, 0.0),   # 正常
        (0.10, 5000, 0.2),   # 高QBER
        (0.05, 50, 0.0),     # 低光子率
        (0.05, 5000, 0.4),   # 高Eve信息
    ]
    
    for qber, rate, eve in test_scenarios:
        decision = engine.make_decision(qber, rate, eve, 10000)
        status = "可行" if decision['feasible'] else "不可行"
        print(f"  QBER={qber*100:.0f}%, rate={rate}, Eve={eve*100:.0f}% -> "
              f"{status} (等级: {decision['security_level']})")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_security_defense()
