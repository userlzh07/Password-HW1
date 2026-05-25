"""
隐私放大原理演示模块
用于直观展示隐私放大的信息论本质：
"利用通用哈希函数将长串映射为短串，使Eve的信息不足以确定任何一位密钥"

可在Gradio中以HTML和图表形式展示
"""

import numpy as np
from typing import Dict, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def binary_entropy(x: float) -> float:
    """二元熵函数 H2(x) = -x*log2(x) - (1-x)*log2(1-x)"""
    if x <= 0 or x >= 1:
        return 0.0
    return -x * np.log2(x) - (1 - x) * np.log2(1 - x)


class PrivacyAmplificationDemo:
    """
    隐私放大原理演示器
    
    生成可视化的二进制密钥流，展示：
    1. 筛选后的原始密钥（标注Alice/Bob/Eve的信息分布）
    2. 隐私放大过程（随机线性组合 / Toeplitz矩阵直观表示）
    3. 最终安全密钥与信息论指标
    """
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)
        
        # HTML颜色标注
        self.colors = {
            'alice_bob': '#28A745',      # 绿色：只有Alice和Bob知道
            'eve_known': '#DC3545',       # 红色：Eve也知道
            'error_bit': '#FFC107',       # 黄色：Alice和Bob不一致（误码）
            'lost_bit': '#6C757D',        # 灰色：未探测/丢失
            'secure': '#007BFF',          # 蓝色：隐私放大后的安全位
            'mixed': '#6F42C1',           # 紫色：被混合的原始位
        }
    
    def generate_sifted_key(self, n: int = 48, 
                           qber: float = 0.05,
                           eve_info_ratio: float = 0.25) -> Dict:
        """
        生成一个模拟的筛选密钥场景
        
        Args:
            n: 筛选密钥长度（建议48，适合网页展示）
            qber: 量子误码率
            eve_info_ratio: Eve知道的信息比例（0-1）
            
        Returns:
            dict: 包含密钥和标注信息
        """
        # Alice的原始比特
        alice_bits = np.random.randint(0, 2, n)
        
        # Bob的比特：与Alice相同，但有一定误码
        bob_bits = alice_bits.copy()
        error_mask = np.random.random(n) < qber
        bob_bits[error_mask] = 1 - bob_bits[error_mask]
        
        # Eve知道的位：随机选择一部分
        # 在这些位上Eve知道Alice的比特值
        eve_known_mask = np.random.random(n) < eve_info_ratio
        
        # 构建每位的状态标签
        bit_status = []
        for i in range(n):
            if error_mask[i]:
                status = 'ERROR'  # Alice和Bob不一致
            elif eve_known_mask[i]:
                status = 'EVE_KNOWN'  # Eve也知道
            else:
                status = 'SECURE'  # 只有Alice和Bob知道
            bit_status.append(status)
        
        return {
            'n': n,
            'alice_bits': alice_bits,
            'bob_bits': bob_bits,
            'qber': qber,
            'eve_info_ratio': eve_info_ratio,
            'error_mask': error_mask,
            'eve_known_mask': eve_known_mask,
            'bit_status': bit_status,
            'n_errors': int(np.sum(error_mask)),
            'n_eve_known': int(np.sum(eve_known_mask)),
            'n_secure': n - int(np.sum(eve_known_mask | error_mask)),
        }
    
    def calculate_secure_length(self, n: int, qber: float, eve_info_ratio: float) -> int:
        """
        计算隐私放大后的安全密钥长度
        
        简化公式: m = n * (1 - 2*H2(QBER) - 2*tau)
        """
        h2_qber = binary_entropy(qber)
        leakage = 2 * eve_info_ratio
        ec_loss = 2 * h2_qber
        total_loss = leakage + ec_loss
        secure_ratio = max(0, 1 - total_loss)
        m = int(n * secure_ratio)
        return max(0, m)
    
    def amplify_demo(self, sifted_key: np.ndarray, 
                     target_length: int,
                     combination_size: int = 6) -> Dict:
        """
        执行可展示的隐私放大
        
        为了教学可视化，这里使用可控的随机线性组合，
        并记录每个输出位是由哪些输入位组合得到的
        
        Args:
            sifted_key: 筛选后的密钥（Alice的比特）
            target_length: 目标安全密钥长度
            combination_size: 每个输出位由多少个输入位XOR得到
            
        Returns:
            dict: 包含安全密钥和组合关系
        """
        n = len(sifted_key)
        if target_length <= 0 or n < target_length:
            return {
                'secure_key': np.array([]),
                'combinations': [],
                'target_length': 0,
            }
        
        secure_key = np.zeros(target_length, dtype=int)
        combinations = []
        
        for i in range(target_length):
            # 随机选择输入位（不重复选择同一位置太多次）
            size = min(combination_size, n)
            indices = np.random.choice(n, size=size, replace=False)
            
            # XOR组合
            secure_key[i] = np.bitwise_xor.reduce(sifted_key[indices])
            
            combinations.append({
                'output_index': i,
                'input_indices': sorted(indices.tolist()),
                'input_values': sifted_key[indices].tolist(),
                'output_value': int(secure_key[i]),
            })
        
        return {
            'secure_key': secure_key,
            'combinations': combinations,
            'target_length': target_length,
        }
    
    def render_key_html(self, bits: np.ndarray, 
                       status_list: list,
                       title: str = "密钥") -> str:
        """
        将密钥渲染为彩色HTML字符串
        
        Args:
            bits: 比特数组
            status_list: 每位状态列表（SECURE/EVE_KNOWN/ERROR）
            title: 标题
            
        Returns:
            str: HTML字符串
        """
        html = f'<div style="margin:10px 0;"><strong>{title}</strong><br>'
        html += '<div style="font-family:monospace;font-size:18px;letter-spacing:4px;margin:8px 0;">'
        
        for i, (bit, status) in enumerate(zip(bits, status_list)):
            color = self.colors.get({
                'SECURE': 'alice_bob',
                'EVE_KNOWN': 'eve_known',
                'ERROR': 'error_bit',
                'LOST': 'lost_bit',
                'MIXED': 'mixed',
            }.get(status, 'alice_bob'), '#333')
            
            # 添加tooltip显示索引
            html += f'<span title="位{i}: {status}" style="color:{color};font-weight:bold;">{bit}</span>'
        
        html += '</div></div>'
        return html
    
    def render_privacy_amplification_process(self, 
                                             sifted_data: Dict,
                                             amp_data: Dict) -> str:
        """
        渲染隐私放大过程的HTML展示
        
        展示每个输出位是如何由输入位XOR组合得到的
        """
        alice_bits = sifted_data['alice_bits']
        bit_status = sifted_data['bit_status']
        combinations = amp_data['combinations']
        
        # 只展示前几个组合（避免太长）
        show_count = min(8, len(combinations))
        
        html = '<div style="margin:15px 0;padding:15px;border:1px solid #dee2e6;border-radius:8px;background:#f8f9fa;">'
        html += '<h4>🔐 隐私放大过程（随机线性组合）</h4>'
        html += '<p style="color:#666;font-size:14px;margin-bottom:10px;">'
        html += '每个安全密钥位 = 随机选取的原始位进行 XOR 运算。Eve 即使知道部分原始位，'
        html += '由于不知道组合方式，也无法推断出任何一位安全密钥。<br>'
        html += '<span style="color:#999;font-size:12px;">'
        html += '注：组合位数 = '+str(show_count)+' 为演示参数。真实系统使用 Toeplitz 矩阵（每行含大量非零元），'
        html += '混淆度远高于此简化模型。</span></p>'
        
        for combo in combinations[:show_count]:
            out_idx = combo['output_index']
            in_indices = combo['input_indices']
            in_values = combo['input_values']
            out_val = combo['output_value']
            
            html += '<div style="margin:6px 0;font-family:monospace;font-size:15px;">'
            html += f'<span style="color:{self.colors["secure"]};font-weight:bold;">K\'{out_idx}</span> = '
            
            parts = []
            for idx, val in zip(in_indices, in_values):
                status = bit_status[idx]
                color = self.colors.get({
                    'SECURE': 'alice_bob',
                    'EVE_KNOWN': 'eve_known',
                    'ERROR': 'error_bit',
                }.get(status, 'alice_bob'), '#333')
                parts.append(f'<span style="color:{color};" title="位{idx} ({status})">{val}</span>')
            
            html += ' ⊕ '.join(parts)
            html += f' = <span style="color:{self.colors["secure"]};font-weight:bold;">{out_val}</span>'
            html += '</div>'
        
        if len(combinations) > show_count:
            html += f'<div style="color:#666;margin-top:8px;">... 共 {len(combinations)} 个组合（仅展示前 {show_count} 个）</div>'
        
        html += '</div>'
        return html
    
    def generate_info_theory_chart(self, sifted_data: Dict, 
                                   secure_length: int) -> Dict:
        """
        生成信息论对比数据（用于Plotly图表）
        
        返回条形图数据，展示：
        - 原始密钥长度
        - Eve知道的信息量（比特）
        - 误码导致的信息损失
        - 最终安全密钥长度
        """
        n = sifted_data['n']
        n_eve = sifted_data['n_eve_known']
        n_errors = sifted_data['n_errors']
        
        # 计算各项的熵/信息量
        # Eve的信息：她知道n_eve位，每位的信息是1 bit
        # 但实际上由于她不知道哪些位，信息论上更复杂，这里用简化模型
        
        categories = ['原始密钥<br>总长度', 'Eve知道<br>的位数', 'Alice/Bob<br>误码位数', 
                      '隐私放大<br>压缩损失', '最终安全<br>密钥长度']
        values = [
            n,
            n_eve,
            n_errors,
            max(0, n - secure_length - n_eve - n_errors),  # 其他压缩损失
            secure_length,
        ]
        colors = ['#6C757D', '#DC3545', '#FFC107', '#17A2B8', '#28A745']
        
        return {
            'categories': categories,
            'values': values,
            'colors': colors,
            'n': n,
            'secure_length': secure_length,
            'efficiency': secure_length / n if n > 0 else 0,
        }
    
    def run_full_demo(self, n: int = 48, qber: float = 0.05, 
                     eve_info_ratio: float = 0.25) -> Dict:
        """
        运行完整的隐私放大演示
        
        Args:
            n: 筛选密钥长度
            qber: 量子误码率
            eve_info_ratio: Eve信息比例
            
        Returns:
            dict: 包含所有可视化所需数据
        """
        # 1. 生成筛选密钥场景
        sifted = self.generate_sifted_key(n, qber, eve_info_ratio)
        
        # 2. 计算安全长度
        secure_length = self.calculate_secure_length(n, qber, eve_info_ratio)
        
        # 3. 执行隐私放大
        amp = self.amplify_demo(sifted['alice_bits'], secure_length)
        
        # 4. 生成HTML可视化
        # Alice视角的原始密钥
        alice_html = self.render_key_html(
            sifted['alice_bits'], sifted['bit_status'], 
            title="📤 Alice 的筛选密钥（原始）"
        )
        
        # Bob视角（带误码标注）
        bob_status = []
        for i in range(n):
            if sifted['error_mask'][i]:
                bob_status.append('ERROR')
            elif sifted['eve_known_mask'][i]:
                bob_status.append('EVE_KNOWN')
            else:
                bob_status.append('SECURE')
        
        bob_html = self.render_key_html(
            sifted['bob_bits'], bob_status,
            title="📥 Bob 的筛选密钥（含误码）"
        )
        
        # Eve视角（她只知道自己知道的位，其他显示为?）
        eve_bits = sifted['alice_bits'].copy()
        eve_display = []
        eve_status = []
        for i in range(n):
            if sifted['eve_known_mask'][i]:
                eve_display.append(str(eve_bits[i]))
                eve_status.append('EVE_KNOWN')
            else:
                eve_display.append('?')
                eve_status.append('LOST')
        
        eve_bits_arr = np.array([int(x) if x != '?' else -1 for x in eve_display])
        # 特殊处理：用-1表示未知，但render_key_html需要整数，我们单独处理
        eve_html = '<div style="margin:10px 0;"><strong>🕵️ Eve 知道的信息（? = 未知）</strong><br>'
        eve_html += '<div style="font-family:monospace;font-size:18px;letter-spacing:4px;margin:8px 0;">'
        for i, (val, status) in enumerate(zip(eve_display, eve_status)):
            color = self.colors['eve_known'] if status == 'EVE_KNOWN' else self.colors['lost_bit']
            eve_html += f'<span style="color:{color};font-weight:bold;">{val}</span>'
        eve_html += '</div></div>'
        
        # 安全密钥
        secure_key = amp['secure_key']
        secure_html = '<div style="margin:10px 0;"><strong>🔐 隐私放大后的安全密钥</strong><br>'
        secure_html += '<div style="font-family:monospace;font-size:18px;letter-spacing:4px;margin:8px 0;">'
        for bit in secure_key:
            secure_html += f'<span style="color:{self.colors["secure"]};font-weight:bold;">{bit}</span>'
        secure_html += '</div></div>'
        
        # 隐私放大过程
        process_html = self.render_privacy_amplification_process(sifted, amp)
        
        # 图例说明
        legend_html = '''
        <div style="margin:10px 0;font-size:14px;">
        <strong>图例：</strong>
        <span style="color:#28A745;font-weight:bold;">■</span> 仅Alice/Bob知道 
        <span style="color:#DC3545;font-weight:bold;">■</span> Eve也知道 
        <span style="color:#FFC107;font-weight:bold;">■</span> Alice/Bob不一致（误码）
        <span style="color:#6C757D;font-weight:bold;">■</span> 未知/丢失
        </div>
        '''
        
        # 信息论指标文本
        h2_qber = binary_entropy(qber)
        ec_loss = 2 * h2_qber
        eve_loss = 2 * eve_info_ratio
        total_loss = ec_loss + eve_loss
        secure_ratio_val = max(0, 1 - total_loss)
        
        theory_html = f'''
        <div style="margin:15px 0;padding:14px;border-left:4px solid #007BFF;background:#f8f9fa;color:#212529;border-radius:0 8px 8px 0;">
        <h4 style="color:#212529;margin-top:0;">📊 信息论分析</h4>
        <ul style="margin:5px 0;">
        <li>原始筛选密钥长度: <strong>{n}</strong> bit</li>
        <li>量子误码率 (QBER): <strong>{qber*100:.2f}%</strong></li>
        <li>二元熵 H₂(QBER): <strong>{h2_qber:.3f}</strong></li>
        <li>Eve 信息比例 (τ): <strong>{eve_info_ratio*100:.1f}%</strong> （约 {sifted['n_eve_known']} 位）</li>
        </ul>
        
        <div style="margin:12px 0;padding:10px;background:#e9ecef;border-radius:6px;font-family:monospace;font-size:13px;">
        <strong>安全密钥长度公式（GLLP 简化形式）：</strong><br>
        m = n × [1 − 2·H₂(QBER) − 2τ]<br><br>
        
        = {n} × [1 − 2×{h2_qber:.3f} − 2×{eve_info_ratio:.3f}]<br>
        = {n} × [1 − {ec_loss:.3f} − {eve_loss:.3f}]<br>
        = {n} × {secure_ratio_val:.3f}<br>
        = <strong>{secure_length}</strong> bit
        </div>
        
        <ul style="margin:5px 0;">
        <li>纠错信息损失: <strong>2×H₂(QBER) = {ec_loss:.3f}</strong> （{ec_loss*100:.1f}%）</li>
        <li>Eve 信息损失: <strong>2τ = {eve_loss:.3f}</strong> （{eve_loss*100:.1f}%）</li>
        <li>总损失比例: <strong>{total_loss:.3f}</strong> （{total_loss*100:.1f}%）</li>
        <li>最终安全密钥长度: <strong>{secure_length}</strong> bit</li>
        <li>密钥生成效率: <strong>{secure_ratio_val*100:.1f}%</strong></li>
        </ul>
        
        <p style="color:#444;font-size:13px;margin-top:10px;line-height:1.6;">
        <strong>公式来源与各项含义：</strong><br>
        本式来源于 <strong>GLLP (Gottesman-Lo-Lütkenhaus-Preskill, 2004)</strong> 安全性分析框架的简化形式。
        原始筛选密钥共 <strong>n</strong> 位，但其中三部分信息必须被"丢掉"才能保证安全：<br><br>
        
        ① <strong>2×H₂(QBER) — 纠错开销与纠错泄露消除</strong><br>
        Alice 与 Bob 的密钥存在 QBER 比例的误码，需通过公开信道交换约 <em>n·H₂(QBER)</em> 比特的奇偶校验信息进行纠错。
        但 Eve 也在监听公开信道！她听到了这些校验信息，因此额外需要再压缩 <em>n·H₂(QBER)</em> 比特来消除这份泄露。
        两项合计为 <strong>2·H₂(QBER)</strong>。<br><br>
        
        ② <strong>2τ — Eve 信息量消除</strong><br>
        Eve 通过攻击已掌握比例为 τ 的信息。隐私放大通过通用哈希函数将长串压缩为短串，
        使得 Eve 的已知信息在压缩后不足以确定任何一位安全密钥。
        系数 2 是保守估计（假设 Eve 信息需两倍长度来消除）。<br><br>
        
        💡 <strong>本质：</strong>隐私放大不是在"加密"密钥，而是在<strong>信息论意义上压缩掉 Eve 的信息优势</strong>。
        把 {n} 位压缩到 {secure_length} 位后，Eve 对她所知的 {sifted['n_eve_known']} 位原始信息的任何了解，
        都无法帮助她推断出这 {secure_length} 位安全密钥中的任何一位。
        </p>
        </div>
        '''
        
        # 组合完整HTML
        full_html = f'''
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        {legend_html}
        {alice_html}
        {eve_html}
        {bob_html}
        {secure_html}
        {process_html}
        {theory_html}
        </div>
        '''
        
        # 图表数据
        chart_data = self.generate_info_theory_chart(sifted, secure_length)
        
        return {
            'html': full_html,
            'chart_data': chart_data,
            'sifted': sifted,
            'amplification': amp,
            'secure_length': secure_length,
        }


# ============ 以下为可直接用于Gradio的便捷函数 ============

def create_privacy_amp_demo_html(qber_percent: float = 5.0,
                                  eve_percent: float = 25.0,
                                  n_bits: int = 48,
                                  seed: Optional[int] = None) -> str:
    """
    生成隐私放大演示的完整HTML（用于Gradio gr.HTML输出）
    
    Args:
        qber_percent: QBER百分比（如5.0表示5%）
        eve_percent: Eve信息百分比（如25.0表示25%）
        n_bits: 展示的密钥位数（建议48）
        seed: 随机种子（可选，用于固定展示）
        
    Returns:
        str: HTML字符串
    """
    demo = PrivacyAmplificationDemo(seed=seed)
    result = demo.run_full_demo(
        n=n_bits,
        qber=qber_percent / 100,
        eve_info_ratio=eve_percent / 100
    )
    return result['html']


def create_info_theory_chart_data(qber_percent: float = 5.0,
                                   eve_percent: float = 25.0,
                                   n_bits: int = 48,
                                   seed: Optional[int] = None) -> Dict:
    """
    生成信息论对比图表数据（用于Plotly）
    
    Returns:
        dict: 包含categories, values, colors等
    """
    demo = PrivacyAmplificationDemo(seed=seed)
    result = demo.run_full_demo(
        n=n_bits,
        qber=qber_percent / 100,
        eve_info_ratio=eve_percent / 100
    )
    return result['chart_data']
