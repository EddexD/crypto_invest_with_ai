"""
Markdown转HTML工具
将AI生成的Markdown文本转换为格式化的HTML
"""

import re
from typing import List

class MarkdownToHtmlConverter:
    """Markdown转HTML转换器"""
    
    def __init__(self):
        self.html_styles = {
            'h3': 'color: #212529; margin: 20px 0 12px 0; font-weight: bold; font-size: 1.2em; border-bottom: 3px solid #007bff; padding-bottom: 8px;',
            'h4': 'color: #343a40; margin: 18px 0 10px 0; font-weight: bold; font-size: 1.1em; border-bottom: 2px solid #dee2e6; padding-bottom: 6px;',
            'h5': 'color: #495057; margin: 15px 0 8px 0; font-weight: bold; font-size: 1.05em; border-bottom: 1px solid #e9ecef; padding-bottom: 4px;',
            'h5_numbered': 'color: #495057; margin: 12px 0 8px 0; font-weight: bold; font-size: 1.05em; background: #f8f9fa; padding: 8px 12px; border-left: 4px solid #007bff; border-radius: 4px;',
            'h4_emoji': 'color: #2c3e50; margin: 14px 0 8px 0; font-weight: bold; font-size: 1.05em; background: linear-gradient(90deg, #f8f9fa, #ffffff); padding: 10px 15px; border-left: 4px solid #28a745; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);',
            'ul': 'margin: 8px 0; padding-left: 20px; list-style-type: disc;',
            'ol': 'margin: 8px 0; padding-left: 20px; list-style-type: decimal;',
            'li': 'margin: 4px 0; padding-left: 8px; color: #495057; line-height: 1.5;',
            'p': 'margin: 8px 0; line-height: 1.6; color: #495057; font-size: 0.95em;',
            'strong': 'color: #2c3e50; font-weight: 600; background: #fff3cd; padding: 2px 4px; border-radius: 3px;',
            'em': 'color: #495057; font-style: italic;',
            'code': 'background: #f1f3f4; padding: 2px 4px; border-radius: 3px; font-family: monospace;',
            'table': 'width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em;',
            'th': 'border: 1px solid #dee2e6; padding: 8px 12px; background: #f8f9fa; font-weight: bold; text-align: left;',
            'td': 'border: 1px solid #dee2e6; padding: 8px 12px; background: #ffffff;'
        }
    
    def convert(self, markdown: str) -> str:
        """
        将Markdown转换为HTML
        
        Args:
            markdown: 原始Markdown文本
            
        Returns:
            str: 转换后的HTML
        """
        if not markdown:
            return ''
        
        # 清理输入并按行分割
        lines = markdown.strip().split('\n')
        html_parts = []
        in_list = False
        list_type = None  # 'ul' 或 'ol'
        in_table = False
        table_headers = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            trimmed_line = line.strip()
            
            # 跳过空行
            if not trimmed_line:
                # 结束当前列表或表格
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                if in_table:
                    html_parts.append('</table>')
                    in_table = False
                    table_headers = []
                i += 1
                continue
            
            # 处理表格
            if '|' in trimmed_line and trimmed_line.startswith('|') and trimmed_line.endswith('|'):
                if not in_table:
                    # 开始表格
                    in_table = True
                    html_parts.append(f'<table style="{self.html_styles["table"]}">')
                    # 处理表头
                    headers = [cell.strip() for cell in trimmed_line.split('|')[1:-1]]
                    table_headers = headers
                    header_html = ''.join([f'<th style="{self.html_styles["th"]}">{self._format_inline_text(header)}</th>' for header in headers])
                    html_parts.append(f'<tr>{header_html}</tr>')
                elif i + 1 < len(lines) and '---' in lines[i + 1]:
                    # 跳过分隔行
                    i += 2
                    continue
                else:
                    # 处理表格行
                    cells = [cell.strip() for cell in trimmed_line.split('|')[1:-1]]
                    row_html = ''.join([f'<td style="{self.html_styles["td"]}">{self._format_inline_text(cell)}</td>' for cell in cells])
                    html_parts.append(f'<tr>{row_html}</tr>')
                i += 1
                continue
            
            # 如果之前在表格中，现在不是表格行，结束表格
            if in_table:
                html_parts.append('</table>')
                in_table = False
                table_headers = []
            
            # 处理标题
            if trimmed_line.startswith('###'):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                title = trimmed_line.replace('###', '').strip()
                html_parts.append(f'<h5 style="{self.html_styles["h5"]}">{self._format_inline_text(title)}</h5>')
            elif trimmed_line.startswith('##'):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                title = trimmed_line.replace('##', '').strip()
                html_parts.append(f'<h4 style="{self.html_styles["h4"]}">{self._format_inline_text(title)}</h4>')
            elif trimmed_line.startswith('#'):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                title = trimmed_line.replace('#', '').strip()
                html_parts.append(f'<h3 style="{self.html_styles["h3"]}">{self._format_inline_text(title)}</h3>')
            
            # 处理数字标题 (如 "1. **USDT余额配置建议**：")
            elif re.match(r'^\d+\.\s+', trimmed_line):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                html_parts.append(f'<h5 style="{self.html_styles["h5_numbered"]}">{self._format_inline_text(trimmed_line)}</h5>')
            
            # 处理emoji开头的标题
            elif re.match(r'^(📊|📈|🎯|💼|⚡|⚠️|💡|📋|🤖|💰|🔍|📌|⚖️|🚀|🛡️|✅|🟡|🟢|🔽|🔼|📉|📈|🟢)\s+', trimmed_line):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                html_parts.append(f'<h4 style="{self.html_styles["h4_emoji"]}">{self._format_inline_text(trimmed_line)}</h4>')
            
            # 处理列表项
            elif trimmed_line.startswith('- ') or trimmed_line.startswith('* ') or trimmed_line.startswith('+ '):
                if not in_list:
                    html_parts.append(f'<ul style="{self.html_styles["ul"]}">')
                    in_list = True
                    list_type = 'ul'
                elif list_type != 'ul':
                    html_parts.append(f'</{list_type}>')
                    html_parts.append(f'<ul style="{self.html_styles["ul"]}">')
                    list_type = 'ul'
                
                content = re.sub(r'^[-*+]\s+', '', trimmed_line)
                html_parts.append(f'<li style="{self.html_styles["li"]}">{self._format_inline_text(content)}</li>')
            
            # 处理缩进的文本（作为列表项）
            elif line.startswith('  ') or line.startswith('\t'):
                if not in_list:
                    html_parts.append(f'<ul style="{self.html_styles["ul"]}">')
                    in_list = True
                    list_type = 'ul'
                html_parts.append(f'<li style="{self.html_styles["li"]}">{self._format_inline_text(trimmed_line)}</li>')
            
            # 处理普通段落
            else:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                html_parts.append(f'<p style="{self.html_styles["p"]}">{self._format_inline_text(trimmed_line)}</p>')
            
            i += 1
        
        # 确保最后关闭列表和表格
        if in_list:
            html_parts.append(f'</{list_type}>')
        if in_table:
            html_parts.append('</table>')
        
        return ''.join(html_parts)
    
    def _format_inline_text(self, text: str) -> str:
        """
        处理行内格式（粗体、斜体等）
        
        Args:
            text: 原始文本
            
        Returns:
            str: 格式化后的HTML文本
        """
        # 处理粗体
        text = re.sub(r'\*\*(.*?)\*\*', f'<strong style="{self.html_styles["strong"]}">\\1</strong>', text)
        
        # 处理斜体
        text = re.sub(r'\*(.*?)\*', f'<em style="{self.html_styles["em"]}">\\1</em>', text)
        
        # 处理代码
        text = re.sub(r'`(.*?)`', f'<code style="{self.html_styles["code"]}">\\1</code>', text)
        
        # 处理价格（如 $113,500）
        text = re.sub(r'\$([0-9,]+(?:\.[0-9]+)?)', '<span style="color: #007bff; font-weight: 600;">$\\1</span>', text)
        
        # 处理百分比
        text = re.sub(r'([0-9]+(?:\.[0-9]+)?)%', '<span style="color: #28a745; font-weight: 600;">\\1%</span>', text)
        
        # 处理USDT
        text = re.sub(r'(\b\d+(?:\.\d+)?\s*USDT\b)', '<span style="color: #ffc107; font-weight: 600;">\\1</span>', text)
        
        return text

# 创建全局转换器实例
markdown_converter = MarkdownToHtmlConverter()
