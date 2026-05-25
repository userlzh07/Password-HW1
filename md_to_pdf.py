# -*- coding: utf-8 -*-
from fpdf import FPDF
import re

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # 添加中文字体（使用系统自带字体）
        # 尝试常见中文字体路径
        import os
        
        # Windows 系统字体路径
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/simkai.ttf",  # 楷体
        ]
        
        self.font_path = None
        for path in font_paths:
            if os.path.exists(path):
                self.font_path = path
                break
        
        if self.font_path:
            self.add_font('Chinese', '', self.font_path, uni=True)
            self.add_font('Chinese', 'B', self.font_path, uni=True)
        
    def header(self):
        pass
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Chinese', '', 9)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')

# 创建 PDF
pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=20)

# 读取 markdown 内容
with open('阅读报告_修订版.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 处理标题和正文
lines = content.split('\n')

# 标题
pdf.set_font('Chinese', 'B', 18)
pdf.cell(0, 15, '论文阅读报告：SQIsign2D2数字签名方案', ln=True, align='C')
pdf.set_font('Chinese', '', 12)
pdf.cell(0, 10, '——基于一维光滑同源的SQIsign2D优化变种', ln=True, align='C')
pdf.ln(5)

# 处理内容
i = 0
in_table = False
table_data = []

while i < len(lines):
    line = lines[i].strip()
    
    # 跳过空行和分隔线
    if not line or line == '---' or line.startswith('─'):
        i += 1
        continue
    
    # 处理表格
    if line.startswith('|') and not in_table:
        in_table = True
        table_data = []
    
    if in_table:
        if line.startswith('|'):
            # 解析表格行
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells and not all(c.replace('-', '').replace(':', '') == '' for c in cells):
                table_data.append(cells)
            i += 1
        else:
            # 表格结束，渲染表格
            if len(table_data) >= 2:
                pdf.set_font('Chinese', '', 10)
                # 计算列宽
                col_widths = [40, 45, 55]
                
                for row_idx, row in enumerate(table_data):
                    if row_idx == 0:
                        pdf.set_font('Chinese', 'B', 10)
                    else:
                        pdf.set_font('Chinese', '', 10)
                    
                    # 计算行高
                    line_heights = []
                    for j, cell in enumerate(row):
                        if j < len(col_widths):
                            lines_needed = max(1, len(cell) // (col_widths[j] // 5))
                            line_heights.append(6 * lines_needed)
                    row_height = max(line_heights) if line_heights else 6
                    
                    # 绘制单元格
                    x_start = pdf.get_x()
                    y_start = pdf.get_y()
                    
                    for j, cell in enumerate(row):
                        if j < len(col_widths):
                            # 绘制边框
                            pdf.rect(x_start + sum(col_widths[:j]), y_start, col_widths[j], row_height)
                            # 添加文字
                            pdf.set_xy(x_start + sum(col_widths[:j]) + 2, y_start + 1)
                            pdf.cell(col_widths[j] - 4, row_height - 2, cell, 0, 0)
                    
                    pdf.set_y(y_start + row_height)
                
                pdf.ln(5)
            
            in_table = False
            table_data = []
            continue
    
    # 处理标题
    if line.startswith('# ') and not line.startswith('## '):
        title = line[2:].strip()
        pdf.set_font('Chinese', 'B', 16)
        pdf.ln(8)
        pdf.cell(0, 12, title, ln=True, align='C')
        pdf.ln(3)
    
    elif line.startswith('## '):
        title = line[3:].strip()
        pdf.set_font('Chinese', 'B', 14)
        pdf.ln(6)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(2)
    
    elif line.startswith('### '):
        title = line[4:].strip()
        pdf.set_font('Chinese', 'B', 12)
        pdf.ln(4)
        pdf.cell(0, 8, title, ln=True)
        pdf.ln(1)
    
    # 处理公式块
    elif line.startswith('$$'):
        formula_lines = []
        i += 1
        while i < len(lines) and not lines[i].strip().startswith('$$'):
            formula_lines.append(lines[i])
            i += 1
        formula = ' '.join(formula_lines).strip()
        if formula:
            pdf.set_font('Chinese', '', 10)
            pdf.cell(0, 8, f'    {formula}', ln=True)
            pdf.ln(2)
    
    # 处理普通段落
    elif line and not line.startswith('#') and not line.startswith('|') and not line.startswith('**'):
        # 处理行内格式
        text = line
        
        # 处理粗体 **text**
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # 处理行内公式 $...$
        text = re.sub(r'\$(.*?)\$', r'\1', text)
        
        # 处理列表
        if text.startswith('- ') or text.startswith('* '):
            text = '    • ' + text[2:]
        elif re.match(r'^\d+\.\s', text):
            text = '    ' + text
        
        if text.strip():
            pdf.set_font('Chinese', '', 11)
            # 首行缩进
            pdf.cell(10, 7, '', ln=0)
            # 自动换行处理
            pdf.multi_cell(0, 7, text)
            pdf.ln(1)
    
    # 处理带粗体的段落
    elif line.startswith('**') and line.endswith('**'):
        text = line[2:-2]
        pdf.set_font('Chinese', 'B', 11)
        pdf.cell(0, 7, text, ln=True)
        pdf.ln(1)
    
    i += 1

# 保存
pdf.output('阅读报告_修订版.pdf')
print('PDF generated: 阅读报告_修订版.pdf')
