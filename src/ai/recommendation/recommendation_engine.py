"""
智能投资推荐引擎
结合AI分析和技术分析生成投资建议
支持异步处理和缓存机制
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.ai.analysis.technical_analysis import TechnicalAnalyzer
from src.ai.analysis.smart_analysis_engine import SmartAnalysisEngine
from src.ai.analysis.analysis_task_manager import analysis_task_manager
from src.data.fetchers.market_data_fetcher import MarketDataFetcher

logger = logging.getLogger(__name__)

@dataclass
class InvestmentRecommendation:
    """投资建议数据类"""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-1之间
    price_target: Optional[float]
    stop_loss: Optional[float]
    reasoning: str
    technical_indicators: Dict
    timestamp: datetime

@dataclass
class SmartRecommendationResult:
    """智能推荐结果"""
    market_analysis: str
    portfolio_review: str
    trading_signals: str
    risk_assessment: str
    individual_recommendations: List[InvestmentRecommendation]
    ai_confidence: float
    analysis_timestamp: datetime
    ai_response: str = ""  # 新增：原始AI响应内容

class SmartRecommendationEngine:
    """智能推荐引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.technical_analyzer = TechnicalAnalyzer()
        self.smart_analyzer = SmartAnalysisEngine()
        
        # 延迟初始化market_fetcher，避免循环依赖
        self.market_fetcher = None
    
    def _get_market_fetcher(self):
        """获取市场数据获取器（延迟初始化）"""
        if self.market_fetcher is None:
            try:
                from config.config_manager import config_manager
                exchange_config = config_manager.get_exchange_config()
                self.market_fetcher = MarketDataFetcher(exchange_config.name)
            except Exception as e:
                self.logger.error(f"初始化市场数据获取器失败: {e}")
                # 使用默认平台
                self.market_fetcher = MarketDataFetcher('okx')
        return self.market_fetcher
    
    def generate_comprehensive_analysis_async(self, portfolio_data: Dict, symbols: List[str], force_refresh: bool = False) -> str:
        """
        异步生成综合智能分析
        
        Args:
            portfolio_data: 投资组合数据
            symbols: 要分析的交易对列表
            force_refresh: 是否强制刷新缓存
            
        Returns:
            str: 任务ID，可用于查询分析状态和结果
        """
        return analysis_task_manager.start_analysis_task(
            portfolio_data=portfolio_data,
            symbols=symbols,
            analysis_func=self._sync_comprehensive_analysis,
            force_refresh=force_refresh
        )
    
    def _sync_comprehensive_analysis(self, portfolio_data: Dict, symbols: List[str]) -> SmartRecommendationResult:
        """同步版本的综合分析（用于异步调用）"""
        return self.generate_comprehensive_analysis(portfolio_data, symbols)
    
    def get_analysis_status(self, task_id: str) -> Optional[Dict]:
        """
        获取分析任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务状态信息，包含进度、结果等
        """
        return analysis_task_manager.get_task_status(task_id)
    
    def generate_comprehensive_analysis(self, portfolio_data: Dict, symbols: List[str]) -> SmartRecommendationResult:
        """
        生成综合智能分析 - 只给出整体持仓和市场信息，不再对每个交易对单独AI分析
        
        Args:
            portfolio_data: 投资组合数据
            symbols: 要分析的交易对列表
            
        Returns:
            SmartRecommendationResult: 综合智能推荐结果
        """
        try:
            # 获取市场数据
            market_fetcher = self._get_market_fetcher()
            market_data = market_fetcher.get_multiple_tickers(symbols)

            # 获取当前限价委托订单
            try:
                # 需要获取私有数据获取器来获取订单信息
                from src.data.fetchers.private_data_fetcher import PrivateDataFetcher
                from config.config_manager import config_manager
                
                exchange_config = config_manager.get_exchange_config()
                private_fetcher = PrivateDataFetcher(
                    platform=exchange_config.name,
                    api_key=exchange_config.api_key,
                    secret=exchange_config.secret_key,
                    password=exchange_config.passphrase
                )
                
                open_orders = private_fetcher.get_open_orders()
                orders_info = []
                if open_orders:
                    for order in open_orders:
                        order_type = f"{order.side.name.upper()} {order.type.name.upper()}"
                        price_info = f"${order.price:.2f}" if order.price else "市价"
                        orders_info.append(f"{order.symbol:<12} {order_type:<10} {order.amount:>10.6f} {price_info:>10}")
                
                orders_table = ""
                if orders_info:
                    orders_table = "交易对         类型        数量          价格\n" + "-"*50 + "\n" + "\n".join(orders_info)
                else:
                    orders_table = "当前无未完成订单"
            except Exception as e:
                self.logger.warning(f"获取订单信息失败: {e}")
                orders_table = "无法获取订单信息"

            # 构建市场行情表格
            market_rows = []
            for symbol in symbols:
                ticker = market_data.get(symbol)
                if ticker:
                    market_rows.append(f"{symbol:<8} {ticker.close:>10.2f} {ticker.percentage:>8.2f}% {ticker.volume:>16,.0f}")
                else:
                    market_rows.append(f"{symbol:<8} {'N/A':>10} {'N/A':>8} {'N/A':>16}")
            market_table = "代币            收盘价     % 变化          24h交易量\n" + "-"*60 + "\n" + "\n".join(market_rows)

            # 获取交易对最近30天的K线数据
            ohlcv_data = {}
            for symbol in symbols:
                ohlcv_data[symbol] = market_fetcher.get_ohlcv(symbol, '1d', limit=45)
            ohlcv_table = "代币 日期 开盘价 高价 低价 收盘价 成交量\n"
            for symbol, ohlcv in ohlcv_data.items():
                ohlcv_table += f"{''.join([f'{symbol:<12} {datetime.fromtimestamp(candle.timestamp / 1000).strftime('%Y-%m-%d')} {candle.open:.2f} {candle.high:.2f} {candle.low:.2f} {candle.close:.2f} {candle.volume:.0f}\n' for candle in ohlcv])}"

            # 构建持仓表格
            position_rows = []
            positions = portfolio_data.get('positions', [])
            for pos in positions:
                pnl_color = '🟢' if pos.get('unrealized_pnl', 0) >= 0 else '🔴'
                pnl_value = f"{pos.get('unrealized_pnl', 0):+.1f} {pnl_color}"
                pnl_rate = f"{pos.get('unrealized_pnl_rate', 0)*100:+.1f}%"
                cost_price = float(pos.get('cost'))/float(pos.get('amount')) if pos.get('amount', 0) != 0 else 0
                market_price = float(pos.get('market_value', 0))/float(pos.get('amount', 0)) if pos.get('amount', 0) != 0 else 0
                position_rows.append(f"{pos.get('symbol', ''):<8} {pos.get('amount', 0):>10.6f} {cost_price:>8.2f} {market_price:>8.2f} {pos.get('cost', 0):>8.1f} {pos.get('market_value', 0):>8.1f} {pnl_value:>8} {pnl_rate:>8}")
            position_table = "代币        数量        成本价    当前价      成本      当前价值     盈亏        盈亏%\n" + "-"*85 + "\n" + "\n".join(position_rows)

            # 投资组合汇总
            total_cost = portfolio_data.get('total_cost', 0)
            total_value = portfolio_data.get('total_value', 0)
            total_pnl = portfolio_data.get('total_pnl', 0)
            total_pnl_rate = portfolio_data.get('total_pnl_rate', 0)
            summary = f"总成本: ${total_cost:.2f} USDT\n当前价值: ${total_value:.2f} USDT\n总盈亏: {total_pnl:+.2f} USDT ({'🟢' if total_pnl >= 0 else '🔴'}{total_pnl_rate*100:+.2f}%)"

            # 构建AI提示词
            prompt = f"""
======================================================================
加密货币投资组合分析 - {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
======================================================================

[ 当前市场行情 ]
{market_table}

[ 最近30天K线数据 ]
{ohlcv_table}

[ 我所关注的币种 ]
{', '.join([s.replace('/USDT','').replace('/USD','') for s in symbols])}

[ 我的持仓情况 ]
{position_table}

[ 投资组合汇总 ]
{summary}

[ 当前未完成订单 ]
{orders_table}

[ 投资指导请求 ]
作为专业的加密货币投资顾问，请基于以上市场数据、我的持仓情况和当前订单状态，请使用网络搜索获取最新市场新闻、宏观政策及技术指标信息，然后再进行分析，提供以下分析：

1. **当前市场环境分析**：基于市场行情判断整体趋势和风险等级
2. **持仓优化建议**：针对当前我的持仓情况，给出明确的操作建议和价格点位。
3. **订单管理建议**：对于当前未完成的限价委托订单，建议是否需要调整价格、取消或保持。
4. **资金管理策略**：USDT余额如何分配、新的建仓机会、风险控制措施
5.1. **具体买入建议**：使用网络搜索获取最新的技术面和新闻面信息；
5.2. 基于历史 K 线数据、技术趋势与最新消息，为每个关注币种提供：
   - 合理的 **买入价格区间**；
   - 建议的 **买入金额**（USDT，下限/上限或具体数量）；
   - **买入原因**（技术面、基本面、消息面等）。

请提供具体、可操作的投资建议，包括：
- 明确的买入/卖出价格点位
- 止损和止盈设置
- 订单调整建议（如修改限价订单价格）
- 资金分配比例建议

请用markdown格式回复，突出重点信息。持仓优化建议、订单管理建议、具体买入建议都以表格形式输出
======================================================================
"""
            with open("debug_prompt.txt", "w",encoding="utf-8") as f:
                f.write(prompt)
            # 调用AI分析引擎
            ai_result = self.smart_analyzer.generate_custom_analysis(
                prompt=prompt,
                market_data=market_data,
                portfolio_data=portfolio_data
            )

            # 返回结果，只填充ai_response字段
            return SmartRecommendationResult(
                market_analysis="",
                portfolio_review="",
                trading_signals="",
                risk_assessment="",
                individual_recommendations=[],
                ai_confidence=ai_result.confidence_score if hasattr(ai_result, 'confidence_score') else 0.8,
                analysis_timestamp=ai_result.analysis_date if hasattr(ai_result, 'analysis_date') else datetime.now(),
                ai_response=ai_result.ai_response if hasattr(ai_result, 'ai_response') else ""
            )
        except Exception as e:
            self.logger.error(f"生成综合分析时出错: {e}")
            return self._generate_fallback_analysis(portfolio_data, symbols)
    
    def generate_recommendations(self, portfolio_data: Dict, symbols: List[str]) -> List[InvestmentRecommendation]:
        """
        生成投资建议（保持向后兼容）
        
        Args:
            portfolio_data: 投资组合数据
            symbols: 要分析的交易对列表
            
        Returns:
            List[InvestmentRecommendation]: 投资建议列表
        """
        comprehensive_result = self.generate_comprehensive_analysis(portfolio_data, symbols)
        return comprehensive_result.individual_recommendations
    
    def _generate_individual_recommendations(self, symbols: List[str], market_data: Dict, 
                                           technical_indicators: Dict, portfolio_data: Dict) -> List[InvestmentRecommendation]:
        """生成个别交易对建议"""
        
        recommendations = []
        
        for symbol in symbols:
            try:
                market_ticker = market_data.get(symbol)
                if market_ticker is None:
                    continue
                
                # 转换MarketDataModel为字典格式
                market_dict = {
                    'price': market_ticker.close,
                    'volume': market_ticker.volume,
                    'change': market_ticker.change,
                    'percentage': market_ticker.percentage
                }
                
                recommendation = self._generate_single_recommendation(
                    symbol, market_dict, 
                    technical_indicators.get(symbol, {}), portfolio_data
                )
                
                if recommendation:
                    recommendations.append(recommendation)
                    
            except Exception as e:
                self.logger.error(f"生成{symbol}建议时出错: {e}")
                continue
        
        return recommendations
    
    def _combine_symbol_analyses(self, symbol_analyses: Dict, field_name: str) -> str:
        """合并各交易对的分析结果"""
        if not symbol_analyses:
            return "暂无分析数据"
        
        combined_text = ""
        for symbol, analysis in symbol_analyses.items():
            symbol_short = symbol.replace('/USDT', '').replace('/USD', '')
            field_value = getattr(analysis, field_name, "暂无数据")
            combined_text += f"\n【{symbol_short}】\n{field_value}\n"
        
        return combined_text.strip()
    
    def _generate_single_recommendation(self, symbol: str, market_data: Dict, 
                                      indicators: Dict, portfolio_data: Dict) -> Optional[InvestmentRecommendation]:
        """生成单个交易对的建议"""
        
        try:
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_position = indicators.get('bb_position', 0.5)
            sma_20 = indicators.get('sma_20', 0)
            sma_50 = indicators.get('sma_50', 0)
            
            current_price = market_data.get('price', 0)
            
            # 强化的信号评分系统
            buy_score = 0
            sell_score = 0
            
            # RSI信号 (权重: 30%)
            if rsi < 25:
                buy_score += 3
            elif rsi < 35:
                buy_score += 2
            elif rsi < 45:
                buy_score += 1
            elif rsi > 75:
                sell_score += 3
            elif rsi > 65:
                sell_score += 2
            elif rsi > 55:
                sell_score += 1
            
            # MACD信号 (权重: 25%)
            macd_diff = macd - macd_signal
            if macd_diff > 0:
                if macd > 0:
                    buy_score += 2  # 金叉且在零轴上方
                else:
                    buy_score += 1  # 金叉但在零轴下方
            else:
                if macd < 0:
                    sell_score += 2  # 死叉且在零轴下方
                else:
                    sell_score += 1  # 死叉但在零轴上方
            
            # 布林带信号 (权重: 20%)
            if bb_position < 0.15:
                buy_score += 2
            elif bb_position < 0.3:
                buy_score += 1
            elif bb_position > 0.85:
                sell_score += 2
            elif bb_position > 0.7:
                sell_score += 1
            
            # 均线信号 (权重: 25%)
            if sma_20 > sma_50:
                price_above_sma20 = current_price > sma_20
                if price_above_sma20:
                    buy_score += 2
                else:
                    buy_score += 1
            else:
                price_below_sma20 = current_price < sma_20
                if price_below_sma20:
                    sell_score += 2
                else:
                    sell_score += 1
            
            # 计算总分
            total_signals = buy_score + sell_score
            max_possible_score = 10
            
            # 确定行动和信心度
            if buy_score > sell_score and buy_score >= 3:
                action = 'BUY'
                confidence = min(buy_score / max_possible_score, 0.9)
                price_target = current_price * (1.03 + confidence * 0.05)  # 3-8%目标
                stop_loss = current_price * (0.95 - confidence * 0.02)     # 3-5%止损
            elif sell_score > buy_score and sell_score >= 3:
                action = 'SELL'
                confidence = min(sell_score / max_possible_score, 0.9)
                price_target = current_price * (0.97 - confidence * 0.05)  # 3-8%目标
                stop_loss = current_price * (1.05 + confidence * 0.02)     # 3-5%止损
            else:
                action = 'HOLD'
                confidence = 0.4 + abs(buy_score - sell_score) / max_possible_score * 0.3
                price_target = current_price
                stop_loss = current_price * 0.97
            
            # 生成详细推理
            reasoning_parts = []
            reasoning_parts.append(f"RSI: {rsi:.1f}")
            
            if rsi < 30:
                reasoning_parts.append("(超卖)")
            elif rsi > 70:
                reasoning_parts.append("(超买)")
            else:
                reasoning_parts.append("(正常)")
            
            reasoning_parts.append(f"MACD: {'金叉' if macd > macd_signal else '死叉'}")
            reasoning_parts.append(f"布林带: {bb_position:.1%}")
            reasoning_parts.append(f"均线: {'多头' if sma_20 > sma_50 else '空头'}排列")
            reasoning_parts.append(f"信号强度: 买入{buy_score}/卖出{sell_score}")
            
            reasoning = " | ".join(reasoning_parts)
            
            return InvestmentRecommendation(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                reasoning=reasoning,
                technical_indicators=indicators,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"生成{symbol}推荐时出错: {e}")
            return None
    
    def _generate_fallback_analysis(self, portfolio_data: Dict, symbols: List[str]) -> SmartRecommendationResult:
        """生成回退分析（当AI分析失败时）"""
        
        try:
            # 生成基本技术分析建议
            basic_recommendations = []
            market_fetcher = self._get_market_fetcher()
            
            for symbol in symbols:
                try:
                    market_data = market_fetcher.get_ticker(symbol)
                    ohlcv_data = market_fetcher.get_ohlcv(symbol, '4h', limit=50)
                    
                    if market_data and ohlcv_data:
                        # 转换OHLCV数据为字典格式
                        candles = []
                        for candle in ohlcv_data:
                            candles.append({
                                'timestamp': candle.timestamp,
                                'open': candle.open,
                                'high': candle.high,
                                'low': candle.low,
                                'close': candle.close,
                                'volume': candle.volume
                            })
                        
                        indicators = self.technical_analyzer.calculate_indicators(candles)
                        # 转换为字典格式
                        indicators_dict = {
                            'sma_20': indicators.sma_20,
                            'sma_50': indicators.sma_50,
                            'rsi': indicators.rsi,
                            'macd': indicators.macd,
                            'macd_signal': indicators.macd_signal,
                            'bb_position': indicators.bb_position
                        }
                        
                        # 转换market_data为字典格式
                        market_dict = {
                            'price': market_data.close,
                            'volume': market_data.volume,
                            'change': market_data.change,
                            'percentage': market_data.percentage
                        }
                        
                        rec = self._generate_single_recommendation(symbol, market_dict, indicators_dict, portfolio_data)
                        if rec:
                            basic_recommendations.append(rec)
                except Exception as e:
                    self.logger.warning(f"生成{symbol}基本分析失败: {e}")
            
            total_value = portfolio_data.get('total_value', 0)
            total_pnl = portfolio_data.get('total_pnl', 0)
            
            return SmartRecommendationResult(
                market_analysis="当前市场数据显示主要加密货币价格波动正常，建议密切关注技术指标变化。",
                portfolio_review=f"投资组合总价值: ${total_value:.2f} USDT，总盈亏: ${total_pnl:.2f} USDT",
                trading_signals="基于技术分析，建议根据个别交易对信号进行操作。",
                risk_assessment="建议保持适当的风险控制，设置合理的止损位。",
                individual_recommendations=basic_recommendations,
                ai_confidence=0.6,
                analysis_timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"生成回退分析失败: {e}")
            return SmartRecommendationResult(
                market_analysis="无法获取完整市场分析",
                portfolio_review="无法获取投资组合分析",
                trading_signals="建议谨慎操作",
                risk_assessment="建议加强风险控制",
                individual_recommendations=[],
                ai_confidence=0.3,
                analysis_timestamp=datetime.now()
            )

# 为了保持向后兼容性，保留原始类名
RecommendationEngine = SmartRecommendationEngine
