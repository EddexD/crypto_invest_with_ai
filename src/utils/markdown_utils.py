"""
Markdown工具模块
提供Markdown到HTML转换功能
"""

import re
import logging

logger = logging.getLogger(__name__)

def markdown_to_html(markdown_text: str) -> str:
    """
    将Markdown文本转换为HTML
    
    Args:
        markdown_text: Markdown格式的文本
        
    Returns:
        str: 转换后的HTML文本
    """
    if not markdown_text:
        return ""
    
    try:
        # 尝试使用markdown库
        import markdown
        
        # 配置markdown扩展
        extensions = [
            'tables',      # 表格支持
            'fenced_code', # 代码块支持
            'nl2br',       # 换行转换
        ]
        
        # 创建markdown实例
        md = markdown.Markdown(extensions=extensions)
        
        # 转换并添加样式
        html = md.convert(markdown_text)
        
        # 添加自定义样式
        html = _add_custom_styles(html)
        
        return html
        
    except ImportError:
        logger.warning("markdown库未安装，使用简化转换")
        return _simple_markdown_to_html(markdown_text)
    except Exception as e:
        logger.error(f"Markdown转换失败: {e}")
        return _simple_markdown_to_html(markdown_text)

def _add_custom_styles(html: str) -> str:
    """为HTML添加自定义样式"""
    
    # 为标题添加样式
    html = re.sub(
        r'<h1>(.*?)</h1>', 
        r'<h1 style="color: #212529; margin: 20px 0 12px 0; font-weight: bold; font-size: 1.2em; border-bottom: 3px solid #007bff; padding-bottom: 8px;">\1</h1>', 
        html
    )
    html = re.sub(
        r'<h2>(.*?)</h2>', 
        r'<h2 style="color: #343a40; margin: 18px 0 10px 0; font-weight: bold; font-size: 1.1em; border-bottom: 2px solid #dee2e6; padding-bottom: 6px;">\1</h2>', 
        html
    )
    html = re.sub(
        r'<h3>(.*?)</h3>', 
        r'<h3 style="color: #495057; margin: 15px 0 8px 0; font-weight: bold; font-size: 1.05em; border-bottom: 1px solid #e9ecef; padding-bottom: 4px;">\1</h3>', 
        html
    )
    html = re.sub(
        r'<h4>(.*?)</h4>', 
        r'<h4 style="color: #2c3e50; margin: 14px 0 8px 0; font-weight: bold; font-size: 1.05em; background: linear-gradient(90deg, #f8f9fa, #ffffff); padding: 10px 15px; border-left: 4px solid #28a745; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">\1</h4>', 
        html
    )
    html = re.sub(
        r'<h5>(.*?)</h5>', 
        r'<h5 style="color: #495057; margin: 12px 0 8px 0; font-weight: bold; font-size: 1.05em; background: #f8f9fa; padding: 8px 12px; border-left: 4px solid #007bff; border-radius: 4px;">\1</h5>', 
        html
    )
    
    # 为段落添加样式
    html = re.sub(
        r'<p>(.*?)</p>', 
        r'<p style="margin: 8px 0; line-height: 1.6; color: #495057; font-size: 0.95em;">\1</p>', 
        html, flags=re.DOTALL
    )
    
    # 为列表添加样式
    html = re.sub(
        r'<ul>', 
        r'<ul style="margin: 8px 0; padding-left: 20px; list-style-type: disc;">', 
        html
    )
    html = re.sub(
        r'<ol>', 
        r'<ol style="margin: 8px 0; padding-left: 20px;">', 
        html
    )
    html = re.sub(
        r'<li>(.*?)</li>', 
        r'<li style="margin: 4px 0; padding-left: 8px; color: #495057; line-height: 1.5;">\1</li>', 
        html, flags=re.DOTALL
    )
    
    # 为强调添加样式
    html = re.sub(
        r'<strong>(.*?)</strong>', 
        r'<strong style="color: #2c3e50; font-weight: 600; background: #fff3cd; padding: 2px 4px; border-radius: 3px;">\1</strong>', 
        html
    )
    html = re.sub(
        r'<em>(.*?)</em>', 
        r'<em style="color: #495057; font-style: italic;">\1</em>', 
        html
    )
    
    # 为表格添加样式
    html = re.sub(
        r'<table>', 
        r'<table style="width: 100%; border-collapse: collapse; margin: 15px 0; border: 1px solid #dee2e6;">', 
        html
    )
    html = re.sub(
        r'<th>(.*?)</th>', 
        r'<th style="padding: 12px; text-align: left; background: #f8f9fa; font-weight: bold; color: #333; border: 1px solid #dee2e6;">\1</th>', 
        html
    )
    html = re.sub(
        r'<td>(.*?)</td>', 
        r'<td style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">\1</td>', 
        html
    )
    
    # 为代码添加样式
    html = re.sub(
        r'<code>(.*?)</code>', 
        r'<code style="background: #f1f3f4; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>', 
        html
    )
    
    return html

def _simple_markdown_to_html(markdown_text: str) -> str:
    """简化的Markdown到HTML转换（当markdown库不可用时）"""
    
    html = markdown_text
    
    # 处理标题
    html = re.sub(r'^### (.*$)', r'<h3 style="color: #495057; margin: 15px 0 8px 0; font-weight: bold; font-size: 1.05em; border-bottom: 1px solid #e9ecef; padding-bottom: 4px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*$)', r'<h2 style="color: #343a40; margin: 18px 0 10px 0; font-weight: bold; font-size: 1.1em; border-bottom: 2px solid #dee2e6; padding-bottom: 6px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*$)', r'<h1 style="color: #212529; margin: 20px 0 12px 0; font-weight: bold; font-size: 1.2em; border-bottom: 3px solid #007bff; padding-bottom: 8px;">\1</h1>', html, flags=re.MULTILINE)
    
    # 处理数字标题
    html = re.sub(r'^(\d+)\.\s+(.+)$', r'<h5 style="color: #495057; margin: 12px 0 8px 0; font-weight: bold; font-size: 1.05em; background: #f8f9fa; padding: 8px 12px; border-left: 4px solid #007bff; border-radius: 4px;">\1. \2</h5>', html, flags=re.MULTILINE)
    
    # 处理emoji标题
    html = re.sub(r'^(📊|📈|🎯|💼|⚡|⚠️|💡|📋|🤖|💰|🔍|📌|⚖️|🚀|🛡️|✅|🟡|🟢|🔽|🔼|📉|📈)\s+(.+)$', r'<h4 style="color: #2c3e50; margin: 14px 0 8px 0; font-weight: bold; font-size: 1.05em; background: linear-gradient(90deg, #f8f9fa, #ffffff); padding: 10px 15px; border-left: 4px solid #28a745; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">\1 \2</h4>', html, flags=re.MULTILINE)
    
    # 处理粗体和斜体
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #2c3e50; font-weight: 600; background: #fff3cd; padding: 2px 4px; border-radius: 3px;">\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em style="color: #495057; font-style: italic;">\1</em>', html)
    
    # 处理列表
    lines = html.split('\n')
    result_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            continue
            
        if line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
            if not in_list:
                result_lines.append('<ul style="margin: 8px 0; padding-left: 20px; list-style-type: disc;">')
                in_list = True
            content = re.sub(r'^[-*+]\s+', '', line)
            result_lines.append(f'<li style="margin: 4px 0; padding-left: 8px; color: #495057; line-height: 1.5;">{content}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            
            # 如果不是标题，包装为段落
            if not line.startswith('<h') and not line.startswith('<ul') and not line.startswith('</ul'):
                result_lines.append(f'<p style="margin: 8px 0; line-height: 1.6; color: #495057; font-size: 0.95em;">{line}</p>')
            else:
                result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    return '\n'.join(result_lines)
