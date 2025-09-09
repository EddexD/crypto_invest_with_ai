"""
智能投资分析引擎
结合技术分析和DeepSeek AI模型生成专业投资建议
"""

import json
import time
import re
import markdown
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from openai import OpenAI

from config.config_manager import config_manager
from src.utils.markdown_utils import markdown_to_html

logger = logging.getLogger(__name__)

@dataclass
class SmartAnalysisResult:
    """智能分析结果数据类"""
    symbol: str
    analysis_date: datetime
    market_overview: str
    portfolio_analysis: str
    trading_recommendations: str
    risk_management: str
    confidence_score: float
    key_price_levels: Dict[str, float]
    reasoning: str
    ai_response: str = ""  # 新增：原始AI响应内容

class SmartAnalysisEngine:
    """智能分析引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ai_config = config_manager.get_ai_config()
        self.client = None
        
        # 初始化DeepSeek客户端
        if self.ai_config.openai_key:
            try:
                self.client = OpenAI(
                    api_key=self.ai_config.openai_key,
                    base_url=self.ai_config.base_url
                )
            except Exception as e:
                self.logger.error(f"初始化DeepSeek客户端失败: {e}")
    
    def generate_custom_analysis(self, 
                                prompt: str,
                                market_data: Dict = None,
                                portfolio_data: Dict = None) -> SmartAnalysisResult:
        """
        使用自定义提示词生成分析
        
        Args:
            prompt: 自定义提示词
            market_data: 市场数据（可选）
            portfolio_data: 投资组合数据（可选）
            
        Returns:
            SmartAnalysisResult: 智能分析结果
        """
        
        # 如果有AI客户端，使用AI分析
        if self.client:
            try:
                ai_response = self._get_ai_analysis(prompt)
                
                # 将Markdown转换为HTML
                ai_response_html = markdown_to_html(ai_response)
                
                # 直接返回AI原始响应
                return SmartAnalysisResult(
                    symbol="CUSTOM",  # 表示这是自定义分析
                    market_overview="",  # 不填充，避免重复
                    portfolio_analysis="",  # 不填充，避免重复
                    trading_recommendations="",  # 不填充，避免重复
                    risk_management="",  # 不填充，避免重复
                    confidence_score=0.85,
                    analysis_date=datetime.now(),
                    key_price_levels={},  # 空字典，因为我们返回原始响应
                    reasoning="DeepSeek AI 自定义分析",
                    ai_response=ai_response_html  # 设置转换后的HTML响应
                )
            except Exception as e:
                self.logger.error(f"AI自定义分析失败: {e}")
                # 返回错误信息
                return SmartAnalysisResult(
                    symbol="CUSTOM",
                    market_overview="AI分析服务暂时不可用",
                    portfolio_analysis="",
                    trading_recommendations="",
                    risk_management="",
                    confidence_score=0.0,
                    analysis_date=datetime.now(),
                    key_price_levels={},
                    reasoning=f"AI分析失败: {str(e)}",
                    ai_response="AI分析服务暂时不可用，请稍后再试。"
                )
        
        # 如果没有AI客户端，返回提示信息
        return SmartAnalysisResult(
            symbol="CUSTOM",
            market_overview="AI服务未配置",
            portfolio_analysis="",
            trading_recommendations="",
            risk_management="",
            confidence_score=0.0,
            analysis_date=datetime.now(),
            key_price_levels={},
            reasoning="AI服务未配置",
            ai_response="AI服务未配置，请检查配置文件。"
        )
    
    def _get_ai_analysis(self, prompt: str) -> str:
        """获取AI分析结果"""
        try:
            st = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.ai_config.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": """你是一位拥有10年经验的专业加密货币投资顾问和技术分析师。"""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                web_search_options = {},  # 启用网络搜索工具
                stream=False,
                # temperature=0.2,  # 更低的随机性，提高分析的准确性和一致性
                max_tokens=3000,  # 增加token数量以获得更详细的分析
                # top_p=0.9,       # 控制输出质量
                # frequency_penalty=0.1,  # 减少重复内容
                # presence_penalty=0.1    # 鼓励多样化表达
            )
            self.logger.info(f"AI分析请求耗时: {time.perf_counter() - st:.2f}秒")
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"AI分析请求失败: {e}")
            raise
    

    def _create_fallback_analysis(self, ai_response: str) -> Dict:
        """创建回退分析数据"""
        # 尝试从AI响应中提取有用信息
        lines = ai_response.split('\n')
        market_content = []
        portfolio_content = []
        trading_content = []
        risk_content = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if any(keyword in line.lower() for keyword in ['市场', 'market', '趋势', 'trend']):
                current_section = 'market'
            elif any(keyword in line.lower() for keyword in ['持仓', 'portfolio', '组合']):
                current_section = 'portfolio'
            elif any(keyword in line.lower() for keyword in ['交易', 'trading', '建议', 'recommendation']):
                current_section = 'trading'
            elif any(keyword in line.lower() for keyword in ['风险', 'risk', '管理']):
                current_section = 'risk'
            
            if current_section == 'market':
                market_content.append(line)
            elif current_section == 'portfolio':
                portfolio_content.append(line)
            elif current_section == 'trading':
                trading_content.append(line)
            elif current_section == 'risk':
                risk_content.append(line)
        
        return {
            "market_overview": ' '.join(market_content[:3]) or "基于当前市场数据的综合分析",
            "portfolio_analysis": ' '.join(portfolio_content[:3]) or "投资组合结构和表现分析",
            "trading_recommendations": ' '.join(trading_content[:3]) or "基于技术分析的交易建议",
            "risk_management": ' '.join(risk_content[:3]) or "风险控制和管理策略",
            "confidence_score": 0.6,
            "key_price_levels": {},
            "reasoning": ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
        }
    
    def _create_fallback_analysis_result(self, ai_response: str) -> SmartAnalysisResult:
        """创建回退分析结果"""
        return SmartAnalysisResult(
            symbol="PORTFOLIO",
            analysis_date=datetime.now(),
            market_overview=f"AI分析：{ai_response[:200]}..." if len(ai_response) > 200 else ai_response,
            portfolio_analysis="基于AI的综合投资组合分析",
            trading_recommendations="请参考AI提供的详细分析内容制定交易策略",
            risk_management="建议保持谨慎的投资策略，控制风险敞口",
            confidence_score=0.6,
            key_price_levels={},
            reasoning=ai_response
        )
    
    def _generate_technical_analysis(self, market_data: Dict, portfolio_data: Dict, technical_indicators: Dict) -> SmartAnalysisResult:
        """生成技术分析（回退方案）"""
        
        # 简单的技术分析逻辑
        market_overview = "基于技术指标的市场分析显示当前市场处于震荡状态。"
        portfolio_analysis = f"当前投资组合总价值${portfolio_data.get('total_value', 0):.2f}，"
        portfolio_analysis += f"盈亏${portfolio_data.get('total_pnl', 0):.2f}。"
        
        trading_recommendations = "建议根据技术指标信号进行操作，注意风险控制。"
        risk_management = "建议设置止损位，控制单笔损失在5%以内。"
        
        return SmartAnalysisResult(
            symbol="PORTFOLIO",
            analysis_date=datetime.now(),
            market_overview=market_overview,
            portfolio_analysis=portfolio_analysis,
            trading_recommendations=trading_recommendations,
            risk_management=risk_management,
            confidence_score=0.6,
            key_price_levels={},
            reasoning="基于技术指标的综合分析"
        )
    
