# -*- coding: utf-8 -*-
import os
import sys

# 获取当前目录下的docx文件
folder = os.path.dirname(os.path.abspath(__file__))
docx_file = os.path.join(folder, '作品设计报告.docx')
pdf_file = os.path.join(folder, '作品设计报告.pdf')

if not os.path.exists(docx_file):
    # 尝试查找包含docx的文件（处理编码问题）
    for f in os.listdir(folder):
        if f.endswith('.docx') and '报告' in f:
            docx_file = os.path.join(folder, f)
            break

print(f'Converting: {docx_file}')
print(f'Output: {pdf_file}')

try:
    from win32com.client import Dispatch
    word = Dispatch('Word.Application')
    word.Visible = False
    doc = word.Documents.Open(docx_file)
    doc.SaveAs(pdf_file, FileFormat=17)  # 17 = PDF
    doc.Close()
    word.Quit()
    print('PDF generated successfully!')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
