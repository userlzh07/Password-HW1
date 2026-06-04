"""
隐私放大演示模块 - Gradio 集成代码片段

使用说明：
1. 将本文件中的代码片段复制到你的 app.py 中
2. 确保已导入 PrivacyAmplificationDemo 相关函数
3. 在创建 Gradio Interface 时，将 demo_tab 添加到界面中
"""

# ===================== 第一部分：导入（添加到 app.py 顶部） =====================

# 在 app.py 的其他 import 下方添加：
from modules.privacy_amp_demo import (
    PrivacyAmplificationDemo,
    create_privacy_amp_demo_html,
    create_info_theory_chart_data,
)


# ===================== 第二部分：添加到 QKDSimulationApp 类中 =====================

# 在 QKDSimulationApp.__init__ 中添加：
# self.pa_demo = PrivacyAmplificationDemo()

# 然后添加以下方法到 QKDSimulationApp 类：

def run_privacy_amp_demo(self, qber_percent: float, eve_percent: float, n_bits: int, seed: int):
    """
    运行隐私放大原理演示
    
    Args:
        qber_percent: QBER百分比
        eve_percent: Eve信息百分比
        n_bits: 密钥位数
        seed: 随机种子（0表示随机）
        
    Returns:
        (html, plotly_figure)
    """
    actual_seed = None if seed == 0 else seed
    
    # 生成HTML展示
    html = create_privacy_amp_demo_html(
        qber_percent=qber_percent,
        eve_percent=eve_percent,
        n_bits=n_bits,
        seed=actual_seed
    )
    
    # 生成信息论对比图
    chart_data = create_info_theory_chart_data(
        qber_percent=qber_percent,
        eve_percent=eve_percent,
        n_bits=n_bits,
        seed=actual_seed
    )
    
    # 创建Plotly图表
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_data['categories'],
        y=chart_data['values'],
        marker_color=chart_data['colors'],
        text=chart_data['values'],
        textposition='auto',
    ))
    fig.update_layout(
        title=f'密钥信息分布图 (效率: {chart_data["efficiency"]*100:.1f}%)',
        xaxis_title='',
        yaxis_title='比特数',
        template='plotly_white',
        height=400,
    )
    
    return html, fig


# ===================== 第三部分：创建演示Tab的界面代码 =====================

def create_privacy_amp_tab(app: QKDSimulationApp):
    """
    创建隐私放大演示Tab
    
    使用方式：在 app.py 构建 Gradio 界面的地方，将此 tab 加入 with gr.Blocks() 中：
    
        with gr.Blocks(...) as demo:
            # ... 其他 tabs ...
            
            with gr.Tab("🔐 隐私放大原理"):
                create_privacy_amp_tab(app)
    """
    
    gr.Markdown("""
    ## 隐私放大的信息论本质
    
    隐私放大（Privacy Amplification）是量子密钥分发的核心后处理步骤之一。
    即使 Eve 通过光束分离等攻击获取了部分信息，通信双方仍可通过**压缩密钥长度**，
    使 Eve 对最终密钥的信息量趋近于零。
    
    > **核心思想**：利用通用哈希函数将长串映射为短串，使得 Eve 的信息在压缩后不足以确定任何一位密钥。
    > 这类似于将"部分信息"通过压缩变为"无信息"。
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 参数设置")
            pa_qber = gr.Slider(
                minimum=0, maximum=20, value=3, step=0.5,
                label="量子误码率 QBER (%)"
            )
            pa_eve = gr.Slider(
                minimum=0, maximum=50, value=10, step=1,
                label="Eve 信息比例 (%)"
            )
            pa_bits = gr.Slider(
                minimum=16, maximum=64, value=32, step=8,
                label="展示密钥位数"
            )
            pa_seed = gr.Number(
                value=0, label="随机种子（0=随机）", precision=0
            )
            pa_btn = gr.Button("🔄 生成演示", variant="primary")
        
        with gr.Column(scale=2):
            pa_html = gr.HTML(label="密钥可视化")
    
    with gr.Row():
        pa_chart = gr.Plot(label="信息论分析")
    
    # 绑定事件
    pa_btn.click(
        fn=app.run_privacy_amp_demo,
        inputs=[pa_qber, pa_eve, pa_bits, pa_seed],
        outputs=[pa_html, pa_chart]
    )
    
    # 页面加载时自动运行一次
    pa_btn.click(
        fn=app.run_privacy_amp_demo,
        inputs=[pa_qber, pa_eve, pa_bits, pa_seed],
        outputs=[pa_html, pa_chart],
        queue=False
    )


# ===================== 第四部分：快速测试代码 =====================

if __name__ == "__main__":
    """
    独立运行此文件可快速预览隐私放大演示效果
    """
    import gradio as gr
    
    app = QKDSimulationApp()
    
    with gr.Blocks(title="隐私放大原理演示") as demo:
        gr.Markdown("# 🔐 隐私放大原理可视化")
        create_privacy_amp_tab(app)
    
    demo.launch()
